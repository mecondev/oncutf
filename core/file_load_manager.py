"""
file_load_manager.py

Author: Michael Economou
Date: 2025-05-01

Manager for handling file loading operations in the MainWindow.
Consolidates all file loading logic including folder loading, dropped items,
and metadata loading operations.
"""

import os
from typing import Optional, List
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication

from config import STATUS_COLORS
from utils.logger_helper import get_cached_logger

logger = get_cached_logger(__name__)


class FileLoadManager:
    """
    Manager for handling all file loading operations.

    This manager consolidates file loading logic that was previously scattered
    throughout the MainWindow, providing a clean interface for:
    - Loading files from folders
    - Handling dropped files and folders
    - Managing metadata loading operations
    - Preparing file tables and UI updates
    """

    def __init__(self, parent_window):
        """
        Initialize the FileLoadManager.

        Args:
            parent_window: Reference to the MainWindow instance
        """
        self.parent_window = parent_window
        logger.debug("[FileLoadManager] Initialized", extra={"dev_only": True})

    def load_files_from_folder(self, folder_path: str, skip_metadata: bool = False, force: bool = False):
        """
        Load files from the specified folder into the file table.

        Args:
            folder_path: Path to the folder to load files from
            skip_metadata: Whether to skip metadata scanning
            force: Whether to force reload even if folder is already loaded
        """
        normalized_new = os.path.abspath(os.path.normpath(folder_path))
        normalized_current = os.path.abspath(os.path.normpath(self.parent_window.current_folder_path or ""))

        if normalized_new == normalized_current and not force:
            logger.info(f"[FolderLoad] Ignored reload of already loaded folder: {normalized_new}")
            self.parent_window.set_status("Folder already loaded.", color="gray", auto_reset=True)
            return

        logger.info(f"Loading files from folder: {folder_path} (skip_metadata={skip_metadata})")

        # Only skip clearing metadata cache immediately after rename action,
        # and only if metadata scan is explicitly skipped (default fast path).
        # In all other cases, always clear cache to reflect current OS state.
        if not (self.parent_window.last_action == "rename" and skip_metadata):
            self.parent_window.metadata_cache.clear()

        self.parent_window.current_folder_path = folder_path
        self.parent_window.metadata_tree_view.refresh_metadata_from_selection()  # reset metadata tree

        file_items = self.get_file_items_from_folder(folder_path)

        if not file_items:
            self.parent_window.metadata_tree_view.clear_view()
            self.parent_window.header.setEnabled(False)
            self.parent_window.set_status("No supported files found.", color="orange", auto_reset=True)
            return

        self.parent_window.prepare_file_table(file_items)
        self.parent_window.sort_by_column(1, Qt.AscendingOrder)
        self.parent_window.metadata_tree_view.clear_view()

        if skip_metadata:
            self.parent_window.set_status("Metadata scan skipped.", color="gray", auto_reset=True)
            return

        self.parent_window.set_status(f"Loading metadata for {len(file_items)} files...", color=STATUS_COLORS["info"])
        QTimer.singleShot(100, lambda: self.parent_window.start_metadata_scan([f.full_path for f in file_items if f.full_path]))

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """
        Prepares the application state and loads files from the specified folder
        into the file table.

        This helper consolidates common logic used in folder-based file loading
        (e.g., from folder select, browse, or dropped folder).

        Args:
            folder_path (str): Absolute path to the folder to load files from.
            clear (bool): Whether to clear the file table before loading. Defaults to True.

        Returns:
            list[str]: A list of file paths (full paths) that were successfully loaded.
        """
        self.parent_window.clear_file_table("No folder selected")
        self.parent_window.metadata_tree_view.clear_view()
        self.parent_window.current_folder_path = folder_path

        return self.parent_window.file_loader.prepare_folder_load(folder_path, clear=clear)

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
        """
        Loads files from a list of file or folder paths.

        Args:
            file_paths: List of absolute file or folder paths
            clear: Whether to clear existing items before loading (True = replace, False = merge)
        """
        if not file_paths:
            if clear:
                self.parent_window.file_table_view.set_placeholder_visible(True)
            return

        # Use FileLoader to get file items
        new_file_items = self.parent_window.file_loader.load_files_from_paths(file_paths, clear=clear)

        if clear:
            # Replace mode: clear everything and load new files
            logger.debug(f"[Load] Replace mode: loading {len(new_file_items)} new files")
            self.parent_window.file_table_view.prepare_table(new_file_items)
            final_items = new_file_items
        else:
            # Merge mode: add to existing files, avoiding duplicates
            existing_items = self.parent_window.file_model.files if self.parent_window.file_model else []
            existing_paths = {item.full_path for item in existing_items}

            # Filter out duplicates
            unique_new_items = [item for item in new_file_items if item.full_path not in existing_paths]

            logger.debug(f"[Load] Merge mode: {len(existing_items)} existing + {len(unique_new_items)} new = {len(existing_items) + len(unique_new_items)} total")

            if unique_new_items:
                # Combine existing + new
                final_items = existing_items + unique_new_items

                # Use prepare_table with combined list
                self.parent_window.file_table_view.prepare_table(final_items)
            else:
                logger.info(f"[Load] No new files to add (all {len(new_file_items)} files already exist)")
                final_items = existing_items

        # Handle application-specific setup
        self.parent_window.files = final_items
        self.parent_window.preview_map = {f.filename: f for f in final_items}

        # Configure sorting and header after prepare_table
        self.parent_window.file_table_view.setSortingEnabled(True)
        if hasattr(self.parent_window, "header"):
            self.parent_window.header.setSectionsClickable(True)
            self.parent_window.header.setSortIndicatorShown(True)
            self.parent_window.header.setEnabled(True)

        self.parent_window.file_table_view.sortByColumn(1, Qt.AscendingOrder)
        self.parent_window.file_table_view.set_placeholder_visible(len(final_items) == 0)
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
                self.parent_window.load_metadata_for_items(items, use_extended=use_extended, source="individual_file_drop")
                # Select files AFTER metadata loading with a delay
                logger.debug(f"[Drop] Scheduling selection after metadata with 100ms delay", extra={"dev_only": True})
                QTimer.singleShot(100, select_dropped_files)
            else:
                logger.info(f"[Drop] Skipping metadata for {len(paths)} individual files (no Ctrl modifier)")
                # Select files immediately if not loading metadata
                logger.warning(f"[Drop] *** SCHEDULING selection immediately with 50ms delay ***")
                QTimer.singleShot(50, select_dropped_files)

        # After loading files + metadata
        self.parent_window.show_metadata_status()

    def load_single_item_from_drop(self, path: str, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Called when user drops a single file or folder from the tree onto file table view.
        Handles the new 4-modifier logic:
        - Normal: Replace + shallow
        - Ctrl: Replace + recursive
        - Shift: Merge + shallow
        - Ctrl+Shift: Merge + recursive
        """
        # Use centralized file loader
        self.parent_window.file_loader.handle_drop_operation(path, modifiers)

    def get_file_items_from_folder(self, folder_path: str) -> list:
        """Get FileItem objects from folder_path. Returns empty list if folder doesn't exist."""
        return self.parent_window.file_loader.get_file_items_from_folder(folder_path)

    def _has_deep_content(self, folder_path: str) -> bool:
        """Check if folder has any supported files in deeper levels (beyond root)"""
        return self.parent_window.file_loader.has_deep_content(folder_path)

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
