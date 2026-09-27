"""Dice-roll simulation with exact reference distributions.

Rolls ``n_dice`` independent dice with ``dice_sides`` faces ``n_rolls`` times.
Dice may be loaded via ``weights``. Analysis methods compare the empirical
face and sum frequencies against the exact theoretical PMFs
(:mod:`pcc_vizforge.analysis.probability`) with Pearson chi-square tests and
check serial independence with Wald-Wolfowitz runs tests.
"""

from __future__ import annotations

import dataclasses
from typing import Any, ClassVar

import numpy as np
import pandas as pd

from pcc_vizforge.analysis.inference import chi_square_gof, runs_test
from pcc_vizforge.analysis.probability import die_moments, face_pmf, sum_pmf
from pcc_vizforge.constants import MAX_DATA_POINTS
from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.generators.base import BaseGenerator, GeneratorParams

__all__ = ["DiceGenerator", "DiceParams"]


@dataclasses.dataclass(frozen=True)
class DiceParams(GeneratorParams):
    """Parameters of the dice generator."""

    n_rolls: int = 1000
    n_dice: int = 2
    dice_sides: int = 6
    weights: tuple[float, ...] | None = None

    def validate(self) -> None:
        super().validate()
        for name in ("n_rolls", "n_dice", "dice_sides"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, np.integer))
                or value < 1
            ):
                raise InvalidParameterError(
                    f"{name} must be a positive integer, got {value!r}"
                )
        if self.dice_sides < 2:
            raise InvalidParameterError("dice_sides must be >= 2")
        if self.n_rolls * self.n_dice > MAX_DATA_POINTS:
            raise InvalidParameterError("n_rolls * n_dice exceeds MAX_DATA_POINTS")
        face_pmf(self.dice_sides, self.weights)  # validates weights


class DiceGenerator(BaseGenerator[DiceParams]):
    """Generator for dice-roll experiments.

    Output: one row per (roll, die) with columns ``roll_id``, ``die_id``,
    ``die_value``, ``roll_sum``, ``roll_sequence`` (1-based), ``is_max_value``,
    ``is_min_value``, ``cumulative_sum``, ``rolling_avg`` (running mean of
    roll sums), ``all_equal`` and ``is_doubles`` (two dice showing the same
    face).
    """

    domain: ClassVar[str] = "dice"
    params_cls: ClassVar[type[GeneratorParams]] = DiceParams
    output_filename: ClassVar[str] = "dice_data.csv"

    def __init__(self, config_name: str | None = "dice", **kwargs: Any) -> None:
        super().__init__(config_name, **kwargs)

    def _simulate(self, params: DiceParams, rng: np.random.Generator) -> pd.DataFrame:
        r, n, s = params.n_rolls, params.n_dice, params.dice_sides
        if params.weights is None:
            values = rng.integers(1, s + 1, size=(r, n))
        else:
            values = rng.choice(
                np.arange(1, s + 1), size=(r, n), p=face_pmf(s, params.weights)
            )
        sums = values.sum(axis=1)
        all_equal = (
            (values == values[:, :1]).all(axis=1) if n > 1 else np.zeros(r, dtype=bool)
        )
        roll_ids = np.arange(r)

        df = pd.DataFrame(
            {
                "roll_id": np.repeat(roll_ids, n),
                "die_id": np.tile(np.arange(n), r),
                "die_value": values.ravel(),
                "roll_sum": np.repeat(sums, n),
                "roll_sequence": np.repeat(roll_ids + 1, n),
            }
        )
        df["is_max_value"] = df["die_value"] == s
        df["is_min_value"] = df["die_value"] == 1
        df["cumulative_sum"] = np.repeat(np.cumsum(sums), n)
        df["rolling_avg"] = np.repeat(np.cumsum(sums) / (roll_ids + 1), n)
        df["all_equal"] = np.repeat(all_equal, n)
        df["is_doubles"] = df["all_equal"] & (n == 2)
        return df

    # ------------------------------------------------------------------ #
    # Analysis
    # ------------------------------------------------------------------ #
    @staticmethod
    def roll_sums(data: pd.DataFrame) -> pd.Series:
        """One sum per roll, ordered by ``roll_id``."""
        return data.groupby("roll_id", sort=True)["roll_sum"].first()

    def theoretical_sum_distribution(self) -> pd.Series:
        """Exact PMF of the roll sum under the configured (possibly loaded) dice."""
        p = self.params
        support, pmf = sum_pmf(p.n_dice, p.dice_sides, p.weights)
        return pd.Series(pmf, index=pd.Index(support, name="sum"), name="probability")

    def calculate_probabilities(self, data: pd.DataFrame) -> dict[str, Any]:
        """Observed vs. theoretical frequencies with goodness-of-fit tests.

        The face test is against the *configured* face distribution, so for
        loaded dice it tests the simulator; use :meth:`fairness_test` to test
        whether the dice are fair.
        """
        p = self.params
        sums = self.roll_sums(data)
        theo = self.theoretical_sum_distribution()
        obs_counts = sums.value_counts().reindex(theo.index, fill_value=0)
        faces = np.arange(1, p.dice_sides + 1)
        face_counts = data["die_value"].value_counts().reindex(faces, fill_value=0)

        sum_test = chi_square_gof(obs_counts.to_numpy(), theo.to_numpy())
        face_test = chi_square_gof(
            face_counts.to_numpy(), face_pmf(p.dice_sides, p.weights), pool=False
        )
        mean, var = die_moments(p.dice_sides, p.weights)
        return {
            "theoretical_sum_probabilities": theo.to_dict(),
            "observed_sum_probabilities": (obs_counts / len(sums)).to_dict(),
            "individual_die_frequencies": face_counts.to_dict(),
            "sum_frequency_counts": obs_counts.to_dict(),
            "total_rolls": len(sums),
            "expected_sum_mean": p.n_dice * mean,
            "expected_sum_variance": p.n_dice * var,
            "observed_sum_mean": float(sums.mean()),
            "observed_sum_variance": float(sums.var(ddof=1))
            if len(sums) > 1
            else float("nan"),
            "chi_square_statistic": sum_test.statistic,
            "sum_gof": sum_test.to_dict(),
            "face_gof": face_test.to_dict(),
        }

    def fairness_test(self, data: pd.DataFrame) -> dict[str, Any]:
        """Chi-square test of the null hypothesis that every face is equally likely."""
        s = self.params.dice_sides
        counts = (
            data["die_value"].value_counts().reindex(np.arange(1, s + 1), fill_value=0)
        )
        return chi_square_gof(
            counts.to_numpy(), np.full(s, 1.0 / s), pool=False
        ).to_dict()

    def generate_streak_analysis(self, data: pd.DataFrame) -> dict[str, Any]:
        """Streaks of identical sums, monotone runs, and a runs test for randomness."""
        sums = self.roll_sums(data).to_numpy()
        if sums.size == 0:
            raise InvalidParameterError("no rolls in data")

        # Maximal blocks of identical consecutive values.
        change = np.flatnonzero(np.diff(sums) != 0) + 1
        starts = np.r_[0, change]
        lengths = np.diff(np.r_[starts, sums.size])
        streaks = [
            {"value": int(sums[st]), "length": int(ln)}
            for st, ln in zip(starts, lengths, strict=True)
            if ln > 1
        ]

        # Monotone runs (length counted in observations, ties break runs).
        d = np.sign(np.diff(sums))
        runs_up: list[int] = []
        runs_down: list[int] = []
        i = 0
        while i < d.size:
            j = i
            while j + 1 < d.size and d[j + 1] == d[i]:
                j += 1
            if d[i] > 0:
                runs_up.append(j - i + 2)
            elif d[i] < 0:
                runs_down.append(j - i + 2)
            i = j + 1

        result: dict[str, Any] = {
            "identical_value_streaks": streaks,
            "longest_streak": max((s["length"] for s in streaks), default=0),
            "total_streaks": len(streaks),
            "increasing_runs": runs_up,
            "decreasing_runs": runs_down,
            "longest_increasing_run": max(runs_up, default=0),
            "longest_decreasing_run": max(runs_down, default=0),
        }
        try:
            result["runs_test"] = runs_test(sums).to_dict()
        except InvalidParameterError:
            result["runs_test"] = None
        return result
