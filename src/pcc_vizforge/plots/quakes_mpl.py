"""Matplotlib plotting for earthquake data."""


import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pcc_vizforge.plots.style import SEQUENTIAL_CMAP
from pcc_vizforge.utils.io import get_export_directory, load_config
from pcc_vizforge.utils.theming import (
    format_axis_labels,
    setup_figure_style,
)


class EarthquakeMatplotlibPlot:
    """Matplotlib plotter for earthquake data."""

    def __init__(self, config_name: str = "quakes"):
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["matplotlib"]
        self.export_config = self.config["export"]

    def plot(self, data: pd.DataFrame, save_path: str | None = None) -> plt.Figure:
        """Create earthquake visualization."""
        figsize = tuple(self.viz_config["figsize"])
        fig = setup_figure_style(figsize=figsize)

        # Global distribution map
        ax1 = plt.subplot(2, 2, 1)
        scatter = ax1.scatter(
            data["longitude"], data["latitude"],
            c=data["magnitude"],
            s=data["magnitude"] * 15,  # Size proportional to magnitude
            alpha=self.viz_config["scatter_alpha"],
            cmap=self.viz_config["magnitude_colormap"],
            edgecolors='black',
            linewidths=0.5
        )
        plt.colorbar(scatter, ax=ax1, label='Magnitude', shrink=0.8)
        format_axis_labels(ax1, "Longitude", "Latitude", "Global Earthquake Distribution")
        ax1.set_xlim(-180, 180)
        ax1.set_ylim(-90, 90)
        ax1.grid(True, alpha=0.3)

        # Magnitude distribution
        ax2 = plt.subplot(2, 2, 2)
        ax2.hist(data["magnitude"], bins=25, alpha=0.7, edgecolor='black',
                color='darkred')
        ax2.axvline(data["magnitude"].mean(), color='blue', linestyle='--',
                   linewidth=2, label=f'Mean: {data["magnitude"].mean():.2f}')
        ax2.axvline(data["magnitude"].median(), color='green', linestyle='--',
                   linewidth=2, label=f'Median: {data["magnitude"].median():.2f}')
        format_axis_labels(ax2, "Magnitude", "Frequency", "Magnitude Distribution")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Depth vs Magnitude relationship
        ax3 = plt.subplot(2, 2, 3)
        scatter2 = ax3.scatter(
            data["magnitude"], data["depth_km"],
            c=data["depth_km"],
            s=50, alpha=0.6,
            cmap=self.viz_config["depth_colormap"]
        )
        plt.colorbar(scatter2, ax=ax3, label='Depth (km)', shrink=0.8)

        # Add trend line
        z = np.polyfit(data["magnitude"], data["depth_km"], 1)
        p = np.poly1d(z)
        ax3.plot(data["magnitude"], p(data["magnitude"]), "r--", alpha=0.8, linewidth=2)

        format_axis_labels(ax3, "Magnitude", "Depth (km)", "Depth vs Magnitude")
        ax3.grid(True, alpha=0.3)

        # Regional distribution
        ax4 = plt.subplot(2, 2, 4)
        region_counts = data["region"].value_counts().head(8)

        bars = ax4.barh(range(len(region_counts)), region_counts.values,
                       alpha=0.7, color='steelblue', edgecolor='black')
        ax4.set_yticks(range(len(region_counts)))
        ax4.set_yticklabels(region_counts.index)

        # Add value labels on bars
        for i, (bar, value) in enumerate(zip(bars, region_counts.values)):
            ax4.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                    str(value), ha='left', va='center')

        format_axis_labels(ax4, "Number of Earthquakes", "Region", "Regional Distribution")
        ax4.grid(True, alpha=0.3, axis='x')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=self.export_config["image_dpi"],
                       bbox_inches='tight')

        return fig

    def plot_temporal_analysis(self, data: pd.DataFrame, save_path: str | None = None) -> plt.Figure:
        """Create temporal earthquake analysis."""
        fig = setup_figure_style(figsize=(16, 12))

        # Timeline of earthquakes
        ax1 = plt.subplot(3, 2, 1)
        data_sorted = data.sort_values('timestamp')
        colors = SEQUENTIAL_CMAP(data_sorted["magnitude"] / data_sorted["magnitude"].max())
        ax1.scatter(data_sorted["timestamp"], data_sorted["magnitude"],
                   c=colors, s=data_sorted["magnitude"]*10, alpha=0.7)
        format_axis_labels(ax1, "Date", "Magnitude", "Earthquake Timeline")
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3)

        # Hourly distribution
        ax2 = plt.subplot(3, 2, 2)
        ax2.hist(data["hour"], bins=24, alpha=0.7, edgecolor='black', color='green')
        format_axis_labels(ax2, "Hour of Day", "Frequency", "Hourly Distribution")
        ax2.set_xticks(range(0, 24, 4))
        ax2.grid(True, alpha=0.3)

        # Magnitude categories
        ax3 = plt.subplot(3, 2, 3)
        mag_categories = data["magnitude_category"].value_counts()
        colors_cat = ['lightblue', 'yellow', 'orange', 'red', 'darkred', 'purple', 'black']
        ax3.pie(mag_categories.values, labels=mag_categories.index, autopct='%1.1f%%',
               colors=colors_cat[:len(mag_categories)], startangle=90)
        ax3.set_title("Magnitude Categories")

        # Depth categories
        ax4 = plt.subplot(3, 2, 4)
        depth_categories = data["depth_category"].value_counts()
        ax4.bar(depth_categories.index, depth_categories.values,
               alpha=0.7, color=['lightcoral', 'gold', 'steelblue'], edgecolor='black')
        format_axis_labels(ax4, "Depth Category", "Count", "Depth Distribution")
        ax4.grid(True, alpha=0.3)

        # Energy release over time
        ax5 = plt.subplot(3, 2, 5)
        monthly_energy = data.groupby(data["timestamp"].dt.to_period('M'))["energy_joules"].sum()
        ax5.plot(monthly_energy.index.astype(str), monthly_energy.values,
                marker='o', linewidth=2, markersize=6)
        format_axis_labels(ax5, "Month", "Total Energy (Joules)", "Monthly Energy Release")
        ax5.tick_params(axis='x', rotation=45)
        ax5.grid(True, alpha=0.3)

        # Magnitude vs Distance from Equator
        ax6 = plt.subplot(3, 2, 6)
        ax6.scatter(data["distance_from_equator"], data["magnitude"],
                   alpha=0.6, s=30, color='purple')

        # Add trend line
        z = np.polyfit(data["distance_from_equator"], data["magnitude"], 1)
        p = np.poly1d(z)
        ax6.plot(data["distance_from_equator"], p(data["distance_from_equator"]),
                "r--", alpha=0.8, linewidth=2)

        format_axis_labels(ax6, "Distance from Equator (°)", "Magnitude",
                          "Latitude Effect on Magnitude")
        ax6.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=self.export_config["image_dpi"],
                       bbox_inches='tight')

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
