"""
Module: metadata_validators.py

Author: Michael Economou
Date: 2025-06-10

metadata_validators.py
This module provides validation functions for metadata values.
Each validator checks if a given value is valid for a specific metadata field.
"""

from typing import Optional, Tuple

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

def validate_rotation(value: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates rotation values.

    Args:
        value: The rotation value to validate as string

    Returns:
        Tuple containing:
        - bool: True if valid, False otherwise
        - str or None: Normalized value if valid, None otherwise
        - str or None: Error message if invalid, None otherwise
    """
    valid_rotations = ["0", "90", "180", "270"]

    # Try to normalize input
    stripped_value = value.strip()

    if stripped_value in valid_rotations:
        return True, stripped_value, None

    # Try to handle common input errors
    try:
        # Try to convert to integer
        int_value = int(float(stripped_value))

        # Handle negative values
        if int_value < 0:
            int_value = (int_value % 360) + 360

        # Normalize to 0, 90, 180, 270
        normalized = str(int_value % 360)
        if normalized in valid_rotations:
            return True, normalized, None

        # For other values, find the closest valid value
        closest = min(valid_rotations, key=lambda x: abs(int(x) - int_value))
        return False, None, f"Value {int_value} is not valid. Allowed values are: 0, 90, 180, 270. Closest value: {closest}"

    except (ValueError, TypeError):
        return False, None, f"Value '{stripped_value}' is not valid. Allowed values are: 0, 90, 180, 270."

def get_validator_for_key(key_path: str):
    """
    Returns the appropriate validator function for a given key path.

    Args:
        key_path: The metadata key path (e.g. "EXIF/Rotation")

    Returns:
        A validator function or None if no specific validator exists
    """
    if "Rotation" in key_path:
        return validate_rotation

    # Add more validators here as needed

    return None
