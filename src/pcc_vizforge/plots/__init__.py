"""Plotting modules for PCC VizForge."""

from .random_walk_mpl import RandomWalkMatplotlibPlot
from .random_walk_plotly import RandomWalkPlotlyPlot
from .dice_mpl import DiceMatplotlibPlot
from .dice_plotly import DicePlotlyPlot
from .weather_mpl import WeatherMatplotlibPlot
from .weather_plotly import WeatherPlotlyPlot
from .quakes_mpl import EarthquakeMatplotlibPlot
from .quakes_plotly import EarthquakePlotlyPlot
from .github_mpl import GitHubMatplotlibPlot
from .github_plotly import GitHubPlotlyPlot

__all__ = [
    "RandomWalkMatplotlibPlot",
    "RandomWalkPlotlyPlot",
    "DiceMatplotlibPlot",
    "DicePlotlyPlot",
    "WeatherMatplotlibPlot",
    "WeatherPlotlyPlot",
    "EarthquakeMatplotlibPlot",
    "EarthquakePlotlyPlot",
    "GitHubMatplotlibPlot",
    "GitHubPlotlyPlot",
]