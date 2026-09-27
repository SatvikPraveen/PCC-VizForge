"""Configuration composition: deep merging and ``key.path=value`` overrides.

Experiments are specified by a base YAML file plus a list of command-line
overrides (in the spirit of Hydra/OmegaConf, but dependency-free)::

    pcc-vizforge run quakes --set data_generation.b_value=0.8 \\
                            --set data_generation.n_earthquakes=5000
"""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from typing import Any

import yaml

from pcc_vizforge.exceptions import InvalidConfigurationError

__all__ = ["apply_overrides", "deep_merge", "parse_override", "set_by_path"]


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into a deep copy of ``base``."""
    merged = copy.deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def parse_override(expr: str) -> tuple[list[str], Any]:
    """Parse ``"a.b.c=value"`` into (``["a", "b", "c"]``, parsed value).

    The right-hand side is parsed as YAML, so ``3``, ``0.5``, ``true``,
    ``[1, 2]`` and ``{a: 1}`` all become the corresponding Python objects.
    """
    if "=" not in expr:
        raise InvalidConfigurationError(f"Override must look like key.path=value, got {expr!r}")
    key, raw = expr.split("=", 1)
    path = [part for part in key.strip().split(".") if part]
    if not path:
        raise InvalidConfigurationError(f"Empty key in override {expr!r}")
    try:
        value = yaml.safe_load(raw) if raw.strip() else None
    except yaml.YAMLError as exc:
        raise InvalidConfigurationError(f"Cannot parse value in override {expr!r}: {exc}") from exc
    return path, value


def set_by_path(config: dict[str, Any], path: list[str], value: Any) -> None:
    """Set ``config[path[0]]...[path[-1]] = value``, creating mappings as needed."""
    node = config
    for part in path[:-1]:
        child = node.get(part)
        if child is None:
            child = node[part] = {}
        elif not isinstance(child, dict):
            raise InvalidConfigurationError(
                f"Cannot set {'.'.join(path)}: {part!r} is not a mapping"
            )
        node = child
    node[path[-1]] = value


def apply_overrides(config: Mapping[str, Any], overrides: Iterable[str]) -> dict[str, Any]:
    """Return a copy of ``config`` with each ``key.path=value`` override applied."""
    result = copy.deepcopy(dict(config))
    for expr in overrides:
        path, value = parse_override(expr)
        set_by_path(result, path, value)
    return result
