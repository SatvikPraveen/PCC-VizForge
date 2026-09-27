# PCC-VizForge developer tasks. Run `make help` for a summary.

PYTHON ?= python
SEED ?= 12345
DOMAINS := random_walk dice weather quakes github

.DEFAULT_GOAL := help
.PHONY: help install install-dev lint format typecheck test test-fast coverage check \
	runs verify validate notebooks build clean clean-outputs pre-commit

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the package
	$(PYTHON) -m pip install -e .

install-dev: ## Install with development extras and pre-commit hooks
	$(PYTHON) -m pip install -e ".[dev]"
	pre-commit install

lint: ## Ruff lint + format check
	ruff check src tests
	ruff format --check src tests

format: ## Auto-format and fix lint
	ruff format src tests
	ruff check --fix src tests

typecheck: ## mypy
	mypy

test: ## Full test suite (incl. statistical Monte Carlo tests)
	pytest

test-fast: ## Skip slow Monte Carlo tests
	pytest -m "not slow"

coverage: ## Tests with coverage report (fails under 85%)
	pytest --cov=pcc_vizforge --cov-report=term-missing --cov-report=html --cov-fail-under=85

check: lint typecheck test ## Everything CI runs

runs: ## Run every domain into runs/ with a fixed seed
	@for d in $(DOMAINS); do pcc-vizforge run $$d --seed $(SEED) --out runs --name $$d --format png --format pdf; done

verify: ## Verify every run in runs/ reproduces bit-for-bit
	@for d in runs/*/; do pcc-vizforge verify $$d || exit 1; done

validate: ## Monte Carlo validation of all estimators
	pcc-vizforge validate all --replicates 500 --out validation

notebooks: ## Execute all notebooks in place
	jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb

build: ## Build sdist and wheel
	$(PYTHON) -m build
	twine check --strict dist/*

pre-commit: ## Run pre-commit on all files
	pre-commit run --all-files

clean: ## Remove caches and build artefacts
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

clean-outputs: ## Remove generated data, exports, runs and validation results
	rm -rf data exports/images/*.* exports/html/*.* runs validation logs
