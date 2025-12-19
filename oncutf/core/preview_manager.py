"""
Module: preview_manager.py

Author: Michael Economou
Date: 2025-05-31

preview_manager.py
Manages preview name generation for rename operations.
Extracted from MainWindow to separate business logic from UI.
"""

import os
import time
from typing import Any

from oncutf.core.type_aliases import MetadataCache, NamePairsList
from oncutf.models.file_item import FileItem
from oncutf.modules.name_transform_module import NameTransformModule
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.preview_engine import apply_rename_modules

logger = get_cached_logger(__name__)


class PreviewManager:
    """Manages preview name generation for rename operations."""

    def __init__(self, parent_window=None):
        """Initialize PreviewManager with reference to parent window."""
        self.parent_window = parent_window
        self.preview_map: dict[str, FileItem] = {}

        # Performance optimization: Cache for preview results
        # cache: key -> (result_pairs, has_changes, timestamp)
        self._preview_cache: dict[str, tuple[list[tuple[str, str]], bool, float]] = {}
        # per-key timestamps removed global timestamp bug
        self._cache_validity_duration = 0.1  # 100ms cache validity

        logger.debug("[PreviewManager] Initialized", extra={"dev_only": True})

    def generate_preview_names(
        self,
        selected_files: list[FileItem],
        rename_data: dict[str, Any],
        metadata_cache: MetadataCache | None,
        all_modules: list[Any],
    ) -> tuple[NamePairsList, bool]:
        """Generate preview names for selected files with caching."""
        if not selected_files:
            return [], False

        # Performance optimization: Check cache first
        cache_key = self._generate_cache_key(selected_files, rename_data)
        current_time = time.time()

        entry = self._preview_cache.get(cache_key)
        if entry:
            cached_result, cached_has_changes, cached_ts = entry
            if current_time - cached_ts < self._cache_validity_duration:
                logger.debug(
                    "[PreviewManager] Using cached preview result (per-key)",
                    extra={"dev_only": True},
                )
                return cached_result, cached_has_changes

        # Generate new preview
        start_time = time.time()
        result = self._generate_preview_names_internal(
            selected_files, rename_data, metadata_cache, all_modules
        )

        # Cache the result
        # store timestamp per-key
        pairs, has_changes = result
        self._preview_cache[cache_key] = (pairs, has_changes, current_time)

        elapsed = time.time() - start_time
        if elapsed > 0.1:  # Log slow preview generation
            logger.info(
                "[PreviewManager] Preview generation took %.3fs for %d files",
                elapsed,
                len(selected_files),
            )

        return result

    def _generate_cache_key(
        self, selected_files: list[FileItem], rename_data: dict[str, Any]
    ) -> str:
        """Generate cache key for preview results."""
        # Create a hash based on file paths and rename data
        file_paths = tuple(f.full_path for f in selected_files)
        import json

        try:
            rename_hash = hash(json.dumps(rename_data, sort_keys=True, default=str))
        except (TypeError, ValueError):
            rename_hash = hash(str(rename_data))

        return f"{hash(file_paths)}_{rename_hash}"

    def _generate_preview_names_internal(
        self,
        selected_files: list[FileItem],
        rename_data: dict[str, Any],
        metadata_cache: MetadataCache | None,
        all_modules: list[Any],
    ) -> tuple[NamePairsList, bool]:
        """Internal preview generation method."""
        modules_data = rename_data.get("modules", [])
        post_transform = rename_data.get("post_transform", {})

        # Check if all modules are no-op
        is_noop = self._check_if_noop(all_modules, post_transform)
        self.preview_map = {file.filename: file for file in selected_files}

        if is_noop:
            if not all_modules and not NameTransformModule.is_effective(post_transform):
                # No modules at all - show empty preview
                self.update_preview_tables_from_pairs([])
                return [], False
            else:
                # Modules exist but are no-op - show original names
                name_pairs = [(f.filename, f.filename) for f in selected_files]
                self.update_preview_tables_from_pairs(name_pairs)
                return name_pairs, False

        name_pairs = self._generate_name_pairs(
            selected_files, modules_data, post_transform, metadata_cache
        )
        self._update_preview_map_with_new_names(name_pairs)

        # Always update preview tables
        self.update_preview_tables_from_pairs(name_pairs)

        has_changes = any(old_name != new_name for old_name, new_name in name_pairs)
        return name_pairs, has_changes

    def _check_if_noop(self, all_modules: list[Any], post_transform: dict[str, Any]) -> bool:
        """Check if all modules are no-op."""
        is_noop = True
        for module_widget in all_modules:
            if module_widget.is_effective():
                is_noop = False
                break
        if NameTransformModule.is_effective(post_transform):
            is_noop = False
        return is_noop

    def _generate_name_pairs(
        self,
        selected_files: list[FileItem],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
        metadata_cache: MetadataCache | None,
    ) -> NamePairsList:
        """Generate name pairs by applying modules with performance optimizations."""
        name_pairs = []

        # Performance optimization: Pre-compute common values
        has_name_transform = NameTransformModule.is_effective(post_transform)

        for idx, file in enumerate(selected_files):
            try:
                basename, extension = os.path.splitext(file.filename)
                new_fullname = apply_rename_modules(
                    modules_data, idx, file, metadata_cache, all_files=selected_files
                )

                if extension and new_fullname.lower().endswith(extension.lower()):
                    new_basename = new_fullname[: -(len(extension))]
                else:
                    new_basename = new_fullname

                if has_name_transform:
                    new_basename = NameTransformModule.apply_from_data(post_transform, new_basename)

                # Validate new basename; if invalid, log and fallback to original filename
                if not self._is_valid_filename_text(new_basename):
                    logger.debug(
                        "[PreviewManager] Invalid basename from modules for '%s': '%s' - falling back to original",
                        file.filename,
                        new_basename,
                        extra={"dev_only": True},
                    )
                    name_pairs.append((file.filename, file.filename))
                    continue

                new_name = f"{new_basename}{extension}" if extension else new_basename
                name_pairs.append((file.filename, new_name))

            except Exception as e:
                logger.warning("Failed to generate preview for %s: %s", file.filename, e)
                name_pairs.append((file.filename, file.filename))

        return name_pairs

    def _update_preview_map_with_new_names(self, name_pairs: list[tuple[str, str]]) -> None:
        """Update preview map with new names."""
        for old_name, new_name in name_pairs:
            if old_name != new_name:
                file_item = self.preview_map.get(old_name)
                if file_item:
                    self.preview_map[new_name] = file_item

    def _is_valid_filename_text(self, basename: str) -> bool:
        """Validate filename text."""
        try:
            from oncutf.utils.validate_filename_text import is_valid_filename_text

            return is_valid_filename_text(basename)
        except ImportError:
            return True

    def get_preview_map(self) -> dict[str, FileItem]:
        """Get the current preview map."""
        return self.preview_map.copy()

    def clear_preview_map(self) -> None:
        """Clear the preview map."""
        self.preview_map.clear()

    def clear_cache(self) -> None:
        """Clear the preview cache."""
        self._preview_cache.clear()

    def clear_all_caches(self) -> None:
        """Clear all caches used by the preview system."""
        # Clear preview cache
        self.clear_cache()

        # Clear module cache
        from oncutf.utils.preview_engine import clear_module_cache

        clear_module_cache()

        # Clear metadata cache
        from oncutf.modules.metadata_module import MetadataModule

        MetadataModule.clear_cache()

        logger.debug("[PreviewManager] All caches cleared", extra={"dev_only": True})

    def compute_max_filename_width(self, file_list: list[FileItem]) -> int:
        """
        Calculate the ideal column width in pixels based on the longest filename.

        The width is estimated as: 8 * length of longest filename,
        clamped between 250 and 1000 pixels. This ensures a readable but bounded width
        for the filename column in the preview table.

        Args:
            file_list: A list of FileItem instances to analyze.

        Returns:
            Pixel width suitable for displaying the longest filename.
        """
        # Get the length of the longest filename (in characters)
        max_len = max((len(file.filename) for file in file_list), default=0)

        # Convert length to pixels (roughly 8 px per character), then clamp
        pixel_width = 8 * max_len
        clamped_width = min(max(pixel_width, 250), 1000)

        logger.debug(
            "Longest filename length: %d chars -> width: %d px (clamped)",
            max_len,
            clamped_width,
        )
        return clamped_width

    def update_status_from_preview(self, status_html: str) -> None:
        """Update the status label from preview widget status updates."""
        if self.parent_window and hasattr(self.parent_window, "status_manager"):
            self.parent_window.status_manager.update_status_from_preview(status_html)

    def get_identity_name_pairs(self, file_list: list[FileItem]) -> list[tuple[str, str]]:
        """Generate identity name pairs (filename -> filename) for given files."""
        return [(file.filename, file.filename) for file in file_list]

    def update_preview_tables_from_pairs(self, name_pairs: list[tuple[str, str]]) -> None:
        """
        Updates all three preview tables using the PreviewTablesView.

        Args:
            name_pairs: List of (old_name, new_name) pairs generated during preview generation.
        """
        if not self.parent_window:
            logger.warning("[PreviewManager] No parent window available for preview table updates")
            return

        # Delegate to the preview tables view
        if hasattr(self.parent_window, "preview_tables_view"):
            self.parent_window.preview_tables_view.update_from_pairs(
                name_pairs,
                getattr(self.parent_window, "preview_icons", {}),
                getattr(self.parent_window, "icon_paths", {}),
            )
        else:
            logger.warning("[PreviewManager] Preview tables view not available")

    def on_hash_calculation_completed(self) -> None:
        """
        Called when hash calculation is completed.
        Triggers preview refresh to update hash-based metadata.
        """
        logger.debug(
            "[PreviewManager] Hash calculation completed, refreshing preview",
            extra={"dev_only": True},
        )

        # Clear caches to force fresh preview generation
        self.clear_cache()

        # Trigger preview refresh if parent window has the method
        if self.parent_window and hasattr(self.parent_window, "refresh_preview"):
            self.parent_window.refresh_preview()
        elif self.parent_window and hasattr(self.parent_window, "update_preview"):
            self.parent_window.update_preview()

    def generate_preview_names_forced(
        self,
        selected_files: list[FileItem],
        rename_data: dict[str, Any],
        metadata_cache: MetadataCache | None,
        all_modules: list[Any],
    ) -> tuple[NamePairsList, bool]:
        """
        Force generate preview names bypassing the short-lived cache.
        This clears the internal preview cache and calls generate_preview_names.
        """
        # Clear short-lived cache and force regeneration
        self.clear_cache()
        logger.debug(
            "[PreviewManager] Forced preview generation requested", extra={"dev_only": True}
        )
        return self.generate_preview_names(selected_files, rename_data, metadata_cache, all_modules)
