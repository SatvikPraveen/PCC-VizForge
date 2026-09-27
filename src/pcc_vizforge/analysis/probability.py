"""Exact discrete distributions and convergence diagnostics for dice experiments.

The distribution of the sum of ``n`` independent dice is the ``n``-fold
convolution of the single-die PMF, i.e. the coefficients of the probability
generating function :math:`G(z)^n`. Convolution is O(n²s) and exact up to
floating-point rounding (or exactly, with :func:`sum_counts_fair`, in
integer arithmetic), replacing the exponential-time recursive enumeration.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import stats

from pcc_vizforge.exceptions import InvalidParameterError

__all__ = [
    "die_moments",
    "face_pmf",
    "running_mean_band",
    "sum_counts_fair",
    "sum_pmf",
]


def face_pmf(sides: int, weights: Sequence[float] | None = None) -> NDArray[np.float64]:
    """Normalised face probabilities for a (possibly loaded) die."""
    if sides < 2:
        raise InvalidParameterError(f"A die needs at least 2 sides, got {sides}")
    if weights is None:
        return np.full(sides, 1.0 / sides)
    w = np.asarray(weights, dtype=float)
    if w.shape != (sides,):
        raise InvalidParameterError(f"weights must have length {sides}, got {w.size}")
    if np.any(w < 0) or w.sum() <= 0:
        raise InvalidParameterError("weights must be non-negative and not all zero")
    return w / w.sum()


def sum_pmf(
    n_dice: int, sides: int, weights: Sequence[float] | None = None
) -> tuple[NDArray[np.int64], NDArray[np.float64]]:
    """Exact PMF of the sum of ``n_dice`` i.i.d. dice.

    Returns:
        ``(support, pmf)`` with ``support = n_dice … n_dice*sides``.
    """
    if n_dice < 1:
        raise InvalidParameterError(f"n_dice must be >= 1, got {n_dice}")
    p = face_pmf(sides, weights)
    pmf = np.array([1.0])
    # Exponentiation by squaring keeps the number of convolutions O(log n).
    base, k = p, n_dice
    while k:
        if k & 1:
            pmf = np.convolve(pmf, base)
        k >>= 1
        if k:
            base = np.convolve(base, base)
    pmf = np.clip(pmf, 0.0, None)
    pmf /= pmf.sum()
    support = np.arange(n_dice, n_dice * sides + 1, dtype=np.int64)
    return support, pmf


def sum_counts_fair(n_dice: int, sides: int) -> list[int]:
    """Exact integer number of outcomes for each sum of fair dice.

    Uses arbitrary-precision Python integers; ``sum(result) == sides**n_dice``.
    """
    if n_dice < 1 or sides < 2:
        raise InvalidParameterError("need n_dice >= 1 and sides >= 2")
    counts = [1]
    for _ in range(n_dice):
        new = [0] * (len(counts) + sides - 1)
        for i, c in enumerate(counts):
            if c:
                for f in range(sides):
                    new[i + f] += c
        counts = new
    return counts


def die_moments(
    sides: int, weights: Sequence[float] | None = None
) -> tuple[float, float]:
    """Mean and variance of a single die (faces 1..sides)."""
    p = face_pmf(sides, weights)
    faces = np.arange(1, sides + 1)
    mean = float(np.dot(faces, p))
    var = float(np.dot((faces - mean) ** 2, p))
    return mean, var


def running_mean_band(
    n: ArrayLike, mean: float, var: float, confidence: float = 0.95
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Pointwise CLT band for the running mean of i.i.d. draws.

    Returns ``(lower, upper)`` such that for each ``n`` the sample mean lies
    in the band with probability ≈ ``confidence``.
    """
    n_arr = np.asarray(n, dtype=float)
    z = stats.norm.ppf(0.5 + confidence / 2)
    half = z * np.sqrt(var / n_arr)
    return mean - half, mean + half
