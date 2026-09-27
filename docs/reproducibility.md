# Reproducibility

PCC-VizForge treats reproducibility as a property that can be tested, not
just claimed. A dataset is fully determined by three inputs:

1. the **configuration**, stored with a SHA-256 hash;
2. an integer **seed**, which is always recorded (drawn from OS entropy and
   saved when you don't supply one);
3. the **code and dependency versions**, stored with the git commit and a
   dirty flag.

## Run directories

```bash
pcc-vizforge run quakes --seed 7 --set data_generation.b_value=0.8 --format png --format pdf
```

writes

```
runs/quakes-20260927-120000-3f2a9c1b7d4e/
├── config.yaml     # resolved config (overrides applied, seed filled in)
├── data.csv        # the simulated catalogue
├── metrics.json    # b-value, Mc, clustering, ...
├── figures/        # diagnostic figures (PNG/PDF/SVG)
└── manifest.json   # provenance record (below)
```

`manifest.json` records the run ID and UTC timestamp, the domain and seed,
the full configuration and its hash, the Python version and platform, the
versions of NumPy, SciPy, pandas, Matplotlib, Plotly and PyYAML, the git
commit (and whether the tree was dirty), and the SHA-256 of every output
file.

## Verification

```bash
pcc-vizforge verify runs/quakes-20260927-120000-3f2a9c1b7d4e
# quakes run 3f2a9c1b7d4e (seed 7): REPRODUCED
```

`verify` rebuilds the generator from the manifest alone, regenerates the
data, and compares its SHA-256 with the recorded one. It also re-hashes every
stored file and reports any that changed after the run. The command exits
non-zero on a mismatch, so it can gate CI. The CI workflow runs and verifies
every domain on every push.

## Design choices that make this work

- **No global RNG state.** Generators receive an explicit
  `numpy.random.Generator`. `np.random.seed` is never called, so results
  don't depend on import order or on other code running in the process.
- **Independent streams for replicates.** `generate_replicates` and the
  validation studies use `SeedSequence.spawn`, so replicate *i* is the same
  regardless of how many replicates you request or how they are scheduled.
- **No wall-clock dependence.** All dates are relative to configured
  `start_date` / `reference_date` values. The original GitHub generator used
  `datetime.now()`.
- **Validated, typed parameters.** Configuration is parsed into frozen
  dataclasses, and unknown keys are rejected, so a typo such as
  `n_step: 500` fails loudly instead of being silently ignored.
- **Deterministic serialisation.** CSVs are written with `\n` line
  endings on every OS, and config hashes use canonical JSON (sorted keys).

## Scope of the guarantee

Within one platform and set of dependency versions, regeneration is
**bit-identical**. PCG64 streams are platform-independent, but
transcendental functions such as `exp` and `log` can differ in the last ulp
between math libraries and CPU architectures. Across platforms, results
should therefore be compared numerically (e.g. `np.allclose`) rather than by
hash. The manifest records the environment so that such differences can be
diagnosed.
