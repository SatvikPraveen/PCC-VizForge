"""Tests for the stochastic weather generator and time-series analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from pcc_vizforge.analysis.timeseries import (
    fit_harmonics,
    fit_markov_chain,
    heat_index_c,
    mann_kendall,
    relative_humidity,
    saturation_vapor_pressure,
    sens_slope,
    spell_lengths,
)
from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.generators.weather import WeatherGenerator, WeatherParams, ar1
from pcc_vizforge.rng import make_rng, spawn_rngs


class TestThermodynamics:
    def test_saturation_vapor_pressure_reference(self):
        # ~6.11 hPa at 0 °C, ~23.4 hPa at 20 °C, ~42.4 hPa at 30 °C
        np.testing.assert_allclose(saturation_vapor_pressure([0, 20, 30]), [6.11, 23.37, 42.43], rtol=0.01)

    def test_relative_humidity(self):
        assert relative_humidity(20, 20) == pytest.approx(100)
        assert relative_humidity(30, 10) == pytest.approx(28.9, abs=0.5)

    def test_heat_index_nws_table(self):
        # NWS table: 90 °F & 70 % RH -> 106 °F ; 100 °F & 40 % -> 109 °F
        t = (np.array([90, 100]) - 32) * 5 / 9
        hi_f = heat_index_c(t, [70, 40]) * 9 / 5 + 32
        np.testing.assert_allclose(hi_f, [106, 109], atol=1.5)

    def test_heat_index_cool_is_temperature(self):
        assert heat_index_c(5.0, 90)[()] == pytest.approx(5.0)


class TestTrend:
    def test_sens_slope_exact(self):
        slope, intercept, lo, hi = sens_slope(3 + 0.5 * np.arange(20.0))
        assert slope == pytest.approx(0.5) and intercept == pytest.approx(3)
        assert lo <= slope <= hi

    def test_mann_kendall_detects_trend(self):
        rng = make_rng(0)
        y = 0.02 * np.arange(300) + rng.normal(0, 1, 300)
        res = mann_kendall(y)
        assert res.reject(1e-6) and res.statistic > 0
        assert res.details["sens_slope"] == pytest.approx(0.02, abs=0.005)

    def test_mann_kendall_ties(self):
        res = mann_kendall([1, 1, 2, 2, 3, 3, 4, 4])
        assert res.details["var_S"] < 8 * 7 * 21 / 18  # tie correction reduces variance

    @pytest.mark.slow
    @pytest.mark.statistical
    def test_prewhitening_controls_type_one_error(self):
        """Under AR(1) noise without trend the plain test over-rejects."""
        rejections = {"none": 0, "prewhiten": 0, "hamed_rao": 0}
        n_rep = 300
        for rng in spawn_rngs(5, n_rep):
            y = ar1(rng, 200, 0.6, 1.0)
            for method in rejections:
                rejections[method] += mann_kendall(y, correction=method).reject(0.05)
        rate = {k: v / n_rep for k, v in rejections.items()}
        assert rate["none"] > 0.2, rate
        assert rate["prewhiten"] < 0.09, rate
        # Hamed-Rao is known to stay somewhat liberal for strong autocorrelation
        assert rate["hamed_rao"] < min(0.2, rate["none"]), rate

    @pytest.mark.slow
    @pytest.mark.statistical
    def test_corrections_retain_power(self):
        power = {"prewhiten": 0, "hamed_rao": 0}
        for rng in spawn_rngs(6, 100):
            y = ar1(rng, 300, 0.5, 1.0) + 0.01 * np.arange(300)
            for method in power:
                power[method] += mann_kendall(y, correction=method).reject(0.05)
        assert min(power.values()) >= 70, power

    def test_invalid(self):
        with pytest.raises(InvalidParameterError):
            mann_kendall([1, 2, 3])
        with pytest.raises(InvalidParameterError):
            mann_kendall([1, 2, 3, 4, 5], correction="tfpw")  # type: ignore[arg-type]


class TestHarmonics:
    def test_recovers_parameters(self):
        t = np.arange(730.0)
        y = 12 + 0.001 * t + 8 * np.cos(2 * np.pi * t / 365.25 - 1.0) + make_rng(1).normal(0, 0.5, t.size)
        fit = fit_harmonics(t, y, n_harmonics=1)
        assert fit.amplitudes[0] == pytest.approx(8, abs=0.1)
        assert fit.phases[0] == pytest.approx(1.0, abs=0.02)
        assert fit.trend_per_unit == pytest.approx(0.001, abs=4 * fit.trend_stderr)
        np.testing.assert_allclose(fit.predict(t), y, atol=2.5)

    def test_invalid(self):
        with pytest.raises(InvalidParameterError):
            fit_harmonics(np.arange(3.0), np.arange(3.0), n_harmonics=2)


class TestMarkov:
    def test_spell_lengths(self):
        wet, dry = spell_lengths([1, 1, 0, 0, 0, 1, 0])
        assert wet.tolist() == [2, 1] and dry.tolist() == [3, 1]
        assert [a.size for a in spell_lengths([])] == [0, 0]

    def test_fit_known(self):
        fit = fit_markov_chain([0, 1, 1, 0, 0, 1, 1, 1])
        # transitions from dry: 0->1, 0->0, 0->1 => p01=2/3 ; from wet: 1->1,1->0,1->1,1->1 => 3/4
        assert fit.p_wet_given_dry == pytest.approx(2 / 3)
        assert fit.p_wet_given_wet == pytest.approx(3 / 4)

    def test_fit_errors(self):
        with pytest.raises(InvalidParameterError):
            fit_markov_chain([1, 1, 1])


class TestAR1:
    def test_moments(self):
        x = ar1(make_rng(2), 100_000, 0.8, 2.0)
        assert x.std() == pytest.approx(2.0, rel=0.03)
        assert np.corrcoef(x[1:], x[:-1])[0, 1] == pytest.approx(0.8, abs=0.01)


class TestWeatherGenerator:
    def test_structure_and_ranges(self):
        df = WeatherGenerator(n_days=400).generate()
        assert len(df) == 400
        assert df["date"].is_monotonic_increasing
        assert df["humidity"].between(0, 100).all()
        assert (df["precipitation"] >= 0).all()
        assert ((df["precipitation"] > 0) == df["is_rainy_day"]).all()
        assert (df["temperature_min"] <= df["temperature_avg"]).all()
        assert (df["temperature_avg"] <= df["temperature_max"]).all()
        for col in ("temperature_morning", "temperature_afternoon", "temperature_evening", "temperature_night"):
            assert df[col].between(df["temperature_min"] - 1e-9, df["temperature_max"] + 1e-9).all()
        assert (df["dewpoint"] <= df["temperature_avg"] + 1e-9).all()
        assert df["cloud_cover"].between(0, 100).all()

    def test_reproducible(self):
        g = WeatherGenerator(n_days=50)
        pd.testing.assert_frame_equal(g.generate(seed=2), g.generate(seed=2))

    def test_seasons_by_hemisphere(self):
        north = WeatherGenerator(n_days=365).generate()
        south = WeatherGenerator(n_days=365, hemisphere="south").generate()
        assert north.loc[north["date"].dt.month == 7, "season"].eq("Summer").all()
        assert south.loc[south["date"].dt.month == 7, "season"].eq("Winter").all()
        assert (
            north.loc[north["date"].dt.month == 7, "temperature_avg"].mean()
            > south.loc[south["date"].dt.month == 7, "temperature_avg"].mean() + 10
        )

    def test_legacy_precipitation_probability(self):
        p = WeatherParams(precipitation_probability=0.3, p_wet_given_wet=0.6)
        p01, p11 = p.transition_probabilities()
        assert p01 / (1 - p11 + p01) == pytest.approx(0.3)

    @pytest.mark.statistical
    def test_recovers_markov_chain_and_gamma(self):
        g = WeatherGenerator(n_days=20_000, p_wet_given_dry=0.25, p_wet_given_wet=0.55)
        df = g.generate()
        fit = fit_markov_chain(df["is_rainy_day"])
        assert fit.p_wet_given_dry == pytest.approx(0.25, abs=0.015)
        assert fit.p_wet_given_wet == pytest.approx(0.55, abs=0.02)
        amounts = df.loc[df["is_rainy_day"], "precipitation"]
        shape, _, scale = stats.gamma.fit(amounts, floc=0)
        assert shape == pytest.approx(0.75, rel=0.08)
        assert shape * scale == pytest.approx(6.0, rel=0.06)

    @pytest.mark.statistical
    def test_trend_detected_and_estimated(self):
        g = WeatherGenerator(n_days=365 * 40 + 10, warming_trend_c_per_decade=0.5)
        s = g.calculate_statistics(g.generate())
        assert s["trend_test_resolution"] == "annual"
        assert s["mann_kendall"]["p_value"] < 0.01
        lo, hi = s["sens_slope_ci_c_per_decade"]
        assert lo < 0.5 < hi
        assert s["harmonic_fit"]["amplitudes"][0] == pytest.approx(10, abs=0.5)

    def test_short_series_uses_monthly_resolution(self):
        g = WeatherGenerator(n_days=400)
        s = g.calculate_statistics(g.generate())
        assert s["trend_test_resolution"] == "monthly"
        assert "variance_inflation" in s["mann_kendall"]["details"]

    def test_monthly_summary_does_not_mutate(self):
        g = WeatherGenerator(n_days=90)
        df = g.generate()
        cols = list(df.columns)
        summary = g.generate_monthly_summary(df)
        assert list(df.columns) == cols
        assert len(summary) == 3 and "precipitation_sum" in summary

    def test_helpers(self):
        g = WeatherGenerator()
        assert g._classify_weather(20, 15, 5) == "Heavy Rain"
        assert g._classify_weather(-5, 0, 5) == "Freezing"
        assert g._get_season(200) == "Summer"

    @pytest.mark.parametrize(
        "bad",
        [{"n_days": 1}, {"hemisphere": "east"}, {"p_wet_given_dry": 1.5}, {"temperature_persistence": 1}, {"precipitation_shape": 0}],
    )
    def test_invalid(self, bad):
        with pytest.raises(InvalidParameterError):
            WeatherGenerator(**bad)
