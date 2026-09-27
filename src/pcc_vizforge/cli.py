"""Command-line interface for PCC-VizForge.

Examples::

    pcc-vizforge run quakes --seed 7 --set data_generation.b_value=0.8
    pcc-vizforge verify runs/quakes-20240101-120000-abc123def456
    pcc-vizforge validate b_value --replicates 500
    pcc-vizforge dashboard weather --library plotly --export-type html
"""

from __future__ import annotations

import functools
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import click
import yaml

from pcc_vizforge._version import __version__
from pcc_vizforge.exceptions import PccVizForgeError
from pcc_vizforge.logging_config import setup_logging
from pcc_vizforge.utils.config import apply_overrides
from pcc_vizforge.utils.io import list_available_configs, load_config

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

DOMAIN_NAMES = ("random_walk", "dice", "weather", "quakes", "github")
DASHBOARD_CLASSES = {
    "random_walk": ("RandomWalkMatplotlibPlot", "RandomWalkPlotlyPlot"),
    "dice": ("DiceMatplotlibPlot", "DicePlotlyPlot"),
    "weather": ("WeatherMatplotlibPlot", "WeatherPlotlyPlot"),
    "quakes": ("EarthquakeMatplotlibPlot", "EarthquakePlotlyPlot"),
    "github": ("GitHubMatplotlibPlot", "GitHubPlotlyPlot"),
}


def handle_error(func: F) -> F:
    """Turn package errors into a clean message and exit code 1."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except PccVizForgeError as exc:
            logger.debug("Command failed", exc_info=True)
            click.echo(click.style(f"Error: {exc}", fg="red"), err=True)
            raise SystemExit(1) from exc

    return wrapper  # type: ignore[return-value]


domain_argument = click.argument("domain", type=click.Choice(DOMAIN_NAMES))
set_option = click.option(
    "--set",
    "overrides",
    multiple=True,
    metavar="KEY.PATH=VALUE",
    help="Override a config value (repeatable), e.g. --set data_generation.n_steps=500",
)
config_option = click.option(
    "--config",
    "config",
    type=click.Path(dir_okay=False),
    help="YAML config file (defaults to the bundled one).",
)
seed_option = click.option(
    "--seed", type=click.IntRange(min=0), help="RNG seed (overrides the config)."
)


@click.group()
@click.version_option(__version__, package_name="pcc-vizforge")
@click.option(
    "--log-level",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    default="WARNING",
    show_default=True,
)
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False),
    help="Also write DEBUG logs to this file.",
)
def main(log_level: str, log_file: str | None) -> None:
    """PCC-VizForge: reproducible stochastic simulation, inference and visualisation."""
    setup_logging(level=log_level, log_file=log_file)


# --------------------------------------------------------------------------- #
# Research workflow
# --------------------------------------------------------------------------- #
@main.command()
@domain_argument
@config_option
@set_option
@seed_option
@click.option(
    "--out",
    "output_dir",
    default="runs",
    show_default=True,
    type=click.Path(file_okay=False),
)
@click.option("--figures/--no-figures", default=True, show_default=True)
@click.option(
    "--format",
    "formats",
    multiple=True,
    type=click.Choice(["png", "pdf", "svg"]),
    default=("png",),
    show_default=True,
    help="Figure format (repeatable).",
)
@click.option(
    "--name", "run_name", help="Run folder name (default: <domain>-<timestamp>-<id>)."
)
@handle_error
def run(
    domain: str,
    config: str | None,
    overrides: tuple[str, ...],
    seed: int | None,
    output_dir: str,
    figures: bool,
    formats: tuple[str, ...],
    run_name: str | None,
) -> None:
    """Simulate, analyse and plot DOMAIN into a reproducible run directory."""
    from pcc_vizforge.experiments import run_experiment

    result = run_experiment(
        domain,
        config=config,
        overrides=overrides,
        seed=seed,
        output_dir=output_dir,
        figures=figures,
        formats=formats,
        run_name=run_name,
    )
    click.echo(
        f"Run {result.manifest.run_id} (seed {result.manifest.seed}) -> {result.run_dir}"
    )
    click.echo(f"  data: {len(result.data):,} rows; figures: {len(result.figures)}")


@main.command()
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False))
@handle_error
def verify(run_dir: str) -> None:
    """Regenerate a run from its manifest and check it is bit-identical."""
    from pcc_vizforge.experiments import verify_run

    report = verify_run(run_dir)
    tampered = [k for k, ok in report["integrity"].items() if not ok]
    status = (
        click.style("REPRODUCED", fg="green")
        if report["reproduced"]
        else click.style("MISMATCH", fg="red")
    )
    click.echo(
        f"{report['domain']} run {report['run_id']} (seed {report['seed']}): {status}"
    )
    if tampered:
        click.echo(
            click.style(
                f"  modified or missing files: {', '.join(tampered)}", fg="yellow"
            )
        )
    if not report["reproduced"] or tampered:
        raise SystemExit(1)


@main.command()
@click.argument(
    "study",
    type=click.Choice(
        ["all", "b_value", "msd_exponent", "power_law", "dice_gof", "trend_hac"]
    ),
)
@click.option(
    "--replicates", default=200, show_default=True, type=click.IntRange(min=2)
)
@click.option("--seed", default=20240101, show_default=True, type=click.IntRange(min=0))
@click.option(
    "--out",
    "output_dir",
    type=click.Path(file_okay=False),
    help="Write CSV/JSON results here.",
)
@handle_error
def validate(study: str, replicates: int, seed: int, output_dir: str | None) -> None:
    """Monte Carlo validation of estimators (bias, RMSE, CI coverage, test size)."""
    from pcc_vizforge.experiments.validation import STUDIES, run_study, study_to_dict

    names = sorted(STUDIES) if study == "all" else [study]
    for name in names:
        result = run_study(name, n_replicates=replicates, seed=seed)
        click.echo(click.style(f"\n{name}: {result.description}", bold=True))
        click.echo(
            result.summary.to_string(index=False, float_format=lambda v: f"{v:.4g}")
        )
        if output_dir:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            result.replicates.to_csv(out / f"{name}_replicates.csv", index=False)
            result.summary.to_csv(out / f"{name}_summary.csv", index=False)
            (out / f"{name}.json").write_text(
                json.dumps(study_to_dict(result), indent=2, default=str) + "\n"
            )


# --------------------------------------------------------------------------- #
# Dashboards
# --------------------------------------------------------------------------- #
def _render_dashboard(
    domain: str,
    library: str,
    export_type: str,
    save: bool,
    filename: str | None,
    seed: int | None = None,
    overrides: tuple[str, ...] = (),
) -> None:
    from pcc_vizforge import plots
    from pcc_vizforge.experiments import DOMAINS

    gen = DOMAINS[domain](overrides=overrides)
    data = gen.generate(save_to_file=save, seed=seed)
    mpl_name, plotly_name = DASHBOARD_CLASSES[domain]
    if library == "matplotlib":
        if export_type == "html":
            raise click.UsageError("HTML export requires --library plotly")
        plotter = getattr(plots, mpl_name)()
        path = plotter.save(plotter.plot(data), filename)
    else:
        plotter = getattr(plots, plotly_name)()
        fig = plotter.plot(data)
        path = (
            plotter.save(fig, filename)
            if export_type == "html"
            else plotter.save_image(fig, filename)
        )
    click.echo(f"✓ {domain}: {len(data):,} rows (seed {gen.last_seed}) -> {path}")


dashboard_options = [
    click.option(
        "--library",
        type=click.Choice(["matplotlib", "plotly"]),
        default="matplotlib",
        show_default=True,
    ),
    click.option(
        "--export-type",
        type=click.Choice(["image", "html"]),
        default="image",
        show_default=True,
    ),
    click.option(
        "--save/--no-save",
        default=False,
        show_default=True,
        help="Also save the generated data as CSV.",
    ),
    click.option("--filename", help="Output file name."),
]


def _with_options(options: list[Callable[[F], F]]) -> Callable[[F], F]:
    def decorate(func: F) -> F:
        for option in reversed(options):
            func = option(func)
        return func

    return decorate


@main.command()
@domain_argument
@_with_options(dashboard_options)
@seed_option
@set_option
@handle_error
def dashboard(
    domain: str,
    library: str,
    export_type: str,
    save: bool,
    filename: str | None,
    seed: int | None,
    overrides: tuple[str, ...],
) -> None:
    """Render the overview dashboard for DOMAIN."""
    _render_dashboard(domain, library, export_type, save, filename, seed, overrides)


def _legacy_command(domain: str, name: str, hidden: bool) -> None:
    """Register a per-domain alias of ``dashboard`` (kept for backwards compatibility)."""

    @main.command(
        name=name,
        hidden=hidden,
        help=f"Render the {domain} dashboard (alias of `dashboard {domain}`).",
    )
    @_with_options(dashboard_options)
    @handle_error
    def command(
        library: str, export_type: str, save: bool, filename: str | None
    ) -> None:
        _render_dashboard(domain, library, export_type, save, filename)


for _domain in DOMAIN_NAMES:
    _legacy_command(_domain, _domain.replace("_", "-"), hidden=False)
    if "_" in _domain:
        _legacy_command(_domain, _domain, hidden=True)


@main.command()
@click.option(
    "--library",
    type=click.Choice(["matplotlib", "plotly"]),
    default="matplotlib",
    show_default=True,
)
@handle_error
def demo(library: str) -> None:
    """Render every dashboard with default settings."""
    export = "image"
    for domain in DOMAIN_NAMES:
        _render_dashboard(domain, library, export, save=False, filename=None)


# --------------------------------------------------------------------------- #
# Configuration helpers
# --------------------------------------------------------------------------- #
@main.command("list-configs")
def list_configs() -> None:
    """List bundled configuration files."""
    for name in list_available_configs():
        click.echo(name)


@main.command("show-config")
@click.argument("config_name")
@set_option
@handle_error
def show_config(config_name: str, overrides: tuple[str, ...]) -> None:
    """Print a configuration (after applying any --set overrides)."""
    config = apply_overrides(load_config(config_name), overrides)
    click.echo(yaml.safe_dump(config, sort_keys=False))


@main.command()
def version() -> None:
    """Show version information."""
    click.echo(f"PCC-VizForge version: {__version__}")


if __name__ == "__main__":
    main()
