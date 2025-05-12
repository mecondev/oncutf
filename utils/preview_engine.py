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
from typing import List

from modules.specified_text_module import SpecifiedTextModule
from modules.counter_module import CounterModule
from modules.metadata_module import MetadataModule
from models.file_item import FileItem  # αν δεν το έχεις ήδη κάνει import

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)

MODULE_TYPE_MAP = {
    "specified_text": SpecifiedTextModule,
    "counter": CounterModule,
    "metadata": MetadataModule,
    # "original_name": OriginalNameModule,  # για μελλοντική επέκταση
}


def apply_rename_modules(modules_data: List[dict], index: int, file_item: FileItem) -> str:
    """
    Applies all rename modules in sequence to generate the final filename.

    Parameters
    ----------
    modules_data : list of dict
        A list of configuration dictionaries for each rename module, typically from `module.to_dict()`.
    index : int
        The index of the current file in the list. Useful for modules like counters.
    file_item : FileItem
        The file item object containing filename, metadata, and other file-related info.

    Returns
    -------
    str
        The final assembled filename after all modules are applied.
    """
    new_name = ""

    for i, data in enumerate(modules_data):
        module_type = data.get("type")

        if module_type == "noop":
            logger.debug(f"[apply_rename_modules] Module {i} is noop — skipping.")
            continue

        module_cls = MODULE_TYPE_MAP.get(module_type)

        if not module_cls:
            logger.warning(f"[apply_rename_modules] Unknown module type '{module_type}' — skipping.")
            continue

        try:
            logger.debug(f"[apply_rename_modules] Applying {module_cls.__name__} to {file_item.filename}")
            part = module_cls.apply_from_data(data, file_item, index)
            logger.debug(f"[apply_rename_modules] Result from {module_cls.__name__}: '{part}'")
        except Exception as e:
            logger.exception(f"[apply_rename_modules] Error in module {module_cls.__name__} for {file_item.filename}: {e}")
            part = "unknown"

        new_name += part

    logger.debug(f"[apply_rename_modules] {file_item.filename} → {new_name}")
    return new_name
