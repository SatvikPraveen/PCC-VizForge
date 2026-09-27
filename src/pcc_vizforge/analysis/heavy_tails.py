"""Power-law and heavy-tail inference following Clauset, Shalizi & Newman (2009).

Workflow
--------
1. :func:`fit_power_law` -- MLE of the exponent α for x ≥ x_min, with x_min
   chosen to minimise the Kolmogorov-Smirnov distance between the data and
   the fitted model.
2. :func:`power_law_gof` -- semi-parametric bootstrap p-value for the
   hypothesis that the data are power-law distributed (p > 0.1 is the
   customary threshold for plausibility).
3. :func:`compare_distributions` -- Vuong's normalised log-likelihood-ratio
   test against lognormal / exponential alternatives on the same tail.

Both continuous and discrete (integer, x_min ≥ 1) power laws are supported;
the discrete MLE uses the Hurwitz zeta normalisation, and the alternatives in
likelihood-ratio tests are discretised (lognormal by binning the CDF at
half-integers, exponential as a geometric law) so that likelihoods are
commensurable pmfs.

References
----------
Clauset, A., Shalizi, C. R. & Newman, M. E. J. (2009). Power-law
    distributions in empirical data. *SIAM Rev.* 51(4), 661-703.
Vuong, Q. H. (1989). Likelihood ratio tests for model selection and
    non-nested hypotheses. *Econometrica* 57(2), 307-333.
Hill, B. M. (1975). A simple general approach to inference about the tail
    of a distribution. *Ann. Statist.* 3(5), 1163-1174.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import optimize, special, stats

from pcc_vizforge.analysis.inference import TestResult
from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.rng import SeedLike, make_rng

__all__ = [
    "PowerLawFit",
    "ccdf",
    "compare_distributions",
    "fit_power_law",
    "gini",
    "hill_estimator",
    "power_law_gof",
    "sample_power_law",
]


@dataclass(frozen=True)
class PowerLawFit:
    """Fitted power law p(x) ∝ x^(-alpha) for x >= xmin."""

    alpha: float
    alpha_stderr: float
    xmin: float
    ks_distance: float
    n_tail: int
    n_total: int
    discrete: bool

    def ccdf(self, x: ArrayLike) -> NDArray[np.float64]:
        """Model P(X >= x) for x >= xmin."""
        xx = np.asarray(x, dtype=float)
        if self.discrete:
            return special.zeta(self.alpha, xx) / special.zeta(self.alpha, self.xmin)
        return (xx / self.xmin) ** (1.0 - self.alpha)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean(x: ArrayLike) -> NDArray[np.float64]:
    arr = np.asarray(x, dtype=float).ravel()
    arr = arr[np.isfinite(arr)]
    return arr[arr > 0]


def ccdf(x: ArrayLike) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Empirical complementary CDF, P(X >= x), at the sorted unique values."""
    arr = np.sort(_clean(x))
    if arr.size == 0:
        raise InvalidParameterError("no positive values")
    values, first = np.unique(arr, return_index=True)
    return values, 1.0 - first / arr.size


# --------------------------------------------------------------------------- #
# MLE for fixed xmin
# --------------------------------------------------------------------------- #
def _alpha_continuous(tail: NDArray[np.float64], xmin: float) -> float:
    return 1.0 + tail.size / np.sum(np.log(tail / xmin))


def _alpha_discrete(tail: NDArray[np.float64], xmin: float) -> float:
    log_sum = np.sum(np.log(tail))
    n = tail.size

    def nll(a: float) -> float:
        return float(n * np.log(special.zeta(a, xmin)) + a * log_sum)

    # CSN eq. (3.7) approximation as a starting bracket.
    guess = 1.0 + n / np.sum(np.log(tail / (xmin - 0.5))) if xmin > 0.5 else 2.5
    res = optimize.minimize_scalar(
        nll, bounds=(1.0001, max(guess * 2, 6.0)), method="bounded"
    )
    return float(res.x)


def _ks_distance(
    tail: NDArray[np.float64], alpha: float, xmin: float, discrete: bool
) -> float:
    xs = np.sort(tail)
    n = xs.size
    if discrete:
        vals, idx = np.unique(xs, return_index=True)
        emp = idx / n  # P(X < v)
        model = 1.0 - special.zeta(alpha, vals) / special.zeta(alpha, xmin)
        return float(np.max(np.abs(emp - model)))
    model = 1.0 - (xs / xmin) ** (1.0 - alpha)
    emp_hi = np.arange(1, n + 1) / n
    emp_lo = np.arange(n) / n
    return float(max(np.max(np.abs(emp_hi - model)), np.max(np.abs(emp_lo - model))))


def _fit_fixed(data: NDArray[np.float64], xmin: float, discrete: bool) -> PowerLawFit:
    tail = data[data >= xmin]
    if tail.size < 2 or np.all(tail == xmin):
        raise InvalidParameterError("not enough distinct observations above xmin")
    alpha = _alpha_discrete(tail, xmin) if discrete else _alpha_continuous(tail, xmin)
    se = (alpha - 1.0) / np.sqrt(tail.size)
    return PowerLawFit(
        alpha=float(alpha),
        alpha_stderr=float(se),
        xmin=float(xmin),
        ks_distance=_ks_distance(tail, alpha, xmin, discrete),
        n_tail=int(tail.size),
        n_total=int(data.size),
        discrete=discrete,
    )


def fit_power_law(
    x: ArrayLike,
    *,
    discrete: bool | None = None,
    xmin: float | None = None,
    min_tail: int = 50,
    max_candidates: int = 200,
) -> PowerLawFit:
    """Fit a power-law tail by maximum likelihood.

    Args:
        x: Observations (non-positive values are dropped).
        discrete: Treat data as integers; inferred when ``None``.
        xmin: Fixed lower cut-off; when ``None`` it is chosen by minimising
            the KS distance over candidate values (CSN §3.3).
        min_tail: Minimum tail size considered during the x_min scan.
        max_candidates: Cap on the number of candidate x_min values scanned
            (quantile-subsampled for large data).
    """
    data = _clean(x)
    if data.size < 10:
        raise InvalidParameterError("need at least 10 positive observations")
    if discrete is None:
        discrete = bool(np.all(np.mod(data, 1) == 0))
    if xmin is not None:
        return _fit_fixed(data, float(xmin), discrete)

    candidates = np.unique(data)
    # Only xmin values that leave at least `min_tail` observations.
    sorted_data = np.sort(data)
    limit = sorted_data[max(0, data.size - min(min_tail, data.size // 2))]
    candidates = candidates[candidates <= limit]
    if candidates.size == 0:
        candidates = np.array([sorted_data[0]])
    if candidates.size > max_candidates:
        idx = np.unique(np.linspace(0, candidates.size - 1, max_candidates).astype(int))
        candidates = candidates[idx]

    best: PowerLawFit | None = None
    for c in candidates:
        try:
            fit = _fit_fixed(data, float(c), discrete)
        except InvalidParameterError:
            continue
        if best is None or fit.ks_distance < best.ks_distance:
            best = fit
    if best is None:  # pragma: no cover - guarded by the candidate filter
        raise InvalidParameterError("could not fit a power law to the data")
    return best


# --------------------------------------------------------------------------- #
# Sampling & goodness of fit
# --------------------------------------------------------------------------- #
def sample_power_law(
    rng: np.random.Generator,
    size: int,
    alpha: float,
    xmin: float,
    discrete: bool = False,
) -> NDArray[np.float64]:
    """Draw from a continuous or discrete power law with exponent ``alpha``."""
    if alpha <= 1 or xmin <= 0:
        raise InvalidParameterError("need alpha > 1 and xmin > 0")
    u = rng.random(size)
    if not discrete:
        return xmin * (1.0 - u) ** (-1.0 / (alpha - 1.0))
    # Discrete: invert the CCDF by doubling + bisection on the Hurwitz zeta.
    norm = special.zeta(alpha, xmin)
    target = (1.0 - u) * norm  # find smallest k with zeta(alpha, k+1) < target
    lo = np.full(size, float(xmin))
    hi = np.full(size, float(xmin))
    while True:
        grow = special.zeta(alpha, hi + 1) >= target
        if not grow.any():
            break
        hi = np.where(grow, hi * 2 + 1, hi)
    while np.any(hi - lo > 0):
        mid = np.floor((lo + hi) / 2)
        go_right = special.zeta(alpha, mid + 1) >= target
        lo = np.where(go_right, mid + 1, lo)
        hi = np.where(go_right, hi, mid)
    return lo


def power_law_gof(
    x: ArrayLike,
    fit: PowerLawFit | None = None,
    *,
    n_bootstrap: int = 200,
    seed: SeedLike = None,
) -> TestResult:
    """Semi-parametric bootstrap goodness-of-fit p-value (CSN §4.1).

    Each synthetic dataset keeps the empirical body (x < x_min) and draws the
    tail from the fitted power law; the full fitting procedure (including x_min
    selection) is re-run and the p-value is the fraction of synthetic KS
    distances that exceed the observed one.
    """
    data = _clean(x)
    fit = fit or fit_power_law(data)
    rng = make_rng(seed)
    body = data[data < fit.xmin]
    n = data.size
    p_tail = fit.n_tail / n
    exceed = 0
    for _ in range(n_bootstrap):
        n_tail = rng.binomial(n, p_tail)
        synth_tail = sample_power_law(rng, n_tail, fit.alpha, fit.xmin, fit.discrete)
        synth_body = (
            rng.choice(body, n - n_tail, replace=True) if body.size else np.array([])
        )
        synth = np.concatenate([synth_body, synth_tail])
        try:
            d = fit_power_law(synth, discrete=fit.discrete).ks_distance
        except InvalidParameterError:
            continue
        exceed += d >= fit.ks_distance
    p = exceed / n_bootstrap
    return TestResult(
        "power_law_gof",
        fit.ks_distance,
        float(p),
        None,
        {
            "n_bootstrap": n_bootstrap,
            "plausible": p > 0.1,
            "alpha": fit.alpha,
            "xmin": fit.xmin,
        },
    )


# --------------------------------------------------------------------------- #
# Model comparison
# --------------------------------------------------------------------------- #
def _loglik_power_law(
    tail: NDArray[np.float64], fit: PowerLawFit
) -> NDArray[np.float64]:
    if fit.discrete:
        return -fit.alpha * np.log(tail) - np.log(special.zeta(fit.alpha, fit.xmin))
    return np.log((fit.alpha - 1) / fit.xmin) - fit.alpha * np.log(tail / fit.xmin)


def _loglik_exponential(
    tail: NDArray[np.float64], xmin: float, discrete: bool
) -> NDArray[np.float64]:
    excess = tail - xmin
    if discrete:
        # Geometric on {xmin, xmin+1, ...}: P(k) = (1-q) q^(k-xmin), MLE q = m/(1+m)
        m = float(np.mean(excess))
        q = m / (1.0 + m) if m > 0 else 1e-12
        return np.log1p(-q) + excess * np.log(q) if q > 0 else np.zeros_like(tail)
    lam = 1.0 / np.mean(excess) if np.mean(excess) > 0 else 1e6
    return np.log(lam) - lam * excess


def _loglik_lognormal(
    tail: NDArray[np.float64], xmin: float, discrete: bool
) -> NDArray[np.float64]:
    logs = np.log(tail)

    def ll(theta: NDArray[np.float64]) -> NDArray[np.float64]:
        mu, sigma = theta[0], np.exp(theta[1])
        if discrete:
            # Discretised lognormal: P(k) ∝ F(k + 1/2) - F(k - 1/2), k >= xmin.
            z_hi = (np.log(tail + 0.5) - mu) / sigma
            z_lo = (np.log(tail - 0.5) - mu) / sigma
            # Use whichever tail of the normal CDF avoids cancellation.
            mass = np.where(
                z_lo > 0,
                stats.norm.sf(z_lo) - stats.norm.sf(z_hi),
                stats.norm.cdf(z_hi) - stats.norm.cdf(z_lo),
            )
            log_mass = np.log(np.clip(mass, 1e-300, None))
            norm = stats.norm.logsf((np.log(xmin - 0.5) - mu) / sigma)
            return log_mass - norm
        norm = stats.norm.logsf((np.log(xmin) - mu) / sigma)
        return stats.norm.logpdf(logs, mu, sigma) - logs - norm

    def objective(theta: NDArray[np.float64]) -> float:
        with np.errstate(all="ignore"):
            value = -float(np.sum(ll(theta)))
        # The truncation normaliser underflows far from the optimum.
        return value if np.isfinite(value) else 1e300

    # Bounds keep the search away from the degenerate μ → -∞, σ → ∞ limit in
    # which a lognormal mimics a power law (the likelihood plateaus there).
    lo_mu, hi_mu = float(np.log(xmin)) - 30.0, float(logs.max()) + 5.0
    bounds = [(lo_mu, hi_mu), (np.log(1e-3), np.log(20.0))]
    x0 = np.array([logs.mean(), np.log(min(max(logs.std(), 1e-3), 19.0))])
    res = optimize.minimize(
        objective, x0, method="Nelder-Mead", bounds=bounds, options={"maxiter": 4000}
    )
    with np.errstate(all="ignore"):
        return ll(res.x)


def compare_distributions(
    x: ArrayLike,
    fit: PowerLawFit | None = None,
    alternative: Literal["lognormal", "exponential"] = "lognormal",
) -> TestResult:
    """Vuong's normalised log-likelihood ratio test, power law vs ``alternative``.

    ``statistic`` is the normalised ratio R/(σ√n): positive favours the power
    law, negative the alternative. ``p_value`` is the two-sided probability
    of observing |R| this large if both models were equally good; a small p
    means the sign of R is trustworthy.
    """
    data = _clean(x)
    fit = fit or fit_power_law(data)
    tail = data[data >= fit.xmin]
    lp = _loglik_power_law(tail, fit)
    if alternative == "lognormal":
        la = _loglik_lognormal(tail, fit.xmin, fit.discrete)
    elif alternative == "exponential":
        la = _loglik_exponential(tail, fit.xmin, fit.discrete)
    else:
        raise InvalidParameterError(f"unknown alternative {alternative!r}")
    diff = lp - la
    n = diff.size
    R = float(diff.sum())
    sigma = float(diff.std(ddof=0))
    z = R / (sigma * np.sqrt(n)) if sigma > 0 else 0.0
    p = float(2 * stats.norm.sf(abs(z)))
    favoured = "power_law" if R > 0 else alternative
    return TestResult(
        f"vuong_power_law_vs_{alternative}",
        float(z),
        p,
        None,
        {
            "log_likelihood_ratio": R,
            "favoured": favoured if p < 0.1 else "inconclusive",
            "n_tail": n,
        },
    )


# --------------------------------------------------------------------------- #
# Simple descriptors
# --------------------------------------------------------------------------- #
def hill_estimator(x: ArrayLike, k: int) -> float:
    """Hill estimator of the tail index using the ``k`` largest order statistics.

    Returns the pdf exponent α (= 1 + tail index ξ⁻¹).
    """
    data = np.sort(_clean(x))[::-1]
    if not 1 <= k < data.size:
        raise InvalidParameterError(f"k must be in [1, {data.size - 1}]")
    gamma = np.mean(np.log(data[:k])) - np.log(data[k])
    return float(1.0 + 1.0 / gamma)


def gini(x: ArrayLike) -> float:
    """Gini coefficient of a non-negative sample (0 = equality, → 1 = concentration)."""
    arr = np.sort(np.asarray(x, dtype=float).ravel())
    if arr.size == 0 or np.any(arr < 0):
        raise InvalidParameterError("gini needs a non-empty, non-negative sample")
    total = arr.sum()
    if total == 0:
        return 0.0
    n = arr.size
    return float((2 * np.sum(np.arange(1, n + 1) * arr) / (n * total)) - (n + 1) / n)
