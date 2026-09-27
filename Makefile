# Location: Makefile

.PHONY: install install-dev test test-verbose test-coverage clean lint format \
	check-format type-check all-checks help jupyter build publish-test publish \
	generate-all demo pre-commit-install pre-commit-run setup clean-data clean-all test-quick

# Default target
help:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "PCC-VizForge - Project Management Commands"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "SETUP & INSTALLATION:"
	@echo "  make setup           Setup pre-commit hooks and install dependencies"
	@echo "  make install         Install the package"
	@echo "  make install-dev     Install package with development dependencies"
	@echo ""
	@echo "TESTING & QUALITY:"
	@echo "  make test            Run tests (pytest)"
	@echo "  make test-verbose    Run tests with verbose output"
	@echo "  make test-coverage   Run tests with coverage report"
	@echo "  make lint            Run code linting (flake8)"
	@echo "  make format          Format code with black and isort"
	@echo "  make check-format    Check code formatting"
	@echo "  make type-check      Run type checking with mypy"
	@echo "  make all-checks      Run all checks (format, lint, type, test)"
	@echo ""
	@echo "CODE GENERATION:"
	@echo "  make generate-all    Generate all visualizations"
	@echo "  make demo            Run quick demo"
	@echo ""
	@echo "PRE-COMMIT HOOKS:"
	@echo "  make pre-commit-install  Install pre-commit hooks"
	@echo "  make pre-commit-run      Run pre-commit on all files"
	@echo ""
	@echo "CLEANUP:"
	@echo "  make clean           Clean build and cache files"
	@echo "  make clean-data      Clean generated data and exports"
	@echo "  make clean-all       Clean everything"
	@echo ""

# ============================= SETUP =============================

setup: install-dev pre-commit-install
	@echo "✓ Project setup completed successfully!"

# ============================= INSTALLATION =============================

install:
	@echo "Installing PCC-VizForge..."
	pip install -e .
	@echo "✓ Installation complete"

install-dev:
	@echo "Installing PCC-VizForge with development dependencies..."
	pip install -e ".[dev]"
	@echo "✓ Installation with dev dependencies complete"

# ============================= TESTING =============================

test:
	@echo "Running tests..."
	pytest tests/
	@echo "✓ Tests completed"

test-verbose:
	@echo "Running tests (verbose)..."
	pytest -v tests/

test-coverage:
	@echo "Running tests with coverage..."
	pytest --cov=pcc_vizforge --cov-report=html --cov-report=term-missing tests/
	@echo "✓ Coverage report generated in htmlcov/index.html"

test-quick:
	@echo "Running quick tests..."
	pytest -m "not slow" tests/

# ============================= CODE QUALITY =============================

lint:
	@echo "Running code linting..."
	flake8 src/ tests/ --count --statistics
	@echo "✓ Linting complete"

format:
	@echo "Formatting code with black and isort..."
	black src/ tests/
	isort src/ tests/ --profile black
	@echo "✓ Code formatting complete"

check-format:
	@echo "Checking code formatting..."
	black --check src/ tests/
	isort --check-only src/ tests/ --profile black
	@echo "✓ Code formatting check passed"

type-check:
	@echo "Running type checking with mypy..."
	mypy --ignore-missing-imports
	@echo "✓ Type checking complete"

all-checks: check-format lint type-check test
	@echo "✓ All checks passed!"

# ============================= PRE-COMMIT =============================

pre-commit-install:
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "✓ Pre-commit hooks installed"

pre-commit-run:
	@echo "Running pre-commit on all files..."
	pre-commit run --all-files
	@echo "✓ Pre-commit checks completed"

# ============================= CLEANING =============================

clean:
	@echo "Cleaning build and cache files..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf logs/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✓ Cleanup complete"

clean-data:
	@echo "Cleaning generated data and exports..."
	rm -rf data/synthetic/*/* 2>/dev/null || true
	rm -rf exports/images/* 2>/dev/null || true
	rm -rf exports/html/* 2>/dev/null || true
	@echo "✓ Data cleanup complete"

clean-all: clean clean-data
	@echo "✓ Complete cleanup finished"

# ============================= DEVELOPMENT =============================

jupyter:
	@echo "Launching Jupyter notebook..."
	jupyter notebook notebooks/

# ============================= BUILD & DISTRIBUTION =============================

build:
	@echo "Building distribution packages..."
	python -m pip install --upgrade build
	python -m build
	@echo "✓ Build complete"

publish-test:
	@echo "Publishing to test PyPI..."
	python -m pip install --upgrade twine
	python -m twine upload --repository testpypi dist/*
	@echo "✓ Published to test PyPI"

publish:
	@echo "Publishing to PyPI..."
	python -m pip install --upgrade twine
	python -m twine upload dist/*
	@echo "✓ Published to PyPI"

# ============================= DATA GENERATION =============================

generate-all:
	@echo "Generating all visualizations..."
	python -m pcc_vizforge.cli random_walk --library matplotlib --export-type image
	python -m pcc_vizforge.cli random_walk --library plotly --export-type html
	python -m pcc_vizforge.cli dice --library matplotlib --export-type image
	python -m pcc_vizforge.cli dice --library plotly --export-type html
	python -m pcc_vizforge.cli weather --library matplotlib --export-type image
	python -m pcc_vizforge.cli weather --library plotly --export-type html
	python -m pcc_vizforge.cli quakes --library matplotlib --export-type image
	python -m pcc_vizforge.cli quakes --library plotly --export-type html
	python -m pcc_vizforge.cli github --library matplotlib --export-type image
	python -m pcc_vizforge.cli github --library plotly --export-type html
	@echo "✓ All visualizations generated"

demo:
	@echo "Running demo..."
	python -m pcc_vizforge.cli demo --library matplotlib
	@echo "✓ Demo complete"
