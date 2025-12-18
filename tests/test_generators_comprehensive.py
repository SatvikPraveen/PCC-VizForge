"""Comprehensive tests for data generators and utilities."""

import logging
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from src.exceptions import (
    InvalidParameterError,
    DataGenerationError,
    DataShapeError,
)
from src.generators import (
    RandomWalkGenerator,
    DiceGenerator,
    WeatherGenerator,
    EarthquakeGenerator,
    GitHubGenerator,
)
from src.utils.io import (
    load_config,
    save_data,
    load_data,
    list_available_configs,
    get_data_directory,
)
from src.utils.validation import (
    validate_positive_int,
    validate_positive_float,
    validate_dimensions,
    validate_data_size,
)


# ==================== Fixture Definitions ====================


@pytest.fixture
def temp_data_dir(tmp_path):
    """Fixture to provide a temporary directory for data files."""
    return tmp_path / "data"


@pytest.fixture
def sample_dataframe():
    """Fixture providing a sample DataFrame."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "value": [10.5, 20.3, 15.8, 25.1, 30.4],
        "category": ["A", "B", "A", "C", "B"],
    })


# ==================== RandomWalkGenerator Tests ====================


class TestRandomWalkGenerator:
    """Test random walk generator."""

    def test_initialize_with_default_config(self):
        """Test initialization with default configuration."""
        generator = RandomWalkGenerator()
        assert generator.config is not None
        assert generator.data_config is not None
        assert "n_steps" in generator.data_config
        assert "n_walks" in generator.data_config

    def test_generate_basic(self):
        """Test basic data generation."""
        generator = RandomWalkGenerator()
        data = generator.generate(save_to_file=False)

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert "walk_id" in data.columns
        assert "step" in data.columns
        assert "position" in data.columns
        assert "cumulative_distance" in data.columns
        assert "step_size" in data.columns

    def test_generate_respects_config(self):
        """Test that generator respects configuration parameters."""
        generator = RandomWalkGenerator()
        data = generator.generate(save_to_file=False)

        n_walks = generator.data_config["n_walks"]
        n_steps = generator.data_config["n_steps"]

        assert data["walk_id"].nunique() == n_walks
        assert len(data) == n_walks * n_steps

    def test_generate_1d_walk(self):
        """Test 1D random walk generation."""
        generator = RandomWalkGenerator()
        generator.data_config["dimensions"] = 1
        data = generator.generate(save_to_file=False)

        assert "x_position" in data.columns
        assert "y_position" in data.columns
        assert (data["y_position"] == 0).all()

    def test_generate_2d_walk(self):
        """Test 2D random walk generation."""
        generator = RandomWalkGenerator()
        generator.data_config["dimensions"] = 2
        data = generator.generate(save_to_file=False)

        assert "x_position" in data.columns
        assert "y_position" in data.columns
        assert data["x_position"].abs().max() > 0
        assert data["y_position"].abs().max() > 0

    def test_generate_3d_walk(self):
        """Test 3D random walk generation."""
        generator = RandomWalkGenerator()
        generator.data_config["dimensions"] = 3
        data = generator.generate(save_to_file=False)

        assert "x_position" in data.columns
        assert "y_position" in data.columns
        assert "z_position" in data.columns

    def test_random_seed_reproducibility(self):
        """Test that random seed produces reproducible results."""
        generator1 = RandomWalkGenerator()
        generator1.data_config["random_seed"] = 42
        data1 = generator1.generate(save_to_file=False)

        generator2 = RandomWalkGenerator()
        generator2.data_config["random_seed"] = 42
        data2 = generator2.generate(save_to_file=False)

        pd.testing.assert_frame_equal(data1, data2)

    def test_calculate_statistics(self):
        """Test statistical calculation."""
        generator = RandomWalkGenerator()
        data = generator.generate(save_to_file=False)
        stats = generator.calculate_statistics(data)

        assert isinstance(stats, dict)
        assert "mean_final_position" in stats
        assert "std_final_position" in stats
        assert "mean_step_size" in stats
        assert "total_steps" in stats
        assert "n_walks" in stats
        assert stats["n_walks"] == data["walk_id"].nunique()

    def test_get_walk_summary(self):
        """Test individual walk summary."""
        generator = RandomWalkGenerator()
        data = generator.generate(save_to_file=False)
        summary = generator.get_walk_summary(data, walk_id=0)

        assert isinstance(summary, dict)
        assert summary["walk_id"] == 0
        assert "n_steps" in summary
        assert "final_position" in summary
        assert "total_distance" in summary

    def test_get_walk_summary_invalid_id(self):
        """Test get_walk_summary with invalid walk_id."""
        generator = RandomWalkGenerator()
        data = generator.generate(save_to_file=False)

        with pytest.raises(InvalidParameterError):
            generator.get_walk_summary(data, walk_id=9999)

    def test_generate_multiple_scenarios(self):
        """Test generating multiple scenarios."""
        generator = RandomWalkGenerator()
        scenarios = [
            {"name": "short", "n_steps": 50, "n_walks": 2},
            {"name": "long", "n_steps": 200, "n_walks": 3},
        ]
        results = generator.generate_multiple_scenarios(scenarios, save_to_file=False)

        assert len(results) == 2
        assert "short" in results
        assert "long" in results
        assert len(results["short"]) == 50 * 2
        assert len(results["long"]) == 200 * 3


# ==================== DiceGenerator Tests ====================


class TestDiceGenerator:
    """Test dice generator."""

    def test_generate_basic(self):
        """Test basic dice generation."""
        generator = DiceGenerator()
        data = generator.generate(save_to_file=False)

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert "roll_id" in data.columns
        assert "die_value" in data.columns
        assert "roll_sum" in data.columns

    def test_dice_values_valid(self):
        """Test that dice values are within valid range."""
        generator = DiceGenerator()
        data = generator.generate(save_to_file=False)

        dice_sides = generator.data_config["dice_sides"]
        assert data["die_value"].min() >= 1
        assert data["die_value"].max() <= dice_sides

    def test_dice_roll_sum(self):
        """Test that roll sum is correct."""
        generator = DiceGenerator()
        data = generator.generate(save_to_file=False)

        for roll_id in data["roll_id"].unique():
            roll_data = data[data["roll_id"] == roll_id]
            expected_sum = roll_data["die_value"].sum()
            actual_sum = roll_data["roll_sum"].iloc[0]
            assert expected_sum == actual_sum


# ==================== WeatherGenerator Tests ====================


class TestWeatherGenerator:
    """Test weather generator."""

    def test_generate_basic(self):
        """Test basic weather generation."""
        generator = WeatherGenerator()
        data = generator.generate(save_to_file=False)

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert "date" in data.columns
        assert "temperature_avg" in data.columns
        assert "humidity" in data.columns

    def test_weather_ranges(self):
        """Test weather data ranges."""
        generator = WeatherGenerator()
        data = generator.generate(save_to_file=False)

        assert data["humidity"].min() >= 0
        assert data["humidity"].max() <= 100
        assert data["precipitation"].min() >= 0


# ==================== EarthquakeGenerator Tests ====================


class TestEarthquakeGenerator:
    """Test earthquake generator."""

    def test_generate_basic(self):
        """Test basic earthquake generation."""
        generator = EarthquakeGenerator()
        data = generator.generate(save_to_file=False)

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert "magnitude" in data.columns
        assert "latitude" in data.columns
        assert "longitude" in data.columns


# ==================== GitHubGenerator Tests ====================


class TestGitHubGenerator:
    """Test GitHub generator."""

    def test_generate_basic(self):
        """Test basic GitHub generation."""
        generator = GitHubGenerator()
        data = generator.generate(save_to_file=False)

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert "stars" in data.columns
        assert "forks" in data.columns


# ==================== IO Utility Tests ====================


class TestIOUtilities:
    """Test I/O utilities."""

    def test_list_available_configs(self):
        """Test listing available configurations."""
        configs = list_available_configs()
        assert isinstance(configs, list)
        assert len(configs) > 0

    def test_save_and_load_csv(self, temp_data_dir, sample_dataframe):
        """Test saving and loading CSV files."""
        temp_data_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_data_dir / "test.csv"

        save_data(sample_dataframe, file_path, "csv")
        assert file_path.exists()

        loaded_data = load_data(file_path, "csv")
        pd.testing.assert_frame_equal(sample_dataframe, loaded_data)

    def test_save_and_load_json(self, temp_data_dir):
        """Test saving and loading JSON files."""
        temp_data_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_data_dir / "test.json"
        test_data = {"key1": "value1", "key2": [1, 2, 3]}

        save_data(test_data, file_path, "json")
        assert file_path.exists()

        loaded_data = load_data(file_path, "json")
        assert loaded_data == test_data


# ==================== Validation Tests ====================


class TestValidationUtilities:
    """Test validation utilities."""

    def test_validate_positive_int(self):
        """Test positive integer validation."""
        assert validate_positive_int(5, "test") == 5
        assert validate_positive_int("10", "test") == 10

        with pytest.raises(InvalidParameterError):
            validate_positive_int(-5, "test")

        with pytest.raises(InvalidParameterError):
            validate_positive_int("not_a_number", "test")

    def test_validate_positive_float(self):
        """Test positive float validation."""
        assert validate_positive_float(5.5, "test") == 5.5
        assert validate_positive_float("10.5", "test") == 10.5

        with pytest.raises(InvalidParameterError):
            validate_positive_float(-5.5, "test")

    def test_validate_dimensions(self):
        """Test dimension validation."""
        assert validate_dimensions(1) == 1
        assert validate_dimensions(2) == 2
        assert validate_dimensions(3) == 3

        with pytest.raises(InvalidParameterError):
            validate_dimensions(4)

    def test_validate_data_size(self):
        """Test data size validation."""
        assert validate_data_size(100) == 100

        with pytest.raises(InvalidParameterError):
            validate_data_size(0)


# ==================== Integration Tests ====================


class TestIntegration:
    """Integration tests across multiple components."""

    def test_random_walk_full_pipeline(self):
        """Test complete random walk pipeline."""
        generator = RandomWalkGenerator()
        data = generator.generate(save_to_file=False)
        stats = generator.calculate_statistics(data)

        assert len(data) > 0
        assert len(stats) > 0

    def test_all_generators_no_errors(self):
        """Test that all generators can run without errors."""
        generators = [
            RandomWalkGenerator(),
            DiceGenerator(),
            WeatherGenerator(),
            EarthquakeGenerator(),
            GitHubGenerator(),
        ]

        for generator in generators:
            data = generator.generate(save_to_file=False)
            assert isinstance(data, pd.DataFrame)
            assert len(data) > 0
