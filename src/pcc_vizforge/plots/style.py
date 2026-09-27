"""Shared, publication-quality visual style for Matplotlib and Plotly.

Colour roles
------------
* **Categorical** -- eight hues in a *fixed* order, validated for colour-vision
  deficiency (worst adjacent CVD ΔE 9.1, normal-vision ΔE ≥ 19.6 on the light
  surface). Slots are assigned in order and never cycled: a ninth series must
  be folded into "Other" or split into small multiples.
* **Sequential** -- a single blue hue, light → dark, for magnitudes.
* **Diverging** -- blue ↔ neutral grey ↔ red, for signed quantities.

Three light-mode slots (aqua, yellow, magenta) sit below 3:1 contrast against
the surface, so figures that use them must carry a legend or direct labels.

Figures use thin recessive axes, 2 px lines, no top/right spines and embed
TrueType fonts in PDF/PS output so they can be submitted to journals as-is.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Literal

import matplotlib as mpl
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.io as pio
from matplotlib.colors import LinearSegmentedColormap

from pcc_vizforge.exceptions import VisualizationError

__all__ = [
    "CATEGORICAL",
    "CATEGORICAL_DARK",
    "DIVERGING_CMAP",
    "SEQUENTIAL_CMAP",
    "SEQUENTIAL_STEPS",
    "TOKENS",
    "apply_matplotlib_style",
    "categorical",
    "matplotlib_rc",
    "plotly_colorscale",
    "publication_style",
    "series_color",
]

Theme = Literal["light", "dark"]

CATEGORICAL: tuple[str, ...] = (
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
)
CATEGORICAL_DARK: tuple[str, ...] = (
    "#3987e5",
    "#d95926",
    "#199e70",
    "#c98500",
    "#d55181",
    "#008300",
    "#9085e9",
    "#e66767",
)

SEQUENTIAL_STEPS: tuple[str, ...] = (
    "#cde2fb",
    "#b7d3f6",
    "#9ec5f4",
    "#86b6ef",
    "#6da7ec",
    "#5598e7",
    "#3987e5",
    "#2a78d6",
    "#256abf",
    "#1c5cab",
    "#184f95",
    "#104281",
    "#0d366b",
)
DIVERGING_STEPS: tuple[str, ...] = ("#0d366b", "#2a78d6", "#9ec5f4", "#f0efec", "#f2a9a8", "#e34948", "#8f1f1e")

TOKENS: dict[Theme, dict[str, str]] = {
    "light": {
        "surface": "#fcfcfb",
        "text_primary": "#0b0b0b",
        "text_secondary": "#52514e",
        "axis": "#b9b8b3",
        "grid": "#ebeae6",
        "neutral": "#8a8984",
    },
    "dark": {
        "surface": "#1a1a19",
        "text_primary": "#ffffff",
        "text_secondary": "#c3c2b7",
        "axis": "#5c5b56",
        "grid": "#2c2c2a",
        "neutral": "#8f8e87",
    },
}

SEQUENTIAL_CMAP = LinearSegmentedColormap.from_list("pcc_sequential", SEQUENTIAL_STEPS)
DIVERGING_CMAP = LinearSegmentedColormap.from_list("pcc_diverging", DIVERGING_STEPS)
for _cmap in (SEQUENTIAL_CMAP, DIVERGING_CMAP):
    if _cmap.name not in mpl.colormaps:
        mpl.colormaps.register(_cmap)
        mpl.colormaps.register(_cmap.reversed())


def categorical(n: int, theme: Theme = "light") -> list[str]:
    """First ``n`` categorical colours; raises instead of cycling past eight."""
    palette = CATEGORICAL if theme == "light" else CATEGORICAL_DARK
    if n > len(palette):
        raise VisualizationError(
            f"{n} categorical series requested but only {len(palette)} distinguishable "
            "colours exist; fold minor series into 'Other' or use small multiples"
        )
    return list(palette[:n])


def series_color(index: int, theme: Theme = "light") -> str:
    """Colour of the ``index``-th series (0-based, fixed order)."""
    return categorical(index + 1, theme)[index]


def plotly_colorscale(kind: Literal["sequential", "diverging"] = "sequential") -> list[list[Any]]:
    """Plotly ``colorscale`` equivalent of the Matplotlib colormaps."""
    steps = SEQUENTIAL_STEPS if kind == "sequential" else DIVERGING_STEPS
    n = len(steps) - 1
    return [[i / n, c] for i, c in enumerate(steps)]


def matplotlib_rc(theme: Theme = "light") -> dict[str, Any]:
    """rcParams implementing the publication style."""
    t = TOKENS[theme]
    return {
        "figure.facecolor": t["surface"],
        "axes.facecolor": t["surface"],
        "savefig.facecolor": t["surface"],
        "figure.dpi": 110,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelsize": 10,
        "axes.labelcolor": t["text_secondary"],
        "axes.edgecolor": t["axis"],
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "axes.prop_cycle": mpl.cycler(color=list(CATEGORICAL if theme == "light" else CATEGORICAL_DARK)),
        "grid.color": t["grid"],
        "grid.linewidth": 0.6,
        "xtick.color": t["text_secondary"],
        "ytick.color": t["text_secondary"],
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "text.color": t["text_primary"],
        "axes.titlecolor": t["text_primary"],
        "legend.frameon": False,
        "legend.fontsize": 9,
        "lines.linewidth": 2.0,
        "lines.markersize": 5,
        "patch.linewidth": 0,
        "image.cmap": "pcc_sequential",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    }


def apply_matplotlib_style(theme: Theme = "light") -> None:
    """Apply the publication style globally."""
    plt.rcParams.update(matplotlib_rc(theme))


@contextmanager
def publication_style(theme: Theme = "light") -> Iterator[None]:
    """Context manager applying the publication style temporarily."""
    with mpl.rc_context(matplotlib_rc(theme)):
        yield


def _plotly_template(theme: Theme) -> go.layout.Template:
    t = TOKENS[theme]
    axis = {
        "showgrid": True,
        "gridcolor": t["grid"],
        "gridwidth": 1,
        "linecolor": t["axis"],
        "zeroline": False,
        "ticks": "outside",
        "tickcolor": t["axis"],
        "title": {"font": {"color": t["text_secondary"]}},
        "tickfont": {"color": t["text_secondary"]},
    }
    return go.layout.Template(
        layout={
            "paper_bgcolor": t["surface"],
            "plot_bgcolor": t["surface"],
            "font": {"family": "Inter, system-ui, sans-serif", "size": 12, "color": t["text_primary"]},
            "colorway": list(CATEGORICAL if theme == "light" else CATEGORICAL_DARK),
            "xaxis": axis,
            "yaxis": axis,
            "hovermode": "closest",
            "hoverlabel": {"font": {"color": t["text_primary"]}, "bgcolor": t["surface"], "bordercolor": t["axis"]},
            "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
            "colorscale": {"sequential": plotly_colorscale("sequential"), "diverging": plotly_colorscale("diverging")},
            "title": {"x": 0.0, "xanchor": "left"},
        },
        data={"scatter": [go.Scatter(line={"width": 2})]},
    )


pio.templates["pcc"] = _plotly_template("light")
pio.templates["pcc_dark"] = _plotly_template("dark")
