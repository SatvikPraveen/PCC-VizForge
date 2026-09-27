"""Synthetic earthquake catalogues with Gutenberg-Richter magnitudes and
ETAS-style aftershock clustering.

Model
-----
*Background* events form a homogeneous Poisson process in time over
``duration_days``. Their epicentres are drawn from a mixture of Gaussian
"hotspots" (tectonic regions) and a background that is uniform **on the
sphere** (latitude via :math:`\\arcsin` of a uniform variate -- sampling
latitude uniformly would over-populate the poles).

*Magnitudes* follow the doubly-truncated Gutenberg-Richter law
:math:`f(m) \\propto 10^{-b m}` on ``magnitude_range``.

*Aftershocks* (optional) follow the epidemic-type aftershock sequence (ETAS)
branching structure of Ogata (1988): an event of magnitude *m* triggers
:math:`\\mathrm{Poisson}(K\\,10^{\\alpha (m - M_c)})` direct aftershocks with
Omori-Utsu delays :math:`\\propto (t + c)^{-p}`, G-R magnitudes and
epicentres scattered around the parent with a magnitude-dependent length
scale :math:`d_0\\,10^{0.5 (m - M_c)}` km. Aftershocks trigger their own
aftershocks up to ``max_generations``. The expected number of direct
offspring per event (the *branching ratio*) must be < 1 for a stationary,
non-explosive process; this is checked at validation time.

References
----------
Gutenberg, B. & Richter, C. F. (1944). Frequency of earthquakes in
    California. *BSSA* 34(4), 185-188.
Ogata, Y. (1988). Statistical models for earthquake occurrences and
    residual analysis for point processes. *JASA* 83(401), 9-27.
Helmstetter, A. & Sornette, D. (2002). Subcritical and supercritical regimes
    in epidemic models of earthquake aftershocks. *JGR* 107(B10), 2237.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any, ClassVar

import numpy as np
import pandas as pd

from pcc_vizforge.analysis.seismology import (
    EARTH_RADIUS_KM,
    b_value_mle,
    b_value_mle_truncated,
    interevent_cv,
    magnitude_of_completeness,
    omori_sample_delays,
    seismic_energy_joules,
    seismic_moment_nm,
    truncated_gr_sample,
)
from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.generators.base import BaseGenerator, GeneratorParams

__all__ = ["EarthquakeGenerator", "EarthquakeParams", "branching_ratio"]

MAGNITUDE_CLASSES = (
    (3.0, "Micro"),
    (4.0, "Minor"),
    (5.0, "Light"),
    (6.0, "Moderate"),
    (7.0, "Strong"),
    (8.0, "Major"),
    (np.inf, "Great"),
)
DEPTH_CLASSES = ((70.0, "Shallow"), (300.0, "Intermediate"), (np.inf, "Deep"))


def branching_ratio(
    b_value: float, alpha: float, productivity: float, m_min: float, m_max: float
) -> float:
    """Expected number of direct aftershocks per event, E[K 10^{α(M - Mc)}]."""
    beta, a = b_value * np.log(10.0), alpha * np.log(10.0)
    L = m_max - m_min
    if np.isinf(L):
        return float(np.inf) if a >= beta else float(productivity * beta / (beta - a))
    if abs(beta - a) < 1e-12:
        return float(productivity * beta * L / (1.0 - np.exp(-beta * L)))
    return float(
        productivity
        * beta
        / (beta - a)
        * (1.0 - np.exp(-(beta - a) * L))
        / (1.0 - np.exp(-beta * L))
    )


@dataclasses.dataclass(frozen=True)
class EarthquakeParams(GeneratorParams):
    """Parameters of the earthquake catalogue generator."""

    n_earthquakes: int = 500
    magnitude_range: tuple[float, float] = (2.0, 8.5)
    b_value: float = 1.0
    depth_range: tuple[float, float] = (1.0, 700.0)
    lat_range: tuple[float, float] = (-90.0, 90.0)
    lon_range: tuple[float, float] = (-180.0, 180.0)
    hotspots: tuple[Any, ...] = ()
    duration_days: float = 365.0
    start_date: str = "2023-01-01"
    shallow_fraction: float = 0.7
    shallow_depth_scale_km: float = 20.0
    magnitude_bin: float = 0.0
    aftershocks: Any = None  # mapping; see configs/quakes.yaml

    # --- derived accessors ------------------------------------------------ #
    @property
    def aftershock_cfg(self) -> dict[str, Any]:
        defaults = {
            "enabled": False,
            "productivity": 0.02,
            "alpha": 0.8,
            "omori_c_days": 0.01,
            "omori_p": 1.1,
            "distance_km": 5.0,
            "max_generations": 10,
        }
        raw = dict(self.aftershocks) if self.aftershocks else {}
        return {**defaults, **raw}

    @property
    def hotspot_list(self) -> list[dict[str, Any]]:
        return [dict(h) for h in self.hotspots]

    def validate(self) -> None:
        super().validate()
        if (
            isinstance(self.n_earthquakes, bool)
            or not isinstance(self.n_earthquakes, (int, np.integer))
            or self.n_earthquakes < 1
        ):
            raise InvalidParameterError("n_earthquakes must be a positive integer")
        m_lo, m_hi = self.magnitude_range
        if not m_hi > m_lo:
            raise InvalidParameterError("magnitude_range must be increasing")
        if not self.b_value > 0:
            raise InvalidParameterError("b_value must be > 0")
        d_lo, d_hi = self.depth_range
        if not 0 <= d_lo < d_hi:
            raise InvalidParameterError("depth_range must satisfy 0 <= min < max")
        la, lb = self.lat_range
        if not -90 <= la < lb <= 90:
            raise InvalidParameterError(
                "lat_range must lie within [-90, 90] and be increasing"
            )
        oa, ob = self.lon_range
        if not -180 <= oa < ob <= 180:
            raise InvalidParameterError(
                "lon_range must lie within [-180, 180] and be increasing"
            )
        if not self.duration_days > 0:
            raise InvalidParameterError("duration_days must be > 0")
        if not 0 <= self.shallow_fraction <= 1:
            raise InvalidParameterError("shallow_fraction must be in [0, 1]")
        if self.magnitude_bin < 0:
            raise InvalidParameterError("magnitude_bin must be >= 0")
        try:
            start = datetime.fromisoformat(str(self.start_date))
        except ValueError as exc:
            raise InvalidParameterError(
                f"start_date must be ISO formatted: {exc}"
            ) from exc
        # pandas nanosecond timestamps only span years 1677-2262.
        span_days = (pd.Timestamp.max - pd.Timestamp(start)).days
        if self.duration_days >= span_days:
            raise InvalidParameterError(
                "start_date + duration_days exceeds the representable timestamp range"
            )
        total = 0.0
        for h in self.hotspot_list:
            missing = {
                "name",
                "lat_center",
                "lon_center",
                "lat_range",
                "lon_range",
                "probability",
            } - set(h)
            if missing:
                raise InvalidParameterError(f"hotspot missing keys: {sorted(missing)}")
            if h["probability"] < 0:
                raise InvalidParameterError("hotspot probabilities must be >= 0")
            total += h["probability"]
        if total > 1 + 1e-9:
            raise InvalidParameterError(f"hotspot probabilities sum to {total} > 1")
        a = self.aftershock_cfg
        if a["enabled"]:
            for key in ("productivity", "omori_c_days", "omori_p", "distance_km"):
                if not a[key] > 0:
                    raise InvalidParameterError(f"aftershocks.{key} must be > 0")
            if a["alpha"] < 0:
                raise InvalidParameterError("aftershocks.alpha must be >= 0")
            n_br = branching_ratio(
                self.b_value, a["alpha"], a["productivity"], m_lo, m_hi
            )
            if n_br >= 1:
                raise InvalidParameterError(
                    f"ETAS branching ratio {n_br:.3f} >= 1 (supercritical); lower productivity or alpha"
                )


class EarthquakeGenerator(BaseGenerator[EarthquakeParams]):
    """Generator for synthetic earthquake catalogues (sorted by origin time)."""

    domain: ClassVar[str] = "quakes"
    params_cls: ClassVar[type[GeneratorParams]] = EarthquakeParams
    output_filename: ClassVar[str] = "earthquake_data.csv"

    def __init__(self, config_name: str | None = "quakes", **kwargs: Any) -> None:
        super().__init__(config_name, **kwargs)

    # ------------------------------------------------------------------ #
    # Simulation
    # ------------------------------------------------------------------ #
    def _background_locations(
        self, p: EarthquakeParams, rng: np.random.Generator, n: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        hotspots = p.hotspot_list
        probs = np.array([h["probability"] for h in hotspots] + [0.0])
        probs[-1] = max(0.0, 1.0 - probs[:-1].sum())
        choice = rng.choice(len(probs), size=n, p=probs / probs.sum())
        lat = np.empty(n)
        lon = np.empty(n)
        region = np.empty(n, dtype=object)

        glob = choice == len(hotspots)
        k = int(glob.sum())
        s_lo, s_hi = np.sin(np.radians(p.lat_range))
        lat[glob] = np.degrees(np.arcsin(rng.uniform(s_lo, s_hi, k)))
        lon[glob] = rng.uniform(*p.lon_range, k)
        region[glob] = "Global"
        for i, h in enumerate(hotspots):
            sel = choice == i
            m = int(sel.sum())
            lat[sel] = rng.normal(h["lat_center"], h["lat_range"] / 6.0, m)
            lon[sel] = rng.normal(h["lon_center"], h["lon_range"] / 6.0, m)
            region[sel] = h["name"]
        return lat, lon, region

    def _depths(
        self, p: EarthquakeParams, rng: np.random.Generator, n: int
    ) -> np.ndarray:
        d_lo, d_hi = p.depth_range
        shallow = rng.random(n) < p.shallow_fraction
        depth = np.where(
            shallow,
            d_lo + rng.exponential(p.shallow_depth_scale_km, n),
            rng.uniform(min(50.0, d_hi), d_hi, n),
        )
        return np.clip(depth, d_lo, d_hi)

    def _simulate(
        self, params: EarthquakeParams, rng: np.random.Generator
    ) -> pd.DataFrame:
        p = params
        m_lo, m_hi = p.magnitude_range
        n0 = p.n_earthquakes

        times = [rng.uniform(0.0, p.duration_days, n0)]
        mags = [truncated_gr_sample(rng, n0, p.b_value, m_lo, m_hi)]
        lat0, lon0, reg0 = self._background_locations(p, rng, n0)
        lats, lons, regions = [lat0], [lon0], [reg0]
        parents = [np.full(n0, -1)]
        gens = [np.zeros(n0, dtype=int)]

        a = p.aftershock_cfg
        if a["enabled"]:
            offset = n0
            cur_idx = np.arange(n0)
            cur_t, cur_m, cur_lat, cur_lon, cur_reg = (
                times[0],
                mags[0],
                lat0,
                lon0,
                reg0,
            )
            for gen in range(1, int(a["max_generations"]) + 1):
                expected = a["productivity"] * np.power(
                    10.0, a["alpha"] * (cur_m - m_lo)
                )
                n_children = rng.poisson(expected)
                total = int(n_children.sum())
                if total == 0:
                    break
                par = np.repeat(np.arange(cur_t.size), n_children)
                delays = omori_sample_delays(
                    rng, total, a["omori_c_days"], a["omori_p"], p.duration_days
                )
                t_child = cur_t[par] + delays
                keep = t_child < p.duration_days
                par, t_child = par[keep], t_child[keep]
                total = int(par.size)
                if total == 0:
                    break
                m_child = truncated_gr_sample(rng, total, p.b_value, m_lo, m_hi)
                # Isotropic Gaussian scatter on the tangent plane (km -> degrees).
                sigma = a["distance_km"] * np.power(10.0, 0.5 * (cur_m[par] - m_lo))
                dx, dy = rng.normal(0.0, 1.0, (2, total)) * sigma
                deg = 180.0 / (np.pi * EARTH_RADIUS_KM)
                lat_c = cur_lat[par] + dy * deg
                lon_c = cur_lon[par] + dx * deg / np.maximum(
                    np.cos(np.radians(cur_lat[par])), 1e-3
                )
                reg_c = cur_reg[par]

                times.append(t_child)
                mags.append(m_child)
                lats.append(lat_c)
                lons.append(lon_c)
                regions.append(reg_c)
                parents.append(cur_idx[par])
                gens.append(np.full(total, gen))

                cur_idx = np.arange(offset, offset + total)
                offset += total
                cur_t, cur_m, cur_lat, cur_lon, cur_reg = (
                    t_child,
                    m_child,
                    lat_c,
                    lon_c,
                    reg_c,
                )

        t = np.concatenate(times)
        mag = np.concatenate(mags)
        lat = np.concatenate(lats)
        lon = np.concatenate(lons)
        region = np.concatenate(regions)
        parent = np.concatenate(parents)
        gen_arr = np.concatenate(gens)

        # Wrap longitude, reflect latitude, then clip to configured window.
        lon = (lon + 180.0) % 360.0 - 180.0
        lat = np.clip(lat, -90.0, 90.0)
        lat = np.clip(lat, *p.lat_range)
        lon = np.clip(lon, *p.lon_range)
        if p.magnitude_bin > 0:
            mag = np.round(mag / p.magnitude_bin) * p.magnitude_bin
        depth = self._depths(p, rng, t.size)

        order = np.argsort(t, kind="stable")
        new_id = np.empty_like(order)
        new_id[order] = np.arange(order.size)
        parent_sorted = np.where(
            parent[order] >= 0, new_id[np.maximum(parent[order], 0)], -1
        )

        start = datetime.fromisoformat(str(p.start_date))
        ts = pd.to_datetime(start) + pd.to_timedelta(t[order], unit="D")
        df = pd.DataFrame(
            {
                "earthquake_id": np.arange(order.size),
                "timestamp": ts,
                "time_days": t[order],
                "latitude": lat[order],
                "longitude": lon[order],
                "magnitude": mag[order],
                "depth_km": depth,
                "region": region[order].astype(str),
                "in_hotspot": region[order] != "Global",
                "parent_id": parent_sorted,
                "generation": gen_arr[order],
            }
        )
        df["is_aftershock"] = df["generation"] > 0
        df["day_of_year"] = df["timestamp"].dt.dayofyear
        df["hour"] = df["timestamp"].dt.hour
        df["magnitude_category"] = self._classify(
            df["magnitude"].to_numpy(), MAGNITUDE_CLASSES
        )
        df["depth_category"] = self._classify(df["depth_km"].to_numpy(), DEPTH_CLASSES)
        df["energy_joules"] = seismic_energy_joules(df["magnitude"])
        df["seismic_moment_nm"] = seismic_moment_nm(df["magnitude"])
        df["distance_from_equator"] = df["latitude"].abs()
        return df

    @staticmethod
    def _classify(
        values: np.ndarray, classes: tuple[tuple[float, str], ...]
    ) -> np.ndarray:
        edges = np.array([c[0] for c in classes])
        labels = np.array([c[1] for c in classes], dtype=object)
        return labels[
            np.searchsorted(edges, values, side="right").clip(max=len(labels) - 1)
        ]

    # Legacy helpers kept for API compatibility.
    def _categorize_magnitude(self, mag: float) -> str:
        return str(self._classify(np.array([mag]), MAGNITUDE_CLASSES)[0])

    def _categorize_depth(self, depth: float) -> str:
        return str(self._classify(np.array([depth]), DEPTH_CLASSES)[0])

    # ------------------------------------------------------------------ #
    # Analysis
    # ------------------------------------------------------------------ #
    def calculate_statistics(self, data: pd.DataFrame) -> dict[str, Any]:
        """Descriptive statistics plus b-value, Mc and clustering diagnostics."""
        p = self.params
        m_lo, m_hi = p.magnitude_range
        mags = data["magnitude"].to_numpy()
        bw = p.magnitude_bin if p.magnitude_bin > 0 else 0.1
        stats: dict[str, Any] = {
            "total_earthquakes": len(data),
            "n_aftershocks": int(data.get("is_aftershock", pd.Series(False)).sum()),
            "magnitude_stats": {
                "mean": float(mags.mean()),
                "median": float(np.median(mags)),
                "max": float(mags.max()),
                "min": float(mags.min()),
                "std": float(mags.std(ddof=1)) if mags.size > 1 else 0.0,
            },
            "depth_stats": {
                "mean": float(data["depth_km"].mean()),
                "median": float(data["depth_km"].median()),
                "max": float(data["depth_km"].max()),
                "min": float(data["depth_km"].min()),
            },
            "regional_distribution": data["region"].value_counts().to_dict(),
            "magnitude_categories": data["magnitude_category"].value_counts().to_dict(),
            "depth_categories": data["depth_category"].value_counts().to_dict(),
            "total_energy_released": float(data["energy_joules"].sum()),
            "true_b_value": p.b_value,
            "mc_maxc": magnitude_of_completeness(mags, bin_width=bw),
        }
        if mags.size >= 2:
            stats["b_value_aki"] = b_value_mle(
                mags, m_lo, bin_width=p.magnitude_bin
            ).to_dict()
            stats["b_value_truncated"] = b_value_mle_truncated(
                mags, m_lo - p.magnitude_bin / 2, m_hi + p.magnitude_bin / 2
            ).to_dict()
        if "time_days" in data and len(data) >= 3:
            stats["interevent_cv"] = interevent_cv(data["time_days"])
        return stats
