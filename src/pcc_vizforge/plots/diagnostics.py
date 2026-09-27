"""Single-panel diagnostic figures that pair data with theory and estimates.

Each function answers one question with one y-axis, shows uncertainty
explicitly (confidence bands or error bars), and labels the fitted quantity
in the legend. All functions return a :class:`matplotlib.figure.Figure` and
accept an optional ``ax`` so they can be composed into multi-panel figures.
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from numpy.typing import ArrayLike
from scipy import stats

from pcc_vizforge.analysis.diffusion import PowerLawFit as MSDFit
from pcc_vizforge.analysis.heavy_tails import PowerLawFit, ccdf
from pcc_vizforge.analysis.seismology import (
    BValueEstimate,
    OmoriFit,
    frequency_magnitude_distribution,
)
from pcc_vizforge.analysis.timeseries import HarmonicFit
from pcc_vizforge.plots.style import TOKENS, publication_style, series_color

__all__ = [
    "ccdf_figure",
    "dice_sum_figure",
    "gutenberg_richter_figure",
    "msd_figure",
    "omori_figure",
    "pvalue_calibration_figure",
    "temperature_figure",
]

NEUTRAL = TOKENS["light"]["neutral"]
TEXT2 = TOKENS["light"]["text_secondary"]


def _axes(
    ax: Axes | None, size: tuple[float, float] = (5.5, 3.8)
) -> tuple[Figure, Axes]:
    if ax is not None:
        return ax.figure, ax  # type: ignore[return-value]
    fig, new_ax = plt.subplots(figsize=size, layout="constrained")
    return fig, new_ax


def msd_figure(
    lags: ArrayLike,
    msd: ArrayLike,
    sem: ArrayLike | None = None,
    *,
    theory: ArrayLike | None = None,
    fit: MSDFit | None = None,
    label: str = "Ensemble MSD",
    ax: Axes | None = None,
) -> Figure:
    """Log-log mean-squared displacement with 95 % band, theory and fitted power law."""
    with publication_style():
        fig, ax = _axes(ax)
        x = np.asarray(lags, dtype=float)
        y = np.asarray(msd, dtype=float)
        color = series_color(0)
        if sem is not None:
            s = 1.96 * np.asarray(sem, dtype=float)
            ax.fill_between(
                x,
                np.clip(y - s, 1e-12, None),
                y + s,
                color=color,
                alpha=0.18,
                linewidth=0,
                label="95% CI",
            )
        ax.plot(x, y, color=color, label=label)
        if theory is not None:
            ax.plot(
                x, theory, color=NEUTRAL, linestyle="--", linewidth=1.5, label="Theory"
            )
        if fit is not None:
            xs = np.geomspace(*fit.x_range, 50)
            lo, hi = fit.alpha_ci
            ax.plot(
                xs,
                fit.prefactor * xs**fit.alpha,
                color=series_color(1),
                linewidth=1.5,
                label=f"Fit: α = {fit.alpha:.3f} [{lo:.3f}, {hi:.3f}]",
            )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Lag t (steps)")
        ax.set_ylabel(r"$\langle |r(t)|^2 \rangle$")
        ax.set_title("Mean-squared displacement")
        ax.legend()
        return fig


def dice_sum_figure(
    support: ArrayLike,
    pmf: ArrayLike,
    counts: ArrayLike,
    *,
    p_value: float | None = None,
    ax: Axes | None = None,
) -> Figure:
    """Observed sum frequencies (with Wilson 95 % intervals) against the exact PMF."""
    with publication_style():
        fig, ax = _axes(ax)
        k = np.asarray(support)
        c = np.asarray(counts, dtype=float)
        n = c.sum()
        phat = c / n
        z = 1.96
        centre = (phat + z**2 / (2 * n)) / (1 + z**2 / n)
        half = z * np.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
        ax.bar(
            k,
            phat,
            width=0.8,
            color=series_color(0),
            label=f"Observed (n = {int(n):,})",
        )
        ax.errorbar(
            k,
            centre,
            yerr=half,
            fmt="none",
            ecolor=TEXT2,
            elinewidth=1,
            capsize=2,
            label="Wilson 95% CI",
        )
        ax.plot(
            k,
            pmf,
            color=series_color(1),
            marker="o",
            markersize=5,
            linewidth=1.5,
            label="Exact PMF",
        )
        title = "Distribution of the sum"
        if p_value is not None:
            title += f"  (χ² GOF p = {p_value:.3g})"
        ax.set_title(title)
        ax.set_xlabel("Sum of dice")
        ax.set_ylabel("Probability")
        ax.grid(axis="x", visible=False)
        ax.legend()
        return fig


def gutenberg_richter_figure(
    magnitudes: ArrayLike,
    estimate: BValueEstimate | None = None,
    *,
    bin_width: float = 0.1,
    ax: Axes | None = None,
) -> Figure:
    """Cumulative frequency-magnitude distribution with the fitted G-R line."""
    with publication_style():
        fig, ax = _axes(ax)
        centres, inc, cum = frequency_magnitude_distribution(magnitudes, bin_width)
        edges = centres - bin_width / 2
        ax.scatter(edges, cum, s=18, color=series_color(0), label="N(M ≥ m)", zorder=3)
        ax.scatter(
            centres[inc > 0],
            inc[inc > 0],
            s=14,
            marker="s",
            color=NEUTRAL,
            label="Per-bin count",
            zorder=2,
        )
        if estimate is not None:
            m = np.linspace(
                estimate.mc, float(np.max(np.asarray(magnitudes, dtype=float))), 50
            )
            lo, hi = estimate.ci
            ax.plot(
                m,
                10 ** (estimate.a_value - estimate.b_value * m),
                color=series_color(1),
                label=f"b = {estimate.b_value:.3f} [{lo:.3f}, {hi:.3f}]",
            )
            ax.axvline(estimate.mc, color=NEUTRAL, linestyle=":", linewidth=1)
        ax.set_yscale("log")
        ax.set_ylim(bottom=0.5)
        ax.set_xlabel("Magnitude m")
        ax.set_ylabel("Number of events")
        ax.set_title("Gutenberg-Richter frequency-magnitude distribution")
        ax.legend()
        return fig


def omori_figure(
    times: ArrayLike,
    fit: OmoriFit | None = None,
    *,
    n_bins: int = 30,
    time_unit: str = "days",
    ax: Axes | None = None,
) -> Figure:
    """Aftershock rate in log-spaced bins with the fitted Omori-Utsu law."""
    with publication_style():
        fig, ax = _axes(ax)
        t = np.asarray(times, dtype=float)
        t = t[t > 0]
        edges = np.geomspace(t.min(), t.max(), n_bins + 1)
        counts, _ = np.histogram(t, edges)
        widths = np.diff(edges)
        mids = np.sqrt(edges[:-1] * edges[1:])
        keep = counts > 0
        rate = counts / widths
        # Exact (Garwood) 68 % Poisson intervals stay positive on a log axis.
        lo = stats.chi2.ppf(0.16, 2 * counts) / 2
        hi = stats.chi2.ppf(0.84, 2 * counts + 2) / 2
        yerr = np.vstack([(counts - lo) / widths, (hi - counts) / widths])
        ax.errorbar(
            mids[keep],
            rate[keep],
            yerr=yerr[:, keep],
            fmt="o",
            color=series_color(0),
            ecolor=TEXT2,
            markersize=5,
            elinewidth=1,
            label="Observed rate (Poisson 68% CI)",
        )
        if fit is not None:
            xs = np.geomspace(t.min(), t.max(), 100)
            ax.plot(
                xs,
                fit.rate(xs),
                color=series_color(1),
                label=f"Omori-Utsu: p = {fit.p:.2f} ± {fit.p_stderr:.2f}, c = {fit.c:.3g}",
            )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(f"Time since parent event ({time_unit})")
        ax.set_ylabel(f"Events per {time_unit.rstrip('s')}")
        ax.set_title("Aftershock decay")
        ax.legend()
        return fig


def ccdf_figure(
    x: ArrayLike,
    fit: PowerLawFit | None = None,
    *,
    label: str = "Empirical",
    ax: Axes | None = None,
) -> Figure:
    """Log-log empirical CCDF with the fitted power-law tail."""
    with publication_style():
        fig, ax = _axes(ax)
        v, c = ccdf(x)
        ax.scatter(v, c, s=10, color=series_color(0), label=label, zorder=3)
        if fit is not None:
            frac = fit.n_tail / fit.n_total
            xs = np.geomspace(fit.xmin, v.max(), 100)
            ax.plot(
                xs,
                frac * fit.ccdf(xs),
                color=series_color(1),
                label=f"Power law: α = {fit.alpha:.2f} ± {fit.alpha_stderr:.2f}",
            )
            ax.axvline(fit.xmin, color=NEUTRAL, linestyle=":", linewidth=1)
            ax.annotate(
                " $x_{min}$", (fit.xmin, c.max()), color=TEXT2, fontsize=9, va="top"
            )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("x")
        ax.set_ylabel("P(X ≥ x)")
        ax.set_title("Complementary CDF")
        ax.legend()
        return fig


def temperature_figure(
    t_days: ArrayLike,
    temperature: ArrayLike,
    fit: HarmonicFit | None = None,
    *,
    ax: Axes | None = None,
) -> Figure:
    """Daily temperatures with the fitted seasonal cycle and linear trend."""
    with publication_style():
        fig, ax = _axes(ax, (7.0, 3.6))
        t = np.asarray(t_days, dtype=float)
        ax.scatter(
            t / 365.25,
            temperature,
            s=3,
            color=NEUTRAL,
            alpha=0.6,
            label="Daily mean",
            rasterized=True,
        )
        if fit is not None:
            ax.plot(
                t / 365.25,
                fit.predict(t),
                color=series_color(0),
                linewidth=1.2,
                label="Harmonic fit",
            )
            trend = fit.mean + fit.trend_per_unit * t
            ax.plot(
                t / 365.25,
                trend,
                color=series_color(1),
                label=(
                    f"Trend: {fit.trend_per_unit * 3652.5:+.2f} ± "
                    f"{1.96 * fit.trend_stderr_hac * 3652.5:.2f} °C/decade (HAC 95%)"
                ),
            )
        ax.set_xlabel("Years since start")
        ax.set_ylabel("Temperature (°C)")
        ax.set_title("Seasonal cycle and trend")
        ax.legend()
        return fig


def pvalue_calibration_figure(
    p_values: Sequence[float] | ArrayLike,
    *,
    label: str = "Test",
    ax: Axes | None = None,
) -> Figure:
    """Uniform Q-Q plot of p-values with a 95 % pointwise band.

    Under the null hypothesis a calibrated test gives p ~ U(0, 1); the order
    statistics then follow Beta(i, n - i + 1).
    """
    with publication_style():
        fig, ax = _axes(ax, (4.2, 4.2))
        p = np.sort(np.asarray(p_values, dtype=float))
        n = p.size
        i = np.arange(1, n + 1)
        expected = i / (n + 1)
        lo = stats.beta.ppf(0.025, i, n - i + 1)
        hi = stats.beta.ppf(0.975, i, n - i + 1)
        ax.fill_between(
            expected, lo, hi, color=NEUTRAL, alpha=0.2, linewidth=0, label="95% band"
        )
        ax.plot([0, 1], [0, 1], color=NEUTRAL, linestyle="--", linewidth=1)
        ax.plot(expected, p, color=series_color(0), label=label)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal")
        ax.set_xlabel("Expected p (uniform)")
        ax.set_ylabel("Observed p")
        ax.set_title("p-value calibration under H₀")
        ax.legend(loc="upper left")
        return fig
