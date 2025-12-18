# PCC-VizForge

**A Personal Data Visualization Playground**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Personal Project](https://img.shields.io/badge/type-personal%20project-green.svg)](https://github.com/SatvikPraveen/PCC-VizForge)

> _"Creating beautiful visualizations from synthetic data across multiple domains - because data should tell compelling stories."_

## 🎯 About This Project

**PCC-VizForge** is my personal exploration into the world of data visualization and synthetic data generation. This toolkit demonstrates my ability to:

- Generate realistic synthetic datasets across diverse domains
- Create publication-quality static visualizations with Matplotlib
- Build interactive web-ready charts with Plotly
- Implement modular, scalable code architecture
- Apply statistical analysis and data science concepts

This project serves as both a learning exercise and a showcase of data visualization capabilities, perfect for educational purposes, prototyping, or when you need realistic data without privacy concerns.

## 🚀 Key Features

### 🎲 Multi-Domain Data Generation

- **Random Walks**: Stochastic processes with 1D/2D simulations and statistical analysis
- **Dice Simulations**: Probability theory demonstrations with Gutenberg-Richter law applications
- **Weather Patterns**: Realistic meteorological data with seasonal variations and extreme events
- **Earthquake Data**: Seismic activity simulations following geological principles
- **GitHub Analytics**: Repository metrics and developer activity patterns

### 📊 Dual Visualization Approach

- **Matplotlib**: Professional static plots for research papers and presentations
- **Plotly**: Interactive dashboards with hover effects, zooming, and web deployment

### 💾 Flexible Export Options

- **Images**: High-resolution PNG/JPG for publications
- **Interactive HTML**: Web-ready visualizations for portfolios
- **Data Formats**: CSV/JSON for further analysis and sharing

## 🛠️ Project Architecture

```
PCC-VizForge/
├── 📋 README.md                    # You are here!
├── ⚙️ pyproject.toml              # Python package configuration
├── 🔧 Makefile                    # Development automation
├── � doc/                        # Documentation (changelog, guides, etc.)
├── �📁 config/                     # YAML configuration files
│   ├── random_walk.yaml          # Random walk parameters
│   ├── dice.yaml                 # Dice simulation settings
│   ├── weather.yaml              # Weather generation config
│   ├── quakes.yaml               # Earthquake data parameters
│   └── github.yaml               # GitHub statistics config
├── 🧬 src/                        # Core source code
│   ├── generators/               # Synthetic data generators
│   │   ├── random_walk.py       # Stochastic process simulation
│   │   ├── dice.py              # Probability distributions
│   │   ├── weather.py           # Meteorological data
│   │   ├── quakes.py            # Seismic activity
│   │   └── github.py            # Repository analytics
│   ├── plots/                   # Visualization modules
│   │   ├── *_mpl.py            # Matplotlib implementations
│   │   └── *_plotly.py         # Plotly implementations
│   ├── utils/                   # Shared utilities
│   │   ├── io.py               # Data I/O operations
│   │   └── theming.py          # Consistent styling
│   └── cli.py                  # Command-line interface
├── 📊 data/synthetic/            # Generated datasets
│   ├── random_walk/             # Random walk data
│   ├── dice/                    # Dice roll results
│   ├── weather/                 # Weather time series
│   ├── quakes/                  # Earthquake catalogs
│   └── github/                  # Repository metrics
├── 🎨 exports/                   # Output visualizations
│   ├── images/                  # Static plots (PNG/JPG)
│   └── html/                    # Interactive charts
├── 📓 notebooks/                 # Jupyter analysis notebooks
│   ├── 01_random_walk.ipynb     # Random walk analysis
│   ├── 02_dice.ipynb            # Probability simulations
│   ├── 03_weather.ipynb         # Weather data exploration
│   ├── 04_quakes.ipynb          # Seismic analysis
│   └── 05_github.ipynb          # Repository analytics
└── 🧪 tests/                     # Unit tests
    ├── test_generators.py       # Data generation tests
    └── test_plots.py            # Visualization tests
```

## 🚀 Quick Start

### Installation

```bash
# Clone my repository
git clone https://github.com/SatvikPraveen/PCC-VizForge.git
cd PCC-VizForge

# Install the package
pip install -e .

# Or use the setup script
chmod +x setup_pcc_vizforge.sh
./setup_pcc_vizforge.sh
```

### Command Line Usage

```bash
# Generate a random walk visualization
pcc-vizforge random_walk --library matplotlib --export-type image

# Create interactive dice probability analysis
pcc-vizforge dice --library plotly --export-type html

# Build a weather dashboard
pcc-vizforge weather --library plotly --export-type html

# Generate earthquake analysis
pcc-vizforge quakes --library matplotlib --export-type image

# Create GitHub repository analytics
pcc-vizforge github --library plotly --export-type html

# Run a complete demonstration
pcc-vizforge demo
```

### Python API

```python
from src.generators.random_walk import RandomWalkGenerator
from src.plots.random_walk_mpl import RandomWalkMatplotlib

# Generate synthetic random walk data
config = {'n_steps': 1000, 'n_walks': 5, 'step_size': 1.0}
generator = RandomWalkGenerator(config)
walk_data = generator.generate_1d_walk(n_steps=1000)

# Create visualization
plotter = RandomWalkMatplotlib(config)
fig, ax = plt.subplots(figsize=(12, 8))
plotter.plot_1d_timeseries(walk_data, ax=ax)
plt.show()
```

### Jupyter Notebooks

```bash
# Launch Jupyter and explore the analysis notebooks
jupyter notebook notebooks/

# Or explore specific domains
jupyter notebook notebooks/01_random_walk.ipynb
jupyter notebook notebooks/03_weather.ipynb
```

## 📊 Visualization Showcase

### 1. Random Walk Analysis 🚶‍♂️

- **1D Time Series**: Multiple trajectory comparisons with statistical convergence
- **2D Spatial Paths**: Beautiful walk patterns with start/end markers
- **Statistical Analysis**: Mean square displacement and diffusion coefficients
- **Interactive Features**: Hover data, zoom controls, animation sequences

### 2. Dice Probability Simulations 🎲

- **Frequency Distributions**: Single die and multiple dice sum analysis
- **Convergence Demonstrations**: Law of large numbers visualizations
- **Theoretical vs Empirical**: Chi-square goodness of fit testing
- **Interactive Probability**: Dynamic probability calculators

### 3. Weather Pattern Analysis 🌦️

- **Time Series Decomposition**: Trend, seasonal, and residual components
- **Climate Comparisons**: Temperate, tropical, arid, and polar zones
- **Extreme Events**: Heatwaves, cold snaps, and storm systems
- **3D Weather Space**: Multi-parameter relationship exploration

### 4. Earthquake Seismology 🌍

- **Magnitude-Frequency**: Gutenberg-Richter law demonstrations
- **Spatial Clustering**: Geographic hotspot identification using DBSCAN
- **Aftershock Analysis**: Omori's law decay patterns
- **Interactive Maps**: Global seismic activity with magnitude scaling

### 5. GitHub Repository Analytics 📈

- **Development Patterns**: Commit frequency and contributor analysis
- **Collaboration Networks**: Developer interaction graphs
- **Repository Health**: Comprehensive scoring system
- **Project Evolution**: Timeline visualization of repository growth

## ⚙️ Configuration System

Each domain has dedicated YAML configuration files for easy customization:

```yaml
# config/random_walk.yaml
data_generation:
  n_steps: 1000
  n_walks: 5
  step_size: 1.0
  random_seed: 42

visualization:
  matplotlib:
    figsize: [12, 8]
    style: "seaborn-v0_8"
    colors: ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

  plotly:
    template: "plotly_white"
    width: 900
    height: 600
    animation_duration: 1000
```

## 🎨 Theming and Aesthetics

Built-in themes for consistent, professional visualizations:

```python
from src.utils.theming import get_plot_theme, apply_style

# Available themes
themes = ['clean', 'dark', 'minimal', 'scientific', 'vibrant']

# Apply theme
theme = get_plot_theme('clean')
apply_style(theme)

# Custom color palettes
colors = theme.get_color_palette('qualitative', n_colors=8)
```

## 🧪 Development Workflow

### Available Make Commands

```bash
make install-dev    # Install with development dependencies
make test          # Run comprehensive unit tests
make lint          # Code quality checks (flake8, mypy)
make format        # Auto-format code with black
make clean         # Remove generated files and __pycache__
make demo          # Quick demonstration of all features
make docs          # Generate documentation
```

### Testing and Quality Assurance

```bash
# Run the full test suite
pytest tests/ -v --cov=src --cov-report=html

# Test specific modules
pytest tests/test_generators.py -k "test_random_walk"
pytest tests/test_plots.py -k "test_matplotlib_plots"

# Code formatting and linting
black src/ tests/
flake8 src/ tests/ --max-line-length=100
mypy src/ --ignore-missing-imports
```

## 📈 Advanced Examples

### Multi-Scenario Analysis

```python
from src.generators.weather import WeatherGenerator

# Generate multiple climate scenarios
generator = WeatherGenerator()
scenarios = {
    'tropical': {'temperature_base': 28, 'humidity_base': 85},
    'temperate': {'temperature_base': 15, 'humidity_base': 65},
    'arid': {'temperature_base': 25, 'humidity_base': 30}
}

results = {}
for climate, params in scenarios.items():
    data = generator.generate_climate_specific_data(
        climate_type=climate, **params
    )
    results[climate] = data
```

### Custom Visualization Pipeline

```python
from src.plots.quakes_plotly import QuakePlotly
from src.utils.io import save_data, load_data

# Load earthquake data
quake_data = load_data('data/synthetic/quakes/earthquake_catalog.csv')

# Create interactive 3D visualization
plotter = QuakePlotly()
fig = plotter.plot_3d_seismicity(quake_data)

# Customize and save
fig.update_layout(
    title="Global Seismic Activity - Interactive 3D View",
    scene=dict(bgcolor='black'),
    template='plotly_dark'
)
fig.write_html('exports/html/custom_earthquake_3d.html')
```

### Statistical Analysis Integration

```python
from scipy import stats
import numpy as np

# Analyze dice rolling fairness
dice_data = load_data('data/synthetic/dice/all_dice_rolls.csv')
single_die = dice_data['single_die'].dropna()

# Chi-square goodness of fit test
observed = [np.sum(single_die == i) for i in range(1, 7)]
expected = [len(single_die) / 6] * 6
chi2_stat, p_value = stats.chisquare(observed, expected)

print(f"Chi-square statistic: {chi2_stat:.4f}")
print(f"P-value: {p_value:.4f}")
print(f"Fair die? {'Yes' if p_value > 0.05 else 'No'}")
```

## 🎯 Personal Learning Outcomes

Through this project, I've demonstrated proficiency in:

### Technical Skills

- **Data Generation**: Synthetic data creation following statistical distributions
- **Visualization**: Both static (Matplotlib) and interactive (Plotly) plotting
- **Statistical Analysis**: Hypothesis testing, regression analysis, clustering
- **Software Architecture**: Modular design with clear separation of concerns
- **Testing**: Unit tests with pytest and code coverage analysis

### Domain Knowledge

- **Probability Theory**: Random processes, central limit theorem, statistical distributions
- **Meteorology**: Weather patterns, seasonal analysis, extreme event modeling
- **Seismology**: Earthquake statistics, magnitude-frequency relationships, spatial analysis
- **Software Engineering**: Development metrics, collaboration patterns, repository health

### Best Practices

- **Code Quality**: Type hints, documentation, consistent styling
- **Configuration Management**: YAML-based settings for reproducibility
- **Data Pipeline**: ETL processes with validation and error handling
- **Version Control**: Structured git workflow with meaningful commits

## 🤝 Contributing

While this is a personal project, I welcome feedback, suggestions, and contributions:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/awesome-addition`)
3. **Commit** your changes (`git commit -m 'Add awesome feature'`)
4. **Push** to the branch (`git push origin feature/awesome-addition`)
5. **Open** a Pull Request with detailed description

### Development Setup

```bash
git clone https://github.com/SatvikPraveen/PCC-VizForge.git
cd PCC-VizForge
make install-dev
make test
```

## 📚 Educational Resources

This project can serve as a learning resource for:

- **Data Science Students**: Real-world data generation and analysis examples
- **Visualization Enthusiasts**: Best practices for both static and interactive plots
- **Python Developers**: Clean, modular code architecture patterns
- **Statistics Learners**: Applied statistical concepts with visual demonstrations

## 🔮 Future Enhancements

Potential areas for expansion:

- [ ] **Time Series Forecasting**: ARIMA, LSTM models for weather/earthquake prediction
- [ ] **Machine Learning Integration**: Clustering, classification, anomaly detection
- [ ] **Real Data Integration**: APIs for live data feeds (weather, seismic, GitHub)
- [ ] **Web Dashboard**: Flask/Streamlit app for interactive exploration
- [ ] **3D Visualizations**: Advanced 3D plotting with better interaction
- [ ] **Performance Optimization**: Cython/Numba for large dataset handling

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

**What this means:**

- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Private use allowed
- ❗ License and copyright notice required

## 🙏 Acknowledgments

- **Libraries**: Built with love using [Matplotlib](https://matplotlib.org/), [Plotly](https://plotly.com/), [NumPy](https://numpy.org/), [Pandas](https://pandas.pydata.org/), and [SciPy](https://scipy.org/)
- **Inspiration**: Scientific visualization best practices and educational data science resources
- **Community**: Stack Overflow, GitHub, and the broader Python data science community

## 📞 Connect With Me

- 🐙 **GitHub**: [@SatvikPraveen](https://github.com/SatvikPraveen)
- 💼 **LinkedIn**: Connect for professional discussions about data science and visualization
- 🐛 **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/SatvikPraveen/PCC-VizForge/issues)

---

**"Data visualization is not just about making pretty charts - it's about revealing the hidden stories within data and making complex concepts accessible to everyone."**

_Built with ❤️ and lots of ☕ by Satvik Praveen_

---

### 🔧 Quick Reference

| Command                       | Description                |
| ----------------------------- | -------------------------- |
| `make demo`                   | Run complete demonstration |
| `pcc-vizforge --help`         | Show all CLI options       |
| `jupyter notebook notebooks/` | Explore analysis notebooks |
| `make test`                   | Run comprehensive tests    |
| `make clean && make demo`     | Fresh start demonstration  |

**Star ⭐ this repository if you find it useful for your data visualization journey!**
