"""
Module: text_helpers.py

Author: Michael Economou
Date: 2025-05-31

text_helpers.py
Utility functions for text manipulation and formatting.
Provides helper functions for truncating, formatting, and processing text strings.
"""

import os


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
    return text[: max_len - 1] + "…"


def truncate_filename_middle(filename: str, max_length: int = 60) -> str:
    """
    Truncate filename with "..." in the middle, preserving file extension.

    This function intelligently truncates long filenames by placing "..." in the middle
    while preserving the file extension. This provides better UX than truncating at the end.

    Args:
        filename: The filename to truncate
        max_length: Maximum length of the truncated filename (default: 60)

    Returns:
        Truncated filename with "..." in the middle

    Examples:
        >>> truncate_filename_middle("very_long_filename_that_needs_truncation.jpg")
        "very_long...truncation.jpg"

        >>> truncate_filename_middle("short.txt")
        "short.txt"

        >>> truncate_filename_middle("no_extension_file")
        "no_extension_file"
    """
    if not filename:
        return ""

    if len(filename) <= max_length:
        return filename

    name_part, ext_part = os.path.splitext(filename)

    if ext_part and len(ext_part) < 10:
        # Preserve extension, truncate name part in the middle
        available_length = max_length - len(ext_part) - 3  # 3 for "..."
        if available_length > 10:
            # Split the name part and add "..." in the middle
            name_start = available_length // 2
            name_end = available_length - name_start
            truncated_name = name_part[:name_start] + "..." + name_part[-name_end:] + ext_part
            return truncated_name

    # Fallback: truncate in the middle without extension consideration
    if len(filename) > max_length:
        start_len = (max_length - 3) // 2  # 3 for "..."
        end_len = max_length - 3 - start_len
        truncated_name = filename[:start_len] + "..." + filename[-end_len:]
        return truncated_name

    return filename


def format_file_size_stable(size_bytes: int) -> str:
    """
    Format file size with stable display for better UX.

    Uses fixed-width formatting to prevent visual "jumping" when text length changes.
    All formatted strings have the same width (10 characters) for perfect alignment.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted size string with consistent width (e.g., "  1.5 GB  ", " 999 MB  ")
    """
    if size_bytes < 0:
        return "     0 B   "[:10].ljust(10)  # Fixed width: 10 characters

    # Use binary units (1024) for consistency with most systems
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    base = 1024

    size = float(size_bytes)
    unit_index = 0

    # Special handling for bytes - don't convert small values to KB
    if size_bytes < 1024:
        # Keep as bytes for values under 1024
        return f"  {int(size)} B   "[:10].ljust(10)

    # Convert to appropriate unit
    while size >= base and unit_index < len(units) - 1:
        size /= base
        unit_index += 1

    # Format with consistent 10-character width
    unit_str = units[unit_index]

    if size >= 100:
        # Large values: no decimals (e.g., "100.0 MB")
        content = f"{size:.1f} {unit_str}"
    else:
        # Small values: one decimal (e.g., "1.0 MB")
        content = f"{size:.1f} {unit_str}"

    # Ensure exactly 10 characters
    return content.rjust(10)[:10]
