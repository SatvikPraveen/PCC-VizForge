"""Matplotlib plotting for dice simulation data."""


import matplotlib.pyplot as plt
import pandas as pd

from pcc_vizforge.utils.io import get_export_directory, load_config
from pcc_vizforge.utils.theming import (
    format_axis_labels,
    setup_figure_style,
)


class DiceMatplotlibPlot:
    """Matplotlib plotter for dice simulation data."""

    def __init__(self, config_name: str = "dice"):
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["matplotlib"]
        self.export_config = self.config["export"]

    def plot(self, data: pd.DataFrame, save_path: str | None = None) -> plt.Figure:
        """Create dice simulation visualization."""
        figsize = tuple(self.viz_config["figsize"])
        fig = setup_figure_style(figsize=figsize)

        # Sum distribution
        ax1 = plt.subplot(2, 2, 1)
        roll_sums = data.groupby("roll_id")["roll_sum"].first()
        ax1.hist(roll_sums, bins=range(int(roll_sums.min()), int(roll_sums.max())+2),
                alpha=0.7, edgecolor='black', color=self.viz_config["bar_color"])
        format_axis_labels(ax1, "Sum", "Frequency", "Dice Sum Distribution")
        ax1.grid(True, alpha=0.3)

        # Individual die values
        ax2 = plt.subplot(2, 2, 2)
        die_values = data["die_value"].value_counts().sort_index()
        ax2.bar(die_values.index, die_values.values, alpha=0.7,
               color=self.viz_config["hist_color"], edgecolor='black')
        format_axis_labels(ax2, "Die Value", "Frequency", "Individual Die Distribution")
        ax2.grid(True, alpha=0.3)

        # Rolling average
        ax3 = plt.subplot(2, 2, 3)
        roll_data = data.groupby("roll_id").agg({"roll_sum": "first", "roll_sequence": "first"})
        ax3.plot(roll_data["roll_sequence"], roll_data["roll_sum"].expanding().mean(),
                color=self.viz_config["line_color"], linewidth=2)
        format_axis_labels(ax3, "Roll Number", "Cumulative Average", "Rolling Average")
        ax3.grid(True, alpha=0.3)

        # Probability comparison
        ax4 = plt.subplot(2, 2, 4)
        observed_probs = roll_sums.value_counts(normalize=True).sort_index()
        ax4.bar(observed_probs.index, observed_probs.values, alpha=0.7,
               color=self.viz_config["bar_color"], label='Observed')
        format_axis_labels(ax4, "Sum", "Probability", "Observed Probabilities")
        ax4.legend()
        ax4.grid(True, alpha=0.3)

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
