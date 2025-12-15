"""
Module: validate_filename_text.py

Author: Michael Economou
Date: 2025-05-12

This module defines a utility function for validating user-supplied text
intended for use in filenames. It ensures that the input conforms to
a predefined set of allowed characters, making it safe for use across
file systems.
Functions:
- is_valid_filename_text(text): Returns True if the input text is valid for filenames.
"""

import re

from oncutf.config import ALLOWED_FILENAME_CHARS


def is_valid_filename_text(text: str) -> bool:
    """
    Checks if the given text is valid for use in filenames.

    Args:
        text (str): The input text to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    return bool(re.match(ALLOWED_FILENAME_CHARS, text))
