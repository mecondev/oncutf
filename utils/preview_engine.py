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
                # If another module precedes, skip specified text entirely (add nothing)
                if new_name_parts:
                    continue
                else:
                    # If it's the first module and empty, only then add the original basename
                    new_name_parts.append(original_base_name)
                    continue
            else:
                # There is text, add it
                part = module_cls.apply_from_data(data, file_item, index, metadata_cache)
                new_name_parts.append(part)
                continue

        # OriginalNameModule logic
        if module_type == "original_name" and not is_effective:
            # If the original name hasn't already been added, add it
            if not new_name_parts:
                new_name_parts.append(original_base_name)
            continue

        # General case (effective module)
        if is_effective:
            part = module_cls.apply_from_data(data, file_item, index, metadata_cache)
            new_name_parts.append(part)

    # If there are no parts, leave only the extension
    final_basename = ''.join(new_name_parts) if new_name_parts else ''
    # Always append the extension (with the dot) at the end
    final_name = final_basename + ext

    logger.debug(f"[apply_rename_modules] Final name: {file_item.filename} → {final_name}")
    return final_name
