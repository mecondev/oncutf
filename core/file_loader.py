"""
file_loader.py

Author: Michael Economou
Date: 2025-01-27

Centralized file loading operations extracted from MainWindow.
Handles folder scanning, file filtering, and drop operations.
"""

import os
from typing import List, Optional

from core.config_imports import ALLOWED_EXTENSIONS, LARGE_FOLDER_WARNING_THRESHOLD
from core.modifier_handler import decode_modifiers_to_flags
from core.qt_imports import Qt, QTimer
from models.file_item import FileItem
from utils.cursor_helper import wait_cursor
from utils.logger_helper import get_logger

logger = get_logger(__name__)


class FileLoader:
    """
    Centralized file loading operations.

    Handles:
    - Folder scanning and file filtering
    - Drop operations with modifier logic
    - File path validation and processing
    """

    def __init__(self, parent_window=None):
        """Initialize FileLoader with optional parent window reference."""
        self.parent_window = parent_window

    def get_file_items_from_folder(self, folder_path: str) -> List[FileItem]:
        """
        Get FileItem objects from a folder path.
        Filters files by allowed extensions.
        """
        if not folder_path or not os.path.exists(folder_path):
            return []

        file_items = []
        try:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)

                if os.path.isfile(item_path):
                    # Check extension
                    _, ext = os.path.splitext(item_path)
                    if ext.startswith('.'):
                        ext = ext[1:].lower()

                    if ext in ALLOWED_EXTENSIONS:
                        file_item = FileItem(item_path)
                        file_items.append(file_item)

        except (OSError, PermissionError) as e:
            logger.error(f"Error reading folder {folder_path}: {e}")

        return file_items

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> List[str]:
        """
        Prepare folder loading by getting file paths.

        Args:
            folder_path: Path to the folder to scan
            clear: Whether to clear existing files (for UI operations)

        Returns:
            List of file paths found in the folder
        """
        if not folder_path or not os.path.exists(folder_path):
            logger.warning(f"Invalid folder path: {folder_path}")
            return []

        # Get file items and extract paths
        file_items = self.get_file_items_from_folder(folder_path)
        file_paths = [item.full_path for item in file_items]

        logger.info(f"[FileLoader] Prepared {len(file_paths)} files from {folder_path}")

        # If we have a parent window, trigger file loading
        if self.parent_window and hasattr(self.parent_window, 'load_files_from_paths'):
            self.parent_window.load_files_from_paths(file_paths, clear=clear)

        return file_paths

    def load_files_from_paths(self, file_paths: List[str], *, clear: bool = True) -> List[FileItem]:
        """
        Load files from a list of file paths and return FileItems.

        Args:
            file_paths: List of file paths to load
            clear: Whether to clear existing files before loading

        Returns:
            List of FileItem objects created from valid paths
        """
        if not file_paths:
            logger.info("[FileLoader] No file paths provided")
            return []

        # Collect new file items (mix of files and folders)
        new_file_items = []
        for path in file_paths:
            if os.path.isdir(path):
                # Extend with folder files
                new_file_items.extend(self.get_file_items_from_folder(path))
            elif os.path.isfile(path):
                # Check extension for individual files
                _, ext = os.path.splitext(path)
                if ext.startswith('.'):
                    ext = ext[1:].lower()

                if ext in ALLOWED_EXTENSIONS:
                    file_item = FileItem(path)
                    new_file_items.append(file_item)

        logger.info(f"[FileLoader] Loading {len(new_file_items)} valid files")

        # Return the file items - let parent window handle UI logic
        return new_file_items

    def has_deep_content(self, folder_path: str) -> bool:
        """Check if folder has any supported files in deeper levels (beyond root)."""
        try:
            for root, dirs, files in os.walk(folder_path):
                if root != folder_path:  # Skip first level
                    for file in files:
                        _, ext = os.path.splitext(file)
                        if ext.startswith('.'):
                            ext = ext[1:].lower()
                        if ext in ALLOWED_EXTENSIONS:
                            return True  # Found supported file in deeper level
            return False
        except (OSError, PermissionError):
            return False  # Assume no content if can't scan

    def handle_folder_drop(self, folder_path: str, merge_mode: bool, recursive: bool) -> None:
        """Handle folder drop with merge/replace and recursive options."""
        logger.debug(f"[FileLoader] Handling folder: {folder_path} (merge={merge_mode}, recursive={recursive})")

        if recursive:
            # Get all files recursively
            file_paths = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Filter by allowed extensions
                    _, ext = os.path.splitext(file_path)
                    if ext.startswith('.'):
                        ext = ext[1:].lower()
                    if ext in ALLOWED_EXTENSIONS:
                        file_paths.append(file_path)

            logger.info(f"[FileLoader] Found {len(file_paths)} files recursively in {folder_path}")
        else:
            # Get files from folder only (shallow)
            file_items = self.get_file_items_from_folder(folder_path)
            file_paths = [item.full_path for item in file_items]

            logger.info(f"[FileLoader] Found {len(file_paths)} files in {folder_path} (shallow)")

        # Handle empty folder scenarios intelligently
        if len(file_paths) == 0:
            if not recursive and self.has_deep_content(folder_path):
                # Folder has no files at root but has content deeper - suggest recursive scan
                if self.parent_window and hasattr(self.parent_window, 'set_status'):
                    self.parent_window.set_status(
                        "Folder has no supported files at root level. Try Ctrl+drag for recursive scan.",
                        color="orange", auto_reset=True
                    )
                logger.info(f"[FileLoader] Folder '{os.path.basename(folder_path)}' has no root-level files but contains deeper content - no action taken")
                return  # No action - leave table as is
            elif not merge_mode:
                # Truly empty folder in replace mode - clear table and show placeholder
                logger.info(f"[FileLoader] Empty folder in replace mode - clearing table")
                if self.parent_window:
                    if hasattr(self.parent_window, 'file_table_view'):
                        self.parent_window.file_table_view.prepare_table([])
                        self.parent_window.file_table_view.set_placeholder_visible(True)
                    if hasattr(self.parent_window, 'files'):
                        self.parent_window.files = []
                    if hasattr(self.parent_window, 'preview_map'):
                        self.parent_window.preview_map = {}
                    if hasattr(self.parent_window, 'update_files_label'):
                        self.parent_window.update_files_label()
                    if hasattr(self.parent_window, 'set_status'):
                        self.parent_window.set_status("Empty folder loaded - table cleared.", color="gray", auto_reset=True)
                return
            else:
                # Empty folder in merge mode - no action
                if self.parent_window and hasattr(self.parent_window, 'set_status'):
                    self.parent_window.set_status("Empty folder ignored in merge mode.", color="gray", auto_reset=True)
                logger.info(f"[FileLoader] Empty folder in merge mode - no action taken")
                return

        # Load files with merge/replace logic (only if we have files)
        if self.parent_window and hasattr(self.parent_window, 'load_files_from_paths'):
            self.parent_window.load_files_from_paths(file_paths, clear=not merge_mode)

        # Update folder tree selection if replace mode
        if (not merge_mode and self.parent_window and
            hasattr(self.parent_window, 'dir_model') and
            hasattr(self.parent_window, 'folder_tree') and
            hasattr(self.parent_window.dir_model, 'index')):
            index = self.parent_window.dir_model.index(folder_path)
            self.parent_window.folder_tree.setCurrentIndex(index)

    def handle_file_drop(self, file_path: str, merge_mode: bool) -> None:
        """Handle single file drop with merge/replace options."""
        logger.debug(f"[FileLoader] Handling file: {file_path} (merge={merge_mode})")

        # Load single file with merge/replace logic
        if self.parent_window and hasattr(self.parent_window, 'load_files_from_paths'):
            self.parent_window.load_files_from_paths([file_path], clear=not merge_mode)

        # Select the dropped file after loading
        if self.parent_window and hasattr(self.parent_window, 'file_table_view'):
            def select_dropped_file():
                self.parent_window.file_table_view.select_dropped_files([file_path])

            QTimer.singleShot(50, select_dropped_file)

    def handle_drop_operation(self, path: str, modifiers: Qt.KeyboardModifiers) -> None:
        """
        Handle drop operation with modifier logic.

        Args:
            path: File or folder path that was dropped
            modifiers: Keyboard modifiers at drop time
        """
        if not path:
            logger.info("[FileLoader] No path provided for drop operation.")
            return

        # Decode modifier combination using centralized logic
        merge_mode, recursive, action_type = decode_modifiers_to_flags(modifiers)

        logger.info(f"[FileLoader] Drop operation: {path} ({action_type})")

        # Use wait cursor for all operations
        with wait_cursor():
            if os.path.isdir(path):
                # Handle folder drop
                self.handle_folder_drop(path, merge_mode, recursive)
            else:
                # Handle single file drop
                self.handle_file_drop(path, merge_mode)

        # Update UI after loading
        if self.parent_window:
            if hasattr(self.parent_window, 'file_table_view'):
                self.parent_window.file_table_view.viewport().update()
            if hasattr(self.parent_window, 'update_files_label'):
                self.parent_window.update_files_label()
            if hasattr(self.parent_window, 'show_metadata_status'):
                self.parent_window.show_metadata_status()

    def should_skip_folder_reload(self, folder_path: str, force: bool = False) -> bool:
        """
        Check if folder reload should be skipped.

        Args:
            folder_path: Path to check
            force: Whether to force reload

        Returns:
            True if reload should be skipped, False otherwise
        """
        if force:
            return False

        # Check if parent window has current folder tracking
        if (self.parent_window and
            hasattr(self.parent_window, 'current_folder_path') and
            self.parent_window.current_folder_path == folder_path):

            # Check if we should show confirmation dialog
            if hasattr(self.parent_window, 'confirm_large_folder'):
                file_items = self.get_file_items_from_folder(folder_path)
                file_paths = [item.full_path for item in file_items]

                if len(file_paths) > LARGE_FOLDER_WARNING_THRESHOLD:
                    return not self.parent_window.confirm_large_folder(file_paths, folder_path)

        return False
