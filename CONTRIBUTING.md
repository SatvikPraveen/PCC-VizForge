# Contributing to PCC-VizForge

Thank you for your interest in contributing to PCC-VizForge! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions with other contributors.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip/conda for package management
- Git for version control

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SatvikPraveen/PCC-VizForge.git
   cd PCC-VizForge
   ```

2. **Set up the development environment:**
   ```bash
   make setup  # Installs dependencies and pre-commit hooks
   ```

3. **Verify installation:**
   ```bash
   make all-checks  # Run all quality checks
   ```

## Development Workflow

### 1. Creating a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix-name
```

Use descriptive branch names that indicate the type of change.

### 2. Making Changes

- Follow the existing code style (see Code Standards below)
- Add type hints to all functions and methods
- Write docstrings for all public functions
- Add logging statements for important operations
- Add appropriate error handling

### 3. Testing Your Changes

Before committing, run the full test suite:

```bash
make all-checks  # Format, lint, type-check, and test
```

Or run individual checks:

```bash
make test           # Run tests
make test-coverage  # Run tests with coverage report
make lint          # Run flake8
make type-check    # Run mypy
make format        # Auto-format code
```

### 4. Committing Changes

```bash
git add .
git commit -m "Brief description of changes"
```

Use clear, concise commit messages. The pre-commit hooks will automatically:
- Format code with black/isort
- Run flake8 linting
- Remove trailing whitespace
- Check for merge conflicts

### 5. Pushing and Creating a Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title describing the change
- Description of what was changed and why
- Reference to related issues (if any)
- Any breaking changes clearly noted

## Code Standards

### Style Guide

- **Formatting:** Code is formatted with `black` (88-character line length)
- **Import Sorting:** Imports are sorted with `isort` (black profile)
- **Linting:** Code is checked with `flake8`
- **Type Checking:** Type hints are checked with `mypy`

### Type Hints

All functions and methods should have complete type hints:

```python
def validate_positive_int(
    value: Any, param_name: str, min_val: int = 1
) -> int:
    """Validate that a value is a positive integer."""
    # implementation
```

### Docstrings

Use Google-style docstrings for all public functions and classes:

```python
def generate(self, save_to_file: bool = True) -> pd.DataFrame:
    """Generate random walk data.

    Args:
        save_to_file: Whether to save generated data to file

    Returns:
        DataFrame with random walk data

    Raises:
        DataGenerationError: If data generation fails
    """
    # implementation
```

### Error Handling

Use custom exceptions from `src/exceptions.py`:

```python
from src.exceptions import InvalidParameterError, DataGenerationError

if not valid:
    raise InvalidParameterError(f"Invalid parameter: {value}")
```

### Logging

Use the logging module for all logging:

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
```

## Adding New Features

### Adding a New Generator

1. Create a new file in `src/generators/`
2. Implement the generator class with proper type hints and error handling
3. Add tests in `tests/test_generators_comprehensive.py`
4. Add configuration file in `config/`
5. Update `src/generators/__init__.py` to export the generator

Example:

```python
# src/generators/new_generator.py
from src.exceptions import DataGenerationError

class NewGenerator:
    def __init__(self, config_name: str = "new_data") -> None:
        """Initialize generator with configuration."""
        self.config = load_config(config_name)
        self._validate_config()
    
    def generate(self, save_to_file: bool = True) -> pd.DataFrame:
        """Generate data."""
        # implementation
```

### Adding a New Plot Type

1. Create matplotlib implementation: `src/plots/new_data_mpl.py`
2. Create plotly implementation: `src/plots/new_data_plotly.py`
3. Add tests in `tests/test_plots.py`
4. Update `src/plots/__init__.py` to export the plot classes

### Adding a New Configuration

1. Create `config/new_config.yaml` with all required parameters
2. Document the configuration in README.md
3. Add configuration to CLI help text

## Running Tests

### Full Test Suite

```bash
make test          # Run all tests
make test-verbose  # Run with verbose output
make test-coverage # Run with coverage report
```

### Specific Tests

```bash
# Run specific test file
pytest tests/test_generators_comprehensive.py

# Run specific test class
pytest tests/test_generators_comprehensive.py::TestRandomWalkGenerator

# Run specific test
pytest tests/test_generators_comprehensive.py::TestRandomWalkGenerator::test_generate_basic

# Run tests matching a pattern
pytest -k "random_walk"

# Run tests with markers
pytest -m "unit"  # unit tests only
pytest -m "integration"  # integration tests only
```

## Documentation

- Keep README.md updated with new features
- Add docstrings to all public APIs
- Update doc/CHANGELOG.md for significant changes
- Add examples for new features in notebooks/

## Reporting Issues

When reporting bugs, please include:

- Python version (`python --version`)
- OS and OS version
- PCC-VizForge version
- Minimal reproducible example
- Expected vs actual behavior
- Any error messages/stack traces

## Git Workflow

### Before Pushing

1. Update local main: `git pull origin main`
2. Rebase your branch: `git rebase main`
3. Run full test suite: `make all-checks`
4. Push changes: `git push origin feature-name`

### After Creating PR

- Wait for CI checks to pass
- Respond to review comments promptly
- Make requested changes in new commits (don't force push)
- Re-request review after making changes

## Release Process

1. Update version in `pyproject.toml` and `src/__init__.py`
2. Update doc/CHANGELOG.md
3. Create a release commit
4. Tag release: `git tag v0.2.0`
5. Push to GitHub: `git push && git push --tags`
6. GitHub Actions will automatically publish to PyPI

## Questions?

- Check existing documentation in README.md
- Look at existing code examples
- Open an issue with the "question" label
- Check project discussions

Thank you for contributing to PCC-VizForge! 🎉
