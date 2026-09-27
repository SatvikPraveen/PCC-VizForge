"""Matplotlib plotting for weather data."""

from typing import Optional
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates

from pcc_vizforge.utils.io import load_config, get_export_directory
from pcc_vizforge.utils.theming import setup_figure_style, format_axis_labels, add_watermark


class WeatherMatplotlibPlot:
    """Matplotlib plotter for weather data."""
    
    def __init__(self, config_name: str = "weather"):
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["matplotlib"]
        self.export_config = self.config["export"]
        
    def plot(self, data: pd.DataFrame, save_path: Optional[str] = None) -> plt.Figure:
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
        ax1.grid(True, alpha=0.3)
        
        # Humidity and precipitation
        ax2 = plt.subplot(2, 2, 2)
        ax2.plot(data["date"], data["humidity"], 
                color=self.viz_config["humidity_color"], linewidth=1.5, label='Humidity %')
        ax2_twin = ax2.twinx()
        rainy_days = data[data["precipitation"] > 0]
        ax2_twin.scatter(rainy_days["date"], rainy_days["precipitation"], 
                        color=self.viz_config["precipitation_color"], alpha=0.6, s=20, label='Precipitation')
        format_axis_labels(ax2, "Date", "Humidity (%)", "Humidity & Precipitation")
        ax2.legend(loc='upper left')
        ax2_twin.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
        
        # Monthly averages
        ax3 = plt.subplot(2, 2, 3)
        monthly = data.groupby(data["date"].dt.month).agg({
            "temperature_avg": "mean",
            "humidity": "mean",
            "precipitation": "sum"
        })
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        ax3.bar(monthly.index, monthly["temperature_avg"], alpha=0.7, 
               color=self.viz_config["temp_color"])
        ax3.set_xticks(monthly.index)
        ax3.set_xticklabels([months[i-1] for i in monthly.index])
        format_axis_labels(ax3, "Month", "Temperature (°C)", "Monthly Temperature Averages")
        ax3.grid(True, alpha=0.3)
        
        # Weather type distribution
        ax4 = plt.subplot(2, 2, 4)
        weather_counts = data["weather_type"].value_counts()
        ax4.pie(weather_counts.values, labels=weather_counts.index, autopct='%1.1f%%',
               startangle=90)
        ax4.set_title("Weather Type Distribution")
        
        plt.tight_layout()
        add_watermark(ax4)
        
        if save_path:
            plt.savefig(save_path, dpi=self.export_config["image_dpi"], bbox_inches='tight')
        
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