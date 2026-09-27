"""Tests for RNG management, provenance manifests and config composition."""

from __future__ import annotations

import json

import numpy as np
import pytest

from pcc_vizforge.exceptions import InvalidConfigurationError, InvalidParameterError
from pcc_vizforge.provenance import (
    RunManifest,
    canonical_json,
    collect_environment,
    config_hash,
    file_sha256,
)
from pcc_vizforge.rng import make_rng, resolve_seed, spawn_rngs, spawn_seeds
from pcc_vizforge.utils.config import apply_overrides, deep_merge, parse_override
from pcc_vizforge.utils.io import load_config


class TestRng:
    def test_same_seed_same_stream(self):
        a = make_rng(123).standard_normal(100)
        b = make_rng(123).standard_normal(100)
        np.testing.assert_array_equal(a, b)

    def test_different_seed_different_stream(self):
        assert not np.array_equal(make_rng(1).random(10), make_rng(2).random(10))

    def test_generator_passthrough(self):
        g = np.random.default_rng(0)
        assert make_rng(g) is g

    def test_does_not_touch_global_state(self):
        np.random.seed(7)
        expected = np.random.random()
        np.random.seed(7)
        make_rng(99).random(1000)
        assert np.random.random() == expected

    def test_resolve_seed_none_draws_entropy(self):
        s1, s2 = resolve_seed(None), resolve_seed(None)
        assert isinstance(s1, int) and s1 >= 0
        assert s1 != s2

    @pytest.mark.parametrize("bad", [-1, 1.5, "3", True])
    def test_resolve_seed_rejects_invalid(self, bad):
        with pytest.raises(InvalidParameterError):
            resolve_seed(bad)

    def test_spawned_streams_are_reproducible_and_distinct(self):
        r1 = [g.random(5) for g in spawn_rngs(42, 4)]
        r2 = [g.random(5) for g in spawn_rngs(42, 4)]
        for x, y in zip(r1, r2):
            np.testing.assert_array_equal(x, y)
        assert len({tuple(x) for x in r1}) == 4

    def test_spawned_streams_are_uncorrelated(self):
        a, b = (g.standard_normal(20_000) for g in spawn_rngs(0, 2))
        # |r| should be O(1/sqrt(n)) ~ 0.007
        assert abs(np.corrcoef(a, b)[0, 1]) < 0.03

    def test_spawn_seeds_count(self):
        assert len(spawn_seeds(1, 0)) == 0
        with pytest.raises(InvalidParameterError):
            spawn_seeds(1, -1)


class TestProvenance:
    def test_config_hash_is_order_independent(self):
        assert config_hash({"a": 1, "b": [1, 2]}) == config_hash({"b": [1, 2], "a": 1})
        assert config_hash({"a": 1}) != config_hash({"a": 2})

    def test_canonical_json_handles_numpy(self):
        assert canonical_json({"x": np.int64(3), "y": np.arange(2)}) == '{"x":3,"y":[0,1]}'

    def test_environment_snapshot(self):
        env = collect_environment()
        assert env["packages"]["numpy"] == np.__version__
        assert "python" in env and "platform" in env

    def test_manifest_roundtrip(self, tmp_path):
        out = tmp_path / "data.csv"
        out.write_text("a,b\n1,2\n")
        m = RunManifest(domain="dice", seed=5, config={"k": 1})
        m.register_output(out, root=tmp_path)
        m.metrics["chi2"] = 1.23
        path = m.write(tmp_path / "manifest.json")

        raw = json.loads(path.read_text())
        assert raw["outputs"]["data.csv"] == file_sha256(out)
        assert raw["config_sha256"] == config_hash({"k": 1})

        m2 = RunManifest.read(path)
        assert m2.seed == 5 and m2.metrics == {"chi2": 1.23}
        assert m2.config_sha256 == m.config_sha256


class TestConfigComposition:
    def test_deep_merge(self):
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        merged = deep_merge(base, {"a": {"c": 20}, "e": 5})
        assert merged == {"a": {"b": 1, "c": 20}, "d": 3, "e": 5}
        assert base["a"]["c"] == 2  # input not mutated

    @pytest.mark.parametrize(
        ("expr", "path", "value"),
        [
            ("a.b=3", ["a", "b"], 3),
            ("x=0.5", ["x"], 0.5),
            ("flag=true", ["flag"], True),
            ("lst=[1, 2]", ["lst"], [1, 2]),
            ("name=hello", ["name"], "hello"),
        ],
    )
    def test_parse_override(self, expr, path, value):
        assert parse_override(expr) == (path, value)

    @pytest.mark.parametrize("bad", ["novalue", "=3", "a=[1,"])
    def test_parse_override_rejects(self, bad):
        with pytest.raises(InvalidConfigurationError):
            parse_override(bad)

    def test_apply_overrides(self):
        cfg = {"data_generation": {"n": 1}}
        out = apply_overrides(cfg, ["data_generation.n=10", "data_generation.new.k=x"])
        assert out == {"data_generation": {"n": 10, "new": {"k": "x"}}}
        assert cfg == {"data_generation": {"n": 1}}

    def test_apply_override_through_scalar_fails(self):
        with pytest.raises(InvalidConfigurationError):
            apply_overrides({"a": 1}, ["a.b=2"])

    def test_load_config_from_path(self, tmp_path):
        p = tmp_path / "custom.yaml"
        p.write_text("data_generation:\n  n: 4\n")
        assert load_config(p) == {"data_generation": {"n": 4}}

    def test_load_config_non_mapping(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text("- 1\n- 2\n")
        with pytest.raises(InvalidConfigurationError):
            load_config(p)
