"""Common machinery shared by all synthetic-data generators.

A generator is configured by a YAML mapping (bundled or user-supplied) whose
``data_generation`` section is parsed into a frozen, validated parameter
dataclass *at generation time*. Keeping the raw mapping (``data_config``) as
the mutable source of truth means that callers -- and parameter sweeps -- can
tweak it in place, while the simulation itself only ever sees validated,
typed parameters.

Every call to :meth:`BaseGenerator.generate` draws from an explicit
:class:`numpy.random.Generator`. The seed actually used is stored on the
generator (``last_seed``) and in ``DataFrame.attrs["provenance"]`` so that any
dataset can be traced back to, and regenerated from, its exact inputs.
"""

from __future__ import annotations

import dataclasses
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, ClassVar, Generic, TypeVar

import numpy as np
import pandas as pd

from pcc_vizforge._version import __version__
from pcc_vizforge.exceptions import (
    DataGenerationError,
    InvalidConfigurationError,
    InvalidParameterError,
)
from pcc_vizforge.provenance import config_hash
from pcc_vizforge.rng import SeedLike, make_rng, resolve_seed
from pcc_vizforge.utils.config import apply_overrides, deep_merge
from pcc_vizforge.utils.io import get_data_directory, load_config, save_data

logger = logging.getLogger(__name__)

__all__ = ["BaseGenerator", "GeneratorParams"]


@dataclasses.dataclass(frozen=True)
class GeneratorParams:
    """Base class for validated generator parameters.

    Subclasses declare typed fields and implement :meth:`validate`. Unknown
    keys in the configuration are rejected so that typos (``n_step`` instead
    of ``n_steps``) fail loudly instead of being silently ignored.
    """

    random_seed: int | None = None

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> GeneratorParams:
        names = {f.name for f in dataclasses.fields(cls)}
        unknown = sorted(set(mapping) - names)
        if unknown:
            raise InvalidConfigurationError(
                f"Unknown {cls.__name__} parameter(s): {unknown}. Valid: {sorted(names)}"
            )
        kwargs = {}
        for f in dataclasses.fields(cls):
            if f.name in mapping:
                value = mapping[f.name]
                # YAML gives lists; store as tuples to keep params hashable/frozen.
                if isinstance(value, list):
                    value = tuple(tuple(v) if isinstance(v, list) else v for v in value)
                kwargs[f.name] = value
        params = cls(**kwargs)
        params.validate()
        return params

    def validate(self) -> None:
        """Raise :class:`InvalidParameterError` if parameters are inconsistent."""
        if self.random_seed is not None:
            resolve_seed(self.random_seed)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


P = TypeVar("P", bound=GeneratorParams)


class BaseGenerator(ABC, Generic[P]):
    """Abstract seeded generator producing a tidy :class:`pandas.DataFrame`."""

    #: Domain key; also the bundled config name and output sub-directory.
    domain: ClassVar[str]
    #: Parameter dataclass parsed from ``config["data_generation"]``.
    params_cls: ClassVar[type[GeneratorParams]]
    #: Default output file name when ``save_to_file=True``.
    output_filename: ClassVar[str]

    def __init__(
        self,
        config_name: str | Path | None = None,
        *,
        config: Mapping[str, Any] | None = None,
        overrides: Iterable[str] = (),
        **params: Any,
    ) -> None:
        """Create a generator.

        Args:
            config_name: Bundled config name or path to a YAML file. Defaults
                to the generator's own domain config.
            config: A full configuration mapping (takes precedence over
                ``config_name``).
            overrides: ``key.path=value`` strings applied on top.
            **params: Direct overrides of ``data_generation`` parameters.
        """
        base = (
            dict(config)
            if config is not None
            else load_config(config_name or self.domain)
        )
        base = apply_overrides(base, overrides)
        if params:
            base = deep_merge(base, {"data_generation": params})
        if "data_generation" not in base or not isinstance(
            base["data_generation"], dict
        ):
            raise InvalidConfigurationError(
                f"{type(self).__name__} config needs a 'data_generation' mapping"
            )
        self.config: dict[str, Any] = base
        self.data_config: dict[str, Any] = base["data_generation"]
        self.last_seed: int | None = None
        # Fail fast on an invalid configuration.
        self.params  # noqa: B018

    # ------------------------------------------------------------------ #
    @property
    def params(self) -> P:
        """Validated parameters parsed from the *current* ``data_config``."""
        try:
            return self.params_cls.from_mapping(self.data_config)  # type: ignore[return-value]
        except (TypeError, ValueError) as exc:
            raise InvalidParameterError(
                f"Invalid {self.domain} parameters: {exc}"
            ) from exc

    def generate(
        self,
        save_to_file: bool = False,
        *,
        seed: SeedLike = None,
        output_path: str | Path | None = None,
    ) -> pd.DataFrame:
        """Simulate one dataset.

        Args:
            save_to_file: Persist the data as CSV under the data directory.
            seed: Seed or Generator overriding ``random_seed`` in the config.
            output_path: Explicit CSV path (implies ``save_to_file``).

        Returns:
            Tidy DataFrame; ``df.attrs["provenance"]`` records domain, seed,
            parameters, config hash and package version.
        """
        params = self.params
        used_seed: int | None
        seed_info: Any
        if isinstance(seed, np.random.Generator):
            rng, used_seed, seed_info = seed, None, "external-generator"
        elif isinstance(seed, np.random.SeedSequence):
            rng, used_seed = make_rng(seed), None
            seed_info = {"entropy": seed.entropy, "spawn_key": list(seed.spawn_key)}
        else:
            used_seed = resolve_seed(seed if seed is not None else params.random_seed)
            rng, seed_info = make_rng(used_seed), used_seed
        self.last_seed = used_seed
        logger.info("Generating %s data (seed=%s)", self.domain, seed_info)

        try:
            df = self._simulate(params, rng)
        except (InvalidParameterError, DataGenerationError):
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise DataGenerationError(
                f"{self.domain} generation failed: {exc}"
            ) from exc

        df.attrs["provenance"] = {
            "domain": self.domain,
            "seed": seed_info,
            "params": params.to_dict(),
            "config_sha256": config_hash(self.data_config),
            "pcc_vizforge": __version__,
        }

        if save_to_file or output_path is not None:
            path = (
                Path(output_path)
                if output_path is not None
                else get_data_directory(self.domain) / self.output_filename
            )
            save_data(df, path, "csv")
            logger.info("Saved %s data to %s", self.domain, path)
        return df

    def generate_replicates(
        self, n: int, seed: int | None = None
    ) -> list[pd.DataFrame]:
        """Generate ``n`` independent replicates from spawned RNG streams."""
        from pcc_vizforge.rng import spawn_seeds

        root = resolve_seed(seed if seed is not None else self.params.random_seed)
        out = []
        for i, ss in enumerate(spawn_seeds(root, n)):
            df = self.generate(seed=ss)
            df.attrs["provenance"].update({"root_seed": root, "replicate": i})
            out.append(df)
        return out

    @abstractmethod
    def _simulate(self, params: P, rng: np.random.Generator) -> pd.DataFrame:
        """Draw one dataset. Must use only ``rng`` for randomness."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.params!r})"
