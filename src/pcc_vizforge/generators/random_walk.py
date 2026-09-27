"""Random Walk data generator."""

import logging
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd

from pcc_vizforge.exceptions import (
    DataGenerationError,
    DataShapeError,
    InvalidParameterError,
)
from pcc_vizforge.utils.io import get_data_directory, load_config, save_data
from pcc_vizforge.utils.validation import (
    validate_config_structure,
    validate_data_size,
    validate_dimensions,
    validate_positive_float,
    validate_positive_int,
    validate_seed,
)

logger = logging.getLogger(__name__)


class RandomWalkGenerator:
    """Generator for random walk data."""

    REQUIRED_CONFIG_KEYS = ["data_generation"]

    def __init__(self, config_name: str = "random_walk") -> None:
        """Initialize the generator with configuration.

        Args:
            config_name: Name of configuration file to use

        Raises:
            InvalidParameterError: If configuration is invalid
            DataGenerationError: If config structure is wrong
        """
        logger.info(f"Initializing RandomWalkGenerator with config: {config_name}")
        try:
            self.config: Dict[str, Any] = load_config(config_name)
            validate_config_structure(self.config, self.REQUIRED_CONFIG_KEYS)
            self.data_config: Dict[str, Any] = self.config["data_generation"]
            self._validate_config()
            logger.debug("RandomWalkGenerator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RandomWalkGenerator: {e}")
            raise

    def _validate_config(self) -> None:
        """Validate that all required configuration parameters are present.

        Raises:
            DataGenerationError: If configuration parameters are invalid
        """
        required_params = ["n_steps", "n_walks", "step_size"]
        try:
            for param in required_params:
                if param not in self.data_config:
                    raise InvalidParameterError(
                        f"Missing required configuration parameter: {param}"
                    )

            # Validate parameter values
            validate_data_size(self.data_config["n_steps"], "n_steps")
            validate_positive_int(self.data_config["n_walks"], "n_walks")
            validate_positive_float(self.data_config["step_size"], "step_size")

            # Optional parameters
            if "dimensions" in self.data_config:
                validate_dimensions(self.data_config["dimensions"])

            if "random_seed" in self.data_config:
                validate_seed(self.data_config["random_seed"])

            logger.debug("Configuration validation passed")

        except (InvalidParameterError, DataGenerationError) as e:
            logger.error(f"Configuration validation failed: {e}")
            raise DataGenerationError(f"Invalid configuration: {e}")

    def generate(self, save_to_file: bool = True) -> pd.DataFrame:
        """Generate random walk data.

        Args:
            save_to_file: Whether to save generated data to file

        Returns:
            DataFrame with random walk data

        Raises:
            DataGenerationError: If data generation fails
            DataShapeError: If generated data has unexpected shape
        """
        logger.info("Starting random walk data generation")
        try:
            # Set random seed for reproducibility
            if "random_seed" in self.data_config:
                seed = self.data_config["random_seed"]
                np.random.seed(seed)
                logger.debug(f"Random seed set to: {seed}")

            n_steps = self.data_config["n_steps"]
            n_walks = self.data_config["n_walks"]
            step_size = self.data_config["step_size"]
            dimensions = self.data_config.get("dimensions", 1)

            logger.debug(
                f"Generating {n_walks} walks with {n_steps} steps each "
                f"in {dimensions}D space"
            )

            data: List[Dict[str, Any]] = []

            for walk_id in range(n_walks):
                if dimensions == 1:
                    # 1D random walk
                    steps = (
                        np.random.choice([-1, 1], size=n_steps) * step_size
                    )
                    positions = np.cumsum(steps)

                    for step in range(n_steps):
                        data.append(
                            {
                                "walk_id": walk_id,
                                "step": step,
                                "position": float(positions[step]),
                                "x_position": float(positions[step]),
                                "y_position": 0.0,
                            }
                        )

                elif dimensions == 2:
                    # 2D random walk
                    x_steps = (
                        np.random.choice([-1, 1], size=n_steps) * step_size
                    )
                    y_steps = (
                        np.random.choice([-1, 1], size=n_steps) * step_size
                    )

                    x_positions = np.cumsum(x_steps)
                    y_positions = np.cumsum(y_steps)

                    for step in range(n_steps):
                        distance = np.sqrt(
                            x_positions[step] ** 2 + y_positions[step] ** 2
                        )
                        data.append(
                            {
                                "walk_id": walk_id,
                                "step": step,
                                "position": float(distance),
                                "x_position": float(x_positions[step]),
                                "y_position": float(y_positions[step]),
                            }
                        )

                elif dimensions == 3:
                    # 3D random walk
                    x_steps = (
                        np.random.choice([-1, 1], size=n_steps) * step_size
                    )
                    y_steps = (
                        np.random.choice([-1, 1], size=n_steps) * step_size
                    )
                    z_steps = (
                        np.random.choice([-1, 1], size=n_steps) * step_size
                    )

                    x_positions = np.cumsum(x_steps)
                    y_positions = np.cumsum(y_steps)
                    z_positions = np.cumsum(z_steps)

                    for step in range(n_steps):
                        distance = np.sqrt(
                            x_positions[step] ** 2
                            + y_positions[step] ** 2
                            + z_positions[step] ** 2
                        )
                        data.append(
                            {
                                "walk_id": walk_id,
                                "step": step,
                                "position": float(distance),
                                "x_position": float(x_positions[step]),
                                "y_position": float(y_positions[step]),
                                "z_position": float(z_positions[step]),
                            }
                        )

            df = pd.DataFrame(data)

            # Validate generated data
            if len(df) != n_walks * n_steps:
                logger.error(
                    f"Generated data has unexpected shape: "
                    f"expected {n_walks * n_steps} rows, got {len(df)}"
                )
                raise DataShapeError(
                    f"Generated data has unexpected number of rows: "
                    f"expected {n_walks * n_steps}, got {len(df)}"
                )

            # Add derived metrics
            df["cumulative_distance"] = df.groupby("walk_id")[
                "position"
            ].cumsum()
            df["step_size"] = (
                df.groupby("walk_id")["position"].diff().fillna(0).abs()
            )

            logger.info(f"Successfully generated {len(df)} random walk data points")

            if save_to_file:
                try:
                    data_dir = get_data_directory("random_walk")
                    file_path = data_dir / "random_walk_data.csv"
                    save_data(df, file_path, "csv")
                    logger.info(f"Saved data to: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to save data: {e}")
                    raise DataGenerationError(f"Failed to save generated data: {e}")

            return df

        except DataGenerationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during data generation: {e}")
            raise DataGenerationError(f"Unexpected error during data generation: {e}")

    def generate_multiple_scenarios(
        self, scenarios: List[Dict[str, Any]], save_to_file: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """Generate multiple random walk scenarios with different parameters.

        Args:
            scenarios: List of parameter dictionaries to override config
            save_to_file: Whether to save generated data to files

        Returns:
            Dictionary mapping scenario names to DataFrames

        Raises:
            DataGenerationError: If any scenario generation fails
        """
        logger.info(f"Generating {len(scenarios)} random walk scenarios")
        results: Dict[str, pd.DataFrame] = {}
        original_config = self.data_config.copy()

        try:
            for i, scenario in enumerate(scenarios):
                scenario_name = scenario.get("name", f"scenario_{i}")
                logger.debug(f"Generating scenario: {scenario_name}")

                # Update config with scenario parameters
                self.data_config.update(scenario)

                try:
                    # Validate updated config
                    self._validate_config()

                    # Generate data
                    df = self.generate(save_to_file=False)
                    df["scenario"] = scenario_name
                    results[scenario_name] = df

                    if save_to_file:
                        data_dir = get_data_directory("random_walk")
                        file_path = data_dir / f"random_walk_{scenario_name}.csv"
                        save_data(df, file_path, "csv")
                        logger.info(f"Saved scenario {scenario_name} to: {file_path}")

                except Exception as e:
                    logger.error(f"Failed to generate scenario {scenario_name}: {e}")
                    raise DataGenerationError(
                        f"Failed to generate scenario {scenario_name}: {e}"
                    )

            logger.info(f"Successfully generated {len(results)} scenarios")
            return results

        finally:
            # Restore original config
            self.data_config = original_config
            logger.debug("Restored original configuration")

    def calculate_statistics(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate statistical measures for random walk data.

        Args:
            data: Random walk DataFrame

        Returns:
            Dictionary of statistical measures

        Raises:
            DataShapeError: If data has unexpected structure
        """
        logger.debug("Calculating random walk statistics")
        try:
            if data.empty:
                raise DataShapeError("Cannot calculate statistics on empty DataFrame")

            if "position" not in data.columns or "walk_id" not in data.columns:
                raise DataShapeError(
                    "DataFrame must contain 'position' and 'walk_id' columns"
                )

            stats: Dict[str, float] = {}

            # Final positions
            final_positions = data.groupby("walk_id")["position"].last()
            stats["mean_final_position"] = float(final_positions.mean())
            stats["std_final_position"] = float(final_positions.std())
            stats["max_final_position"] = float(final_positions.max())
            stats["min_final_position"] = float(final_positions.min())

            # Maximum excursions
            max_positions = data.groupby("walk_id")["position"].max()
            min_positions = data.groupby("walk_id")["position"].min()

            stats["mean_max_excursion"] = float(max_positions.mean())
            stats["mean_min_excursion"] = float(min_positions.mean())
            stats["mean_total_excursion"] = float((max_positions - min_positions).mean())

            # Step statistics
            stats["mean_step_size"] = float(data["step_size"].mean())
            stats["total_steps"] = int(len(data))
            stats["n_walks"] = int(data["walk_id"].nunique())

            logger.debug(f"Calculated statistics for {stats['n_walks']} walks")
            return stats

        except DataShapeError:
            raise
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            raise DataShapeError(f"Error calculating statistics: {e}")

    def get_walk_summary(
        self, data: pd.DataFrame, walk_id: int
    ) -> Dict[str, Union[float, int]]:
        """Get summary statistics for a specific walk.

        Args:
            data: Random walk DataFrame
            walk_id: ID of the walk to summarize

        Returns:
            Dictionary of walk statistics

        Raises:
            InvalidParameterError: If walk_id not found in data
        """
        logger.debug(f"Getting summary for walk_id: {walk_id}")

        walk_data = data[data["walk_id"] == walk_id]

        if walk_data.empty:
            logger.error(f"Walk ID {walk_id} not found in data")
            raise InvalidParameterError(f"Walk ID {walk_id} not found in data")

        summary: Dict[str, Union[float, int]] = {
            "walk_id": walk_id,
            "n_steps": int(len(walk_data)),
            "final_position": float(walk_data["position"].iloc[-1]),
            "max_position": float(walk_data["position"].max()),
            "min_position": float(walk_data["position"].min()),
            "total_distance": float(walk_data["cumulative_distance"].iloc[-1]),
            "mean_step_size": float(walk_data["step_size"].mean()),
            "net_displacement": float(abs(walk_data["position"].iloc[-1])),
        }

        logger.debug(f"Summary for walk {walk_id}: {summary}")
        return summary
