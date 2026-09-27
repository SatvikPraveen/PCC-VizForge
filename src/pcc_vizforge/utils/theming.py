"""Theming and styling utilities for PCC VizForge."""

from typing import Dict, List, Optional, Union

import matplotlib.pyplot as plt
import matplotlib as mpl


# Color palettes
COLOR_PALETTES = {
    "default": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
    "vibrant": ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"],
    "pastel": ["#ffb3ba", "#baffc9", "#bae1ff", "#ffffba", "#ffdfba"],
    "dark": ["#2c3e50", "#34495e", "#7f8c8d", "#95a5a6", "#bdc3c7"],
    "scientific": ["#003f5c", "#2f4b7c", "#665191", "#a05195", "#d45087"],
    "earth": ["#8B4513", "#228B22", "#4682B4", "#DAA520", "#CD853F"],
    "github": ["#24292e", "#0366d6", "#28a745", "#ffd33d", "#d73a49"],
}

# Matplotlib styles
MATPLOTLIB_STYLES = {
    "clean": {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#cccccc",
        "axes.linewidth": 1,
        "axes.grid": True,
        "grid.color": "#e6e6e6",
        "grid.linewidth": 0.5,
        "xtick.color": "#666666",
        "ytick.color": "#666666",
        "text.color": "#333333",
    },
    "dark": {
        "figure.facecolor": "#2e2e2e",
        "axes.facecolor": "#2e2e2e",
        "axes.edgecolor": "#666666",
        "axes.linewidth": 1,
        "axes.grid": True,
        "grid.color": "#404040",
        "grid.linewidth": 0.5,
        "xtick.color": "#cccccc",
        "ytick.color": "#cccccc",
        "text.color": "#ffffff",
    },
    "minimal": {
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "xtick.bottom": True,
        "xtick.top": False,
        "ytick.left": True,
        "ytick.right": False,
    }
}

# Plotly templates
PLOTLY_TEMPLATES = {
    "clean": "plotly_white",
    "dark": "plotly_dark", 
    "minimal": "simple_white",
    "presentation": "presentation",
    "seaborn": "seaborn",
}


def get_color_palette(name: str = "default", n_colors: Optional[int] = None) -> List[str]:
    """Get a color palette by name.
    
    Args:
        name: Name of the color palette
        n_colors: Number of colors to return (cycles if more than available)
        
    Returns:
        List of color hex codes
    """
    if name not in COLOR_PALETTES:
        name = "default"
    
    palette = COLOR_PALETTES[name]
    
    if n_colors is None:
        return palette
    
    # Cycle colors if more needed than available
    extended_palette = []
    for i in range(n_colors):
        extended_palette.append(palette[i % len(palette)])
    
    return extended_palette


def apply_style(style_name: str = "clean") -> None:
    """Apply a predefined matplotlib style.
    
    Args:
        style_name: Name of the style to apply
    """
    if style_name in MATPLOTLIB_STYLES:
        plt.rcParams.update(MATPLOTLIB_STYLES[style_name])
    else:
        # Fall back to matplotlib built-in styles
        try:
            plt.style.use(style_name)
        except OSError:
            print(f"Warning: Style '{style_name}' not found, using default")


def get_matplotlib_style(style_name: str = "clean") -> Dict[str, Union[str, float, bool]]:
    """Get matplotlib style parameters.
    
    Args:
        style_name: Name of the style
        
    Returns:
        Dictionary of matplotlib rcParams
    """
    return MATPLOTLIB_STYLES.get(style_name, MATPLOTLIB_STYLES["clean"])


def get_plotly_template(template_name: str = "clean") -> str:
    """Get Plotly template name.
    
    Args:
        template_name: Name of the template
        
    Returns:
        Plotly template string
    """
    return PLOTLY_TEMPLATES.get(template_name, "plotly_white")


def create_custom_colormap(colors: List[str], name: str = "custom") -> mpl.colors.LinearSegmentedColormap:
    """Create a custom matplotlib colormap.
    
    Args:
        colors: List of color hex codes
        name: Name for the colormap
        
    Returns:
        Custom colormap
    """
    return mpl.colors.LinearSegmentedColormap.from_list(name, colors)


def setup_figure_style(figsize: tuple = (12, 8), style: str = "clean", 
                      palette: str = "default") -> plt.Figure:
    """Setup a matplotlib figure with consistent styling.
    
    Args:
        figsize: Figure size (width, height)
        style: Style name to apply
        palette: Color palette name
        
    Returns:
        Configured matplotlib figure
    """
    apply_style(style)
    fig = plt.figure(figsize=figsize)
    
    # Set color cycle
    colors = get_color_palette(palette)
    plt.rcParams['axes.prop_cycle'] = plt.cycler(color=colors)
    
    return fig


def format_axis_labels(ax: plt.Axes, xlabel: str = "", ylabel: str = "", 
                      title: str = "", title_size: int = 14) -> None:
    """Format axis labels with consistent styling.
    
    Args:
        ax: Matplotlib axes object
        xlabel: X-axis label
        ylabel: Y-axis label
        title: Plot title
        title_size: Title font size
    """
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=12, fontweight='medium')
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=12, fontweight='medium')
    if title:
        ax.set_title(title, fontsize=title_size, fontweight='bold', pad=20)
    
    # Format tick labels
    ax.tick_params(axis='both', which='major', labelsize=10)


def add_watermark(ax: plt.Axes, text: str = "PCC VizForge", 
                 position: tuple = (0.99, 0.01), alpha: float = 0.3) -> None:
    """Add a watermark to the plot.
    
    Args:
        ax: Matplotlib axes object
        text: Watermark text
        position: Position (x, y) in axes coordinates
        alpha: Transparency level
    """
    ax.text(position[0], position[1], text, transform=ax.transAxes,
            fontsize=8, alpha=alpha, ha='right', va='bottom',
            style='italic', color='gray')