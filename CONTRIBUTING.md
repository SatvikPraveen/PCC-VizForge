# Contributing to PCC-VizForge

Thanks for your interest in improving PCC-VizForge! This guide covers the
development setup, the standards every change must meet, and how to add new
models and estimators.

## Setup

```bash
git clone https://github.com/SatvikPraveen/PCC-VizForge.git
cd PCC-VizForge
python -m venv .venv && source .venv/bin/activate
make install-dev      # editable install with [dev] extras + pre-commit hooks
make check            # ruff, mypy and the full test suite
```

## Workflow

1. Branch from `main` (`feat/...`, `fix/...`, `docs/...`).
2. Make focused commits using [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat(quakes): ...`, `fix(analysis): ...`, `test: ...`, `docs: ...`).
3. Run `make check` locally; CI runs the same checks on Python 3.10–3.13
   across Linux, macOS and Windows, plus an end-to-end reproducibility job.
4. Open a pull request that explains **what** changed and **why**, and call
   out any change to generated data, which breaks bit-for-bit reproducibility
   of existing runs.

## Standards

| Area | Rule |
|---|---|
| Formatting / lint | `ruff format` and `ruff check` (config in `pyproject.toml`) |
| Types | complete annotations; `mypy` must pass |
| Docstrings | Google style, with references for any published method |
| Errors | raise subclasses of `PccVizForgeError` (`pcc_vizforge.exceptions`) and chain causes (`raise ... from exc`) |
| Logging | `logging.getLogger(__name__)`; the library never configures handlers |
| Coverage | CI fails below 85 % (line + branch) |

### Research-code rules

These rules protect the package's core guarantees:

- **Never use global randomness.** All randomness must come from the
  `numpy.random.Generator` passed to `_simulate`, or from
  `pcc_vizforge.rng.make_rng(seed)`. `np.random.seed`, `np.random.rand` and
  friends are banned (ruff rule `NPY002`).
- **Never read the wall clock** in a generator. Use a configured
  `start_date` / `reference_date` instead.
- **Validate parameters** in a frozen `GeneratorParams` dataclass. Unknown
  config keys must fail loudly.
- **Test against theory, not just shapes.** Every new model needs at least
  one statistical test comparing simulated output with a closed form or a
  known property (a KS test, moments, z-scores against a formula, etc.).
  Mark Monte Carlo tests that take more than about a second with
  `@pytest.mark.slow`, and use `pytest.mark.statistical` where appropriate.
- **Report honest uncertainty.** Any estimator that returns a confidence
  interval must have its coverage checked, either in a slow test or in a
  study in `experiments/validation.py`, with results added to
  `docs/validation.md`.
- **Cite methods** in the module docstring and add the BibTeX entry to
  `docs/references.bib`.

## Adding a new generator

1. Create `src/pcc_vizforge/generators/<name>.py` with a `GeneratorParams`
   subclass (typed fields plus `validate()`) and a `BaseGenerator` subclass
   that implements `_simulate(params, rng) -> pd.DataFrame`.
2. Add `src/pcc_vizforge/configs/<name>.yaml` with `data_generation`,
   `visualization` and `export` sections.
3. Export it from `generators/__init__.py`, and register it in
   `experiments/runner.py` (`DOMAINS`, `ANALYZERS`, `_figures`) and in
   `cli.py` (`DOMAIN_NAMES`, `DASHBOARD_CLASSES`).
4. Add estimators to `analysis/`, figures to `plots/diagnostics.py`, and
   tests in `tests/test_<name>.py`.
5. Document the model in `docs/methods.md`.

## Adding an estimator or test

Put it in the relevant `analysis/` module. Return a `TestResult`,
`ConfidenceInterval` or a frozen dataclass with `to_dict()`. Validate it
against known values (hand computation, SciPy, or brute force) and by
simulation.

## Running tests

```bash
pytest                          # everything (about 20 s)
pytest -m "not slow"            # quick loop
pytest tests/test_quakes.py -k b_value
make coverage                   # HTML report in htmlcov/
```

## Reporting issues

Please include the Python version, OS, PCC-VizForge version, a minimal
reproducible example (ideally a `pcc-vizforge run ...` command with its
seed, or the run's `manifest.json`), and the expected vs. actual behaviour.
