"""
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

Author: Michael Economou
Date: 2025-05-12
"""

import os
from typing import List, Optional

from modules.specified_text_module import SpecifiedTextModule
from modules.counter_module import CounterModule
from modules.metadata_module import MetadataModule
from modules.original_name_module import OriginalNameModule
from models.file_item import FileItem

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)

MODULE_TYPE_MAP = {
    "specified_text": SpecifiedTextModule,
    "counter": CounterModule,
    "metadata": MetadataModule,
    "original_name": OriginalNameModule,
}

def apply_rename_modules(modules_data, index, file_item, metadata_cache=None):
    """
    Applies the rename modules to the basename only. The extension (with the dot) is always appended at the end, unchanged.
    """
    new_name_parts = []
    original_base_name, ext = os.path.splitext(file_item.filename)
    logger.debug(f"[apply_rename_modules] Start: original filename='{file_item.filename}', base='{original_base_name}', ext='{ext}'")
    # All modules operate only on the basename. The extension is not affected by any module.

    for i, data in enumerate(modules_data):
        module_type = data.get("type")
        logger.debug(f"[apply_rename_modules] Module {i}: {module_type} | data={data}")

        if module_type == "noop":
            continue

        module_cls = MODULE_TYPE_MAP.get(module_type)
        if not module_cls:
            logger.warning(f"Unknown module type: {module_type}")
            continue

        is_effective = True
        if hasattr(module_cls, 'is_effective'):
            is_effective = module_cls.is_effective(data)

        # SpecifiedTextModule logic
        if module_type == "specified_text":
            text = data.get("text", "").strip()
            if not text:
                if new_name_parts:
                    continue
                else:
                    new_name_parts.append(original_base_name)
                    logger.debug(f"[apply_rename_modules] SpecifiedText empty, using original base: {original_base_name}")
                    continue
            else:
                part = module_cls.apply_from_data(data, file_item, index, metadata_cache)
                logger.debug(f"[apply_rename_modules] SpecifiedText part: '{part}' (from text='{text}')")
                new_name_parts.append(part)
                continue

        if module_type == "original_name" and not is_effective:
            if not new_name_parts:
                new_name_parts.append(original_base_name)
                logger.debug(f"[apply_rename_modules] OriginalName fallback, using original base: {original_base_name}")
            continue

        if is_effective:
            part = module_cls.apply_from_data(data, file_item, index, metadata_cache)
            logger.debug(f"[apply_rename_modules] Module {module_type} part: '{part}'")
            new_name_parts.append(part)

    logger.debug(f"[apply_rename_modules] All parts before join: {new_name_parts}")
    final_basename = ''.join(new_name_parts) if new_name_parts else ''
    logger.debug(f"[apply_rename_modules] Final basename before extension: '{final_basename}'")
    final_name = final_basename + ext
    logger.debug(f"[apply_rename_modules] Final name with extension: '{final_name}'")
    logger.debug(f"[apply_rename_modules] Final name: {file_item.filename} → {final_name}")
    return final_name
