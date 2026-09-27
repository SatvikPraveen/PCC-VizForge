"""Reproducible experiment runs.

A *run* simulates one dataset, analyses it, renders diagnostic figures, and
writes everything to a self-contained directory::

    runs/<domain>-<YYYYmmdd-HHMMSS>-<run_id>/
        config.yaml      fully resolved configuration (after overrides)
        data.csv         the simulated dataset
        metrics.json     analysis results
        figures/*.png    diagnostic figures (and/or .pdf/.svg)
        manifest.json    provenance: seed, config hash, environment, git
                         revision and SHA-256 of every file above

:func:`verify_run` regenerates the dataset from ``manifest.json`` alone and
checks that its hash matches, turning reproducibility into a testable claim.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from pcc_vizforge.exceptions import ConfigurationError, PccVizForgeError
from pcc_vizforge.generators import (
    DiceGenerator,
    EarthquakeGenerator,
    GitHubGenerator,
    RandomWalkGenerator,
    WeatherGenerator,
)
from pcc_vizforge.generators.base import BaseGenerator
from pcc_vizforge.provenance import RunManifest, file_sha256
from pcc_vizforge.rng import resolve_seed

logger = logging.getLogger(__name__)

__all__ = ["DOMAINS", "RunResult", "analyze", "run_experiment", "verify_run"]

DOMAINS: dict[str, type[BaseGenerator[Any]]] = {
    "random_walk": RandomWalkGenerator,
    "dice": DiceGenerator,
    "weather": WeatherGenerator,
    "quakes": EarthquakeGenerator,
    "github": GitHubGenerator,
}


def _jsonable(obj: Any) -> Any:
    """Recursively convert NumPy / pandas objects into JSON-friendly values."""
    if isinstance(obj, Mapping):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, float) and not np.isfinite(obj):
        return str(obj)
    return obj


# --------------------------------------------------------------------------- #
# Per-domain analysis and figures
# --------------------------------------------------------------------------- #
def _analyze_random_walk(gen: RandomWalkGenerator, df: pd.DataFrame, seed: int) -> dict[str, Any]:
    from pcc_vizforge.analysis import diffusion
    from pcc_vizforge.generators.random_walk import frame_to_positions, theoretical_msd

    p = gen.params
    pos = frame_to_positions(df)
    out: dict[str, Any] = {"summary": gen.calculate_statistics(df)}
    lags = diffusion.log_spaced_lags(p.n_steps + 1)
    lags = lags[lags <= p.n_steps]
    if p.n_walks >= 2 and lags.size >= 3:
        fit = diffusion.bootstrap_msd_exponent(pos, lags=lags, n_bootstrap=500, seed=seed)
        out["msd_exponent"] = fit.to_dict()
        theo = theoretical_msd(p, np.array([1.0, 2.0]))
        if np.all(np.isfinite(theo)) and p.model in ("lattice", "gaussian", "fbm"):
            out["theoretical_exponent"] = 2 * p.hurst if p.model == "fbm" else 1.0
        tl, tamsd = diffusion.time_averaged_msd(pos, lags)
        out["ergodicity_breaking"] = dict(
            zip(map(int, tl), map(float, diffusion.ergodicity_breaking_parameter(tamsd)), strict=True)
        )
    if p.n_steps >= 128 and p.model in ("gaussian", "fbm", "lattice"):
        increments = np.diff(pos[..., 0], axis=1, prepend=0.0)
        hursts = [diffusion.dfa(inc)[0].alpha for inc in increments[: min(50, p.n_walks)]]
        out["dfa_hurst_mean"] = float(np.mean(hursts))
        out["dfa_hurst_sd"] = float(np.std(hursts, ddof=1)) if len(hursts) > 1 else 0.0
    return out


def _analyze_dice(gen: DiceGenerator, df: pd.DataFrame, seed: int) -> dict[str, Any]:
    probs = gen.calculate_probabilities(df)
    return {
        "probabilities": probs,
        "fairness_test": gen.fairness_test(df),
        "streaks": {k: v for k, v in gen.generate_streak_analysis(df).items() if k != "identical_value_streaks"},
    }


def _analyze_default(gen: Any, df: pd.DataFrame, seed: int) -> dict[str, Any]:
    return dict(gen.calculate_statistics(df))


ANALYZERS: dict[str, Callable[[Any, pd.DataFrame, int], dict[str, Any]]] = {
    "random_walk": _analyze_random_walk,
    "dice": _analyze_dice,
    "weather": _analyze_default,
    "quakes": _analyze_default,
    "github": _analyze_default,
}


def analyze(domain: str, gen: BaseGenerator[Any], df: pd.DataFrame, seed: int = 0) -> dict[str, Any]:
    """Run the standard analysis for ``domain`` and return JSON-ready metrics."""
    return _jsonable(ANALYZERS[domain](gen, df, seed))


def _figures(domain: str, gen: Any, df: pd.DataFrame, metrics: dict[str, Any]) -> dict[str, Any]:
    """Build the diagnostic figures for a domain (name -> Figure)."""
    import matplotlib

    matplotlib.use("Agg", force=False)
    from pcc_vizforge.analysis import (
        diffusion,
        heavy_tails,
        probability,
        seismology,
        timeseries,
    )
    from pcc_vizforge.plots import diagnostics as D

    figs: dict[str, Any] = {}
    if domain == "random_walk":
        from pcc_vizforge.generators.random_walk import (
            frame_to_positions,
            theoretical_msd,
        )

        pos = frame_to_positions(df)
        if pos.shape[0] >= 2:
            msd, sem = diffusion.ensemble_msd(pos)
            t = np.arange(1, msd.size + 1)
            theo = theoretical_msd(gen.params, t)
            fit = None
            if "msd_exponent" in metrics:
                m = metrics["msd_exponent"]
                fit = diffusion.PowerLawFit(
                    m["alpha"], m["alpha_stderr"], tuple(m["alpha_ci"]), m["prefactor"], m["r_squared"], m["n_points"], tuple(m["x_range"])
                )
            figs["msd"] = D.msd_figure(t, msd, sem, theory=theo if np.all(np.isfinite(theo)) else None, fit=fit)
    elif domain == "dice":
        p = gen.params
        support, pmf = probability.sum_pmf(p.n_dice, p.dice_sides, p.weights)
        counts = gen.roll_sums(df).value_counts().reindex(support, fill_value=0).to_numpy()
        figs["sum_distribution"] = D.dice_sum_figure(
            support, pmf, counts, p_value=metrics["probabilities"]["sum_gof"]["p_value"]
        )
    elif domain == "quakes":
        p = gen.params
        est = seismology.b_value_mle(df["magnitude"], p.magnitude_range[0], bin_width=p.magnitude_bin)
        figs["gutenberg_richter"] = D.gutenberg_richter_figure(df["magnitude"], est, bin_width=max(p.magnitude_bin, 0.1))
        after = df[df["is_aftershock"]]
        if len(after) >= 30:
            parent_t = df.set_index("earthquake_id").loc[after["parent_id"], "time_days"].to_numpy()
            delays = after["time_days"].to_numpy() - parent_t
            try:
                figs["aftershock_decay"] = D.omori_figure(delays, seismology.fit_omori(delays))
            except PccVizForgeError:
                logger.info("Skipping Omori figure: fit failed")
    elif domain == "weather":
        t = (df["date"] - df["date"].iloc[0]).dt.days.to_numpy(dtype=float)
        harmonic = timeseries.fit_harmonics(t, df["temperature_avg"].to_numpy(), n_harmonics=1)
        figs["temperature"] = D.temperature_figure(t, df["temperature_avg"], harmonic)
    elif domain == "github":
        stars = df["stars"].to_numpy()
        stars = stars[stars > 0]
        fit = None
        if "power_law" in metrics:
            m = metrics["power_law"]
            fit = heavy_tails.PowerLawFit(**m)
        if stars.size:
            figs["stars_ccdf"] = D.ccdf_figure(stars, fit, label="Stars")
    return figs


# --------------------------------------------------------------------------- #
# Runs
# --------------------------------------------------------------------------- #
@dataclass
class RunResult:
    """Paths and results of a completed run."""

    run_dir: Path
    manifest: RunManifest
    data: pd.DataFrame
    metrics: dict[str, Any]
    figures: list[Path] = field(default_factory=list)


def run_experiment(
    domain: str,
    *,
    config: str | Path | Mapping[str, Any] | None = None,
    overrides: Iterable[str] = (),
    seed: int | None = None,
    output_dir: str | Path = "runs",
    figures: bool = True,
    formats: Iterable[str] = ("png",),
    run_name: str | None = None,
) -> RunResult:
    """Simulate, analyse, plot and record one experiment.

    Args:
        domain: One of :data:`DOMAINS`.
        config: Bundled config name, YAML path or config mapping (defaults to
            the domain's bundled config).
        overrides: ``key.path=value`` overrides.
        seed: RNG seed; defaults to ``data_generation.random_seed`` or fresh
            entropy. The seed actually used is always recorded.
        output_dir: Parent directory for run folders.
        figures: Render diagnostic figures.
        formats: Figure file formats (e.g. ``("png", "pdf")``).
        run_name: Folder name override.
    """
    if domain not in DOMAINS:
        raise ConfigurationError(f"Unknown domain {domain!r}; choose from {sorted(DOMAINS)}")
    cls = DOMAINS[domain]
    gen = cls(config=config, overrides=overrides) if isinstance(config, Mapping) else cls(config, overrides=overrides)
    used_seed = resolve_seed(seed if seed is not None else gen.params.random_seed)
    # Record the seed in the config so config.yaml alone reproduces the run.
    gen.data_config["random_seed"] = used_seed

    manifest = RunManifest(domain=domain, seed=used_seed, config=gen.config)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = Path(output_dir) / (run_name or f"{domain}-{stamp}-{manifest.run_id}")
    run_dir.mkdir(parents=True, exist_ok=False)

    config_path = run_dir / "config.yaml"
    config_path.write_text(yaml.safe_dump(_jsonable(gen.config), sort_keys=False), encoding="utf-8")

    df = gen.generate(seed=used_seed)
    data_path = run_dir / "data.csv"
    df.to_csv(data_path, index=False)

    metrics = analyze(domain, gen, df, used_seed)
    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    fig_paths: list[Path] = []
    if figures:
        import matplotlib.pyplot as plt

        fig_dir = run_dir / "figures"
        fig_dir.mkdir()
        for name, fig in _figures(domain, gen, df, metrics).items():
            for fmt in formats:
                path = fig_dir / f"{name}.{fmt}"
                # Fixed metadata keeps PDF/SVG bytes deterministic.
                fig.savefig(path, format=fmt, metadata={"CreationDate": None} if fmt == "pdf" else None)
                fig_paths.append(path)
            plt.close(fig)

    manifest.metrics = {"data_sha256": file_sha256(data_path)}
    for path in [config_path, data_path, metrics_path, *fig_paths]:
        manifest.register_output(path, root=run_dir)
    manifest.write(run_dir / "manifest.json")
    logger.info("Run written to %s", run_dir)
    return RunResult(run_dir, manifest, df, metrics, fig_paths)


def verify_run(run_dir: str | Path) -> dict[str, Any]:
    """Regenerate a run's dataset from its manifest and compare hashes.

    Returns a report with ``reproduced`` (data hash matches), per-file
    ``integrity`` (stored files unchanged since the run) and version info.
    """
    run_dir = Path(run_dir)
    manifest = RunManifest.read(run_dir / "manifest.json")
    gen = DOMAINS[manifest.domain](config=manifest.config)
    df = gen.generate(seed=manifest.seed)
    tmp = run_dir / ".verify.csv"
    try:
        df.to_csv(tmp, index=False)
        regenerated = file_sha256(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    integrity = {
        name: (run_dir / name).exists() and file_sha256(run_dir / name) == digest
        for name, digest in manifest.outputs.items()
    }
    return {
        "run_id": manifest.run_id,
        "domain": manifest.domain,
        "seed": manifest.seed,
        "reproduced": regenerated == manifest.outputs.get("data.csv"),
        "integrity": integrity,
        "recorded_versions": manifest.environment.get("packages", {}),
    }
