"""Random-walk and anomalous-diffusion generator.

Supported models (``model`` parameter), all normalised so that the
single-step mean-squared displacement equals ``step_size**2``:

``lattice``
    Simple random walk on :math:`\\mathbb{Z}^d`: each step moves
    ``±step_size`` along one uniformly chosen axis. MSD(t) = a² t.
``gaussian``
    Discretised Brownian motion with i.i.d. isotropic Gaussian increments
    :math:`\\Delta r \\sim N(0, (a^2/d) I_d)`. MSD(t) = a² t.
``correlated``
    Persistent (velocity-autoregressive) walk,
    :math:`v_t = \\rho v_{t-1} + \\sqrt{1-\\rho^2}\\,\\xi_t`, started in
    stationarity. Ballistic for t ≪ 1/(1-ρ), diffusive with enhanced
    coefficient (1+ρ)/(1-ρ) for t ≫ 1/(1-ρ).
``levy``
    Lévy flight with isotropic directions and Pareto step lengths,
    :math:`P(L > \\ell) = (\\ell/a)^{-\\alpha}`, :math:`0 < \\alpha \\le 2`.
    For α < 2 the MSD diverges (super-diffusion).
``fbm``
    Fractional Brownian motion with Hurst exponent H, simulated exactly by
    circulant embedding of fractional Gaussian noise (Davies & Harte, 1987;
    Dietrich & Newsam, 1997). MSD(t) = a² t^{2H}: sub-diffusive for H < ½,
    super-diffusive for H > ½.

References
----------
Davies, R. B. & Harte, D. S. (1987). Tests for Hurst effect. *Biometrika*
    74(1), 95-101.
Metzler, R. & Klafter, J. (2000). The random walk's guide to anomalous
    diffusion. *Phys. Rep.* 339, 1-77.
Mandelbrot, B. B. & Van Ness, J. W. (1968). Fractional Brownian motions,
    fractional noises and applications. *SIAM Rev.* 10(4), 422-437.
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Sequence
from typing import Any, ClassVar, Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from pcc_vizforge.constants import MAX_DATA_POINTS, VALID_DIMENSIONS
from pcc_vizforge.exceptions import (
    DataGenerationError,
    DataShapeError,
    InvalidParameterError,
)
from pcc_vizforge.generators.base import BaseGenerator, GeneratorParams
from pcc_vizforge.utils.io import get_data_directory, save_data

logger = logging.getLogger(__name__)

WalkModel = Literal["lattice", "gaussian", "correlated", "levy", "fbm"]
WALK_MODELS: tuple[str, ...] = ("lattice", "gaussian", "correlated", "levy", "fbm")
AXES: tuple[str, ...] = ("x_position", "y_position", "z_position")

__all__ = [
    "WALK_MODELS",
    "RandomWalkGenerator",
    "RandomWalkParams",
    "fractional_gaussian_noise",
    "simulate_increments",
    "theoretical_msd",
]


@dataclasses.dataclass(frozen=True)
class RandomWalkParams(GeneratorParams):
    """Parameters of the random-walk generator."""

    n_steps: int = 1000
    n_walks: int = 5
    step_size: float = 1.0
    dimensions: int = 1
    model: str = "lattice"
    hurst: float = 0.5
    levy_alpha: float = 1.5
    persistence: float = 0.0

    def validate(self) -> None:
        super().validate()
        for name in ("n_steps", "n_walks", "dimensions"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise InvalidParameterError(f"{name} must be an integer, got {value!r}")
        if self.n_steps < 1 or self.n_walks < 1:
            raise InvalidParameterError("n_steps and n_walks must be >= 1")
        if self.n_steps * self.n_walks > MAX_DATA_POINTS:
            raise InvalidParameterError(
                f"n_steps * n_walks = {self.n_steps * self.n_walks} exceeds {MAX_DATA_POINTS}"
            )
        if self.dimensions not in VALID_DIMENSIONS:
            raise InvalidParameterError(
                f"dimensions must be one of {VALID_DIMENSIONS}, got {self.dimensions}"
            )
        if not self.step_size > 0:
            raise InvalidParameterError(f"step_size must be > 0, got {self.step_size}")
        if self.model not in WALK_MODELS:
            raise InvalidParameterError(
                f"model must be one of {WALK_MODELS}, got {self.model!r}"
            )
        if not 0 < self.hurst < 1:
            raise InvalidParameterError(f"hurst must be in (0, 1), got {self.hurst}")
        if not 0 < self.levy_alpha <= 2:
            raise InvalidParameterError(
                f"levy_alpha must be in (0, 2], got {self.levy_alpha}"
            )
        if not -1 < self.persistence < 1:
            raise InvalidParameterError(
                f"persistence must be in (-1, 1), got {self.persistence}"
            )


# --------------------------------------------------------------------------- #
# Increment samplers (pure functions; shape = (n_walks, n_steps, d))
# --------------------------------------------------------------------------- #
def _unit_vectors(
    rng: np.random.Generator, shape: tuple[int, int], d: int
) -> NDArray[np.float64]:
    """Isotropic random unit vectors (±1 in one dimension)."""
    if d == 1:
        return rng.choice(np.array([-1.0, 1.0]), size=(*shape, 1))
    v = rng.standard_normal((*shape, d))
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def fractional_gaussian_noise(
    rng: np.random.Generator, n: int, hurst: float, size: int = 1
) -> NDArray[np.float64]:
    """Exact unit-variance fractional Gaussian noise via Davies-Harte.

    Returns an array of shape ``(size, n)``; cumulative sums are fBm paths
    with :math:`\\operatorname{Var}[B_H(t)] = t^{2H}`.
    """
    if n == 1:
        return rng.standard_normal((size, 1))
    k = np.arange(n + 1, dtype=float)
    two_h = 2.0 * hurst
    gamma = 0.5 * (np.abs(k + 1) ** two_h - 2 * k**two_h + np.abs(k - 1) ** two_h)
    row = np.concatenate([gamma, gamma[-2:0:-1]])  # circulant first row, length 2n
    eig = np.fft.fft(row).real
    if eig.min() < -1e-8 * eig.max():  # pragma: no cover - cannot happen for fGn
        raise DataGenerationError("Circulant embedding is not non-negative definite")
    eig = np.clip(eig, 0.0, None)
    m = row.size
    z = rng.standard_normal((size, m)) + 1j * rng.standard_normal((size, m))
    y = np.fft.fft(np.sqrt(eig / m) * z, axis=-1)
    return y.real[:, :n]


def simulate_increments(
    params: RandomWalkParams, rng: np.random.Generator
) -> NDArray[np.float64]:
    """Draw displacement increments of shape ``(n_walks, n_steps, dimensions)``."""
    w, n, d, a = (
        params.n_walks,
        params.n_steps,
        params.dimensions,
        float(params.step_size),
    )
    model = params.model

    if model == "lattice":
        axis = rng.integers(0, d, size=(w, n))
        sign = rng.choice(np.array([-1.0, 1.0]), size=(w, n))
        inc = np.zeros((w, n, d))
        np.put_along_axis(inc, axis[..., None], (sign * a)[..., None], axis=-1)
        return inc

    if model == "gaussian":
        return rng.standard_normal((w, n, d)) * (a / np.sqrt(d))

    if model == "correlated":
        rho = params.persistence
        xi = rng.standard_normal((w, n, d)) * (a / np.sqrt(d))
        v = np.empty_like(xi)
        v[:, 0] = xi[:, 0]  # stationary start: Var = a²/d per axis
        scale = np.sqrt(1.0 - rho**2)
        for t in range(1, n):
            v[:, t] = rho * v[:, t - 1] + scale * xi[:, t]
        return v

    if model == "levy":
        # Pareto(α) lengths with minimum a; scale so that α=2 has E[L²]=∞ limit.
        u = rng.random((w, n))
        lengths = a * (1.0 - u) ** (-1.0 / params.levy_alpha)
        return _unit_vectors(rng, (w, n), d) * lengths[..., None]

    if model == "fbm":
        noise = fractional_gaussian_noise(rng, n, params.hurst, size=w * d)
        return noise.reshape(w, d, n).transpose(0, 2, 1) * (a / np.sqrt(d))

    raise InvalidParameterError(f"Unknown model {model!r}")  # pragma: no cover


def theoretical_msd(
    params: RandomWalkParams, t: NDArray[np.float64] | Sequence[float]
) -> NDArray[np.float64]:
    """Exact ensemble MSD :math:`\\langle |r(t)|^2 \\rangle` for the model.

    Returns ``inf`` for Lévy flights (α ≤ 2), whose MSD diverges.
    """
    t = np.asarray(t, dtype=float)
    a2 = float(params.step_size) ** 2
    if params.model in ("lattice", "gaussian"):
        return a2 * t
    if params.model == "fbm":
        return a2 * t ** (2 * params.hurst)
    if params.model == "correlated":
        rho = params.persistence
        return a2 * (
            t * (1 + rho) / (1 - rho) - 2 * rho * (1 - rho**t) / (1 - rho) ** 2
        )
    if params.model == "levy":
        # Pareto lengths with alpha <= 2 have an infinite second moment.
        return np.full_like(t, np.inf)
    raise InvalidParameterError(f"Unknown model {params.model!r}")  # pragma: no cover


class RandomWalkGenerator(BaseGenerator[RandomWalkParams]):
    """Generator for ensembles of random walks.

    The output is a long-format DataFrame with one row per (walk, step):

    ==================  ======================================================
    ``walk_id``         walk index, 0 … n_walks-1
    ``step``            time t = 1 … n_steps (position *after* t steps)
    ``x/y/z_position``  Cartesian coordinates (``y`` is 0 in 1-D; ``z`` only
                        present in 3-D)
    ``displacement``    Euclidean distance from the origin, |r(t)|
    ``position``        signed x in 1-D, otherwise ``displacement``
    ``step_length``     |r(t) - r(t-1)|
    ``path_length``     cumulative distance travelled, Σ step_length
    ==================  ======================================================
    """

    domain: ClassVar[str] = "random_walk"
    params_cls: ClassVar[type[GeneratorParams]] = RandomWalkParams
    output_filename: ClassVar[str] = "random_walk_data.csv"

    def __init__(self, config_name: str | None = "random_walk", **kwargs: Any) -> None:
        logger.info("Initializing RandomWalkGenerator with config: %s", config_name)
        super().__init__(config_name, **kwargs)

    def simulate_positions(
        self, rng: np.random.Generator, params: RandomWalkParams | None = None
    ) -> NDArray[np.float64]:
        """Return positions as an array of shape ``(n_walks, n_steps, d)``."""
        params = params or self.params
        return np.cumsum(simulate_increments(params, rng), axis=1)

    def _simulate(
        self, params: RandomWalkParams, rng: np.random.Generator
    ) -> pd.DataFrame:
        positions = self.simulate_positions(rng, params)
        return positions_to_frame(positions)

    # ------------------------------------------------------------------ #
    # Back-compatible convenience API
    # ------------------------------------------------------------------ #
    def generate_multiple_scenarios(
        self, scenarios: list[dict[str, Any]], save_to_file: bool = True
    ) -> dict[str, pd.DataFrame]:
        """Generate several parameter scenarios (each dict overrides the config)."""
        results: dict[str, pd.DataFrame] = {}
        original = dict(self.data_config)
        try:
            for i, scenario in enumerate(scenarios):
                scenario = dict(scenario)
                name = scenario.pop("name", f"scenario_{i}")
                self.data_config.clear()
                self.data_config.update({**original, **scenario})
                try:
                    df = self.generate()
                except Exception as exc:
                    raise DataGenerationError(
                        f"Failed to generate scenario {name}: {exc}"
                    ) from exc
                df["scenario"] = name
                results[name] = df
                if save_to_file:
                    save_data(
                        df,
                        get_data_directory(self.domain) / f"random_walk_{name}.csv",
                        "csv",
                    )
        finally:
            self.data_config.clear()
            self.data_config.update(original)
        return results

    def calculate_statistics(self, data: pd.DataFrame) -> dict[str, float]:
        """Summary statistics of an ensemble (see also :mod:`analysis.diffusion`)."""
        if data.empty:
            raise DataShapeError("Cannot calculate statistics on empty DataFrame")
        if "position" not in data.columns or "walk_id" not in data.columns:
            raise DataShapeError(
                "DataFrame must contain 'position' and 'walk_id' columns"
            )
        g = data.groupby("walk_id")
        final = g["position"].last()
        max_pos, min_pos = g["position"].max(), g["position"].min()
        disp = g["displacement"].last() if "displacement" in data else final.abs()
        stats: dict[str, float] = {
            "mean_final_position": float(final.mean()),
            "std_final_position": float(final.std(ddof=1)) if len(final) > 1 else 0.0,
            "max_final_position": float(final.max()),
            "min_final_position": float(final.min()),
            "mean_max_excursion": float(max_pos.mean()),
            "mean_min_excursion": float(min_pos.mean()),
            "mean_total_excursion": float((max_pos - min_pos).mean()),
            "mean_squared_displacement": float((disp**2).mean()),
            "mean_step_size": float(data["step_length"].mean())
            if "step_length" in data
            else float("nan"),
            "total_steps": len(data),
            "n_walks": int(data["walk_id"].nunique()),
        }
        return stats

    def get_walk_summary(
        self, data: pd.DataFrame, walk_id: int
    ) -> dict[str, float | int]:
        """Summary statistics for a single walk."""
        walk = data[data["walk_id"] == walk_id]
        if walk.empty:
            raise InvalidParameterError(f"Walk ID {walk_id} not found in data")
        return {
            "walk_id": walk_id,
            "n_steps": len(walk),
            "final_position": float(walk["position"].iloc[-1]),
            "max_position": float(walk["position"].max()),
            "min_position": float(walk["position"].min()),
            "total_distance": float(walk["path_length"].iloc[-1]),
            "mean_step_size": float(walk["step_length"].mean()),
            "net_displacement": float(walk["displacement"].iloc[-1]),
        }


def positions_to_frame(positions: NDArray[np.float64]) -> pd.DataFrame:
    """Convert a ``(n_walks, n_steps, d)`` array into the tidy long format."""
    if positions.ndim != 3 or positions.shape[-1] not in VALID_DIMENSIONS:
        raise DataShapeError(
            f"positions must have shape (walks, steps, 1..3), got {positions.shape}"
        )
    w, n, d = positions.shape
    steps = np.diff(positions, axis=1, prepend=np.zeros((w, 1, d)))
    step_length = np.linalg.norm(steps, axis=-1)
    displacement = np.linalg.norm(positions, axis=-1)

    data: dict[str, Any] = {
        "walk_id": np.repeat(np.arange(w), n),
        "step": np.tile(np.arange(1, n + 1), w),
    }
    for k in range(d):
        data[AXES[k]] = positions[..., k].ravel()
    if d == 1:
        data["y_position"] = np.zeros(w * n)
    data["displacement"] = displacement.ravel()
    data["position"] = positions[..., 0].ravel() if d == 1 else data["displacement"]
    data["step_length"] = step_length.ravel()
    data["path_length"] = np.cumsum(step_length, axis=1).ravel()
    df = pd.DataFrame(data)
    # Legacy column names kept for backwards compatibility.
    df["step_size"] = df["step_length"]
    df["cumulative_distance"] = df["path_length"]
    return df


def frame_to_positions(df: pd.DataFrame) -> NDArray[np.float64]:
    """Inverse of :func:`positions_to_frame` -> ``(n_walks, n_steps, d)``."""
    dims = df.attrs.get("provenance", {}).get("params", {}).get("dimensions")
    if dims is None:
        if "z_position" in df.columns:
            dims = 3
        elif "y_position" in df.columns and not np.allclose(df["y_position"], 0):
            dims = 2
        else:
            dims = 1
    axes = list(AXES[:dims])
    df = df.sort_values(["walk_id", "step"])
    w = df["walk_id"].nunique()
    n = len(df) // w
    if w * n != len(df):
        raise DataShapeError("All walks must have the same number of steps")
    return df[axes].to_numpy().reshape(w, n, len(axes))
