"""Naming/Rename utilities package.

Filename validation, text helpers, rename logic, and preview generation.
"""

# Re-exports for backward compatibility
from oncutf.utils.naming.filename_validator import (
    clean_and_validate,
    clean_filename_text,
    get_validation_error_message,
    is_valid_filename_char,
    is_validation_error_marker,
    prepare_final_filename,
    validate_filename_part,
)
from oncutf.utils.naming.text_helpers import (
    elide_text,
    format_file_size_stable,
    truncate_filename_middle,
)

__all__ = [
    "clean_and_validate",
    "clean_filename_text",
    "elide_text",
    "format_file_size_stable",
    "get_validation_error_message",
    "is_valid_filename_char",
    "is_validation_error_marker",
    "prepare_final_filename",
    "truncate_filename_middle",
    "validate_filename_part",
]
