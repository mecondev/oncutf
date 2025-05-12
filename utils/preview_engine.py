"""
preview_engine.py

This module provides the core logic for applying rename rules
(modules) to filenames based on user-defined configurations.

Supported module types include:
- Specified Text: Adds static text to the filename
- Counter: Adds an incrementing number with configurable padding
- Metadata: Appends a formatted date based on file metadata

The function `apply_rename_modules()` is used by the main application
to generate preview names and resolve rename plans for batch processing.

Author: Michael Economou
Date: 2025-05-12
"""

import os
from logger_helper import get_logger
from models.file_item import FileItem


logger = get_logger(__name__)

def apply_rename_modules(modules_data: list[dict], index: int, file_item: FileItem) -> str:
    """
    Applies rename modules to build a new filename.

    Ignores original name unless a module explicitly uses it (e.g., 'original_name' module).

    Args:
        modules_data (list[dict]): List of rename module configurations.
        index (int): Index of the file in the list (used for counters).
        file_item (FileItem): FileItem instance with access to original filename and metadata.

    Returns:
        str: The new filename generated from modules (including extension).
    """
    try:
        name_parts = []
        ext = os.path.splitext(file_item.filename)[1]  # keep the extension

        for module in modules_data:
            if module["type"] == "specified_text":
                name_parts.append(module.get("text", ""))
            elif module["type"] == "counter":
                start = module.get("start", 1)
                padding = module.get("padding", 4)
                step = module.get("step", 1)
                number = start + index * step
                name_parts.append(f"{number:0{padding}d}")
            elif module["type"] == "metadata":
                field = module.get("field")
                value = file_item.metadata.get(field, "unknown")
                name_parts.append(str(value))
            elif module["type"] == "original_name":
                base_name = os.path.splitext(file_item.filename)[0]
                name_parts.append(base_name)

        new_name = "".join(name_parts) + ext
        logger.debug(f"[apply_rename_modules] {file_item.filename} → {new_name}")
        return new_name

    except Exception as e:
        logger.warning(f"Failed to apply rename modules to {file_item.filename}: {e}")
        return file_item.filename
