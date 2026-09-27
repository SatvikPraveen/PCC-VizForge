"""Tests for the earthquake generator and statistical-seismology estimators."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from pcc_vizforge.analysis.seismology import (
    b_value_mle,
    b_value_mle_truncated,
    fit_omori,
    frequency_magnitude_distribution,
    haversine_km,
    interevent_cv,
    magnitude_of_completeness,
    omori_sample_delays,
    seismic_energy_joules,
    seismic_moment_nm,
    truncated_gr_sample,
)
from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.generators.quakes import EarthquakeGenerator, branching_ratio
from pcc_vizforge.rng import make_rng, spawn_rngs

NO_AFTERSHOCKS = {"aftershocks": {"enabled": False}}


class TestSamplers:
    def test_truncated_gr_bounds_and_ks(self):
        m = truncated_gr_sample(make_rng(0), 20_000, 1.0, 2.0, 5.0)
        assert m.min() >= 2.0 and m.max() <= 5.0
        beta = np.log(10)
        cdf = lambda x: (1 - np.exp(-beta * (x - 2))) / (1 - np.exp(-beta * 3))  # noqa: E731
        assert stats.kstest(m, cdf).pvalue > 0.001

    def test_omori_delays_ks(self):
        c, p, T = 0.05, 1.2, 100.0
        t = omori_sample_delays(make_rng(1), 20_000, c, p, T)
        assert t.min() >= 0 and t.max() <= T
        q = 1 - p
        cdf = lambda x: ((x + c) ** q - c**q) / ((T + c) ** q - c**q)  # noqa: E731
        assert stats.kstest(t, cdf).pvalue > 0.001

    def test_omori_p_equal_one(self):
        t = omori_sample_delays(make_rng(1), 10_000, 0.1, 1.0, 10.0)
        cdf = lambda x: np.log((x + 0.1) / 0.1) / np.log(10.1 / 0.1)  # noqa: E731
        assert stats.kstest(t, cdf).pvalue > 0.001

    @pytest.mark.parametrize("bad", [(0, 2, 3), (1, 3, 2)])
    def test_gr_invalid(self, bad):
        with pytest.raises(InvalidParameterError):
            truncated_gr_sample(make_rng(0), 5, *bad)


class TestPhysics:
    def test_energy_and_moment(self):
        assert seismic_energy_joules([0.0])[0] == pytest.approx(10**4.8)
        # one magnitude unit = 10^1.5 ~ 31.6x energy
        e = seismic_energy_joules([5.0, 6.0])
        assert e[1] / e[0] == pytest.approx(10**1.5)
        assert seismic_moment_nm([6.0])[0] == pytest.approx(10**18.1)

    def test_haversine(self):
        assert haversine_km(0, 0, 0, 0) == 0
        # quarter meridian
        assert haversine_km(0, 0, 90, 0) == pytest.approx(np.pi / 2 * 6371.0088)
        assert haversine_km(0, 179.5, 0, -179.5) == pytest.approx(111.195, rel=1e-3)


@pytest.mark.statistical
class TestEstimators:
    @pytest.mark.parametrize("b", [0.8, 1.0, 1.3])
    def test_aki_recovers_b(self, b):
        m = truncated_gr_sample(make_rng(3), 5000, b, 2.0)
        est = b_value_mle(m, 2.0)
        assert est.ci[0] < b < est.ci[1]
        assert est.n_events == 5000

    def test_aki_with_binning(self):
        m = np.round(truncated_gr_sample(make_rng(4), 20_000, 1.0, 1.95) / 0.1) * 0.1
        m = m[m >= 2.0 - 1e-9]
        assert b_value_mle(m, 2.0, bin_width=0.1).b_value == pytest.approx(
            1.0, abs=0.03
        )
        # ignoring the bin correction is biased upward
        assert b_value_mle(m, 2.0).b_value > 1.04

    def test_truncated_mle_corrects_aki_bias(self):
        m = truncated_gr_sample(make_rng(5), 20_000, 1.0, 2.0, 3.0)
        aki = b_value_mle(m, 2.0)
        page = b_value_mle_truncated(m, 2.0, 3.0)
        assert abs(page.b_value - 1.0) < 3 * page.std_error
        assert aki.b_value > page.b_value + 0.1  # Aki is biased for narrow ranges

    def test_shi_bolt_se_is_calibrated(self):
        """Empirical sd of b-hat across replicates should match the reported SE."""
        ests = [
            b_value_mle(truncated_gr_sample(r, 400, 1.0, 2.0), 2.0)
            for r in spawn_rngs(8, 400)
        ]
        b = np.array([e.b_value for e in ests])
        se = np.mean([e.std_error for e in ests])
        assert b.std(ddof=1) == pytest.approx(se, rel=0.15)
        coverage = np.mean([e.ci[0] <= 1.0 <= e.ci[1] for e in ests])
        assert 0.91 <= coverage <= 0.98

    def test_mc_maxc_with_incomplete_catalogue(self):
        rng = make_rng(9)
        m = truncated_gr_sample(rng, 50_000, 1.0, 0.0)
        # detection probability rises smoothly around M=1.5
        detected = rng.random(m.size) < stats.norm.cdf(m, 1.5, 0.2)
        mc = magnitude_of_completeness(m[detected], correction=0.0)
        assert 1.3 <= mc <= 1.8

    def test_fmd(self):
        centres, inc, cum = frequency_magnitude_distribution([2.0, 2.04, 2.1, 2.5], 0.1)
        assert inc.sum() == 4 and cum[0] == 4 and cum[-1] == inc[-1]
        np.testing.assert_allclose(centres[[0, -1]], [2.0, 2.5])

    def test_omori_fit_recovers_p(self):
        t = omori_sample_delays(make_rng(10), 3000, 0.05, 1.15, 200.0)
        fit = fit_omori(t, t_max=200.0)
        assert fit.p == pytest.approx(1.15, abs=4 * fit.p_stderr + 0.02)
        assert fit.rate(np.array([0.0]))[0] > fit.rate(np.array([10.0]))[0]

    def test_interevent_cv_poisson(self):
        t = np.sort(make_rng(2).uniform(0, 1000, 5000))
        assert interevent_cv(t) == pytest.approx(1.0, abs=0.05)

    def test_errors(self):
        with pytest.raises(InvalidParameterError):
            b_value_mle([2.0], 2.0)
        with pytest.raises(InvalidParameterError):
            fit_omori([1, 2, 3])
        with pytest.raises(InvalidParameterError):
            interevent_cv([1, 2])
        with pytest.raises(InvalidParameterError):
            frequency_magnitude_distribution([])


class TestBranchingRatio:
    def test_closed_form_matches_monte_carlo(self):
        rng = make_rng(0)
        m = truncated_gr_sample(rng, 200_000, 1.0, 2.0, 7.0)
        mc = np.mean(0.05 * 10 ** (0.8 * (m - 2.0)))
        assert branching_ratio(1.0, 0.8, 0.05, 2.0, 7.0) == pytest.approx(mc, rel=0.03)

    def test_equal_exponents(self):
        n = branching_ratio(1.0, 1.0, 0.01, 2.0, 5.0)
        beta = np.log(10)
        assert n == pytest.approx(0.01 * beta * 3 / (1 - np.exp(-beta * 3)))

    def test_supercritical_rejected(self):
        with pytest.raises(InvalidParameterError, match="branching ratio"):
            EarthquakeGenerator(aftershocks={"enabled": True, "productivity": 5.0})


class TestGenerator:
    def test_structure(self):
        df = EarthquakeGenerator(n_earthquakes=300).generate()
        assert df["timestamp"].is_monotonic_increasing
        assert df["earthquake_id"].tolist() == list(range(len(df)))
        assert df["latitude"].between(-90, 90).all()
        assert df["longitude"].between(-180, 180).all()
        assert df["magnitude"].between(2.0, 8.5).all()
        assert df["depth_km"].between(1.0, 700.0).all()
        # parents precede their aftershocks
        after = df[df["is_aftershock"]]
        parent_times = (
            df.set_index("earthquake_id")
            .loc[after["parent_id"], "time_days"]
            .to_numpy()
        )
        assert np.all(parent_times <= after["time_days"].to_numpy())
        assert (df.loc[~df["is_aftershock"], "parent_id"] == -1).all()

    def test_reproducible(self):
        g = EarthquakeGenerator(n_earthquakes=100)
        pd.testing.assert_frame_equal(g.generate(seed=1), g.generate(seed=1))

    def test_background_uniform_on_sphere(self):
        df = EarthquakeGenerator(
            n_earthquakes=20_000, hotspots=[], **NO_AFTERSHOCKS
        ).generate()
        # sin(latitude) ~ U(-1, 1) for sphere-uniform points
        assert (
            stats.kstest(
                np.sin(np.radians(df["latitude"])), "uniform", args=(-1, 2)
            ).pvalue
            > 1e-3
        )
        assert set(df["region"]) == {"Global"}

    def test_hotspot_fractions(self):
        df = EarthquakeGenerator(n_earthquakes=10_000, **NO_AFTERSHOCKS).generate()
        frac = df["region"].value_counts(normalize=True)
        assert frac["Pacific Ring of Fire"] == pytest.approx(0.4, abs=0.02)
        assert frac["Mid-Atlantic Ridge"] == pytest.approx(0.2, abs=0.02)

    def test_aftershock_fraction_matches_branching_ratio(self):
        # short Omori tail + long window so few aftershocks fall past the end
        g = EarthquakeGenerator(
            n_earthquakes=20_000, duration_days=36_500, aftershocks={"omori_p": 2.0}
        )
        df = g.generate()
        p = g.params
        a = p.aftershock_cfg
        n_br = branching_ratio(
            p.b_value, a["alpha"], a["productivity"], *p.magnitude_range
        )
        # total/background = 1/(1-n) for a subcritical cascade
        assert len(df) / 20_000 == pytest.approx(1 / (1 - n_br), rel=0.03)

    def test_clustering_raises_interevent_cv(self):
        kw = {"n_earthquakes": 3000, "magnitude_range": [2.0, 8.0]}
        clustered = EarthquakeGenerator(
            aftershocks={"enabled": True, "productivity": 0.3, "alpha": 0.5}, **kw
        ).generate()
        poisson = EarthquakeGenerator(**NO_AFTERSHOCKS, **kw).generate()
        assert (
            interevent_cv(clustered["time_days"])
            > interevent_cv(poisson["time_days"]) + 0.1
        )

    def test_magnitude_binning(self):
        df = EarthquakeGenerator(n_earthquakes=200, magnitude_bin=0.1).generate()
        np.testing.assert_allclose(
            df["magnitude"] * 10, np.round(df["magnitude"] * 10), atol=1e-9
        )

    def test_statistics(self):
        g = EarthquakeGenerator(n_earthquakes=3000)
        s = g.calculate_statistics(g.generate())
        assert s["b_value_aki"]["ci"][0] < 1.0 < s["b_value_aki"]["ci"][1]
        assert s["total_earthquakes"] > 3000 and s["n_aftershocks"] > 0
        assert "interevent_cv" in s

    def test_categories(self):
        g = EarthquakeGenerator()
        assert g._categorize_magnitude(2.5) == "Micro"
        assert g._categorize_magnitude(9.0) == "Great"
        assert g._categorize_depth(100) == "Intermediate"

    @pytest.mark.parametrize(
        "bad",
        [
            {"magnitude_range": [5, 3]},
            {"b_value": 0},
            {"lat_range": [-100, 0]},
            {"start_date": "yesterday"},
            {"duration_days": 1e6},
            {"hotspots": [{"name": "x"}]},
            {
                "hotspots": [
                    {
                        "name": "a",
                        "lat_center": 0,
                        "lon_center": 0,
                        "lat_range": 1,
                        "lon_range": 1,
                        "probability": 1.5,
                    }
                ]
            },
        ],
    )
    def test_invalid(self, bad):
        with pytest.raises(InvalidParameterError):
            EarthquakeGenerator(**bad)
