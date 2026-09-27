"""Regenerate the README / docs figure gallery with fixed seeds.

Usage::

    python scripts/make_figures.py [--out docs/figures]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from pcc_vizforge.analysis import (
    diffusion,
    heavy_tails,
    probability,
    seismology,
    timeseries,
)
from pcc_vizforge.generators import (
    DiceGenerator,
    EarthquakeGenerator,
    GitHubGenerator,
    RandomWalkGenerator,
    WeatherGenerator,
)
from pcc_vizforge.generators.random_walk import frame_to_positions, theoretical_msd
from pcc_vizforge.plots import diagnostics as D

SEED = 20240101


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    figs = {}

    g = RandomWalkGenerator(
        n_steps=1000, n_walks=400, dimensions=2, model="fbm", hurst=0.35
    )
    pos = frame_to_positions(g.generate(seed=SEED))
    msd, sem = diffusion.ensemble_msd(pos)
    t = np.arange(1, msd.size + 1, dtype=float)
    fit = diffusion.bootstrap_msd_exponent(pos, seed=SEED)
    figs["msd"] = D.msd_figure(
        t, msd, sem, theory=theoretical_msd(g.params, t), fit=fit
    )

    d = DiceGenerator(n_rolls=3000, n_dice=3)
    report = d.calculate_probabilities(d.generate(seed=SEED))
    support, pmf = probability.sum_pmf(3, 6)
    counts = [report["sum_frequency_counts"][int(k)] for k in support]
    figs["dice"] = D.dice_sum_figure(
        support, pmf, counts, p_value=report["sum_gof"]["p_value"]
    )

    q = EarthquakeGenerator(n_earthquakes=5000)
    cat = q.generate(seed=SEED)
    figs["gutenberg_richter"] = D.gutenberg_richter_figure(
        cat["magnitude"], seismology.b_value_mle(cat["magnitude"], 2.0)
    )

    stars = GitHubGenerator(n_repositories=5000).generate(seed=SEED)["stars"].to_numpy()
    stars = stars[stars > 0]
    figs["stars_ccdf"] = D.ccdf_figure(
        stars,
        heavy_tails.fit_power_law(stars, discrete=True, min_tail=250),
        label="Stars",
    )

    w = WeatherGenerator(n_days=3653, warming_trend_c_per_decade=0.5).generate(
        seed=SEED
    )
    days = np.arange(len(w), dtype=float)
    temp = w["temperature_avg"].to_numpy()
    figs["temperature"] = D.temperature_figure(
        days, temp, timeseries.fit_harmonics(days, temp, n_harmonics=1)
    )

    for name, fig in figs.items():
        fig.savefig(out / f"{name}.png", dpi=150)
        plt.close(fig)
        print(f"wrote {out / name}.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("docs/figures"))
    main(parser.parse_args().out)
