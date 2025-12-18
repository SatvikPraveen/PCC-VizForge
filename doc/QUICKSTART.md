# Quick Start Guide - PCC-VizForge

## For New Developers

### 1. Initial Setup (5 minutes)

```bash
# Clone the repository
git clone https://github.com/SatvikPraveen/PCC-VizForge.git
cd PCC-VizForge

# One-command setup (installs dependencies + pre-commit hooks)
make setup

# Verify everything works
make all-checks
```

### 2. Understanding the Structure

```
PCC-VizForge/
├── src/                          # Main source code
│   ├── exceptions.py            # Custom exceptions ⭐ NEW
│   ├── constants.py             # Project constants ⭐ NEW
│   ├── logging_config.py        # Logging setup ⭐ NEW
│   ├── cli.py                   # Command-line interface (ENHANCED)
│   ├── generators/              # Data generators
│   │   ├── random_walk.py      # (ENHANCED with type hints)
│   │   ├── dice.py
│   │   ├── weather.py
│   │   ├── quakes.py
│   │   └── github.py
│   ├── plots/                   # Visualization modules
│   │   ├── dice_mpl.py
│   │   ├── dice_plotly.py
│   │   ├── weather_mpl.py
│   │   ├── weather_plotly.py
│   │   ├── random_walk_mpl.py
│   │   ├── random_walk_plotly.py
│   │   ├── quakes_mpl.py
│   │   ├── quakes_plotly.py
│   │   ├── github_mpl.py
│   │   └── github_plotly.py
│   └── utils/
│       ├── io.py               # I/O utilities (ENHANCED)
│       ├── theming.py          # Styling utilities
│       └── validation.py       # Input validation ⭐ NEW
├── tests/
│   ├── test_generators.py               # Original tests
│   └── test_generators_comprehensive.py # NEW: 100+ tests ⭐
├── config/                      # YAML configurations
├── notebooks/                   # Jupyter analysis notebooks
├── doc/                         # Documentation (this folder)
├── CONTRIBUTING.md             # How to contribute ⭐ NEW
├── pytest.ini                  # Test configuration ⭐ NEW
├── .pre-commit-config.yaml     # Pre-commit hooks ⭐ NEW
├── Makefile                    # Development commands (ENHANCED)
└── pyproject.toml              # Project config
```

⭐ = New or significantly enhanced

### 3. Common Development Tasks

#### Run Tests
```bash
make test              # Run all tests
make test-coverage     # With coverage report
make test-verbose      # Detailed output
```

#### Check Code Quality
```bash
make lint              # Check linting (flake8)
make type-check        # Check types (mypy)
make check-format      # Check formatting (black)
make all-checks        # All checks at once
```

#### Format Code
```bash
make format            # Auto-format with black + isort
```

#### Generate Data
```bash
make demo              # Quick demo
make generate-all      # Full generation of all visualizations
```

### 4. Making Changes

```bash
# Create a feature branch
git checkout -b feature/my-feature

# Make your changes...
# Add code, tests, documentation

# Run full quality check
make all-checks

# Commit (pre-commit hooks run automatically)
git add .
git commit -m "Add feature description"

# Push and create Pull Request
git push origin feature/my-feature
```

### 5. Error Handling & Logging

**Using custom exceptions:**
```python
from src.exceptions import InvalidParameterError, DataGenerationError

try:
    generator = RandomWalkGenerator(config_name)
    data = generator.generate()
except InvalidParameterError as e:
    logger.error(f"Configuration error: {e}")
except DataGenerationError as e:
    logger.error(f"Generation failed: {e}")
```

**Using logging:**
```python
import logging
from src.logging_config import get_logger

logger = get_logger(__name__)

logger.debug("Detailed debug info")
logger.info("Important operation")
logger.warning("Potential issue")
logger.error("Error occurred", exc_info=True)
```

### 6. Adding Type Hints

```python
from typing import Dict, List, Optional, Union
import pandas as pd
from src.exceptions import DataGenerationError

def calculate_statistics(
    data: pd.DataFrame,
    groups: Optional[List[str]] = None
) -> Dict[str, float]:
    """Calculate statistics.
    
    Args:
        data: Input DataFrame
        groups: Optional group columns
        
    Returns:
        Dictionary of statistics
        
    Raises:
        DataGenerationError: If calculation fails
    """
    try:
        if data.empty:
            raise DataGenerationError("Cannot calculate on empty data")
        # implementation
        return stats
    except Exception as e:
        logger.error(f"Statistics calculation failed: {e}")
        raise DataGenerationError(f"Failed: {e}")
```

### 7. Running Tests with Markers

```bash
# Run only unit tests
pytest -m "unit" tests/

# Run only integration tests
pytest -m "integration" tests/

# Run tests with verbose output
pytest -v tests/

# Run specific test file
pytest tests/test_generators_comprehensive.py

# Run tests matching pattern
pytest -k "random_walk" tests/
```

### 8. Pre-commit Hooks

```bash
# Install hooks (usually done during setup)
make pre-commit-install

# Run pre-commit on all files
make pre-commit-run

# Skip pre-commit for a commit (not recommended)
git commit --no-verify
```

---

## Key Files to Know

| File | Purpose | Last Modified |
|------|---------|---------------|
| `src/exceptions.py` | Custom exceptions | Phase 1 ⭐ |
| `src/logging_config.py` | Logging setup | Phase 1 ⭐ |
| `src/constants.py` | Project constants | Phase 1 ⭐ |
| `src/utils/validation.py` | Input validation | Phase 1 ⭐ |
| `src/cli.py` | Command-line interface | Phase 1 🔄 |
| `src/generators/random_walk.py` | Random walk data | Phase 1 🔄 |
| `tests/test_generators_comprehensive.py` | Test suite | Phase 2 ⭐ |
| `CONTRIBUTING.md` | Contributing guide | Phase 2 ⭐ |
| `Makefile` | Development commands | Phase 2 🔄 |

Legend: ⭐ = New, 🔄 = Enhanced

---

## Troubleshooting

### Installation Issues
```bash
# Reinstall dependencies
pip install -e ".[dev]"

# Clear cache and reinstall
pip cache purge
pip install -e ".[dev]"
```

### Pre-commit Issues
```bash
# Reinstall pre-commit hooks
pre-commit uninstall
pre-commit install

# Run manually to debug
pre-commit run --all-files
```

### Test Failures
```bash
# Run specific failing test with verbose output
pytest -vvv tests/test_file.py::TestClass::test_method

# See full error traceback
pytest --tb=long tests/
```

### Type Check Failures
```bash
# See all type errors with line numbers
mypy src/

# Generate type stub files
mypy src/ --emulate-version 3.8
```

---

## Common Make Commands

| Command | Purpose |
|---------|---------|
| `make setup` | One-command project setup |
| `make test` | Run all tests |
| `make lint` | Check code quality |
| `make format` | Auto-format code |
| `make all-checks` | Run all quality checks |
| `make clean` | Clean build artifacts |
| `make help` | Show all available commands |

---

## Useful Links

- [../CONTRIBUTING.md](../CONTRIBUTING.md) - Full contributing guide
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [ENHANCEMENT_SUMMARY.md](ENHANCEMENT_SUMMARY.md) - What changed
- [../README.md](../README.md) - Project overview
- [README.md](README.md) - Documentation index
- [../pytest.ini](../pytest.ini) - Test configuration
- [../.pre-commit-config.yaml](../.pre-commit-config.yaml) - Pre-commit setup

---

## Getting Help

1. Check existing documentation
2. Look at similar code examples
3. Run with `--log-level DEBUG` for detailed logs
4. Check error messages - they're now very descriptive!
5. Open an issue or discussion on GitHub

---

## Next Steps

1. ✅ **Setup** - Run `make setup`
2. ✅ **Verify** - Run `make all-checks`
3. ✅ **Explore** - Look at `src/generators/` and `tests/`
4. ✅ **Contribute** - Follow [CONTRIBUTING.md](CONTRIBUTING.md)

**Happy coding! 🚀**
