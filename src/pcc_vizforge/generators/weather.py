"""WGEN-style stochastic daily weather generator.

Model (after Richardson, 1981)
------------------------------
*Precipitation occurrence* is a two-state first-order Markov chain with
transition probabilities :math:`p_{01} = P(\\text{wet} | \\text{dry})` and
:math:`p_{11} = P(\\text{wet} | \\text{wet})`; *amounts* on wet days are
Gamma distributed.

*Temperature*: the daily mean is

.. math::
    T_t = \\bar T + A \\sin\\!\\left(\\frac{2\\pi (d_t - \\phi)}{365.25}\\right)
          + \\tau \\frac{t}{3652.5} + \\delta\\,\\mathbb{1}[\\text{wet}_t] + \\varepsilon_t,

where the anomaly :math:`\\varepsilon_t` is a stationary AR(1) process with
standard deviation ``temperature_variation`` and lag-1 autocorrelation
``temperature_persistence``, and :math:`\\tau` is a linear warming trend in
°C per decade. The diurnal range is narrower on wet (cloudy) days.

*Humidity* is derived physically: the dew point is the daily minimum minus a
stochastic depression (smaller on wet days), and relative humidity follows
from the Magnus formula, so RH ∈ [0, 100]. The heat index is evaluated at the
daily maximum temperature with the corresponding (afternoon) humidity.

*Wind* is Weibull distributed (stronger on wet days) and *pressure* is an
AR(1) process around 1013.25 hPa, depressed on wet days.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any, ClassVar

import numpy as np
import pandas as pd
from scipy.special import gamma as gamma_fn

from pcc_vizforge.analysis.timeseries import (
    fit_harmonics,
    fit_markov_chain,
    heat_index_c,
    mann_kendall,
    relative_humidity,
)
from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.generators.base import BaseGenerator, GeneratorParams

__all__ = ["WeatherGenerator", "WeatherParams", "ar1"]

STANDARD_PRESSURE_HPA = 1013.25
SEASONS_NORTH = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
                 6: "Summer", 7: "Summer", 8: "Summer", 9: "Autumn", 10: "Autumn", 11: "Autumn"}
FLIP = {"Winter": "Summer", "Summer": "Winter", "Spring": "Autumn", "Autumn": "Spring"}


def ar1(rng: np.random.Generator, n: int, phi: float, sigma: float) -> np.ndarray:
    """Stationary AR(1) series with marginal standard deviation ``sigma``."""
    eps = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = eps[0] * sigma
    innov = sigma * np.sqrt(1.0 - phi**2)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + innov * eps[t]
    return x


@dataclasses.dataclass(frozen=True)
class WeatherParams(GeneratorParams):
    """Parameters of the stochastic weather generator."""

    n_days: int = 365
    start_date: str = "2023-01-01"
    hemisphere: str = "north"
    # temperature
    base_temperature: float = 15.0
    seasonal_amplitude: float = 10.0
    seasonal_phase_days: float = 110.0
    temperature_variation: float = 3.0
    temperature_persistence: float = 0.7
    warming_trend_c_per_decade: float = 0.0
    wet_day_temperature_offset: float = -1.0
    diurnal_range_dry: float = 11.0
    diurnal_range_wet: float = 6.0
    # precipitation
    p_wet_given_dry: float = 0.2
    p_wet_given_wet: float = 0.6
    precipitation_shape: float = 0.75
    precipitation_mean_mm: float = 6.0
    # moisture, wind, pressure
    dewpoint_depression_dry: float = 3.0
    dewpoint_depression_wet: float = 0.5
    wind_weibull_shape: float = 2.0
    wind_mean_dry: float = 12.0
    wind_mean_wet: float = 20.0
    pressure_std: float = 8.0
    pressure_persistence: float = 0.8
    wet_day_pressure_offset: float = -6.0
    # Legacy keys. ``precipitation_probability`` (stationary wet-day
    # probability) is mapped onto p01; the humidity keys are accepted but
    # ignored because humidity is now derived from the dew point.
    humidity_base: float | None = None
    humidity_variation: float | None = None
    precipitation_probability: float | None = None

    def validate(self) -> None:
        super().validate()
        if isinstance(self.n_days, bool) or not isinstance(self.n_days, (int, np.integer)) or self.n_days < 2:
            raise InvalidParameterError("n_days must be an integer >= 2")
        try:
            datetime.fromisoformat(str(self.start_date))
        except ValueError as exc:
            raise InvalidParameterError(f"start_date must be ISO formatted: {exc}") from exc
        if self.hemisphere not in ("north", "south"):
            raise InvalidParameterError("hemisphere must be 'north' or 'south'")
        for name in ("p_wet_given_dry", "p_wet_given_wet"):
            if not 0 <= getattr(self, name) <= 1:
                raise InvalidParameterError(f"{name} must be in [0, 1]")
        for name in ("temperature_persistence", "pressure_persistence"):
            if not -1 < getattr(self, name) < 1:
                raise InvalidParameterError(f"{name} must be in (-1, 1)")
        for name in (
            "temperature_variation",
            "precipitation_shape",
            "precipitation_mean_mm",
            "wind_weibull_shape",
            "wind_mean_dry",
            "wind_mean_wet",
            "pressure_std",
        ):
            if not getattr(self, name) > 0:
                raise InvalidParameterError(f"{name} must be > 0")
        for name in ("diurnal_range_dry", "diurnal_range_wet", "dewpoint_depression_dry", "dewpoint_depression_wet"):
            if getattr(self, name) < 0:
                raise InvalidParameterError(f"{name} must be >= 0")
        if self.precipitation_probability is not None and not 0 < self.precipitation_probability < 1:
            raise InvalidParameterError("precipitation_probability must be in (0, 1)")

    def transition_probabilities(self) -> tuple[float, float]:
        """(p01, p11), honouring the legacy ``precipitation_probability`` key.

        If only the stationary wet-day probability π is given, keep the
        configured persistence p11 and solve π = p01 / (1 - p11 + p01) for p01.
        """
        if self.precipitation_probability is None:
            return self.p_wet_given_dry, self.p_wet_given_wet
        pi, p11 = self.precipitation_probability, self.p_wet_given_wet
        p01 = pi * (1 - p11) / (1 - pi)
        return float(min(max(p01, 0.0), 1.0)), p11


class WeatherGenerator(BaseGenerator[WeatherParams]):
    """Generator for daily weather series."""

    domain: ClassVar[str] = "weather"
    params_cls: ClassVar[type[GeneratorParams]] = WeatherParams
    output_filename: ClassVar[str] = "weather_data.csv"

    def __init__(self, config_name: str | None = "weather", **kwargs: Any) -> None:
        super().__init__(config_name, **kwargs)

    def _simulate(self, params: WeatherParams, rng: np.random.Generator) -> pd.DataFrame:
        p = params
        n = p.n_days
        dates = pd.date_range(datetime.fromisoformat(str(p.start_date)), periods=n, freq="D")
        doy = dates.dayofyear.to_numpy()
        t = np.arange(n, dtype=float)

        # --- precipitation occurrence: 2-state Markov chain --------------- #
        p01, p11 = p.transition_probabilities()
        pi = p01 / (1 - p11 + p01) if (1 - p11 + p01) > 0 else 0.0
        u = rng.random(n)
        wet = np.empty(n, dtype=bool)
        wet[0] = u[0] < pi
        for i in range(1, n):
            wet[i] = u[i] < (p11 if wet[i - 1] else p01)
        scale = p.precipitation_mean_mm / p.precipitation_shape
        precip = np.where(wet, rng.gamma(p.precipitation_shape, scale, n), 0.0)

        # --- temperature --------------------------------------------------- #
        phase_sign = 1.0 if p.hemisphere == "north" else -1.0
        seasonal = phase_sign * p.seasonal_amplitude * np.sin(2 * np.pi * (doy - p.seasonal_phase_days) / 365.25)
        trend = p.warming_trend_c_per_decade * t / 3652.5
        anomaly = ar1(rng, n, p.temperature_persistence, p.temperature_variation)
        t_mean = p.base_temperature + seasonal + trend + anomaly + p.wet_day_temperature_offset * wet
        dtr = np.where(wet, p.diurnal_range_wet, p.diurnal_range_dry) * rng.lognormal(0.0, 0.15, n)
        t_min, t_max = t_mean - dtr / 2, t_mean + dtr / 2

        def diurnal(hour: float) -> np.ndarray:
            # Cosine diurnal cycle peaking at 15:00 local time.
            return t_mean + dtr / 2 * np.cos(2 * np.pi * (hour - 15.0) / 24.0)

        # --- humidity from dew point -------------------------------------- #
        depression = np.where(wet, p.dewpoint_depression_wet, p.dewpoint_depression_dry)
        dewpoint = t_min - rng.gamma(2.0, depression / 2.0 + 1e-9, n)
        dewpoint = np.minimum(dewpoint, t_mean)
        rh = relative_humidity(t_mean, dewpoint)

        # --- wind & pressure ----------------------------------------------- #
        k = p.wind_weibull_shape
        wind_mean = np.where(wet, p.wind_mean_wet, p.wind_mean_dry)
        wind = rng.weibull(k, n) * wind_mean / gamma_fn(1 + 1 / k)
        pressure = (
            STANDARD_PRESSURE_HPA
            + ar1(rng, n, p.pressure_persistence, p.pressure_std)
            + p.wet_day_pressure_offset * wet
        )
        cloud = np.clip(100 / (1 + np.exp(-(rh - 70) / 8)) + 25 * wet + rng.normal(0, 8, n), 0, 100)

        month = dates.month.to_numpy()
        season = np.array([SEASONS_NORTH[m] for m in month], dtype=object)
        if p.hemisphere == "south":
            season = np.array([FLIP[s] for s in season], dtype=object)

        df = pd.DataFrame(
            {
                "date": dates,
                "day_of_year": doy,
                "temperature_avg": t_mean,
                "temperature_morning": diurnal(6.0),
                "temperature_afternoon": diurnal(15.0),
                "temperature_evening": diurnal(20.0),
                "temperature_night": diurnal(2.0),
                "temperature_min": t_min,
                "temperature_max": t_max,
                "temperature_anomaly": anomaly,
                "dewpoint": dewpoint,
                "humidity": rh,
                "precipitation": precip,
                "wind_speed": wind,
                "pressure": pressure,
                "cloud_cover": cloud,
                "season": season,
            }
        )
        df["weather_type"] = self._classify_weather_vec(t_mean, precip, wind)
        df["temperature_range"] = df["temperature_max"] - df["temperature_min"]
        df["is_rainy_day"] = wet
        df["heat_index"] = heat_index_c(t_max, relative_humidity(t_max, dewpoint))
        df["comfort_index"] = self._calculate_comfort_index(df["temperature_avg"], df["humidity"])
        return df

    # ------------------------------------------------------------------ #
    @staticmethod
    def _classify_weather_vec(temp: np.ndarray, precip: np.ndarray, wind: np.ndarray) -> np.ndarray:
        conditions = [precip > 10, precip > 0, wind > 25, temp > 30, temp < 0]
        choices = ["Heavy Rain", "Light Rain", "Windy", "Hot", "Freezing"]
        return np.select(conditions, choices, default="Clear")

    def _classify_weather(self, temp: float, precip: float, wind: float) -> str:
        return str(self._classify_weather_vec(np.array([temp]), np.array([precip]), np.array([wind]))[0])

    def _get_season(self, day_of_year: int) -> str:
        month = (datetime(2023, 1, 1) + pd.Timedelta(days=day_of_year - 1)).month
        season = SEASONS_NORTH[month]
        return FLIP[season] if self.params.hemisphere == "south" else season

    @staticmethod
    def _calculate_comfort_index(temp: pd.Series, humidity: pd.Series) -> pd.Series:
        """Heuristic comfort score in [0, 100] (optimum 22 °C, 45 % RH)."""
        temp_comfort = 100 - np.abs(temp - 22) * 4
        humidity_comfort = 100 - np.abs(humidity - 45) * 2
        return np.clip((temp_comfort + humidity_comfort) / 2, 0, 100)

    # ------------------------------------------------------------------ #
    # Analysis
    # ------------------------------------------------------------------ #
    def generate_monthly_summary(self, data: pd.DataFrame) -> pd.DataFrame:
        """Monthly aggregates (does not mutate ``data``)."""
        d = data.assign(month=data["date"].dt.month, year=data["date"].dt.year)
        monthly = d.groupby(["year", "month"]).agg(
            temperature_avg_mean=("temperature_avg", "mean"),
            temperature_avg_std=("temperature_avg", "std"),
            temperature_min_min=("temperature_min", "min"),
            temperature_max_max=("temperature_max", "max"),
            humidity_mean=("humidity", "mean"),
            precipitation_sum=("precipitation", "sum"),
            precipitation_mean=("precipitation", "mean"),
            wind_speed_mean=("wind_speed", "mean"),
            pressure_mean=("pressure", "mean"),
            is_rainy_day_sum=("is_rainy_day", "sum"),
        )
        return monthly.round(2).reset_index()

    def calculate_statistics(self, data: pd.DataFrame) -> dict[str, Any]:
        """Seasonal cycle, trend tests and precipitation-occurrence diagnostics."""
        t = (data["date"] - data["date"].iloc[0]).dt.days.to_numpy(dtype=float)
        temp = data["temperature_avg"].to_numpy()
        harmonic = fit_harmonics(t, temp, n_harmonics=1)
        stats: dict[str, Any] = {
            "n_days": len(data),
            "temperature_mean": float(temp.mean()),
            "harmonic_fit": harmonic.to_dict(),
            "trend_c_per_decade": harmonic.trend_per_unit * 3652.5,
            # Newey-West HAC SE: daily anomalies are autocorrelated, so the OLS
            # SE (also reported) is far too small.
            "trend_se_c_per_decade_hac": harmonic.trend_stderr_hac * 3652.5,
            "trend_se_c_per_decade_ols": harmonic.trend_stderr * 3652.5,
            "wet_day_fraction": float(data["is_rainy_day"].mean()),
            "total_precipitation_mm": float(data["precipitation"].sum()),
            "humidity_temperature_correlation": float(np.corrcoef(temp, data["humidity"])[0, 1]),
        }
        try:
            stats["markov_chain"] = fit_markov_chain(data["is_rainy_day"]).to_dict()
        except InvalidParameterError:
            stats["markov_chain"] = None
        # Trend test on deseasonalised anomalies. Following standard
        # climatological practice we aggregate to annual means when at least
        # three full years are available (removing most serial correlation),
        # otherwise to monthly means with the Hamed-Rao correction.
        deseason = pd.Series(temp - harmonic.predict(t) + harmonic.trend_per_unit * t, index=data["date"])
        annual = deseason.groupby(deseason.index.year).agg(["mean", "size"])
        annual = annual[annual["size"] >= 365]["mean"]
        if annual.size >= 4:
            mk = mann_kendall(annual.to_numpy())
            per_decade, resolution = 10.0, "annual"
        else:
            monthly = deseason.resample("MS").mean().dropna()
            if monthly.size < 4:
                return stats
            mk = mann_kendall(monthly.to_numpy(), correction="hamed_rao")
            per_decade, resolution = 120.0, "monthly"
        stats["mann_kendall"] = mk.to_dict()
        stats["trend_test_resolution"] = resolution
        stats["sens_slope_c_per_decade"] = mk.details["sens_slope"] * per_decade
        lo, hi = mk.details["sens_slope_ci"]
        stats["sens_slope_ci_c_per_decade"] = (lo * per_decade, hi * per_decade)
        return stats
