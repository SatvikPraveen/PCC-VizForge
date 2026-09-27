"""Plotly plotting for GitHub data."""

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pcc_vizforge.utils.io import get_export_directory, load_config


class GitHubPlotlyPlot:
    """Plotly plotter for GitHub data."""
    
    def __init__(self, config_name: str = "github"):
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["plotly"]
        self.export_config = self.config["export"]
        
    def plot(self, data: pd.DataFrame) -> go.Figure:
        """Create interactive GitHub visualization."""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Stars vs Forks (Repository Popularity)", 
                "Programming Language Distribution", 
                "Activity Score Distribution", 
                "Repository Age vs Popularity"
            ),
            specs=[[{"type": "scatter"}, {"type": "bar"}],
                   [{"type": "histogram"}, {"type": "scatter"}]]
        )
        
        colors = self.viz_config["color_discrete_sequence"]
        
        # Stars vs Forks scatter plot
        fig.add_trace(
            go.Scatter(
                x=data["stars"], 
                y=data["forks"],
                mode='markers',
                marker=dict(
                    color=data["popularity_score"], 
                    colorscale='viridis', 
                    size=data["contributors"] * 2,
                    sizemin=4,
                    opacity=0.7,
                    colorbar=dict(title="Popularity Score")
                ),
                text=data.apply(
                    lambda x: f"<b>{x['repo_name']}</b><br>"
                             f"Language: {x['primary_language']}<br>"
                             f"Type: {x['repo_type']}<br>"
                             f"Contributors: {x['contributors']}<br>"
                             f"Age: {x['repo_age_days']} days",
                    axis=1
                ),
                hovertemplate="%{text}<br>Stars: %{x}<br>Forks: %{y}<extra></extra>",
                name="Repositories"
            ),
            row=1, col=1
        )
        
        # Language distribution
        lang_counts = data["primary_language"].value_counts().head(10)
        fig.add_trace(
            go.Bar(
                x=lang_counts.index, 
                y=lang_counts.values,
                marker_color=colors[:len(lang_counts)],
                opacity=0.8,
                name="Language Distribution"
            ),
            row=1, col=2
        )
        
        # Activity score distribution
        fig.add_trace(
            go.Histogram(
                x=data["activity_score"], 
                nbinsx=20,
                marker_color=colors[2], 
                opacity=0.7,
                name="Activity Distribution"
            ),
            row=2, col=1
        )
        
        # Repository age vs popularity
        fig.add_trace(
            go.Scatter(
                x=data["repo_age_days"], 
                y=data["popularity_score"],
                mode='markers',
                marker=dict(
                    color=data["primary_language"].astype('category').cat.codes,
                    colorscale='Set3',
                    size=10,
                    opacity=0.7
                ),
                text=data.apply(
                    lambda x: f"<b>{x['repo_name']}</b><br>"
                             f"Language: {x['primary_language']}<br>"
                             f"Stars: {x['stars']}<br>"
                             f"Active: {'Yes' if x['is_active'] else 'No'}",
                    axis=1
                ),
                hovertemplate="%{text}<extra></extra>",
                name="Age vs Popularity"
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=self.viz_config["height"],
            width=self.viz_config["width"],
            title_text=self.viz_config["title"],
            template=self.viz_config["template"],
            showlegend=False
        )
        
        # Update axis labels
        fig.update_xaxes(title_text="Stars", row=1, col=1)
        fig.update_yaxes(title_text="Forks", row=1, col=1)
        fig.update_xaxes(title_text="Programming Language", row=1, col=2)
        fig.update_yaxes(title_text="Number of Repositories", row=1, col=2)
        fig.update_xaxes(title_text="Activity Score", row=2, col=1)
        fig.update_yaxes(title_text="Frequency", row=2, col=1)
        fig.update_xaxes(title_text="Repository Age (days)", row=2, col=2)
        fig.update_yaxes(title_text="Popularity Score", row=2, col=2)
        
        return fig
    
    def plot_language_analysis(self, data: pd.DataFrame) -> go.Figure:
        """Create detailed language analysis dashboard."""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Average Stars by Language",
                "Total Commits by Language", 
                "Language Popularity Over Time",
                "License Distribution"
            ),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "scatter"}, {"type": "pie"}]]
        )
        
        # Average stars by language
        lang_stats = data.groupby("primary_language").agg({
            "stars": "mean",
            "commits": "sum",
            "repo_age_days": "mean"
        }).round(1)
        
        fig.add_trace(
            go.Bar(
                x=lang_stats.index,
                y=lang_stats["stars"],
                marker_color="lightblue",
                name="Avg Stars"
            ),
            row=1, col=1
        )
        
        # Total commits by language
        fig.add_trace(
            go.Bar(
                x=lang_stats.index,
                y=lang_stats["commits"],
                marker_color="lightgreen",
                name="Total Commits"
            ),
            row=1, col=2
        )
        
        # Language popularity over repository age
        for lang in data["primary_language"].value_counts().head(5).index:
            lang_data = data[data["primary_language"] == lang]
            fig.add_trace(
                go.Scatter(
                    x=lang_data["repo_age_days"],
                    y=lang_data["stars"],
                    mode='markers',
                    name=lang,
                    opacity=0.7
                ),
                row=2, col=1
            )
        
        # License distribution
        license_counts = data["license"].value_counts()
        fig.add_trace(
            go.Pie(
                labels=license_counts.index,
                values=license_counts.values,
                name="Licenses"
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=800,
            width=1200,
            title_text="GitHub Language & License Analysis",
            template=self.viz_config["template"]
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