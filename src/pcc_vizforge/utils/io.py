"""Input/Output utilities for PCC VizForge."""

import json
import logging
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from pcc_vizforge.constants import (
    CONFIG_DIR,
    DATA_DIR,
    HTML_EXPORT_DIR,
    IMAGE_EXPORT_DIR,
    LOGS_DIR,
)
from pcc_vizforge.exceptions import (
    ConfigFileNotFoundError,
    ExportError,
    InvalidConfigurationError,
    ValidationError,
)
from pcc_vizforge.exceptions import (
    IOError as PccIOError,
)

logger = logging.getLogger(__name__)


def resolve_config_path(config_name: str | Path) -> Path:
    """Resolve a bundled config name (``"dice"``) or a filesystem path."""
    candidate = Path(config_name)
    if candidate.suffix in {".yaml", ".yml"} or candidate.is_file():
        return candidate
    return CONFIG_DIR / f"{config_name}.yaml"


def load_config(config_name: str | Path) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_name: Name of a bundled config (without ``.yaml``) or a path
            to a user-supplied YAML file.

    Returns:
        Dictionary containing configuration data

    Raises:
        ConfigFileNotFoundError: If config file doesn't exist
        InvalidConfigurationError: If config file is invalid YAML
    """
    config_path = resolve_config_path(config_name)

    logger.debug(f"Loading configuration from: {config_path}")

    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        raise ConfigFileNotFoundError(
            f"Configuration file not found: {config_path}. "
            f"Available configs: {', '.join(list_available_configs())}"
        )

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config file {config_path}: {e}")
        raise InvalidConfigurationError(
            f"Error parsing config file {config_path}: {e}"
        ) from e

    if config is None:
        logger.error(f"Configuration file is empty: {config_path}")
        raise InvalidConfigurationError(f"Configuration file is empty: {config_path}")
    if not isinstance(config, dict):
        raise InvalidConfigurationError(
            f"Top level of {config_path} must be a mapping, got {type(config).__name__}"
        )

    logger.debug(f"Successfully loaded configuration: {config_name}")
    return config


def ensure_directory_exists(file_path: str | Path) -> None:
    """Ensure that the directory for a file path exists.

    Args:
        file_path: Path to file (directory will be created if it doesn't exist)

    Raises:
        IOError: If directory creation fails
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directory ensured: {path.parent}")
    except OSError as e:
        logger.error(f"Failed to create directory for {file_path}: {e}")
        raise PccIOError(f"Failed to create directory for {file_path}: {e}") from e


def save_data(data: Any, file_path: str | Path, format_type: str = "auto") -> None:
    """Save data to file in specified format.

    Args:
        data: Data to save (pandas DataFrame, dict, list, etc.)
        file_path: Output file path
        format_type: Format to save in ('csv', 'json', 'pickle', 'auto')
                    'auto' infers from file extension

    Raises:
        ValidationError: If data type doesn't match format
        ExportError: If save operation fails
    """
    file_path = Path(file_path)
    ensure_directory_exists(file_path)

    if format_type == "auto":
        format_type = file_path.suffix.lower().lstrip(".")

    try:
        if format_type == "csv":
            if not isinstance(data, pd.DataFrame):
                raise ValidationError("CSV format requires pandas DataFrame")
            data.to_csv(file_path, index=False)
            logger.info(f"Saved data to CSV: {file_path}")

        elif format_type == "json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Saved data to JSON: {file_path}")

        elif format_type in ["pickle", "pkl"]:
            with open(file_path, "wb") as f:
                pickle.dump(data, f)
            logger.info(f"Saved data to pickle: {file_path}")

        else:
            raise ValidationError(
                f"Unsupported format: {format_type}. Supported: csv, json, pickle"
            )

    except Exception as e:
        logger.error(f"Failed to save data to {file_path}: {e}")
        raise ExportError(f"Failed to save data to {file_path}: {e}") from e


def load_data(file_path: str | Path, format_type: str = "auto") -> Any:
    """Load data from file.

    Args:
        file_path: Input file path
        format_type: Format to load from ('csv', 'json', 'pickle', 'auto')
                    'auto' infers from file extension

    Returns:
        Loaded data

    Raises:
        PccIOError: If file doesn't exist or load fails
        ValidationError: If format is unsupported
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.error(f"Data file not found: {file_path}")
        raise PccIOError(f"Data file not found: {file_path}")

    if format_type == "auto":
        format_type = file_path.suffix.lower().lstrip(".")

    try:
        if format_type == "csv":
            data = pd.read_csv(file_path)
            logger.debug(f"Loaded CSV data from {file_path}")

        elif format_type == "json":
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(f"Loaded JSON data from {file_path}")

        elif format_type in ["pickle", "pkl"]:
            with open(file_path, "rb") as f:
                data = pickle.load(f)
            logger.debug(f"Loaded pickle data from {file_path}")

        else:
            raise ValidationError(
                f"Unsupported format: {format_type}. Supported: csv, json, pickle"
            )

        return data

    except (json.JSONDecodeError, pickle.UnpicklingError) as e:
        logger.error(f"Failed to parse data file {file_path}: {e}")
        raise PccIOError(f"Failed to parse data file {file_path}: {e}") from e


def get_data_directory(data_type: str) -> Path:
    """Get the data directory path for a specific data type.

    Args:
        data_type: Type of data (e.g., 'random_walk', 'dice', etc.)

    Returns:
        Path to the data directory

    Raises:
        PccIOError: If directory creation fails
    """
    data_dir = DATA_DIR / data_type
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Data directory ensured: {data_dir}")
        return data_dir
    except OSError as e:
        logger.error(f"Failed to create data directory {data_dir}: {e}")
        raise PccIOError(f"Failed to create data directory {data_dir}: {e}") from e


def get_export_directory(export_type: str) -> Path:
    """Get the export directory path for a specific export type.

    Args:
        export_type: Type of export ('images' or 'html')

    Returns:
        Path to the export directory

    Raises:
        ValidationError: If export type is invalid
        PccIOError: If directory creation fails
    """
    if export_type not in ["images", "html"]:
        logger.error(f"Invalid export type: {export_type}")
        raise ValidationError(
            f"Invalid export type: {export_type}. Supported: images, html"
        )

    export_dir = IMAGE_EXPORT_DIR if export_type == "images" else HTML_EXPORT_DIR
    try:
        export_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Export directory ensured: {export_dir}")
        return export_dir
    except OSError as e:
        logger.error(f"Failed to create export directory {export_dir}: {e}")
        raise PccIOError(f"Failed to create export directory {export_dir}: {e}") from e


def list_available_configs() -> list[str]:
    """List all available configuration files.

    Returns:
        List of configuration names (without .yaml extension)
    """
    if not CONFIG_DIR.exists():
        logger.warning(f"Configuration directory does not exist: {CONFIG_DIR}")
        return []

    configs = []
    try:
        for file in CONFIG_DIR.glob("*.yaml"):
            configs.append(file.stem)
        logger.debug(f"Found {len(configs)} configuration files")
    except OSError as e:
        logger.error(f"Failed to list configurations: {e}")

    return sorted(configs)


def ensure_logs_directory() -> Path:
    """Ensure that the logs directory exists.

    Returns:
        Path to the logs directory
    """
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        return LOGS_DIR
    except OSError as e:
        logger.error(f"Failed to create logs directory: {e}")
        raise PccIOError(f"Failed to create logs directory: {e}") from e
