"""Plotly plotting for weather data."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pcc_vizforge.utils.io import get_export_directory, load_config


class WeatherPlotlyPlot:
    """Plotly plotter for weather data."""

    def __init__(self, config_name: str = "weather"):
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["plotly"]
        self.export_config = self.config["export"]

    def plot(self, data: pd.DataFrame) -> go.Figure:
        """Create interactive weather visualization (one y-axis per panel)."""
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Temperature",
                "Relative humidity",
                "Daily precipitation",
                "Monthly mean temperature (95% CI)",
            ),
            vertical_spacing=0.14,
        )
        color_map = self.viz_config["color_discrete_map"]
        temp_color = color_map["temperature"]

        # Min/max band first, then the mean on top.
        fig.add_trace(
            go.Scatter(
                x=data["date"],
                y=data["temperature_max"],
                mode="lines",
                line=dict(width=0),
                hoverinfo="skip",
                showlegend=False,
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=data["date"],
                y=data["temperature_min"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor=_rgba(temp_color, 0.2),
                name="Daily min-max",
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=data["date"],
                y=data["temperature_avg"],
                mode="lines",
                name="Daily mean",
                line=dict(color=temp_color, width=2),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:.1f} °C<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=data["date"],
                y=data["humidity"],
                mode="lines",
                name="Relative humidity",
                line=dict(color=color_map["humidity"], width=2),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:.0f} %<extra></extra>",
            ),
            row=1,
            col=2,
        )
        fig.add_trace(
            go.Bar(
                x=data["date"],
                y=data["precipitation"],
                name="Precipitation",
                marker_color=color_map["precipitation"],
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:.1f} mm<extra></extra>",
            ),
            row=2,
            col=1,
        )
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        monthly = data.groupby(data["date"].dt.month)["temperature_avg"].agg(
            ["mean", "std", "count"]
        )
        sem = monthly["std"] / monthly["count"].pow(0.5)
        fig.add_trace(
            go.Bar(
                x=[months[i - 1] for i in monthly.index],
                y=monthly["mean"],
                error_y=dict(
                    type="data", array=1.96 * sem, color="#52514e", thickness=1
                ),
                marker_color=temp_color,
                name="Monthly mean",
                showlegend=False,
                hovertemplate="%{x}: %{y:.1f} °C<extra></extra>",
            ),
            row=2,
            col=2,
        )
        fig.update_layout(
            height=self.viz_config["height"],
            width=self.viz_config["width"],
            title_text=self.viz_config["title"],
            template=self.viz_config["template"],
            bargap=0.15,
        )
        fig.update_yaxes(title_text="°C", row=1, col=1)
        fig.update_yaxes(title_text="%", row=1, col=2)
        fig.update_yaxes(title_text="mm/day", row=2, col=1)
        fig.update_yaxes(title_text="°C", row=2, col=2)
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


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"
