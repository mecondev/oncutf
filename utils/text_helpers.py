"""
text_helpers.py

Author: Michael Economou
Date: 2025-05-01

Utility functions for text manipulation and formatting.
Provides helper functions for truncating, formatting, and processing text strings.
"""

from typing import Optional


def elide_text(text: str, max_len: int) -> str:
    """
    Truncates text to a maximum number of characters with ellipsis if needed.

    Example:
        elide_text("example_filename_that_is_too_long.txt", 25)
        → "example_filename_that_i…"

    Parameters:
        text (str): The original text to truncate.
        max_len (int): Maximum allowed length, including ellipsis.

    Returns:
        str: Elided version of the text.
    """
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "…"
