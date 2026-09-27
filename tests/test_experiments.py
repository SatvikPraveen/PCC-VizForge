"""Integration tests for experiment runs, validation studies and the CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pytest
import yaml
from click.testing import CliRunner

from pcc_vizforge.cli import main
from pcc_vizforge.exceptions import ConfigurationError, InvalidParameterError
from pcc_vizforge.experiments import DOMAINS, run_experiment, run_study, verify_run
from pcc_vizforge.experiments.validation import STUDIES

SMALL = {
    "random_walk": [
        "data_generation.n_walks=20",
        "data_generation.n_steps=200",
        "data_generation.model=fbm",
    ],
    "dice": ["data_generation.n_rolls=300"],
    "weather": ["data_generation.n_days=400"],
    "quakes": ["data_generation.n_earthquakes=800"],
    "github": ["data_generation.n_repositories=600"],
}

pytestmark = pytest.mark.integration


@pytest.fixture
def redirect_exports(tmp_path, monkeypatch):
    import pcc_vizforge.utils.io as io

    monkeypatch.setattr(io, "IMAGE_EXPORT_DIR", tmp_path / "images")
    monkeypatch.setattr(io, "HTML_EXPORT_DIR", tmp_path / "html")
    monkeypatch.setattr(io, "DATA_DIR", tmp_path / "data")
    return tmp_path


@pytest.mark.parametrize("domain", sorted(DOMAINS))
def test_run_and_verify_every_domain(domain, tmp_path):
    result = run_experiment(
        domain,
        overrides=SMALL[domain],
        seed=11,
        output_dir=tmp_path,
        formats=("png", "pdf"),
    )
    run_dir = result.run_dir
    for name in ("config.yaml", "data.csv", "metrics.json", "manifest.json"):
        assert (run_dir / name).exists()
    assert result.figures and all(p.exists() for p in result.figures)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["seed"] == 11 and manifest["domain"] == domain
    assert set(manifest["outputs"]) >= {"config.yaml", "data.csv", "metrics.json"}
    # The saved config alone (with its recorded seed) reproduces the data.
    cfg = yaml.safe_load((run_dir / "config.yaml").read_text())
    assert cfg["data_generation"]["random_seed"] == 11
    report = verify_run(run_dir)
    assert report["reproduced"] and all(report["integrity"].values())


def test_default_random_walk_config_with_few_walks(tmp_path):
    """Regression: 5 lattice walks made bootstrap MSDs zero -> NaN CI -> crash."""
    r = run_experiment("random_walk", seed=12345, output_dir=tmp_path)
    lo, hi = r.metrics["msd_exponent"]["alpha_ci"]
    assert isinstance(lo, float) and lo < hi
    assert r.figures


def test_verify_detects_tampering(tmp_path):
    r = run_experiment(
        "dice", overrides=SMALL["dice"], seed=1, output_dir=tmp_path, figures=False
    )
    (r.run_dir / "data.csv").write_text("roll_id\n0\n")
    report = verify_run(r.run_dir)
    assert report["reproduced"]  # regeneration still matches the recorded hash...
    assert not report["integrity"]["data.csv"]  # ...but the stored file was altered


def test_run_records_fresh_seed_when_unseeded(tmp_path):
    r = run_experiment(
        "dice",
        config={"data_generation": {"n_rolls": 50}},
        output_dir=tmp_path,
        figures=False,
    )
    assert isinstance(r.manifest.seed, int)
    assert verify_run(r.run_dir)["reproduced"]


def test_run_metrics_content(tmp_path):
    r = run_experiment(
        "random_walk",
        overrides=[*SMALL["random_walk"], "data_generation.hurst=0.3"],
        seed=2,
        output_dir=tmp_path,
        figures=False,
    )
    m = r.metrics
    assert m["theoretical_exponent"] == pytest.approx(0.6)
    lo, hi = m["msd_exponent"]["alpha_ci"]
    assert lo < m["msd_exponent"]["alpha"] < hi
    assert "ergodicity_breaking" in m and "dfa_hurst_mean" in m


def test_unknown_domain(tmp_path):
    with pytest.raises(ConfigurationError):
        run_experiment("nope", output_dir=tmp_path)


@pytest.mark.parametrize("study", sorted(STUDIES))
def test_studies_run(study):
    res = run_study(study, n_replicates=5, seed=3)
    assert len(res.summary) > 0 and len(res.replicates) > 0
    again = run_study(study, n_replicates=5, seed=3)
    assert res.summary.equals(again.summary)


def test_unknown_study():
    with pytest.raises(InvalidParameterError):
        run_study("nope")


class TestCli:
    def test_help_and_version(self):
        r = CliRunner().invoke(main, ["--help"])
        assert r.exit_code == 0 and "run" in r.output and "verify" in r.output
        assert CliRunner().invoke(main, ["--version"]).exit_code == 0

    def test_run_verify_roundtrip(self, tmp_path):
        runner = CliRunner()
        r = runner.invoke(
            main,
            [
                "run",
                "dice",
                "--seed",
                "4",
                "--out",
                str(tmp_path),
                "--name",
                "d",
                "--set",
                "data_generation.n_rolls=100",
                "--no-figures",
            ],
        )
        assert r.exit_code == 0, r.output
        r = runner.invoke(main, ["verify", str(tmp_path / "d")])
        assert r.exit_code == 0 and "REPRODUCED" in r.output
        (tmp_path / "d" / "metrics.json").write_text("{}")
        r = runner.invoke(main, ["verify", str(tmp_path / "d")])
        assert r.exit_code == 1 and "metrics.json" in r.output

    def test_bad_override_is_clean_error(self, tmp_path):
        r = CliRunner().invoke(
            main,
            [
                "run",
                "dice",
                "--out",
                str(tmp_path),
                "--set",
                "data_generation.n_dice=0",
            ],
        )
        assert r.exit_code == 1 and "Error:" in r.output

    def test_validate_writes_outputs(self, tmp_path):
        r = CliRunner().invoke(
            main, ["validate", "b_value", "--replicates", "4", "--out", str(tmp_path)]
        )
        assert r.exit_code == 0, r.output
        assert (tmp_path / "b_value_summary.csv").exists() and (
            tmp_path / "b_value.json"
        ).exists()

    @pytest.mark.parametrize(
        "args",
        [
            ["dashboard", "dice"],
            ["dashboard", "weather", "--library", "plotly", "--export-type", "html"],
            ["random-walk"],
            ["random_walk"],
        ],
    )
    def test_dashboards(self, args, redirect_exports):
        r = CliRunner().invoke(main, args)
        assert r.exit_code == 0, r.output
        assert any(redirect_exports.rglob("*.*"))

    def test_html_requires_plotly(self, redirect_exports):
        r = CliRunner().invoke(main, ["dashboard", "dice", "--export-type", "html"])
        assert r.exit_code != 0

    def test_show_and_list_configs(self):
        r = CliRunner().invoke(
            main, ["show-config", "dice", "--set", "data_generation.n_dice=4"]
        )
        assert yaml.safe_load(r.output)["data_generation"]["n_dice"] == 4
        assert "quakes" in CliRunner().invoke(main, ["list-configs"]).output


def test_plotly_template_available_in_fresh_process():
    """Regression: dashboards must register the `pcc` template themselves."""
    code = (
        "from pcc_vizforge.plots import WeatherPlotlyPlot\n"
        "from pcc_vizforge.generators import WeatherGenerator\n"
        "WeatherPlotlyPlot().plot(WeatherGenerator(n_days=30).generate())\n"
    )
    src = Path(__file__).resolve().parents[1] / "src"
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(src), os.environ.get("PYTHONPATH", "")]),
    }
    subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, env=env
    )
