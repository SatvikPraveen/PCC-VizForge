"""Logging configuration for PCC-VizForge."""

import logging
import logging.config
from pathlib import Path
from typing import Optional


# Default logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(funcName)s(): %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[%(levelname)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "logs/pcc_vizforge.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": "logs/errors.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "src": {
            "level": "DEBUG",
            "handlers": ["console", "file", "error_file"],
            "propagate": False,
        },
        "src.generators": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "src.plots": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "src.utils": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
}


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    config: Optional[dict] = None,
) -> None:
    """Setup logging for PCC-VizForge.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        config: Optional custom logging configuration dict

    Raises:
        ValueError: If invalid logging level is provided
    """
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if level not in valid_levels:
        raise ValueError(
            f"Invalid logging level: {level}. Must be one of {valid_levels}"
        )

    # Use provided config or default
    log_config = config or LOGGING_CONFIG

    # Update log file path if provided
    if log_file:
        log_config["handlers"]["file"]["filename"] = log_file

    # Create logs directory if it doesn't exist
    log_dir = Path(log_config["handlers"]["file"]["filename"]).parent
    log_dir.mkdir(exist_ok=True, parents=True)

    # Set root logger level
    log_config["root"]["level"] = level

    # Apply configuration
    logging.config.dictConfig(log_config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
