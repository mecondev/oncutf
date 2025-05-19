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

                value = meta.get(key)
                name_parts.append(str(value) if value else "unknown")

            else:
                name_parts.append("invalid")

        new_name = "".join(name_parts)

        if not is_valid_filename_text(new_name):
            logger.warning(f"[Preview] Invalid name generated: {new_name}")
            has_error = True
            tooltip = f"Invalid filename: {new_name}"
            break


        preview_pairs.append((file.filename, f"{new_name}.{file.extension}"))

    return preview_pairs, has_error, tooltip
