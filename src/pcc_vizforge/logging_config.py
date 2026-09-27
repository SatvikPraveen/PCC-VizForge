"""Logging configuration for PCC-VizForge.

As a library, :mod:`pcc_vizforge` only attaches a :class:`logging.NullHandler`
to its top-level logger; applications (including the bundled CLI) opt in to
output by calling :func:`setup_logging`.
"""

from __future__ import annotations

import copy
import logging
import logging.config
from pathlib import Path
from typing import Any

PACKAGE_LOGGER = "pcc_vizforge"
VALID_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": (
                "%(asctime)s [%(levelname)s] %(name)s "
                "(%(filename)s:%(lineno)d) %(funcName)s(): %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        PACKAGE_LOGGER: {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}


def setup_logging(
    level: str = "INFO",
    log_file: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    """Configure logging for the ``pcc_vizforge`` logger hierarchy.

    Args:
        level: Console log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path of a rotating DEBUG-level log file.
        config: Optional full :func:`logging.config.dictConfig` mapping that
            replaces the default configuration.

    Raises:
        ValueError: If ``level`` is not a valid level name.
    """
    level = level.upper()
    if level not in VALID_LEVELS:
        raise ValueError(f"Invalid logging level: {level}. Must be one of {sorted(VALID_LEVELS)}")

    log_config = copy.deepcopy(config if config is not None else LOGGING_CONFIG)
    if config is None:
        log_config["handlers"]["console"]["level"] = level
        if log_file is not None:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": str(log_path),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            }
            log_config["loggers"][PACKAGE_LOGGER]["handlers"].append("file")

    logging.config.dictConfig(log_config)


def get_logger(name: str) -> logging.Logger:
    """Return a logger (thin wrapper kept for backwards compatibility)."""
    return logging.getLogger(name)
