"""Constants and configuration for PCC-VizForge."""

from pathlib import Path
from typing import Final

# Project root directory (where pyproject.toml is located)
PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent

# Data directories
DATA_DIR: Final[Path] = PROJECT_ROOT / "data" / "synthetic"
CONFIG_DIR: Final[Path] = PROJECT_ROOT / "config"
EXPORT_DIR: Final[Path] = PROJECT_ROOT / "exports"
LOGS_DIR: Final[Path] = PROJECT_ROOT / "logs"

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
DEFAULT_CONFIGS = {
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
SUPPORTED_IMAGE_FORMATS: Final[tuple] = ("png", "jpg", "jpeg", "pdf", "svg")
SUPPORTED_DATA_FORMATS: Final[tuple] = ("csv", "json", "pickle", "pkl")
SUPPORTED_LIBRARIES: Final[tuple] = ("matplotlib", "plotly")
SUPPORTED_EXPORT_TYPES: Final[tuple] = ("image", "html")

# Validation ranges
VALID_DIMENSIONS: Final[tuple] = (1, 2, 3)
MIN_DATA_POINTS: Final[int] = 1
MAX_DATA_POINTS: Final[int] = 1000000
