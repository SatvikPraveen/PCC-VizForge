"""Reproducible random-number management.

Every stochastic routine in PCC-VizForge takes an explicit
:class:`numpy.random.Generator` rather than touching NumPy's global state.
This makes results independent of call order, safe under parallelism, and
exactly reproducible from a single integer seed that is recorded in the run
manifest (see :mod:`pcc_vizforge.provenance`).

Independent streams for Monte Carlo replicates are derived with
:meth:`numpy.random.SeedSequence.spawn`, which guarantees statistically
independent, non-overlapping sequences (O'Neill, 2014; NumPy NEP 19).
"""

from __future__ import annotations

import secrets
from typing import Union

import numpy as np

from pcc_vizforge.exceptions import InvalidParameterError

SeedLike = Union[int, np.integer, np.random.SeedSequence, np.random.Generator, None]

__all__ = ["SeedLike", "make_rng", "resolve_seed", "spawn_rngs", "spawn_seeds"]


def resolve_seed(seed: int | np.integer | None) -> int:
    """Return a concrete, non-negative integer seed.

    If ``seed`` is ``None`` a fresh 63-bit seed is drawn from the operating
    system's entropy pool. Returning it (instead of seeding implicitly) lets
    callers record the seed so that an "unseeded" run can still be replayed.
    """
    if seed is None:
        return secrets.randbits(63)
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise InvalidParameterError(f"Seed must be a non-negative integer, got {seed!r}")
    if seed < 0:
        raise InvalidParameterError(f"Seed must be non-negative, got {seed}")
    return int(seed)


def make_rng(seed: SeedLike = None) -> np.random.Generator:
    """Create a PCG64 :class:`~numpy.random.Generator` from ``seed``.

    Passing an existing ``Generator`` returns it unchanged, so functions can
    accept either a seed or a generator without re-seeding.
    """
    if isinstance(seed, np.random.Generator):
        return seed
    if isinstance(seed, np.random.SeedSequence):
        return np.random.Generator(np.random.PCG64(seed))
    return np.random.Generator(np.random.PCG64(resolve_seed(seed)))


def spawn_seeds(seed: int | np.integer | None, n: int) -> list[np.random.SeedSequence]:
    """Derive ``n`` independent child seed sequences from a root seed."""
    if n < 0:
        raise InvalidParameterError(f"n must be non-negative, got {n}")
    return np.random.SeedSequence(resolve_seed(seed)).spawn(n)


def spawn_rngs(seed: int | np.integer | None, n: int) -> list[np.random.Generator]:
    """Derive ``n`` statistically independent generators from a root seed."""
    return [make_rng(ss) for ss in spawn_seeds(seed, n)]
