"""Command-line interface for PCC VizForge."""

from typing import Optional

import click
import yaml

from pcc_vizforge.exceptions import PccVizForgeError
from pcc_vizforge.generators import (
    DiceGenerator,
    EarthquakeGenerator,
    GitHubGenerator,
    RandomWalkGenerator,
    WeatherGenerator,
)
from pcc_vizforge.logging_config import get_logger, setup_logging
from pcc_vizforge.plots import (
    DiceMatplotlibPlot,
    EarthquakeMatplotlibPlot,
    GitHubMatplotlibPlot,
    RandomWalkMatplotlibPlot,
    WeatherMatplotlibPlot,
)
from pcc_vizforge.utils.io import list_available_configs, load_config

logger = get_logger(__name__)


def handle_error(func):
    """Decorator to handle exceptions in CLI commands.

    Args:
        func: CLI command function to decorate

    Returns:
        Decorated function with error handling
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PccVizForgeError as e:
            logger.error(f"PCC VizForge error: {e}")
            click.echo(click.style(f"Error: {e}", fg="red"), err=True)
            raise SystemExit(1)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            click.echo(
                click.style(f"Unexpected error: {e}", fg="red"),
                err=True,
            )
            raise SystemExit(1)

    return wrapper


@click.group()
@click.version_option(package_name="pcc-vizforge")
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="Set logging level",
)
def main(log_level: str) -> None:
    """PCC VizForge - Comprehensive Data Visualization Toolkit.

    A personal exploration into data visualization and synthetic data generation.
    """
    setup_logging(level=log_level)
    logger.debug(f"PCC VizForge CLI initialized with log level: {log_level}")


@main.command()
@click.option(
    "--library",
    type=click.Choice(["matplotlib", "plotly"]),
    default="matplotlib",
    help="Visualization library to use",
)
@click.option(
    "--export-type",
    type=click.Choice(["image", "html"]),
    default="image",
    help="Export format",
)
@click.option("--save/--no-save", default=True, help="Save generated data")
@click.option("--filename", help="Custom output filename")
@handle_error
def random_walk(
    library: str, export_type: str, save: bool, filename: Optional[str]
) -> None:
    """Generate random walk visualization."""
    click.echo("Generating random walk data...")
    logger.info("Starting random walk generation")

    try:
        # Generate data
        generator = RandomWalkGenerator()
        data = generator.generate(save_to_file=save)

        # Create visualization
        if library == "matplotlib":
            plotter = RandomWalkMatplotlibPlot()
            fig = plotter.plot(data)

            if export_type == "image":
                output_path = plotter.save(fig, filename)
                click.echo(f"✓ Saved matplotlib plot to: {output_path}")
                logger.info(f"Saved random walk plot to: {output_path}")
            else:
                click.echo(
                    click.style(
                        "HTML export not supported for matplotlib. "
                        "Use plotly instead.",
                        fg="yellow",
                    )
                )

        elif library == "plotly":
            from pcc_vizforge.plots.random_walk_plotly import RandomWalkPlotlyPlot

            plotter = RandomWalkPlotlyPlot()
            fig = plotter.plot(data)

            if export_type == "html":
                output_path = plotter.save(fig, filename)
                click.echo(f"✓ Saved plotly plot to: {output_path}")
                logger.info(f"Saved random walk HTML to: {output_path}")
            else:
                output_path = plotter.save_image(fig, filename)
                click.echo(f"✓ Saved plotly image to: {output_path}")
                logger.info(f"Saved random walk image to: {output_path}")

        click.echo(
            f"Generated {len(data)} data points for {data['walk_id'].nunique()} walks"
        )
        logger.info("Random walk generation completed successfully")

    except Exception as e:
        logger.error(f"Failed to generate random walk: {e}")
        raise


@main.command()
@click.option(
    "--library",
    type=click.Choice(["matplotlib", "plotly"]),
    default="matplotlib",
    help="Visualization library to use",
)
@click.option(
    "--export-type",
    type=click.Choice(["image", "html"]),
    default="image",
    help="Export format",
)
@click.option("--save/--no-save", default=True, help="Save generated data")
@click.option("--filename", help="Custom output filename")
@handle_error
def dice(
    library: str, export_type: str, save: bool, filename: Optional[str]
) -> None:
    """Generate dice simulation visualization."""
    click.echo("Generating dice simulation data...")
    logger.info("Starting dice generation")

    try:
        generator = DiceGenerator()
        data = generator.generate(save_to_file=save)

        if library == "matplotlib":
            plotter = DiceMatplotlibPlot()
            fig = plotter.plot(data)

            if export_type == "image":
                output_path = plotter.save(fig, filename)
                click.echo(f"✓ Saved matplotlib plot to: {output_path}")
                logger.info(f"Saved dice plot to: {output_path}")

        elif library == "plotly":
            from pcc_vizforge.plots.dice_plotly import DicePlotlyPlot

            plotter = DicePlotlyPlot()
            fig = plotter.plot(data)

            if export_type == "html":
                output_path = plotter.save(fig, filename)
                click.echo(f"✓ Saved plotly plot to: {output_path}")
                logger.info(f"Saved dice HTML to: {output_path}")
            else:
                output_path = plotter.save_image(fig, filename)
                click.echo(f"✓ Saved plotly image to: {output_path}")
                logger.info(f"Saved dice image to: {output_path}")

        click.echo(f"Generated {len(data)} data points for dice simulation")
        logger.info("Dice generation completed successfully")

    except Exception as e:
        logger.error(f"Failed to generate dice visualization: {e}")
        raise


@main.command()
@click.option(
    "--library",
    type=click.Choice(["matplotlib", "plotly"]),
    default="matplotlib",
    help="Visualization library to use",
)
@click.option(
    "--export-type",
    type=click.Choice(["image", "html"]),
    default="image",
    help="Export format",
)
@click.option("--save/--no-save", default=True, help="Save generated data")
@click.option("--filename", help="Custom output filename")
@handle_error
def weather(
    library: str, export_type: str, save: bool, filename: Optional[str]
) -> None:
    """Generate weather data visualization."""
    click.echo("Generating weather data...")
    logger.info("Starting weather generation")

    try:
        generator = WeatherGenerator()
        data = generator.generate(save_to_file=save)

        if library == "matplotlib":
            plotter = WeatherMatplotlibPlot()
            fig = plotter.plot(data)

            if export_type == "image":
                output_path = plotter.save(fig, filename)
                click.echo(f"✓ Saved matplotlib plot to: {output_path}")
                logger.info(f"Saved weather plot to: {output_path}")

        elif library == "plotly":
            from pcc_vizforge.plots.weather_plotly import WeatherPlotlyPlot

            plotter = WeatherPlotlyPlot()
            fig = plotter.plot(data)

            if export_type == "html":
                output_path = plotter.save(fig, filename)
                click.echo(f"✓ Saved plotly plot to: {output_path}")
                logger.info(f"Saved weather HTML to: {output_path}")
            else:
                output_path = plotter.save_image(fig, filename)
                click.echo(f"✓ Saved plotly image to: {output_path}")
                logger.info(f"Saved weather image to: {output_path}")

        click.echo(f"Generated {len(data)} days of weather data")
        logger.info("Weather generation completed successfully")

    except Exception as e:
        logger.error(f"Failed to generate weather visualization: {e}")
        raise


@main.command()
@click.option(
    "--library",
    type=click.Choice(["matplotlib", "plotly"]),
    default="matplotlib",
    help="Visualization library to use",
)
@click.option(
    "--export-type",
    type=click.Choice(["image", "html"]),
    default="image",
    help="Export format",
)
@click.option("--save/--no-save", default=True, help="Save generated data")
@click.option("--filename", help="Custom output filename")
@handle_error
def quakes(
    library: str, export_type: str, save: bool, filename: Optional[str]
) -> None:
    """Generate earthquake data visualization."""
    click.echo("Generating earthquake data...")
    logger.info("Starting earthquake generation")

    try:
        generator = EarthquakeGenerator()
        data = generator.generate(save_to_file=save)

        if library == "matplotlib":
            plotter = EarthquakeMatplotlibPlot()
            fig = plotter.plot(data)

            if export_type == "image":
                output_path = plotter.save(fig, filename)
                click.echo(f"✓ Saved matplotlib plot to: {output_path}")
                logger.info(f"Saved earthquake plot to: {output_path}")

        elif library == "plotly":
            from pcc_vizforge.plots.quakes_plotly import EarthquakePlotlyPlot

            plotter = EarthquakePlotlyPlot()
            fig = plotter.plot(data)

            if export_type == "html":
                output_path = plotter.save(fig, filename)
                click.echo(f"✓ Saved plotly plot to: {output_path}")
                logger.info(f"Saved earthquake HTML to: {output_path}")
            else:
                output_path = plotter.save_image(fig, filename)
                click.echo(f"✓ Saved plotly image to: {output_path}")
                logger.info(f"Saved earthquake image to: {output_path}")

        click.echo(f"Generated {len(data)} earthquake data points")
        logger.info("Earthquake generation completed successfully")

    except Exception as e:
        logger.error(f"Failed to generate earthquake visualization: {e}")
        raise


@main.command()
@click.option(
    "--library",
    type=click.Choice(["matplotlib", "plotly"]),
    default="matplotlib",
    help="Visualization library to use",
)
@click.option(
    "--export-type",
    type=click.Choice(["image", "html"]),
    default="image",
    help="Export format",
)
@click.option("--save/--no-save", default=True, help="Save generated data")
@click.option("--filename", help="Custom output filename")
@handle_error
def github(
    library: str, export_type: str, save: bool, filename: Optional[str]
) -> None:
    """Generate GitHub statistics visualization."""
    click.echo("Generating GitHub statistics...")
    logger.info("Starting GitHub generation")

    try:
        generator = GitHubGenerator()
        data = generator.generate(save_to_file=save)

        if library == "matplotlib":
            plotter = GitHubMatplotlibPlot()
            fig = plotter.plot(data)

            if export_type == "image":
                output_path = plotter.save(fig, filename)
                click.echo(f"✓ Saved matplotlib plot to: {output_path}")
                logger.info(f"Saved GitHub plot to: {output_path}")

        elif library == "plotly":
            from pcc_vizforge.plots.github_plotly import GitHubPlotlyPlot

            plotter = GitHubPlotlyPlot()
            fig = plotter.plot(data)

            if export_type == "html":
                output_path = plotter.save(fig, filename)
                click.echo(f"✓ Saved plotly plot to: {output_path}")
                logger.info(f"Saved GitHub HTML to: {output_path}")
            else:
                output_path = plotter.save_image(fig, filename)
                click.echo(f"✓ Saved plotly image to: {output_path}")
                logger.info(f"Saved GitHub image to: {output_path}")

        click.echo(f"Generated {len(data)} repository data points")
        logger.info("GitHub generation completed successfully")

    except Exception as e:
        logger.error(f"Failed to generate GitHub visualization: {e}")
        raise


@main.command()
@handle_error
def list_configs() -> None:
    """List available configuration files."""
    click.echo("Available configurations:")
    configs = list_available_configs()

    if configs:
        for config in configs:
            click.echo(f"  • {config}")
        logger.info(f"Listed {len(configs)} configuration files")
    else:
        click.echo("  (No configuration files found)")
        logger.warning("No configuration files found in config/ directory")


@main.command()
@click.argument("config_name")
@handle_error
def show_config(config_name: str) -> None:
    """Show configuration file contents.

    Args:
        config_name: Name of the configuration file to display
    """
    logger.info(f"Displaying configuration: {config_name}")

    try:
        config = load_config(config_name)
        click.echo(f"\nConfiguration: {config_name}")
        click.echo("-" * 60)
        click.echo(yaml.dump(config, default_flow_style=False, indent=2))
        logger.debug("Configuration displayed successfully")
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        logger.error(f"Failed to load configuration {config_name}: {e}")
        raise


@main.command()
@click.option(
    "--library",
    type=click.Choice(["matplotlib", "plotly"]),
    default="matplotlib",
    help="Visualization library to use for all demos",
)
@handle_error
def demo(library: str) -> None:
    """Run a quick demo generating all visualizations.

    Args:
        library: Visualization library to use for all demos
    """
    click.echo("Running PCC VizForge demo...\n")
    logger.info(f"Starting demo with {library}")

    demos = [
        ("random_walk", library, "image"),
        ("dice", library, "image"),
        ("weather", library, "image"),
        ("quakes", library, "image"),
        ("github", library, "image"),
    ]

    success_count = 0
    failed_count = 0

    for data_type, lib, export in demos:
        try:
            click.echo(f"→ Generating {data_type} with {lib}...", nl=False)
            click.flush()

            if data_type == "random_walk":
                generator = RandomWalkGenerator()
                data = generator.generate(save_to_file=True)
            elif data_type == "dice":
                generator = DiceGenerator()
                data = generator.generate(save_to_file=True)
            elif data_type == "weather":
                generator = WeatherGenerator()
                data = generator.generate(save_to_file=True)
            elif data_type == "quakes":
                generator = EarthquakeGenerator()
                data = generator.generate(save_to_file=True)
            elif data_type == "github":
                generator = GitHubGenerator()
                data = generator.generate(save_to_file=True)

            click.echo(f" ✓ ({len(data)} points)\n")
            success_count += 1
            logger.info(f"Demo: {data_type} generated successfully")

        except Exception as e:
            click.echo(f" ✗ ({str(e)[:30]}...)\n")
            failed_count += 1
            logger.error(f"Demo: {data_type} failed: {e}")

    click.echo("-" * 60)
    click.echo(
        f"Demo completed: {success_count} successful, {failed_count} failed"
    )
    logger.info(
        f"Demo completed: {success_count} successful, {failed_count} failed"
    )

    if failed_count == 0:
        click.echo(click.style("All demos completed successfully!", fg="green"))
    else:
        click.echo(
            click.style(
                f"{failed_count} demo(s) failed. Check logs for details.",
                fg="yellow",
            )
        )


@main.command()
def version() -> None:
    """Show version information."""
    from pcc_vizforge import __version__ as version_str

    click.echo(f"PCC-VizForge version: {version_str}")


if __name__ == "__main__":
    main()
