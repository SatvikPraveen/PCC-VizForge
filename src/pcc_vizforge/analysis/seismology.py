"""Statistical seismology: frequency-magnitude and aftershock-decay estimators.

References
----------
Aki, K. (1965). Maximum likelihood estimate of b in the formula
    log N = a - bM and its confidence limits. *Bull. Earthq. Res. Inst.* 43.
Utsu, T. (1966). A statistical significance test of the difference in
    b-value between two earthquake groups. *J. Phys. Earth* 14, 37-40.
Page, R. (1968). Aftershocks and microaftershocks of the great Alaska
    earthquake of 1964. *BSSA* 58(3), 1131-1168.  (truncated G-R MLE)
Shi, Y. & Bolt, B. A. (1982). The standard error of the magnitude-frequency
    b value. *BSSA* 72(5), 1677-1687.
Wiemer, S. & Wyss, M. (2000). Minimum magnitude of completeness in
    earthquake catalogs. *BSSA* 90(4), 859-869.
Utsu, T., Ogata, Y. & Matsu'ura, R. S. (1995). The centenary of the Omori
    formula for a decay law of aftershock activity. *J. Phys. Earth* 43, 1-33.
Ogata, Y. (1988). Statistical models for earthquake occurrences and
    residual analysis for point processes. *JASA* 83(401), 9-27.
Hanks, T. C. & Kanamori, H. (1979). A moment magnitude scale.
    *J. Geophys. Res.* 84(B5), 2348-2350.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import optimize, stats

from pcc_vizforge.exceptions import InvalidParameterError

__all__ = [
    "EARTH_RADIUS_KM",
    "BValueEstimate",
    "OmoriFit",
    "b_value_mle",
    "b_value_mle_truncated",
    "fit_omori",
    "frequency_magnitude_distribution",
    "haversine_km",
    "interevent_cv",
    "magnitude_of_completeness",
    "omori_expected_density",
    "omori_sample_delays",
    "seismic_energy_joules",
    "seismic_moment_nm",
    "truncated_gr_sample",
]

EARTH_RADIUS_KM = 6371.0088
LOG10_E = float(np.log10(np.e))


# --------------------------------------------------------------------------- #
# Physical relations
# --------------------------------------------------------------------------- #
def seismic_energy_joules(magnitude: ArrayLike) -> NDArray[np.float64]:
    """Radiated energy from the Gutenberg-Richter relation log10 E = 1.5 M + 4.8."""
    return np.power(10.0, 1.5 * np.asarray(magnitude, dtype=float) + 4.8)


def seismic_moment_nm(magnitude: ArrayLike) -> NDArray[np.float64]:
    """Scalar seismic moment M0 [N·m] from moment magnitude (Hanks & Kanamori)."""
    return np.power(10.0, 1.5 * np.asarray(magnitude, dtype=float) + 9.1)


def haversine_km(
    lat1: ArrayLike, lon1: ArrayLike, lat2: ArrayLike, lon2: ArrayLike
) -> NDArray[np.float64]:
    """Great-circle distance in kilometres."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


# --------------------------------------------------------------------------- #
# Samplers
# --------------------------------------------------------------------------- #
def truncated_gr_sample(
    rng: np.random.Generator,
    size: int,
    b_value: float,
    m_min: float,
    m_max: float = np.inf,
) -> NDArray[np.float64]:
    """Draw magnitudes from the (doubly) truncated Gutenberg-Richter law.

    The density is :math:`f(m) \\propto 10^{-b m}` on ``[m_min, m_max]``,
    i.e. an exponential with rate :math:`\\beta = b \\ln 10`.
    """
    if b_value <= 0 or m_max <= m_min:
        raise InvalidParameterError("need b_value > 0 and m_max > m_min")
    beta = b_value * np.log(10.0)
    u = rng.random(size)
    tail = 0.0 if np.isinf(m_max) else np.exp(-beta * (m_max - m_min))
    return m_min - np.log1p(-u * (1.0 - tail)) / beta


def omori_sample_delays(
    rng: np.random.Generator, size: int, c: float, p: float, t_max: float
) -> NDArray[np.float64]:
    """Draw delays from the Omori-Utsu density ∝ (t + c)^(-p) on [0, t_max]."""
    if c <= 0 or p <= 0 or t_max <= 0:
        raise InvalidParameterError("need c > 0, p > 0 and t_max > 0")
    u = rng.random(size)
    if abs(p - 1.0) < 1e-12:
        return c * np.power((t_max + c) / c, u) - c
    q = 1.0 - p
    lo, hi = c**q, (t_max + c) ** q
    return np.power(lo + u * (hi - lo), 1.0 / q) - c


# --------------------------------------------------------------------------- #
# Frequency-magnitude distribution
# --------------------------------------------------------------------------- #
def frequency_magnitude_distribution(
    magnitudes: ArrayLike, bin_width: float = 0.1
) -> tuple[NDArray[np.float64], NDArray[np.int64], NDArray[np.int64]]:
    """Binned FMD.

    Returns:
        ``(bin_centres, incremental_counts, cumulative_counts)`` where the
        cumulative count is N(M >= bin centre - bin_width/2).
    """
    m = np.asarray(magnitudes, dtype=float)
    if m.size == 0:
        raise InvalidParameterError("no magnitudes")
    idx = np.round(m / bin_width).astype(np.int64)
    lo, hi = idx.min(), idx.max()
    counts = np.bincount(idx - lo, minlength=hi - lo + 1)
    centres = (np.arange(lo, hi + 1) * bin_width).astype(np.float64)
    counts = counts.astype(np.int64)
    cumulative = np.cumsum(counts[::-1])[::-1].astype(np.int64)
    return centres, counts, cumulative


def magnitude_of_completeness(
    magnitudes: ArrayLike, bin_width: float = 0.1, correction: float = 0.2
) -> float:
    """Magnitude of completeness by the maximum-curvature method.

    Mc is the magnitude bin with the highest incremental count, plus an
    empirical ``correction`` (+0.2 by default, Woessner & Wiemer 2005) that
    compensates for the method's known underestimation.
    """
    centres, counts, _ = frequency_magnitude_distribution(magnitudes, bin_width)
    return float(centres[int(np.argmax(counts))] + correction)


@dataclass(frozen=True)
class BValueEstimate:
    """Maximum-likelihood b-value estimate."""

    b_value: float
    a_value: float
    std_error: float
    ci: tuple[float, float]
    n_events: int
    mc: float
    method: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def b_value_mle(
    magnitudes: ArrayLike,
    mc: float,
    *,
    bin_width: float = 0.0,
    confidence: float = 0.95,
    unbiased: bool = False,
) -> BValueEstimate:
    """Aki-Utsu maximum-likelihood b-value for events with M >= ``mc``.

    .. math:: \\hat b = \\frac{\\log_{10} e}{\\bar M - (M_c - \\Delta M/2)}

    The standard error is that of Shi & Bolt (1982). For continuous
    magnitudes use ``bin_width=0``.

    The MLE is biased upward by the factor n/(n-1) (the reciprocal of a
    Gamma-distributed mean); ``unbiased=True`` multiplies by (n-1)/n, which
    matters for small catalogues (≈ 2 % at n = 50).
    """
    m = np.asarray(magnitudes, dtype=float)
    m = m[m >= mc - 1e-9]
    n = m.size
    if n < 2:
        raise InvalidParameterError(f"need at least 2 events above Mc={mc}, got {n}")
    mean = m.mean()
    denom = mean - (mc - bin_width / 2.0)
    if denom <= 0:
        raise InvalidParameterError("mean magnitude must exceed Mc - bin_width/2")
    b = LOG10_E / denom
    if unbiased:
        b *= (n - 1) / n
    se = 2.30 * b**2 * np.sqrt(np.sum((m - mean) ** 2) / (n * (n - 1)))
    z = stats.norm.ppf(0.5 + confidence / 2)
    a = np.log10(n) + b * mc
    return BValueEstimate(
        float(b),
        float(a),
        float(se),
        (float(b - z * se), float(b + z * se)),
        int(n),
        float(mc),
        "aki-utsu-unbiased" if unbiased else "aki-utsu",
    )


def b_value_mle_truncated(
    magnitudes: ArrayLike,
    mc: float,
    m_max: float,
    *,
    confidence: float = 0.95,
) -> BValueEstimate:
    """MLE of b for the doubly-truncated G-R law on ``[mc, m_max]`` (Page 1968).

    Solves the score equation numerically; the standard error comes from the
    observed Fisher information. Unlike the Aki estimator this is unbiased
    when a finite maximum magnitude is present in the data-generating process.
    """
    m = np.asarray(magnitudes, dtype=float)
    m = m[(m >= mc - 1e-9) & (m <= m_max + 1e-9)]
    n = m.size
    if n < 2:
        raise InvalidParameterError("need at least 2 events in [mc, m_max]")
    x = m - mc
    xbar = x.mean()
    L = m_max - mc

    def tail_term(beta: float) -> float:
        # L e^{-βL} / (1 - e^{-βL}), written to avoid overflow for large βL
        return float(L * np.exp(-beta * L) / -np.expm1(-beta * L))

    def score(beta: float) -> float:
        # d/dβ log-lik / n = 1/β - x̄ - L e^{-βL}/(1 - e^{-βL})
        return 1.0 / beta - xbar - tail_term(beta)

    lo, hi = 1e-6, 1e3
    if score(hi) > 0:  # pragma: no cover - degenerate: all magnitudes at Mc
        raise InvalidParameterError("b-value diverges (all events at Mc)")
    beta = optimize.brentq(score, lo, hi)
    # Observed information per event: 1/β² - L² e^{-βL} / (1 - e^{-βL})²
    q = np.exp(-beta * L)
    info = n * (1.0 / beta**2 - L**2 * q / (1.0 - q) ** 2)
    se_beta = 1.0 / np.sqrt(info)
    b = beta / np.log(10.0)
    se = se_beta / np.log(10.0)
    z = stats.norm.ppf(0.5 + confidence / 2)
    a = np.log10(n) + b * mc
    return BValueEstimate(
        float(b),
        float(a),
        float(se),
        (float(b - z * se), float(b + z * se)),
        int(n),
        float(mc),
        "page-truncated",
    )


# --------------------------------------------------------------------------- #
# Temporal clustering
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class OmoriFit:
    """MLE of the Omori-Utsu law n(t) = K / (t + c)^p on [0, T]."""

    K: float
    c: float
    p: float
    p_stderr: float
    n_events: int
    t_max: float
    log_likelihood: float

    def rate(self, t: ArrayLike) -> NDArray[np.float64]:
        return self.K / np.power(np.asarray(t, dtype=float) + self.c, self.p)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _omori_integral(c: float, p: float, T: float | NDArray[np.float64]) -> Any:
    """∫_0^T (t + c)^(-p) dt (vectorised over ``T``)."""
    T_arr = np.asarray(T, dtype=float)
    if abs(p - 1.0) < 1e-10:
        out = np.log((T_arr + c) / c)
    else:
        out = ((T_arr + c) ** (1 - p) - c ** (1 - p)) / (1 - p)
    return float(out) if out.ndim == 0 else out


def omori_expected_density(
    t: ArrayLike, fit: OmoriFit, windows: ArrayLike | None = None
) -> NDArray[np.float64]:
    """Expected density of observed delays under a fitted Omori-Utsu law.

    With per-event observation ``windows`` T_i (see :func:`fit_omori`) this is
    Σ_i (t + c)^(-p) 1[t < T_i] / ∫_0^{T_i}(u + c)^(-p) du, which accounts for
    the censoring of long delays near the end of a catalogue.
    """
    tt = np.asarray(t, dtype=float)
    base = np.power(tt + fit.c, -fit.p)
    if windows is None:
        return fit.K * base
    w = np.sort(np.asarray(windows, dtype=float))
    inv_norm = 1.0 / _omori_integral(fit.c, fit.p, w)
    # suffix sums: Σ_{i: T_i > t} 1/I_i
    suffix = np.concatenate([np.cumsum(inv_norm[::-1])[::-1], [0.0]])
    return base * suffix[np.searchsorted(w, tt, side="right")]


def fit_omori(times: ArrayLike, t_max: float | ArrayLike | None = None) -> OmoriFit:
    """Maximum-likelihood fit of the Omori-Utsu law to aftershock delays.

    Args:
        times: Delays since the triggering event (> 0), any unit.
        t_max: Observation window. Either a scalar common to all events
            (default ``max(times)``) or an array with one window per delay,
            e.g. ``catalogue_end - parent_time`` when delays from many
            parents are pooled. Ignoring per-event windows censors long
            delays unevenly and biases ``p`` upward.

    The conditional likelihood normalises each delay's density
    ∝ (t + c)^(-p) over its own window. ``K`` is reported for the largest
    window; use :func:`omori_expected_density` to overlay pooled data.
    """
    t_all = np.asarray(times, dtype=float).ravel()
    if t_max is None:
        windows = np.full(t_all.shape, float(t_all.max()) if t_all.size else 0.0)
    else:
        windows = np.broadcast_to(np.asarray(t_max, dtype=float), t_all.shape).astype(
            float
        )
    keep = t_all > 0
    t, windows = t_all[keep], windows[keep]
    n = t.size
    if n < 10:
        raise InvalidParameterError("need at least 10 aftershocks to fit Omori's law")
    if np.any(windows < t):
        raise InvalidParameterError("each observation window must be >= its delay")
    T = float(windows.max())

    def nll(theta: NDArray[np.float64]) -> float:
        c, p = np.exp(theta[0]), np.exp(theta[1])
        # Conditional log-likelihood of the delays given n (K profiles out).
        return float(
            p * np.sum(np.log(t + c)) + np.sum(np.log(_omori_integral(c, p, windows)))
        )

    x0 = np.log([max(1e-3, 0.01 * T), 1.1])
    res = optimize.minimize(
        nll,
        x0,
        method="Nelder-Mead",
        options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000},
    )
    c, p = (float(v) for v in np.exp(res.x))
    K = n / _omori_integral(c, p, T)
    # Numerical Hessian in (log c, log p) for the stderr of p.
    h = 1e-4
    H = np.empty((2, 2))
    for i in range(2):
        for j in range(2):
            ei, ej = np.eye(2)[i] * h, np.eye(2)[j] * h
            H[i, j] = (
                nll(res.x + ei + ej)
                - nll(res.x + ei - ej)
                - nll(res.x - ei + ej)
                + nll(res.x - ei - ej)
            ) / (4 * h * h)
    try:
        cov = np.linalg.inv(H)
        p_se = float(p * np.sqrt(max(cov[1, 1], 0.0)))
    except np.linalg.LinAlgError:  # pragma: no cover
        p_se = float("nan")
    return OmoriFit(float(K), c, p, p_se, int(n), T, float(-res.fun))


def interevent_cv(times: ArrayLike) -> float:
    """Coefficient of variation of inter-event times.

    CV = 1 for a homogeneous Poisson process; CV > 1 indicates temporal
    clustering (e.g. aftershock sequences), CV < 1 quasi-periodicity.
    """
    t = np.sort(np.asarray(times, dtype=float))
    if t.size < 3:
        raise InvalidParameterError("need at least 3 events")
    dt = np.diff(t)
    return float(dt.std(ddof=1) / dt.mean())
