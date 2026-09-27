"""Tests for plotting modules."""

import pytest
import pandas as pd
import matplotlib.pyplot as plt
from pcc_vizforge.generators import RandomWalkGenerator, DiceGenerator
from pcc_vizforge.plots import RandomWalkMatplotlibPlot, DiceMatplotlibPlot


class TestRandomWalkPlot:
    """Test random walk plotting."""
    
    def test_matplotlib_plot(self):
        # Generate test data
        generator = RandomWalkGenerator()
        data = generator.generate(save_to_file=False)
        
        # Create plot
        plotter = RandomWalkMatplotlibPlot()
        fig = plotter.plot(data)
        
        assert isinstance(fig, plt.Figure)
        plt.close(fig)  # Clean up
    
    def test_plot_statistics(self):
        generator = RandomWalkGenerator()
        data = generator.generate(save_to_file=False)
        
        plotter = RandomWalkMatplotlibPlot()
        fig = plotter.plot_statistics(data)
        
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestDicePlot:
    """Test dice plotting."""
    
    def test_matplotlib_plot(self):
        generator = DiceGenerator()
        data = generator.generate(save_to_file=False)
        
        plotter = DiceMatplotlibPlot()
        fig = plotter.plot(data)
        
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestPlotlyImports:
    """Test that plotly modules can be imported."""
    
    def test_import_plotly_modules(self):
        """Test that plotly plot modules can be imported."""
        try:
            from pcc_vizforge.plots.random_walk_plotly import RandomWalkPlotlyPlot
            from pcc_vizforge.plots.dice_plotly import DicePlotlyPlot
            assert True  # If we get here, imports worked
        except ImportError as e:
            pytest.skip(f"Plotly not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__])