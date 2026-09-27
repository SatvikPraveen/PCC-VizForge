"""Plotly plotting for dice simulation data."""

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pcc_vizforge.utils.io import get_export_directory, load_config


class DicePlotlyPlot:
    """Plotly plotter for dice simulation data."""
    
    def __init__(self, config_name: str = "dice"):
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["plotly"]
        self.export_config = self.config["export"]
        
    def plot(self, data: pd.DataFrame) -> go.Figure:
        """Create interactive dice simulation visualization."""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Sum Distribution", "Individual Die Values", 
                          "Rolling Average", "Probability Analysis")
        )
        
        colors = self.viz_config["color_discrete_sequence"]
        
        # Sum distribution
        roll_sums = data.groupby("roll_id")["roll_sum"].first()
        fig.add_trace(
            go.Histogram(x=roll_sums, nbinsx=len(roll_sums.unique()),
                        marker_color=colors[0], opacity=0.7, name="Sum Distribution"),
            row=1, col=1
        )
        
        # Individual die values
        die_counts = data["die_value"].value_counts().sort_index()
        fig.add_trace(
            go.Bar(x=die_counts.index, y=die_counts.values,
                   marker_color=colors[1], opacity=0.7, name="Die Values"),
            row=1, col=2
        )
        
        # Rolling average
        roll_data = data.groupby("roll_id").agg({"roll_sum": "first", "roll_sequence": "first"})
        rolling_avg = roll_data["roll_sum"].expanding().mean()
        fig.add_trace(
            go.Scatter(x=roll_data["roll_sequence"], y=rolling_avg,
                      mode='lines', line=dict(color=colors[2], width=2),
                      name="Rolling Average"),
            row=2, col=1
        )
        
        # Probability comparison
        observed_probs = roll_sums.value_counts(normalize=True).sort_index()
        fig.add_trace(
            go.Bar(x=observed_probs.index, y=observed_probs.values,
                   marker_color=colors[3], opacity=0.7, name="Observed Probabilities"),
            row=2, col=2
        )
        
        fig.update_layout(
            height=self.viz_config["height"],
            width=self.viz_config["width"],
            title_text=self.viz_config["title"],
            template=self.viz_config["template"],
            showlegend=False
        )
        
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