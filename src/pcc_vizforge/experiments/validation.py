"""Monte Carlo validation of the package's estimators and tests.

Because every generator has *known* ground-truth parameters, we can measure
how well each estimator recovers them: bias, root-mean-square error and the
empirical coverage of nominal 95 % confidence intervals, and -- for
hypothesis tests -- the rejection rate under the null (size). Replicates use
independent RNG streams spawned from one root seed, so each study is exactly
reproducible.

Studies
-------
``b_value``        Aki-Utsu b-value MLE vs. catalogue size.
``msd_exponent``   Walk-bootstrap anomalous exponent vs. Hurst exponent.
``power_law``      CSN discrete power-law α vs. true exponent.
``dice_gof``       Size of the χ² sum test (p-values should be U(0, 1)).
``trend_hac``      Coverage of OLS vs. Newey-West trend CIs under AR(1) noise.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.rng import make_rng, spawn_seeds

__all__ = ["STUDIES", "StudyResult", "run_study", "summarize"]


@dataclass
class StudyResult:
    """Replicate-level results and their per-setting summary."""

    name: str
    replicates: pd.DataFrame
    summary: pd.DataFrame
    description: str


def summarize(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Bias, RMSE and coverage per ``by`` value (with Monte Carlo SEs)."""
    rows = []
    for value, g in df.groupby(by, sort=True):
        err = g["estimate"] - g["truth"]
        n = len(g)
        cov = g["covered"].mean()
        rows.append(
            {
                by: value,
                "n_replicates": n,
                "truth": g["truth"].iloc[0],
                "mean_estimate": g["estimate"].mean(),
                "bias": err.mean(),
                "bias_mcse": err.std(ddof=1) / np.sqrt(n),
                "rmse": float(np.sqrt(np.mean(err**2))),
                "coverage_95": cov,
                "coverage_mcse": float(np.sqrt(cov * (1 - cov) / n)),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Individual studies (each returns replicate-level rows)
# --------------------------------------------------------------------------- #
def _study_b_value(seeds: list[np.random.SeedSequence], sizes: Iterable[int] = (50, 100, 250, 500, 1000, 2500)) -> pd.DataFrame:
    from pcc_vizforge.analysis.seismology import b_value_mle, truncated_gr_sample

    rows = []
    for n in sizes:
        for i, ss in enumerate(seeds):
            m = truncated_gr_sample(make_rng(ss), n, 1.0, 2.0)
            est = b_value_mle(m, 2.0)
            rows.append({"n_events": n, "replicate": i, "truth": 1.0, "estimate": est.b_value, "covered": est.ci[0] <= 1.0 <= est.ci[1]})
    return pd.DataFrame(rows)


def _study_msd_exponent(seeds: list[np.random.SeedSequence], hursts: Iterable[float] = (0.25, 0.5, 0.75)) -> pd.DataFrame:
    from pcc_vizforge.analysis.diffusion import bootstrap_msd_exponent
    from pcc_vizforge.generators.random_walk import (
        RandomWalkParams,
        simulate_increments,
    )

    rows = []
    for h in hursts:
        p = RandomWalkParams(n_steps=256, n_walks=100, model="fbm", hurst=h)
        for i, ss in enumerate(seeds):
            pos = np.cumsum(simulate_increments(p, make_rng(ss)), axis=1)
            fit = bootstrap_msd_exponent(pos, n_bootstrap=200, seed=ss.spawn(1)[0])
            rows.append({"hurst": h, "replicate": i, "truth": 2 * h, "estimate": fit.alpha, "covered": fit.alpha_ci[0] <= 2 * h <= fit.alpha_ci[1]})
    return pd.DataFrame(rows)


def _study_power_law(seeds: list[np.random.SeedSequence], alphas: Iterable[float] = (1.8, 2.2, 2.6, 3.0)) -> pd.DataFrame:
    from pcc_vizforge.analysis.heavy_tails import fit_power_law, sample_power_law

    rows = []
    for a in alphas:
        for i, ss in enumerate(seeds):
            x = sample_power_law(make_rng(ss), 1000, a, 1, discrete=True)
            fit = fit_power_law(x, xmin=1)
            lo, hi = fit.alpha - 1.96 * fit.alpha_stderr, fit.alpha + 1.96 * fit.alpha_stderr
            rows.append({"alpha": a, "replicate": i, "truth": a, "estimate": fit.alpha, "covered": lo <= a <= hi})
    return pd.DataFrame(rows)


def _study_dice_gof(seeds: list[np.random.SeedSequence], n_dice: Iterable[int] = (1, 2, 3, 5)) -> pd.DataFrame:
    from pcc_vizforge.generators.dice import DiceGenerator

    rows = []
    for k in n_dice:
        gen = DiceGenerator(n_rolls=500, n_dice=k)
        for i, ss in enumerate(seeds):
            p = gen.calculate_probabilities(gen.generate(seed=ss))["sum_gof"]["p_value"]
            rows.append({"n_dice": k, "replicate": i, "p_value": p, "rejected_5pct": p < 0.05})
    return pd.DataFrame(rows)


def _study_trend_hac(seeds: list[np.random.SeedSequence], phis: Iterable[float] = (0.0, 0.4, 0.7, 0.9)) -> pd.DataFrame:
    from pcc_vizforge.analysis.timeseries import fit_harmonics
    from pcc_vizforge.generators.weather import ar1

    rows = []
    t = np.arange(1500.0)
    slope = 0.002
    for phi in phis:
        for i, ss in enumerate(seeds):
            y = slope * t + 5 * np.sin(2 * np.pi * t / 365.25) + ar1(make_rng(ss), t.size, phi, 2.0)
            fit = fit_harmonics(t, y, n_harmonics=1)
            for method, se in (("ols", fit.trend_stderr), ("hac", fit.trend_stderr_hac)):
                rows.append(
                    {
                        "phi": phi,
                        "method": method,
                        "replicate": i,
                        "truth": slope,
                        "estimate": fit.trend_per_unit,
                        "covered": abs(fit.trend_per_unit - slope) <= 1.96 * se,
                    }
                )
    return pd.DataFrame(rows)


STUDIES: dict[str, tuple[Callable[[list[np.random.SeedSequence]], pd.DataFrame], str, str]] = {
    "b_value": (_study_b_value, "n_events", "Aki-Utsu b-value MLE (true b = 1) vs catalogue size"),
    "msd_exponent": (_study_msd_exponent, "hurst", "Walk-bootstrap MSD exponent for fBm (true α = 2H)"),
    "power_law": (_study_power_law, "alpha", "Discrete power-law MLE (x_min = 1, n = 1000)"),
    "dice_gof": (_study_dice_gof, "n_dice", "Size of the χ² GOF test on dice sums under H0"),
    "trend_hac": (_study_trend_hac, "phi", "Trend-CI coverage, OLS vs Newey-West, AR(1) noise"),
}


def run_study(name: str, n_replicates: int = 200, seed: int = 20240101) -> StudyResult:
    """Run a validation study and summarise it."""
    if name not in STUDIES:
        raise InvalidParameterError(f"Unknown study {name!r}; choose from {sorted(STUDIES)}")
    fn, by, description = STUDIES[name]
    reps = fn(spawn_seeds(seed, n_replicates))
    if name == "dice_gof":
        rows = []
        for k, g in reps.groupby(by):
            size = g["rejected_5pct"].mean()
            rows.append(
                {
                    by: k,
                    "n_replicates": len(g),
                    "size_at_5pct": size,
                    "size_mcse": float(np.sqrt(size * (1 - size) / len(g))),
                    "ks_uniform_pvalue": float(stats.kstest(g["p_value"], "uniform").pvalue),
                }
            )
        summary = pd.DataFrame(rows)
    elif name == "trend_hac":
        parts = []
        for method, g in reps.groupby("method"):
            s = summarize(g, by)
            s.insert(1, "method", method)
            parts.append(s)
        summary = pd.concat(parts).sort_values([by, "method"]).reset_index(drop=True)
    else:
        summary = summarize(reps, by)
    return StudyResult(name, reps, summary, description)


def study_to_dict(result: StudyResult) -> dict[str, Any]:
    """JSON-friendly summary of a study."""
    return {
        "study": result.name,
        "description": result.description,
        "summary": result.summary.to_dict(orient="records"),
    }
