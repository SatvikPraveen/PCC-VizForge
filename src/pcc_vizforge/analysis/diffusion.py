"""Estimators for diffusive and anomalous-diffusive trajectories.

Functions accept trajectories as an array of shape ``(n_walks, n_steps, d)``
(use :func:`pcc_vizforge.generators.random_walk.frame_to_positions` to
convert the tidy DataFrame) where index ``t-1`` holds the position after
``t`` steps and every walk starts from the origin.

References
----------
Metzler, R., Jeon, J.-H., Cherstvy, A. G. & Barkai, E. (2014). Anomalous
    diffusion models and their properties: non-stationarity,
    non-ergodicity, and ageing at the centenary of single particle tracking.
    *Phys. Chem. Chem. Phys.* 16, 24128-24164.
Peng, C.-K. et al. (1994). Mosaic organization of DNA nucleotides.
    *Phys. Rev. E* 49(2), 1685-1689.  (Detrended fluctuation analysis)
Redner, S. (2001). *A Guide to First-Passage Processes*. Cambridge UP.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import stats

from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.rng import SeedLike, make_rng

__all__ = [
    "PowerLawFit",
    "bootstrap_msd_exponent",
    "dfa",
    "ensemble_msd",
    "ergodicity_breaking_parameter",
    "first_passage_times",
    "fit_msd_exponent",
    "log_spaced_lags",
    "time_averaged_msd",
]


def _as_positions(positions: ArrayLike) -> NDArray[np.float64]:
    arr = np.asarray(positions, dtype=float)
    if arr.ndim == 2:  # (walks, steps) -> 1-D walks
        arr = arr[..., None]
    if arr.ndim != 3:
        raise InvalidParameterError(
            f"positions must have shape (n_walks, n_steps[, d]), got {arr.shape}"
        )
    if arr.shape[1] < 2:
        raise InvalidParameterError("need at least two steps per walk")
    return arr


def log_spaced_lags(
    n_steps: int, n_lags: int = 30, min_lag: int = 1
) -> NDArray[np.int64]:
    """Unique, approximately log-spaced integer lags in ``[min_lag, n_steps-1]``."""
    if n_steps < 2:
        raise InvalidParameterError("n_steps must be >= 2")
    hi = max(min_lag, n_steps - 1)
    return np.unique(np.geomspace(min_lag, hi, n_lags).round().astype(np.int64))


def ensemble_msd(
    positions: ArrayLike,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Ensemble-averaged MSD from the origin and its standard error.

    Returns:
        ``(msd, sem)`` each of length ``n_steps``; ``msd[t-1]`` estimates
        :math:`\\langle |r(t)|^2 \\rangle`.
    """
    pos = _as_positions(positions)
    sq = np.sum(pos**2, axis=-1)  # (walks, steps)
    msd = sq.mean(axis=0)
    sem = (
        sq.std(axis=0, ddof=1) / np.sqrt(sq.shape[0])
        if sq.shape[0] > 1
        else np.zeros_like(msd)
    )
    return msd, sem


def time_averaged_msd(
    positions: ArrayLike, lags: ArrayLike | None = None
) -> tuple[NDArray[np.int64], NDArray[np.float64]]:
    """Per-walk time-averaged MSD, :math:`\\overline{\\delta^2}(\\Delta)`.

    .. math::
        \\overline{\\delta^2}(\\Delta) = \\frac{1}{T-\\Delta}\\sum_{t=0}^{T-\\Delta}
        |r(t+\\Delta) - r(t)|^2

    with the origin prepended as r(0).

    Returns:
        ``(lags, tamsd)`` where ``tamsd`` has shape ``(n_walks, len(lags))``.
    """
    pos = _as_positions(positions)
    w, n, d = pos.shape
    full = np.concatenate([np.zeros((w, 1, d)), pos], axis=1)  # include r(0)=0
    lag_arr = (
        log_spaced_lags(n + 1) if lags is None else np.asarray(lags, dtype=np.int64)
    )
    if np.any(lag_arr < 1) or np.any(lag_arr > n):
        raise InvalidParameterError(f"lags must lie in [1, {n}]")
    out = np.empty((w, lag_arr.size))
    for j, lag in enumerate(lag_arr):
        diff = full[:, lag:] - full[:, :-lag]
        out[:, j] = np.mean(np.sum(diff**2, axis=-1), axis=1)
    return lag_arr, out


def ergodicity_breaking_parameter(tamsd: ArrayLike) -> NDArray[np.float64]:
    """EB(Δ) = Var[δ²] / ⟨δ²⟩² across walks (→ 0 for ergodic processes)."""
    arr = np.asarray(tamsd, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 2:
        raise InvalidParameterError("tamsd must have shape (n_walks >= 2, n_lags)")
    mean = arr.mean(axis=0)
    return arr.var(axis=0, ddof=1) / mean**2


@dataclass(frozen=True)
class PowerLawFit:
    """Result of fitting ``y = K * x**alpha`` in log-log space."""

    alpha: float
    alpha_stderr: float
    alpha_ci: tuple[float, float]
    prefactor: float
    r_squared: float
    n_points: int
    x_range: tuple[float, float]

    @property
    def regime(self) -> str:
        """'subdiffusive', 'normal' or 'superdiffusive' based on the 95 % CI."""
        lo, hi = self.alpha_ci
        if hi < 1.0:
            return "subdiffusive"
        if lo > 1.0:
            return "superdiffusive"
        return "normal"

    def diffusion_coefficient(self, dimensions: int) -> float:
        """Generalised diffusion coefficient K_α = K / (2d)."""
        return self.prefactor / (2.0 * dimensions)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["regime"] = self.regime
        return d


def fit_msd_exponent(
    lags: ArrayLike,
    msd: ArrayLike,
    *,
    lag_range: tuple[float, float] | None = None,
    sigma: ArrayLike | None = None,
    confidence: float = 0.95,
) -> PowerLawFit:
    """Estimate the anomalous exponent α in MSD ∝ Δ^α by log-log regression.

    .. warning::
        The reported standard error treats MSD values at different lags as
        independent. Ensemble MSDs at neighbouring lags are strongly
        correlated, so this CI is too narrow; use
        :func:`bootstrap_msd_exponent` (resampling walks) for inference.

    Args:
        lags: Lag times (> 0).
        msd: MSD values (> 0) at those lags.
        lag_range: Optional inclusive ``(min, max)`` lag window to fit.
        sigma: Optional standard errors of ``msd``; enables weighted least
            squares with weights ``(msd/sigma)^2`` (delta method in log space).
        confidence: Two-sided confidence level for ``alpha_ci``.
    """
    x = np.asarray(lags, dtype=float)
    y = np.asarray(msd, dtype=float)
    if x.shape != y.shape:
        raise InvalidParameterError("lags and msd must have the same shape")
    mask = (x > 0) & (y > 0) & np.isfinite(y)
    if lag_range is not None:
        mask &= (x >= lag_range[0]) & (x <= lag_range[1])
    w: NDArray[np.float64] | None = None
    if sigma is not None:
        s = np.asarray(sigma, dtype=float)
        mask &= s > 0
        w = (y[mask] / s[mask]) ** 2
    if mask.sum() < 3:
        raise InvalidParameterError(
            "need at least 3 positive points to fit an exponent"
        )

    lx, ly = np.log(x[mask]), np.log(y[mask])
    W = np.ones_like(lx) if w is None else w
    X = np.column_stack([np.ones_like(lx), lx])
    XtW = X.T * W
    cov_unscaled = np.linalg.inv(XtW @ X)
    beta = cov_unscaled @ (XtW @ ly)
    resid = ly - X @ beta
    n = lx.size
    dof = n - 2
    s2 = float(np.sum(W * resid**2) / dof) if dof > 0 else 0.0
    se = float(np.sqrt(s2 * cov_unscaled[1, 1]))
    tcrit = float(stats.t.ppf(0.5 + confidence / 2, dof)) if dof > 0 else float("inf")
    ss_tot = float(np.sum(W * (ly - np.average(ly, weights=W)) ** 2))
    r2 = 1.0 - float(np.sum(W * resid**2)) / ss_tot if ss_tot > 0 else 1.0
    alpha = float(beta[1])
    return PowerLawFit(
        alpha=alpha,
        alpha_stderr=se,
        alpha_ci=(alpha - tcrit * se, alpha + tcrit * se),
        prefactor=float(np.exp(beta[0])),
        r_squared=r2,
        n_points=int(n),
        x_range=(float(x[mask].min()), float(x[mask].max())),
    )


def bootstrap_msd_exponent(
    positions: ArrayLike,
    *,
    lags: ArrayLike | None = None,
    n_bootstrap: int = 500,
    confidence: float = 0.95,
    seed: SeedLike = None,
) -> PowerLawFit:
    """Anomalous exponent with a walk-level bootstrap confidence interval.

    Walks are the independent sampling unit, so resampling them with
    replacement and re-fitting the ensemble MSD yields a CI that accounts for
    the correlation between lags. The point estimate is the fit on the full
    ensemble; ``alpha_stderr`` is the bootstrap standard deviation and
    ``alpha_ci`` the percentile interval.
    """
    pos = _as_positions(positions)
    w, n, _ = pos.shape
    if w < 2:
        raise InvalidParameterError("bootstrap needs at least two walks")
    lag_arr = (
        log_spaced_lags(n + 1) if lags is None else np.asarray(lags, dtype=np.int64)
    )
    if np.any(lag_arr < 1) or np.any(lag_arr > n):
        raise InvalidParameterError(f"lags must lie in [1, {n}]")
    sq = np.sum(pos[:, lag_arr - 1] ** 2, axis=-1)  # (walks, lags)
    rng = make_rng(seed)
    idx = rng.integers(0, w, size=(n_bootstrap, w))
    boot_msd = sq[idx].mean(axis=1)  # (n_bootstrap, lags)
    # With few walks (e.g. 1-D lattice walks) a resample can have zero MSD at
    # some lag; use only lags that are positive in every resample so that the
    # point estimate and all replicates are fitted on the same design.
    usable = np.all(boot_msd > 0, axis=0)
    if usable.sum() < 3:
        raise InvalidParameterError(
            "too few lags with positive MSD in every bootstrap resample; "
            "increase n_walks"
        )
    lag_arr, sq, boot_msd = lag_arr[usable], sq[:, usable], boot_msd[:, usable]
    point = fit_msd_exponent(lag_arr, sq.mean(axis=0))
    log_x = np.log(lag_arr.astype(float))
    xc = log_x - log_x.mean()
    log_boot = np.log(boot_msd)
    alphas = (log_boot - log_boot.mean(axis=1, keepdims=True)) @ xc / (xc @ xc)
    q = (1 - confidence) / 2
    lo, hi = np.quantile(alphas, [q, 1 - q])
    return PowerLawFit(
        alpha=point.alpha,
        alpha_stderr=float(alphas.std(ddof=1)),
        alpha_ci=(float(lo), float(hi)),
        prefactor=point.prefactor,
        r_squared=point.r_squared,
        n_points=point.n_points,
        x_range=point.x_range,
    )


def dfa(
    x: ArrayLike,
    scales: ArrayLike | None = None,
    order: int = 1,
) -> tuple[PowerLawFit, NDArray[np.int64], NDArray[np.float64]]:
    """Detrended fluctuation analysis of a stationary increment series.

    For fractional Gaussian noise with Hurst exponent H the fluctuation
    function scales as F(s) ∝ s^H, so ``fit.alpha`` estimates H.

    Args:
        x: 1-D increment series (e.g. ``np.diff`` of a walk).
        scales: Window sizes; defaults to ~20 log-spaced sizes in
            ``[order + 3, n/4]``.
        order: Polynomial order of local detrending (DFA-``order``).

    Returns:
        ``(fit, scales, F)``.
    """
    series = np.asarray(x, dtype=float).ravel()
    n = series.size
    if n < 32:
        raise InvalidParameterError("DFA needs at least 32 observations")
    profile = np.cumsum(series - series.mean())
    if scales is None:
        lo, hi = order + 3, max(order + 4, n // 4)
        scales_arr = np.unique(np.geomspace(lo, hi, 20).astype(np.int64))
    else:
        scales_arr = np.asarray(scales, dtype=np.int64)
    if np.any(scales_arr <= order + 1) or np.any(scales_arr > n):
        raise InvalidParameterError("scales must lie in (order+1, n]")

    fluct = np.empty(scales_arr.size)
    for i, s in enumerate(scales_arr):
        m = n // s
        segs = profile[: m * s].reshape(m, s)
        t = np.arange(s, dtype=float)
        V = np.vander(t, order + 1)
        coef, *_ = np.linalg.lstsq(V, segs.T, rcond=None)
        resid = segs.T - V @ coef
        fluct[i] = np.sqrt(np.mean(resid**2))
    fit = fit_msd_exponent(scales_arr, fluct)
    return fit, scales_arr, fluct


def first_passage_times(positions: ArrayLike, level: float) -> NDArray[np.float64]:
    """First time t at which |r(t)| >= ``level`` for each walk (NaN if never)."""
    if level <= 0:
        raise InvalidParameterError("level must be > 0")
    pos = _as_positions(positions)
    dist = np.linalg.norm(pos, axis=-1)
    hit = dist >= level
    first = np.argmax(hit, axis=1).astype(float) + 1.0
    first[~hit.any(axis=1)] = np.nan
    return first
