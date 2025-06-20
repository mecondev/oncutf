"""
event_handler_manager.py

Author: Michael Economou
Date: 2025-05-01

Manages all event handling operations for the application.
Centralizes UI event handlers, user interactions, and widget callbacks.
"""

import os
from typing import List

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtWidgets import QApplication, QFileDialog, QMenu

from core.modifier_handler import decode_modifiers_to_flags
from utils.cursor_helper import wait_cursor
from utils.logger_factory import get_cached_logger
from utils.path_utils import paths_equal

logger = get_cached_logger(__name__)


class EventHandlerManager:
    """
    Manages all event handling operations.

    Features:
    - Browse and folder import handlers
    - Table interaction handlers (context menu, double click, row click)
    - Header toggle handler
    - Splitter movement handlers
    """

    def __init__(self, parent_window):
        self.parent_window = parent_window
        logger.debug("[EventHandlerManager] Initialized")

    def handle_browse(self) -> None:
        """
        Opens a file dialog to select a folder and loads its files.
        Supports modifier keys for different loading modes:
        - Normal: Replace + shallow (skip metadata)
        - Ctrl: Replace + recursive (skip metadata)
        - Shift: Merge + shallow (skip metadata)
        - Ctrl+Shift: Merge + recursive (skip metadata)
        """
        folder_path = QFileDialog.getExistingDirectory(
            self.parent_window,
            "Select Folder",
            self.parent_window.current_folder_path or os.path.expanduser("~")
        )

        if folder_path:
            # Get current modifiers at time of selection
            modifiers = QApplication.keyboardModifiers()
            merge_mode, recursive, action_type = decode_modifiers_to_flags(modifiers)

            logger.info(f"[Browse] User selected folder: {folder_path} ({action_type})")

            # Use unified folder loading method
            if os.path.isdir(folder_path):
                self.parent_window.file_load_manager.load_folder(folder_path, merge_mode, recursive)

            # Update folder tree selection if replace mode
            if (not merge_mode and
                hasattr(self.parent_window, 'dir_model') and
                hasattr(self.parent_window, 'folder_tree') and
                hasattr(self.parent_window.dir_model, 'index')):
                index = self.parent_window.dir_model.index(folder_path)
                self.parent_window.folder_tree.setCurrentIndex(index)
        else:
            logger.debug("[Browse] User cancelled folder selection")

    def handle_folder_import(self) -> None:
        """Handle folder import from browse button"""
        selected_path = self.parent_window.folder_tree.get_selected_path()
        if not selected_path:
            logger.debug("[FolderImport] No folder selected")
            return

        # Get modifier state for merge/recursive options
        modifiers = QApplication.keyboardModifiers()
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)

        merge_mode = shift
        recursive = ctrl

        logger.info(f"[FolderImport] Loading folder: {selected_path} ({'Merge' if merge_mode else 'Replace'} + {'Recursive' if recursive else 'Shallow'})")

        # Use unified folder loading method
        self.parent_window.file_load_manager.load_folder(selected_path, merge_mode, recursive)

    def handle_table_context_menu(self, position) -> None:
        """
        Handles the right-click context menu for the file table.

        Supports:
        - Metadata load (normal / extended) for selected or all files
        - Invert selection, select all, reload folder
        - Uses unified selection system (_get_current_selection)
        """
        if not self.parent_window.file_model.files:
            return

        from utils.icons_loader import get_menu_icon

        # Get the index at position to ensure proper context
        index_at_position = self.parent_window.file_table_view.indexAt(position)
        total_files = len(self.parent_window.file_model.files)

        # Force sync selection to ensure it's current before showing menu
        self.parent_window.file_table_view._sync_selection_safely()

        # Give a brief moment for sync to complete
        QApplication.processEvents()

        # Use the unified selection system (same as shortcuts and drag-drop)
        selected_rows = self.parent_window.file_table_view._get_current_selection()
        selected_files = [self.parent_window.file_model.files[r] for r in selected_rows if 0 <= r < total_files]

        logger.debug(f"[ContextMenu] Found {len(selected_files)} selected files at position row {index_at_position.row() if index_at_position.isValid() else 'invalid'}", extra={"dev_only": True})

        menu = QMenu(self.parent_window)

        # --- Metadata actions ---
        action_load_sel = menu.addAction(get_menu_icon("file"), "Load metadata for selected file(s)")
        action_load_all = menu.addAction(get_menu_icon("folder"), "Load metadata for all files")
        action_load_ext_sel = menu.addAction(get_menu_icon("file-plus"), "Load extended metadata for selected file(s)")
        action_load_ext_all = menu.addAction(get_menu_icon("folder-plus"), "Load extended metadata for all files")

        menu.addSeparator()

        # --- Selection actions ---
        action_invert = menu.addAction(get_menu_icon("refresh-cw"), "Invert selection (Ctrl+I)")
        action_select_all = menu.addAction(get_menu_icon("check-square"), "Select all (Ctrl+A)")
        action_deselect_all = menu.addAction(get_menu_icon("square"), "Deselect all")

        menu.addSeparator()

        # --- Other actions ---
        action_reload = menu.addAction(get_menu_icon("refresh-cw"), "Reload folder (Ctrl+R)")

        menu.addSeparator()

        # --- Bulk rotation action ---
        action_bulk_rotation = menu.addAction(get_menu_icon("rotate-ccw"), "Set All Files to 0° Rotation...")
        action_bulk_rotation.setEnabled(len(selected_files) > 0)
        if len(selected_files) > 0:
            # Count how many files actually need rotation changes
            files_needing_rotation = 0
            for file_item in selected_files:
                current_rotation = self._get_current_rotation_for_file(file_item)
                if current_rotation != "0":
                    files_needing_rotation += 1

            if files_needing_rotation == 0:
                action_bulk_rotation.setToolTip("All selected files already have 0° rotation")
                action_bulk_rotation.setEnabled(False)
            elif files_needing_rotation == len(selected_files):
                action_bulk_rotation.setToolTip(f"Reset rotation to 0° for {files_needing_rotation} selected file(s)")
            else:
                action_bulk_rotation.setToolTip(f"Reset rotation to 0° for {files_needing_rotation} of {len(selected_files)} selected file(s)")
        else:
            action_bulk_rotation.setToolTip("Select files first to reset their rotation")

        menu.addSeparator()

        # --- Disabled future options ---
        action_save_sel = menu.addAction(get_menu_icon("save"), "Save metadata for selected file(s)")
        action_save_all = menu.addAction(get_menu_icon("save"), "Save ALL modified metadata")

        # Check for modifications using the new methods
        has_selected_modifications = False
        has_any_modifications = False

        if hasattr(self.parent_window, 'metadata_tree_view'):
            has_selected_modifications = self.parent_window.metadata_tree_view.has_modifications_for_selected_files()
            has_any_modifications = self.parent_window.metadata_tree_view.has_any_modifications()

        # Enable/disable save actions based on modifications
        action_save_sel.setEnabled(has_selected_modifications)
        action_save_all.setEnabled(has_any_modifications)

        # Update tooltips
        if has_selected_modifications:
            action_save_sel.setToolTip("Save metadata for selected file(s) with modifications")
        else:
            action_save_sel.setToolTip("No modifications in selected files")

        if has_any_modifications:
            action_save_all.setToolTip("Save ALL modified metadata")
        else:
            action_save_all.setToolTip("No metadata modifications to save")

        # --- Enable/disable logic with enhanced debugging ---
        has_selection = len(selected_files) > 0
        logger.debug(f"[ContextMenu] Selection state: {has_selection} ({len(selected_files)} files)", extra={"dev_only": True})

        if not has_selection:
            action_load_sel.setEnabled(False)
            action_load_ext_sel.setEnabled(False)
            action_invert.setEnabled(total_files > 0)
            logger.debug("[ContextMenu] Disabled selection-based actions (no selection)", extra={"dev_only": True})
        else:
            action_load_sel.setEnabled(True)
            action_load_ext_sel.setEnabled(True)
            logger.debug(f"[ContextMenu] Enabled selection-based actions ({len(selected_files)} files selected)", extra={"dev_only": True})

        action_load_all.setEnabled(total_files > 0)
        action_load_ext_all.setEnabled(total_files > 0)
        action_select_all.setEnabled(total_files > 0)
        action_reload.setEnabled(total_files > 0)

        # Show menu and get chosen action
        action = menu.exec_(self.parent_window.file_table_view.viewport().mapToGlobal(position))

        self.parent_window.file_table_view.context_focused_row = None
        self.parent_window.file_table_view.viewport().update()
        # Force full repaint of the table to avoid stale selection highlight
        self.parent_window.file_table_view.update()

        # === Handlers ===
        if action == action_load_sel:
            # Use intelligent loading with cache checking and smart UX
            self.parent_window.load_metadata_for_items(selected_files, use_extended=False, source="context_menu")

        elif action == action_load_ext_sel:
            # Use intelligent loading with cache checking and smart UX
            self.parent_window.load_metadata_for_items(selected_files, use_extended=True, source="context_menu")

        elif action == action_load_all:
            # Use intelligent loading with cache checking and smart UX
            self.parent_window.load_metadata_for_items(self.parent_window.file_model.files, use_extended=False, source="context_menu_all")

        elif action == action_load_ext_all:
            # Use intelligent loading with cache checking and smart UX
            self.parent_window.load_metadata_for_items(self.parent_window.file_model.files, use_extended=True, source="context_menu_all")

        elif action == action_invert:
            self.parent_window.invert_selection()

        elif action == action_select_all:
            self.parent_window.select_all_rows()

        elif action == action_reload:
            self.parent_window.force_reload()

        elif action == action_deselect_all:
            self.parent_window.clear_all_selection()

        elif action == action_save_sel:
            # Save modified metadata for selected files
            if hasattr(self.parent_window, 'metadata_manager'):
                self.parent_window.metadata_manager.save_metadata_for_selected()
            else:
                logger.warning("[EventHandler] No metadata manager available for save")

        elif action == action_save_all:
            # Save ALL modified metadata regardless of selection
            if hasattr(self.parent_window, 'metadata_manager'):
                self.parent_window.metadata_manager.save_all_modified_metadata()
            else:
                logger.warning("[EventHandler] No metadata manager available for save all")

        elif action == action_bulk_rotation:
            # Handle bulk rotation to 0°
            self._handle_bulk_rotation(selected_files)

    def handle_file_double_click(self, index: QModelIndex, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Loads metadata for the file (even if already loaded), on double-click.
        Uses unified dialog-based loading for consistency.
        """
        row = index.row()
        if 0 <= row < len(self.parent_window.file_model.files):
            file = self.parent_window.file_model.files[row]
            logger.info(f"[DoubleClick] Requested metadata reload for: {file.filename}")

            # Get selected files for context
            selected_files = [f for f in self.parent_window.file_model.files if f.checked]

            if len(selected_files) <= 1:
                # Single file or no selection - intelligent loading (will use wait cursor for single file)
                    self.parent_window.load_metadata_for_items([file], use_extended=False, source="double_click")
            else:
                # Multiple files selected - intelligent loading (will use dialog for multiple)
                self.parent_window.load_metadata_for_items(selected_files, use_extended=False, source="double_click_multi")

    def handle_header_toggle(self, _) -> None:
        """
        Triggered when column 0 header is clicked.
        Toggles selection and checked state of all files (efficient, like Ctrl+A).
        """
        if not self.parent_window.file_model.files:
            return

        total = len(self.parent_window.file_model.files)
        all_selected = all(file.checked for file in self.parent_window.file_model.files)
        selection_model = self.parent_window.file_table_view.selectionModel()

        with wait_cursor():
            if all_selected:
                # Unselect all
                selection_model.clearSelection()
                for file in self.parent_window.file_model.files:
                    file.checked = False
            else:
                # Select all efficiently
                self.parent_window.file_table_view.select_rows_range(0, total - 1)
                for file in self.parent_window.file_model.files:
                    file.checked = True
                self.parent_window.file_table_view.anchor_row = 0

            self.parent_window.file_table_view.viewport().update()
            self.parent_window.update_files_label()
            self.parent_window.request_preview_update()
            self.parent_window.metadata_tree_view.refresh_metadata_from_selection()

    def on_table_row_clicked(self, index: QModelIndex) -> None:
        """
        Handles single clicks on table rows.
        Updates metadata view based on the clicked file.
        """
        if not index.isValid():
            return

        row = index.row()
        if 0 <= row < len(self.parent_window.file_model.files):
            file = self.parent_window.file_model.files[row]
            logger.debug(f"[RowClick] Clicked on: {file.filename}", extra={"dev_only": True})

            # Update metadata view for clicked file
            self.parent_window.metadata_tree_view.refresh_metadata_from_selection()

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """
        Handle horizontal splitter movement.
        Updates UI elements that depend on horizontal space allocation.
        """
        logger.debug(f"[Splitter] Horizontal moved: pos={pos}, index={index}", extra={"dev_only": True})

        # Update any UI elements that need to respond to horizontal space changes
        if hasattr(self.parent_window, 'folder_tree'):
            self.parent_window.folder_tree.on_horizontal_splitter_moved(pos, index)

        if hasattr(self.parent_window, 'file_table_view'):
            self.parent_window.file_table_view.on_horizontal_splitter_moved(pos, index)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """
        Handle vertical splitter movement.
        Updates UI elements that depend on vertical space allocation.
        """
        logger.debug(f"[Splitter] Vertical moved: pos={pos}, index={index}", extra={"dev_only": True})

        # Update any UI elements that need to respond to vertical space changes
        if hasattr(self.parent_window, 'folder_tree'):
            self.parent_window.folder_tree.on_vertical_splitter_moved(pos, index)

        if hasattr(self.parent_window, 'file_table_view'):
            self.parent_window.file_table_view.on_vertical_splitter_moved(pos, index)

        if hasattr(self.parent_window, 'preview_tables_view'):
            self.parent_window.preview_tables_view.handle_splitter_moved(pos, index)

    def _handle_bulk_rotation(self, selected_files: List) -> None:
        """
        Handle bulk rotation setting to 0° for selected files.

        Args:
            selected_files: List of FileItem objects to process
        """
        if not selected_files:
            logger.warning("[BulkRotation] No files selected for bulk rotation")
            return

        logger.info(f"[BulkRotation] Starting bulk rotation for {len(selected_files)} files")

        try:
            from widgets.bulk_rotation_dialog import BulkRotationDialog

            # Show dialog and get user choices
            files_to_process = BulkRotationDialog.get_bulk_rotation_choice(
                self.parent_window,
                selected_files,
                self.parent_window.metadata_cache
            )

            if not files_to_process:
                logger.debug("[BulkRotation] User cancelled bulk rotation or no files selected")
                return

            if not files_to_process:
                logger.info("[BulkRotation] No files selected for processing")
                return

            logger.info(f"[BulkRotation] Processing {len(files_to_process)} files")

            # Apply rotation directly
            self._apply_bulk_rotation(files_to_process)

        except ImportError as e:
            logger.error(f"[BulkRotation] Failed to import BulkRotationDialog: {e}")
            from utils.dialog_utils import show_error_message
            show_error_message(
                self.parent_window,
                "Error",
                "Bulk rotation dialog is not available. Please check the installation."
            )
        except Exception as e:
            logger.exception(f"[BulkRotation] Unexpected error: {e}")
            from utils.dialog_utils import show_error_message
            show_error_message(
                self.parent_window,
                "Error",
                f"An error occurred during bulk rotation: {str(e)}"
            )

    def _apply_bulk_rotation(self, files_to_process: List) -> None:
        """
        Apply 0° rotation to the specified files, but only to files that actually need the change.

        Args:
            files_to_process: List of FileItem objects to set rotation to 0°
        """
        if not files_to_process:
            return

        logger.info(f"[BulkRotation] Checking rotation for {len(files_to_process)} files")

        try:
            # Apply rotation changes to metadata cache, but only for files that need it
            modified_count = 0
            skipped_count = 0

            for file_item in files_to_process:
                # Check current rotation first
                current_rotation = self._get_current_rotation_for_file(file_item)

                # Skip files that already have 0° rotation
                if current_rotation == "0":
                    logger.debug(f"[BulkRotation] Skipping {file_item.filename} - already has 0° rotation")
                    skipped_count += 1
                    continue

                # Get or create metadata cache entry
                cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
                if not cache_entry:
                    # Create a new cache entry if none exists
                    metadata_dict = getattr(file_item, 'metadata', {}) or {}
                    self.parent_window.metadata_cache.set(file_item.full_path, metadata_dict)
                    cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)

                if cache_entry and hasattr(cache_entry, 'data'):
                    # Set rotation to 0
                    cache_entry.data["Rotation"] = "0"
                    cache_entry.modified = True

                    # Update file item metadata too
                    if not hasattr(file_item, 'metadata') or file_item.metadata is None:
                        file_item.metadata = {}
                    file_item.metadata["Rotation"] = "0"

                    # Mark file as modified
                    file_item.metadata_status = "modified"
                    modified_count += 1

                    logger.debug(f"[BulkRotation] Set rotation=0 for {file_item.filename} (was: {current_rotation})")

            # Update UI to reflect changes
            if modified_count > 0:
                # Update file table icons
                self.parent_window.file_model.layoutChanged.emit()

                # CRITICAL: Update metadata tree view to mark items as modified
                if hasattr(self.parent_window, 'metadata_tree_view'):
                    # For each modified file, mark rotation as modified in tree view
                    for file_item in files_to_process:
                        if file_item.metadata_status == "modified":
                            # Add to modified items for this file path
                            if not self.parent_window.metadata_tree_view._path_in_dict(file_item.full_path, self.parent_window.metadata_tree_view.modified_items_per_file):
                                self.parent_window.metadata_tree_view._set_in_path_dict(file_item.full_path, set(), self.parent_window.metadata_tree_view.modified_items_per_file)

                            existing_modifications = self.parent_window.metadata_tree_view._get_from_path_dict(file_item.full_path, self.parent_window.metadata_tree_view.modified_items_per_file)
                            if existing_modifications is None:
                                existing_modifications = set()
                            existing_modifications.add("Rotation")
                            self.parent_window.metadata_tree_view._set_in_path_dict(file_item.full_path, existing_modifications, self.parent_window.metadata_tree_view.modified_items_per_file)

                            # If this is the currently displayed file, update current modified items too
                            if (hasattr(self.parent_window.metadata_tree_view, '_current_file_path') and
                                paths_equal(self.parent_window.metadata_tree_view._current_file_path, file_item.full_path)):
                                self.parent_window.metadata_tree_view.modified_items.add("Rotation")

                    # Refresh the metadata display to show the changes
                    self.parent_window.metadata_tree_view.update_from_parent_selection()

                # Show status message
                if hasattr(self.parent_window, 'set_status'):
                    if skipped_count > 0:
                        status_msg = f"Set rotation to 0° for {modified_count} file(s), {skipped_count} already had 0° rotation"
                    else:
                        status_msg = f"Set rotation to 0° for {modified_count} file(s)"

                    self.parent_window.set_status(status_msg, color="green", auto_reset=True)

                logger.info(f"[BulkRotation] Successfully applied rotation to {modified_count} files, skipped {skipped_count} files")
            else:
                logger.info("[BulkRotation] No files needed rotation changes")
                if hasattr(self.parent_window, 'set_status'):
                    self.parent_window.set_status("All selected files already have 0° rotation", color="gray", auto_reset=True)

        except Exception as e:
            logger.exception(f"[BulkRotation] Error applying rotation: {e}")
            from utils.dialog_utils import show_error_message
            show_error_message(
                self.parent_window,
                "Error",
                f"Failed to apply rotation changes: {str(e)}"
            )

    def _get_current_rotation_for_file(self, file_item) -> str:
        """
        Get the current rotation value for a file, checking cache first then file metadata.

        Returns:
            str: Current rotation value ("0", "90", "180", "270") or "0" if not found
        """
        # Check metadata cache first (includes any pending modifications)
        if hasattr(self.parent_window, 'metadata_cache'):
            cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
            if cache_entry and hasattr(cache_entry, 'data'):
                rotation = cache_entry.data.get("Rotation")
                if rotation is not None:
                    return str(rotation)

        # Fallback to file item metadata
        if hasattr(file_item, 'metadata') and file_item.metadata:
            rotation = file_item.metadata.get("Rotation")
            if rotation is not None:
                return str(rotation)

        # Default to "0" if no rotation found
        return "0"
