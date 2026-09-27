# Methods

This document specifies every stochastic model and estimator implemented in
PCC-VizForge. Each section names the module that implements it and the
tests that check it against theory. Citation keys refer to
[`references.bib`](references.bib).

- [Conventions](#conventions)
- [Random walks and anomalous diffusion](#1-random-walks-and-anomalous-diffusion)
- [Dice](#2-dice)
- [Earthquake catalogues](#3-earthquake-catalogues)
- [Daily weather](#4-daily-weather)
- [Repository popularity and heavy tails](#5-repository-popularity-and-heavy-tails)
- [General inference](#6-general-inference)

## Conventions

- **Randomness.** Every simulation draws from an explicit
  `numpy.random.Generator` (PCG64) built from one recorded integer seed.
  Independent replicates use `SeedSequence.spawn`, which gives
  non-overlapping, statistically independent streams [@oneill2014pcg].
  Nothing touches NumPy's global RNG state.
- **Uncertainty.** Unless stated otherwise, intervals are two-sided at 95 %.
  [`validation.md`](validation.md) reports the empirical coverage of every
  interval.
- **Units.** Time is in steps (walks) or days (quakes, weather). Magnitudes
  are moment magnitudes. Temperatures are in °C.

---

## 1. Random walks and anomalous diffusion

*Module:* `pcc_vizforge.generators.random_walk`, `pcc_vizforge.analysis.diffusion`
*Tests:* `tests/test_random_walk.py`

### 1.1 Models

A walk in $d \in \{1,2,3\}$ dimensions starts at the origin, and
$\mathbf r(t) = \sum_{s \le t} \Delta \mathbf r_s$. Each model is scaled so
that the single-step mean-squared displacement (MSD) is $a^2$, where $a$ is
`step_size`.

| `model` | Increments | Ensemble MSD $\langle \lvert \mathbf r(t)\rvert^2 \rangle$ |
|---|---|---|
| `lattice` | $\pm a$ along one uniformly chosen axis | $a^2 t$ |
| `gaussian` | $\Delta \mathbf r \sim \mathcal N(0, \tfrac{a^2}{d} I_d)$ | $a^2 t$ |
| `correlated` | $\mathbf v_t = \rho \mathbf v_{t-1} + \sqrt{1-\rho^2}\,\boldsymbol\xi_t$, stationary start | $a^2\!\left[t\frac{1+\rho}{1-\rho} - \frac{2\rho(1-\rho^t)}{(1-\rho)^2}\right]$ |
| `levy` | isotropic direction, length $L$ with $P(L>\ell)=(\ell/a)^{-\alpha}$, $0<\alpha\le 2$ | $\infty$ (heavy tail) |
| `fbm` | fractional Gaussian noise with Hurst $H$ | $a^2 t^{2H}$ |

**Fractional Brownian motion** is simulated *exactly* by circulant embedding
[@davies1987tests; @dietrich1997fast]. The autocovariance of unit fractional
Gaussian noise is

$$\gamma(k) = \tfrac12\left(|k+1|^{2H} - 2|k|^{2H} + |k-1|^{2H}\right).$$

Embedding $\gamma$ in a circulant matrix of size $2n$ with eigenvalues
$\lambda_j = \mathrm{FFT}(c)_j \ge 0$, and drawing complex Gaussian
$Z_j$, the real part of $\mathrm{FFT}\big(\sqrt{\lambda_j/2n}\,Z_j\big)$ has
exactly the covariance $\gamma$. This costs $O(n\log n)$ with no
approximation error, unlike the Cholesky ($O(n^3)$) or Riemann-sum methods.

### 1.2 Estimators

**Ensemble MSD** $\hat M(t) = N^{-1}\sum_i |\mathbf r_i(t)|^2$ with standard
error across walks.

**Time-averaged MSD** of one walk of length $T$ at lag $\Delta$:

$$\overline{\delta^2}(\Delta) = \frac{1}{T-\Delta+1}\sum_{t=0}^{T-\Delta}|\mathbf r(t+\Delta)-\mathbf r(t)|^2.$$

The **ergodicity-breaking parameter**
$\mathrm{EB}(\Delta) = \mathrm{Var}[\overline{\delta^2}]/\langle\overline{\delta^2}\rangle^2$
tends to zero for ergodic processes; for Brownian motion
$\mathrm{EB}(\Delta) \approx 4\Delta/3T$ [@metzler2014anomalous], which the
tests verify.

**Anomalous exponent.** $\alpha$ in $M(t) \propto t^\alpha$ is estimated by
least squares on $\log \hat M$ vs. $\log t$ over log-spaced lags. MSD values at
neighbouring lags are strongly correlated, so the textbook regression CI is
far too narrow (in one diagnostic run it excluded the true value, 0.700, as
[0.693, 0.698]). `bootstrap_msd_exponent` therefore resamples **walks** (the
independent unit) and refits, reporting percentile intervals; its empirical
coverage is 92-94 %.

**Detrended fluctuation analysis** [@peng1994mosaic]. For an increment series
with profile $Y_k = \sum_{j\le k}(x_j - \bar x)$, split into windows of size
$s$, remove a local polynomial fit and compute the RMS residual $F(s)$. For
fractional Gaussian noise, $F(s) \propto s^H$.

**First-passage time** to radius $L$: the first $t$ with
$|\mathbf r(t)| \ge L$ (NaN if never reached).

---

## 2. Dice

*Module:* `pcc_vizforge.generators.dice`, `pcc_vizforge.analysis.probability`
*Tests:* `tests/test_dice.py`

$n$ i.i.d. dice with $s$ faces and face probabilities $p_1,\dots,p_s$ (fair
unless `weights` is given). The exact PMF of the sum is the $n$-fold
convolution of $(p_1,\dots,p_s)$, i.e. the coefficients of $G(z)^n$ with
$G(z)=\sum_f p_f z^f$. It is computed by exponentiation by squaring
($O(\log n)$ convolutions). This replaces the original recursive enumeration,
which was exponential in $n$. For fair dice, `sum_counts_fair` gives the exact
integer counts in arbitrary precision; the tests check both against
brute-force enumeration and rational arithmetic.

**Goodness of fit** is Pearson's $\chi^2$, with adjacent cells pooled until
every expected count is at least 5 [@cochran1954some]. Cramér's $V$ is
reported as an effect size. **Independence** is checked with the
Wald-Wolfowitz runs test [@wald1940test]. `fairness_test` tests
$H_0{:}\ p_f = 1/s$ whatever `weights` the dice were simulated with.

---

## 3. Earthquake catalogues

*Module:* `pcc_vizforge.generators.quakes`, `pcc_vizforge.analysis.seismology`
*Tests:* `tests/test_quakes.py`

### 3.1 Model

**Magnitudes** follow the doubly truncated Gutenberg-Richter law
[@gutenberg1944frequency] on $[M_c, M_{\max}]$:

$$f(m) = \frac{\beta e^{-\beta(m-M_c)}}{1-e^{-\beta(M_{\max}-M_c)}},\qquad \beta = b\ln 10,$$

sampled by inversion. The original generator used $\mathrm{Exp}(\text{scale}=1.5)$,
which implies $b \approx 0.29$. Tectonic catalogues have $b \approx 1$.

**Background epicentres** are a mixture of Gaussian "hotspots" and a
component that is uniform *on the sphere*
($\phi = \arcsin U$, $U\sim\mathcal U(\sin\phi_{\min},\sin\phi_{\max})$).
Drawing latitude uniformly, as the original code did, over-populates the
poles. Background origin times are a homogeneous Poisson process.

**Aftershocks** follow the branching structure of the ETAS model
[@ogata1988statistical]. An event of magnitude $m$ triggers
$\mathrm{Poisson}\big(K\,10^{\alpha(m-M_c)}\big)$ direct aftershocks. Their
delays follow the Omori-Utsu density $\propto (t+c)^{-p}$ [@utsu1995centenary],
their magnitudes are drawn from the same G-R law, and their epicentres are
displaced isotropically with scale $d_0\,10^{0.5(m-M_c)}$ km. The expected
number of direct offspring per event (the branching ratio) is

$$n = K\,\frac{\beta}{\beta-a}\,\frac{1-e^{-(\beta-a)(M_{\max}-M_c)}}{1-e^{-\beta(M_{\max}-M_c)}},\qquad a=\alpha\ln 10.$$

Configurations with $n \ge 1$ are supercritical, so the cascade can grow
without bound; they are rejected at validation [@helmstetter2002subcritical].
For a subcritical cascade the total catalogue size is $N_0/(1-n)$, which the
tests confirm.

Radiated energy uses $\log_{10}E = 1.5M + 4.8$ (J), and seismic moment uses
$M_0 = 10^{1.5M + 9.1}$ N·m [@hanks1979moment].

### 3.2 Estimators

| Quantity | Estimator | Reference |
|---|---|---|
| $b$ | $\hat b = \log_{10}e \,/\, [\bar M - (M_c - \Delta M/2)]$ | @aki1965maximum; @utsu1966statistical |
| SE($\hat b$) | $2.30\,\hat b^2\sqrt{\sum(M_i-\bar M)^2/n(n-1)}$ | @shi1982standard |
| $b$ (truncated) | root of the score equation $1/\beta - \bar x - L e^{-\beta L}/(1-e^{-\beta L}) = 0$ | @page1968aftershocks |
| $M_c$ | maximum curvature + 0.2 | @wiemer2000minimum; @woessner2005assessing |
| $(c,p)$ | MLE of Omori-Utsu on $[0,T]$ (profile likelihood, Nelder-Mead) | @ogata1983estimation |
| clustering | CV of inter-event times (1 for Poisson) | — |

The Aki estimator is biased upward by the factor $n/(n-1)$.
`unbiased=True` removes this bias. The validation study finds exactly the
predicted +2.0 % at $n=50$. The Aki estimator is also biased when
$M_{\max}-M_c$ is small; the Page estimator corrects this, and the tests
demonstrate both effects.

---

## 4. Daily weather

*Module:* `pcc_vizforge.generators.weather`, `pcc_vizforge.analysis.timeseries`
*Tests:* `tests/test_weather.py`

This is a WGEN-type generator [@richardson1981stochastic].

- **Occurrence:** a two-state Markov chain with $p_{01}=P(\text{wet}\mid\text{dry})$
  and $p_{11}=P(\text{wet}\mid\text{wet})$. The stationary wet probability is
  $\pi = p_{01}/(1-p_{11}+p_{01})$, the mean wet spell is $1/(1-p_{11})$ and
  the mean dry spell is $1/p_{01}$.
- **Amounts:** Gamma(shape $k$, mean $\mu$) on wet days.
- **Temperature:**
  $T_t = \bar T + A\sin\!\big(2\pi(d_t-\phi)/365.25\big) + \tau t/3652.5 + \delta\,\mathbb 1[\text{wet}_t] + \varepsilon_t$,
  where $\varepsilon_t$ is a stationary AR(1) process with standard deviation
  $\sigma$ and lag-1 correlation $\phi_T$, and $\tau$ is the trend in
  °C per decade. The diurnal range is narrower on wet days.
- **Humidity:** the dew point is $T_{\min}$ minus a Gamma-distributed
  depression, and relative humidity follows from the Magnus formula
  [@alduchov1996improved]. The heat index uses the NWS Rothfusz regression
  with its humidity adjustments [@rothfusz1990heat].

### 4.1 Estimators

**Harmonic regression**
$y_t = \mu + \beta t + \sum_k [a_k\cos(2\pi kt/P) + b_k\sin(2\pi kt/P)]$ by
OLS. Daily anomalies are autocorrelated, so the OLS standard error of
$\beta$ is too small: its 95 % coverage falls to 31 % when $\phi_T = 0.9$.
Newey-West HAC standard errors [@newey1987simple] with the Andrews (1991)
AR(1) plug-in bandwidth [@andrews1991heteroskedasticity] restore most of the
coverage (86-93 %).

**Mann-Kendall** tests for a monotonic trend [@mann1945nonparametric;
@kendall1975rank], with a tie-corrected variance and a Theil-Sen slope and CI
[@sen1968estimates]. Two corrections for serial correlation are offered:
von Storch pre-whitening [@vonstorch1995misuses] and the Hamed-Rao variance
inflation [@hamed1998modified]. Trend-free pre-whitening is deliberately
omitted. In our tests it rejected a true null 43 % of the time at
$\alpha = 0.05$, consistent with @bayazit2007prewhiten. `WeatherGenerator.calculate_statistics` tests
annual-mean anomalies when three or more full years are available, and
otherwise monthly means with the Hamed-Rao correction.

---

## 5. Repository popularity and heavy tails

*Module:* `pcc_vizforge.generators.github`, `pcc_vizforge.analysis.heavy_tails`
*Tests:* `tests/test_github.py`

Each repository has a latent popularity $\pi \sim \mathrm{Pareto}(\alpha)$
(pdf exponent $\alpha$) and an age $a$. Star counts are
$\mathrm{Poisson}\big(s\,\pi\,(a/365)^{\gamma}\big)$. Mixing a Poisson over a
Pareto rate preserves the tail, so stars have a power-law tail with exponent
$\alpha$. Forks are $\mathrm{Poisson}(\rho\cdot\text{stars})$ with a
per-repository $\rho \sim \mathrm{Beta}$. Commits are negative binomial. All
dates are relative to a fixed `reference_date`. The original generator called
`datetime.now()`, so its output was not reproducible.

**Power-law inference** follows @clauset2009power:

1. For each candidate $x_{\min}$, fit $\alpha$ by maximum likelihood.
   Continuous: $\hat\alpha = 1 + n/\sum\ln(x_i/x_{\min})$. Discrete: maximise
   $-n\ln\zeta(\alpha,x_{\min}) - \alpha\sum\ln x_i$ (Hurwitz zeta).
2. Choose the $x_{\min}$ that minimises the Kolmogorov-Smirnov distance.
3. Compute the standard error from the Fisher information. For discrete data
   this is $\big[n\,\partial^2_\alpha \ln\zeta(\alpha,x_{\min})\big]^{-1/2}$;
   using the continuous formula $(\alpha-1)/\sqrt n$ instead under-covers
   (87.6 % at $\alpha=3$).
4. Compute a goodness-of-fit $p$-value with the semi-parametric bootstrap,
   re-running the full fit on each synthetic dataset.
5. Compare against lognormal and exponential alternatives with Vuong's
   normalised likelihood-ratio test [@vuong1989likelihood]. For integer data
   the alternatives are discretised (half-integer-binned lognormal, geometric)
   so that the likelihoods are comparable probability mass functions.

The Hill estimator [@hill1975simple] and the Gini coefficient are also
provided.

---

## 6. General inference

*Module:* `pcc_vizforge.analysis.inference` · *Tests:* `tests/test_inference.py`

- Pearson $\chi^2$ GOF with Cochran pooling; type-I error verified by Monte
  Carlo.
- Wald-Wolfowitz runs test [@wald1940test].
- Sample ACF computed by FFT (biased, positive semi-definite); Ljung-Box
  portmanteau test [@ljung1978measure].
- Nonparametric bootstrap CIs (BCa by default) [@efron1987better].
- Multiple-testing adjustment: Bonferroni, Holm [@holm1979simple] and
  Benjamini-Hochberg [@benjamini1995controlling].
