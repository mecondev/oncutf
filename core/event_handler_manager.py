"""
Module: event_handler_manager.py

Author: Michael Economou
Date: 2025-05-31

Manages all event handling operations for the main window.
Handles browse, folder import, table interactions, context menus, and user actions.
"""

import os
import time

from config import STATUS_COLORS
from core.modifier_handler import decode_modifiers_to_flags
from core.pyqt_imports import QAction, QApplication, QMenu, QModelIndex, Qt
from utils.cursor_helper import wait_cursor
from utils.file_status_helpers import (
    has_hash,
    has_metadata,
)
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
        self.hash_worker = None
        self.hash_dialog = None
        self._operation_cancelled = False  # Track if operation was cancelled
        logger.debug("EventHandlerManager initialized", extra={"dev_only": True})

    def handle_browse(self) -> None:
        """
        Opens a file dialog to select a folder and loads its files.
        Supports modifier keys for different loading modes:
        - Normal: Replace + shallow (skip metadata)
        - Ctrl: Replace + recursive (skip metadata)
        - Shift: Merge + shallow (skip metadata)
        - Ctrl+Shift: Merge + recursive (skip metadata)
        """
        from utils.multiscreen_helper import get_existing_directory_on_parent_screen

        folder_path = get_existing_directory_on_parent_screen(
            self.parent_window,
            "Select Folder",
            self.parent_window.current_folder_path or os.path.expanduser("~"),
        )

        if folder_path:
            # Get current modifiers at time of selection
            modifiers = QApplication.keyboardModifiers()
            merge_mode, recursive, action_type = decode_modifiers_to_flags(modifiers)

            logger.info(f"User selected folder: {folder_path} ({action_type})")

            # Use unified folder loading method
            if os.path.isdir(folder_path):
                self.parent_window.file_load_manager.load_folder(folder_path, merge_mode, recursive)

            # Update folder tree selection if replace mode
            if (
                not merge_mode
                and hasattr(self.parent_window, "dir_model")
                and hasattr(self.parent_window, "folder_tree")
                and hasattr(self.parent_window.dir_model, "index")
            ):
                index = self.parent_window.dir_model.index(folder_path)
                self.parent_window.folder_tree.setCurrentIndex(index)
        else:
            logger.debug("User cancelled folder selection", extra={"dev_only": True})

    def handle_folder_import(self) -> None:
        """Handle folder import from browse button"""
        selected_path = self.parent_window.folder_tree.get_selected_path()
        if not selected_path:
            logger.debug("No folder selected", extra={"dev_only": True})
            return

        # Get modifier state for merge/recursive options
        modifiers = QApplication.keyboardModifiers()
        ctrl = bool(modifiers & Qt.ControlModifier)  # type: ignore
        shift = bool(modifiers & Qt.ShiftModifier)  # type: ignore

        merge_mode = shift
        recursive = ctrl

        logger.info(
            f"Loading folder: {selected_path} ({'Merge' if merge_mode else 'Replace'} + {'Recursive' if recursive else 'Shallow'})"
        )

        # Use unified folder loading method
        self.parent_window.file_load_manager.load_folder(selected_path, merge_mode, recursive)

    def handle_table_context_menu(self, position) -> None:
        """
        Handles the right-click context menu for the file table.
        Simplified for faster response - basic functionality only.
        """
        if not self.parent_window.file_model.files:
            return

        from utils.icons_loader import get_menu_icon

        # Helper function to create actions with shortcuts
        def create_action_with_shortcut(icon, text, shortcut=None):
            action = QAction(text, self.parent_window)
            action.setIcon(icon)
            if shortcut:
                # Use tab character for right alignment - Qt handles this automatically
                action.setText(f"{text}\t{shortcut}")
            return action

        # Get total files for context
        total_files = len(self.parent_window.file_model.files)

        # Use unified selection method (fast)
        selected_files = self.parent_window.get_selected_files_ordered()
        has_selection = len(selected_files) > 0

        logger.debug(
            f"Context menu: {len(selected_files)} selected files", extra={"dev_only": True}
        )

        menu = QMenu(self.parent_window)

        # Enhanced styling for better appearance and spacing
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #232323;
                color: #f0ebd8;
                border: none;
                border-radius: 8px;
                font-family: "Inter", "Segoe UI", Arial, sans-serif;
                font-size: 9pt;
                padding: 6px 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 3px 16px 3px 8px;
                margin: 1px 2px;
                border-radius: 4px;
                min-height: 16px;
                icon-size: 16px;
            }
            QMenu::item:selected {
                background-color: #748cab;
                color: #0d1321;
            }
            QMenu::item:disabled {
                color: #888888;
            }
            QMenu::icon {
                padding-left: 6px;
                padding-right: 6px;
            }
            QMenu::separator {
                background-color: #5a5a5a;
                height: 1px;
                margin: 4px 8px;
            }
        """
        )

        # Smart Metadata actions - only analyze selected files for speed
        selected_analysis = self._analyze_metadata_state(selected_files)

        # Use simple analysis for all files to avoid performance issues
        # all_files_analysis = self._get_simple_metadata_analysis()

        # Create actions with smart labels and tooltips
        action_load_sel = create_action_with_shortcut(
            get_menu_icon("file"), f"{selected_analysis['fast_label']} for selection", "Ctrl+M"
        )
        action_load_all = create_action_with_shortcut(
            get_menu_icon("folder"), "Load Fast Metadata for all files", "Shift+Ctrl+M"
        )
        action_load_ext_sel = create_action_with_shortcut(
            get_menu_icon("file-plus"),
            f"{selected_analysis['extended_label']} for selection",
            "Ctrl+E",
        )
        action_load_ext_all = create_action_with_shortcut(
            get_menu_icon("folder-plus"), "Load Extended Metadata for all files", "Shift+Ctrl+E"
        )

        menu.addAction(action_load_sel)
        menu.addAction(action_load_all)
        menu.addAction(action_load_ext_sel)
        menu.addAction(action_load_ext_all)

        # Smart enable/disable logic based on analysis
        action_load_sel.setEnabled(has_selection and selected_analysis["enable_fast_selected"])
        action_load_ext_sel.setEnabled(
            has_selection and selected_analysis["enable_extended_selected"]
        )
        action_load_all.setEnabled(total_files > 0)
        action_load_ext_all.setEnabled(total_files > 0)

        # Set smart tooltips
        action_load_sel.setToolTip(selected_analysis["fast_tooltip"])
        action_load_ext_sel.setToolTip(selected_analysis["extended_tooltip"])
        action_load_all.setToolTip(f"Load fast metadata for {total_files} file(s)")
        action_load_ext_all.setToolTip(f"Load extended metadata for {total_files} file(s)")

        menu.addSeparator()

        # Selection actions
        action_select_all = create_action_with_shortcut(
            get_menu_icon("check-square"), "Select all", "Ctrl+A"
        )
        action_invert = create_action_with_shortcut(
            get_menu_icon("refresh-cw"), "Invert selection", "Ctrl+I"
        )
        action_deselect_all = create_action_with_shortcut(
            get_menu_icon("square"), "Deselect all", "Ctrl+Shift+A"
        )

        menu.addAction(action_select_all)
        menu.addAction(action_invert)
        menu.addAction(action_deselect_all)

        menu.addSeparator()

        # Other actions
        action_reload = create_action_with_shortcut(
            get_menu_icon("refresh-cw"), "Reload folder", "F5"
        )
        action_clear_table = create_action_with_shortcut(
            get_menu_icon("x"), "Clear file table", "Shift+Esc"
        )

        menu.addAction(action_reload)
        menu.addAction(action_clear_table)

        menu.addSeparator()

        # Hash actions
        action_calculate_hashes = create_action_with_shortcut(
            get_menu_icon("hash"), "Calculate checksums for selected", "Ctrl+H"
        )
        action_calculate_hashes_all = create_action_with_shortcut(
            get_menu_icon("hash"), "Calculate checksums for all files", "Shift+Ctrl+H"
        )

        # Smart hash state analysis - only analyze selected files for speed
        selected_hash_analysis = self._analyze_hash_state(selected_files)

        # Use simple analysis for all files to avoid performance issues
        # all_files_hash_analysis = self._get_simple_hash_analysis()

        # Update hash actions with smart logic
        action_calculate_hashes.setText(selected_hash_analysis["selected_label"] + "\tCtrl+H")
        action_calculate_hashes_all.setText("Calculate checksums for all files\tShift+Ctrl+H")

        menu.addAction(action_calculate_hashes)
        menu.addAction(action_calculate_hashes_all)

        # Smart enable/disable for hash actions
        action_calculate_hashes.setEnabled(
            has_selection and selected_hash_analysis["enable_selected"]
        )
        action_calculate_hashes_all.setEnabled(total_files > 0)

        # Set smart tooltips for hash actions
        action_calculate_hashes.setToolTip(selected_hash_analysis["selected_tooltip"])
        action_calculate_hashes_all.setToolTip(f"Calculate checksums for {total_files} file(s)")

        menu.addSeparator()

        # Save actions
        action_save_sel = create_action_with_shortcut(
            get_menu_icon("save"), "Save metadata for selection", "Ctrl+S"
        )
        action_save_all = create_action_with_shortcut(
            get_menu_icon("save"), "Save ALL modified metadata", "Ctrl+Shift+S"
        )

        menu.addAction(action_save_sel)
        menu.addAction(action_save_all)

        # Simple check for modifications
        has_modifications = False
        if hasattr(self.parent_window, "metadata_tree_view"):
            has_modifications = bool(self.parent_window.metadata_tree_view.modified_items)

        action_save_sel.setEnabled(has_selection and has_modifications)
        action_save_all.setEnabled(has_modifications)

        menu.addSeparator()

        # Bulk rotation action - simplified for performance
        action_bulk_rotation = create_action_with_shortcut(
            get_menu_icon("rotate-ccw"), "Set All Files to 0° Rotation...", None
        )
        menu.addAction(action_bulk_rotation)
        action_bulk_rotation.setEnabled(len(selected_files) > 0)
        if len(selected_files) > 0:
            action_bulk_rotation.setToolTip(
                f"Reset rotation to 0° for {len(selected_files)} selected file(s)"
            )
        else:
            action_bulk_rotation.setToolTip("Select files first to reset their rotation")

        menu.addSeparator()

        # Hash & Comparison actions
        action_find_duplicates_sel = create_action_with_shortcut(
            get_menu_icon("copy"), "Find duplicates in selected files", None
        )
        action_find_duplicates_all = create_action_with_shortcut(
            get_menu_icon("layers"), "Find duplicates in all files", None
        )
        action_compare_external = create_action_with_shortcut(
            get_menu_icon("folder"), "Compare with external folder...", None
        )

        menu.addAction(action_find_duplicates_sel)
        menu.addAction(action_find_duplicates_all)
        menu.addAction(action_compare_external)

        menu.addSeparator()

        # Export actions
        action_export_sel = create_action_with_shortcut(
            get_menu_icon("download"), "Export metadata for selection", None
        )
        action_export_all = create_action_with_shortcut(
            get_menu_icon("download"), "Export metadata for all files", None
        )

        menu.addAction(action_export_sel)
        menu.addAction(action_export_all)

        # Enable/disable export actions based on metadata availability
        action_export_sel.setEnabled(has_selection)
        action_export_all.setEnabled(total_files > 0)

        # Update tooltips
        if has_selection:
            action_export_sel.setToolTip(
                f"Export metadata for {len(selected_files)} selected file(s)"
            )
        else:
            action_export_sel.setToolTip("Select files first to export their metadata")

        if total_files > 0:
            action_export_all.setToolTip("Export metadata for all files in folder")
        else:
            action_export_all.setToolTip("No files have metadata to export")

        # Enable/disable logic with enhanced debugging
        logger.debug(
            f"Context menu: Selection state: {has_selection} ({len(selected_files)} files)",
            extra={"dev_only": True},
        )

        # Only handle non-metadata selection actions here
        action_invert.setEnabled(total_files > 0 and has_selection)
        action_select_all.setEnabled(total_files > 0)
        action_reload.setEnabled(total_files > 0)
        action_clear_table.setEnabled(total_files > 0)

        # Hash actions enable/disable logic with smart behavior
        action_find_duplicates_sel.setEnabled(
            len(selected_files) >= 2
        )  # Need at least 2 files to find duplicates
        action_find_duplicates_all.setEnabled(total_files >= 2)
        action_compare_external.setEnabled(has_selection)  # Need selection to compare
        action_calculate_hashes.setEnabled(
            has_selection and selected_hash_analysis["enable_selected"]
        )
        action_calculate_hashes_all.setEnabled(total_files > 0)

        # Update hash tooltip
        if has_selection:
            action_calculate_hashes.setToolTip(selected_hash_analysis["selected_tooltip"])
        else:
            action_calculate_hashes.setToolTip("Select files first to calculate their checksums")

        if total_files > 0:
            action_calculate_hashes_all.setToolTip(f"Calculate checksums for {total_files} file(s)")
        else:
            action_calculate_hashes_all.setToolTip("No files available to calculate checksums")

        # Show menu and get chosen action
        action = menu.exec_(self.parent_window.file_table_view.viewport().mapToGlobal(position))

        self.parent_window.file_table_view.context_focused_row = None
        # Remove the problematic update() calls that can cause loops
        # self.parent_window.file_table_view.viewport().update()
        # self.parent_window.file_table_view.update()

        # === Handlers ===
        if action == action_load_sel:
            # Use intelligent loading with cache checking and smart UX
            self.parent_window.load_metadata_for_items(
                selected_files, use_extended=False, source="context_menu"
            )

        elif action == action_load_ext_sel:
            # Use intelligent loading with cache checking and smart UX
            self.parent_window.load_metadata_for_items(
                selected_files, use_extended=True, source="context_menu"
            )

        elif action == action_load_all:
            # Use intelligent loading with cache checking and smart UX
            self.parent_window.load_metadata_for_items(
                self.parent_window.file_model.files, use_extended=False, source="context_menu_all"
            )

        elif action == action_load_ext_all:
            # Use intelligent loading with cache checking and smart UX
            self.parent_window.load_metadata_for_items(
                self.parent_window.file_model.files, use_extended=True, source="context_menu_all"
            )

        elif action == action_invert:
            self.parent_window.invert_selection()

        elif action == action_select_all:
            self.parent_window.select_all_rows()

        elif action == action_reload:
            self.parent_window.force_reload()

        elif action == action_clear_table:
            self.parent_window.clear_file_table_shortcut()

        elif action == action_deselect_all:
            self.parent_window.clear_all_selection()

        elif action == action_save_sel:
            # Save modified metadata for selected files
            if hasattr(self.parent_window, "metadata_manager"):
                self.parent_window.metadata_manager.save_metadata_for_selected()
            else:
                logger.warning("[EventHandler] No metadata manager available for save")

        elif action == action_save_all:
            # Save ALL modified metadata regardless of selection
            if hasattr(self.parent_window, "metadata_manager"):
                self.parent_window.metadata_manager.save_all_modified_metadata()
            else:
                logger.warning("[EventHandler] No metadata manager available for save all")

        elif action == action_bulk_rotation:
            # Handle bulk rotation to 0°
            self._handle_bulk_rotation(selected_files)

        elif action == action_find_duplicates_sel:
            # Find duplicates in selected files
            self._handle_find_duplicates(selected_files, "selected")

        elif action == action_find_duplicates_all:
            # Find duplicates in all files
            self._handle_find_duplicates(self.parent_window.file_model.files, "all")

        elif action == action_compare_external:
            # Compare selected files with external folder
            self._handle_compare_external(selected_files)

        elif action == action_calculate_hashes:
            # Calculate checksums for selected files
            self._handle_calculate_hashes(selected_files)

        elif action == action_calculate_hashes_all:
            # Calculate checksums for all files
            self._handle_calculate_hashes(self.parent_window.file_model.files)

        elif action == action_export_sel:
            # Handle metadata export for selected files
            self._handle_export_metadata(selected_files, "selected")

        elif action == action_export_all:
            # Handle metadata export for all files
            self._handle_export_metadata(self.parent_window.file_model.files, "all")

    def handle_file_double_click(
        self, index: QModelIndex, modifiers: Qt.KeyboardModifiers = Qt.KeyboardModifiers()
    ) -> None:
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
                self.parent_window.load_metadata_for_items(
                    [file], use_extended=False, source="double_click"
                )
            else:
                # Multiple files selected - intelligent loading (will use dialog for multiple)
                self.parent_window.load_metadata_for_items(
                    selected_files, use_extended=False, source="double_click_multi"
                )

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
        Metadata updates are handled by the selection system, not here.
        """
        if not index.isValid():
            return

        row = index.row()
        if 0 <= row < len(self.parent_window.file_model.files):
            file = self.parent_window.file_model.files[row]
            logger.debug(f"[RowClick] Clicked on: {file.filename}", extra={"dev_only": True})

            # NOTE: Metadata updates are handled by the selection system automatically
            # Removed redundant refresh_metadata_from_selection() call that was causing conflicts

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """
        Handle horizontal splitter movement.
        DEPRECATED: This functionality has been moved to SplitterManager.
        This method is kept for backward compatibility and delegates to SplitterManager.
        """
        logger.debug(
            "[EventHandlerManager] DEPRECATED: Delegating splitter handling to SplitterManager",
            extra={"dev_only": True},
        )

        if hasattr(self.parent_window, "splitter_manager"):
            self.parent_window.splitter_manager.on_horizontal_splitter_moved(pos, index)
        else:
            # Fallback to legacy behavior if SplitterManager is not available
            logger.debug(
                f"[Splitter] Horizontal moved: pos={pos}, index={index}", extra={"dev_only": True}
            )

            # Update any UI elements that need to respond to horizontal space changes
            if hasattr(self.parent_window, "folder_tree"):
                self.parent_window.folder_tree.on_horizontal_splitter_moved(pos, index)

            if hasattr(self.parent_window, "file_table_view"):
                self.parent_window.file_table_view.on_horizontal_splitter_moved(pos, index)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """
        Handle vertical splitter movement.
        DEPRECATED: This functionality has been moved to SplitterManager.
        This method is kept for backward compatibility and delegates to SplitterManager.
        """
        logger.debug(
            "[EventHandlerManager] DEPRECATED: Delegating splitter handling to SplitterManager",
            extra={"dev_only": True},
        )

        if hasattr(self.parent_window, "splitter_manager"):
            self.parent_window.splitter_manager.on_vertical_splitter_moved(pos, index)
        else:
            # Fallback to legacy behavior if SplitterManager is not available
            logger.debug(
                f"[Splitter] Vertical moved: pos={pos}, index={index}", extra={"dev_only": True}
            )

            # Update any UI elements that need to respond to vertical space changes
            if hasattr(self.parent_window, "folder_tree"):
                self.parent_window.folder_tree.on_vertical_splitter_moved(pos, index)

            if hasattr(self.parent_window, "file_table_view"):
                self.parent_window.file_table_view.on_vertical_splitter_moved(pos, index)

            if hasattr(self.parent_window, "preview_tables_view"):
                self.parent_window.preview_tables_view.handle_splitter_moved(pos, index)

    def _handle_bulk_rotation(self, selected_files: list) -> None:
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
                self.parent_window, selected_files, self.parent_window.metadata_cache
            )

            if not files_to_process:
                logger.debug(
                    "[BulkRotation] User cancelled bulk rotation or no files selected",
                    extra={"dev_only": True},
                )
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
                "Bulk rotation dialog is not available. Please check the installation.",
            )
        except Exception as e:
            logger.exception(f"[BulkRotation] Unexpected error: {e}")
            from utils.dialog_utils import show_error_message

            show_error_message(
                self.parent_window, "Error", f"An error occurred during bulk rotation: {str(e)}"
            )

    def _apply_bulk_rotation(self, files_to_process: list) -> None:
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
                    logger.debug(
                        f"[BulkRotation] Skipping {file_item.filename} - already has 0° rotation",
                        extra={"dev_only": True},
                    )
                    skipped_count += 1
                    continue

                # Get or create metadata cache entry
                cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
                if not cache_entry:
                    # Create a new cache entry if none exists
                    metadata_dict = getattr(file_item, "metadata", {}) or {}
                    self.parent_window.metadata_cache.set(file_item.full_path, metadata_dict)
                    cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)

                if cache_entry and hasattr(cache_entry, "data"):
                    # Set rotation to 0
                    cache_entry.data["Rotation"] = "0"
                    cache_entry.modified = True

                    # Update file item metadata too
                    if not hasattr(file_item, "metadata") or file_item.metadata is None:
                        file_item.metadata = {}
                    file_item.metadata["Rotation"] = "0"

                    # Mark file as modified
                    file_item.metadata_status = "modified"
                    modified_count += 1

                    logger.debug(
                        f"[BulkRotation] Set rotation=0 for {file_item.filename} (was: {current_rotation})",
                        extra={"dev_only": True},
                    )

            # Update UI to reflect changes
            if modified_count > 0:
                # Update file table icons
                self.parent_window.file_model.layoutChanged.emit()

                # CRITICAL: Update metadata tree view to mark items as modified
                if hasattr(self.parent_window, "metadata_tree_view"):
                    # For each modified file, mark rotation as modified in tree view
                    for file_item in files_to_process:
                        if file_item.metadata_status == "modified":
                            # Add to modified items for this file path
                            if not self.parent_window.metadata_tree_view._path_in_dict(
                                file_item.full_path,
                                self.parent_window.metadata_tree_view.modified_items_per_file,
                            ):
                                self.parent_window.metadata_tree_view._set_in_path_dict(
                                    file_item.full_path,
                                    set(),
                                    self.parent_window.metadata_tree_view.modified_items_per_file,
                                )

                            existing_modifications = (
                                self.parent_window.metadata_tree_view._get_from_path_dict(
                                    file_item.full_path,
                                    self.parent_window.metadata_tree_view.modified_items_per_file,
                                )
                            )
                            if existing_modifications is None:
                                existing_modifications = set()
                            existing_modifications.add("Rotation")
                            self.parent_window.metadata_tree_view._set_in_path_dict(
                                file_item.full_path,
                                existing_modifications,
                                self.parent_window.metadata_tree_view.modified_items_per_file,
                            )

                            # If this is the currently displayed file, update current modified items too
                            if hasattr(
                                self.parent_window.metadata_tree_view, "_current_file_path"
                            ) and paths_equal(
                                self.parent_window.metadata_tree_view._current_file_path,
                                file_item.full_path,
                            ):
                                self.parent_window.metadata_tree_view.modified_items.add("Rotation")

                    # Refresh the metadata display to show the changes
                    self.parent_window.metadata_tree_view.update_from_parent_selection()

                # Update preview tables to reflect the changes
                if hasattr(self.parent_window, "request_preview_update"):
                    self.parent_window.request_preview_update()

                # Show status message
                if hasattr(self.parent_window, "set_status"):
                    if skipped_count > 0:
                        status_msg = f"Set rotation to 0° for {modified_count} file(s), {skipped_count} already had 0° rotation"
                    else:
                        status_msg = f"Set rotation to 0° for {modified_count} file(s)"

                    self.parent_window.set_status(
                        status_msg, color=STATUS_COLORS["operation_success"], auto_reset=True
                    )

                logger.info(
                    f"[BulkRotation] Successfully applied rotation to {modified_count} files, skipped {skipped_count} files"
                )
            else:
                logger.info("[BulkRotation] No files needed rotation changes")
                if hasattr(self.parent_window, "set_status"):
                    self.parent_window.set_status(
                        "All selected files already have 0° rotation",
                        color=STATUS_COLORS["neutral_info"],
                        auto_reset=True,
                    )

        except Exception as e:
            logger.exception(f"[BulkRotation] Error applying rotation: {e}")
            from utils.dialog_utils import show_error_message

            show_error_message(
                self.parent_window, "Error", f"Failed to apply rotation changes: {str(e)}"
            )

    def _get_current_rotation_for_file(self, file_item) -> str:
        """
        Get the current rotation value for a file, checking cache first then file metadata.

        Returns:
            str: Current rotation value ("0", "90", "180", "270") or "0" if not found
        """
        # Check metadata cache first (includes any pending modifications)
        if hasattr(self.parent_window, "metadata_cache"):
            cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
            if cache_entry and hasattr(cache_entry, "data"):
                rotation = cache_entry.data.get("Rotation")
                if rotation is not None:
                    return str(rotation)

        # Fallback to file item metadata
        if hasattr(file_item, "metadata") and file_item.metadata:
            rotation = file_item.metadata.get("Rotation")
            if rotation is not None:
                return str(rotation)

        # Default to "0" if no rotation found
        return "0"

    # === Hash & Comparison Methods ===

    def _handle_find_duplicates(self, file_items: list, scope: str) -> None:
        """
        Handle finding duplicates in the given file list.

        Args:
            file_items: List of FileItem objects to scan for duplicates
            scope: Either "selected" or "all" for logging/status purposes
        """
        if not file_items:
            logger.warning(f"[HashManager] No files provided for duplicate detection ({scope})")
            return

        logger.info(
            f"[HashManager] Starting duplicate detection for {len(file_items)} files ({scope})"
        )

        # Convert FileItem objects to file paths
        file_paths = [item.full_path for item in file_items]

        if len(file_paths) == 1:
            # Single file - use wait cursor (like metadata system)
            from core.hash_manager import HashManager
            from utils.cursor_helper import wait_cursor

            try:
                with wait_cursor():
                    hash_manager = HashManager()
                    duplicates = hash_manager.find_duplicates_in_list(file_paths)
                    self._show_duplicates_results(duplicates, scope)
            except Exception as e:
                logger.error(f"[HashManager] Error finding duplicates: {e}")
                from widgets.custom_message_dialog import CustomMessageDialog

                CustomMessageDialog.information(
                    self.parent_window, "Error", f"Failed to find duplicates: {str(e)}"
                )
        else:
            # Multiple files - use worker thread with progress dialog
            self._start_hash_operation("duplicates", file_paths, scope)

    def _start_hash_operation(
        self,
        operation_type: str,
        file_paths: list[str],
        scope: str | None = None,
        external_folder: str | None = None,
    ) -> None:
        """Start hash operation with progress dialog."""
        # Reset operation cancelled flag for new operation
        self._operation_cancelled = False

        # Create and configure hash worker
        from core.hash_worker import HashWorker
        from utils.progress_dialog import ProgressDialog

        self.hash_worker = HashWorker()

        try:
            # Calculate total size for enhanced progress tracking
            from utils.file_size_calculator import calculate_files_total_size

            # Convert paths to FileItem-like objects for size calculation
            file_items = []
            for path in file_paths:

                class PathWrapper:
                    def __init__(self, path):
                        self.full_path = path

                file_items.append(PathWrapper(path))

            total_size = calculate_files_total_size(file_items)
            self._total_size_bytes = total_size  # Store for progress tracking

            # Create waiting dialog
            self.hash_dialog = ProgressDialog.create_hash_dialog(
                parent=self.parent_window, cancel_callback=self._cancel_hash_operation
            )

            # Start enhanced tracking with total size
            self.hash_dialog.start_progress_tracking(total_size)

            # Connect signals - simplified approach (2025): fewer connections are now more reliable
            self.hash_worker.progress_updated.connect(self._on_hash_progress_updated)
            self.hash_worker.size_progress.connect(self._on_size_progress_updated)
            self.hash_worker.status_updated.connect(self.hash_dialog.set_status)

            # Connect real-time UI update signal
            self.hash_worker.file_hash_calculated.connect(self._on_file_hash_calculated)

            # Connect result signals
            if operation_type == "duplicates":
                self.hash_worker.duplicates_found.connect(
                    lambda duplicates: self._on_duplicates_found(duplicates, scope or "unknown")
                )
            elif operation_type == "compare":
                self.hash_worker.comparison_result.connect(
                    lambda results: self._on_comparison_result(
                        results, external_folder or "unknown"
                    )
                )
            elif operation_type == "checksums":
                self.hash_worker.checksums_calculated.connect(self._on_checksums_calculated)

            # Connect control signals
            self.hash_worker.finished_processing.connect(self._on_hash_operation_finished)
            self.hash_worker.error_occurred.connect(self._on_hash_operation_error)

            # Setup worker based on operation type
            if operation_type == "duplicates":
                self.hash_worker.setup_duplicate_scan(file_paths)
                initial_status = f"Scanning {len(file_paths)} files for duplicates..."
            elif operation_type == "compare":
                self.hash_worker.setup_external_comparison(file_paths, external_folder or "")
                initial_status = f"Comparing {len(file_paths)} files with external folder..."
            elif operation_type == "checksums":
                self.hash_worker.setup_checksum_calculation(file_paths)
                initial_status = f"Calculating checksums for {len(file_paths)} files..."
            else:
                raise ValueError(f"Unknown operation type: {operation_type}")

            # Pass the calculated total size to the worker to avoid duplicate calculation
            self.hash_worker.set_total_size(total_size)

            # Show dialog and start worker
            self.hash_dialog.set_status(initial_status)

            # Start progress tracking for size and time info with total size
            if hasattr(self.hash_dialog, "start_progress_tracking"):
                self.hash_dialog.start_progress_tracking(self._total_size_bytes)

            # Show dialog with smooth appearance to prevent shadow flicker
            from utils.dialog_utils import show_dialog_smooth

            show_dialog_smooth(self.hash_dialog)

            # Update main window status
            if hasattr(self.parent_window, "set_status"):
                self.parent_window.set_status(
                    initial_status, color=STATUS_COLORS["action_completed"], auto_reset=False
                )

            # Start worker thread
            self.hash_worker.start()

            # Connect signals to main window if available
            if hasattr(self.parent_window, "connect_hash_worker_signals"):
                self.parent_window.connect_hash_worker_signals()

        except Exception as e:
            logger.error(f"[HashManager] Error starting hash operation: {e}")
            from widgets.custom_message_dialog import CustomMessageDialog

            CustomMessageDialog.information(
                self.parent_window, "Error", f"Failed to start hash operation: {str(e)}"
            )

    def _cancel_hash_operation(self) -> None:
        """Cancel the current hash operation."""
        if hasattr(self, "hash_worker") and self.hash_worker:
            logger.info("[HashManager] Cancelling hash operation")
            self._operation_cancelled = True  # Set flag before cancelling
            self.hash_worker.cancel()

    def _on_hash_progress_updated(self, current_file: int, total_files: int, filename: str) -> None:
        """Handle hash worker progress updates."""
        if hasattr(self, "hash_dialog") and self.hash_dialog:
            # Use the unified progress method that respects the progress mode
            # For size-based progress, this will use the size data; for count-based, it will use file count
            if hasattr(self.hash_dialog, "update_progress"):
                # Pass both file count and size data - the widget will choose based on its mode
                self.hash_dialog.update_progress(
                    file_count=current_file,
                    total_files=total_files,
                    processed_bytes=getattr(self, "_last_processed_bytes", 0),
                    total_bytes=getattr(self, "_total_size_bytes", 0),
                )
            else:
                # Fallback to old method
                self.hash_dialog.set_progress(current_file, total_files)

            self.hash_dialog.set_count(current_file, total_files)
            self.hash_dialog.set_filename(filename)

    def _on_size_progress_updated(self, total_processed: int, total_size: int) -> None:
        """
        Handle overall size progress updates from hash worker.

        Debug tracking (2025): Added logging to monitor cumulative progress issues.
        Fixed integer overflow handling for large file operations (37GB+).
        Now supports 64-bit integers from hash worker.
        """
        if hasattr(self, "hash_dialog") and self.hash_dialog:
            # Convert to Python integers to handle 64-bit values from Qt signals
            total_processed = int(total_processed)
            total_size = int(total_size)

            # Debug: Track progress to identify reset issues - reduced logging
            if hasattr(self, "_last_processed_bytes"):
                if total_processed < 0:
                    # Integer overflow detected - log error and reset
                    logger.error(f"[HashProgress] Integer overflow detected: {total_processed}")
                    # Don't update with negative values
                    return
                elif total_processed < self._last_processed_bytes:
                    # Only warn if it's a significant backwards movement (not overflow)
                    diff = self._last_processed_bytes - total_processed
                    if diff > 1000000:  # Only warn for >1MB backwards movement
                        logger.warning(
                            f"[HashProgress] Significant progress regression: {total_processed:,} < {self._last_processed_bytes:,} (diff: {diff:,} bytes)"
                        )
                    # Remove minor progress adjustment logging to reduce spam
                # Remove regular progress update logging to reduce spam - only log issues
            else:
                logger.debug(
                    f"[HashProgress] Starting progress tracking: {total_processed:,}/{total_size:,} bytes",
                    extra={"dev_only": True},
                )

            self._last_processed_bytes = total_processed

            # Use the accurate size progress from the worker to update both progress bar and size info
            self.hash_dialog.update_progress(
                file_count=0,  # File count will be updated by _on_hash_progress_updated
                total_files=0,
                processed_bytes=total_processed,
                total_bytes=total_size,
            )

    def _on_file_hash_calculated(self, file_path: str) -> None:
        """Handle individual file hash calculation for real-time UI updates."""
        try:
            # Update file table icon for this specific file
            if hasattr(self.parent_window, "file_model") and self.parent_window.file_model:
                # Find the file in the model and update its icon
                for i, file_item in enumerate(self.parent_window.file_model.files):
                    if file_item.full_path == file_path:
                        # Emit dataChanged signal for the first column (icon column) only
                        index = self.parent_window.file_model.index(i, 0)
                        self.parent_window.file_model.dataChanged.emit(
                            index, index, [Qt.DecorationRole, Qt.ToolTipRole]
                        )  # type: ignore
                        logger.debug(
                            f"[HashWorker] Updated icon for: {os.path.basename(file_path)}",
                            extra={"dev_only": True},
                        )
                        break
        except Exception as e:
            logger.warning(f"[HashWorker] Error updating icon for {file_path}: {e}")

    def _on_duplicates_found(self, duplicates: dict, scope: str) -> None:
        """Handle duplicates found result."""
        self._show_duplicates_results(duplicates, scope)

    def _on_comparison_result(self, results: dict, external_folder: str) -> None:
        """Handle comparison result."""
        self._show_comparison_results(results, external_folder)

    def _on_checksums_calculated(self, hash_results: dict) -> None:
        """Handle checksums calculated result."""
        # Force restore cursor before showing results dialog
        from utils.cursor_helper import force_restore_cursor

        force_restore_cursor()

        # Check if this was a cancelled operation
        was_cancelled = self._operation_cancelled

        self._show_hash_results(hash_results, was_cancelled)

        # Reset the flag after showing results
        self._operation_cancelled = False

    def _on_hash_operation_finished(self, success: bool) -> None:
        """Handle hash operation completion."""
        if hasattr(self, "hash_dialog") and self.hash_dialog:
            # Keep dialog visible for a moment to show completion
            from utils.timer_manager import schedule_dialog_close

            schedule_dialog_close(self.hash_dialog.close, 500)

        # Refresh file table icons to show new hash status
        if hasattr(self.parent_window, "file_table_model") and self.parent_window.file_table_model:
            if hasattr(self.parent_window.file_table_model, "refresh_icons"):
                self.parent_window.file_table_model.refresh_icons()
                logger.debug(
                    "[EventHandler] Refreshed file table icons after hash operation",
                    extra={"dev_only": True},
                )

        # Notify preview manager about hash calculation completion
        if hasattr(self.parent_window, "preview_manager") and self.parent_window.preview_manager:
            self.parent_window.preview_manager.on_hash_calculation_completed()

        # Clean up worker
        if hasattr(self, "hash_worker") and self.hash_worker:
            self.hash_worker.quit()
            self.hash_worker.wait()
            self.hash_worker = None

        # Reset operation cancelled flag
        self._operation_cancelled = False

    def _on_hash_operation_error(self, error_message: str) -> None:
        """Handle hash operation error."""
        logger.error(f"[HashManager] Hash operation error: {error_message}")

        # Close dialog
        if hasattr(self, "hash_dialog") and self.hash_dialog:
            self.hash_dialog.close()

        # Show error message
        from widgets.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.information(
            self.parent_window, "Error", f"Hash operation failed: {error_message}"
        )

        # Update status
        if hasattr(self.parent_window, "set_status"):
            self.parent_window.set_status(
                "Hash operation failed", color=STATUS_COLORS["critical_error"], auto_reset=True
            )

        # Clean up worker
        if hasattr(self, "hash_worker") and self.hash_worker:
            self.hash_worker.quit()
            self.hash_worker.wait()
            self.hash_worker = None

    def _handle_compare_external(self, selected_files: list) -> None:
        """
        Handle comparison of selected files with an external folder.

        Args:
            selected_files: List of FileItem objects to compare
        """
        if not selected_files:
            logger.warning("[HashManager] No files selected for external comparison")
            return

        try:
            # Import Qt components
            from core.pyqt_imports import QFileDialog

            # Show folder picker dialog
            from utils.multiscreen_helper import get_existing_directory_on_parent_screen

            external_folder = get_existing_directory_on_parent_screen(
                self.parent_window,
                "Select folder to compare with",
                "",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
            )

            if not external_folder:
                logger.debug(
                    "[HashManager] User cancelled external folder selection",
                    extra={"dev_only": True},
                )
                return

            logger.info(
                f"[HashManager] Comparing {len(selected_files)} files with {external_folder}"
            )

            # Convert FileItem objects to file paths
            file_paths = [item.full_path for item in selected_files]

            # Always use worker thread with progress dialog for cancellation support
            # This is especially important for large files (videos) that may take time
            self._start_hash_operation("compare", file_paths, external_folder=external_folder)

        except Exception as e:
            logger.error(f"[HashManager] Error setting up external comparison: {e}")
            from widgets.custom_message_dialog import CustomMessageDialog

            CustomMessageDialog.information(
                self.parent_window, "Error", f"Failed to start external comparison: {str(e)}"
            )

    def _handle_calculate_hashes(self, selected_files: list) -> None:
        """
        Handle calculating and displaying checksums for selected files.

        Args:
            selected_files: List of FileItem objects to calculate hashes for
        """
        if not selected_files:
            logger.warning("[HashManager] No files selected for checksum calculation")
            return

        logger.info(f"[HashManager] Calculating checksums for {len(selected_files)} files")

        # Convert FileItem objects to file paths
        file_paths = [item.full_path for item in selected_files]

        if len(file_paths) == 1:
            # Single file - use wait cursor (fast, simple)
            self._calculate_single_file_hash_fast(selected_files[0])
        else:
            # Multiple files - use worker thread with progress dialog
            self._start_hash_operation("checksums", file_paths)

    def _calculate_single_file_hash_fast(self, file_item) -> None:
        """
        Calculate hash for a single small file using wait cursor (fast, no cancellation).

        Args:
            file_item: FileItem object to calculate hash for
        """
        from core.hash_manager import HashManager
        from utils.cursor_helper import wait_cursor

        try:
            hash_results = {}
            with wait_cursor():
                hash_manager = HashManager()
                file_hash = hash_manager.calculate_hash(file_item.full_path)

                if file_hash:
                    hash_results[file_item.full_path] = file_hash

            # Show results after cursor is restored
            self._show_hash_results(hash_results)

        except Exception as e:
            logger.error(f"[HashManager] Error calculating checksum: {e}")
            from widgets.custom_message_dialog import CustomMessageDialog

            CustomMessageDialog.information(
                self.parent_window, "Error", f"Failed to calculate checksum: {str(e)}"
            )

    def _show_duplicates_results(self, duplicates: dict, scope: str) -> None:
        """
        Show duplicate detection results to the user.

        Args:
            duplicates: Dictionary with hash as key and list of duplicate FileItem objects as value
            scope: Either "selected" or "all" for display purposes
        """
        if not duplicates:
            from widgets.custom_message_dialog import CustomMessageDialog

            CustomMessageDialog.information(
                self.parent_window,
                "Duplicate Detection Results",
                f"No duplicates found in {scope} files.",
            )
            if hasattr(self.parent_window, "set_status"):
                self.parent_window.set_status(
                    f"No duplicates found in {scope} files",
                    color=STATUS_COLORS["operation_success"],
                    auto_reset=True,
                )
            return

        # Build results message
        duplicate_count = sum(len(files) for files in duplicates.values())
        duplicate_groups = len(duplicates)

        message_lines = [f"Found {duplicate_count} duplicate files in {duplicate_groups} groups:\n"]

        for i, (hash_val, files) in enumerate(duplicates.items(), 1):
            message_lines.append(f"Group {i} ({len(files)} files):")
            for file_item in files:
                message_lines.append(f"  • {file_item.filename}")
            message_lines.append(f"  Hash: {hash_val[:16]}...")
            message_lines.append("")

        # Show results dialog
        from widgets.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.information(
            self.parent_window, "Duplicate Detection Results", "\n".join(message_lines)
        )

        # Update status
        if hasattr(self.parent_window, "set_status"):
            self.parent_window.set_status(
                f"Found {duplicate_count} duplicates in {duplicate_groups} groups",
                color=STATUS_COLORS["duplicate_found"],
                auto_reset=True,
            )

        logger.info(
            f"[HashManager] Showed duplicate results: {duplicate_count} files in {duplicate_groups} groups"
        )

    def _show_comparison_results(self, results: dict, external_folder: str) -> None:
        """
        Show external folder comparison results to the user.

        Args:
            results: Dictionary with comparison results
            external_folder: Path to the external folder that was compared
        """
        if not results:
            from widgets.custom_message_dialog import CustomMessageDialog

            CustomMessageDialog.information(
                self.parent_window,
                "External Comparison Results",
                f"No matching files found in:\n{external_folder}",
            )
            if hasattr(self.parent_window, "set_status"):
                self.parent_window.set_status(
                    "No matching files found", color=STATUS_COLORS["no_action"], auto_reset=True
                )
            return

        # Count matches and differences
        matches = sum(1 for r in results.values() if r["is_same"])
        differences = len(results) - matches

        # Build results message
        message_lines = [
            f"Comparison with: {external_folder}\n",
            f"Files compared: {len(results)}",
            f"Identical: {matches}",
            f"Different: {differences}\n",
        ]

        if differences > 0:
            message_lines.append("Different files:")
            for filename, data in results.items():
                if not data["is_same"]:
                    message_lines.append(f"  • {filename}")

        if matches > 0:
            message_lines.append("\nIdentical files:")
            for filename, data in results.items():
                if data["is_same"]:
                    message_lines.append(f"  • {filename}")

        # Show results dialog
        from widgets.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.information(
            self.parent_window, "External Comparison Results", "\n".join(message_lines)
        )

        # Update status
        if hasattr(self.parent_window, "set_status"):
            if differences > 0:
                self.parent_window.set_status(
                    f"Found {differences} different files, {matches} identical",
                    color=STATUS_COLORS["alert_notice"],
                    auto_reset=True,
                )
            else:
                self.parent_window.set_status(
                    f"All {matches} files are identical",
                    color=STATUS_COLORS["operation_success"],
                    auto_reset=True,
                )

        logger.info(
            f"[HashManager] Showed comparison results: {matches} identical, {differences} different"
        )

    def _show_hash_results(self, hash_results: dict, was_cancelled: bool = False) -> None:
        """
        Show checksum calculation results to the user.

        Args:
            hash_results: Dictionary with filename as key and hash data as value
            was_cancelled: Whether the operation was cancelled (for partial results)
        """
        if not hash_results:
            from widgets.custom_message_dialog import CustomMessageDialog

            if was_cancelled:
                CustomMessageDialog.information(
                    self.parent_window,
                    "Checksum Results",
                    "Operation was cancelled before any checksums could be calculated.",
                )
            else:
                CustomMessageDialog.information(
                    self.parent_window, "Checksum Results", "No checksums could be calculated."
                )
            if hasattr(self.parent_window, "set_status"):
                status_msg = "Operation cancelled" if was_cancelled else "No checksums calculated"
                self.parent_window.set_status(
                    status_msg, color=STATUS_COLORS["no_action"], auto_reset=True
                )
            return

        # Build results message
        if was_cancelled:
            message_lines = [
                f"CRC32 Checksums for {len(hash_results)} files (partial results - operation was cancelled):\n"
            ]
        else:
            message_lines = [f"CRC32 Checksums for {len(hash_results)} files:\n"]

        for file_path, hash_value in hash_results.items():
            import os

            filename = os.path.basename(file_path)
            message_lines.append(f"{filename}:")
            message_lines.append(f"  {hash_value}\n")

        # Show results dialog
        from widgets.custom_message_dialog import CustomMessageDialog

        dialog_title = "Checksum Results (Partial)" if was_cancelled else "Checksum Results"
        CustomMessageDialog.information(self.parent_window, dialog_title, "\n".join(message_lines))

        # Update status
        if hasattr(self.parent_window, "set_status"):
            if was_cancelled:
                self.parent_window.set_status(
                    f"Calculated checksums for {len(hash_results)} files (cancelled)",
                    color=STATUS_COLORS["hash_success"],
                    auto_reset=True,
                )
            else:
                self.parent_window.set_status(
                    f"Calculated checksums for {len(hash_results)} files",
                    color=STATUS_COLORS["hash_success"],
                    auto_reset=True,
                )

        logger.info(
            f"[HashManager] Showed checksum results for {len(hash_results)} files"
            + (" (cancelled)" if was_cancelled else "")
        )

    def _check_selected_files_have_metadata(self, selected_files: list) -> bool:
        """Check if any of the selected files have metadata."""
        status = self.check_files_status(
            files=selected_files, check_type="metadata", extended=False
        )
        return status["count"] > 0  # Any files have metadata

    def _check_any_files_have_metadata(self) -> bool:
        """Check if any file in the current folder has metadata."""
        status = self.check_files_status(
            files=None, check_type="metadata", extended=False, scope="all"
        )
        return status["count"] > 0  # Any files have metadata

    def _file_has_metadata(self, file_item) -> bool:
        return has_metadata(file_item.full_path)

    def _handle_export_metadata(self, file_items: list, scope: str) -> None:
        """Handle metadata export dialog and process."""
        from PyQt5.QtWidgets import (
            QComboBox,
            QDialog,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QVBoxLayout,
        )

        # Create export dialog
        dialog = QDialog(self.parent_window)
        dialog.setWindowTitle(f"Export Metadata - {scope.title()} Files")
        dialog.setModal(True)
        dialog.resize(400, 200)

        layout = QVBoxLayout(dialog)

        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Export Format:"))

        format_combo = QComboBox()
        format_combo.addItems(["JSON (Structured)", "Markdown (Human Readable)"])
        format_layout.addWidget(format_combo)

        layout.addLayout(format_layout)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        export_button = QPushButton("Export...")
        export_button.clicked.connect(
            lambda: self._execute_export(dialog, format_combo, file_items, scope)
        )
        export_button.setDefault(True)
        button_layout.addWidget(export_button)

        layout.addLayout(button_layout)

        # Show dialog
        dialog.exec_()

    def _execute_export(self, dialog, format_combo, file_items: list, scope: str) -> None:
        """Execute the actual export process."""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox

        # Get format
        format_map = {0: "json", 1: "markdown"}
        format_type = format_map.get(format_combo.currentIndex(), "json")

        # Get output directory
        from utils.multiscreen_helper import get_existing_directory_on_parent_screen

        output_dir = get_existing_directory_on_parent_screen(
            dialog, f"Select Export Directory - {scope.title()} Files", "", QFileDialog.ShowDirsOnly
        )

        if not output_dir:
            return

        dialog.accept()

        # Perform export
        try:
            from utils.metadata_exporter import MetadataExporter

            exporter = MetadataExporter(self.parent_window)

            # Export based on scope
            if scope == "selected":
                success = exporter.export_files(file_items, output_dir, format_type)
            else:
                success = exporter.export_all_files(output_dir, format_type)

            # Show result
            if success:
                QMessageBox.information(
                    self.parent_window,
                    "Export Successful",
                    f"Metadata exported successfully to:\n{output_dir}",
                )
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Export Failed",
                    "Failed to export metadata. Check the logs for details.",
                )

        except Exception as e:
            logger.exception(f"[EventHandler] Export error: {e}")
            QMessageBox.critical(
                self.parent_window, "Export Error", f"An error occurred during export:\n{str(e)}"
            )

    # === Metadata Field Compatibility Detection ===

    def _check_metadata_field_compatibility(self, selected_files: list, field_name: str) -> bool:
        """
        Check if all selected files support a specific metadata field.
        Uses exiftool metadata to determine compatibility.

        Args:
            selected_files: List of FileItem objects to check
            field_name: Name of the metadata field to check support for

        Returns:
            bool: True if ALL selected files support the field, False otherwise
        """
        if not selected_files:
            logger.debug(
                f"[FieldCompatibility] No files provided for {field_name} compatibility check",
                extra={"dev_only": True},
            )
            return False

        # Check if all files have metadata loaded
        files_with_metadata = [f for f in selected_files if self._file_has_metadata(f)]
        if len(files_with_metadata) != len(selected_files):
            logger.debug(
                f"[FieldCompatibility] Not all files have metadata loaded for {field_name} check",
                extra={"dev_only": True},
            )
            return False

        # Check if all files support the specific field
        supported_count = 0
        for file_item in selected_files:
            if self._file_supports_field(file_item, field_name):
                supported_count += 1

        # Enable only if ALL selected files support the field
        result = supported_count == len(selected_files)
        logger.debug(
            f"[FieldCompatibility] {field_name} support: {supported_count}/{len(selected_files)} files, enabled: {result}",
            extra={"dev_only": True},
        )
        return result

    def _file_supports_field(self, file_item, field_name: str) -> bool:
        """
        Check if a file supports a specific metadata field.
        Uses exiftool's field availability information from metadata cache.

        Args:
            file_item: FileItem object to check
            field_name: Name of the metadata field

        Returns:
            bool: True if the file supports the field, False otherwise
        """
        try:
            # Get metadata from cache
            cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
            if not cache_entry or not hasattr(cache_entry, "data") or not cache_entry.data:
                logger.debug(
                    f"[FieldSupport] No metadata cache for {file_item.filename}",
                    extra={"dev_only": True},
                )
                return False

            # Field support mapping based on exiftool output
            field_support_map = {
                "Title": ["EXIF:ImageDescription", "XMP:Title", "IPTC:Headline", "XMP:Description"],
                "Artist": ["EXIF:Artist", "XMP:Creator", "IPTC:By-line", "XMP:Author"],
                "Author": [
                    "EXIF:Artist",
                    "XMP:Creator",
                    "IPTC:By-line",
                    "XMP:Author",
                ],  # Same as Artist
                "Copyright": [
                    "EXIF:Copyright",
                    "XMP:Rights",
                    "IPTC:CopyrightNotice",
                    "XMP:UsageTerms",
                ],
                "Description": [
                    "EXIF:ImageDescription",
                    "XMP:Description",
                    "IPTC:Caption-Abstract",
                    "XMP:Title",
                ],
                "Keywords": ["XMP:Keywords", "IPTC:Keywords", "XMP:Subject"],
                "Rotation": ["EXIF:Orientation"],  # Images/Videos only
            }

            # Get supported fields for this field name
            supported_fields = field_support_map.get(field_name, [])
            if not supported_fields:
                logger.debug(
                    f"[FieldSupport] Unknown field name: {field_name}", extra={"dev_only": True}
                )
                return False

            # Check if any of the supported fields exist in metadata OR could be written
            metadata = cache_entry.data

            # Check existing fields
            for field in supported_fields:
                if field in metadata:
                    logger.debug(
                        f"[FieldSupport] {file_item.filename} supports {field_name} via existing {field}"
                    )
                    return True

            # For files with metadata, we can generally write standard fields
            # Check if file type supports the field category
            file_type_support = self._get_file_type_field_support(file_item, metadata)

            supports_field = field_name in file_type_support
            if supports_field:
                logger.debug(
                    f"[FieldSupport] {file_item.filename} supports {field_name} via file type compatibility"
                )
            else:
                logger.debug(f"[FieldSupport] {file_item.filename} does not support {field_name}")

            return supports_field

        except Exception as e:
            logger.debug(
                f"[FieldSupport] Error checking field support for {getattr(file_item, 'filename', 'unknown')}: {e}"
            )
            return False

    def _get_file_type_field_support(self, file_item, metadata: dict) -> set:
        """
        Determine which metadata fields a file type supports based on its metadata.

        Args:
            file_item: FileItem object
            metadata: Metadata dictionary from exiftool

        Returns:
            set: Set of supported field names
        """
        try:
            # Basic fields that most files with metadata support
            basic_fields = {"Title", "Description", "Keywords"}

            # Check for image/video specific fields
            image_video_fields = {"Artist", "Author", "Copyright", "Rotation"}

            # Determine file type from metadata or extension
            is_image = self._is_image_file(file_item, metadata)
            is_video = self._is_video_file(file_item, metadata)
            is_audio = self._is_audio_file(file_item, metadata)
            is_document = self._is_document_file(file_item, metadata)

            supported_fields = basic_fields.copy()

            if is_image or is_video:
                # Images and videos support creative fields and rotation
                supported_fields.update(image_video_fields)
            elif is_audio:
                # Audio files support creative fields but not rotation
                supported_fields.update({"Artist", "Author", "Copyright"})
            elif is_document:
                # Documents support author and copyright but not rotation
                supported_fields.update({"Author", "Copyright"})

            return supported_fields

        except Exception as e:
            logger.debug(f"[FileTypeSupport] Error determining file type support: {e}")
            # Return basic fields as fallback
            return {"Title", "Description", "Keywords"}

    def _is_image_file(self, file_item, metadata: dict) -> bool:
        """Check if file is an image based on metadata and extension."""
        # Check metadata for image indicators
        if any(key.startswith(("EXIF:", "JFIF:", "PNG:", "GIF:")) for key in metadata):
            return True

        # Check file extension as fallback
        if hasattr(file_item, "filename"):
            ext = file_item.filename.lower().split(".")[-1] if "." in file_item.filename else ""
            return ext in {
                "jpg",
                "jpeg",
                "png",
                "gif",
                "bmp",
                "tiff",
                "tif",
                "webp",
                "heic",
                "raw",
                "cr2",
                "nef",
                "arw",
            }

        return False

    def _is_video_file(self, file_item, metadata: dict) -> bool:
        """Check if file is a video based on metadata and extension."""
        # Check metadata for video indicators
        if any(key.startswith(("QuickTime:", "Matroska:", "RIFF:", "MPEG:")) for key in metadata):
            return True

        # Check file extension as fallback
        if hasattr(file_item, "filename"):
            ext = file_item.filename.lower().split(".")[-1] if "." in file_item.filename else ""
            return ext in {
                "mp4",
                "avi",
                "mkv",
                "mov",
                "wmv",
                "flv",
                "webm",
                "m4v",
                "3gp",
                "mpg",
                "mpeg",
            }

        return False

    def _is_audio_file(self, file_item, metadata: dict) -> bool:
        """Check if file is an audio file based on metadata and extension."""
        # Check metadata for audio indicators
        if any(key.startswith(("ID3:", "FLAC:", "Vorbis:", "APE:")) for key in metadata):
            return True

        # Check file extension as fallback
        if hasattr(file_item, "filename"):
            ext = file_item.filename.lower().split(".")[-1] if "." in file_item.filename else ""
            return ext in {"mp3", "flac", "wav", "ogg", "aac", "m4a", "wma", "opus"}

        return False

    def _is_document_file(self, file_item, metadata: dict) -> bool:
        """Check if file is a document based on metadata and extension."""
        # Check metadata for document indicators
        if any(key.startswith(("PDF:", "XMP-pdf:", "XMP-x:")) for key in metadata):
            return True

        # Check file extension as fallback
        if hasattr(file_item, "filename"):
            ext = file_item.filename.lower().split(".")[-1] if "." in file_item.filename else ""
            return ext in {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp"}

        return False

    def _get_preferred_field_standard(self, file_item, field_name: str) -> str | None:
        """
        Get the preferred metadata standard for a field based on file type and existing metadata.
        Uses exiftool's field hierarchy and existing field availability.

        Args:
            file_item: FileItem object
            field_name: Name of the metadata field

        Returns:
            str: Preferred field standard name (e.g., "XMP:Title") or None if not supported
        """
        try:
            cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
            if not cache_entry or not hasattr(cache_entry, "data"):
                return None

            # Priority order (exiftool's preference: XMP > IPTC > EXIF)
            field_priorities = {
                "Title": ["XMP:Title", "IPTC:Headline", "EXIF:ImageDescription", "XMP:Description"],
                "Artist": ["XMP:Creator", "IPTC:By-line", "EXIF:Artist", "XMP:Author"],
                "Author": ["XMP:Creator", "IPTC:By-line", "EXIF:Artist", "XMP:Author"],
                "Copyright": [
                    "XMP:Rights",
                    "IPTC:CopyrightNotice",
                    "EXIF:Copyright",
                    "XMP:UsageTerms",
                ],
                "Description": [
                    "XMP:Description",
                    "IPTC:Caption-Abstract",
                    "EXIF:ImageDescription",
                ],
                "Keywords": ["XMP:Keywords", "IPTC:Keywords", "XMP:Subject"],
                "Rotation": ["EXIF:Orientation"],
            }

            priorities = field_priorities.get(field_name, [])
            if not priorities:
                return None

            metadata = cache_entry.data

            # Return the first existing field
            for field in priorities:
                if field in metadata:
                    logger.debug(
                        f"[FieldStandard] Using existing {field} for {field_name} in {file_item.filename}"
                    )
                    return field

            # Return preferred default if none exist (first in priority list)
            preferred = priorities[0]
            logger.debug(
                f"[FieldStandard] Using preferred {preferred} for {field_name} in {file_item.filename}"
            )
            return preferred

        except Exception as e:
            logger.debug(f"[FieldStandard] Error getting preferred standard: {e}")
            return None

    # === Metadata Field Editing Handlers ===

    def _handle_metadata_field_edit(self, selected_files: list, field_name: str) -> None:
        """
        Handle metadata field editing for selected files.

        Args:
            selected_files: List of FileItem objects to edit
            field_name: Name of the field to edit (Title, Artist, etc.)
        """
        if not selected_files:
            logger.warning(f"[MetadataEdit] No files selected for {field_name} editing")
            return

        logger.info(f"[MetadataEdit] Starting {field_name} editing for {len(selected_files)} files")

        try:
            # Get current value (for single file editing)
            current_value = ""
            if len(selected_files) == 1:
                current_value = self._get_current_field_value(selected_files[0], field_name) or ""

            # Import and show the metadata edit dialog
            from widgets.metadata_edit_dialog import MetadataEditDialog

            success, new_value, files_to_modify = MetadataEditDialog.edit_metadata_field(
                parent=self.parent_window,
                selected_files=selected_files,
                metadata_cache=self.parent_window.metadata_cache,
                field_name=field_name,
                current_value=current_value,
            )

            if not success:
                logger.debug(f"[MetadataEdit] User cancelled {field_name} editing")
                return

            if not files_to_modify:
                logger.debug(f"[MetadataEdit] No files selected for {field_name} modification")
                return

            # Apply the changes
            self._apply_metadata_field_changes(files_to_modify, field_name, new_value)

            # Update status
            if hasattr(self.parent_window, "set_status"):
                from config import STATUS_COLORS

                status_msg = f"Updated {field_name} for {len(files_to_modify)} file(s)"
                self.parent_window.set_status(
                    status_msg, color=STATUS_COLORS["operation_success"], auto_reset=True
                )

            logger.info(
                f"[MetadataEdit] Successfully updated {field_name} for {len(files_to_modify)} files"
            )

        except ImportError as e:
            logger.error(f"[MetadataEdit] Failed to import MetadataEditDialog: {e}")
            from utils.dialog_utils import show_error_message

            show_error_message(
                self.parent_window,
                "Error",
                "Metadata editing dialog is not available. Please check the installation.",
            )
        except Exception as e:
            logger.exception(f"[MetadataEdit] Unexpected error during {field_name} editing: {e}")
            from utils.dialog_utils import show_error_message

            show_error_message(
                self.parent_window,
                "Error",
                f"An error occurred during {field_name} editing: {str(e)}",
            )

    def _get_current_field_value(self, file_item, field_name: str) -> str:
        """
        Get the current value of a metadata field for a file.

        Args:
            file_item: FileItem object
            field_name: Name of the field

        Returns:
            str: Current value or empty string if not found
        """
        try:
            if not self.parent_window.metadata_cache:
                return ""

            # Check metadata cache first
            cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
            if cache_entry and hasattr(cache_entry, "data"):
                # Try different field standards based on field name
                standards = self._get_field_standards_for_reading(field_name)
                for standard in standards:
                    value = cache_entry.data.get(standard)
                    if value:
                        return str(value)

            # Fallback to file metadata
            if hasattr(file_item, "metadata") and file_item.metadata:
                standards = self._get_field_standards_for_reading(field_name)
                for standard in standards:
                    value = file_item.metadata.get(standard)
                    if value:
                        return str(value)

            return ""

        except Exception as e:
            logger.debug(f"[MetadataEdit] Error getting current {field_name} value: {e}")
            return ""

    def _get_field_standards_for_reading(self, field_name: str) -> list:
        """Get the metadata standards for reading a field (in priority order)."""
        field_standards = {
            "Title": ["XMP:Title", "IPTC:Headline", "EXIF:ImageDescription"],
            "Artist": ["XMP:Creator", "IPTC:By-line", "EXIF:Artist"],
            "Author": ["XMP:Creator", "IPTC:By-line", "EXIF:Artist"],
            "Copyright": ["XMP:Rights", "IPTC:CopyrightNotice", "EXIF:Copyright"],
            "Description": ["XMP:Description", "IPTC:Caption-Abstract", "EXIF:ImageDescription"],
            "Keywords": ["XMP:Keywords", "IPTC:Keywords"],
        }
        return field_standards.get(field_name, [])

    def _apply_metadata_field_changes(
        self, files_to_modify: list, field_name: str, new_value: str
    ) -> None:
        """
        Apply metadata field changes to files by updating the metadata tree view.
        This ensures the changes are properly tracked and can be saved later.
        """
        if not hasattr(self.parent_window, "metadata_tree_view"):
            logger.warning("[EventHandler] No metadata tree view available for field changes")
            return

        metadata_tree_view = self.parent_window.metadata_tree_view

        # Apply changes to each file
        for file_item in files_to_modify:
            logger.debug(
                f"[EventHandler] Applying {field_name} change to {file_item.filename}: '{new_value}'"
            )

            # Get the preferred field standard for this file
            field_standard = self._get_preferred_field_standard(file_item, field_name)
            if not field_standard:
                logger.warning(
                    f"[EventHandler] No field standard found for {field_name} in {file_item.filename}"
                )
                continue

            # Apply the change through metadata tree view
            metadata_tree_view.apply_field_change_to_file(
                file_item.full_path, field_standard, new_value
            )

        logger.info(f"[EventHandler] Applied {field_name} changes to {len(files_to_modify)} files")

    def _check_files_have_metadata_type(self, files: list, extended: bool) -> bool:
        """Check if all files have the specified type of metadata (basic or extended)."""
        status = self.check_files_status(files=files, check_type="metadata", extended=extended)
        return status["has_status"]  # All files have the metadata type

    def _check_all_files_have_metadata_type(self, extended: bool) -> bool:
        """Check if all files in the current folder have the specified type of metadata."""
        status = self.check_files_status(
            files=None, check_type="metadata", extended=extended, scope="all"
        )
        return status["has_status"]  # All files have the metadata type

    def _file_has_metadata_type(self, file_item, extended: bool) -> bool:
        """Check if a file has the specified type of metadata (basic or extended)."""
        from utils.metadata_cache_helper import get_metadata_cache_helper

        cache_helper = get_metadata_cache_helper(parent_window=self.parent_window)
        return cache_helper.has_metadata(file_item, extended=extended)

    # =====================================
    # Unified File Status Checking System
    # =====================================

    def check_files_status(
        self,
        files: list = None,
        check_type: str = "metadata",
        extended: bool = False,
        scope: str = "selected",
    ) -> dict:
        """
        Unified file status checking for metadata and hash operations.

        Args:
            files: List of files to check (None for all files)
            check_type: 'metadata' or 'hash'
            extended: For metadata checks, whether to check for extended metadata
            scope: 'selected' or 'all' (used when files is None)

        Returns:
            dict: {
                'has_status': bool,  # True if files have the requested status
                'count': int,        # Number of files with status
                'total': int,        # Total number of files checked
                'files_with_status': list,  # Files that have the status
                'files_without_status': list  # Files that don't have the status
            }
        """
        # Determine which files to check
        if files is None:
            if scope == "all" and hasattr(self.parent_window, "file_model"):
                files = self.parent_window.file_model.files or []
            else:
                files = []

        if not files:
            return {
                "has_status": False,
                "count": 0,
                "total": 0,
                "files_with_status": [],
                "files_without_status": [],
            }

        files_with_status = []
        files_without_status = []

        # Check each file
        for file_item in files:
            if check_type == "metadata":
                if extended:
                    has_status = self._file_has_metadata_type(file_item, extended=True)
                else:
                    # For basic metadata, accept either basic or extended (extended includes basic)
                    has_status = self._file_has_metadata_type(
                        file_item, extended=False
                    ) or self._file_has_metadata_type(file_item, extended=True)
            elif check_type == "hash":
                has_status = self._file_has_hash(file_item)
            else:
                has_status = False

            if has_status:
                files_with_status.append(file_item)
            else:
                files_without_status.append(file_item)

        return {
            "has_status": len(files_with_status) == len(files),  # All files have status
            "count": len(files_with_status),
            "total": len(files),
            "files_with_status": files_with_status,
            "files_without_status": files_without_status,
        }

    def _check_files_have_hashes(self, files: list) -> bool:
        """Check if all files have hash values calculated."""
        status = self.check_files_status(files=files, check_type="hash")
        return status["has_status"]  # All files have hashes

    # =====================================
    # Convenience Methods Using Unified System
    # =====================================

    def get_files_without_metadata(
        self, files: list = None, extended: bool = False, scope: str = "selected"
    ) -> list:
        """Get list of files that don't have metadata."""
        status = self.check_files_status(
            files=files, check_type="metadata", extended=extended, scope=scope
        )
        return status["files_without_status"]

    def get_files_without_hashes(self, files: list = None, scope: str = "selected") -> list:
        """Get list of files that don't have hash values."""
        status = self.check_files_status(files=files, check_type="hash", scope=scope)
        return status["files_without_status"]

    def get_metadata_status_summary(self, files: list = None, scope: str = "selected") -> dict:
        """Get comprehensive metadata status summary."""
        basic_status = self.check_files_status(
            files=files, check_type="metadata", extended=False, scope=scope
        )
        extended_status = self.check_files_status(
            files=files, check_type="metadata", extended=True, scope=scope
        )

        return {
            "total_files": basic_status["total"],
            "basic_metadata": {
                "count": basic_status["count"],
                "percentage": (
                    (basic_status["count"] / basic_status["total"] * 100)
                    if basic_status["total"] > 0
                    else 0
                ),
            },
            "extended_metadata": {
                "count": extended_status["count"],
                "percentage": (
                    (extended_status["count"] / extended_status["total"] * 100)
                    if extended_status["total"] > 0
                    else 0
                ),
            },
            "files_needing_basic": basic_status["files_without_status"],
            "files_needing_extended": extended_status["files_without_status"],
        }

    def _file_has_hash(self, file_item) -> bool:
        return has_hash(file_item.full_path)

    def _analyze_metadata_state(self, files: list) -> dict:
        """
        Analyze the metadata state of files to determine smart context menu options.

        Args:
            files: List of FileItem objects to analyze

        Returns:
            dict: Analysis results with enable/disable logic for menu items
        """
        if not files:
            return {
                "enable_fast_selected": False,
                "enable_extended_selected": False,
                "fast_label": "Load Fast Metadata",
                "extended_label": "Load Extended Metadata",
                "fast_tooltip": "No files selected",
                "extended_tooltip": "No files selected",
            }

        # Analyze each file's metadata state
        no_metadata = []
        has_fast = []
        has_extended = []

        for file_item in files:
            if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
                if entry and entry.data:
                    if entry.is_extended:
                        has_extended.append(file_item)
                    else:
                        has_fast.append(file_item)
                else:
                    no_metadata.append(file_item)
            else:
                no_metadata.append(file_item)

        total = len(files)
        no_count = len(no_metadata)
        fast_count = len(has_fast)
        extended_count = len(has_extended)

        # Determine enable states and labels based on smart logic
        enable_fast = False
        enable_extended = False
        fast_label = "Load Fast Metadata"
        extended_label = "Load Extended Metadata"
        fast_tooltip = ""
        extended_tooltip = ""

        if no_count == total:
            # All files have no metadata
            enable_fast = True
            enable_extended = True
            fast_tooltip = f"Load fast metadata for {total} file(s)"
            extended_tooltip = f"Load extended metadata for {total} file(s)"

        elif extended_count == total:
            # All files have extended metadata - nothing to do
            enable_fast = False
            enable_extended = False
            fast_tooltip = "All files already have extended metadata (higher level)"
            extended_tooltip = "All files already have extended metadata"

        elif fast_count == total:
            # All files have fast metadata - can upgrade to extended
            enable_fast = False
            enable_extended = True
            fast_tooltip = "All files already have fast metadata"
            extended_tooltip = f"Upgrade {total} file(s) to extended metadata"
            extended_label = "Upgrade to Extended Metadata"

        elif no_count > 0:
            # Some files have no metadata - can load both types
            enable_fast = True
            enable_extended = True

            if fast_count > 0 or extended_count > 0:
                # Mixed state
                fast_tooltip = f"Load fast metadata for {no_count} file(s) without metadata"
                extended_tooltip = f"Load extended metadata for {no_count} file(s) without metadata"
                if fast_count > 0:
                    extended_tooltip += f" and upgrade {fast_count} file(s) from fast"
            else:
                fast_tooltip = f"Load fast metadata for {no_count} file(s)"
                extended_tooltip = f"Load extended metadata for {no_count} file(s)"

        elif fast_count > 0 and extended_count > 0:
            # Mixed fast and extended - can upgrade fast to extended
            enable_fast = False
            enable_extended = True
            fast_tooltip = "Some files have fast, some have extended metadata"
            extended_tooltip = f"Upgrade {fast_count} file(s) from fast to extended metadata"
            extended_label = "Upgrade Fast to Extended"

        return {
            "enable_fast_selected": enable_fast,
            "enable_extended_selected": enable_extended,
            "fast_label": fast_label,
            "extended_label": extended_label,
            "fast_tooltip": fast_tooltip,
            "extended_tooltip": extended_tooltip,
            "stats": {
                "total": total,
                "no_metadata": no_count,
                "fast": fast_count,
                "extended": extended_count,
            },
        }

    def _analyze_hash_state(self, files: list) -> dict:
        """
        Analyze the hash state of files to determine smart hash menu options.

        Args:
            files: List of FileItem objects to analyze

        Returns:
            dict: Analysis results with enable/disable logic for hash menu items
        """
        if not files:
            return {
                "enable_selected": False,
                "enable_all": False,
                "selected_label": "Calculate checksums for selection",
                "all_label": "Calculate checksums for all files",
                "selected_tooltip": "No files selected",
                "all_tooltip": "No files available",
            }

        start_time = time.time()

        # Use batch query to check which files have hashes
        files_with_hash = []
        files_without_hash = []

        try:
            # Get file paths
            file_paths = [file_item.full_path for file_item in files]

            # Use batch query to get files with hashes
            if hasattr(self.parent_window, "hash_cache") and hasattr(
                self.parent_window.hash_cache, "get_files_with_hash_batch"
            ):
                files_with_hash_paths = self.parent_window.hash_cache.get_files_with_hash_batch(
                    file_paths, "CRC32"
                )
                files_with_hash_set = set(files_with_hash_paths)

                # Categorize files based on batch query results
                for file_item in files:
                    if file_item.full_path in files_with_hash_set:
                        files_with_hash.append(file_item)
                    else:
                        files_without_hash.append(file_item)

                elapsed_time = time.time() - start_time
                logger.debug(
                    f"[EventHandler] Batch hash check completed in {elapsed_time:.3f}s: {len(files_with_hash)}/{len(files)} files have hashes"
                )
            else:
                # Fallback to individual checking
                for file_item in files:
                    if self._file_has_hash(file_item):
                        files_with_hash.append(file_item)
                    else:
                        files_without_hash.append(file_item)

                elapsed_time = time.time() - start_time
                logger.debug(
                    f"[EventHandler] Individual hash check completed in {elapsed_time:.3f}s: {len(files_with_hash)}/{len(files)} files have hashes"
                )

        except Exception as e:
            logger.warning(
                f"[EventHandler] Batch hash check failed, falling back to individual checks: {e}"
            )
            # Fallback to individual checking
            for file_item in files:
                if self._file_has_hash(file_item):
                    files_with_hash.append(file_item)
                else:
                    files_without_hash.append(file_item)

            elapsed_time = time.time() - start_time
            logger.debug(
                f"[EventHandler] Fallback hash check completed in {elapsed_time:.3f}s: {len(files_with_hash)}/{len(files)} files have hashes"
            )

        total = len(files)
        with_hash_count = len(files_with_hash)
        without_hash_count = len(files_without_hash)

        # Determine enable states and labels
        enable_selected = without_hash_count > 0  # Enable if any files don't have hash
        selected_label = "Calculate checksums for selection"
        selected_tooltip = ""

        if without_hash_count == 0:
            # All files have hashes
            selected_tooltip = f"All {total} file(s) already have checksums calculated"
        elif without_hash_count == total:
            # No files have hashes
            selected_tooltip = f"Calculate checksums for {total} file(s)"
        else:
            # Mixed state
            selected_tooltip = (
                f"Calculate checksums for {without_hash_count} of {total} file(s) that need them"
            )

        return {
            "enable_selected": enable_selected,
            "selected_label": selected_label,
            "selected_tooltip": selected_tooltip,
            "stats": {
                "total": total,
                "with_hash": with_hash_count,
                "without_hash": without_hash_count,
            },
        }

    def _get_simple_metadata_analysis(self) -> dict:
        """Get simple metadata analysis for all files without detailed scanning."""
        return {
            "enable_fast_selected": True,
            "enable_extended_selected": True,
            "fast_label": "Load Fast Metadata",
            "extended_label": "Load Extended Metadata",
            "fast_tooltip": "Load fast metadata for all files",
            "extended_tooltip": "Load extended metadata for all files",
        }

    def _get_simple_hash_analysis(self) -> dict:
        """Get simple hash analysis for all files without detailed scanning."""
        return {
            "enable_selected": True,
            "selected_label": "Calculate checksums for all files",
            "selected_tooltip": "Calculate checksums for all files",
        }
