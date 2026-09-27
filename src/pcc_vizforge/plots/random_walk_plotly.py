"""Plotly plotting for random walk data."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pcc_vizforge.utils.io import get_export_directory, load_config


class RandomWalkPlotlyPlot:
    """Plotly plotter for random walk data."""

    def __init__(self, config_name: str = "random_walk"):
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["plotly"]
        self.export_config = self.config["export"]

    def plot(self, data: pd.DataFrame) -> go.Figure:
        """Create interactive random walk visualization."""
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Random Walk Paths",
                "Final Position Distribution",
                "2D Walk Visualization",
                "Step Size Distribution",
            ),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"secondary_y": False}],
            ],
        )

        colors = self.viz_config["color_scheme"]

        # Random walk paths
        for i, walk_id in enumerate(data["walk_id"].unique()):
            walk_data = data[data["walk_id"] == walk_id]
            color = colors[i % len(colors)]

            fig.add_trace(
                go.Scatter(
                    x=walk_data["step"],
                    y=walk_data["position"],
                    mode="lines",
                    name=f"Walk {walk_id}",
                    line=dict(color=color, width=self.viz_config["line_width"]),
                    showlegend=i < 5,
                ),  # Show legend for first 5 walks only
                row=1,
                col=1,
            )

        # Final positions histogram
        final_positions = data.groupby("walk_id")["position"].last()
        fig.add_trace(
            go.Histogram(
                x=final_positions,
                nbinsx=20,
                name="Final Positions",
                marker_color=colors[0],
                opacity=0.7,
                showlegend=False,
            ),
            row=1,
            col=2,
        )

        # 2D visualization
        if "x_position" in data.columns:
            for i, walk_id in enumerate(data["walk_id"].unique()[:5]):
                walk_data = data[data["walk_id"] == walk_id]
                color = colors[i % len(colors)]

                fig.add_trace(
                    go.Scatter(
                        x=walk_data["x_position"],
                        y=walk_data["y_position"],
                        mode="lines+markers",
                        name=f"2D Walk {walk_id}",
                        line=dict(color=color, width=2),
                        marker=dict(size=3),
                        showlegend=False,
                    ),
                    row=2,
                    col=1,
                )

        # Step size distribution
        step_sizes = data["step_size"][data["step_size"] > 0]
        fig.add_trace(
            go.Histogram(
                x=step_sizes,
                nbinsx=30,
                name="Step Sizes",
                marker_color=colors[1],
                opacity=0.7,
                showlegend=False,
            ),
            row=2,
            col=2,
        )

        fig.update_layout(
            height=self.viz_config["height"],
            width=self.viz_config["width"],
            title_text=self.viz_config["title"],
            template=self.viz_config["template"],
            showlegend=self.viz_config["show_legend"],
        )

        # Update axis labels
        fig.update_xaxes(title_text="Steps", row=1, col=1)
        fig.update_yaxes(title_text="Position", row=1, col=1)
        fig.update_xaxes(title_text="Final Position", row=1, col=2)
        fig.update_yaxes(title_text="Count", row=1, col=2)
        fig.update_xaxes(title_text="X Position", row=2, col=1)
        fig.update_yaxes(title_text="Y Position", row=2, col=1)
        fig.update_xaxes(title_text="Step Size", row=2, col=2)
        fig.update_yaxes(title_text="Count", row=2, col=2)

        return fig

    def save(self, fig: go.Figure, filename: str | None = None) -> str:
        """Save the plot to HTML file."""
        if filename is None:
            filename = f"{self.export_config['filename_prefix']}_plotly.html"

        export_dir = get_export_directory("html")
        full_path = export_dir / filename

        fig.write_html(
            full_path, include_plotlyjs=self.export_config["html_include_plotlyjs"]
        )

        return str(full_path)

    def save_image(self, fig: go.Figure, filename: str | None = None) -> str:
        """Save the plot to image file."""
        if filename is None:
            filename = f"{self.export_config['filename_prefix']}_plotly.{self.export_config['image_format']}"

        export_dir = get_export_directory("images")
        full_path = export_dir / filename

        fig.write_image(full_path, format=self.export_config["image_format"])

        return str(full_path)
