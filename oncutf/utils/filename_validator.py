"""
Module: filename_validator.py

Author: Michael Economou
Date: 2025-05-06

This module provides functions for validating and cleaning filenames according
to Windows standards. It includes utilities for checking character validity,
cleaning text, and preparing final filenames.
Contains:
- is_valid_filename_char: Check if a character is valid for filenames
- clean_filename_text: Clean text by removing invalid characters
"""

import logging

from config import INVALID_FILENAME_CHARS, INVALID_FILENAME_MARKER, INVALID_TRAILING_CHARS

logger = logging.getLogger(__name__)


def is_valid_filename_char(char: str) -> bool:
    """
    Check if a character is valid for filenames

    Args:
        char: Single character to check

    Returns:
        bool: True if character is valid for filenames
    """
    return char not in INVALID_FILENAME_CHARS


def clean_filename_text(text: str) -> str:
    """
    Clean text by removing invalid filename characters

    Args:
        text: Input text to clean

    Returns:
        str: Cleaned text with invalid characters removed
    """
    # Remove invalid characters
    cleaned = "".join(char for char in text if is_valid_filename_char(char))

    logger.debug(f"[FilenameValidator] Cleaned text: '{text}' -> '{cleaned}'")
    return cleaned


def clean_trailing_chars(filename_part: str) -> str:
    """
    Remove trailing characters that are not allowed at the end of filenames

    Args:
        filename_part: The filename part (without extension) to clean

    Returns:
        str: Cleaned filename part
    """
    original = filename_part
    cleaned = filename_part.rstrip(INVALID_TRAILING_CHARS)

    if cleaned != original:
        logger.debug(f"[FilenameValidator] Removed trailing chars: '{original}' -> '{cleaned}'")

    return cleaned


def validate_filename_part(filename_part: str) -> tuple[bool, str]:
    """
    Validate a filename part and return validation status and clean version

    Args:
        filename_part: The filename part to validate

    Returns:
        Tuple[bool, str]: (is_valid, cleaned_filename_part)
    """
    if not filename_part:
        return False, INVALID_FILENAME_MARKER

    # Check for invalid characters
    has_invalid_chars = any(char in INVALID_FILENAME_CHARS for char in filename_part)

    if has_invalid_chars:
        logger.debug(f"[FilenameValidator] Invalid characters found in: '{filename_part}'")
        return False, INVALID_FILENAME_MARKER

    # Clean trailing characters
    cleaned = clean_trailing_chars(filename_part)

    # Check if result is empty after cleaning
    if not cleaned.strip():
        logger.debug(f"[FilenameValidator] Empty filename after cleaning: '{filename_part}'")
        return False, INVALID_FILENAME_MARKER

    # Check for Windows reserved names
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    if cleaned.upper() in reserved_names:
        logger.debug(f"[FilenameValidator] Reserved Windows name: '{cleaned}'")
        return False, INVALID_FILENAME_MARKER

    return True, cleaned


def should_allow_character_input(char: str) -> bool:
    """
    Determine if a character input should be allowed in filename text fields

    Args:
        char: Character being typed

    Returns:
        bool: True if character should be allowed
    """
    return is_valid_filename_char(char)


def get_validation_error_message(filename_part: str) -> str:
    """
    Get a user-friendly error message for invalid filename

    Args:
        filename_part: The invalid filename part

    Returns:
        str: User-friendly error message
    """
    if not filename_part:
        return "Filename cannot be empty"

    # Check for invalid characters
    invalid_chars = [char for char in filename_part if char in INVALID_FILENAME_CHARS]
    if invalid_chars:
        unique_chars = list(set(invalid_chars))
        char_list = "', '".join(unique_chars)
        return f"Invalid characters: '{char_list}'"

    # Check for trailing characters
    if filename_part != filename_part.rstrip(INVALID_TRAILING_CHARS):
        return "Filename cannot end with spaces or dots"

    # Check for Windows reserved names
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    if filename_part.upper() in reserved_names:
        return f"'{filename_part}' is a reserved Windows filename"

    # Check if empty after cleaning
    cleaned = clean_trailing_chars(filename_part)
    if not cleaned.strip():
        return "Filename becomes empty after removing invalid trailing characters"

    return "Invalid filename"


def is_validation_error_marker(text: str) -> bool:
    """
    Check if text is a validation error marker

        Args:
        text: Text to check

        Returns:
        bool: True if text is a validation error marker
    """
    return text == INVALID_FILENAME_MARKER or text.endswith(INVALID_FILENAME_MARKER)


# Convenience functions for common operations
def clean_and_validate(text: str) -> tuple[bool, str, str]:
    """
    Clean and validate text in one operation

    Args:
        text: Input text

    Returns:
        Tuple[bool, str, str]: (is_valid, cleaned_text, error_message)
    """
    cleaned = clean_filename_text(text)
    is_valid, result = validate_filename_part(cleaned)

    if not is_valid:
        error_msg = get_validation_error_message(text)
        return False, result, error_msg

    return True, result, ""


def prepare_final_filename(filename_part: str, extension: str = "") -> str:
    """
    Prepare final filename by cleaning and combining with extension

        Args:
        filename_part: The main filename part
        extension: File extension (with or without dot)

        Returns:
        str: Final cleaned filename
    """
    # Clean the filename part
    cleaned_part = clean_trailing_chars(filename_part)

    # Handle extension
    if extension and not extension.startswith("."):
        extension = "." + extension

    final_filename = cleaned_part + extension

    logger.debug(
        f"[FilenameValidator] Prepared final filename: '{filename_part}' + '{extension}' → '{final_filename}'"
    )

    return final_filename
