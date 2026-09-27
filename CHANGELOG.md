# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — 0.2.0

This release turns the toolkit into a research-grade package. Most generators
were rewritten, because the originals produced statistically incorrect or
irreproducible data (details below).

### Breaking

- The import package is now `pcc_vizforge` (`src/pcc_vizforge`); it was `src`.
- Python ≥ 3.10 is required. `kaleido` moved to the `export` extra.
- `generate()` no longer writes files unless you pass `save_to_file=True`.
- Unknown configuration keys raise `InvalidConfigurationError`.
- Generator output schemas were extended. Legacy random-walk column names
  (`step_size`, `cumulative_distance`) remain as aliases.
- The CLI defaults to `WARNING` logs on stderr, and file logging is opt-in.

### Added

- **Reproducibility core:** explicit PCG64 generators, `SeedSequence`
  streams, and `RunManifest` provenance (config hash, versions, git commit,
  output SHA-256).
- **Experiment pipeline:** `pcc-vizforge run` / `verify`, plus Monte Carlo
  validation studies via `pcc-vizforge validate`.
- **`analysis` package:** `inference`, `diffusion`, `probability`,
  `seismology`, `timeseries`, `heavy_tails` (see `docs/methods.md`).
- **Random walks:** Gaussian, persistent, Lévy and exact fractional Brownian
  motion models; bootstrap anomalous-exponent inference; DFA; ergodicity
  breaking.
- **Earthquakes:** configurable b-value, sphere-uniform epicentres, ETAS
  aftershocks with a branching-ratio check, and Aki/Page/M<sub>c</sub>/Omori
  estimators.
- **Weather:** WGEN-type generator, Newey–West trend SEs, and Mann–Kendall
  with Hamed–Rao / pre-whitening.
- **GitHub:** heavy-tailed popularity model; Clauset–Shalizi–Newman
  power-law fitting with bootstrap GOF and Vuong tests.
- Publication plotting style (CVD-validated palette, embedded fonts) and
  diagnostic figures.
- CI on Python 3.10–3.13 across Linux, macOS and Windows; end-to-end
  reproducibility job; wheel smoke test; mypy; ruff; Dependabot.
- `docs/` (methods, validation, reproducibility, references), `CITATION.cff`.

### Fixed

- **Earthquakes:** magnitudes implied b ≈ 0.29 instead of ≈ 1; latitude was
  sampled uniformly, over-weighting the poles.
- **GitHub:** `datetime.now()` made output irreproducible; Pareto(0.5) star
  counts (infinite mean) were clipped, destroying the tail.
- **Dice:** exponential-time sum enumeration; no p-values.
- **Weather:** i.i.d. daily noise with a 15 °C SD; toy heat index.
- **Random walks:** the `step_size` column was actually the change in radial
  distance; walks were built with a Python loop per row.
- Several confidence intervals under-covered and were corrected:
  - regression CIs for MSD exponents;
  - OLS trend SEs under autocorrelation;
  - continuous-formula SEs for discrete power laws.
- **Plotting:**
  - Plotly `Scattermapbox` (removed in Plotly 6) and the Matplotlib
    `boxplot(labels=...)` API broke dashboards;
  - the weather dashboards used dual y-axes;
  - rainbow colormaps were replaced.
- **CLI:** the `version` command used the deprecated `pkg_resources`, and the
  Makefile targets called non-existent commands.

### Removed

- The obsolete scaffolding script `setup_pcc_vizforge.sh` and generated
  status documents in `doc/`.

## [0.1.0]

- Initial release: five synthetic-data generators with Matplotlib and Plotly
  dashboards.
