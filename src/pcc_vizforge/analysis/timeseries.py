"""Climate/time-series analysis: seasonality, trends and wet/dry spells.

References
----------
Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica* 13.
Kendall, M. G. (1975). *Rank Correlation Methods*, 4th ed. Griffin.
Sen, P. K. (1968). Estimates of the regression coefficient based on
    Kendall's tau. *JASA* 63(324), 1379-1389.
Gilbert, R. O. (1987). *Statistical Methods for Environmental Pollution
    Monitoring*. Wiley.  (confidence interval for Sen's slope)
von Storch, H. (1995). Misuses of statistical analysis in climate research.
    In *Analysis of Climate Variability*, Springer, 11-26.  (pre-whitening)
Hamed, K. H. & Rao, A. R. (1998). A modified Mann-Kendall trend test for
    autocorrelated data. *J. Hydrol.* 204, 182-196.
Bayazit, M. & Önöz, B. (2007). To prewhiten or not to prewhiten in trend
    analysis? *Hydrol. Sci. J.* 52(4), 611-624.
Richardson, C. W. (1981). Stochastic simulation of daily precipitation,
    temperature, and solar radiation. *Water Resour. Res.* 17(1), 182-190.
Alduchov, O. A. & Eskridge, R. E. (1996). Improved Magnus form
    approximation of saturation vapor pressure. *J. Appl. Meteor.* 35.
Newey, W. K. & West, K. D. (1987). A simple, positive semi-definite,
    heteroskedasticity and autocorrelation consistent covariance matrix.
    *Econometrica* 55(3), 703-708.
Andrews, D. W. K. (1991). Heteroskedasticity and autocorrelation consistent
    covariance matrix estimation. *Econometrica* 59(3), 817-858.
Rothfusz, L. P. (1990). The heat index equation. NWS Technical Attachment
    SR 90-23.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import stats

from pcc_vizforge.analysis.inference import TestResult, autocorrelation
from pcc_vizforge.exceptions import InvalidParameterError

__all__ = [
    "HarmonicFit",
    "MarkovChainFit",
    "andrews_bandwidth",
    "fit_harmonics",
    "fit_markov_chain",
    "heat_index_c",
    "mann_kendall",
    "newey_west_cov",
    "relative_humidity",
    "saturation_vapor_pressure",
    "sens_slope",
    "spell_lengths",
]


# --------------------------------------------------------------------------- #
# Thermodynamics
# --------------------------------------------------------------------------- #
def saturation_vapor_pressure(temp_c: ArrayLike) -> NDArray[np.float64]:
    """Saturation vapour pressure over water [hPa] (Magnus-Alduchov-Eskridge)."""
    t = np.asarray(temp_c, dtype=float)
    return 6.1094 * np.exp(17.625 * t / (t + 243.04))


def relative_humidity(temp_c: ArrayLike, dewpoint_c: ArrayLike) -> NDArray[np.float64]:
    """Relative humidity [%] from air and dew-point temperature."""
    rh = (
        100.0
        * saturation_vapor_pressure(dewpoint_c)
        / saturation_vapor_pressure(temp_c)
    )
    return np.clip(rh, 0.0, 100.0)


def heat_index_c(temp_c: ArrayLike, rh: ArrayLike) -> NDArray[np.float64]:
    """NWS heat index [°C] (Rothfusz regression with Steadman fallback).

    Follows the NWS algorithm: the simple Steadman formula is used first and
    the full Rothfusz regression (with its low-/high-humidity adjustments)
    only when the simple estimate is at least 80 °F.
    """
    T = np.asarray(temp_c, dtype=float) * 9 / 5 + 32
    R = np.asarray(rh, dtype=float)
    simple = 0.5 * (T + 61.0 + (T - 68.0) * 1.2 + R * 0.094)
    full = (
        -42.379
        + 2.04901523 * T
        + 10.14333127 * R
        - 0.22475541 * T * R
        - 6.83783e-3 * T**2
        - 5.481717e-2 * R**2
        + 1.22874e-3 * T**2 * R
        + 8.5282e-4 * T * R**2
        - 1.99e-6 * T**2 * R**2
    )
    low_rh = (R < 13) & (T >= 80) & (T <= 112)
    adj_low = ((13 - R) / 4) * np.sqrt(np.clip((17 - np.abs(T - 95.0)) / 17, 0, None))
    high_rh = (R > 85) & (T >= 80) & (T <= 87)
    adj_high = ((R - 85) / 10) * ((87 - T) / 5)
    full = full - np.where(low_rh, adj_low, 0.0) + np.where(high_rh, adj_high, 0.0)
    hi_f = np.where((simple + T) / 2 >= 80, full, simple)
    # Heat index is not defined below the air temperature for cool conditions.
    hi_f = np.where(T < 50, T, hi_f)
    return (hi_f - 32) * 5 / 9


# --------------------------------------------------------------------------- #
# Seasonality
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class HarmonicFit:
    """OLS fit of y = μ + β t + Σ_k [a_k cos(2πkt/P) + b_k sin(2πkt/P)]."""

    mean: float
    trend_per_unit: float
    trend_stderr: float
    trend_stderr_hac: float
    hac_lags: int
    amplitudes: tuple[float, ...]
    phases: tuple[float, ...]
    period: float
    r_squared: float
    residual_std: float
    coefficients: tuple[float, ...]

    def predict(self, t: ArrayLike) -> NDArray[np.float64]:
        X = _harmonic_design(
            np.asarray(t, dtype=float), self.period, len(self.amplitudes), True
        )
        return X @ np.asarray(self.coefficients)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _harmonic_design(
    t: NDArray[np.float64], period: float, n_harmonics: int, trend: bool
) -> NDArray[np.float64]:
    cols = [np.ones_like(t)]
    if trend:
        cols.append(t)
    for k in range(1, n_harmonics + 1):
        w = 2 * np.pi * k * t / period
        cols.extend([np.cos(w), np.sin(w)])
    return np.column_stack(cols)


def newey_west_cov(
    X: NDArray[np.float64], resid: NDArray[np.float64], lags: int
) -> NDArray[np.float64]:
    """Heteroskedasticity- and autocorrelation-consistent (HAC) covariance.

    Newey & West (1987) sandwich estimator with Bartlett weights
    :math:`w_\\ell = 1 - \\ell/(L+1)`.
    """
    n = X.shape[0]
    u = X * resid[:, None]
    S = u.T @ u
    for lag in range(1, lags + 1):
        w = 1.0 - lag / (lags + 1.0)
        G = u[lag:].T @ u[:-lag]
        S += w * (G + G.T)
    bread = np.linalg.inv(X.T @ X)
    return bread @ S @ bread * n / (n - X.shape[1])


def andrews_bandwidth(resid: ArrayLike) -> int:
    """Andrews (1991) AR(1) plug-in bandwidth for the Bartlett kernel.

    :math:`L = \\lfloor 1.1447\\,(\\hat\\alpha\\, n)^{1/3} \\rfloor` with
    :math:`\\hat\\alpha = 4\\hat\\rho^2 / (1 - \\hat\\rho^2)^2`.
    """
    e = np.asarray(resid, dtype=float)
    n = e.size
    denom = float(np.sum(e[:-1] ** 2))
    rho = float(np.sum(e[1:] * e[:-1]) / denom) if denom > 0 else 0.0
    rho = float(np.clip(rho, -0.97, 0.97))
    alpha = 4 * rho**2 / (1 - rho**2) ** 2
    return int(min(max(np.floor(1.1447 * (alpha * n) ** (1 / 3)), 0), n - 2))


def fit_harmonics(
    t: ArrayLike,
    y: ArrayLike,
    *,
    period: float = 365.25,
    n_harmonics: int = 2,
    hac_lags: int | None = None,
) -> HarmonicFit:
    """Least-squares harmonic regression with a linear trend.

    ``amplitudes[k]`` and ``phases[k]`` (radians) describe
    :math:`A_k \\cos(2\\pi k t / P - \\phi_k)`.

    Two trend standard errors are reported: the classical OLS one
    (``trend_stderr``, valid only for independent residuals) and the
    Newey-West HAC one (``trend_stderr_hac``) with ``hac_lags`` lags --
    by default Andrews' (1991) AR(1) plug-in bandwidth -- which should be
    used whenever residuals are serially correlated (e.g. daily weather).
    """
    tt = np.asarray(t, dtype=float)
    yy = np.asarray(y, dtype=float)
    if tt.shape != yy.shape or tt.ndim != 1:
        raise InvalidParameterError("t and y must be 1-D arrays of equal length")
    X = _harmonic_design(tt, period, n_harmonics, trend=True)
    if yy.size <= X.shape[1]:
        raise InvalidParameterError(
            "not enough observations for the requested harmonics"
        )
    coef, *_ = np.linalg.lstsq(X, yy, rcond=None)
    resid = yy - X @ coef
    dof = yy.size - X.shape[1]
    s2 = float(resid @ resid / dof)
    cov = s2 * np.linalg.inv(X.T @ X)
    amps, phases = [], []
    for k in range(n_harmonics):
        a, b = coef[2 + 2 * k], coef[3 + 2 * k]
        amps.append(float(np.hypot(a, b)))
        phases.append(float(np.arctan2(b, a)))
    ss_tot = float(np.sum((yy - yy.mean()) ** 2))
    L = andrews_bandwidth(resid) if hac_lags is None else int(hac_lags)
    cov_hac = newey_west_cov(X, resid, L)
    return HarmonicFit(
        mean=float(coef[0]),
        trend_per_unit=float(coef[1]),
        trend_stderr=float(np.sqrt(cov[1, 1])),
        trend_stderr_hac=float(np.sqrt(cov_hac[1, 1])),
        hac_lags=L,
        amplitudes=tuple(amps),
        phases=tuple(phases),
        period=period,
        r_squared=1 - float(resid @ resid) / ss_tot if ss_tot > 0 else 1.0,
        residual_std=float(np.sqrt(s2)),
        coefficients=tuple(float(c) for c in coef),
    )


# --------------------------------------------------------------------------- #
# Trend tests
# --------------------------------------------------------------------------- #
def sens_slope(
    y: ArrayLike, t: ArrayLike | None = None, confidence: float = 0.95
) -> tuple[float, float, float, float]:
    """Theil-Sen slope with Gilbert's (1987) confidence interval.

    Returns:
        ``(slope, intercept, low, high)``.
    """
    yy = np.asarray(y, dtype=float)
    tt = np.arange(yy.size, dtype=float) if t is None else np.asarray(t, dtype=float)
    res = stats.theilslopes(yy, tt, alpha=confidence)
    return (
        float(res.slope),
        float(res.intercept),
        float(res.low_slope),
        float(res.high_slope),
    )


def _mk_statistic(y: NDArray[np.float64]) -> tuple[float, float]:
    """Mann-Kendall S and its tie-corrected variance (O(n²) time, O(n) memory)."""
    n = y.size
    s = 0.0
    for i in range(n - 1):
        s += float(np.sign(y[i + 1 :] - y[i]).sum())
    _, counts = np.unique(y, return_counts=True)
    ties = counts[counts > 1]
    var = (
        n * (n - 1) * (2 * n + 5) - np.sum(ties * (ties - 1) * (2 * ties + 5))
    ) / 18.0
    return s, float(var)


def mann_kendall(
    y: ArrayLike,
    *,
    correction: Literal["none", "prewhiten", "hamed_rao"] = "none",
    alpha_acf: float = 0.05,
) -> TestResult:
    """Mann-Kendall test for a monotonic trend (two-sided, tie-corrected).

    Positive serial correlation inflates the type-I error of the plain test.
    Two standard corrections are available:

    ``"prewhiten"``
        von Storch (1995) pre-whitening: test
        :math:`y_t - \\hat r_1 y_{t-1}`. Conservative, loses some power.
    ``"hamed_rao"``
        Hamed & Rao (1998) variance correction: Var(S) is inflated by
        :math:`n/n^* = 1 + \\frac{2}{n(n-1)(n-2)}\\sum_k (n-k)(n-k-1)(n-k-2)\\rho_k`
        where :math:`\\rho_k` are the significant autocorrelations of the
        ranks of the Sen-detrended series.

    Both reduce, but do not eliminate, size distortion under strong
    autocorrelation; Hamed-Rao remains liberal for short series. Trend-free
    pre-whitening is deliberately not offered as it is over-liberal
    (Bayazit & Önöz 2007). For daily climate data, testing annual means is
    usually preferable.
    """
    yy = np.asarray(y, dtype=float)
    if yy.size < 4 or not np.all(np.isfinite(yy)):
        raise InvalidParameterError("Mann-Kendall needs >= 4 finite observations")
    if yy.size > 20_000:
        raise InvalidParameterError(
            "series too long for the O(n²) Mann-Kendall statistic"
        )
    details: dict[str, Any] = {"correction": correction}
    series = yy
    if correction == "prewhiten":
        yc = yy - yy.mean()
        r1 = float(np.sum(yc[1:] * yc[:-1]) / np.sum(yc**2)) if np.any(yc) else 0.0
        details["lag1_autocorrelation"] = r1
        series = yy[1:] - r1 * yy[:-1]
    elif correction not in ("none", "hamed_rao"):
        raise InvalidParameterError(f"unknown correction {correction!r}")

    s, var = _mk_statistic(series)
    n = series.size
    if correction == "hamed_rao":
        t = np.arange(n, dtype=float)
        slope, *_ = sens_slope(series, t)
        ranks = stats.rankdata(series - slope * t)
        rho = autocorrelation(ranks, n - 1)[1:]
        bound = stats.norm.ppf(1 - alpha_acf / 2) / np.sqrt(n)
        rho = np.where(np.abs(rho) > bound, rho, 0.0)
        k = np.arange(1, n)
        ratio = 1 + 2 / (n * (n - 1) * (n - 2)) * np.sum(
            (n - k) * (n - k - 1) * (n - k - 2) * rho
        )
        inflation = max(float(ratio), 1e-12)
        details["variance_inflation"] = inflation
        var *= inflation

    if var <= 0:
        z = 0.0
    elif s > 0:
        z = (s - 1) / np.sqrt(var)
    elif s < 0:
        z = (s + 1) / np.sqrt(var)
    else:
        z = 0.0
    details.update({"S": s, "var_S": var, "tau": s / (0.5 * n * (n - 1)), "n": n})
    slope, _, lo, hi = sens_slope(yy)
    details.update({"sens_slope": slope, "sens_slope_ci": (lo, hi)})
    return TestResult(
        "mann_kendall", float(z), float(2 * stats.norm.sf(abs(z))), None, details
    )


# --------------------------------------------------------------------------- #
# Wet/dry Markov chain
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MarkovChainFit:
    """MLE of a two-state first-order Markov chain for daily occurrence."""

    p_wet_given_dry: float
    p_wet_given_wet: float
    stationary_wet_probability: float
    mean_wet_spell: float
    mean_dry_spell: float
    n_transitions: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fit_markov_chain(wet: ArrayLike) -> MarkovChainFit:
    """Estimate p01 = P(wet | dry) and p11 = P(wet | wet) from a wet/dry series."""
    w = np.asarray(wet, dtype=bool)
    if w.size < 2:
        raise InvalidParameterError("need at least two days")
    prev, nxt = w[:-1], w[1:]
    n_dry, n_wet = int((~prev).sum()), int(prev.sum())
    if n_dry == 0 or n_wet == 0:
        raise InvalidParameterError("series must contain both wet and dry days")
    p01 = float((nxt & ~prev).sum() / n_dry)
    p11 = float((nxt & prev).sum() / n_wet)
    denom = 1 - p11 + p01
    return MarkovChainFit(
        p_wet_given_dry=p01,
        p_wet_given_wet=p11,
        stationary_wet_probability=p01 / denom if denom > 0 else float("nan"),
        mean_wet_spell=1 / (1 - p11) if p11 < 1 else float("inf"),
        mean_dry_spell=1 / p01 if p01 > 0 else float("inf"),
        n_transitions=int(w.size - 1),
    )


def spell_lengths(flags: ArrayLike) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Lengths of consecutive ``True`` and ``False`` runs, as ``(true_runs, false_runs)``."""
    f = np.asarray(flags, dtype=bool)
    if f.size == 0:
        return np.array([], dtype=np.int64), np.array([], dtype=np.int64)
    change = np.flatnonzero(np.diff(f.astype(np.int8))) + 1
    starts = np.r_[0, change]
    lengths = np.diff(np.r_[starts, f.size])
    values = f[starts]
    return lengths[values].astype(np.int64), lengths[~values].astype(np.int64)
