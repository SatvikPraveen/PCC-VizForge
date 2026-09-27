"""Constants and default paths for PCC-VizForge.

Configuration files ship *inside* the package so that an installed copy of
``pcc_vizforge`` is self-contained. Generated artefacts (data, figures, logs)
are written relative to an output root that defaults to the current working
directory and can be overridden with the ``PCC_VIZFORGE_OUTPUT_DIR``
environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent

# Bundled default configurations
CONFIG_DIR: Final[Path] = PACKAGE_ROOT / "configs"


def output_root() -> Path:
    """Return the root directory under which artefacts are written."""
    return Path(os.environ.get("PCC_VIZFORGE_OUTPUT_DIR", Path.cwd())).resolve()


# Output directories (resolved lazily at import time from the output root)
OUTPUT_ROOT: Final[Path] = output_root()
DATA_DIR: Final[Path] = OUTPUT_ROOT / "data" / "synthetic"
EXPORT_DIR: Final[Path] = OUTPUT_ROOT / "exports"
LOGS_DIR: Final[Path] = OUTPUT_ROOT / "logs"

# Export subdirectories
IMAGE_EXPORT_DIR: Final[Path] = EXPORT_DIR / "images"
HTML_EXPORT_DIR: Final[Path] = EXPORT_DIR / "html"

# Domain-specific data directories
RANDOM_WALK_DATA_DIR: Final[Path] = DATA_DIR / "random_walk"
DICE_DATA_DIR: Final[Path] = DATA_DIR / "dice"
WEATHER_DATA_DIR: Final[Path] = DATA_DIR / "weather"
QUAKES_DATA_DIR: Final[Path] = DATA_DIR / "quakes"
GITHUB_DATA_DIR: Final[Path] = DATA_DIR / "github"

# Default configuration names
DEFAULT_CONFIGS: Final[dict[str, str]] = {
    "random_walk": "random_walk",
    "dice": "dice",
    "weather": "weather",
    "quakes": "quakes",
    "github": "github",
}

# File format defaults
DEFAULT_IMAGE_FORMAT: Final[str] = "png"
DEFAULT_IMAGE_DPI: Final[int] = 300
DEFAULT_HTML_PLOTLYJS: Final[str] = "cdn"

# Visualization defaults
DEFAULT_FIGURE_STYLE: Final[str] = "clean"
DEFAULT_COLOR_PALETTE: Final[str] = "default"

# Supported formats
SUPPORTED_IMAGE_FORMATS: Final[tuple[str, ...]] = ("png", "jpg", "jpeg", "pdf", "svg")
SUPPORTED_DATA_FORMATS: Final[tuple[str, ...]] = (
    "csv",
    "json",
    "parquet",
    "pickle",
    "pkl",
)
SUPPORTED_LIBRARIES: Final[tuple[str, ...]] = ("matplotlib", "plotly")
SUPPORTED_EXPORT_TYPES: Final[tuple[str, ...]] = ("image", "html")

# Validation ranges
VALID_DIMENSIONS: Final[tuple[int, ...]] = (1, 2, 3)
MIN_DATA_POINTS: Final[int] = 1
MAX_DATA_POINTS: Final[int] = 10_000_000
