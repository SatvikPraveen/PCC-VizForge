"""Smoke and contract tests for dashboards, diagnostic figures and styling."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import pytest

from pcc_vizforge import generators as G
from pcc_vizforge import plots as P
from pcc_vizforge.analysis import (
    diffusion,
    heavy_tails,
    probability,
    seismology,
    timeseries,
)
from pcc_vizforge.exceptions import VisualizationError
from pcc_vizforge.generators.random_walk import frame_to_positions, theoretical_msd
from pcc_vizforge.plots import diagnostics as D
from pcc_vizforge.plots.style import (
    CATEGORICAL,
    categorical,
    plotly_colorscale,
    publication_style,
    series_color,
)
from pcc_vizforge.utils.theming import get_color_palette

DASHBOARDS = [
    (G.RandomWalkGenerator, P.RandomWalkMatplotlibPlot, P.RandomWalkPlotlyPlot),
    (G.DiceGenerator, P.DiceMatplotlibPlot, P.DicePlotlyPlot),
    (G.WeatherGenerator, P.WeatherMatplotlibPlot, P.WeatherPlotlyPlot),
    (G.EarthquakeGenerator, P.EarthquakeMatplotlibPlot, P.EarthquakePlotlyPlot),
    (G.GitHubGenerator, P.GitHubMatplotlibPlot, P.GitHubPlotlyPlot),
]


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


@pytest.mark.parametrize(("gen", "mpl_cls", "plotly_cls"), DASHBOARDS, ids=lambda c: getattr(c, "__name__", ""))
def test_dashboards_render(gen, mpl_cls, plotly_cls, recwarn):
    data = gen().generate()
    for cls in (mpl_cls, plotly_cls):
        plotter = cls()
        for name in (n for n in dir(plotter) if n.startswith("plot")):
            fig = getattr(plotter, name)(data)
            assert isinstance(fig, (plt.Figure, go.Figure))
            if isinstance(fig, plt.Figure):
                # One y-axis per panel: no twinned axes sharing an x-axis.
                positions = [tuple(np.round(ax.get_position().bounds, 4)) for ax in fig.axes if ax.get_label() != "<colorbar>"]
                assert len(positions) == len(set(positions)), f"{cls.__name__}.{name} has overlaid axes"
            else:
                assert not any(getattr(fig.layout[k], "overlaying", None) for k in fig.layout if k.startswith("yaxis"))


def test_matplotlib_save(tmp_path, monkeypatch):
    import pcc_vizforge.utils.io as io

    monkeypatch.setattr(io, "IMAGE_EXPORT_DIR", tmp_path)
    plotter = P.DiceMatplotlibPlot()
    path = plotter.save(plotter.plot(G.DiceGenerator(n_rolls=50).generate()), "dice.png")
    assert (tmp_path / "dice.png").exists() and path.endswith("dice.png")


class TestStyle:
    def test_fixed_order_and_no_cycling(self):
        assert categorical(3) == list(CATEGORICAL[:3])
        assert series_color(0) == CATEGORICAL[0]
        with pytest.raises(VisualizationError):
            categorical(9)
        with pytest.raises(VisualizationError):
            get_color_palette("default", 9)

    def test_colormaps_registered(self):
        assert "pcc_sequential" in matplotlib.colormaps
        assert "pcc_diverging" in matplotlib.colormaps
        scale = plotly_colorscale()
        assert scale[0][0] == 0 and scale[-1][0] == 1

    def test_sequential_ramp_is_monotone_in_lightness(self):
        rgb = matplotlib.colormaps["pcc_sequential"](np.linspace(0, 1, 20))[:, :3]
        luminance = rgb @ [0.2126, 0.7152, 0.0722]
        assert np.all(np.diff(luminance) < 0)

    def test_publication_style_is_scoped(self):
        before = plt.rcParams["axes.spines.top"]
        with publication_style():
            assert plt.rcParams["pdf.fonttype"] == 42
            assert plt.rcParams["axes.spines.top"] is False
        assert plt.rcParams["axes.spines.top"] == before

    def test_plotly_template_registered(self):
        import plotly.io as pio

        assert {"pcc", "pcc_dark"} <= set(pio.templates)


class TestDiagnostics:
    def test_msd(self):
        g = G.RandomWalkGenerator(n_steps=200, n_walks=50, model="fbm", hurst=0.3)
        pos = frame_to_positions(g.generate())
        msd, sem = diffusion.ensemble_msd(pos)
        t = np.arange(1, 201)
        fit = diffusion.bootstrap_msd_exponent(pos, n_bootstrap=50, seed=0)
        fig = D.msd_figure(t, msd, sem, theory=theoretical_msd(g.params, t), fit=fit)
        ax = fig.axes[0]
        assert ax.get_xscale() == "log" and ax.get_yscale() == "log"
        assert "α" in " ".join(t.get_text() for t in ax.get_legend().get_texts())

    def test_dice(self):
        s, p = probability.sum_pmf(2, 6)
        fig = D.dice_sum_figure(s, p, np.round(p * 1000), p_value=0.5)
        assert "p = 0.5" in fig.axes[0].get_title(loc="left")

    def test_gutenberg_richter(self):
        m = seismology.truncated_gr_sample(np.random.default_rng(0), 2000, 1.0, 2.0)
        fig = D.gutenberg_richter_figure(m, seismology.b_value_mle(m, 2.0))
        assert fig.axes[0].get_yscale() == "log"

    def test_omori(self):
        t = seismology.omori_sample_delays(np.random.default_rng(0), 500, 0.05, 1.1, 100)
        D.omori_figure(t, seismology.fit_omori(t, 100))

    def test_ccdf(self):
        x = heavy_tails.sample_power_law(np.random.default_rng(0), 500, 2.5, 1.0)
        D.ccdf_figure(x, heavy_tails.fit_power_law(x))

    def test_temperature(self):
        w = G.WeatherGenerator(n_days=400).generate()
        t = np.arange(len(w), dtype=float)
        fig = D.temperature_figure(t, w["temperature_avg"], timeseries.fit_harmonics(t, w["temperature_avg"].to_numpy(), n_harmonics=1))
        assert "HAC" in " ".join(x.get_text() for x in fig.axes[0].get_legend().get_texts())

    def test_pvalue_calibration_and_axes_composition(self):
        fig, (a, b) = plt.subplots(1, 2)
        out = D.pvalue_calibration_figure(np.random.default_rng(0).random(100), ax=a)
        assert out is fig and a.get_xlim() == (0.0, 1.0)
        assert not b.lines
