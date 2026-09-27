"""Synthetic GitHub repository statistics with heavy-tailed popularity.

Model
-----
Each repository has a latent *popularity* :math:`\\pi_i` drawn from a
Pareto distribution with pdf exponent ``popularity_exponent`` (α) and an age
:math:`a_i` (days). Counts are then conditionally Poisson/negative-binomial:

* stars ~ Poisson(``stars_scale`` · π · (a/365)^``age_exponent``) -- Poisson
  mixing preserves the Pareto tail, so star counts have a power-law tail
  with the same exponent α (Clauset et al. 2009; empirical GitHub star
  distributions have α ≈ 2).
* forks | stars ~ Poisson(ρ · stars), per-repo fork propensity ρ ~ Beta.
* contributors = 1 + Poisson(``contributors_scale`` · √stars).
* commits ~ NegBin with mean ``commits_per_day`` · a · contributors^0.7.
* issues ~ Poisson(0.03 · stars + 0.2 · contributors).

All dates are relative to a fixed ``reference_date`` (not "now"), so the
output is exactly reproducible from the seed.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta
from typing import Any, ClassVar

import numpy as np
import pandas as pd

from pcc_vizforge.analysis.heavy_tails import compare_distributions, fit_power_law, gini
from pcc_vizforge.exceptions import InvalidParameterError
from pcc_vizforge.generators.base import BaseGenerator, GeneratorParams
from pcc_vizforge.rng import make_rng, resolve_seed
from pcc_vizforge.utils.io import get_data_directory, save_data

__all__ = ["GitHubGenerator", "GitHubParams"]

REPO_TYPES = ("library", "application", "framework", "tool", "game", "website")
LICENSES = ("MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "ISC", "None")
LICENSE_WEIGHTS = (0.4, 0.2, 0.15, 0.1, 0.05, 0.1)


@dataclasses.dataclass(frozen=True)
class GitHubParams(GeneratorParams):
    """Parameters of the GitHub repository generator."""

    n_repositories: int = 500
    languages: tuple[str, ...] = (
        "Python",
        "JavaScript",
        "TypeScript",
        "Java",
        "Go",
        "Rust",
        "C++",
    )
    language_weights: tuple[float, ...] | None = None
    reference_date: str = "2024-01-01"
    max_age_days: int = 3650
    popularity_exponent: float = 2.0
    stars_scale: float = 2.0
    age_exponent: float = 0.5
    fork_ratio_beta: tuple[float, float] = (2.0, 10.0)
    contributors_scale: float = 0.5
    commits_per_day: float = 0.3
    commits_dispersion: float = 1.5
    activity_days: int = 365
    # Legacy caps; clipping truncates the power-law tail, so they are off by default.
    stars_range: tuple[float, float] | None = None
    forks_range: tuple[float, float] | None = None
    issues_range: tuple[float, float] | None = None
    commits_range: tuple[float, float] | None = None

    def validate(self) -> None:
        super().validate()
        for name in ("n_repositories", "max_age_days", "activity_days"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v < 1:
                raise InvalidParameterError(f"{name} must be a positive integer")
        if not self.languages:
            raise InvalidParameterError("languages must be non-empty")
        if self.language_weights is not None:
            w = np.asarray(self.language_weights, dtype=float)
            if w.shape != (len(self.languages),) or np.any(w < 0) or w.sum() <= 0:
                raise InvalidParameterError(
                    "language_weights must be non-negative, one per language"
                )
        if not self.popularity_exponent > 1:
            raise InvalidParameterError("popularity_exponent must be > 1")
        for name in (
            "stars_scale",
            "contributors_scale",
            "commits_per_day",
            "commits_dispersion",
        ):
            if not getattr(self, name) > 0:
                raise InvalidParameterError(f"{name} must be > 0")
        if self.age_exponent < 0:
            raise InvalidParameterError("age_exponent must be >= 0")
        if len(self.fork_ratio_beta) != 2 or min(self.fork_ratio_beta) <= 0:
            raise InvalidParameterError("fork_ratio_beta must be two positive numbers")
        try:
            datetime.fromisoformat(str(self.reference_date))
        except ValueError as exc:
            raise InvalidParameterError(
                f"reference_date must be ISO formatted: {exc}"
            ) from exc


class GitHubGenerator(BaseGenerator[GitHubParams]):
    """Generator for synthetic repository-level GitHub statistics."""

    domain: ClassVar[str] = "github"
    params_cls: ClassVar[type[GeneratorParams]] = GitHubParams
    output_filename: ClassVar[str] = "github_data.csv"

    def __init__(self, config_name: str | None = "github", **kwargs: Any) -> None:
        super().__init__(config_name, **kwargs)

    def _simulate(self, params: GitHubParams, rng: np.random.Generator) -> pd.DataFrame:
        p = params
        n = p.n_repositories
        ref = pd.Timestamp(datetime.fromisoformat(str(p.reference_date)))

        lang_w = (
            None
            if p.language_weights is None
            else np.asarray(p.language_weights) / np.sum(p.language_weights)
        )
        language = rng.choice(np.array(p.languages, dtype=object), size=n, p=lang_w)
        repo_type = rng.choice(np.array(REPO_TYPES, dtype=object), size=n)
        license_type = rng.choice(
            np.array(LICENSES, dtype=object), size=n, p=LICENSE_WEIGHTS
        )

        age = rng.integers(30, p.max_age_days + 1, size=n)
        popularity = (1.0 - rng.random(n)) ** (-1.0 / (p.popularity_exponent - 1.0))
        stars = rng.poisson(
            p.stars_scale * popularity * (age / 365.0) ** p.age_exponent
        )
        fork_ratio = rng.beta(*p.fork_ratio_beta, size=n)
        forks = rng.poisson(fork_ratio * stars)
        watchers = 1 + rng.poisson(0.05 * stars)
        contributors = 1 + rng.poisson(p.contributors_scale * np.sqrt(stars))
        mean_commits = p.commits_per_day * age * contributors**0.7
        # Negative binomial parameterised by mean and dispersion k (var = μ + μ²/k)
        k = p.commits_dispersion
        commits = 1 + rng.negative_binomial(k, k / (k + mean_commits))
        issues = rng.poisson(0.03 * stars + 0.2 * contributors)
        size_kb = np.round(rng.lognormal(8.0, 2.0, n)).astype(np.int64)

        # Recency of the last update: busier repos are updated more recently.
        daily_rate = commits / age
        days_since_update = np.minimum(
            rng.exponential(1.0 / np.maximum(daily_rate, 1e-3)), age
        ).astype(int)

        def clip(values: np.ndarray, bounds: tuple[float, float] | None) -> np.ndarray:
            return values if bounds is None else np.clip(values, bounds[0], bounds[1])

        created = ref - pd.to_timedelta(age, unit="D")
        df = pd.DataFrame(
            {
                "repo_id": np.arange(n),
                "repo_name": [f"project_{i:04d}" for i in range(n)],
                "primary_language": language.astype(str),
                "repo_type": repo_type.astype(str),
                "stars": clip(stars, p.stars_range),
                "forks": clip(forks, p.forks_range),
                "watchers": watchers,
                "issues": clip(issues, p.issues_range),
                "commits": clip(commits, p.commits_range),
                "contributors": contributors,
                "size_kb": size_kb,
                "license": license_type.astype(str),
                "created_date": created,
                "last_updated": ref - pd.to_timedelta(days_since_update, unit="D"),
                "repo_age_days": age,
                "latent_popularity": popularity,
            }
        )
        df["is_active"] = days_since_update < 30
        df["stars_per_day"] = df["stars"] / df["repo_age_days"]
        df["commits_per_day"] = df["commits"] / df["repo_age_days"]
        df["popularity_score"] = (
            df["stars"] * 0.4
            + df["forks"] * 0.3
            + df["watchers"] * 0.2
            + df["contributors"] * 0.1
        )
        df["activity_score"] = (
            df["commits_per_day"] * 10 + df["is_active"].astype(int) * 5
        )
        df["fork_ratio"] = df["forks"] / (df["stars"] + 1)
        return df

    # ------------------------------------------------------------------ #
    def generate_activity_timeline(
        self,
        n_days: int | None = None,
        save_to_file: bool = False,
        seed: int | None = None,
    ) -> pd.DataFrame:
        """Daily aggregate activity with weekly and annual seasonality.

        Uses an RNG stream independent of :meth:`generate` (spawn key 1), so
        both outputs are reproducible from the same root seed.
        """
        p = self.params
        n_days = n_days or p.activity_days
        root = resolve_seed(seed if seed is not None else p.random_seed)
        rng = make_rng(np.random.SeedSequence(root, spawn_key=(1,)))
        ref = datetime.fromisoformat(str(p.reference_date))
        dates = pd.date_range(ref - timedelta(days=n_days), periods=n_days, freq="D")
        dow = dates.dayofweek.to_numpy()
        i = np.arange(n_days)
        weekend = np.where(dow >= 5, 0.3, 1.0)
        seasonal = 0.8 + 0.4 * np.sin(2 * np.pi * i / 365.25)
        commits = rng.poisson(5 * weekend * seasonal)
        prs = rng.poisson(2 * weekend)
        opened = rng.poisson(3 * weekend)
        closed = rng.poisson(2.5 * weekend)
        df = pd.DataFrame(
            {
                "date": dates,
                "day_of_week": dow,
                "commits": commits,
                "pull_requests": prs,
                "issues_opened": opened,
                "issues_closed": closed,
                "net_issues": opened - closed,
                "total_activity": commits + prs + opened + closed,
            }
        )
        df["cumulative_commits"] = df["commits"].cumsum()
        df["rolling_avg_activity"] = df["total_activity"].rolling(window=7).mean()
        if save_to_file:
            save_data(
                df, get_data_directory(self.domain) / "github_activity.csv", "csv"
            )
        return df

    def calculate_language_statistics(self, data: pd.DataFrame) -> dict[str, Any]:
        """Per-language aggregates."""
        agg = (
            data.groupby("primary_language")
            .agg(
                stars_count=("stars", "count"),
                stars_mean=("stars", "mean"),
                stars_sum=("stars", "sum"),
                forks_mean=("forks", "mean"),
                forks_sum=("forks", "sum"),
                commits_mean=("commits", "mean"),
                contributors_mean=("contributors", "mean"),
                popularity_score_mean=("popularity_score", "mean"),
            )
            .round(2)
        )
        return {
            "language_distribution": data["primary_language"].value_counts().to_dict(),
            "language_metrics": agg.to_dict(),
            "most_popular_language": data.groupby("primary_language")["stars"]
            .sum()
            .idxmax(),
            "most_active_language": data.groupby("primary_language")["commits"]
            .sum()
            .idxmax(),
        }

    def calculate_statistics(self, data: pd.DataFrame) -> dict[str, Any]:
        """Heavy-tail diagnostics for star counts (CSN power-law fit + Vuong tests)."""
        stars = data["stars"].to_numpy()
        out: dict[str, Any] = {
            "n_repositories": len(data),
            "stars_gini": gini(stars),
            "stars_median": float(np.median(stars)),
            "stars_max": int(stars.max()),
            "true_popularity_exponent": self.params.popularity_exponent,
            "star_fork_spearman": float(
                data[["stars", "forks"]].corr("spearman").to_numpy()[0, 1]
            ),
        }
        positive = stars[stars > 0]
        if positive.size >= 50:
            fit = fit_power_law(
                positive, discrete=True, min_tail=max(20, positive.size // 20)
            )
            out["power_law"] = fit.to_dict()
            out["vs_lognormal"] = compare_distributions(
                positive, fit, "lognormal"
            ).to_dict()
            out["vs_exponential"] = compare_distributions(
                positive, fit, "exponential"
            ).to_dict()
        return out
