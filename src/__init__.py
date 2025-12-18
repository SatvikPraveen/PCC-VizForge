# Location: src/__init__.py

"""
PCC VizForge - Comprehensive Data Visualization Toolkit

A powerful toolkit for generating and visualizing synthetic data across multiple domains
including random walks, dice simulations, weather patterns, earthquake data, and GitHub statistics.
"""

__version__ = "0.1.0"
__author__ = "Satvik Praveen"
__license__ = "MIT"

from src.exceptions import (
    ConfigFileNotFoundError,
    ConfigurationError,
    DataGenerationError,
    DataShapeError,
    ExportError,
    InvalidConfigurationError,
    InvalidParameterError,
    IOError as PccIOError,
    PccVizForgeError,
    ValidationError,
    VisualizationError,
)
from src.generators import (
    DiceGenerator,
    EarthquakeGenerator,
    GitHubGenerator,
    RandomWalkGenerator,
    WeatherGenerator,
)

__all__ = [
    "PccVizForgeError",
    "ConfigurationError",
    "ConfigFileNotFoundError",
    "InvalidConfigurationError",
    "DataGenerationError",
    "DataShapeError",
    "ValidationError",
    "InvalidParameterError",
    "VisualizationError",
    "ExportError",
    "PccIOError",
    "RandomWalkGenerator",
    "DiceGenerator",
    "WeatherGenerator",
    "EarthquakeGenerator",
    "GitHubGenerator",
]
__author__ = "PCC VizForge Team"
__email__ = "team@pcc-vizforge.com"

# Import main components for easy access
from src.generators import (
    RandomWalkGenerator,
    DiceGenerator,
    WeatherGenerator,
    EarthquakeGenerator,
    GitHubGenerator,
)

from src.plots import (
    RandomWalkMatplotlibPlot,
    RandomWalkPlotlyPlot,
    DiceMatplotlibPlot,
    DicePlotlyPlot,
    WeatherMatplotlibPlot,
    WeatherPlotlyPlot,
    EarthquakeMatplotlibPlot,
    EarthquakePlotlyPlot,
    GitHubMatplotlibPlot,
    GitHubPlotlyPlot,
)

from src.utils.io import load_config, save_data, load_data
from src.utils.theming import get_color_palette, apply_style

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    
    # Generators
    "RandomWalkGenerator",
    "DiceGenerator", 
    "WeatherGenerator",
    "EarthquakeGenerator",
    "GitHubGenerator",
    
    # Matplotlib plots
    "RandomWalkMatplotlibPlot",
    "DiceMatplotlibPlot",
    "WeatherMatplotlibPlot",
    "EarthquakeMatplotlibPlot",
    "GitHubMatplotlibPlot",
    
    # Plotly plots
    "RandomWalkPlotlyPlot",
    "DicePlotlyPlot",
    "WeatherPlotlyPlot",
    "EarthquakePlotlyPlot",
    "GitHubPlotlyPlot",
    
    # Utilities
    "load_config",
    "save_data",
    "load_data",
    "get_color_palette",
    "apply_style",
]