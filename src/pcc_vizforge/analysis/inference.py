"""General-purpose statistical inference utilities.

All tests return a :class:`TestResult` so that downstream code (reports,
manifests, plots) can treat them uniformly.

References
----------
Cochran, W. G. (1954). Some methods for strengthening the common chi-squared
    tests. *Biometrics* 10(4), 417-451.
Wald, A. & Wolfowitz, J. (1940). On a test whether two samples are from the
    same population. *Ann. Math. Statist.* 11(2), 147-162.
Ljung, G. M. & Box, G. E. P. (1978). On a measure of lack of fit in time
    series models. *Biometrika* 65(2), 297-303.
Efron, B. (1987). Better bootstrap confidence intervals. *JASA* 82(397),
    171-185.
Benjamini, Y. & Hochberg, Y. (1995). Controlling the false discovery rate.
    *J. R. Stat. Soc. B* 57(1), 289-300.
Holm, S. (1979). A simple sequentially rejective multiple test procedure.
    *Scand. J. Statist.* 6(2), 65-70.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import stats

from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.rng import SeedLike, make_rng

__all__ = [
    "ConfidenceInterval",
    "TestResult",
    "adjust_pvalues",
    "autocorrelation",
    "bootstrap_ci",
    "chi_square_gof",
    "ljung_box",
    "runs_test",
]


@dataclass(frozen=True)
class TestResult:
    """Outcome of a statistical hypothesis test."""

    __test__ = False  # stop pytest from collecting this class

    name: str
    statistic: float
    p_value: float
    dof: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def reject(self, alpha: float = 0.05) -> bool:
        """Whether the null hypothesis is rejected at level ``alpha``."""
        return bool(self.p_value < alpha)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConfidenceInterval:
    """A point estimate with a two-sided confidence interval."""

    estimate: float
    low: float
    high: float
    confidence: float
    method: str

    def contains(self, value: float) -> bool:
        return bool(self.low <= value <= self.high)

    @property
    def width(self) -> float:
        return self.high - self.low

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_1d(x: ArrayLike, name: str = "x") -> NDArray[np.float64]:
    arr = np.asarray(x, dtype=float).ravel()
    if arr.size == 0:
        raise InvalidParameterError(f"{name} must be non-empty")
    if not np.all(np.isfinite(arr)):
        raise InvalidParameterError(f"{name} contains NaN or infinite values")
    return arr


# --------------------------------------------------------------------------- #
# Goodness of fit
# --------------------------------------------------------------------------- #
def _pool_small_bins(
    observed: NDArray[np.float64], expected: NDArray[np.float64], min_expected: float
) -> tuple[NDArray[np.float64], NDArray[np.float64], list[list[int]]]:
    """Greedily merge adjacent bins until every expected count >= ``min_expected``.

    Bins are assumed to be ordered (e.g. dice sums); merging proceeds from the
    tails inwards, which is the textbook treatment for unimodal distributions.
    """
    groups: list[list[int]] = [[i] for i in range(len(expected))]
    obs = list(observed)
    exp = list(expected)

    def merge(i: int, j: int) -> None:
        obs[i] += obs[j]
        exp[i] += exp[j]
        groups[i].extend(groups[j])
        del obs[j], exp[j], groups[j]

    while len(exp) > 1 and exp[0] < min_expected:
        merge(0, 1)
    while len(exp) > 1 and exp[-1] < min_expected:
        merge(len(exp) - 2, len(exp) - 1)
    i = 0
    while i < len(exp) and len(exp) > 1:
        if exp[i] < min_expected:
            j = i + 1 if i + 1 < len(exp) else i - 1
            lo, hi = min(i, j), max(i, j)
            merge(lo, hi)
            i = max(lo - 1, 0)
        else:
            i += 1
    for g in groups:
        g.sort()
    return np.asarray(obs), np.asarray(exp), groups


def chi_square_gof(
    observed: ArrayLike,
    expected_probs: ArrayLike,
    *,
    min_expected: float = 5.0,
    pool: bool = True,
    ddof: int = 0,
) -> TestResult:
    """Pearson chi-square goodness-of-fit test.

    Args:
        observed: Observed counts per category (ordered if pooling).
        expected_probs: Hypothesised category probabilities (renormalised).
        min_expected: Cochran's minimum expected count per cell.
        pool: Merge adjacent sparse cells so every expected count reaches
            ``min_expected``; otherwise the chi-square approximation is poor.
        ddof: Extra degrees of freedom lost to parameters estimated from the
            data (e.g. 1 for a fitted Poisson mean).
    """
    obs = np.asarray(observed, dtype=float).ravel()
    probs = np.asarray(expected_probs, dtype=float).ravel()
    if obs.shape != probs.shape:
        raise InvalidParameterError(
            "observed and expected_probs must have equal length"
        )
    if np.any(obs < 0) or np.any(probs < 0):
        raise InvalidParameterError("counts and probabilities must be non-negative")
    if probs.sum() <= 0:
        raise InvalidParameterError("expected_probs must not sum to zero")
    n = obs.sum()
    expected = probs / probs.sum() * n

    groups = [[i] for i in range(len(obs))]
    if pool:
        obs, expected, groups = _pool_small_bins(obs, expected, min_expected)

    mask = expected > 0
    if np.any(obs[~mask] > 0):
        return TestResult(
            "chi_square_gof",
            float("inf"),
            0.0,
            None,
            {"reason": "observed count in a zero-probability cell"},
        )
    obs, expected = obs[mask], expected[mask]
    k = len(obs)
    dof = k - 1 - ddof
    if dof < 1:
        raise InvalidParameterError(
            f"Not enough cells after pooling for a chi-square test (cells={k}, ddof={ddof})"
        )
    statistic = float(np.sum((obs - expected) ** 2 / expected))
    p_value = float(stats.chi2.sf(statistic, dof))
    return TestResult(
        "chi_square_gof",
        statistic,
        p_value,
        float(dof),
        {
            "n": float(n),
            "n_cells": k,
            "pooled_groups": groups,
            "min_expected": float(expected.min()),
            "cramers_v": float(np.sqrt(statistic / (n * max(k - 1, 1))))
            if n > 0
            else 0.0,
        },
    )


# --------------------------------------------------------------------------- #
# Randomness / independence
# --------------------------------------------------------------------------- #
def runs_test(
    x: ArrayLike, cutoff: float | Literal["median", "mean"] = "median"
) -> TestResult:
    """Wald-Wolfowitz runs test for randomness of a sequence.

    Observations equal to the cutoff are discarded (standard practice). Under
    H0 (exchangeable sequence) the number of runs is asymptotically normal.
    """
    arr = _as_1d(x)
    if cutoff == "median":
        c = float(np.median(arr))
    elif cutoff == "mean":
        c = float(np.mean(arr))
    else:
        c = float(cutoff)
    signs = arr[arr != c] > c
    n1 = int(signs.sum())
    n2 = int(signs.size - n1)
    if n1 == 0 or n2 == 0:
        raise InvalidParameterError(
            "runs_test needs observations on both sides of the cutoff"
        )
    runs = int(1 + np.count_nonzero(signs[1:] != signs[:-1]))
    n = n1 + n2
    mu = 2.0 * n1 * n2 / n + 1.0
    var = 2.0 * n1 * n2 * (2.0 * n1 * n2 - n) / (n**2 * (n - 1.0))
    z = (runs - mu) / np.sqrt(var) if var > 0 else 0.0
    p = float(2.0 * stats.norm.sf(abs(z)))
    return TestResult(
        "wald_wolfowitz_runs",
        float(z),
        p,
        None,
        {"runs": runs, "expected_runs": mu, "n_above": n1, "n_below": n2, "cutoff": c},
    )


def autocorrelation(x: ArrayLike, max_lag: int | None = None) -> NDArray[np.float64]:
    """Sample autocorrelation function via FFT, ``acf[0] == 1``.

    Uses the biased (1/n) estimator, which guarantees a positive
    semi-definite sequence.
    """
    arr = _as_1d(x)
    n = arr.size
    if max_lag is None:
        max_lag = min(n - 1, int(10 * np.log10(n)) if n > 1 else 0)
    if not 0 <= max_lag < n:
        raise InvalidParameterError(f"max_lag must be in [0, {n - 1}], got {max_lag}")
    centred = arr - arr.mean()
    nfft = 1 << int(np.ceil(np.log2(2 * n - 1)))
    f = np.fft.rfft(centred, n=nfft)
    acov = np.fft.irfft(f * np.conj(f), n=nfft)[: max_lag + 1] / n
    if acov[0] == 0:
        return np.r_[1.0, np.zeros(max_lag)]
    return acov / acov[0]


def ljung_box(x: ArrayLike, lags: int = 10, ddof: int = 0) -> TestResult:
    """Ljung-Box portmanteau test for autocorrelation up to ``lags``."""
    arr = _as_1d(x)
    n = arr.size
    if not 1 <= lags < n:
        raise InvalidParameterError(f"lags must be in [1, {n - 1}], got {lags}")
    r = autocorrelation(arr, lags)[1:]
    q = float(n * (n + 2) * np.sum(r**2 / (n - np.arange(1, lags + 1))))
    dof = lags - ddof
    return TestResult(
        "ljung_box", q, float(stats.chi2.sf(q, dof)), float(dof), {"lags": lags}
    )


# --------------------------------------------------------------------------- #
# Resampling
# --------------------------------------------------------------------------- #
def bootstrap_ci(
    data: ArrayLike,
    statistic: Callable[..., Any] = np.mean,
    *,
    confidence: float = 0.95,
    n_resamples: int = 2000,
    method: Literal["percentile", "basic", "BCa"] = "BCa",
    seed: SeedLike = None,
) -> ConfidenceInterval:
    """Non-parametric bootstrap confidence interval for a scalar statistic.

    ``statistic`` must accept an ``axis`` keyword (NumPy reductions do), which
    lets SciPy vectorise the resampling.
    """
    arr = _as_1d(data, "data")
    if not 0 < confidence < 1:
        raise InvalidParameterError("confidence must be in (0, 1)")
    if arr.size < 2:
        raise InvalidParameterError("bootstrap needs at least two observations")
    rng = make_rng(seed)
    res = stats.bootstrap(
        (arr,),
        statistic,
        confidence_level=confidence,
        n_resamples=n_resamples,
        method=method,
        random_state=rng,
        vectorized=True,
    )
    low, high = float(res.confidence_interval.low), float(res.confidence_interval.high)
    return ConfidenceInterval(
        float(statistic(arr, axis=-1)), low, high, confidence, method
    )


# --------------------------------------------------------------------------- #
# Multiple comparisons
# --------------------------------------------------------------------------- #
def adjust_pvalues(
    p_values: Sequence[float] | Mapping[str, float] | NDArray[np.float64],
    method: Literal["bonferroni", "holm", "bh"] = "bh",
) -> NDArray[np.float64]:
    """Adjust p-values for multiple testing.

    ``"bh"`` controls the false discovery rate (Benjamini-Hochberg); ``"holm"``
    and ``"bonferroni"`` control the family-wise error rate.
    """
    values = list(p_values.values()) if isinstance(p_values, Mapping) else p_values
    p = np.asarray(values, dtype=float)
    if p.ndim != 1:
        raise InvalidParameterError("p_values must be one-dimensional")
    if np.any((p < 0) | (p > 1)):
        raise InvalidParameterError("p-values must lie in [0, 1]")
    m = p.size
    if m == 0:
        return p
    order = np.argsort(p)
    ranked = p[order]
    if method == "bonferroni":
        adj = np.minimum(ranked * m, 1.0)
    elif method == "holm":
        adj = np.maximum.accumulate((m - np.arange(m)) * ranked)
        adj = np.minimum(adj, 1.0)
    elif method == "bh":
        adj = ranked * m / np.arange(1, m + 1)
        adj = np.minimum.accumulate(adj[::-1])[::-1]
        adj = np.minimum(adj, 1.0)
    else:
        raise InvalidParameterError(f"Unknown method {method!r}")
    out = np.empty_like(adj)
    out[order] = adj
    return out
