"""Tests for pcc_vizforge.analysis.inference."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy import stats

from pcc_vizforge.analysis.inference import (
    adjust_pvalues,
    autocorrelation,
    bootstrap_ci,
    chi_square_gof,
    ljung_box,
    runs_test,
)
from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.rng import make_rng, spawn_rngs


class TestChiSquare:
    def test_matches_scipy_without_pooling(self):
        obs = np.array([18, 22, 20, 25, 15])
        probs = np.full(5, 0.2)
        res = chi_square_gof(obs, probs, pool=False)
        ref = stats.chisquare(obs)
        assert res.statistic == pytest.approx(ref.statistic)
        assert res.p_value == pytest.approx(ref.pvalue)
        assert res.dof == 4

    def test_pooling_merges_sparse_tails(self):
        probs = np.array([0.01, 0.04, 0.45, 0.45, 0.04, 0.01])
        obs = np.array([1, 3, 45, 46, 4, 1])
        res = chi_square_gof(obs, probs, min_expected=5)
        assert res.details["min_expected"] >= 5
        flat = sorted(i for g in res.details["pooled_groups"] for i in g)
        assert flat == list(range(6))

    def test_zero_probability_cell_with_counts(self):
        res = chi_square_gof([5, 5, 1], [0.5, 0.5, 0.0], pool=False)
        assert res.p_value == 0.0 and res.reject()

    def test_length_mismatch(self):
        with pytest.raises(InvalidParameterError):
            chi_square_gof([1, 2], [0.5, 0.25, 0.25])

    @pytest.mark.statistical
    def test_type_one_error_is_calibrated(self):
        """Under H0 the rejection rate at alpha=0.05 should be ~5 %."""
        probs = np.array([1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]) / 36
        rejections = 0
        n_rep = 1000
        for rng in spawn_rngs(2024, n_rep):
            counts = rng.multinomial(500, probs)
            rejections += chi_square_gof(counts, probs).reject(0.05)
        rate = rejections / n_rep
        # 99.9 % binomial band around 0.05 for n=1000 is roughly [0.028, 0.075]
        assert 0.028 < rate < 0.075

    def test_detects_loaded_die(self):
        rng = make_rng(0)
        loaded = np.array([0.1, 0.1, 0.1, 0.1, 0.1, 0.5])
        counts = rng.multinomial(2000, loaded)
        assert chi_square_gof(counts, np.full(6, 1 / 6)).p_value < 1e-10


class TestRunsTest:
    def test_alternating_sequence_rejects(self):
        x = np.tile([0.0, 1.0], 50)
        res = runs_test(x, cutoff=0.5)
        assert res.statistic > 0 and res.reject(1e-6)

    def test_clustered_sequence_rejects(self):
        x = np.r_[np.zeros(50), np.ones(50)]
        res = runs_test(x, cutoff=0.5)
        assert res.details["runs"] == 2 and res.statistic < 0 and res.reject(1e-6)

    def test_iid_does_not_reject(self):
        res = runs_test(make_rng(3).standard_normal(2000))
        assert not res.reject(0.001)

    def test_constant_sequence_raises(self):
        with pytest.raises(InvalidParameterError):
            runs_test(np.ones(10))


class TestAutocorrelation:
    def test_lag_zero_is_one(self):
        acf = autocorrelation(make_rng(1).standard_normal(500), 20)
        assert acf[0] == pytest.approx(1.0)
        assert acf.shape == (21,)

    def test_matches_direct_computation(self):
        x = make_rng(5).standard_normal(200)
        acf = autocorrelation(x, 5)
        xc = x - x.mean()
        direct = [np.sum(xc[: len(x) - k] * xc[k:]) / np.sum(xc**2) for k in range(6)]
        np.testing.assert_allclose(acf, direct, atol=1e-12)

    def test_ar1_lag_one(self):
        rng = make_rng(7)
        phi, n = 0.7, 20_000
        e = rng.standard_normal(n)
        x = np.empty(n)
        x[0] = e[0]
        for t in range(1, n):
            x[t] = phi * x[t - 1] + e[t]
        acf = autocorrelation(x, 3)
        np.testing.assert_allclose(acf[1:], phi ** np.arange(1, 4), atol=0.03)

    def test_constant_series(self):
        np.testing.assert_array_equal(autocorrelation(np.ones(10), 2), [1, 0, 0])

    def test_invalid_lag(self):
        with pytest.raises(InvalidParameterError):
            autocorrelation(np.arange(5.0), 5)


class TestLjungBox:
    def test_white_noise(self):
        assert not ljung_box(make_rng(11).standard_normal(1000), 10).reject(0.001)

    def test_random_walk_rejects(self):
        assert ljung_box(np.cumsum(make_rng(11).standard_normal(1000)), 10).reject(
            1e-10
        )


class TestBootstrap:
    def test_ci_contains_estimate_and_is_reproducible(self):
        x = make_rng(0).exponential(2.0, 300)
        a = bootstrap_ci(x, np.mean, seed=1, n_resamples=500)
        b = bootstrap_ci(x, np.mean, seed=1, n_resamples=500)
        assert a == b
        assert a.low < a.estimate < a.high
        assert a.contains(a.estimate)

    @pytest.mark.slow
    @pytest.mark.statistical
    def test_coverage_is_near_nominal(self):
        hits = 0
        n_rep = 200
        for i, rng in enumerate(spawn_rngs(99, n_rep)):
            x = rng.normal(3.0, 1.0, 60)
            hits += bootstrap_ci(x, np.mean, n_resamples=400, seed=i).contains(3.0)
        assert 0.88 <= hits / n_rep <= 0.99

    def test_rejects_tiny_sample(self):
        with pytest.raises(InvalidParameterError):
            bootstrap_ci([1.0])


class TestAdjustPvalues:
    P = np.array([0.01, 0.04, 0.03, 0.005])

    def test_bonferroni(self):
        np.testing.assert_allclose(
            adjust_pvalues(self.P, "bonferroni"), [0.04, 0.16, 0.12, 0.02]
        )

    def test_holm(self):
        # sorted: .005*4=.02, .01*3=.03, .03*2=.06, .04*1=.04 -> monotone .06
        np.testing.assert_allclose(
            adjust_pvalues(self.P, "holm"), [0.03, 0.06, 0.06, 0.02]
        )

    def test_bh(self):
        # sorted: .005*4/1=.02, .01*4/2=.02, .03*4/3=.04, .04*4/4=.04
        np.testing.assert_allclose(
            adjust_pvalues(self.P, "bh"), [0.02, 0.04, 0.04, 0.02]
        )

    def test_mapping_input(self):
        out = adjust_pvalues({"a": 0.5, "b": 0.01}, "bonferroni")
        np.testing.assert_allclose(out, [1.0, 0.02])

    @given(st.lists(st.floats(0, 1), min_size=1, max_size=30))
    @settings(max_examples=100, deadline=None)
    def test_adjusted_dominate_raw_and_bounded(self, ps):
        p = np.array(ps)
        for method in ("bonferroni", "holm", "bh"):
            adj = adjust_pvalues(p, method)
            assert np.all(adj >= p - 1e-12)
            assert np.all(adj <= 1.0)
        assert np.all(adjust_pvalues(p, "bh") <= adjust_pvalues(p, "holm") + 1e-12)

    def test_invalid(self):
        with pytest.raises(InvalidParameterError):
            adjust_pvalues([1.2])
        with pytest.raises(InvalidParameterError):
            adjust_pvalues([0.1], "nope")  # type: ignore[arg-type]
