"""
preview_generator.py

This module provides functions to generate preview names for file renaming
based on user-defined modules. It supports modular rename logic and allows
integration with metadata.

Author: Michael Economou
Date: 2025-05-13
"""

from typing import List, Tuple, Dict, Optional, Any
from models.file_item import FileItem
from utils.validation import is_valid_filename_text
from utils.logger_helper import get_logger

logger = get_logger(__name__)


def generate_preview_names(
    files: List[FileItem],
    modules_data: List[Dict[str, Any]],
    metadata_cache: Optional[Dict[str, Dict[str, Any]]] = None
) -> Tuple[List[Tuple[str, str]], bool, str]:
    """
    Generate new filenames based on rename modules for a list of files.

    Parameters
    ----------
    files : List[FileItem]
        The list of files to rename.
    modules_data : List[Dict[str, Any]]
        The list of rename modules in serialized form.
    metadata : Optional[Dict[str, Dict[str, Any]]]
        Cached metadata for the files (optional).

    Returns
    -------
    Tuple[List[Tuple[str, str]], bool, str]
        A tuple containing:
        - List of (old_name, new_name) preview pairs
        - Bool indicating if any error occurred
        - Tooltip message if an error occurred
    """
    preview_pairs = []
    has_error = False
    tooltip = ""

    for index, file in enumerate(files):
        name_parts = []
        for module in modules_data:
            module_type = module.get("type")

            if module_type == "specified_text":
                text = module.get("text", "")
                name_parts.append(text)

            elif module_type == "counter":
                start = module.get("start", 1)
                padding = module.get("padding", 4)
                step = module.get("step", 1)
                value = start + (index * step)
                name_parts.append(str(value).zfill(padding))

            elif module_type == "metadata":
                key = module.get("field")
                meta = (metadata_cache or {}).get(file.full_path)

                if not isinstance(meta, dict):
                    logger.warning(f"[Preview] No metadata found for {file.filename}")
                    name_parts.append("unknown")
                    continue

                try:
                    value = meta.get(key) if isinstance(key, str) and key else None
                except Exception as e:
                    logger.warning(f"[Preview] Exception while getting metadata key '{key}' for {file.filename}: {e}")
                    value = None
                name_parts.append(str(value) if value else "unknown")

            else:
                name_parts.append("invalid")

        # --- Work only on the basename, extension is handled separately ---
        new_basename = "".join(name_parts)
        extension = file.extension or ""
        if extension and not extension.startswith("."):
            extension = "." + extension

        # --- Post-processing for trailing space and separator (basename only) ---
        separator = None
        for module in modules_data:
            if module.get("type") in ("original_name", "specified_text"):
                sep = module.get("separator")
                if sep:
                    separator = sep
        if not separator:
            separator = "as-is"
        if new_basename.endswith(" "):
            if separator == "snake_case":
                new_basename = new_basename.rstrip(" ") + "_"
            elif separator == "kebab-case":
                new_basename = new_basename.rstrip(" ") + "-"
            else:  # "space" or "as-is"
                new_basename = new_basename.rstrip(" ")
        # ---

        # Always join basename + extension (with dot)
        if extension:
            if not extension.startswith("."):
                extension = "." + extension
            new_name = f"{new_basename}{extension}"
        else:
            new_name = new_basename

        if not is_valid_filename_text(new_name):
            logger.warning(f"[Preview] Invalid name generated: {new_name}")
            has_error = True
            tooltip = f"Invalid filename: {new_name}"
            break

        preview_pairs.append((file.filename, new_name))

    return preview_pairs, has_error, tooltip
