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
from core.theme_manager import get_theme_manager
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

        # Delegate hash operations to specialized manager
        from core.hash_operations_manager import HashOperationsManager

        self.hash_ops = HashOperationsManager(parent_window)

        # Delegate metadata operations to specialized manager
        from core.metadata_operations_manager import MetadataOperationsManager

        self.metadata_ops = MetadataOperationsManager(parent_window)

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

        # Get theme colors from ThemeManager
        theme = get_theme_manager()

        # Enhanced styling for better appearance and spacing
        menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: {theme.get_color('menu_background')};
                color: {theme.get_color('menu_text')};
                border: none;
                border-radius: 8px;
                font-family: "Inter", "Segoe UI", Arial, sans-serif;
                font-size: 9pt;
                padding: 6px 4px;
            }}
            QMenu::item {{
                background-color: transparent;
                padding: 3px 16px 3px 8px;
                margin: 1px 2px;
                border-radius: 4px;
                min-height: 16px;
                icon-size: 16px;
            }}
            QMenu::item:selected {{
                background-color: {theme.get_color('menu_selected_bg')};
                color: {theme.get_color('menu_selected_text')};
            }}
            QMenu::item:disabled {{
                color: {theme.get_color('menu_disabled_text')};
            }}
            QMenu::icon {{
                padding-left: 6px;
                padding-right: 6px;
            }}
            QMenu::separator {{
                background-color: {theme.get_color('separator')};
                height: 1px;
                margin: 4px 8px;
            }}
        """
        )

        # Smart Metadata actions - only analyze selected files for speed
        selected_analysis = self._analyze_metadata_state(selected_files)

        # === SELECTION ACTIONS (First in menu) ===
        action_select_all = create_action_with_shortcut(
            get_menu_icon("check-square"), "Select All", "Ctrl+A"
        )
        action_invert = create_action_with_shortcut(
            get_menu_icon("refresh-cw"), "Invert Selection", "Ctrl+I"
        )
        action_deselect_all = create_action_with_shortcut(
            get_menu_icon("square"), "Deselect All", "Ctrl+Shift+A"
        )

        menu.addAction(action_select_all)
        menu.addAction(action_invert)
        menu.addAction(action_deselect_all)

        menu.addSeparator()

        # === METADATA OPERATIONS (Selection-only) ===
        # Use simple analysis for all files to avoid performance issues
        # all_files_analysis = self._get_simple_metadata_analysis()

        # Create actions with clean labels (selection-only pattern)
        action_load_fast = create_action_with_shortcut(
            get_menu_icon("file"), "Load Fast Metadata", "Ctrl+M"
        )
        action_load_extended = create_action_with_shortcut(
            get_menu_icon("file-plus"), "Load Extended Metadata", "Ctrl+E"
        )

        menu.addAction(action_load_fast)
        menu.addAction(action_load_extended)

        # Smart enable/disable logic based on analysis
        action_load_fast.setEnabled(has_selection and selected_analysis["enable_fast_selected"])
        action_load_extended.setEnabled(
            has_selection and selected_analysis["enable_extended_selected"]
        )

        # Set smart tooltips with selection context
        if has_selection:
            sel_count = len(selected_files)
            load_fast_tip = selected_analysis["fast_tooltip"]
            if sel_count < total_files:
                load_fast_tip += f" (Tip: Ctrl+A to select all {total_files} files)"
            action_load_fast.setToolTip(load_fast_tip)

            load_ext_tip = selected_analysis["extended_tooltip"]
            if sel_count < total_files:
                load_ext_tip += f" (Tip: Ctrl+A to select all {total_files} files)"
            action_load_extended.setToolTip(load_ext_tip)
        else:
            action_load_fast.setToolTip("Select files first (Ctrl+A to select all)")
            action_load_extended.setToolTip("Select files first (Ctrl+A to select all)")

        menu.addSeparator()

        # === OTHER ACTIONS ===
        action_reload = create_action_with_shortcut(
            get_menu_icon("refresh-cw"), "Reload Folder", "F5"
        )
        action_clear_table = create_action_with_shortcut(
            get_menu_icon("x"), "Clear File Table", "Shift+Esc"
        )

        menu.addAction(action_reload)
        menu.addAction(action_clear_table)

        menu.addSeparator()

        # === HASH OPERATIONS (Selection-only) ===
        action_calculate_hashes = create_action_with_shortcut(
            get_menu_icon("hash"), "Calculate Checksums", "Ctrl+H"
        )

        # Smart hash state analysis - only analyze selected files for speed
        selected_hash_analysis = self._analyze_hash_state(selected_files)

        menu.addAction(action_calculate_hashes)

        # Smart enable/disable for hash actions
        action_calculate_hashes.setEnabled(
            has_selection and selected_hash_analysis["enable_selected"]
        )

        # Set smart tooltips with selection context
        if has_selection:
            sel_count = len(selected_files)
            hash_tip = selected_hash_analysis["selected_tooltip"]
            if sel_count < total_files:
                hash_tip += f" (Tip: Ctrl+A to select all {total_files} files)"
            action_calculate_hashes.setToolTip(hash_tip)
        else:
            action_calculate_hashes.setToolTip("Select files first (Ctrl+A to select all)")

        # Show results hash list action
        action_show_hash_results = create_action_with_shortcut(
            get_menu_icon("list"), "Show calculated hashes", "Ctrl+L"
        )
        menu.addAction(action_show_hash_results)

        # Enable only if there are selected files
        action_show_hash_results.setEnabled(has_selection)
        action_show_hash_results.setToolTip(
            "Display hashes for selected files that have been calculated" if has_selection
            else "Select files first to show their hashes"
        )

        # Connect show hash results action
        action_show_hash_results.triggered.connect(self.parent_window.shortcut_manager.show_results_hash_list)

        menu.addSeparator()

        # === SAVE OPERATIONS ===
        action_save_all_modified = create_action_with_shortcut(
            get_menu_icon("save"), "Save Modified Metadata", "Ctrl+S"
        )

        menu.addAction(action_save_all_modified)

        # Simple check for modifications
        has_modifications = False
        if hasattr(self.parent_window, "metadata_tree_view"):
            has_modifications = bool(self.parent_window.metadata_tree_view.modified_items)

        action_save_all_modified.setEnabled(has_modifications)

        if has_modifications:
            action_save_all_modified.setToolTip("Save all modified metadata (Ctrl+S)")
        else:
            action_save_all_modified.setToolTip("No modified metadata to save")

        action_save_all_modified.triggered.connect(self.parent_window.shortcut_save_all_metadata)

        menu.addSeparator()

        # === ROTATION OPERATION (Selection-only) ===
        action_set_rotation = create_action_with_shortcut(
            get_menu_icon("rotate-ccw"), "Set Rotation to 0°", None
        )
        menu.addAction(action_set_rotation)
        action_set_rotation.setEnabled(has_selection)

        if has_selection:
            sel_count = len(selected_files)
            rotation_tip = f"Reset rotation to 0° for {sel_count} selected file(s)"
            if sel_count < total_files:
                rotation_tip += f" (Tip: Ctrl+A to select all {total_files} files)"
            action_set_rotation.setToolTip(rotation_tip)
        else:
            action_set_rotation.setToolTip("Select files first (Ctrl+A to select all)")

        menu.addSeparator()

        # === HASH COMPARISON ACTIONS (Selection-only + All) ===
        # Note: These keep separate Selected/All variants for different use cases
        action_find_duplicates_sel = create_action_with_shortcut(
            get_menu_icon("copy"), "Find Duplicates in Selection", None
        )
        action_find_duplicates_all = create_action_with_shortcut(
            get_menu_icon("layers"), "Find Duplicates in All Files", None
        )
        action_compare_external = create_action_with_shortcut(
            get_menu_icon("folder"), "Compare with external folder...", None
        )

        menu.addAction(action_find_duplicates_sel)
        menu.addAction(action_find_duplicates_all)
        menu.addAction(action_compare_external)

        menu.addSeparator()

        # === UNDO/REDO/HISTORY ACTIONS (Global) ===
        action_undo = create_action_with_shortcut(
            get_menu_icon("rotate-ccw"), "Undo\tCtrl+Z", None
        )
        action_redo = create_action_with_shortcut(
            get_menu_icon("rotate-cw"), "Redo\tCtrl+Shift+Z", None
        )
        action_show_history = create_action_with_shortcut(
            get_menu_icon("list"), "Show Command History\tCtrl+Y", None
        )

        menu.addAction(action_undo)
        menu.addAction(action_redo)
        menu.addAction(action_show_history)

        # Enable/disable undo/redo based on command manager state
        # Note: Currently uses metadata command manager until unified system is implemented
        try:
            from core.metadata_command_manager import get_metadata_command_manager
            command_manager = get_metadata_command_manager()
            action_undo.setEnabled(command_manager.can_undo())
            action_redo.setEnabled(command_manager.can_redo())
        except Exception as e:
            logger.debug(f"[FileTable] Could not check undo/redo state: {e}", extra={"dev_only": True})
            action_undo.setEnabled(False)
            action_redo.setEnabled(False)
        
        action_show_history.setEnabled(True)  # Always available

        menu.addSeparator()

        # === EXPORT ACTIONS (Selection-only + All) ===
        # Note: These keep separate Selected/All variants for different export scopes
        action_export_sel = create_action_with_shortcut(
            get_menu_icon("download"), "Export Metadata (Selection)", None
        )
        action_export_all = create_action_with_shortcut(
            get_menu_icon("download"), "Export Metadata (All Files)", None
        )

        menu.addAction(action_export_sel)
        menu.addAction(action_export_all)

        # Enable/disable export actions based on metadata availability
        action_export_sel.setEnabled(has_selection)
        action_export_all.setEnabled(total_files > 0)

        # Smart tooltips
        if has_selection:
            sel_count = len(selected_files)
            export_tip = f"Export metadata for {sel_count} selected file(s)"
            if sel_count < total_files:
                export_tip += f" (Tip: Ctrl+A to export all {total_files} files)"
            action_export_sel.setToolTip(export_tip)
        else:
            action_export_sel.setToolTip("Select files first (Ctrl+A to select all)")

        if total_files > 0:
            action_export_all.setToolTip(f"Export metadata for all {total_files} files in folder")
        else:
            action_export_all.setToolTip("No files have metadata to export")

        # Enable/disable logic with enhanced debugging
        logger.debug(
            f"Context menu: Selection state: {has_selection} ({len(selected_files)} files)",
            extra={"dev_only": True},
        )

        # Enable/disable logic for non-operation actions
        action_invert.setEnabled(total_files > 0 and has_selection)
        action_select_all.setEnabled(total_files > 0)
        action_reload.setEnabled(total_files > 0)
        action_clear_table.setEnabled(total_files > 0)

        # Hash comparison actions enable/disable logic
        action_find_duplicates_sel.setEnabled(
            len(selected_files) >= 2
        )  # Need at least 2 files to find duplicates
        action_find_duplicates_all.setEnabled(total_files >= 2)
        action_compare_external.setEnabled(has_selection)  # Need selection to compare

        # Show menu and get chosen action
        action = menu.exec_(self.parent_window.file_table_view.viewport().mapToGlobal(position))

        self.parent_window.file_table_view.context_focused_row = None
        # Remove the problematic update() calls that can cause loops
        # self.parent_window.file_table_view.viewport().update()
        # self.parent_window.file_table_view.update()

        # === Handlers ===
        if action == action_load_fast:
            # Use intelligent loading with cache checking and smart UX
            self.parent_window.load_metadata_for_items(
                selected_files, use_extended=False, source="context_menu"
            )

        elif action == action_load_extended:
            # Use intelligent loading with cache checking and smart UX
            self.parent_window.load_metadata_for_items(
                selected_files, use_extended=True, source="context_menu"
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

        elif action == action_save_all_modified:
            # Save ALL modified metadata regardless of selection
            try:
                metadata_mgr = self.parent_window.context.get_manager('metadata')
                metadata_mgr.save_all_modified_metadata()
            except KeyError:
                logger.warning("[EventHandler] No metadata manager available for save all")

        elif action == action_set_rotation:
            # Handle rotation reset to 0° for selected files
            self._handle_bulk_rotation(selected_files)

        elif action == action_find_duplicates_sel:
            # Find duplicates in selected files
            self.hash_ops.handle_find_duplicates(selected_files)

        elif action == action_find_duplicates_all:
            # Find duplicates in all files
            self.hash_ops.handle_find_duplicates(None)  # None = all files

        elif action == action_compare_external:
            # Compare selected files with external folder
            self.hash_ops.handle_compare_external(selected_files)

        elif action == action_calculate_hashes:
            # Calculate checksums for selected files
            self.hash_ops.handle_calculate_hashes(selected_files)

        elif action == action_undo:
            # Call global undo handler
            self.parent_window.global_undo()

        elif action == action_redo:
            # Call global redo handler
            self.parent_window.global_redo()

        elif action == action_show_history:
            # Call global show history handler
            self.parent_window.show_command_history()

        elif action == action_export_sel:
            # Handle metadata export for selected files
            self.metadata_ops.handle_export_metadata(selected_files, "selected")

        elif action == action_export_all:
            # Handle metadata export for all files
            all_files = self.parent_window.file_table_model.get_all_file_items() if hasattr(self.parent_window, "file_table_model") and self.parent_window.file_table_model else []
            self.metadata_ops.handle_export_metadata(all_files, "all")

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

            # Check for Ctrl modifier for extended metadata
            ctrl_pressed = bool(modifiers & Qt.ControlModifier)  # type: ignore
            use_extended = ctrl_pressed

            # Get selected files for context
            selected_files = [f for f in self.parent_window.file_model.files if f.checked]
            target_files = selected_files if len(selected_files) > 1 else [file]

            # Analyze metadata state to show appropriate dialog
            metadata_analysis = self._analyze_metadata_state(target_files)

            # Check if we should show a dialog instead of loading
            if use_extended and not metadata_analysis["enable_extended_selected"]:
                # Extended metadata requested but all files already have it
                from utils.dialog_utils import show_info_message

                message = f"All {len(target_files)} file(s) already have extended metadata."
                if metadata_analysis.get("extended_tooltip"):
                    message += f"\n\n{metadata_analysis['extended_tooltip']}"

                show_info_message(
                    self.parent_window,
                    "Extended Metadata",
                    message,
                )
                return
            elif not use_extended and not metadata_analysis["enable_fast_selected"]:
                # Fast metadata requested but files have extended metadata or already have fast
                from utils.dialog_utils import show_info_message

                message = f"Cannot load fast metadata for {len(target_files)} file(s)."
                if metadata_analysis.get("fast_tooltip"):
                    message += f"\n\n{metadata_analysis['fast_tooltip']}"

                show_info_message(
                    self.parent_window,
                    "Fast Metadata",
                    message,
                )
                return

            # Proceed with loading
            source = "double_click_extended" if use_extended else "double_click"
            if len(selected_files) > 1:
                source += "_multi"

            self.parent_window.load_metadata_for_items(
                target_files, use_extended=use_extended, source=source
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

        with wait_cursor():  # type: ignore
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
        Analyzes metadata availability and prompts user to load if needed.

        Args:
            selected_files: List of FileItem objects to process
        """
        if not selected_files:
            logger.warning("[BulkRotation] No files selected for bulk rotation")
            return

        logger.info(f"[BulkRotation] Starting bulk rotation for {len(selected_files)} files")

        # Analyze which files have metadata loaded
        files_with_metadata = []
        files_without_metadata = []

        for file_item in selected_files:
            if self._has_metadata_loaded(file_item):
                files_with_metadata.append(file_item)
            else:
                files_without_metadata.append(file_item)

        logger.debug(
            f"[BulkRotation] Metadata analysis: {len(files_with_metadata)} with metadata, "
            f"{len(files_without_metadata)} without metadata",
            extra={"dev_only": True}
        )

        # If files without metadata exist, prompt user
        files_to_process = selected_files
        if files_without_metadata:
            choice = self._show_load_metadata_prompt(
                len(files_with_metadata),
                len(files_without_metadata)
            )

            if choice == "load":
                # Load metadata for files that don't have it
                logger.info(
                    f"[BulkRotation] Loading metadata for {len(files_without_metadata)} files"
                )
                self.parent_window.load_metadata_for_items(
                    files_without_metadata,
                    use_extended=False,
                    source="rotation_prep"
                )
                # After load, all files should have metadata
                files_to_process = selected_files
            elif choice == "skip":
                # Only process files that already have metadata
                if not files_with_metadata:
                    logger.info("[BulkRotation] No files with metadata to process")
                    return
                files_to_process = files_with_metadata
                logger.info(
                    f"[BulkRotation] Skipping {len(files_without_metadata)} files without metadata"
                )
            else:  # cancel
                logger.debug("[BulkRotation] User cancelled operation", extra={"dev_only": True})
                return

        try:
            from widgets.bulk_rotation_dialog import BulkRotationDialog

            # Show dialog and get user choices
            final_files = BulkRotationDialog.get_bulk_rotation_choice(
                self.parent_window, files_to_process, self.parent_window.metadata_cache
            )

            if not final_files:
                logger.debug(
                    "[BulkRotation] User cancelled bulk rotation or no files selected",
                    extra={"dev_only": True},
                )
                return

            logger.info(f"[BulkRotation] Processing {len(final_files)} files")

            # Apply rotation directly
            self._apply_bulk_rotation(final_files)

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

    def _has_metadata_loaded(self, file_item) -> bool:
        """
        Check if a file has metadata loaded in cache.

        Args:
            file_item: FileItem to check

        Returns:
            True if file has metadata loaded, False otherwise
        """
        if not self.parent_window or not hasattr(self.parent_window, "metadata_cache"):
            return False

        metadata_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
        if metadata_entry and hasattr(metadata_entry, "data") and metadata_entry.data:
            return True

        # Fallback: check file_item.metadata
        return hasattr(file_item, "metadata") and bool(file_item.metadata)

    def _show_load_metadata_prompt(self, with_metadata_count: int, without_metadata_count: int) -> str:
        """
        Show prompt asking user whether to load metadata for files that don't have it.

        Args:
            with_metadata_count: Number of files that have metadata
            without_metadata_count: Number of files without metadata

        Returns:
            'load': Load metadata and continue
            'skip': Skip files without metadata
            'cancel': Cancel operation
        """
        from widgets.custom_message_dialog import CustomMessageDialog

        with_metadata_count + without_metadata_count

        message_parts = []
        if with_metadata_count > 0:
            message_parts.append(f"{with_metadata_count} file(s) have metadata and can be processed")

        message_parts.append(
            f"{without_metadata_count} file(s) don't have metadata loaded yet"
        )
        message_parts.append("\nLoad metadata for these files first?")
        message_parts.append("(This ensures rotation changes can be saved properly)")

        message = "\n".join(message_parts)

        buttons = ["Load & Continue", "Skip", "Cancel"]
        dlg = CustomMessageDialog("Load Metadata First?", message, buttons, self.parent_window)

        # Ensure proper positioning
        if self.parent_window:
            from utils.multiscreen_helper import ensure_dialog_on_parent_screen
            ensure_dialog_on_parent_screen(dlg, self.parent_window)

        dlg.exec_()

        # Map button text to return values
        button_map = {
            "Load & Continue": "load",
            "Skip": "skip",
            "Cancel": "cancel",
        }

        return button_map.get(dlg.selected, "cancel")

    def _show_load_metadata_choice_dialog(
        self, files_with_metadata: int, files_without_metadata: int
    ) -> str:
        """
        Show dialog asking user what to do about files without metadata.

        Args:
            files_with_metadata: Count of files that have metadata
            files_without_metadata: Count of files that don't have metadata

        Returns:
            str: One of 'load', 'skip', or 'cancel'
        """
        from widgets.custom_message_dialog import CustomMessageDialog

        # Build message
        message_parts = []

        if files_with_metadata > 0:
            message_parts.append(
                f"{files_with_metadata} file(s) have metadata and can be processed."
            )

        message_parts.append(
            f"{files_without_metadata} file(s) don't have metadata loaded yet."
        )
        message_parts.append("")
        message_parts.append(
            "Load metadata for these files first? This ensures rotation changes can be saved."
        )

        message = "\n".join(message_parts)

        # Show 3-button dialog
        buttons = ["Load & Continue", "Skip These Files", "Cancel"]
        dlg = CustomMessageDialog(
            "Load Metadata First?",
            message,
            buttons,
            self.parent_window
        )

        # Ensure proper positioning
        if self.parent_window:
            from utils.multiscreen_helper import ensure_dialog_on_parent_screen
            ensure_dialog_on_parent_screen(dlg, self.parent_window)

        dlg.exec_()

        # Map button text to return values
        button_map = {
            "Load & Continue": "load",
            "Skip These Files": "skip",
            "Cancel": "cancel",
        }

        return button_map.get(dlg.selected, "cancel")

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
            # Get staging manager
            try:
                staging_manager = self.parent_window.context.get_manager('metadata_staging')
            except KeyError:
                logger.error("[BulkRotation] MetadataStagingManager not found")
                return

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

                # Stage the change
                staging_manager.stage_change(file_item.full_path, "Rotation", "0")

                # Get or create metadata cache entry (for UI display)
                cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
                if not cache_entry:
                    # Create a new cache entry if none exists
                    metadata_dict = getattr(file_item, "metadata", {}) or {}
                    self.parent_window.metadata_cache.set(file_item.full_path, metadata_dict)
                    cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)

                if cache_entry and hasattr(cache_entry, "data"):
                    # Set rotation to 0 in cache for display purposes
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
                # Update file table icons with proper refresh
                if hasattr(self.parent_window, "file_model"):
                    # Emit dataChanged for all modified files to update icons
                    for file_item in files_to_process:
                        if file_item.metadata_status == "modified":
                            try:
                                # Find row index
                                for row, model_file in enumerate(self.parent_window.file_model.files):
                                    if paths_equal(model_file.full_path, file_item.full_path):
                                        # Emit dataChanged for the icon column (column 0)
                                        idx = self.parent_window.file_model.index(row, 0)
                                        self.parent_window.file_model.dataChanged.emit(idx, idx)
                                        break
                            except Exception as e:
                                logger.warning(f"[BulkRotation] Error updating icon for {file_item.filename}: {e}")

                    # Also emit layoutChanged as backup
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


    def _check_selected_files_have_metadata(self, selected_files: list) -> bool:
        """Check if any of the selected files have metadata."""
        status = self.check_files_status(
            files=selected_files, check_type="metadata", extended=False
        )
        return status["count"] > 0  # Any files have metadata

    def _check_any_files_have_metadata(self) -> bool:
        """Check if any file in the current folder has metadata."""
        status = self.check_files_status(
            files=None,
            check_type="metadata",
            extended=False,
            scope="all",  # type: ignore
        )
        return status["count"] > 0  # Any files have metadata

    def _file_has_metadata(self, file_item) -> bool:
        return has_metadata(file_item.full_path)

    def _check_files_have_metadata_type(self, files: list, extended: bool) -> bool:
        """Check if all files have the specified type of metadata (basic or extended)."""
        status = self.check_files_status(files=files, check_type="metadata", extended=extended)
        return status["has_status"]  # All files have the metadata type

    def _check_all_files_have_metadata_type(self, extended: bool) -> bool:
        """Check if all files in the current folder have the specified type of metadata."""
        status = self.check_files_status(
            files=None,
            check_type="metadata",
            extended=extended,
            scope="all",  # type: ignore
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
        files: list = None,  # type: ignore
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
        self,
        files: list = None,
        extended: bool = False,
        scope: str = "selected",  # type: ignore
    ) -> list:
        """Get list of files that don't have metadata."""
        status = self.check_files_status(
            files=files, check_type="metadata", extended=extended, scope=scope
        )
        return status["files_without_status"]

    def get_files_without_hashes(self, files: list = None, scope: str = "selected") -> list:  # type: ignore
        """Get list of files that don't have hash values."""
        status = self.check_files_status(files=files, check_type="hash", scope=scope)
        return status["files_without_status"]

    def get_metadata_status_summary(self, files: list = None, scope: str = "selected") -> dict:  # type: ignore
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

    def _analyze_metadata_state(self, files: list) -> dict:
        """
        Analyze the metadata state of files to determine smart metadata menu options.

        Args:
            files: List of FileItem objects to analyze

        Returns:
            dict: Analysis results with enable/disable logic for metadata menu items
        """
        if not files:
            return {
                "enable_fast_selected": False,
                "enable_extended_selected": False,
                "fast_tooltip": "No files selected",
                "extended_tooltip": "No files selected",
            }

        start_time = time.time()

        # Check metadata state for each file
        files_no_metadata = []
        files_fast_metadata = []
        files_extended_metadata = []

        try:
            # Get metadata cache if available
            metadata_cache = getattr(self.parent_window, "metadata_cache", None)

            if metadata_cache and hasattr(metadata_cache, "get_entries_batch"):
                # Use batch lookup for better performance
                file_paths = [file_item.full_path for file_item in files]
                batch_entries = metadata_cache.get_entries_batch(file_paths)

                for file_item in files:
                    cache_entry = batch_entries.get(file_item.full_path)

                    if cache_entry and hasattr(cache_entry, "data") and cache_entry.data:
                        # File has metadata
                        if hasattr(cache_entry, "is_extended") and cache_entry.is_extended:
                            files_extended_metadata.append(file_item)
                        else:
                            files_fast_metadata.append(file_item)
                    else:
                        # File has no metadata
                        files_no_metadata.append(file_item)
            elif metadata_cache:
                # Fallback to individual lookups
                for file_item in files:
                    cache_entry = metadata_cache.get_entry(file_item.full_path)

                    if cache_entry and hasattr(cache_entry, "data") and cache_entry.data:
                        # File has metadata
                        if hasattr(cache_entry, "is_extended") and cache_entry.is_extended:
                            files_extended_metadata.append(file_item)
                        else:
                            files_fast_metadata.append(file_item)
                    else:
                        # File has no metadata
                        files_no_metadata.append(file_item)
            else:
                # No cache available, assume no metadata
                files_no_metadata.extend(files)

            elapsed_time = time.time() - start_time
            logger.debug(
                f"[EventHandler] Batch metadata check completed in {elapsed_time:.3f}s: "
                f"{len(files_no_metadata)} no metadata, {len(files_fast_metadata)} fast, "
                f"{len(files_extended_metadata)} extended"
            )

        except Exception as e:
            logger.warning(f"[EventHandler] Metadata state analysis failed: {e}")
            # Fallback: assume all files need metadata
            files_no_metadata = files
            files_fast_metadata = []
            files_extended_metadata = []

        total = len(files)
        no_metadata_count = len(files_no_metadata)
        fast_metadata_count = len(files_fast_metadata)
        extended_metadata_count = len(files_extended_metadata)

        # Determine enable states and tooltips
        # Fast metadata is only enabled if we have files that need fast metadata AND no files have extended metadata
        # (we don't want to mix fast and extended metadata in the same operation)
        enable_fast_selected = (
            no_metadata_count > 0 or fast_metadata_count > 0
        ) and extended_metadata_count == 0

        # Extended metadata is enabled if we have any files that need it or can be upgraded
        enable_extended_selected = (
            no_metadata_count > 0 or fast_metadata_count > 0 or extended_metadata_count > 0
        )

        # Fast metadata tooltip
        if extended_metadata_count > 0:
            fast_tooltip = f"Cannot load fast metadata: {extended_metadata_count} file(s) already have extended metadata"
            enable_fast_selected = False
        elif no_metadata_count == total:
            fast_tooltip = f"Load fast metadata for {total} file(s)"
        elif no_metadata_count == 0 and fast_metadata_count == total:
            fast_tooltip = f"All {total} file(s) already have fast metadata"
            enable_fast_selected = False
        else:
            need_fast = no_metadata_count
            fast_tooltip = f"Load fast metadata for {need_fast} of {total} file(s) that need it"

        # Extended metadata tooltip
        if extended_metadata_count == total:
            extended_tooltip = f"All {total} file(s) already have extended metadata"
            enable_extended_selected = False
        elif extended_metadata_count == 0:
            if fast_metadata_count > 0:
                extended_tooltip = f"Upgrade {fast_metadata_count} file(s) to extended metadata and load for {no_metadata_count} file(s)"
            else:
                extended_tooltip = f"Load extended metadata for {total} file(s)"
        else:
            need_extended = total - extended_metadata_count
            extended_tooltip = (
                f"Load/upgrade extended metadata for {need_extended} of {total} file(s)"
            )

        return {
            "enable_fast_selected": enable_fast_selected,
            "enable_extended_selected": enable_extended_selected,
            "fast_label": "Load Fast Metadata",
            "extended_label": "Load Extended Metadata",
            "fast_tooltip": fast_tooltip,
            "extended_tooltip": extended_tooltip,
            "stats": {
                "total": total,
                "no_metadata": no_metadata_count,
                "fast_metadata": fast_metadata_count,
                "extended_metadata": extended_metadata_count,
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
