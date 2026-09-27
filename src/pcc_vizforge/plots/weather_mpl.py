"""Matplotlib plotting for weather data."""


import matplotlib.pyplot as plt
import pandas as pd

from pcc_vizforge.utils.io import get_export_directory, load_config
from pcc_vizforge.utils.theming import (
    format_axis_labels,
    setup_figure_style,
)


class WeatherMatplotlibPlot:
    """Matplotlib plotter for weather data."""

    def __init__(self, config_name: str = "weather"):
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["matplotlib"]
        self.export_config = self.config["export"]

    def plot(self, data: pd.DataFrame, save_path: str | None = None) -> plt.Figure:
        """Create weather visualization."""
        figsize = tuple(self.viz_config["figsize"])
        fig = setup_figure_style(figsize=figsize)

        # Temperature over time
        ax1 = plt.subplot(2, 2, 1)
        ax1.plot(data["date"], data["temperature_avg"],
                color=self.viz_config["temp_color"], linewidth=1.5, label='Avg Temp')
        ax1.fill_between(data["date"], data["temperature_min"], data["temperature_max"],
                        alpha=0.3, color=self.viz_config["temp_color"], label='Min/Max Range')
        format_axis_labels(ax1, "Date", "Temperature (°C)", "Temperature Variation")
        ax1.legend()

        # Humidity (own axis -- never share a y-axis with precipitation)
        ax2 = plt.subplot(2, 2, 2)
        ax2.plot(data["date"], data["humidity"],
                color=self.viz_config["humidity_color"], linewidth=1.2)
        format_axis_labels(ax2, "Date", "Relative humidity (%)", "Relative humidity")

        # Daily precipitation
        ax3 = plt.subplot(2, 2, 3)
        ax3.bar(data["date"], data["precipitation"], width=1.0,
               color=self.viz_config["precipitation_color"])
        format_axis_labels(ax3, "Date", "Precipitation (mm/day)", "Daily precipitation")
        ax3.grid(axis="x", visible=False)

        # Monthly mean temperature
        ax4 = plt.subplot(2, 2, 4)
        monthly = data.groupby(data["date"].dt.month)["temperature_avg"].agg(["mean", "std", "count"])
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        sem = monthly["std"] / monthly["count"].pow(0.5)
        ax4.bar(monthly.index, monthly["mean"], color=self.viz_config["temp_color"], width=0.8)
        ax4.errorbar(monthly.index, monthly["mean"], yerr=1.96 * sem, fmt="none",
                    ecolor="#52514e", elinewidth=1, capsize=2)
        ax4.set_xticks(monthly.index, [months[i - 1] for i in monthly.index])
        format_axis_labels(ax4, "Month", "Temperature (°C)", "Monthly mean temperature (95% CI)")
        ax4.grid(axis="x", visible=False)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=self.export_config["image_dpi"], bbox_inches='tight')

        return fig

    def save(self, fig: plt.Figure, filename: str | None = None) -> str:
        """Save the plot to file."""
        if filename is None:
            filename = f"{self.export_config['filename_prefix']}_matplotlib.{self.export_config['image_format']}"

        export_dir = get_export_directory("images")
        full_path = export_dir / filename

        fig.savefig(full_path, dpi=self.export_config["image_dpi"],
                   bbox_inches='tight', format=self.export_config['image_format'])

        return str(full_path)
