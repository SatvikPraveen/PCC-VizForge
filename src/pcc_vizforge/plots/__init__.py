"""Plotting: domain dashboards (Matplotlib / Plotly) and diagnostic figures.

Classes are imported lazily (PEP 562) so that ``import pcc_vizforge.plots.style``
does not pull in every dashboard module.
"""

from __future__ import annotations

import importlib
from typing import Any

# Imported eagerly: registers the `pcc` Plotly templates and colormaps that the
# dashboards reference by name. It has no intra-package dependencies.
from pcc_vizforge.plots import style as style

_LAZY: dict[str, str] = {
    "RandomWalkMatplotlibPlot": "random_walk_mpl",
    "RandomWalkPlotlyPlot": "random_walk_plotly",
    "DiceMatplotlibPlot": "dice_mpl",
    "DicePlotlyPlot": "dice_plotly",
    "WeatherMatplotlibPlot": "weather_mpl",
    "WeatherPlotlyPlot": "weather_plotly",
    "EarthquakeMatplotlibPlot": "quakes_mpl",
    "EarthquakePlotlyPlot": "quakes_plotly",
    "GitHubMatplotlibPlot": "github_mpl",
    "GitHubPlotlyPlot": "github_plotly",
}

__all__ = sorted([*_LAZY, "style"])


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        module = importlib.import_module(f"{__name__}.{_LAZY[name]}")
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted([*globals(), *_LAZY])
