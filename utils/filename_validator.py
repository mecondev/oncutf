"""
Module: filename_validator.py

Author: Michael Economou
Date: 2025-05-01

This utility module provides logic for validating filenames across
different operating systems. It checks for invalid characters, reserved
names, and other constraints to ensure safe and portable file naming.

Used by oncutf to prevent errors during batch renaming.
"""

import os
import re
import platform

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class FilenameValidator:
    """
    Validates proposed filenames for compatibility across operating systems.
    Includes checks for invalid characters, reserved names, length, and duplicates.
    """

    # Reserved names on Windows (case-insensitive)
    WINDOWS_RESERVED_NAMES = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10))
    }

    # Common invalid characters (based on Windows)
    INVALID_CHARS_WIN = r'<>:"/\\|?*'
    INVALID_CHARS_UNIX = '/'  # Unix only disallows slash

    def __init__(self) -> None:
        self.os_name = platform.system()

    def is_valid_filename(self, name: str) -> tuple[bool, str]:
        """
        Checks if a given filename is valid for the current platform.

        Args:
            name (str): The filename to validate.

        Returns:
            (bool, str): A tuple where the first value is True if valid,
                         and the second is an error message if not.
        """
        if not name or name.strip() == "":
            return False, "Filename cannot be empty"

        # Check invalid characters
        if self.os_name == "Windows":
            if any(c in name for c in self.INVALID_CHARS_WIN):
                return False, f"Filename contains invalid characters: {self.INVALID_CHARS_WIN}"
        else:
            if "/" in name:
                return False, "Filename cannot contain '/' on Unix-like systems"

        # Check reserved names (Windows)
        base_name = os.path.splitext(name)[0].upper()
        if self.os_name == "Windows" and base_name in self.WINDOWS_RESERVED_NAMES:
            return False, f"'{base_name}' is a reserved name in Windows"

        # Check max length
        if len(name) > 255:
            return False, "Filename is too long (maximum 255 characters)"

        return True, ""

    def has_duplicates(self, names: list[str]) -> tuple[bool, str]:
        """
        Checks for duplicate filenames in a list.

        Args:
            names (list[str]): A list of filenames to check.

        Returns:
            (bool, str): True if duplicates exist, along with an error message.
        """
        seen = set()
        for name in names:
            lower_name = name.lower()
            if lower_name in seen:
                return True, f"Duplicate filename found: '{name}'"
            seen.add(lower_name)
        return False, ""
