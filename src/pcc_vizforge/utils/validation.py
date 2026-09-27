"""Input validation utilities for PCC-VizForge."""

import logging
from typing import Any, Dict, Optional

from pcc_vizforge.constants import (
    MAX_DATA_POINTS,
    MIN_DATA_POINTS,
    VALID_DIMENSIONS,
)
from pcc_vizforge.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


def validate_positive_int(
    value: Any, param_name: str, min_val: int = 1
) -> int:
    """Validate that a value is a positive integer.

    Args:
        value: Value to validate
        param_name: Name of the parameter (for error messages)
        min_val: Minimum allowed value

    Returns:
        Validated integer

    Raises:
        InvalidParameterError: If validation fails
    """
    try:
        int_val = int(value)
        if int_val < min_val:
            raise ValueError(f"must be >= {min_val}")
        return int_val
    except (TypeError, ValueError) as e:
        logger.error(f"Invalid {param_name}: {value}. {e}")
        raise InvalidParameterError(
            f"Invalid {param_name}: {value}. Must be integer >= {min_val}"
        )


def validate_positive_float(
    value: Any, param_name: str, min_val: float = 0.0
) -> float:
    """Validate that a value is a positive float.

    Args:
        value: Value to validate
        param_name: Name of the parameter (for error messages)
        min_val: Minimum allowed value

    Returns:
        Validated float

    Raises:
        InvalidParameterError: If validation fails
    """
    try:
        float_val = float(value)
        if float_val < min_val:
            raise ValueError(f"must be >= {min_val}")
        return float_val
    except (TypeError, ValueError) as e:
        logger.error(f"Invalid {param_name}: {value}. {e}")
        raise InvalidParameterError(
            f"Invalid {param_name}: {value}. Must be float >= {min_val}"
        )


def validate_data_size(n_points: int, param_name: str = "n_points") -> int:
    """Validate data size is within acceptable range.

    Args:
        n_points: Number of data points
        param_name: Name of the parameter (for error messages)

    Returns:
        Validated number of data points

    Raises:
        InvalidParameterError: If size is out of range
    """
    validated = validate_positive_int(n_points, param_name, min_val=MIN_DATA_POINTS)

    if validated > MAX_DATA_POINTS:
        logger.error(
            f"Data size {validated} exceeds maximum {MAX_DATA_POINTS}"
        )
        raise InvalidParameterError(
            f"Data size {validated} exceeds maximum {MAX_DATA_POINTS}"
        )

    return validated


def validate_dimensions(dimensions: int, param_name: str = "dimensions") -> int:
    """Validate that dimensions are valid.

    Args:
        dimensions: Number of dimensions
        param_name: Name of the parameter (for error messages)

    Returns:
        Validated dimensions

    Raises:
        InvalidParameterError: If dimensions are invalid
    """
    if dimensions not in VALID_DIMENSIONS:
        logger.error(
            f"Invalid {param_name}: {dimensions}. "
            f"Valid options: {VALID_DIMENSIONS}"
        )
        raise InvalidParameterError(
            f"Invalid {param_name}: {dimensions}. "
            f"Valid options: {VALID_DIMENSIONS}"
        )
    return dimensions


def validate_config_structure(
    config: Dict[str, Any], required_keys: list[str]
) -> None:
    """Validate that a config dictionary has required keys.

    Args:
        config: Configuration dictionary to validate
        required_keys: List of required top-level keys

    Raises:
        InvalidParameterError: If required keys are missing
    """
    missing_keys = [key for key in required_keys if key not in config]

    if missing_keys:
        logger.error(
            f"Configuration missing required keys: {missing_keys}"
        )
        raise InvalidParameterError(
            f"Configuration missing required keys: {missing_keys}"
        )


def validate_seed(seed: Optional[int]) -> Optional[int]:
    """Validate random seed value.

    Args:
        seed: Random seed value (can be None)

    Returns:
        Validated seed

    Raises:
        InvalidParameterError: If seed is invalid
    """
    if seed is None:
        return None

    try:
        seed_int = int(seed)
        if seed_int < 0:
            raise ValueError("must be >= 0")
        return seed_int
    except (TypeError, ValueError) as e:
        logger.error(f"Invalid random seed: {seed}. {e}")
        raise InvalidParameterError(
            f"Invalid random seed: {seed}. Must be non-negative integer"
        )
