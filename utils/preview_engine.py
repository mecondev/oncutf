"""
Module: preview_engine.py

Author: Michael Economou
Date: 2025-06-01

preview_engine.py
This module provides the core logic for applying rename rules
(modules) to filenames based on user-defined configurations.
Supported module types include:
- Specified Text: Adds static text to the filename
- Counter: Adds an incrementing number with configurable padding
- Metadata: Appends a formatted date based on file metadata
- Original Name: Applies transformation to the original filename
The function `apply_rename_modules()` is used by the main application
to generate preview names and resolve rename plans for batch processing.
"""
import os

from modules.counter_module import CounterModule
from modules.metadata_module import MetadataModule
from modules.original_name_module import OriginalNameModule
from modules.specified_text_module import SpecifiedTextModule
from modules.text_removal_module import TextRemovalModule

# Initialize Logger
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

MODULE_TYPE_MAP = {
    "specified_text": SpecifiedTextModule,
    "counter": CounterModule,
    "metadata": MetadataModule,
    "original_name": OriginalNameModule,
    "remove_text_from_original_name": TextRemovalModule,
}

def apply_rename_modules(modules_data, index, file_item, metadata_cache=None):
    """
    Applies the rename modules to the basename only. The extension (with the dot) is always appended at the end, unchanged.
    """
    original_base_name, ext = os.path.splitext(file_item.filename)
    logger.debug(f"[apply_rename_modules] Start: original filename='{file_item.filename}', base='{original_base_name}', ext='{ext}'", extra={"dev_only": True})

    new_name_parts = []
    for i, data in enumerate(modules_data):
        module_type = data.get("type")
        logger.debug(f"[apply_rename_modules] Module {i}: {module_type} | data={data}", extra={"dev_only": True})

        part = ""

        if module_type == "counter":
            start = data.get("start", 1)
            step = data.get("step", 1)
            padding = data.get("padding", 1)
            value = start + (index * step)
            part = str(value).zfill(padding)

        elif module_type == "specified_text":
            part = SpecifiedTextModule.apply_from_data(data, file_item, index, metadata_cache)
            logger.debug(f"[apply_rename_modules] SpecifiedText part: '{part}'", extra={"dev_only": True})

        elif module_type == "original_name":
            part = original_base_name
            if not part:
                logger.debug(f"[apply_rename_modules] OriginalName fallback, using original base: {original_base_name}", extra={"dev_only": True})
                part = "originalname"

        elif module_type == "remove_text_from_original_name":
            # Apply text removal to original filename and return the result
            result_filename = TextRemovalModule.apply_from_data(data, file_item, index, metadata_cache)
            # Extract just the base name without extension
            part, _ = os.path.splitext(result_filename)
            logger.debug(f"[apply_rename_modules] TextRemoval result: '{part}'", extra={"dev_only": True})

        else:
            logger.warning(f"[apply_rename_modules] Unknown module type: '{module_type}'")

        if part:
            logger.debug(f"[apply_rename_modules] Module {module_type} part: '{part}'", extra={"dev_only": True})
            new_name_parts.append(part)

    logger.debug(f"[apply_rename_modules] All parts before join: {new_name_parts}", extra={"dev_only": True})

    # If no effective modules produced content, fallback to original name
    if not new_name_parts or all(not part.strip() for part in new_name_parts):
        logger.debug(f"[apply_rename_modules] No effective modules, using original base: {original_base_name}", extra={"dev_only": True})
        final_basename = original_base_name
    else:
        final_basename = "".join(new_name_parts)

    logger.debug(f"[apply_rename_modules] Final basename before extension: '{final_basename}'", extra={"dev_only": True})
    final_name = f"{final_basename}{ext}"
    logger.debug(f"[apply_rename_modules] Final name with extension: '{final_name}'", extra={"dev_only": True})
    logger.debug(f"[apply_rename_modules] Final name: {file_item.filename} → {final_name}", extra={"dev_only": True})
    return final_name
