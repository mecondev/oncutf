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
from typing import Any, Dict, List, Tuple

from models.file_item import FileItem
from modules.name_transform_module import NameTransformModule
from utils.logger_factory import get_cached_logger
from utils.preview_engine import apply_rename_modules

logger = get_cached_logger(__name__)


class PreviewManager:
    """Manages preview name generation for rename operations."""

    def __init__(self, parent_window=None):
        """Initialize PreviewManager with reference to parent window."""
        self.parent_window = parent_window
        self.preview_map: Dict[str, FileItem] = {}

        # Performance optimization: Cache for preview results
        self._preview_cache: Dict[str, Tuple[List[Tuple[str, str]], bool]] = {}
        self._cache_timestamp = 0
        self._cache_validity_duration = 0.1  # 100ms cache validity

        logger.debug("[PreviewManager] Initialized", extra={"dev_only": True})

    def generate_preview_names(
        self,
        selected_files: List[FileItem],
        rename_data: Dict[str, Any],
        metadata_cache: Any,
        all_modules: List[Any]
    ) -> Tuple[List[Tuple[str, str]], bool]:
        """Generate preview names for selected files with caching."""
        if not selected_files:
            return [], False

        # Performance optimization: Check cache first
        cache_key = self._generate_cache_key(selected_files, rename_data)
        current_time = time.time()

        if (cache_key in self._preview_cache and
            current_time - self._cache_timestamp < self._cache_validity_duration):
            logger.debug("[PreviewManager] Using cached preview result", extra={"dev_only": True})
            return self._preview_cache[cache_key]

        # Generate new preview
        start_time = time.time()
        result = self._generate_preview_names_internal(selected_files, rename_data, metadata_cache, all_modules)

        # Cache the result
        self._preview_cache[cache_key] = result
        self._cache_timestamp = current_time

        elapsed = time.time() - start_time
        if elapsed > 0.1:  # Log slow preview generation
            logger.info(f"[PreviewManager] Preview generation took {elapsed:.3f}s for {len(selected_files)} files")

        return result

    def _generate_cache_key(self, selected_files: List[FileItem], rename_data: Dict[str, Any]) -> str:
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
        selected_files: List[FileItem],
        rename_data: Dict[str, Any],
        metadata_cache: Any,
        all_modules: List[Any]
    ) -> Tuple[List[Tuple[str, str]], bool]:
        """Internal preview generation method."""
        modules_data = rename_data.get("modules", [])
        post_transform = rename_data.get("post_transform", {})

        # Check if hash calculation is needed for hash modules
        if self._needs_hash_calculation(modules_data, selected_files):
            if not self._ask_user_for_hash_calculation(selected_files):
                # User cancelled - return original names unchanged but still show preview
                name_pairs = [(f.filename, f.filename) for f in selected_files]
                self.preview_map = {file.filename: file for file in selected_files}
                # Always update preview tables even with no changes
                self.update_preview_tables_from_pairs(name_pairs)
                return name_pairs, False

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

        name_pairs = self._generate_name_pairs(selected_files, modules_data, post_transform, metadata_cache)
        self._update_preview_map_with_new_names(name_pairs)

        # Always update preview tables
        self.update_preview_tables_from_pairs(name_pairs)

        has_changes = any(old_name != new_name for old_name, new_name in name_pairs)
        return name_pairs, has_changes

    def _check_if_noop(self, all_modules: List[Any], post_transform: Dict[str, Any]) -> bool:
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
        selected_files: List[FileItem],
        modules_data: List[Dict[str, Any]],
        post_transform: Dict[str, Any],
        metadata_cache: Any
    ) -> List[Tuple[str, str]]:
        """Generate name pairs by applying modules with performance optimizations."""
        name_pairs = []

        # Performance optimization: Pre-compute common values
        has_name_transform = NameTransformModule.is_effective(post_transform)

        for idx, file in enumerate(selected_files):
            try:
                basename, extension = os.path.splitext(file.filename)
                new_fullname = apply_rename_modules(modules_data, idx, file, metadata_cache)

                if extension and new_fullname.lower().endswith(extension.lower()):
                    new_basename = new_fullname[:-(len(extension))]
                else:
                    new_basename = new_fullname

                if has_name_transform:
                    new_basename = NameTransformModule.apply_from_data(post_transform, new_basename)

                if not self._is_valid_filename_text(new_basename):
                    name_pairs.append((file.filename, file.filename))
                    continue

                new_name = f"{new_basename}{extension}" if extension else new_basename
                name_pairs.append((file.filename, new_name))

            except Exception as e:
                logger.warning(f"Failed to generate preview for {file.filename}: {e}")
                name_pairs.append((file.filename, file.filename))

        return name_pairs

    def _update_preview_map_with_new_names(self, name_pairs: List[Tuple[str, str]]) -> None:
        """Update preview map with new names."""
        for old_name, new_name in name_pairs:
            if old_name != new_name:
                file_item = self.preview_map.get(old_name)
                if file_item:
                    self.preview_map[new_name] = file_item

    def _is_valid_filename_text(self, basename: str) -> bool:
        """Validate filename text."""
        try:
            from utils.validate_filename_text import is_valid_filename_text
            return is_valid_filename_text(basename)
        except ImportError:
            return True

    def get_preview_map(self) -> Dict[str, FileItem]:
        """Get the current preview map."""
        return self.preview_map.copy()

    def clear_preview_map(self) -> None:
        """Clear the preview map."""
        self.preview_map.clear()

    def clear_cache(self) -> None:
        """Clear the preview cache."""
        self._preview_cache.clear()
        self._cache_timestamp = 0

    def clear_all_caches(self) -> None:
        """Clear all caches used by the preview system."""
        # Clear preview cache
        self.clear_cache()

        # Clear module cache
        from utils.preview_engine import clear_module_cache
        clear_module_cache()

        # Clear metadata cache
        from modules.metadata_module import MetadataModule
        MetadataModule.clear_cache()

        logger.debug("[PreviewManager] All caches cleared", extra={"dev_only": True})

    def compute_max_filename_width(self, file_list: List[FileItem]) -> int:
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

        logger.debug(f'Longest filename length: {max_len} chars -> width: {clamped_width} px (clamped)')
        return clamped_width

    def update_status_from_preview(self, status_html: str) -> None:
        """Update the status label from preview widget status updates."""
        if self.parent_window and hasattr(self.parent_window, 'status_manager'):
            self.parent_window.status_manager.update_status_from_preview(status_html)

    def get_identity_name_pairs(self, file_list: List[FileItem]) -> List[Tuple[str, str]]:
        """Generate identity name pairs (filename -> filename) for given files."""
        return [(file.filename, file.filename) for file in file_list]

    def update_preview_tables_from_pairs(self, name_pairs: List[Tuple[str, str]]) -> None:
        """
        Updates all three preview tables using the PreviewTablesView.

        Args:
            name_pairs: List of (old_name, new_name) pairs generated during preview generation.
        """
        if not self.parent_window:
            logger.warning("[PreviewManager] No parent window available for preview table updates")
            return

        # Delegate to the preview tables view
        if hasattr(self.parent_window, 'preview_tables_view'):
            self.parent_window.preview_tables_view.update_from_pairs(
                name_pairs,
                getattr(self.parent_window, 'preview_icons', {}),
                getattr(self.parent_window, 'icon_paths', {})
            )
        else:
            logger.warning("[PreviewManager] Preview tables view not available")

    def _needs_hash_calculation(self, modules_data: List[Dict[str, Any]], selected_files: List[FileItem]) -> bool:
        """
        Check if any hash modules are used and if selected files need hash calculation.

        Returns:
            bool: True if hash calculation is needed, False otherwise
        """
        # Check if any modules are hash modules
        has_hash_modules = False
        for module in modules_data:
            if module.get("type") == "metadata" and module.get("category") == "hash":
                has_hash_modules = True
                break

        if not has_hash_modules:
            return False

        # Check if any selected files don't have hashes
        try:
            from core.persistent_hash_cache import get_persistent_hash_cache
            hash_cache = get_persistent_hash_cache()

            files_without_hash = 0
            for file_item in selected_files:
                if not hash_cache.has_hash(file_item.full_path, "CRC32"):
                    files_without_hash += 1

            if files_without_hash > 0:
                return True
            else:
                return False

        except Exception as e:
            return False

        return False

    def _ask_user_for_hash_calculation(self, selected_files: List[FileItem]) -> bool:
        """
        Ask user if they want to calculate missing hashes.

        Args:
            selected_files: List of selected files

        Returns:
            bool: True if user wants to proceed, False if cancelled
        """
        try:
            from widgets.custom_message_dialog import CustomMessageDialog
            from core.persistent_hash_cache import get_persistent_hash_cache

            # Count files that need hash calculation
            hash_cache = get_persistent_hash_cache()
            files_without_hash = 0
            for file_item in selected_files:
                if not hash_cache.has_hash(file_item.full_path, "CRC32"):
                    files_without_hash += 1

            message = f"Some selected files don't have calculated hash values ({files_without_hash} out of {len(selected_files)} files).\n\nCalculating hashes may take some time depending on file sizes.\n\nWould you like to calculate the missing hashes now?"

            dialog = CustomMessageDialog(
                title="Hash calculation required",
                message=message,
                buttons=["Calculate Hashes", "Cancel"],
                parent=self.parent_window if self.parent_window else None
            )

            dialog.exec_()

            if dialog.selected == "Calculate Hashes":
                # Start hash calculation
                self._start_hash_calculation(selected_files)

                # Don't wait here - let the hash calculation run in background
                # The preview will be regenerated when hash calculation completes
                return True
            else:
                return False

        except Exception as e:
            return False

    def _start_hash_calculation(self, selected_files: List[FileItem]) -> None:
        """
        Start hash calculation for selected files that don't have hashes.

        Args:
            selected_files: List of files to calculate hashes for
        """
        try:
            # Filter files that don't have hashes
            from core.persistent_hash_cache import get_persistent_hash_cache
            hash_cache = get_persistent_hash_cache()

            files_without_hash = []
            for file_item in selected_files:
                if not hash_cache.has_hash(file_item.full_path, "CRC32"):
                    files_without_hash.append(file_item)

            if not files_without_hash:
                return

            # Start hash calculation using the existing system
            if self.parent_window:
                # Try to use ApplicationService if available
                if hasattr(self.parent_window, "application_service"):
                    self.parent_window.application_service.calculate_hash_selected()
                # Fallback to EventHandlerManager
                elif hasattr(self.parent_window, "event_handler_manager"):
                    self.parent_window.event_handler_manager._handle_calculate_hashes(selected_files)
                # Fallback to UnifiedMetadataManager
                elif hasattr(self.parent_window, "unified_metadata_manager"):
                    self.parent_window.unified_metadata_manager.load_hashes_for_files(
                        files_without_hash, source="preview_manager_hash_calculation"
                    )
                # Final fallback to DirectMetadataLoader
                elif hasattr(self.parent_window, "direct_metadata_loader"):
                    self.parent_window.direct_metadata_loader.load_hashes_for_files(
                        files_without_hash, source="preview_manager_hash_calculation"
                    )

        except Exception as e:
            pass

    def on_hash_calculation_completed(self) -> None:
        """
        Called when hash calculation is completed.
        Triggers preview regeneration if hash modules are active.
        """
        try:
            if not self.parent_window:
                return

            # Check if any hash modules are currently active
            rename_data = self.parent_window.rename_modules_area.get_all_data()
            modules_data = rename_data.get("modules", [])

            has_hash_modules = False
            for module in modules_data:
                if module.get("type") == "metadata" and module.get("category") == "hash":
                    has_hash_modules = True
                    break

            if has_hash_modules:
                # Trigger preview regeneration
                if hasattr(self.parent_window, "utility_manager"):
                    self.parent_window.utility_manager.generate_preview_names()

        except Exception as e:
            pass
