"""Plotly plotting for earthquake data."""

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pcc_vizforge.utils.io import get_export_directory, load_config


class EarthquakePlotlyPlot:
    """Plotly plotter for earthquake data."""
    
    def __init__(self, config_name: str = "quakes"):
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["plotly"]
        self.export_config = self.config["export"]
        
    def plot(self, data: pd.DataFrame) -> go.Figure:
        """Create interactive earthquake visualization."""
        # Create main map visualization
        fig = go.Figure()
        
        # Main world map with earthquakes
        fig.add_trace(
            go.Scattermapbox(
                lat=data["latitude"],
                lon=data["longitude"],
                mode='markers',
                marker=dict(
                    size=data["magnitude"] * 4,  # Scale marker size by magnitude
                    color=data["magnitude"],
                    colorscale=self.viz_config["color_continuous_scale"],
                    colorbar=dict(
                        title="Magnitude",
                        titleside="right",
                        tickmode="linear",
                        tick0=data["magnitude"].min(),
                        dtick=0.5
                    ),
                    opacity=0.7,
                    sizemode='diameter'
                ),
                text=data.apply(
                    lambda x: f"<b>Magnitude:</b> {x['magnitude']:.1f}<br>"
                             f"<b>Depth:</b> {x['depth_km']:.0f} km<br>"
                             f"<b>Region:</b> {x['region']}<br>"
                             f"<b>Date:</b> {x['timestamp'].strftime('%Y-%m-%d %H:%M')}", 
                    axis=1
                ),
                hovertemplate="%{text}<extra></extra>",
                name="Earthquakes"
            )
        )
        
        # Update layout for map
        fig.update_layout(
            mapbox=dict(
                style=self.viz_config["mapbox_style"],
                zoom=1.2,
                center=dict(lat=20, lon=0)
            ),
            height=self.viz_config["height"],
            width=self.viz_config["width"],
            title=dict(
                text=self.viz_config["title"],
                x=0.5,
                font=dict(size=20)
            ),
            template=self.viz_config["template"],
            showlegend=False
        )
        
        return fig
    
    def plot_analysis(self, data: pd.DataFrame) -> go.Figure:
        """Create detailed earthquake analysis dashboard."""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Magnitude Distribution", 
                "Depth vs Magnitude",
                "Regional Activity", 
                "Temporal Distribution"
            ),
            specs=[[{"type": "histogram"}, {"type": "scatter"}],
                   [{"type": "bar"}, {"type": "histogram"}]]
        )
        
        # Magnitude distribution
        fig.add_trace(
            go.Histogram(
                x=data["magnitude"], 
                nbinsx=25,
                marker_color="darkred",
                opacity=0.7,
                name="Magnitude Distribution"
            ),
            row=1, col=1
        )
        
        # Depth vs Magnitude scatter
        fig.add_trace(
            go.Scatter(
                x=data["magnitude"],
                y=data["depth_km"],
                mode='markers',
                marker=dict(
                    color=data["magnitude"],
                    colorscale="plasma",
                    size=8,
                    opacity=0.6
                ),
                text=data["region"],
                hovertemplate="<b>Magnitude:</b> %{x:.1f}<br>" +
                             "<b>Depth:</b> %{y:.0f} km<br>" +
                             "<b>Region:</b> %{text}<extra></extra>",
                name="Depth vs Magnitude"
            ),
            row=1, col=2
        )
        
        # Regional activity
        region_counts = data["region"].value_counts().head(10)
        fig.add_trace(
            go.Bar(
                x=region_counts.values,
                y=region_counts.index,
                orientation='h',
                marker_color="steelblue",
                opacity=0.8,
                name="Regional Activity"
            ),
            row=2, col=1
        )
        
        # Temporal distribution (hour of day)
        fig.add_trace(
            go.Histogram(
                x=data["hour"],
                nbinsx=24,
                marker_color="green",
                opacity=0.7,
                name="Hourly Distribution"
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=800,
            width=1200,
            title_text="Comprehensive Earthquake Analysis",
            template=self.viz_config["template"],
            showlegend=False
        )
        
        # Update axis labels
        fig.update_xaxes(title_text="Magnitude", row=1, col=1)
        fig.update_yaxes(title_text="Frequency", row=1, col=1)
        fig.update_xaxes(title_text="Magnitude", row=1, col=2)
        fig.update_yaxes(title_text="Depth (km)", row=1, col=2)
        fig.update_xaxes(title_text="Number of Earthquakes", row=2, col=1)
        fig.update_yaxes(title_text="Region", row=2, col=1)
        fig.update_xaxes(title_text="Hour of Day", row=2, col=2)
        fig.update_yaxes(title_text="Frequency", row=2, col=2)
        
        return fig
    
    def save(self, fig: go.Figure, filename: Optional[str] = None) -> str:
        """Save the plot to HTML file."""
        if filename is None:
            filename = f"{self.export_config['filename_prefix']}_plotly.html"
        
        export_dir = get_export_directory("html")
        full_path = export_dir / filename
        
        fig.write_html(full_path, include_plotlyjs=self.export_config["html_include_plotlyjs"])
        
        return str(full_path)
    
    def save_image(self, fig: go.Figure, filename: Optional[str] = None) -> str:
        """Save the plot to image file."""
        if filename is None:
            filename = f"{self.export_config['filename_prefix']}_plotly.{self.export_config['image_format']}"
        
        export_dir = get_export_directory("images")
        full_path = export_dir / filename
        
        fig.write_image(full_path, format=self.export_config['image_format'])
        
        return str(full_path)