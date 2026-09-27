"""Theming helpers (thin compatibility layer over :mod:`pcc_vizforge.plots.style`)."""

from __future__ import annotations

import logging
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

from pcc_vizforge.exceptions import VisualizationError
from pcc_vizforge.plots.style import CATEGORICAL, CATEGORICAL_DARK, matplotlib_rc

logger = logging.getLogger(__name__)

# Only CVD-validated palettes are offered; see plots/style.py.
COLOR_PALETTES: dict[str, list[str]] = {
    "default": list(CATEGORICAL),
    "scientific": list(CATEGORICAL),
    "dark": list(CATEGORICAL_DARK),
}

MATPLOTLIB_STYLES: dict[str, dict[str, Any]] = {
    "clean": matplotlib_rc("light"),
    "publication": matplotlib_rc("light"),
    "dark": matplotlib_rc("dark"),
    "minimal": {**matplotlib_rc("light"), "axes.grid": False},
}

PLOTLY_TEMPLATES: dict[str, str] = {
    "clean": "pcc",
    "publication": "pcc",
    "dark": "pcc_dark",
    "minimal": "simple_white",
}


def get_color_palette(name: str = "default", n_colors: int | None = None) -> list[str]:
    """Return a categorical palette.

    Colours are never cycled: requesting more colours than the palette holds
    raises :class:`VisualizationError`, because repeated hues make series
    indistinguishable.
    """
    palette = COLOR_PALETTES.get(name, COLOR_PALETTES["default"])
    if n_colors is None:
        return list(palette)
    if n_colors > len(palette):
        raise VisualizationError(
            f"Requested {n_colors} colours but palette '{name}' has {len(palette)}; "
            "group minor categories into 'Other' or use small multiples"
        )
    return list(palette[:n_colors])


def apply_style(style_name: str = "clean") -> None:
    """Apply a named Matplotlib style globally."""
    if style_name in MATPLOTLIB_STYLES:
        plt.rcParams.update(MATPLOTLIB_STYLES[style_name])
        return
    try:
        plt.style.use(style_name)
    except OSError:
        logger.warning("Style %r not found; using 'clean'", style_name)
        plt.rcParams.update(MATPLOTLIB_STYLES["clean"])


def get_matplotlib_style(style_name: str = "clean") -> dict[str, Any]:
    """rcParams dictionary for a named style."""
    return MATPLOTLIB_STYLES.get(style_name, MATPLOTLIB_STYLES["clean"])


def get_plotly_template(template_name: str = "clean") -> str:
    """Plotly template name for a named style."""
    return PLOTLY_TEMPLATES.get(template_name, "pcc")


def create_custom_colormap(colors: list[str], name: str = "custom") -> LinearSegmentedColormap:
    """Linear colormap through ``colors``."""
    return LinearSegmentedColormap.from_list(name, colors)


def setup_figure_style(
    figsize: tuple[float, float] = (12, 8), style: str = "clean", palette: str = "default"
) -> Figure:
    """Apply ``style`` and create a figure using ``palette`` as the colour cycle."""
    apply_style(style)
    plt.rcParams["axes.prop_cycle"] = mpl.cycler(color=get_color_palette(palette))
    return plt.figure(figsize=figsize)


def format_axis_labels(
    ax: Axes, xlabel: str = "", ylabel: str = "", title: str = "", title_size: int = 11
) -> None:
    """Set axis labels and a left-aligned title."""
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, fontsize=title_size, loc="left")


def add_watermark(
    ax: Axes, text: str = "PCC-VizForge", position: tuple[float, float] = (0.99, 0.01), alpha: float = 0.3
) -> None:
    """Add a small attribution mark (not used by the built-in figures)."""
    ax.text(
        position[0], position[1], text, transform=ax.transAxes, fontsize=7, alpha=alpha,
        ha="right", va="bottom", style="italic", color="gray",
    )
