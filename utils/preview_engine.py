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
import time

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

# Performance optimization: Module result cache
_module_cache: dict = {}
_cache_timestamp = 0
_cache_validity_duration = 0.05  # 50ms cache validity


def apply_rename_modules(modules_data, index, file_item, metadata_cache=None):
    """
    Applies the rename modules to the basename only. The extension (with the dot) is always appended at the end, unchanged.
    """
    global _cache_timestamp

    original_base_name, ext = os.path.splitext(file_item.filename)

    # Performance optimization: Check cache first
    cache_key = _generate_module_cache_key(modules_data, index, file_item.filename)
    current_time = time.time()

    if cache_key in _module_cache and current_time - _cache_timestamp < _cache_validity_duration:
        return _module_cache[cache_key]

    new_name_parts = []
    for i, data in enumerate(modules_data):
        module_type = data.get("type")

        part = ""

        if module_type == "counter":
            start = data.get("start", 1)
            step = data.get("step", 1)
            padding = data.get("padding", 1)
            value = start + (index * step)
            part = str(value).zfill(padding)

        elif module_type == "specified_text":
            part = SpecifiedTextModule.apply_from_data(data, file_item, index, metadata_cache)

        elif module_type == "original_name":
            part = original_base_name
            if not part:
                part = "originalname"

        elif module_type == "remove_text_from_original_name":
            # Apply text removal to original filename and return the result
            result_filename = TextRemovalModule.apply_from_data(
                data, file_item, index, metadata_cache
            )
            # Extract just the base name without extension
            part, _ = os.path.splitext(result_filename)

        elif module_type == "metadata":
            part = MetadataModule.apply_from_data(data, file_item, index, metadata_cache)

        new_name_parts.append(part)

    # Join all parts
    new_fullname = "".join(new_name_parts)

    # Cache the result
    _module_cache[cache_key] = new_fullname
    _cache_timestamp = current_time

    return new_fullname


def _generate_module_cache_key(modules_data, index, filename):
    """Generate cache key for module results."""
    import json

    try:
        modules_hash = hash(json.dumps(modules_data, sort_keys=True, default=str))
    except (TypeError, ValueError):
        modules_hash = hash(str(modules_data))

    return f"{modules_hash}_{index}_{filename}"


def clear_module_cache():
    """Clear the module cache."""
    global _module_cache, _cache_timestamp
    _module_cache.clear()
    _cache_timestamp = 0
