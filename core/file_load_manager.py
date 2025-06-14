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
from widgets.compact_waiting_widget import CompactWaitingWidget

logger = get_cached_logger(__name__)


class FileLoadManager:
    """
    Manages file loading operations with support for both synchronous and threaded loading.
    Handles drag & drop, folder loading, and metadata integration.
    """

    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.waiting_widget = None
        self.allowed_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ts', '.mts', '.m2ts'}

    def _count_files_in_folder(self, folder_path: str, recursive: bool = False) -> int:
        """
        Count total number of valid files in folder.
        Returns accurate count for progress bar.
        """
        count = 0
        for root, _, filenames in os.walk(folder_path):
            if not recursive and root != folder_path:
                continue
            count += sum(1 for f in filenames if os.path.splitext(f)[1].lower()[1:] in ALLOWED_EXTENSIONS)
        return count

    def _get_files_from_folder(self, folder_path: str, recursive: bool = False) -> List[str]:
        """
        Get list of valid file paths from folder.
        Returns list of full paths.
        """
        files = []
        for root, _, filenames in os.walk(folder_path):
            if not recursive and root != folder_path:
                continue
            for filename in filenames:
                if os.path.splitext(filename)[1].lower()[1:] in ALLOWED_EXTENSIONS:
                    full_path = os.path.join(root, filename)
                    files.append(full_path)
        return files

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """
        Prepare folder for loading by checking contents and permissions.
        Returns list of file paths to load.
        """
        if not os.path.isdir(folder_path):
            logger.error(f"[FileLoadManager] Path is not a directory: {folder_path}")
            return []

        # Get all files in folder
        return self._get_files_from_folder(folder_path)

    def load_single_item_from_drop(self, path: str, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Load a single item (file or folder) from drag & drop.
        Handles both files and folders with proper modifier support.
        """
        logger.info(f"[Drop] Loading single item: {path}")

        if os.path.isdir(path):
            # Handle folder drop
            self.load_files_from_paths([path], clear=True)

            # Apply modifier logic
            ctrl = bool(modifiers & Qt.ControlModifier)
            shift = bool(modifiers & Qt.ShiftModifier)
            skip_metadata = not ctrl
            use_extended = ctrl and shift

            logger.debug(f"[Drop] Folder: ctrl={ctrl}, shift={shift} → skip={skip_metadata}, extended={use_extended}")

            if not skip_metadata:
                items = self.parent_window.file_model.files
                self.parent_window.load_metadata_for_items(
                    items,
                    use_extended=use_extended,
                    source="folder_drop"
                )
        else:
            # Handle single file drop
            self.load_files_from_paths([path], clear=True)

            # Apply modifier logic
            ctrl = bool(modifiers & Qt.ControlModifier)
            shift = bool(modifiers & Qt.ShiftModifier)
            skip_metadata = not ctrl
            use_extended = ctrl and shift

            logger.debug(f"[Drop] File: ctrl={ctrl}, shift={shift} → skip={skip_metadata}, extended={use_extended}")

            if not skip_metadata:
                items = self.parent_window.file_model.files
                self.parent_window.load_metadata_for_items(
                    items,
                    use_extended=use_extended,
                    source="file_drop"
                )

    def load_files_from_paths(self, paths: List[str], clear: bool = False) -> None:
        """
        Load files from the given paths using a worker thread.
        Shows a progress dialog and allows cancellation.
        """
        try:
            items = []
            for path in paths:
                if os.path.isfile(path):
                    if self._is_allowed_extension(path):
                        extension = os.path.splitext(path)[1].lower()
                        modified = datetime.fromtimestamp(os.path.getmtime(path))
                        items.append(FileItem(path, extension, modified))
                else:
                    for root, _, files in os.walk(path):
                        for file in files:
                            if self._is_allowed_extension(file):
                                full_path = os.path.join(root, file)
                                extension = os.path.splitext(file)[1].lower()
                                modified = datetime.fromtimestamp(os.path.getmtime(full_path))
                                items.append(FileItem(full_path, extension, modified))

            if items:
                # TODO: Update UI with loaded items
                logger.info(f"Loaded {len(items)} files")
            else:
                logger.warning("No files found with allowed extensions")

        except Exception as e:
            logger.error(f"Error loading files: {str(e)}")
            raise

    def _is_allowed_extension(self, path: str) -> bool:
        """Check if file has an allowed extension."""
        ext = os.path.splitext(path)[1].lower()
        return ext in self.allowed_extensions

    def set_allowed_extensions(self, extensions: Set[str]) -> None:
        """Update the set of allowed file extensions."""
        self.allowed_extensions = extensions

    def _update_ui_after_load(self, items: List[FileItem]) -> None:
        """Update UI elements after loading files."""
        if not hasattr(self.parent_window, "file_model"):
            return

        # Update preview map
        self.parent_window.preview_map = {f.filename: f for f in items}

        # Configure sorting and header
        self.parent_window.file_table_view.setSortingEnabled(True)
        if hasattr(self.parent_window, "header"):
            self.parent_window.header.setSectionsClickable(True)
            self.parent_window.header.setSortIndicatorShown(True)
            self.parent_window.header.setEnabled(True)

        # Sort and update UI
        self.parent_window.file_table_view.sortByColumn(1, Qt.AscendingOrder)
        self.parent_window.file_table_view.set_placeholder_visible(len(items) == 0)
        self.parent_window.file_table_view.scrollToTop()
        self.parent_window.update_preview_tables_from_pairs([])
        self.parent_window.update_files_label()

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
        self.parent_window.load_metadata_for_items(file_items, use_extended=use_extended, source="dropped_files")

    def load_files_from_dropped_items(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Called when user drops files or folders onto file table view.
        Imports the dropped files into the current view.
        """
        if not paths:
            logger.info("[Drop] No files dropped in table.")
            return

        logger.info(f"[Drop] {len(paths)} file(s)/folder(s) dropped in table view")

        if len(paths) == 1 and os.path.isdir(paths[0]):
            folder_path = paths[0]
            logger.info(f"[Drop] Setting folder from drop: {folder_path}")

            # Use passed modifiers (from drag start) instead of current state
            self.parent_window.modifier_state = modifiers if modifiers != Qt.NoModifier else QApplication.keyboardModifiers()

            # Use safe casting via helper method
            skip_metadata, use_extended = self.parent_window.determine_metadata_mode()
            logger.debug(f"[Drop] Using stored modifiers: {modifiers}, skip_metadata={skip_metadata}, use_extended={use_extended}")

            self.parent_window.force_extended_metadata = use_extended
            self.parent_window.skip_metadata_mode = skip_metadata

            logger.debug(f"[Drop] skip_metadata={skip_metadata}, use_extended={use_extended}")

            # Centralized loading logic
            self.prepare_folder_load(folder_path)

            # Get loaded items (from self.file_model or retrieved from paths if needed)
            items = self.parent_window.file_model.files

            if not self.parent_window.skip_metadata_mode:
                self.parent_window.load_metadata_for_items(
                    items,
                    use_extended=self.parent_window.force_extended_metadata,
                    source="folder_drop"
                )

            # Update folder tree selection (UI logic)
            if hasattr(self.parent_window.dir_model, "index"):
                index = self.parent_window.dir_model.index(folder_path)
                self.parent_window.folder_tree.setCurrentIndex(index)

            # Trigger label update and ensure repaint
            self.parent_window.file_table_view.viewport().update()
            self.parent_window.update_files_label()
        else:
            # Load directly dropped files with modifier support
            self.load_files_from_paths(paths, clear=True)

            # Apply modifier logic for individual files
            ctrl = bool(modifiers & Qt.ControlModifier)
            shift = bool(modifiers & Qt.ShiftModifier)
            skip_metadata = not ctrl
            use_extended = ctrl and shift

            logger.debug(f"[Drop] Individual files: ctrl={ctrl}, shift={shift} → skip={skip_metadata}, extended={use_extended}")

            # Define selection function to call after metadata loading (or immediately if skipping)
            def select_dropped_files():
                logger.warning(f"[Drop] *** CALLING select_dropped_files with {len(paths)} paths ***")
                self.parent_window.file_table_view.select_dropped_files(paths)

            # Load metadata if not skipping
            if not skip_metadata:
                items = self.parent_window.file_model.files
                self.parent_window.load_metadata_for_items(
                    items,
                    use_extended=use_extended,
                    source="file_drop"
                )
            else:
                # If skipping metadata, just select the files
                select_dropped_files()

    def _handle_folder_drop(self, folder_path: str, merge_mode: bool, recursive: bool) -> None:
        """Handle folder drop with merge/replace and recursive options"""
        self.parent_window.file_loader.handle_folder_drop(folder_path, merge_mode, recursive)

    def _handle_file_drop(self, file_path: str, merge_mode: bool) -> None:
        """Handle single file drop with merge/replace options"""
        self.parent_window.file_loader.handle_file_drop(file_path, merge_mode)

    def reload_current_folder(self) -> None:
        """Reload the current folder if one is loaded"""
        # Optional: adjust if flags need to be preserved
        if self.parent_window.current_folder_path:
            self.load_files_from_folder(self.parent_window.current_folder_path, skip_metadata=False)
            self.parent_window.sort_by_column(1, Qt.AscendingOrder)
