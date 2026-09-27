"""Utility modules: configuration, I/O, validation and theming."""

from __future__ import annotations

import importlib
from typing import Any

from .io import ensure_directory_exists, load_config, load_data, save_data

_LAZY_THEMING = ("apply_style", "get_color_palette", "get_matplotlib_style", "get_plotly_template")

__all__ = [
    "apply_style",
    "ensure_directory_exists",
    "get_color_palette",
    "get_matplotlib_style",
    "get_plotly_template",
    "load_config",
    "load_data",
    "save_data",
]


def __getattr__(name: str) -> Any:
    # Theming imports Matplotlib/Plotly; load it only when actually needed.
    if name in _LAZY_THEMING:
        value = getattr(importlib.import_module(f"{__name__}.theming"), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
