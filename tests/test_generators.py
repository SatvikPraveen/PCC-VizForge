"""Tests for data generators."""

import pandas as pd

from pcc_vizforge.generators import (
    DiceGenerator,
    EarthquakeGenerator,
    GitHubGenerator,
    RandomWalkGenerator,
    WeatherGenerator,
)


class TestRandomWalkGenerator:
    """Test random walk generator."""

    def test_generate_basic(self):
        generator = RandomWalkGenerator()
        data = generator.generate(save_to_file=False)

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert "walk_id" in data.columns
        assert "step" in data.columns
        assert "position" in data.columns

    def test_generate_with_config(self):
        generator = RandomWalkGenerator()
        data = generator.generate(save_to_file=False)

        # Check that config parameters are respected
        n_walks = generator.data_config["n_walks"]
        n_steps = generator.data_config["n_steps"]

        assert data["walk_id"].nunique() == n_walks
        assert len(data) == n_walks * n_steps


class TestDiceGenerator:
    """Test dice generator."""

    def test_generate_basic(self):
        generator = DiceGenerator()
        data = generator.generate(save_to_file=False)

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert "roll_id" in data.columns
        assert "die_value" in data.columns
        assert "roll_sum" in data.columns

    def test_dice_values_valid(self):
        generator = DiceGenerator()
        data = generator.generate(save_to_file=False)

        dice_sides = generator.data_config["dice_sides"]
        assert data["die_value"].min() >= 1
        assert data["die_value"].max() <= dice_sides


class TestWeatherGenerator:
    """Test weather generator."""

    def test_generate_basic(self):
        generator = WeatherGenerator()
        data = generator.generate(save_to_file=False)

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert "date" in data.columns
        assert "temperature_avg" in data.columns
        assert "humidity" in data.columns

    def test_weather_ranges(self):
        generator = WeatherGenerator()
        data = generator.generate(save_to_file=False)

        assert data["humidity"].min() >= 0
        assert data["humidity"].max() <= 100
        assert data["precipitation"].min() >= 0


class TestEarthquakeGenerator:
    """Test earthquake generator."""

    def test_generate_basic(self):
        generator = EarthquakeGenerator()
        data = generator.generate(save_to_file=False)

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert "magnitude" in data.columns
        assert "latitude" in data.columns
        assert "longitude" in data.columns


class TestGitHubGenerator:
    """Test GitHub generator."""

    def test_generate_basic(self):
        generator = GitHubGenerator()
        data = generator.generate(save_to_file=False)

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert "stars" in data.columns
        assert "forks" in data.columns
        assert "primary_language" in data.columns
