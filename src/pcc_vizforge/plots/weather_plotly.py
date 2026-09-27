"""Plotly plotting for weather data."""

from typing import Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from pcc_vizforge.utils.io import load_config, get_export_directory


class WeatherPlotlyPlot:
    """Plotly plotter for weather data."""
    
    def __init__(self, config_name: str = "weather"):
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["plotly"]
        self.export_config = self.config["export"]
        
    def plot(self, data: pd.DataFrame) -> go.Figure:
        """Create interactive weather visualization."""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Temperature Over Time", "Humidity & Precipitation", 
                          "Monthly Temperature Averages", "Weather Type Distribution"),
            specs=[[{"secondary_y": True}, {"secondary_y": True}],
                   [{"secondary_y": False}, {"type": "pie"}]]
        )
        
        color_map = self.viz_config["color_discrete_map"]
        
        # Temperature over time with min/max range
        fig.add_trace(
            go.Scatter(x=data["date"], y=data["temperature_avg"],
                      mode='lines', name='Avg Temperature',
                      line=dict(color=color_map["temperature"], width=2)),
            row=1, col=1
        )
        
        # Temperature range
        fig.add_trace(
            go.Scatter(
                x=pd.concat([data["date"], data["date"][::-1]]),
                y=pd.concat([data["temperature_max"], data["temperature_min"][::-1]]),
                fill='tonexty',
                fillcolor=f'rgba(231, 76, 60, 0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                showlegend=True,
                name='Min/Max Range'
            ),
            row=1, col=1
        )
        
        # Humidity
        fig.add_trace(
            go.Scatter(x=data["date"], y=data["humidity"],
                      mode='lines', name='Humidity (%)',
                      line=dict(color=color_map["humidity"], width=2)),
            row=1, col=2
        )
        
        # Precipitation scatter on secondary axis
        rainy_days = data[data["precipitation"] > 0]
        fig.add_trace(
            go.Scatter(x=rainy_days["date"], y=rainy_days["precipitation"],
                      mode='markers', name='Precipitation (mm)',
                      marker=dict(color=color_map["precipitation"], size=8, opacity=0.7)),
            row=1, col=2, secondary_y=True
        )
        
        # Monthly temperature averages
        monthly = data.groupby(data["date"].dt.month)["temperature_avg"].mean()
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        fig.add_trace(
            go.Bar(x=[months[i-1] for i in monthly.index], y=monthly.values,
                   marker_color=color_map["temperature"], opacity=0.7,
                   name="Monthly Avg Temp", showlegend=False),
            row=2, col=1
        )
        
        # Weather type distribution pie chart
        weather_counts = data["weather_type"].value_counts()
        fig.add_trace(
            go.Pie(labels=weather_counts.index, values=weather_counts.values,
                   name="Weather Types", showlegend=False),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=self.viz_config["height"],
            width=self.viz_config["width"],
            title_text=self.viz_config["title"],
            template=self.viz_config["template"],
            showlegend=True
        )
        
        # Update axis labels
        fig.update_xaxes(title_text="Date", row=1, col=1)
        fig.update_yaxes(title_text="Temperature (°C)", row=1, col=1)
        fig.update_xaxes(title_text="Date", row=1, col=2)
        fig.update_yaxes(title_text="Humidity (%)", row=1, col=2)
        fig.update_yaxes(title_text="Precipitation (mm)", row=1, col=2, secondary_y=True)
        fig.update_xaxes(title_text="Month", row=2, col=1)
        fig.update_yaxes(title_text="Temperature (°C)", row=2, col=1)
        
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