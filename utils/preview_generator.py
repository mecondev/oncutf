"""
Module: preview_generator.py

Author: Michael Economou
Date: 2025-05-02

This module implements the core logic for generating preview filenames
based on the active rename modules. It orchestrates the execution of
each module in sequence and validates the resulting names.

Used by oncutf to display accurate previews before performing batch
renaming operations.

Supports:
- Modular rename pipeline execution
- Duplicate and invalid filename detection
- Conflict resolution and visual feedback
"""

from typing import List, Tuple
from models.file_item import FileItem
from utils.filename_validator import FilenameValidator

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


def generate_preview_names(
    files: List[FileItem],
    modules_data: List[dict],
    validator: FilenameValidator
) -> Tuple[List[Tuple[str, str]], bool, str]:
    """
    Generates new filenames based on provided module configurations.

    Args:
        files (List[FileItem]): The list of files to process.
        modules_data (List[dict]): Rename module configuration dictionaries.
        validator (FilenameValidator): Validation utility for filenames.

    Returns:
        Tuple[
            List[Tuple[str, str]],  # List of (old_name, new_name)
            bool,                   # has_error: whether any validation failed
            str                     # tooltip message describing result or error
        ]
    """
    new_names: List[Tuple[str, str]] = []
    new_filenames_only: List[str] = []
    tooltip_msg = "Rename selected files"
    has_error = False
    counter_value = 1

    # Check if any module has an actual effect
    modules_have_effect = any(
        mod.get("type") == "counter"
        or mod.get("type") == "metadata"
        or (mod.get("type") == "specified_text" and mod.get("text", "").strip())
        for mod in modules_data
    )

    # No modules active: fallback to original names
    if not modules_have_effect:
        for file in files:
            if file.checked:
                new_names.append((file.filename, file.filename))
                new_filenames_only.append(file.filename)
    else:
        for file in files:
            if not file.checked:
                continue

            name_parts: List[str] = []

            for mod in modules_data:
                mod_type = mod.get("type")

                if mod_type == "specified_text":
                    name_parts.append(mod.get("text", "").strip())

                elif mod_type == "counter":
                    # Fetch start, padding, step (increment by)
                    start = mod.get("start", 1)
                    padding = mod.get("padding", 4)
                    step = mod.get("step", 1)

                    # Ensure counter starts correctly
                    if counter_value < start:
                        counter_value = start

                    padded = str(counter_value).zfill(padding)
                    name_parts.append(padded)
                    counter_value += step

                elif mod_type == "metadata" and mod.get("field") == "date":
                    # Format file date safely for filenames
                    date_str = file.date.replace(":", "-").replace(" ", "_")
                    name_parts.append(date_str)

            # Combine name parts or fallback
            if not any(part.strip() for part in name_parts):
                new_filename = file.filename
            else:
                new_filename = "_".join(name_parts) + "." + file.filetype

            # Validate the filename
            is_valid, error_msg = validator.is_valid_filename(new_filename)
            if not is_valid:
                has_error = True
                tooltip_msg = f"Invalid filename: {error_msg}"

            new_names.append((file.filename, new_filename))
            new_filenames_only.append(new_filename)

    # Detect duplicate names
    has_dupes, dup_msg = validator.has_duplicates(new_filenames_only)
    if has_dupes:
        has_error = True
        tooltip_msg = f"Duplicate names detected: {dup_msg}"

    # Detect "no change"
    if all(old == new for old, new in new_names):
        has_error = True
        tooltip_msg = "No changes to apply — all filenames are unchanged."

    return new_names, has_error, tooltip_msg
