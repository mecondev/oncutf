"""
file_load_manager.py

Author: Michael Economou
Date: 2025-05-01

Manages file loading operations with support for both synchronous and threaded loading.
Handles drag & drop, folder loading, and metadata integration.
Uses UnifiedFileLoader for advanced scenarios and FileLoadingDialog for simple cases.
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
from core.unified_file_loader import UnifiedFileLoader

logger = get_cached_logger(__name__)


class FileLoadManager:
    """
    Manages file loading operations with support for both synchronous and threaded loading.
    Handles drag & drop, folder loading, and metadata integration.
    Now supports both FileLoadingDialog and UnifiedFileLoader for different scenarios.

    Features:
    - Automatic mode selection based on operation complexity
    - Support for both FileLoadingDialog and UnifiedFileLoader
    - Drag & drop with modifier key support
    - Recursive and non-recursive folder scanning
    """

    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.allowed_extensions = set(ALLOWED_EXTENSIONS)

        # Initialize unified file loader for advanced scenarios
        self.unified_loader = UnifiedFileLoader(parent_window)
        if hasattr(self.unified_loader, 'files_loaded'):
            self.unified_loader.files_loaded.connect(self._on_unified_files_loaded)
        if hasattr(self.unified_loader, 'loading_failed'):
            self.unified_loader.loading_failed.connect(self._on_unified_loading_failed)

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
        Load files from the given paths using FileLoadingDialog.
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

    def load_files_from_paths_legacy(self, paths: List[str], clear: bool = True) -> None:
        """
        Legacy method using FileLoadingDialog directly.
        Kept for compatibility with existing code.
        """
        logger.info(f"[FileLoadManager] load_files_from_paths_legacy: {len(paths)} paths")

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

    def load_files_with_unified_loader(self, paths: List[str], clear: bool = True, recursive: bool = False) -> None:
        """
        Load files using UnifiedFileLoader for automatic mode selection.
        Alternative to the standard FileLoadingDialog approach.
        """
        logger.info(f"[FileLoadManager] load_files_with_unified_loader: {len(paths)} paths")

        # Use UnifiedFileLoader for automatic mode selection
        self.unified_loader.load_files(
            paths,
            recursive=recursive,
            completion_callback=lambda files: self._update_ui_with_files(files, clear=clear)
        )

    def _on_unified_files_loaded(self, file_paths: List[str]) -> None:
        """Handle files loaded by UnifiedFileLoader."""
        logger.info(f"[FileLoadManager] UnifiedFileLoader loaded {len(file_paths)} files")

    def _on_unified_loading_failed(self, error_msg: str) -> None:
        """Handle loading failure from UnifiedFileLoader."""
        logger.error(f"[FileLoadManager] UnifiedFileLoader failed: {error_msg}")

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
                pass
        return count

    def _get_files_from_folder(self, folder_path: str, recursive: bool = False) -> List[str]:
        """
        Get all valid files from folder.
        Returns list of file paths.
        """
        file_paths = []
        if recursive:
            for root, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    if self._is_allowed_extension(filename):
                        file_paths.append(os.path.join(root, filename))
        else:
            try:
                for filename in os.listdir(folder_path):
                    if self._is_allowed_extension(filename):
                        full_path = os.path.join(folder_path, filename)
                        if os.path.isfile(full_path):
                            file_paths.append(full_path)
            except OSError:
                pass
        return file_paths

    def _is_allowed_extension(self, path: str) -> bool:
        """Check if file has allowed extension."""
        ext = os.path.splitext(path)[1].lower()
        if ext.startswith('.'):
            ext = ext[1:]
        return ext in self.allowed_extensions

    def _update_ui_with_files(self, file_paths: List[str], clear: bool = True) -> None:
        """
        Update UI with loaded files.
        Converts file paths to FileItem objects and updates the model.
        """
        if not file_paths:
            logger.info("[FileLoadManager] No files to update UI with")
            return

        logger.info(f"[FileLoadManager] Updating UI with {len(file_paths)} files (clear={clear})")

        # Convert file paths to FileItem objects
        file_items = []
        for path in file_paths:
            try:
                file_item = FileItem(path)
                file_items.append(file_item)
            except Exception as e:
                logger.error(f"Error creating FileItem for {path}: {e}")

        if not file_items:
            logger.warning("[FileLoadManager] No valid FileItem objects created")
            return

        # Update the model
        self._update_ui_after_load(file_items, clear=clear)

    def _update_ui_after_load(self, items: List[FileItem], clear: bool = True) -> None:
        """
        Update UI after loading files.
        Handles model updates and UI refresh.
        """
        if not hasattr(self.parent_window, 'file_model'):
            logger.error("[FileLoadManager] Parent window has no file_model attribute")
            return

        try:
            if clear:
                # Replace existing files
                self.parent_window.file_model.set_files(items)
                logger.info(f"[FileLoadManager] Replaced files with {len(items)} new items")
            else:
                # Add to existing files
                existing_files = self.parent_window.file_model.files
                combined_files = existing_files + items
                self.parent_window.file_model.set_files(combined_files)
                logger.info(f"[FileLoadManager] Added {len(items)} items to existing {len(existing_files)} files")

            # Update UI elements
            if hasattr(self.parent_window, 'update_ui_after_file_load'):
                self.parent_window.update_ui_after_file_load()

        except Exception as e:
            logger.error(f"[FileLoadManager] Error updating UI: {e}")

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """
        Prepare folder for loading by getting file list.
        Returns list of file paths without loading them into UI.
        """
        logger.info(f"[FileLoadManager] prepare_folder_load: {folder_path}")
        return self._get_files_from_folder(folder_path, recursive=False)

    def reload_current_folder(self) -> None:
        """Reload the current folder if available."""
        logger.info("[FileLoadManager] reload_current_folder called")
        # Implementation depends on how current folder is tracked

    def set_allowed_extensions(self, extensions: Set[str]) -> None:
        """Update the set of allowed file extensions."""
        self.allowed_extensions = extensions
        if self.unified_loader:
            self.unified_loader.allowed_extensions = extensions
        logger.info(f"[FileLoadManager] Updated allowed extensions: {extensions}")
