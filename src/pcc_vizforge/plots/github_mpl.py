"""Matplotlib plotting for GitHub data."""


import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pcc_vizforge.plots.style import series_color
from pcc_vizforge.utils.io import get_export_directory, load_config
from pcc_vizforge.utils.theming import (
    format_axis_labels,
    setup_figure_style,
)


class GitHubMatplotlibPlot:
    """Matplotlib plotter for GitHub data."""

    def __init__(self, config_name: str = "github"):
        self.config = load_config(config_name)
        self.viz_config = self.config["visualization"]["matplotlib"]
        self.export_config = self.config["export"]

    def plot(self, data: pd.DataFrame, save_path: str | None = None) -> plt.Figure:
        """Create GitHub repository analysis visualization."""
        figsize = tuple(self.viz_config["figsize"])
        fig = setup_figure_style(figsize=figsize)

        # Stars vs Forks scatter plot
        ax1 = plt.subplot(2, 2, 1)
        scatter = ax1.scatter(
            data["stars"], data["forks"],
            c=data["popularity_score"],
            s=data["contributors"] * 8,
            alpha=self.viz_config["alpha"],
            cmap='pcc_sequential',
            edgecolors='black',
            linewidths=0.5
        )
        plt.colorbar(scatter, ax=ax1, label='Popularity Score', shrink=0.8)

        # Add trend line
        if len(data) > 1:
            z = np.polyfit(data["stars"], data["forks"], 1)
            p = np.poly1d(z)
            ax1.plot(data["stars"], p(data["stars"]),
                    color=self.viz_config["secondary_color"],
                    linestyle='--', linewidth=2, alpha=0.8)

        format_axis_labels(ax1, "Stars", "Forks", "Repository Popularity")
        ax1.grid(True, alpha=0.3)

        # Programming language distribution
        ax2 = plt.subplot(2, 2, 2)
        lang_counts = data["primary_language"].value_counts().head(10)

        bars = ax2.bar(range(len(lang_counts)), lang_counts.values,
                      alpha=0.7, color=self.viz_config["primary_color"],
                      edgecolor='black')
        ax2.set_xticks(range(len(lang_counts)))
        ax2.set_xticklabels(lang_counts.index, rotation=45, ha='right')

        # Add value labels on bars
        for bar, value in zip(bars, lang_counts.values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    str(value), ha='center', va='bottom')

        format_axis_labels(ax2, "Programming Language", "Number of Repositories",
                          "Language Distribution")
        ax2.grid(True, alpha=0.3, axis='y')

        # Activity score distribution
        ax3 = plt.subplot(2, 2, 3)
        ax3.hist(data["activity_score"], bins=20, alpha=0.7,
                color=self.viz_config["success_color"], edgecolor='black')
        ax3.axvline(data["activity_score"].mean(),
                   color=self.viz_config["danger_color"],
                   linestyle='--', linewidth=2,
                   label=f'Mean: {data["activity_score"].mean():.1f}')
        ax3.axvline(data["activity_score"].median(),
                   color=self.viz_config["warning_color"],
                   linestyle='--', linewidth=2,
                   label=f'Median: {data["activity_score"].median():.1f}')

        format_axis_labels(ax3, "Activity Score", "Frequency", "Activity Distribution")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Repository age vs popularity
        ax4 = plt.subplot(2, 2, 4)

        # Color by language (top 5 languages)
        top_languages = data["primary_language"].value_counts().head(5).index
        colors = ['red', 'blue', 'green', 'orange', 'purple']

        for i, lang in enumerate(top_languages):
            lang_data = data[data["primary_language"] == lang]
            ax4.scatter(lang_data["repo_age_days"], lang_data["popularity_score"],
                       alpha=0.7, s=60, color=colors[i], label=lang)

        # Other languages in gray
        other_data = data[~data["primary_language"].isin(top_languages)]
        if len(other_data) > 0:
            ax4.scatter(other_data["repo_age_days"], other_data["popularity_score"],
                       alpha=0.4, s=30, color='gray', label='Others')

        format_axis_labels(ax4, "Repository Age (days)", "Popularity Score",
                          "Age vs Popularity by Language")
        ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=self.export_config["image_dpi"],
                       bbox_inches='tight')

        return fig

    def plot_detailed_analysis(self, data: pd.DataFrame, save_path: str | None = None) -> plt.Figure:
        """Create detailed GitHub analysis dashboard."""
        fig = setup_figure_style(figsize=(18, 14))

        # Repository metrics correlation heatmap
        ax1 = plt.subplot(3, 3, 1)
        correlation_cols = ["stars", "forks", "watchers", "issues", "commits",
                           "contributors", "popularity_score", "activity_score"]
        corr_matrix = data[correlation_cols].corr()

        im = ax1.imshow(corr_matrix, cmap='pcc_diverging', aspect='auto', vmin=-1, vmax=1)
        ax1.set_xticks(range(len(correlation_cols)))
        ax1.set_yticks(range(len(correlation_cols)))
        ax1.set_xticklabels(correlation_cols, rotation=45, ha='right')
        ax1.set_yticklabels(correlation_cols)

        # Add correlation values
        for i in range(len(correlation_cols)):
            for j in range(len(correlation_cols)):
                text = ax1.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                               ha="center", va="center", color="black", fontsize=8)

        ax1.set_title("Metrics Correlation Matrix")
        plt.colorbar(im, ax=ax1, shrink=0.6)

        # Stars distribution by language (box plot)
        ax2 = plt.subplot(3, 3, 2)
        top_langs = data["primary_language"].value_counts().head(6).index
        stars_by_lang = [data[data["primary_language"] == lang]["stars"].values
                        for lang in top_langs]

        box_plot = ax2.boxplot(stars_by_lang, patch_artist=True)
        ax2.set_xticks(range(1, len(top_langs) + 1), list(top_langs))
        ax2.set_yscale("symlog")  # star counts are heavy-tailed
        for patch in box_plot['boxes']:
            patch.set_facecolor(series_color(0))
            patch.set_alpha(0.5)

        format_axis_labels(ax2, "Language", "Stars", "Stars Distribution by Language")
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)

        # Repository size vs activity
        ax3 = plt.subplot(3, 3, 3)
        ax3.scatter(data["size_kb"], data["commits"],
                   c=data["repo_age_days"], s=50, alpha=0.6, cmap='pcc_sequential')
        ax3.set_xscale('log')
        ax3.set_yscale('log')
        format_axis_labels(ax3, "Size (KB, log scale)", "Commits (log scale)",
                          "Repository Size vs Activity")
        ax3.grid(True, alpha=0.3)

        # License distribution pie chart
        ax4 = plt.subplot(3, 3, 4)
        license_counts = data["license"].value_counts()
        colors_pie = ['gold', 'lightcoral', 'lightskyblue', 'lightgreen', 'plum', 'orange']
        ax4.pie(license_counts.values, labels=license_counts.index, autopct='%1.1f%%',
               colors=colors_pie[:len(license_counts)], startangle=90)
        ax4.set_title("License Distribution")

        # Fork ratio analysis
        ax5 = plt.subplot(3, 3, 5)
        ax5.hist(data["fork_ratio"], bins=20, alpha=0.7,
                color='steelblue', edgecolor='black')
        ax5.axvline(data["fork_ratio"].mean(), color='red', linestyle='--', linewidth=2,
                   label=f'Mean: {data["fork_ratio"].mean():.3f}')
        format_axis_labels(ax5, "Fork Ratio", "Frequency", "Fork to Stars Ratio")
        ax5.legend()
        ax5.grid(True, alpha=0.3)

        # Active vs inactive repositories
        ax6 = plt.subplot(3, 3, 6)
        active_counts = data["is_active"].value_counts()
        bars = ax6.bar(['Inactive', 'Active'], active_counts.values,
                      color=['lightcoral', 'lightgreen'], alpha=0.7, edgecolor='black')

        # Add percentage labels
        total = sum(active_counts.values)
        for bar, count in zip(bars, active_counts.values):
            height = bar.get_height()
            ax6.text(bar.get_x() + bar.get_width()/2., height + total*0.01,
                    f'{count}\n({count/total*100:.1f}%)',
                    ha='center', va='bottom', fontweight='bold')

        format_axis_labels(ax6, "Activity Status", "Count", "Repository Activity Status")
        ax6.grid(True, alpha=0.3, axis='y')

        # Commits per contributor
        ax7 = plt.subplot(3, 3, 7)
        data["commits_per_contributor"] = data["commits"] / data["contributors"]
        ax7.scatter(data["contributors"], data["commits_per_contributor"],
                   alpha=0.6, s=50, color='darkgreen')
        format_axis_labels(ax7, "Contributors", "Commits per Contributor",
                          "Productivity Analysis")
        ax7.grid(True, alpha=0.3)

        # Repository type distribution
        ax8 = plt.subplot(3, 3, 8)
        type_counts = data["repo_type"].value_counts()
        ax8.bar(range(len(type_counts)), type_counts.values,
               alpha=0.7, color='orange', edgecolor='black')
        ax8.set_xticks(range(len(type_counts)))
        ax8.set_xticklabels(type_counts.index, rotation=45, ha='right')
        format_axis_labels(ax8, "Repository Type", "Count", "Repository Types")
        ax8.grid(True, alpha=0.3, axis='y')

        # Popularity vs activity scatter
        ax9 = plt.subplot(3, 3, 9)
        ax9.scatter(data["popularity_score"], data["activity_score"],
                   c=data["repo_age_days"], s=60, alpha=0.6, cmap='pcc_sequential')
        format_axis_labels(ax9, "Popularity Score", "Activity Score",
                          "Popularity vs Activity")
        ax9.grid(True, alpha=0.3)

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
