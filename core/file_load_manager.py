"""
file_load_manager.py

Author: Michael Economou
Date: 2025-05-01

Manages file loading operations with support for both synchronous and threaded loading.
Handles drag & drop, folder loading, and metadata integration.
"""

import os
from typing import List, Optional, Tuple, Set
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from config import ALLOWED_EXTENSIONS
from models.file_item import FileItem
from utils.cursor_helper import wait_cursor
from utils.logger_factory import get_cached_logger
from widgets.file_loading_dialog import FileLoadingDialog

logger = get_cached_logger(__name__)


class FileLoadManager:
    """
    Manages file loading operations with support for both synchronous and threaded loading.
    Handles drag & drop, folder loading, and metadata integration.
    """

    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.allowed_extensions = set(ALLOWED_EXTENSIONS)

    def handle_folder_drop(self, folder_path: str, merge_mode: bool = False, recursive: bool = False) -> None:
        """
        Handle folder drop with merge/replace and recursive options.
        Shows progress dialog only for recursive operations to avoid flashing.
        """
        logger.info(f"[FileLoadManager] handle_folder_drop: {folder_path} (merge={merge_mode}, recursive={recursive})")

        if not os.path.isdir(folder_path):
            logger.error(f"Path is not a directory: {folder_path}")
            return

        # Clear any drag cursor immediately to show we're processing
        if hasattr(self.parent_window, 'setCursor'):
            self.parent_window.setCursor(Qt.ArrowCursor)

        if recursive:
            # Recursive operations: show progress dialog for user feedback
            # Create callback to handle loaded files
            def on_files_loaded(file_paths: List[str]):
                logger.info(f"[FileLoadManager] Loaded {len(file_paths)} files from folder")
                self._update_ui_with_files(file_paths, clear=not merge_mode)

            # Show loading dialog and start worker
            dialog = FileLoadingDialog(self.parent_window, on_files_loaded)
            dialog.load_files_with_options([folder_path], self.allowed_extensions, recursive=recursive)
            dialog.exec_()
        else:
            # Non-recursive operations: simple synchronous loading with wait cursor
            with wait_cursor():
                file_paths = self._get_files_from_folder(folder_path, recursive=False)
                self._update_ui_with_files(file_paths, clear=not merge_mode)

    def load_single_item_from_drop(self, path: str, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Handle loading a single item from drag & drop with proper modifier support.

        Modifier behavior:
        - No modifier: Simple import (no progress bar, no metadata)
        - Ctrl: Recursive import (no metadata)
        - Shift: Merge with existing files (no metadata)
        - Ctrl+Shift: Recursive + Merge (no metadata)
        """
        logger.info(f"[FileLoadManager] load_single_item_from_drop: {path}")

        # Parse modifiers
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
        recursive = ctrl
        merge_mode = shift

        logger.debug(f"[Drop] Modifiers: ctrl={ctrl}, shift={shift} → recursive={recursive}, merge={merge_mode}")

        if os.path.isdir(path):
            # Handle folder drop
            self.handle_folder_drop(path, merge_mode=merge_mode, recursive=recursive)
        else:
            # Handle single file drop
            if merge_mode:
                # Add to existing files
                file_paths = [path] if self._is_allowed_extension(path) else []
                self._update_ui_with_files(file_paths, clear=False)
            else:
                # Replace existing files
                file_paths = [path] if self._is_allowed_extension(path) else []
                self._update_ui_with_files(file_paths, clear=True)

        # No automatic metadata loading - metadata should be loaded separately
        logger.debug(f"[Metadata] Automatic metadata loading disabled for drag & drop")

    def load_files_from_paths(self, paths: List[str], clear: bool = True) -> None:
        """
        Load files from the given paths using worker thread.
        Shows progress dialog and updates UI.
        """
        logger.info(f"[FileLoadManager] load_files_from_paths: {len(paths)} paths")

        # Create callback to handle loaded files
        def on_files_loaded(file_paths: List[str]):
            logger.info(f"[FileLoadManager] Loaded {len(file_paths)} files from paths")
            self._update_ui_with_files(file_paths, clear=clear)

        # Show loading dialog and start worker
        dialog = FileLoadingDialog(self.parent_window, on_files_loaded)
        dialog.load_files(paths, self.allowed_extensions)
        dialog.exec_()

    def load_files_from_dropped_items(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Called when user drops files or folders onto file table view.
        Imports the dropped files into the current view with proper modifier support.
        """
        if not paths:
            logger.info("[Drop] No files dropped in table.")
            return

        logger.info(f"[Drop] {len(paths)} file(s)/folder(s) dropped in table view")

        # Parse modifiers
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
        recursive = ctrl
        merge_mode = shift

        logger.debug(f"[Drop] Table modifiers: ctrl={ctrl}, shift={shift} → recursive={recursive}, merge={merge_mode}")

        # Process each dropped item
        all_file_paths = []
        for path in paths:
            if os.path.isfile(path):
                if self._is_allowed_extension(path):
                    all_file_paths.append(path)
            elif os.path.isdir(path):
                folder_files = self._get_files_from_folder(path, recursive)
                all_file_paths.extend(folder_files)

        # Update UI with all collected files
        if all_file_paths:
            self._update_ui_with_files(all_file_paths, clear=not merge_mode)

        # No automatic metadata loading - metadata should be loaded separately
        logger.debug(f"[Metadata] Automatic metadata loading disabled for table drops")

    def load_metadata_from_dropped_files(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Called when user drops files onto metadata tree.
        Maps filenames to FileItem objects and triggers forced metadata loading.
        """
        file_items = []
        for path in paths:
            filename = os.path.basename(path)
            file = next((f for f in self.parent_window.file_model.files if f.filename == filename), None)
            if file:
                file_items.append(file)

        if not file_items:
            logger.info("[Drop] No matching files found in table.")
            return

        # New logic for FileTable → MetadataTree drag:
        # - No modifiers: fast metadata (normal metadata loading)
        # - Shift: extended metadata
        shift = bool(modifiers & Qt.ShiftModifier)
        use_extended = shift

        logger.debug(f"[Modifiers] File drop on metadata tree: shift={shift} → extended={use_extended}")

        # Always load metadata (no skip option for metadata tree drops)
        if hasattr(self.parent_window, 'load_metadata_for_items'):
            self.parent_window.load_metadata_for_items(file_items, use_extended=use_extended, source="dropped_files")

    def _count_files_in_folder(self, folder_path: str, recursive: bool = False) -> int:
        """
        Count total number of valid files in folder.
        Returns accurate count for progress bar decision.
        """
        count = 0
        if recursive:
            for root, _, filenames in os.walk(folder_path):
                count += sum(1 for f in filenames if self._is_allowed_extension(f))
        else:
            try:
                filenames = os.listdir(folder_path)
                count = sum(1 for f in filenames if self._is_allowed_extension(f))
            except OSError:
                count = 0
        return count

    def _get_files_from_folder(self, folder_path: str, recursive: bool = False) -> List[str]:
        """
        Get list of valid file paths from folder.
        Returns list of full paths.
        """
        files = []
        if recursive:
            for root, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    if self._is_allowed_extension(filename):
                        full_path = os.path.join(root, filename)
                        files.append(full_path)
        else:
            try:
                filenames = os.listdir(folder_path)
                for filename in filenames:
                    if self._is_allowed_extension(filename):
                        full_path = os.path.join(folder_path, filename)
                        if os.path.isfile(full_path):
                            files.append(full_path)
            except OSError:
                pass
        return files

    def _is_allowed_extension(self, path: str) -> bool:
        """Check if file has an allowed extension."""
        ext = os.path.splitext(path)[1].lower()
        # Remove the dot from extension for comparison
        if ext.startswith('.'):
            ext = ext[1:]
        return ext in self.allowed_extensions

    def _update_ui_with_files(self, file_paths: List[str], clear: bool = True) -> None:
        """
        Update UI with loaded files.
        Creates FileItem objects and updates the file model.
        """
        try:
            # Create FileItem objects
            items = []
            for path in file_paths:
                if os.path.isfile(path):
                    extension = os.path.splitext(path)[1].lower()
                    modified = datetime.fromtimestamp(os.path.getmtime(path))
                    items.append(FileItem(path, extension, modified))

            if not items:
                logger.warning("No valid files to add to UI")
                return

            # Update file model
            if hasattr(self.parent_window, "file_model"):
                if clear:
                    self.parent_window.file_model.clear()
                self.parent_window.file_model.add_files(items)

            # Update UI elements
            self._update_ui_after_load(items)

        except Exception as e:
            logger.error(f"Error updating UI with files: {str(e)}")
            raise

    def _update_ui_after_load(self, items: List[FileItem]) -> None:
        """Update UI elements after loading files."""
        if not hasattr(self.parent_window, "file_model"):
            return

        # Update preview map
        if hasattr(self.parent_window, 'preview_map'):
            self.parent_window.preview_map = {f.filename: f for f in items}

        # Configure sorting and header
        if hasattr(self.parent_window, 'file_table_view'):
            self.parent_window.file_table_view.setSortingEnabled(True)

            if hasattr(self.parent_window, "header"):
                self.parent_window.header.setSectionsClickable(True)
                self.parent_window.header.setSortIndicatorShown(True)
                self.parent_window.header.setEnabled(True)

            # Sort and update UI
            self.parent_window.file_table_view.sortByColumn(1, Qt.AscendingOrder)
            self.parent_window.file_table_view.set_placeholder_visible(len(items) == 0)
            self.parent_window.file_table_view.scrollToTop()

            # Update viewport
            self.parent_window.file_table_view.viewport().update()

        # Update preview tables and labels
        if hasattr(self.parent_window, 'update_preview_tables_from_pairs'):
            self.parent_window.update_preview_tables_from_pairs([])

        if hasattr(self.parent_window, 'update_files_label'):
            self.parent_window.update_files_label()

        logger.info(f"[FileLoadManager] UI updated with {len(items)} files")

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """
        Prepare folder for loading by checking contents and permissions.
        Returns list of file paths to load.
        """
        if not os.path.isdir(folder_path):
            logger.error(f"[FileLoadManager] Path is not a directory: {folder_path}")
            return []

        # Get all files in folder (non-recursive by default)
        return self._get_files_from_folder(folder_path, recursive=False)

    def reload_current_folder(self) -> None:
        """Reload the current folder if one is loaded"""
        if hasattr(self.parent_window, 'current_folder_path') and self.parent_window.current_folder_path:
            self.handle_folder_drop(self.parent_window.current_folder_path, merge_mode=False, recursive=False)

    def set_allowed_extensions(self, extensions: Set[str]) -> None:
        """Update the set of allowed file extensions."""
        self.allowed_extensions = extensions
