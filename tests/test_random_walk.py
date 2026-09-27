"""Statistical and structural tests for random-walk models and diffusion analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pcc_vizforge.analysis.diffusion import (
    bootstrap_msd_exponent,
    dfa,
    ensemble_msd,
    ergodicity_breaking_parameter,
    first_passage_times,
    fit_msd_exponent,
    log_spaced_lags,
    time_averaged_msd,
)
from pcc_vizforge.exceptions import InvalidConfigurationError, InvalidParameterError
from pcc_vizforge.generators.random_walk import (
    WALK_MODELS,
    RandomWalkGenerator,
    RandomWalkParams,
    fractional_gaussian_noise,
    frame_to_positions,
    positions_to_frame,
    simulate_increments,
    theoretical_msd,
)
from pcc_vizforge.rng import make_rng


def _positions(**kw):
    p = RandomWalkParams(**kw)
    return p, np.cumsum(
        simulate_increments(p, make_rng(kw.get("random_seed", 0))), axis=1
    )


class TestParams:
    @pytest.mark.parametrize(
        "bad",
        [
            {"n_steps": 0},
            {"dimensions": 4},
            {"step_size": 0},
            {"model": "brownian"},
            {"hurst": 1.0},
            {"levy_alpha": 2.5},
            {"persistence": 1.0},
            {"n_walks": 2.5},
        ],
    )
    def test_invalid(self, bad):
        with pytest.raises(InvalidParameterError):
            RandomWalkParams(**bad).validate()

    def test_unknown_key_rejected(self):
        with pytest.raises(InvalidConfigurationError):
            RandomWalkGenerator(n_step=10)

    def test_direct_kwargs_and_overrides(self):
        g = RandomWalkGenerator(n_steps=7, overrides=["data_generation.n_walks=3"])
        df = g.generate()
        assert df["walk_id"].nunique() == 3 and df["step"].max() == 7


class TestStructure:
    @pytest.mark.parametrize("model", WALK_MODELS)
    @pytest.mark.parametrize("d", [1, 2, 3])
    def test_shapes_and_columns(self, model, d):
        df = RandomWalkGenerator(
            n_steps=20, n_walks=3, dimensions=d, model=model
        ).generate()
        assert len(df) == 60
        assert (df["y_position"] == 0).all() if d == 1 else True
        assert ("z_position" in df) == (d == 3)
        assert np.all(np.isfinite(df.select_dtypes("number")))
        assert (df.groupby("walk_id")["path_length"].diff().dropna() >= 0).all()

    def test_lattice_steps_are_unit_axis_moves(self):
        _, pos = _positions(
            n_steps=200, n_walks=10, dimensions=3, model="lattice", step_size=2.0
        )
        inc = np.diff(pos, axis=1, prepend=0)
        assert np.all(np.count_nonzero(inc, axis=-1) == 1)
        assert np.allclose(np.abs(inc).sum(-1), 2.0)

    def test_levy_step_lengths_bounded_below(self):
        _, pos = _positions(
            n_steps=500, n_walks=5, dimensions=2, model="levy", step_size=0.5
        )
        lengths = np.linalg.norm(np.diff(pos, axis=1, prepend=0), axis=-1)
        assert lengths.min() >= 0.5 - 1e-12

    def test_frame_roundtrip(self):
        for d in (1, 2, 3):
            _, pos = _positions(n_steps=15, n_walks=4, dimensions=d, model="gaussian")
            np.testing.assert_allclose(frame_to_positions(positions_to_frame(pos)), pos)

    def test_reproducible_and_seed_sensitive(self):
        g = RandomWalkGenerator(n_steps=50, n_walks=2, model="fbm", hurst=0.7)
        pd.testing.assert_frame_equal(g.generate(seed=1), g.generate(seed=1))
        assert not g.generate(seed=1).equals(g.generate(seed=2))
        assert g.generate(seed=5).attrs["provenance"]["seed"] == 5

    def test_replicates_independent(self):
        reps = RandomWalkGenerator(n_steps=30, n_walks=1).generate_replicates(3, seed=9)
        assert len(reps) == 3
        assert not reps[0]["x_position"].equals(reps[1]["x_position"])
        assert [r.attrs["provenance"]["replicate"] for r in reps] == [0, 1, 2]

    @given(
        n=st.integers(1, 40),
        w=st.integers(1, 4),
        d=st.sampled_from([1, 2, 3]),
        model=st.sampled_from(WALK_MODELS),
    )
    @settings(max_examples=40, deadline=None)
    def test_property_consistency(self, n, w, d, model):
        df = RandomWalkGenerator(
            n_steps=n, n_walks=w, dimensions=d, model=model
        ).generate(seed=0)
        pos = frame_to_positions(df)
        np.testing.assert_allclose(
            np.linalg.norm(pos, axis=-1).ravel(), df["displacement"]
        )
        # triangle inequality: displacement never exceeds distance travelled
        assert np.all(df["displacement"] <= df["path_length"] + 1e-9)


@pytest.mark.statistical
class TestAgainstTheory:
    @pytest.mark.parametrize(
        "kw",
        [
            {"model": "lattice"},
            {"model": "gaussian"},
            {"model": "correlated", "persistence": 0.6},
            {"model": "correlated", "persistence": -0.5},
            {"model": "fbm", "hurst": 0.25},
            {"model": "fbm", "hurst": 0.75},
        ],
    )
    def test_ensemble_msd_matches_theory(self, kw):
        p, pos = _positions(
            n_steps=256, n_walks=3000, dimensions=2, step_size=1.5, **kw
        )
        msd, sem = ensemble_msd(pos)
        t = np.array([1, 16, 64, 256])
        theo = theoretical_msd(p, t)
        exact = sem[t - 1] == 0  # e.g. lattice MSD at t=1 is deterministic
        np.testing.assert_allclose(msd[t - 1][exact], theo[exact])
        z = (msd[t - 1][~exact] - theo[~exact]) / sem[t - 1][~exact]
        assert np.all(np.abs(z) < 4.5), z

    @pytest.mark.parametrize("hurst", [0.2, 0.5, 0.8])
    def test_fbm_exponent_recovered(self, hurst):
        _, pos = _positions(
            n_steps=1024, n_walks=500, dimensions=1, model="fbm", hurst=hurst
        )
        msd, sem = ensemble_msd(pos)
        t = np.arange(1, 1025)
        fit = fit_msd_exponent(t, msd, sigma=sem)
        assert fit.alpha == pytest.approx(2 * hurst, abs=0.04)

    @pytest.mark.slow
    def test_bootstrap_ci_covers_true_exponent(self):
        """Walk-level bootstrap CIs should have near-nominal coverage, unlike the
        naive regression CI which ignores correlation between lags."""
        from pcc_vizforge.rng import spawn_seeds

        hits_boot = hits_naive = 0
        n_rep = 60
        for i, ss in enumerate(spawn_seeds(3, n_rep)):
            p = RandomWalkParams(n_steps=400, n_walks=150, model="fbm", hurst=0.35)
            pos = np.cumsum(simulate_increments(p, make_rng(ss)), axis=1)
            boot = bootstrap_msd_exponent(pos, n_bootstrap=300, seed=i)
            hits_boot += boot.alpha_ci[0] <= 0.7 <= boot.alpha_ci[1]
            msd, sem = ensemble_msd(pos)
            naive = fit_msd_exponent(np.arange(1, 401), msd, sigma=sem)
            hits_naive += naive.alpha_ci[0] <= 0.7 <= naive.alpha_ci[1]
        assert hits_boot / n_rep >= 0.85
        assert hits_naive < hits_boot

    def test_bootstrap_reproducible(self):
        _, pos = _positions(n_steps=100, n_walks=20, model="gaussian")
        a = bootstrap_msd_exponent(pos, n_bootstrap=50, seed=1)
        assert a == bootstrap_msd_exponent(pos, n_bootstrap=50, seed=1)
        assert a.alpha_ci[0] < a.alpha < a.alpha_ci[1]
        with pytest.raises(InvalidParameterError):
            bootstrap_msd_exponent(pos[:1])

    def test_regime_classification(self):
        t = np.arange(1, 200)
        for alpha, regime in [
            (0.5, "subdiffusive"),
            (1.0, "normal"),
            (1.6, "superdiffusive"),
        ]:
            noise = np.exp(make_rng(1).normal(0, 0.01, t.size))
            assert fit_msd_exponent(t, 3 * t**alpha * noise).regime == regime

    def test_fit_exact_power_law(self):
        t = np.arange(1, 50)
        fit = fit_msd_exponent(t, 2.5 * t**0.7)
        assert fit.alpha == pytest.approx(0.7) and fit.prefactor == pytest.approx(2.5)
        assert fit.r_squared == pytest.approx(1.0)
        assert fit.diffusion_coefficient(2) == pytest.approx(2.5 / 4)

    def test_fgn_unit_variance_and_covariance(self):
        h = 0.7
        x = fractional_gaussian_noise(make_rng(3), 64, h, size=20_000)
        assert x.var() == pytest.approx(1.0, rel=0.02)
        rho1 = 0.5 * (2 ** (2 * h) - 2)
        assert np.mean(x[:, 1:] * x[:, :-1]) == pytest.approx(rho1, abs=0.02)

    @pytest.mark.parametrize("hurst", [0.3, 0.5, 0.75])
    def test_dfa_recovers_hurst(self, hurst):
        x = fractional_gaussian_noise(make_rng(8), 2**14, hurst)[0]
        fit, scales, F = dfa(x)
        assert fit.alpha == pytest.approx(hurst, abs=0.06)
        assert scales.size == F.size

    def test_brownian_is_ergodic_fbm_tamsd_consistent(self):
        _, pos = _positions(n_steps=2000, n_walks=200, dimensions=1, model="gaussian")
        lags, tamsd = time_averaged_msd(pos, [1, 10, 100])
        np.testing.assert_allclose(tamsd.mean(0), lags, rtol=0.05)
        eb = ergodicity_breaking_parameter(tamsd)
        # For Brownian motion EB(Δ) ≈ 4Δ/(3T) (Metzler et al. 2014)
        np.testing.assert_allclose(eb, 4 * lags / (3 * 2000), rtol=0.35)

    def test_first_passage_1d_scaling(self):
        _, pos = _positions(n_steps=4000, n_walks=2000, dimensions=1, model="lattice")
        fpt = first_passage_times(pos, 10)
        # Median FPT for SRW to |x|=L scales ~ L^2; certainly finite and >= L
        assert np.nanmin(fpt) >= 10
        assert np.nanmedian(fpt) == pytest.approx(10**2 * 0.9, rel=0.25)


class TestEstimatorValidation:
    def test_log_spaced_lags(self):
        lags = log_spaced_lags(1000, 20)
        assert lags[0] == 1 and lags[-1] == 999 and np.all(np.diff(lags) > 0)

    def test_errors(self):
        with pytest.raises(InvalidParameterError):
            fit_msd_exponent([1, 2], [1, 2])
        with pytest.raises(InvalidParameterError):
            fit_msd_exponent([1, 2, 3], [1, 2])
        with pytest.raises(InvalidParameterError):
            dfa(np.zeros(10))
        with pytest.raises(InvalidParameterError):
            time_averaged_msd(np.zeros((2, 5, 1)), [0])
        with pytest.raises(InvalidParameterError):
            first_passage_times(np.zeros((2, 5)), 0)
        with pytest.raises(InvalidParameterError):
            ensemble_msd(np.zeros(5))
        with pytest.raises(InvalidParameterError):
            ergodicity_breaking_parameter(np.ones((1, 3)))

    def test_first_passage_never(self):
        assert np.isnan(first_passage_times(np.zeros((1, 5, 1)), 1.0)).all()
