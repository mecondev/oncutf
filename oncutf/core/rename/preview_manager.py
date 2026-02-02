"""oncutf.core.rename.preview_manager.

Preview generation management for the unified rename engine.

This module provides the UnifiedPreviewManager class that orchestrates
preview generation using batch queries and caching.

Author: Michael Economou
Date: 2026-01-01
Updated: 2026-01-27 (consolidated preview_engine.py)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.core.rename.query_managers import BatchQueryManager, SmartCacheManager
    from oncutf.models.file_item import FileItem

from oncutf.core.rename.data_classes import PreviewResult
from oncutf.models.counter_scope import CounterScope
from oncutf.modules.logic.counter_logic import CounterLogic
from oncutf.modules.logic.specified_text_logic import SpecifiedTextLogic
from oncutf.modules.logic.text_removal_logic import TextRemovalLogic
from oncutf.modules.metadata_module import MetadataModule
from oncutf.modules.original_name_module import OriginalNameModule
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Module type mapping for rename operations
MODULE_TYPE_MAP = {
    "specified_text": SpecifiedTextLogic,
    "counter": CounterLogic,
    "metadata": MetadataModule,
    "original_name": OriginalNameModule,
    "remove_text_from_original_name": TextRemovalLogic,
}


class UnifiedPreviewManager:
    """Orchestrates preview generation using batch queries and caching.

    Responsibilities:
        - Compose rename output by applying modules to each file.
        - Use `BatchQueryManager` to supply availability hints (hash/metadata).
        - Cache results to reduce repeated computation during UI edits.
    """

    def __init__(self, batch_query_manager: BatchQueryManager, cache_manager: SmartCacheManager):
        """Initialize the preview manager with batch query and cache managers."""
        self.batch_query_manager = batch_query_manager
        self.cache_manager = cache_manager

    def generate_preview(
        self,
        files: list[FileItem],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
        metadata_cache: Any,
    ) -> PreviewResult:
        """Generate filename preview for `files`.

        Args:
            files: List of FileItem objects to preview.
            modules_data: Module configuration used to build names.
            post_transform: Final transform settings applied after module
                composition.
            metadata_cache: Reference to the metadata cache used by modules.

        Returns:
            A :class:`PreviewResult` containing proposed names and a flag
            indicating whether any change is present.

        """
        if not files:
            return PreviewResult([], False)

        # Generate cache key
        cache_key = self._generate_cache_key(files, modules_data, post_transform)

        # Check cache first
        cached_result = self.cache_manager.get_cached_preview(cache_key)
        if cached_result:
            logger.debug("[UnifiedPreviewManager] Using cached preview")
            return cached_result

        # Get batch availability data
        hash_availability = self.batch_query_manager.get_hash_availability(files)
        metadata_availability = self.batch_query_manager.get_metadata_availability(files)

        # Generate preview
        start_time = time.time()
        name_pairs = self._generate_name_pairs(
            files,
            modules_data,
            post_transform,
            metadata_cache,
            hash_availability,
            metadata_availability,
        )

        # Check for changes
        has_changes = any(old_name != new_name for old_name, new_name in name_pairs)

        # Create result
        result = PreviewResult(name_pairs, has_changes)

        # Cache result
        self.cache_manager.cache_preview(cache_key, result)

        elapsed = time.time() - start_time
        if elapsed > 0.05:  # Log slow preview generation
            logger.info(
                "[UnifiedPreviewManager] Preview generation took %.3fs for %d files",
                elapsed,
                len(files),
            )

        return result

    def _generate_cache_key(
        self,
        files: list[FileItem],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
    ) -> str:
        """Create a stable cache key for the preview parameters.

        The key incorporates file paths, module configuration and post-
        transform data. When JSON encoding fails for complex objects a
        fallback to `str()` is used.
        """
        file_paths = tuple(f.full_path for f in files if f.full_path)

        try:
            modules_hash = hash(json.dumps(modules_data, sort_keys=True, default=str))
            transform_hash = hash(json.dumps(post_transform, sort_keys=True, default=str))
        except (TypeError, ValueError):
            modules_hash = hash(str(modules_data))
            transform_hash = hash(str(post_transform))

        return f"{hash(file_paths)}_{modules_hash}_{transform_hash}"

    def _generate_name_pairs(
        self,
        files: list[FileItem],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
        metadata_cache: Any,
        hash_availability: dict[str, bool],
        metadata_availability: dict[str, bool],
    ) -> list[tuple[str, str]]:
        """Produce (old_name, new_name) tuples for each file.

        The method applies configured modules and post-transforms, uses
        availability hints to short-circuit modules that require metadata or
        hashes, and validates generated basenames before returning them.
        """
        from oncutf.modules.name_transform_module import NameTransformModule

        name_pairs = []
        has_name_transform = NameTransformModule.is_effective_data(post_transform)

        for idx, file in enumerate(files):
            try:
                file_path_obj = Path(file.filename)
                _basename, extension = file_path_obj.stem, file_path_obj.suffix

                # Apply modules with availability context
                new_fullname = self._apply_modules_with_context(
                    file,
                    modules_data,
                    idx,
                    metadata_cache,
                    hash_availability,
                    metadata_availability,
                    all_files=files,  # Pass full file list for scope-aware counters
                )

                # Strip extension from generated fullname
                new_basename = self._strip_extension_from_fullname(new_fullname, extension)

                # Apply post-transform if configured
                new_basename = self._apply_post_transform_if_needed(
                    new_basename, post_transform, has_name_transform
                )

                # Validate basename
                if not self._is_valid_filename_text(new_basename):
                    name_pairs.append((file.filename, file.filename))
                    continue

                # Build final filename
                new_name = self._build_final_filename(new_basename, extension)
                name_pairs.append((file.filename, new_name))

            except Exception:
                logger.warning(
                    "Failed to generate preview for %s",
                    file.filename,
                    exc_info=True,
                )
                name_pairs.append((file.filename, file.filename))

        return name_pairs

    def _apply_modules_with_context(
        self,
        file: FileItem,
        modules_data: list[dict[str, Any]],
        index: int,
        metadata_cache: Any,
        hash_availability: dict[str, bool],
        metadata_availability: dict[str, bool],
        all_files: list[FileItem] | None = None,
    ) -> str:
        """Apply rename modules for a single file, checking required data.

        Modules that depend on hash or metadata availability will be
        short-circuited and a sentinel string (e.g. "missing_hash") will be
        returned when preconditions are not met.

        Args:
            file: File being renamed
            modules_data: List of module configurations
            index: Global index in file list
            metadata_cache: Metadata cache
            hash_availability: Dict of hash availability per file
            metadata_availability: Dict of metadata availability per file
            all_files: Full file list (for scope-aware counters)

        """
        # Check if this file has required data for modules
        for module_data in modules_data:
            if module_data.get("type") == "metadata":
                category = module_data.get("category")
                if category == "tag":
                    # Check if file has hash
                    if not hash_availability.get(file.full_path, False):
                        return "missing_hash"
                elif category == "metadata_keys" and not metadata_availability.get(
                    file.full_path, False
                ):
                    # Check if file has metadata
                    return "missing_metadata"

        # Apply modules normally with full file list for scope-aware counters
        return self._apply_rename_modules(modules_data, index, file, metadata_cache, all_files)

    def _apply_rename_modules(
        self,
        modules_data: list[dict[str, Any]],
        index: int,
        file_item: FileItem,
        metadata_cache: dict[str, Any] | None = None,
        all_files: list[FileItem] | None = None,
    ) -> str:
        """Apply rename modules to generate a new filename.

        Args:
            modules_data: List of module configurations
            index: Global index of file in the list
            file_item: FileItem being renamed
            metadata_cache: Optional metadata cache
            all_files: Full list of files (required for scope-aware counters)

        Returns:
            The new filename (basename only, without extension).

        """
        file_path_obj = Path(file_item.filename)
        original_base_name, _ext = file_path_obj.stem, file_path_obj.suffix
        new_name_parts = []

        for data in modules_data:
            module_type = data.get("type")
            part = ""

            if module_type == "counter":
                # Calculate scope-aware index for counter
                scope = data.get("scope", CounterScope.PER_FOLDER.value)
                counter_index = self._calculate_scope_aware_index(
                    scope, index, file_item, all_files
                )
                part = CounterLogic.apply_from_data(data, file_item, counter_index, metadata_cache)

            elif module_type == "specified_text":
                part = SpecifiedTextLogic.apply_from_data(data, file_item, index, metadata_cache)

            elif module_type == "original_name":
                part = original_base_name or "originalname"

            elif module_type == "remove_text_from_original_name":
                result_filename = TextRemovalLogic.apply_from_data(
                    data, file_item, index, metadata_cache
                )
                part = Path(result_filename).stem

            elif module_type == "metadata":
                part = MetadataModule.apply_from_data(data, file_item, index, metadata_cache)

            new_name_parts.append(part)

        return "".join(new_name_parts)

    def _calculate_scope_aware_index(
        self,
        scope: str,
        global_index: int,
        file_item: FileItem,
        all_files: list[FileItem] | None = None,
    ) -> int:
        """Calculate the appropriate counter index based on scope.

        Args:
            scope: Counter scope ('global', 'per_folder', 'per_extension', 'per_filegroup')
            global_index: The global index in the full file list
            file_item: Current file being processed
            all_files: Full list of files

        Returns:
            The scope-adjusted index to use for counter calculation

        """
        try:
            scope_enum = CounterScope(scope)
        except ValueError:
            logger.warning("[PreviewManager] Unknown counter scope: %s, using GLOBAL", scope)
            return global_index

        if scope_enum == CounterScope.GLOBAL:
            return global_index

        if scope_enum == CounterScope.PER_FOLDER:
            if not all_files or not file_item:
                return global_index
            current_folder = str(Path(file_item.full_path).parent)
            folder_index = 0
            for i, f in enumerate(all_files):
                if i >= global_index:
                    break
                if str(Path(f.full_path).parent) == current_folder:
                    folder_index += 1
            return folder_index

        if scope_enum == CounterScope.PER_EXTENSION:
            if not all_files or not file_item:
                return global_index
            current_ext = Path(file_item.filename).suffix.lower()
            ext_index = 0
            for i, f in enumerate(all_files):
                if i >= global_index:
                    break
                if Path(f.filename).suffix.lower() == current_ext:
                    ext_index += 1
            return ext_index

        # CounterScope.PER_FILEGROUP
        if not all_files or not file_item:
            return global_index
        from oncutf.utils.filesystem.file_grouper import (
            calculate_filegroup_counter_index,
        )

        try:
            return calculate_filegroup_counter_index(
                file_item, all_files, global_index, groups=None
            )
        except Exception as e:
            logger.warning("[PreviewManager] Error calculating filegroup index: %s", e)
            return global_index

    def _strip_extension_from_fullname(self, fullname: str, extension: str) -> str:
        """Strip extension from fullname if present."""
        if extension and fullname.lower().endswith(extension.lower()):
            return fullname[: -(len(extension))]
        return fullname

    def _apply_post_transform_if_needed(
        self, basename: str, post_transform: dict[str, Any], has_transform: bool
    ) -> str:
        """Apply post-transform to basename if transform is active."""
        if not has_transform:
            return basename
        from oncutf.modules.name_transform_module import NameTransformModule

        return NameTransformModule.apply_from_data(post_transform, basename)

    def _build_final_filename(self, basename: str, extension: str) -> str:
        """Build final filename from basename and extension."""
        return f"{basename}{extension}" if extension else basename

    def _is_valid_filename_text(self, basename: str) -> bool:
        """Return True if `basename` is acceptable for use as a filename."""
        try:
            from oncutf.utils.naming.validate_filename_text import (
                is_valid_filename_text,
            )

            return is_valid_filename_text(basename)
        except ImportError:
            return True


# Backwards-compatible standalone functions (for direct callers)
def apply_rename_modules(
    modules_data: list[dict[str, Any]],
    index: int,
    file_item: FileItem,
    metadata_cache: dict[str, Any] | None = None,
    all_files: list[FileItem] | None = None,
) -> str:
    """Apply rename modules to generate a new filename (standalone function).

    This is a backwards-compatible wrapper. New code should use
    UnifiedPreviewManager._apply_rename_modules instead.
    """
    # Create a minimal manager instance for standalone use
    file_path_obj = Path(file_item.filename)
    original_base_name, _ext = file_path_obj.stem, file_path_obj.suffix
    new_name_parts = []

    for data in modules_data:
        module_type = data.get("type")
        part = ""

        if module_type == "counter":
            scope = data.get("scope", CounterScope.PER_FOLDER.value)
            counter_index = calculate_scope_aware_index(scope, index, file_item, all_files)
            part = CounterLogic.apply_from_data(data, file_item, counter_index, metadata_cache)
        elif module_type == "specified_text":
            part = SpecifiedTextLogic.apply_from_data(data, file_item, index, metadata_cache)
        elif module_type == "original_name":
            part = original_base_name or "originalname"
        elif module_type == "remove_text_from_original_name":
            result_filename = TextRemovalLogic.apply_from_data(
                data, file_item, index, metadata_cache
            )
            part = Path(result_filename).stem
        elif module_type == "metadata":
            part = MetadataModule.apply_from_data(data, file_item, index, metadata_cache)

        new_name_parts.append(part)

    return "".join(new_name_parts)


def calculate_scope_aware_index(
    scope: str,
    global_index: int,
    file_item: FileItem,
    all_files: list[FileItem] | None = None,
) -> int:
    """Calculate counter index based on scope (standalone function)."""
    try:
        scope_enum = CounterScope(scope)
    except ValueError:
        return global_index

    if scope_enum == CounterScope.GLOBAL:
        return global_index

    if scope_enum == CounterScope.PER_FOLDER:
        if not all_files or not file_item:
            return global_index
        current_folder = str(Path(file_item.full_path).parent)
        folder_index = 0
        for i, f in enumerate(all_files):
            if i >= global_index:
                break
            if str(Path(f.full_path).parent) == current_folder:
                folder_index += 1
        return folder_index

    if scope_enum == CounterScope.PER_EXTENSION:
        if not all_files or not file_item:
            return global_index
        current_ext = Path(file_item.filename).suffix.lower()
        ext_index = 0
        for i, f in enumerate(all_files):
            if i >= global_index:
                break
            if Path(f.filename).suffix.lower() == current_ext:
                ext_index += 1
        return ext_index

    # CounterScope.PER_FILEGROUP
    if not all_files or not file_item:
        return global_index
    from oncutf.utils.filesystem.file_grouper import (
        calculate_filegroup_counter_index,
    )

    try:
        return calculate_filegroup_counter_index(file_item, all_files, global_index, groups=None)
    except Exception:
        return global_index
