"""oncutf.core.rename.preview_manager.

Preview generation management for the unified rename engine.

This module provides the UnifiedPreviewManager class that orchestrates
preview generation using batch queries and caching.

Name composition logic has been extracted to :mod:`name_composer` and the
canonical module-type registry lives in :mod:`module_registry`.

Author: Michael Economou
Date: 2026-01-01
Updated: 2026-01-27 (consolidated preview_engine.py)
Updated: 2026-03-08 (extracted NameComposer + module_registry)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.core.rename.query_managers import BatchQueryManager, SmartCacheManager
    from oncutf.models.file_item import FileItem

from oncutf.core.rename.data_classes import PreviewResult
from oncutf.core.rename.name_composer import NameComposer
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class UnifiedPreviewManager:
    """Orchestrates preview generation using batch queries and caching.

    Responsibilities:
        - Use ``BatchQueryManager`` to supply availability hints.
        - Cache results to reduce repeated computation during UI edits.
        - Delegate name composition to :class:`NameComposer`.
    """

    def __init__(self, batch_query_manager: BatchQueryManager, cache_manager: SmartCacheManager):
        """Initialize the preview manager with batch query and cache managers."""
        self.batch_query_manager = batch_query_manager
        self.cache_manager = cache_manager
        self._composer = NameComposer()

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

        Delegates name composition to :class:`NameComposer` while keeping
        availability checks, post-transform, validation and error handling
        in this orchestration layer.
        """
        from oncutf.modules.name_transform_module import NameTransformModule

        name_pairs: list[tuple[str, str]] = []
        has_name_transform = NameTransformModule.is_effective_data(post_transform)
        composer = self._composer

        for idx, file in enumerate(files):
            try:
                file_path_obj = Path(file.filename)
                extension = file_path_obj.suffix

                # Apply modules with availability context
                new_fullname = composer.compose_name_with_context(
                    file,
                    modules_data,
                    idx,
                    metadata_cache,
                    hash_availability,
                    metadata_availability,
                    all_files=files,
                )

                # Strip extension from generated fullname
                new_basename = composer.strip_extension(new_fullname, extension)

                # Apply post-transform if configured
                new_basename = composer.apply_post_transform(
                    new_basename, post_transform, has_name_transform
                )

                # Validate basename
                if not composer.is_valid_filename_text(new_basename):
                    name_pairs.append((file.filename, file.filename))
                    continue

                # Build final filename
                new_name = composer.build_final_filename(new_basename, extension)
                name_pairs.append((file.filename, new_name))

            except Exception:
                logger.warning(
                    "Failed to generate preview for %s",
                    file.filename,
                    exc_info=True,
                )
                name_pairs.append((file.filename, file.filename))

        return name_pairs


# Backwards-compatible standalone functions (for direct callers)

# Shared composer instance for standalone functions
_standalone_composer = NameComposer()


def apply_rename_modules(
    modules_data: list[dict[str, Any]],
    index: int,
    file_item: FileItem,
    metadata_cache: dict[str, Any] | None = None,
    all_files: list[FileItem] | None = None,
) -> str:
    """Apply rename modules to generate a new filename (standalone function).

    This is a backwards-compatible wrapper. New code should use
    :meth:`NameComposer.compose_name` instead.
    """
    return _standalone_composer.compose_name(
        modules_data, index, file_item, metadata_cache, all_files
    )


def calculate_scope_aware_index(
    scope: str,
    global_index: int,
    file_item: FileItem,
    all_files: list[FileItem] | None = None,
) -> int:
    """Calculate counter index based on scope (standalone function).

    This is a backwards-compatible wrapper. New code should use
    :meth:`NameComposer.calculate_scope_aware_index` instead.
    """
    return NameComposer.calculate_scope_aware_index(scope, global_index, file_item, all_files)
