"""Matplotlib plotting for random walk data."""

from typing import Optional, Tuple
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from pcc_vizforge.utils.io import load_config, get_export_directory
from pcc_vizforge.utils.theming import setup_figure_style, format_axis_labels, add_watermark


class RandomWalkMatplotlibPlot:
    """Matplotlib plotter for random walk data."""
    
    def __init__(self, config_name: str = "random_walk"):
        """Initialize with configuration."""
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["matplotlib"]
        self.export_config = self.config["export"]
        
    def plot(self, data: pd.DataFrame, save_path: Optional[str] = None) -> plt.Figure:
        """Create random walk visualization."""
        figsize = tuple(self.viz_config["figsize"])
        fig = setup_figure_style(figsize=figsize)
        
        # Main plot: time series of all walks
        ax1 = plt.subplot(2, 2, 1)
        for walk_id in data["walk_id"].unique():
            walk_data = data[data["walk_id"] == walk_id]
            ax1.plot(walk_data["step"], walk_data["position"], 
                    alpha=self.viz_config["alpha"], 
                    linewidth=self.viz_config["line_width"],
                    label=f"Walk {walk_id}")
        
        format_axis_labels(ax1, 
                          xlabel=self.viz_config["xlabel"],
                          ylabel=self.viz_config["ylabel"],
                          title="Random Walk Paths")
        if self.viz_config["legend"] and data["walk_id"].nunique() <= 10:
            ax1.legend()
        ax1.grid(self.viz_config["grid"])
        
        # Subplot 2: Final positions distribution
        ax2 = plt.subplot(2, 2, 2)
        final_positions = data.groupby("walk_id")["position"].last()
        ax2.hist(final_positions, bins=min(20, len(final_positions)//2), 
                alpha=0.7, edgecolor='black')
        format_axis_labels(ax2, 
                          xlabel="Final Position",
                          ylabel="Frequency",
                          title="Final Position Distribution")
        ax2.grid(True, alpha=0.3)
        
        # Subplot 3: 2D plot if available
        ax3 = plt.subplot(2, 2, 3)
        if "x_position" in data.columns and "y_position" in data.columns:
            for walk_id in data["walk_id"].unique()[:5]:  # Limit to 5 walks for clarity
                walk_data = data[data["walk_id"] == walk_id]
                ax3.plot(walk_data["x_position"], walk_data["y_position"], 
                        alpha=self.viz_config["alpha"], 
                        linewidth=self.viz_config["line_width"],
                        marker='o', markersize=2, markevery=50)
                # Mark start and end
                ax3.plot(walk_data["x_position"].iloc[0], walk_data["y_position"].iloc[0], 
                        'go', markersize=8, label='Start' if walk_id == 0 else "")
                ax3.plot(walk_data["x_position"].iloc[-1], walk_data["y_position"].iloc[-1], 
                        'ro', markersize=8, label='End' if walk_id == 0 else "")
        
        format_axis_labels(ax3, 
                          xlabel="X Position",
                          ylabel="Y Position", 
                          title="2D Random Walk Visualization")
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.set_aspect('equal', adjustable='box')
        
        # Subplot 4: Step size distribution
        ax4 = plt.subplot(2, 2, 4)
        step_sizes = data["step_size"][data["step_size"] > 0]  # Remove zeros
        ax4.hist(step_sizes, bins=30, alpha=0.7, edgecolor='black')
        ax4.axvline(step_sizes.mean(), color='red', linestyle='--', 
                   label=f'Mean: {step_sizes.mean():.2f}')
        format_axis_labels(ax4,
                          xlabel="Step Size",
                          ylabel="Frequency",
                          title="Step Size Distribution")
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        add_watermark(ax4)
        
        if save_path:
            plt.savefig(save_path, dpi=self.export_config["image_dpi"], 
                       bbox_inches='tight')
        
        return fig
    
    def plot_statistics(self, data: pd.DataFrame, save_path: Optional[str] = None) -> plt.Figure:
        """Create statistical analysis plots."""
        fig = setup_figure_style(figsize=(14, 10))
        
        # Calculate statistics for each walk
        walk_stats = []
        for walk_id in data["walk_id"].unique():
            walk_data = data[data["walk_id"] == walk_id]
            walk_stats.append({
                "walk_id": walk_id,
                "final_position": walk_data["position"].iloc[-1],
                "max_excursion": walk_data["position"].max() - walk_data["position"].min(),
                "mean_step_size": walk_data["step_size"].mean(),
                "total_distance": walk_data["position"].abs().sum(),
            })
        
        stats_df = pd.DataFrame(walk_stats)
        
        # Plot 1: Walk statistics comparison
        ax1 = plt.subplot(2, 3, 1)
        ax1.scatter(stats_df["walk_id"], stats_df["final_position"], alpha=0.7)
        format_axis_labels(ax1, "Walk ID", "Final Position", "Final Positions by Walk")
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Excursion vs Final Position
        ax2 = plt.subplot(2, 3, 2)
        ax2.scatter(stats_df["final_position"], stats_df["max_excursion"], alpha=0.7)
        format_axis_labels(ax2, "Final Position", "Max Excursion", "Excursion vs Final Position")
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Cumulative displacement over time
        ax3 = plt.subplot(2, 3, 3)
        for walk_id in data["walk_id"].unique()[:5]:
            walk_data = data[data["walk_id"] == walk_id]
            cumulative_displacement = walk_data["position"].abs().cumsum()
            ax3.plot(walk_data["step"], cumulative_displacement, alpha=0.7)
        format_axis_labels(ax3, "Steps", "Cumulative |Displacement|", "Cumulative Displacement")
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Position variance over time
        ax4 = plt.subplot(2, 3, 4)
        position_variance = data.groupby("step")["position"].var()
        ax4.plot(position_variance.index, position_variance.values, 'b-', linewidth=2)
        ax4.plot(position_variance.index, position_variance.index, 'r--', 
                label='Theoretical (linear growth)', alpha=0.7)
        format_axis_labels(ax4, "Steps", "Position Variance", "Variance Growth")
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # Plot 5: Return to origin probability
        ax5 = plt.subplot(2, 3, 5)
        return_data = []
        for walk_id in data["walk_id"].unique():
            walk_data = data[data["walk_id"] == walk_id]
            returns_to_origin = (walk_data["position"] == 0).sum()
            return_data.append(returns_to_origin)
        
        ax5.hist(return_data, bins=max(1, len(return_data)//3), alpha=0.7, edgecolor='black')
        format_axis_labels(ax5, "Returns to Origin", "Frequency", "Returns to Origin Distribution")
        ax5.grid(True, alpha=0.3)
        
        # Plot 6: Step correlation
        ax6 = plt.subplot(2, 3, 6)
        all_positions = data["position"].values
        if len(all_positions) > 1:
            correlation = np.correlate(all_positions[1:], all_positions[:-1], mode='valid')
            ax6.plot(correlation[:100], alpha=0.7)  # Show first 100 correlations
        format_axis_labels(ax6, "Lag", "Autocorrelation", "Position Autocorrelation")
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        add_watermark(ax6)
        
        if save_path:
            plt.savefig(save_path, dpi=self.export_config["image_dpi"], 
                       bbox_inches='tight')
        
        return fig
    
    def save(self, fig: plt.Figure, filename: Optional[str] = None) -> str:
        """Save the plot to file."""
        if filename is None:
            filename = f"{self.export_config['filename_prefix']}_matplotlib.{self.export_config['image_format']}"
        
        export_dir = get_export_directory("images")
        full_path = export_dir / filename
        
        fig.savefig(full_path, dpi=self.export_config["image_dpi"], 
                   bbox_inches='tight', format=self.export_config['image_format'])
        
        return str(full_path)