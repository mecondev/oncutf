"""
Module: preview_engine.py

Author: Michael Economou
Date: 2025-05-12

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

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

from oncutf.models.counter_scope import CounterScope
from oncutf.modules.counter_module import CounterModule
from oncutf.modules.metadata_module import MetadataModule
from oncutf.modules.original_name_module import OriginalNameModule
from oncutf.modules.specified_text_module import SpecifiedTextModule
from oncutf.modules.text_removal_module import TextRemovalModule

# Initialize Logger
from oncutf.utils.logger_factory import get_cached_logger

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


def calculate_scope_aware_index(
    scope: str,
    global_index: int,
    file_item,
    all_files: list | None = None
) -> int:
    """
    Calculate the appropriate counter index based on scope.

    Args:
        scope: Counter scope ('global', 'per_folder', 'per_extension', 'per_filegroup')
        global_index: The global index in the full file list
        file_item: Current file being processed
        all_files: Full list of files (needed for per_folder/per_extension calculation)

    Returns:
        The scope-adjusted index to use for counter calculation

    Note:
        For GLOBAL scope: returns global_index unchanged
        For PER_FOLDER: returns index within current folder group
        For PER_EXTENSION: returns index within current extension group
        For PER_FILEGROUP: returns index within file group (future feature)
    """
    # Default to global scope if not recognized
    try:
        scope_enum = CounterScope(scope)
    except ValueError:
        logger.warning("[PreviewEngine] Unknown counter scope: %s, using GLOBAL", scope)
        return global_index

    # GLOBAL: use index as-is
    if scope_enum == CounterScope.GLOBAL:
        return global_index

    # PER_FOLDER: calculate index within folder
    if scope_enum == CounterScope.PER_FOLDER:
        if not all_files or not file_item:
            logger.debug(
                "[PreviewEngine] PER_FOLDER scope but no files list, using global index",
                extra={"dev_only": True}
            )
            return global_index

        # Count files in same folder before this one
        current_folder = os.path.dirname(file_item.full_path)
        folder_index = 0
        for i, f in enumerate(all_files):
            if i >= global_index:
                break
            if os.path.dirname(f.full_path) == current_folder:
                folder_index += 1

        logger.debug(
            "[PreviewEngine] PER_FOLDER scope: folder=%s, folder_index=%d",
            current_folder,
            folder_index,
            extra={"dev_only": True}
        )
        return folder_index

    # PER_EXTENSION: calculate index within extension group
    if scope_enum == CounterScope.PER_EXTENSION:
        if not all_files or not file_item:
            logger.debug(
                "[PreviewEngine] PER_EXTENSION scope but no files list, using global index",
                extra={"dev_only": True}
            )
            return global_index

        # Count files with same extension before this one
        current_ext = os.path.splitext(file_item.filename)[1].lower()
        ext_index = 0
        for i, f in enumerate(all_files):
            if i >= global_index:
                break
            if os.path.splitext(f.filename)[1].lower() == current_ext:
                ext_index += 1

        logger.debug(
            "[PreviewEngine] PER_EXTENSION scope: ext=%s, ext_index=%d",
            current_ext,
            ext_index,
            extra={"dev_only": True}
        )
        return ext_index

    # PER_FILEGROUP: calculate index within file group
    if scope_enum == CounterScope.PER_FILEGROUP:
        if not all_files or not file_item:
            logger.debug(
                "[PreviewEngine] PER_FILEGROUP scope but no files list, using global index",
                extra={"dev_only": True}
            )
            return global_index

        # Import here to avoid circular dependency
        from oncutf.utils.file_grouper import calculate_filegroup_counter_index

        try:
            filegroup_index = calculate_filegroup_counter_index(
                file_item, all_files, global_index, groups=None
            )
            logger.debug(
                "[PreviewEngine] PER_FILEGROUP scope: filegroup_index=%d",
                filegroup_index,
                extra={"dev_only": True}
            )
            return filegroup_index
        except Exception as e:
            logger.warning(
                "[PreviewEngine] Error calculating filegroup index: %s, using global",
                e
            )
            return global_index

    # Fallback
    return global_index


def apply_rename_modules(
    modules_data: list[dict],
    index: int,
    file_item: FileItem,
    metadata_cache: dict | None = None,
    all_files: list | None = None,
) -> str:
    """
    Applies the rename modules to the basename only. The extension (with the dot) is always appended at the end, unchanged.

    Args:
        modules_data: List of module configurations
        index: Global index of file in the list
        file_item: FileItem being renamed
        metadata_cache: Optional metadata cache
        all_files: Optional full list of files (required for scope-aware counters)

    Returns:
        The new filename with extension.
    """
    logger.debug(
        "[DEBUG] [PreviewEngine] apply_rename_modules CALLED for %s",
        file_item.filename,
        extra={"dev_only": True},
    )
    logger.debug("[DEBUG] [PreviewEngine] modules_data: %s", modules_data, extra={"dev_only": True})
    logger.debug("[DEBUG] [PreviewEngine] index: %s", index, extra={"dev_only": True})
    logger.debug(
        "[DEBUG] [PreviewEngine] metadata_cache provided: %s",
        metadata_cache is not None,
        extra={"dev_only": True},
    )

    global _cache_timestamp

    original_base_name, ext = os.path.splitext(file_item.filename)

    # Performance optimization: Check cache first
    cache_key = _generate_module_cache_key(modules_data, index, file_item.filename)
    current_time = time.time()

    if cache_key in _module_cache and current_time - _cache_timestamp < _cache_validity_duration:
        logger.debug(
            "[DEBUG] [PreviewEngine] Using cached result for %s",
            file_item.filename,
            extra={"dev_only": True},
        )
        return _module_cache[cache_key]

    new_name_parts = []
    for i, data in enumerate(modules_data):
        module_type = data.get("type")
        logger.debug(
            "[DEBUG] [PreviewEngine] Processing module %d: type=%s, data=%s",
            i,
            module_type,
            data,
            extra={"dev_only": True},
        )

        part = ""

        if module_type == "counter":
            # Calculate scope-aware index for counter
            scope = data.get("scope", CounterScope.PER_FOLDER.value)
            counter_index = calculate_scope_aware_index(scope, index, file_item, all_files)

            # Use CounterModule.apply_from_data() for proper counter logic including scope
            part = CounterModule.apply_from_data(data, file_item, counter_index, metadata_cache)
            logger.debug(
                "[DEBUG] [PreviewEngine] Counter result: %s (scope=%s, global_index=%d, scope_index=%d)",
                part,
                scope,
                index,
                counter_index,
                extra={"dev_only": True},
            )

        elif module_type == "specified_text":
            part = SpecifiedTextModule.apply_from_data(data, file_item, index, metadata_cache)
            logger.debug(
                "[DEBUG] [PreviewEngine] SpecifiedText result: %s",
                part,
                extra={"dev_only": True},
            )

        elif module_type == "original_name":
            part = original_base_name
            if not part:
                part = "originalname"
            logger.debug(
                "[DEBUG] [PreviewEngine] OriginalName result: %s",
                part,
                extra={"dev_only": True},
            )

        elif module_type == "remove_text_from_original_name":
            # Apply text removal to original filename and return the result
            result_filename = TextRemovalModule.apply_from_data(
                data, file_item, index, metadata_cache
            )
            # Extract just the base name without extension
            part, _ = os.path.splitext(result_filename)
            logger.debug(
                "[DEBUG] [PreviewEngine] TextRemoval result: %s",
                part,
                extra={"dev_only": True},
            )

        elif module_type == "metadata":
            logger.debug(
                "[DEBUG] [PreviewEngine] Calling MetadataModule.apply_from_data for %s",
                file_item.filename,
                extra={"dev_only": True},
            )
            part = MetadataModule.apply_from_data(data, file_item, index, metadata_cache)
            logger.debug(
                "[DEBUG] [PreviewEngine] MetadataModule result: %s",
                part,
                extra={"dev_only": True},
            )

        new_name_parts.append(part)

    # Join all parts
    new_fullname = "".join(new_name_parts)
    logger.debug(
        "[DEBUG] [PreviewEngine] Final result for %s: %s",
        file_item.filename,
        new_fullname,
        extra={"dev_only": True},
    )

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


def clear_module_cache() -> None:
    """Clear the module cache."""
    global _module_cache, _cache_timestamp
    _module_cache.clear()
    _cache_timestamp = 0
