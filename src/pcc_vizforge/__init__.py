"""PCC-VizForge: reproducible synthetic-data generation, statistical analysis
and visualisation of canonical stochastic processes.

The package is organised in layers:

* :mod:`pcc_vizforge.generators` -- seeded, vectorised stochastic models.
* :mod:`pcc_vizforge.plots` -- Matplotlib (static) and Plotly (interactive) views.
* :mod:`pcc_vizforge.utils` -- configuration, I/O and theming helpers.
"""

from __future__ import annotations

import logging

from pcc_vizforge._version import __version__
from pcc_vizforge.exceptions import (
    ConfigFileNotFoundError,
    ConfigurationError,
    DataGenerationError,
    DataShapeError,
    ExportError,
    InvalidConfigurationError,
    InvalidParameterError,
    PccVizForgeError,
    ValidationError,
    VisualizationError,
)
from pcc_vizforge.exceptions import IOError as PccIOError
from pcc_vizforge.generators import (
    DiceGenerator,
    EarthquakeGenerator,
    GitHubGenerator,
    RandomWalkGenerator,
    WeatherGenerator,
)

logging.getLogger(__name__).addHandler(logging.NullHandler())

__author__ = "Satvik Praveen"
__email__ = "satvikpraveen707@gmail.com"
__license__ = "MIT"

__all__ = [
    "__version__",
    # Exceptions
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
    # Generators
    "RandomWalkGenerator",
    "DiceGenerator",
    "WeatherGenerator",
    "EarthquakeGenerator",
    "GitHubGenerator",
]
