"""Tests for the GitHub generator and heavy-tail inference."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import special, stats

from pcc_vizforge.analysis.heavy_tails import (
    ccdf,
    compare_distributions,
    fit_power_law,
    gini,
    hill_estimator,
    power_law_gof,
    sample_power_law,
)
from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.generators.github import GitHubGenerator
from pcc_vizforge.rng import make_rng


class TestSampling:
    def test_continuous_ks(self):
        x = sample_power_law(make_rng(0), 5000, 2.5, 3.0)
        assert x.min() >= 3.0
        cdf = lambda v: 1 - (v / 3.0) ** (-1.5)  # noqa: E731
        assert stats.kstest(x, cdf).pvalue > 0.001

    def test_discrete_pmf(self):
        alpha, xmin = 2.2, 2
        x = sample_power_law(make_rng(1), 50_000, alpha, xmin, discrete=True)
        assert np.all(x == np.round(x)) and x.min() >= xmin
        for k in (2, 3, 5):
            expected = k ** (-alpha) / special.zeta(alpha, xmin)
            assert np.mean(x == k) == pytest.approx(expected, abs=0.006)

    def test_invalid(self):
        with pytest.raises(InvalidParameterError):
            sample_power_law(make_rng(0), 5, 1.0, 1.0)


@pytest.mark.statistical
class TestFitting:
    @pytest.mark.parametrize("alpha", [1.8, 2.5, 3.2])
    def test_continuous_alpha_recovery_known_xmin(self, alpha):
        x = sample_power_law(make_rng(2), 4000, alpha, 1.0)
        fit = fit_power_law(x, xmin=1.0)
        assert abs(fit.alpha - alpha) < 4 * fit.alpha_stderr

    def test_discrete_alpha_recovery(self):
        x = sample_power_law(make_rng(3), 4000, 2.3, 1, discrete=True)
        fit = fit_power_law(x, xmin=1)
        assert fit.discrete and abs(fit.alpha - 2.3) < 4 * fit.alpha_stderr

    def test_discrete_stderr_uses_fisher_information(self):
        x = sample_power_law(make_rng(12), 1000, 3.0, 1, discrete=True)
        fit = fit_power_law(x, xmin=1)
        # the continuous formula (alpha-1)/sqrt(n) understates discrete uncertainty
        assert fit.alpha_stderr > 1.1 * (fit.alpha - 1) / np.sqrt(fit.n_tail)

    @pytest.mark.slow
    def test_discrete_ci_coverage(self):
        from pcc_vizforge.rng import spawn_rngs

        hits = 0
        for rng in spawn_rngs(21, 200):
            fit = fit_power_law(
                sample_power_law(rng, 800, 3.0, 1, discrete=True), xmin=1
            )
            hits += abs(fit.alpha - 3.0) <= 1.96 * fit.alpha_stderr
        assert hits / 200 >= 0.91

    def test_xmin_detection_with_body(self):
        rng = make_rng(4)
        body = rng.uniform(0.1, 5.0, 3000)
        tail = sample_power_law(rng, 3000, 2.5, 5.0)
        fit = fit_power_law(np.concatenate([body, tail]))
        assert fit.xmin == pytest.approx(5.0, rel=0.25)
        assert fit.alpha == pytest.approx(2.5, abs=0.15)

    def test_gof_plausible_for_power_law(self):
        x = sample_power_law(make_rng(5), 800, 2.5, 1.0)
        res = power_law_gof(x, n_bootstrap=40, seed=1)
        # p ~ U(0,1) under H0, so only a very small p-value would be a failure
        assert res.p_value > 0.01

    def test_gof_rejects_exponential(self):
        x = make_rng(6).exponential(10.0, 2000) + 1
        res = power_law_gof(x, fit_power_law(x, xmin=1.0), n_bootstrap=40, seed=1)
        assert res.p_value < 0.1

    def test_vuong_favours_true_model(self):
        rng = make_rng(7)
        pl = sample_power_law(rng, 3000, 2.2, 1.0)
        exp = rng.exponential(3.0, 3000) + 1.0
        assert (
            compare_distributions(
                pl, fit_power_law(pl, xmin=1.0), "exponential"
            ).details["favoured"]
            == "power_law"
        )
        assert (
            compare_distributions(
                exp, fit_power_law(exp, xmin=1.0), "exponential"
            ).details["favoured"]
            == "exponential"
        )

    def test_vuong_discrete_lognormal_vs_power_law(self):
        x = np.round(make_rng(8).lognormal(1.0, 0.6, 5000))
        x = x[x > 0]
        res = compare_distributions(x, fit_power_law(x, xmin=1), "lognormal")
        assert res.statistic < 0 and res.details["favoured"] == "lognormal"

    def test_hill(self):
        x = sample_power_law(make_rng(9), 20_000, 3.0, 1.0)
        assert hill_estimator(x, 2000) == pytest.approx(3.0, abs=0.15)


class TestDescriptors:
    def test_ccdf(self):
        v, c = ccdf([1, 2, 2, 3])
        np.testing.assert_allclose(v, [1, 2, 3])
        np.testing.assert_allclose(c, [1.0, 0.75, 0.25])

    def test_gini(self):
        assert gini([1, 1, 1, 1]) == pytest.approx(0.0)
        assert gini([0, 0, 0, 10]) == pytest.approx(0.75)
        assert gini([0, 0]) == 0.0
        with pytest.raises(InvalidParameterError):
            gini([-1, 2])

    def test_errors(self):
        with pytest.raises(InvalidParameterError):
            fit_power_law([1, 2, 3])
        with pytest.raises(InvalidParameterError):
            hill_estimator([1, 2, 3], 5)
        with pytest.raises(InvalidParameterError):
            ccdf([0, -1])


class TestGitHubGenerator:
    def test_structure(self):
        df = GitHubGenerator(n_repositories=200).generate()
        assert len(df) == 200
        for col in ("stars", "forks", "issues", "commits", "contributors", "watchers"):
            assert (df[col] >= 0).all()
        assert (df["contributors"] >= 1).all() and (df["commits"] >= 1).all()
        assert (df["created_date"] <= df["last_updated"]).all()
        assert (df["last_updated"] <= pd.Timestamp("2024-01-01")).all()

    def test_reproducible_regardless_of_wall_clock(self):
        g = GitHubGenerator(n_repositories=50)
        pd.testing.assert_frame_equal(g.generate(seed=3), g.generate(seed=3))

    def test_timeline(self):
        g = GitHubGenerator()
        a = g.generate_activity_timeline(100, seed=1)
        b = g.generate_activity_timeline(100, seed=1)
        pd.testing.assert_frame_equal(a, b)
        assert len(a) == 100
        weekday = a.loc[a["day_of_week"] < 5, "commits"].mean()
        weekend = a.loc[a["day_of_week"] >= 5, "commits"].mean()
        assert weekday > weekend

    def test_language_weights(self):
        df = GitHubGenerator(
            n_repositories=2000, languages=["A", "B"], language_weights=[3, 1]
        ).generate()
        assert df["primary_language"].value_counts(normalize=True)[
            "A"
        ] == pytest.approx(0.75, abs=0.03)

    def test_legacy_caps(self):
        df = GitHubGenerator(n_repositories=500, stars_range=[0, 100]).generate()
        assert df["stars"].max() <= 100

    def test_language_statistics(self):
        g = GitHubGenerator(n_repositories=300)
        s = g.calculate_language_statistics(g.generate())
        assert sum(s["language_distribution"].values()) == 300
        assert s["most_popular_language"] in g.params.languages

    @pytest.mark.statistical
    def test_star_tail_exponent_recovered(self):
        g = GitHubGenerator(n_repositories=8000, popularity_exponent=2.3)
        s = g.calculate_statistics(g.generate())
        pl = s["power_law"]
        assert abs(pl["alpha"] - 2.3) < 4 * pl["alpha_stderr"] + 0.05
        assert s["vs_exponential"]["details"]["favoured"] == "power_law"
        assert s["star_fork_spearman"] > 0.4

    @pytest.mark.parametrize(
        "bad",
        [
            {"popularity_exponent": 1.0},
            {"languages": []},
            {"language_weights": [1]},
            {"reference_date": "soon"},
            {"fork_ratio_beta": [0, 1]},
        ],
    )
    def test_invalid(self, bad):
        with pytest.raises(InvalidParameterError):
            GitHubGenerator(**bad)
