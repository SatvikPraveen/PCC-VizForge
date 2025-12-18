.
├── .DS_Store
├── .gitignore
├── config
│   ├── dice.yaml
│   ├── github.yaml
│   ├── quakes.yaml
│   ├── random_walk.yaml
│   └── weather.yaml
├── data
│   └── synthetic
│   ├── dice
│   │   └── .keep
│   ├── github
│   │   └── .keep
│   ├── quakes
│   │   └── .keep
│   ├── random_walk
│   │   └── .keep
│   └── weather
│   └── .keep
├── exports
│   ├── html
│   │   └── .keep
│   └── images
│   └── .keep
├── Makefile
├── notebooks
│   ├── 01_random_walk.ipynb
│   ├── 02_dice.ipynb
│   ├── 03_weather.ipynb
│   ├── 04_quakes.ipynb
│   └── 05_github.ipynb
├── PROJECT_STRUCTURE.md
├── pyproject.toml
├── README.md
├── setup_pcc_vizforge.sh
├── src
│   ├── **init**.py
│   ├── cli.py
│   ├── generators
│   │   ├── **init**.py
│   │   ├── dice.py
│   │   ├── github.py
│   │   ├── quakes.py
│   │   ├── random_walk.py
│   │   └── weather.py
│   ├── plots
│   │   ├── **init**.py
│   │   ├── dice_mpl.py
│   │   ├── dice_plotly.py
│   │   ├── github_mpl.py
│   │   ├── github_plotly.py
│   │   ├── quakes_mpl.py
│   │   ├── quakes_plotly.py
│   │   ├── random_walk_mpl.py
│   │   ├── random_walk_plotly.py
│   │   ├── weather_mpl.py
│   │   └── weather_plotly.py
│   └── utils
│   ├── **init**.py
│   ├── io.py
│   └── theming.py
└── tests
├── **init**.py
├── test_generators.py
└── test_plots.py

18 directories, 49 files
