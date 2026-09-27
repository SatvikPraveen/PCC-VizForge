"""Tests for the dice generator and exact probability utilities."""

from __future__ import annotations

import itertools
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pcc_vizforge.analysis.probability import (
    die_moments,
    face_pmf,
    running_mean_band,
    sum_counts_fair,
    sum_pmf,
)
from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.generators.dice import DiceGenerator, DiceParams
from pcc_vizforge.rng import spawn_seeds


class TestExactDistributions:
    def test_two_d6_counts(self):
        assert sum_counts_fair(2, 6) == [1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]

    @pytest.mark.parametrize(("n", "s"), [(1, 6), (3, 4), (3, 6), (4, 3)])
    def test_matches_brute_force_enumeration(self, n, s):
        brute = np.zeros(n * s - n + 1)
        for faces in itertools.product(range(1, s + 1), repeat=n):
            brute[sum(faces) - n] += 1
        support, pmf = sum_pmf(n, s)
        np.testing.assert_allclose(pmf, brute / s**n, atol=1e-15)
        assert support[0] == n and support[-1] == n * s
        assert sum_counts_fair(n, s) == brute.astype(int).tolist()

    def test_large_n_exact_integers(self):
        counts = sum_counts_fair(20, 6)
        assert sum(counts) == 6**20
        _, pmf = sum_pmf(20, 6)
        exact = np.array([float(Fraction(c, 6**20)) for c in counts])
        np.testing.assert_allclose(pmf, exact, rtol=1e-10, atol=1e-300)

    @given(n=st.integers(1, 12), s=st.integers(2, 12))
    @settings(max_examples=60, deadline=None)
    def test_pmf_properties(self, n, s):
        support, pmf = sum_pmf(n, s)
        assert pmf.sum() == pytest.approx(1.0)
        assert np.all(pmf >= 0)
        np.testing.assert_allclose(pmf, pmf[::-1], atol=1e-12)  # fair dice: symmetric
        mean, var = die_moments(s)
        assert np.dot(support, pmf) == pytest.approx(n * mean)
        assert np.dot((support - n * mean) ** 2, pmf) == pytest.approx(n * var)

    def test_loaded_die(self):
        w = [0, 0, 0, 0, 0, 1]
        support, pmf = sum_pmf(3, 6, w)
        assert pmf[support == 18][0] == pytest.approx(1.0)
        assert die_moments(6, w) == (6.0, 0.0)

    def test_moments_fair(self):
        assert die_moments(6) == pytest.approx((3.5, 35 / 12))

    def test_running_mean_band(self):
        lo, hi = running_mean_band([1, 100], 3.5, 35 / 12)
        assert np.all(lo < 3.5) and np.all(hi > 3.5)
        assert (hi - lo)[1] == pytest.approx((hi - lo)[0] / 10)

    @pytest.mark.parametrize("bad", [(0, 6), (2, 1)])
    def test_invalid(self, bad):
        with pytest.raises(InvalidParameterError):
            sum_pmf(*bad)
        with pytest.raises(InvalidParameterError):
            sum_counts_fair(*bad)

    def test_invalid_weights(self):
        with pytest.raises(InvalidParameterError):
            face_pmf(6, [1, 2])
        with pytest.raises(InvalidParameterError):
            face_pmf(3, [-1, 1, 1])


class TestDiceGenerator:
    def test_structure(self):
        df = DiceGenerator(n_rolls=50, n_dice=3, dice_sides=8).generate()
        assert len(df) == 150
        assert df["die_value"].between(1, 8).all()
        sums = df.groupby("roll_id")["die_value"].sum()
        assert (sums == df.groupby("roll_id")["roll_sum"].first()).all()
        assert not df["is_doubles"].any()  # only defined for 2 dice
        rolls = df.groupby("roll_id").first()
        np.testing.assert_allclose(rolls["rolling_avg"], rolls["roll_sum"].expanding().mean())

    def test_doubles(self):
        df = DiceGenerator(n_rolls=500, n_dice=2).generate()
        rolls = df.groupby("roll_id")
        doubles = rolls["die_value"].nunique() == 1
        assert (rolls["is_doubles"].first() == doubles).all()

    def test_reproducible(self):
        g = DiceGenerator(n_rolls=100)
        pd.testing.assert_frame_equal(g.generate(seed=3), g.generate(seed=3))

    def test_invalid_params(self):
        with pytest.raises(InvalidParameterError):
            DiceParams(dice_sides=1).validate()
        with pytest.raises(InvalidParameterError):
            DiceGenerator(n_rolls=0)

    def test_probability_report(self):
        g = DiceGenerator(n_rolls=2000)
        report = g.calculate_probabilities(g.generate())
        assert sum(report["theoretical_sum_probabilities"].values()) == pytest.approx(1.0)
        assert report["total_rolls"] == 2000
        assert 0 <= report["sum_gof"]["p_value"] <= 1
        assert report["expected_sum_mean"] == pytest.approx(7.0)

    def test_streaks(self):
        g = DiceGenerator(n_rolls=300)
        res = g.generate_streak_analysis(g.generate())
        assert res["longest_streak"] >= 0
        assert all(r >= 2 for r in res["increasing_runs"] + res["decreasing_runs"])
        assert res["runs_test"]["p_value"] > 0.0001

    def test_streaks_known_sequence(self):
        seq = [5, 5, 6, 7, 3, 3, 3, 2]
        df = pd.DataFrame({"roll_id": range(8), "roll_sum": seq})
        res = DiceGenerator().generate_streak_analysis(df)
        assert res["identical_value_streaks"] == [
            {"value": 5, "length": 2},
            {"value": 3, "length": 3},
        ]
        assert res["increasing_runs"] == [3]  # 5,6,7
        assert res["decreasing_runs"] == [2, 2]  # 7,3 and 3,2

    @pytest.mark.statistical
    def test_sum_gof_calibrated_under_h0(self):
        g = DiceGenerator(n_rolls=600, n_dice=3)
        pvals = [
            g.calculate_probabilities(g.generate(seed=ss))["sum_gof"]["p_value"]
            for ss in spawn_seeds(11, 300)
        ]
        # p-values ~ U(0,1) under H0: KS test should not reject
        from scipy import stats

        assert stats.kstest(pvals, "uniform").pvalue > 0.001

    @pytest.mark.statistical
    def test_fairness_test_detects_loading(self):
        g = DiceGenerator(n_rolls=3000, weights=[1, 1, 1, 1, 1, 2])
        data = g.generate()
        assert g.fairness_test(data)["p_value"] < 1e-6
        # ...while the configured-distribution test is consistent with H0
        assert g.calculate_probabilities(data)["face_gof"]["p_value"] > 1e-4
