"""Provenance capture for reproducible computational experiments.

A :class:`RunManifest` records everything needed to reproduce -- or audit --
an artefact: the exact configuration (and its hash), the RNG seed, package
and dependency versions, the platform, the git revision of the source tree
(when available) and SHA-256 digests of every output file.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

from pcc_vizforge._version import __version__

__all__ = [
    "RunManifest",
    "canonical_json",
    "collect_environment",
    "config_hash",
    "file_sha256",
    "git_revision",
]

TRACKED_PACKAGES: tuple[str, ...] = (
    "numpy",
    "scipy",
    "pandas",
    "matplotlib",
    "plotly",
    "pyyaml",
)


def _json_default(obj: Any) -> Any:
    """Serialise NumPy scalars/arrays, paths and datetimes for JSON."""
    try:
        import numpy as np

        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:  # pragma: no cover
        pass
    if isinstance(obj, (Path, datetime)):
        return str(obj)
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")


def canonical_json(obj: Any) -> str:
    """Deterministic JSON encoding (sorted keys, no whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_json_default)


def config_hash(config: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical JSON encoding of ``config``."""
    return hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest()


def file_sha256(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """Stream a file through SHA-256."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision(path: str | Path | None = None) -> dict[str, Any] | None:
    """Return the current commit and dirty flag, or ``None`` outside git."""
    cwd = Path(path) if path is not None else Path(__file__).resolve().parent
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return {"commit": commit, "dirty": bool(status.strip())}


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def collect_environment(packages: Iterable[str] = TRACKED_PACKAGES) -> dict[str, Any]:
    """Snapshot interpreter, platform and dependency versions."""
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "pcc_vizforge": __version__,
        "packages": {name: _package_version(name) for name in packages},
    }


@dataclass
class RunManifest:
    """Machine-readable record of a single experiment run."""

    domain: str
    seed: int
    config: dict[str, Any]
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    environment: dict[str, Any] = field(default_factory=collect_environment)
    git: dict[str, Any] | None = field(default_factory=git_revision)
    outputs: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def config_sha256(self) -> str:
        return config_hash(self.config)

    def register_output(self, path: str | Path, root: str | Path | None = None) -> None:
        """Record ``path`` (relative to ``root`` if given) with its SHA-256."""
        p = Path(path)
        key = str(p.relative_to(root)) if root is not None else str(p)
        self.outputs[key] = file_sha256(p)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["config_sha256"] = self.config_sha256
        data["schema_version"] = 1
        return data

    def write(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True, default=_json_default)
            + "\n",
            encoding="utf-8",
        )
        return path

    @classmethod
    def read(cls, path: str | Path) -> RunManifest:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data.pop("config_sha256", None)
        data.pop("schema_version", None)
        return cls(**data)
