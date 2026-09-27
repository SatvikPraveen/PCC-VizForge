# Estimator validation

Every generator has known ground-truth parameters, so we can measure how well
each estimator recovers them. `pcc-vizforge validate` simulates independent
replicate datasets on RNG streams spawned from one root seed, then reports:

- **bias** = mean(estimate − truth), with its Monte Carlo standard error (MCSE);
- **RMSE**;
- **coverage** of the nominal 95 % confidence interval, with MCSE
  √(p(1−p)/R);
- for hypothesis tests, the **size**: the rejection rate at α = 0.05 when
  H₀ is true.

With R = 500 replicates the coverage MCSE is about 1 percentage point, so
coverage between 93 % and 97 % is consistent with the nominal 95 %.

Reproduce everything below with:

```bash
pcc-vizforge validate all --replicates 500 --seed 20240101 --out validation
```

The full per-replicate results are written to `validation/*_replicates.csv`.

## b-value (Aki-Utsu MLE)

True b = 1, continuous magnitudes above M<sub>c</sub> = 2.

| events | mean b̂ | bias (MCSE) | RMSE | 95 % coverage |
|---:|---:|---:|---:|---:|
| 50 | 1.021 | +0.021 (0.007) | 0.159 | 0.934 |
| 100 | 1.011 | +0.011 (0.005) | 0.110 | 0.926 |
| 250 | 1.004 | +0.004 (0.003) | 0.063 | 0.952 |
| 500 | 1.004 | +0.004 (0.002) | 0.044 | 0.950 |
| 1000 | 1.003 | +0.003 (0.001) | 0.032 | 0.946 |
| 2500 | 1.002 | +0.002 (0.001) | 0.021 | 0.934 |

The small-sample bias matches the theoretical factor n/(n−1) exactly
(50/49 = 1.0204). `b_value_mle(..., unbiased=True)` removes it. The
Shi-Bolt interval slightly under-covers for n ≤ 100.

## Anomalous-diffusion exponent (walk bootstrap)

Fractional Brownian motion, 100 walks × 256 steps, true α = 2H.

| H | true α | mean α̂ | bias (MCSE) | RMSE | 95 % coverage |
|---:|---:|---:|---:|---:|---:|
| 0.25 | 0.5 | 0.500 | −0.000 (0.002) | 0.035 | 0.922 |
| 0.50 | 1.0 | 1.002 | +0.002 (0.002) | 0.040 | 0.920 |
| 0.75 | 1.5 | 1.503 | +0.003 (0.002) | 0.042 | 0.942 |

The estimator is essentially unbiased. Percentile-bootstrap intervals cover
92-94 %, slightly below nominal, as is typical for 100 resampling units. The
naive regression interval, which treats lags as independent, covers far
less (see `tests/test_random_walk.py::test_bootstrap_ci_covers_true_exponent`).

## Discrete power law (CSN MLE)

n = 1000, x<sub>min</sub> = 1.

| true α | mean α̂ | bias (MCSE) | RMSE | 95 % coverage |
|---:|---:|---:|---:|---:|
| 1.8 | 1.802 | +0.002 (0.001) | 0.027 | 0.948 |
| 2.2 | 2.204 | +0.004 (0.002) | 0.041 | 0.956 |
| 2.6 | 2.605 | +0.005 (0.003) | 0.058 | 0.944 |
| 3.0 | 3.006 | +0.006 (0.003) | 0.078 | 0.956 |

An earlier version computed the standard error with the continuous formula
(α−1)/√n, and its coverage fell to 87.6 % at α = 3. The Fisher-information
standard error now used for discrete data fixes this (see
[`methods.md` §5](methods.md#5-repository-popularity-and-heavy-tails)).

## χ² goodness-of-fit test on dice sums (size)

500 rolls per replicate; H₀ is true.

| dice | rejection rate at 5 % (MCSE) | KS test of p ~ U(0,1) |
|---:|---:|---:|
| 1 | 0.062 (0.011) | 0.040 |
| 2 | 0.042 (0.009) | 0.931 |
| 3 | 0.048 (0.010) | 0.169 |
| 5 | 0.056 (0.010) | 0.513 |

The size is within about 1 MCSE of 5 % in every case. The low KS p-value for
a single die does not indicate miscalibration: with 6 cells, the multinomial
χ² statistic takes few distinct values, so its p-values are discrete and
cannot be exactly uniform.

## Trend standard errors under autocorrelation

Daily series: linear trend + annual harmonic + AR(1) noise with lag-1
correlation φ, n = 1500.

| φ | OLS coverage | Newey-West (Andrews bandwidth) coverage |
|---:|---:|---:|
| 0.0 | 0.936 | 0.932 |
| 0.4 | 0.780 | 0.920 |
| 0.7 | 0.556 | 0.904 |
| 0.9 | 0.312 | 0.860 |

Under strong persistence the OLS interval is badly anti-conservative. HAC
restores most of the coverage, but it remains below nominal as φ approaches 1.
This is a known finite-sample property of kernel HAC estimators. For
long daily records, `WeatherGenerator.calculate_statistics` therefore tests
the trend on annual means, which are close to independent.

## Other calibration checks in the test suite

These run in CI on every push.

| Check | Test |
|---|---|
| χ² GOF type-I error ≈ 5 % | `test_inference.py::test_type_one_error_is_calibrated` |
| BCa bootstrap coverage of a mean | `test_inference.py::test_coverage_is_near_nominal` |
| Every walk model's MSD matches its closed form (z-scores) | `test_random_walk.py::test_ensemble_msd_matches_theory` |
| DFA recovers H ∈ {0.3, 0.5, 0.75} | `test_random_walk.py::test_dfa_recovers_hurst` |
| Brownian EB(Δ) ≈ 4Δ/3T | `test_random_walk.py::test_brownian_is_ergodic_fbm_tamsd_consistent` |
| Shi-Bolt SE matches the replicate SD | `test_quakes.py::test_shi_bolt_se_is_calibrated` |
| ETAS catalogue size = N₀/(1−n) | `test_quakes.py::test_aftershock_fraction_matches_branching_ratio` |
| Background epicentres uniform on the sphere | `test_quakes.py::test_background_uniform_on_sphere` |
| Markov-chain and Gamma parameters recovered | `test_weather.py::test_recovers_markov_chain_and_gamma` |
| Mann-Kendall size under AR(1): plain vs corrected | `test_weather.py::test_prewhitening_controls_type_one_error` |
| Star-count tail exponent recovered | `test_github.py::test_star_tail_exponent_recovered` |
