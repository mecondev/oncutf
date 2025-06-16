"""
preview_manager.py

Author: Michael Economou
Date: 2025-06-13

Manages preview name generation for rename operations.
Extracted from MainWindow to separate business logic from UI.
"""

import os
from typing import List, Tuple, Dict, Any

from core.qt_imports import QElapsedTimer
from models.file_item import FileItem
from modules.name_transform_module import NameTransformModule
from utils.cursor_helper import wait_cursor
from utils.logger_factory import get_cached_logger
from utils.preview_engine import apply_rename_modules

logger = get_cached_logger(__name__)


class PreviewManager:
    """Manages preview name generation for rename operations."""

    def __init__(self, parent_window=None):
        """Initialize PreviewManager with reference to parent window."""
        self.parent_window = parent_window
        self.preview_map: Dict[str, FileItem] = {}
        logger.debug("[PreviewManager] Initialized", extra={"dev_only": True})

    def generate_preview_names(
        self,
        selected_files: List[FileItem],
        rename_data: Dict[str, Any],
        metadata_cache: Any,
        all_modules: List[Any]
    ) -> Tuple[List[Tuple[str, str]], bool]:
        """Generate preview names for selected files."""
        with wait_cursor():
            timer = QElapsedTimer()
            timer.start()

            if not selected_files:
                return [], False

            modules_data = rename_data.get("modules", [])
            post_transform = rename_data.get("post_transform", {})

            # Check if all modules are no-op
            is_noop = self._check_if_noop(all_modules, post_transform)
            self.preview_map = {file.filename: file for file in selected_files}

            if is_noop:
                if not all_modules and not NameTransformModule.is_effective(post_transform):
                    return [], False
                else:
                    name_pairs = [(f.filename, f.filename) for f in selected_files]
                    return name_pairs, False

            name_pairs = self._generate_name_pairs(selected_files, modules_data, post_transform, metadata_cache)
            self._update_preview_map_with_new_names(name_pairs)

            elapsed = timer.elapsed()
            logger.debug(f"[Performance] generate_preview_names took {elapsed} ms", extra={"dev_only": True})

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
        """Generate name pairs by applying modules."""
        name_pairs = []
        for idx, file in enumerate(selected_files):
            try:
                basename, extension = os.path.splitext(file.filename)
                new_fullname = apply_rename_modules(modules_data, idx, file, metadata_cache)

                if extension and new_fullname.lower().endswith(extension.lower()):
                    new_basename = new_fullname[:-(len(extension))]
                else:
                    new_basename = new_fullname

                if NameTransformModule.is_effective(post_transform):
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
            from utils.validation import is_valid_filename_text
            return is_valid_filename_text(basename)
        except ImportError:
            return True

    def get_preview_map(self) -> Dict[str, FileItem]:
        """Get the current preview map."""
        return self.preview_map.copy()

    def clear_preview_map(self) -> None:
        """Clear the preview map."""
        self.preview_map.clear()

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
