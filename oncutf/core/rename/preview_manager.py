"""oncutf.core.rename.preview_manager.

Preview generation management for the unified rename engine.

This module provides the UnifiedPreviewManager class that orchestrates
preview generation using batch queries and caching.

Author: Michael Economou
Date: 2026-01-01
"""

import json
import os
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

from oncutf.core.rename.data_classes import PreviewResult
from oncutf.core.rename.query_managers import BatchQueryManager, SmartCacheManager
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


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
        files: list["FileItem"],
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
        files: list["FileItem"],
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
        files: list["FileItem"],
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
                _basename, extension = os.path.splitext(file.filename)

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
        file: "FileItem",
        modules_data: list[dict[str, Any]],
        index: int,
        metadata_cache: Any,
        hash_availability: dict[str, bool],
        metadata_availability: dict[str, bool],
        all_files: list["FileItem"] | None = None,
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
        from oncutf.utils.naming.preview_engine import apply_rename_modules

        # Check if this file has required data for modules
        for module_data in modules_data:
            if module_data.get("type") == "metadata":
                category = module_data.get("category")
                if category == "hash":
                    # Check if file has hash
                    if not hash_availability.get(file.full_path, False):
                        return "missing_hash"
                elif category == "metadata_keys":
                    # Check if file has metadata
                    if not metadata_availability.get(file.full_path, False):
                        return "missing_metadata"

        # Apply modules normally with full file list for scope-aware counters
        return apply_rename_modules(modules_data, index, file, metadata_cache, all_files=all_files)

    def _strip_extension_from_fullname(self, fullname: str, extension: str) -> str:
        """Strip extension from fullname if present.

        Args:
            fullname: The full generated name (may include extension).
            extension: The original file extension (with dot).

        Returns:
            Basename without extension.

        """
        if extension and fullname.lower().endswith(extension.lower()):
            return fullname[: -(len(extension))]
        return fullname

    def _apply_post_transform_if_needed(
        self, basename: str, post_transform: dict[str, Any], has_transform: bool
    ) -> str:
        """Apply post-transform to basename if transform is active.

        Args:
            basename: The base name to transform.
            post_transform: Transform configuration dictionary.
            has_transform: Flag indicating if transform should be applied.

        Returns:
            Transformed basename or original if no transform.

        """
        if not has_transform:
            return basename

        from oncutf.modules.name_transform_module import NameTransformModule

        return NameTransformModule.apply_from_data(post_transform, basename)

    def _build_final_filename(self, basename: str, extension: str) -> str:
        """Build final filename from basename and extension.

        Args:
            basename: The validated base name.
            extension: The file extension (with dot, may be empty).

        Returns:
            Complete filename.

        """
        return f"{basename}{extension}" if extension else basename

    def _is_valid_filename_text(self, basename: str) -> bool:
        """Return True if `basename` is acceptable for use as a filename.

        Falls back to permissive behaviour if the validator import fails.
        """
        try:
            from oncutf.utils.naming.validate_filename_text import is_valid_filename_text

            return is_valid_filename_text(basename)
        except ImportError:
            return True
