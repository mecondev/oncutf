"""
main_window.py
Author: Michael Economou
Date: 2025-05-01

This module defines the MainWindow class, which implements the primary user interface
for the oncutf application. It includes logic for loading files from folders, launching
metadata extraction in the background, and managing user interaction such as rename previews.

Note: PyQt5 type hints are not fully supported by static type checkers.
Many of the linter warnings are false positives and can be safely ignored.
"""

# type: ignore (PyQt5 attributes not recognized by linter)

import datetime
import glob
import os
import platform
import traceback
from typing import Optional

# Import all PyQt5 classes from centralized module
from core.qt_imports import *

# Import all config constants from centralized module
from core.config_imports import *

# Core application modules
from core.application_context import ApplicationContext
from core.drag_manager import DragManager
from core.file_loader import FileLoader
from core.file_operations_manager import FileOperationsManager
from core.modifier_handler import decode_modifiers_to_flags
from core.preview_manager import PreviewManager
from core.status_manager import StatusManager
from core.ui_manager import UIManager
# Data models and business logic modules
from models.file_item import FileItem
from models.file_table_model import FileTableModel
from modules.name_transform_module import NameTransformModule
# Utility functions and helpers
from utils.cursor_helper import wait_cursor, emergency_cursor_cleanup, force_restore_cursor
from utils.filename_validator import FilenameValidator
from utils.icon_cache import load_preview_status_icons, prepare_status_icons
from utils.icons import create_colored_icon
from utils.icons_loader import get_menu_icon, icons_loader, load_metadata_icons
from utils.logger_helper import get_logger
from utils.metadata_cache import MetadataCache
from utils.metadata_loader import MetadataLoader
from utils.preview_engine import apply_rename_modules
from utils.renamer import Renamer
# UI widgets and custom components
from widgets.custom_file_system_model import CustomFileSystemModel
from widgets.custom_msgdialog import CustomMessageDialog
from widgets.file_table_view import FileTableView
from widgets.file_tree_view import FileTreeView
from widgets.interactive_header import InteractiveHeader
from widgets.metadata_tree_view import MetadataTreeView
from widgets.metadata_waiting_dialog import MetadataWaitingDialog
from widgets.metadata_worker import MetadataWorker
from widgets.preview_tables_view import PreviewTablesView
from widgets.rename_modules_area import RenameModulesArea
from core.dialog_manager import DialogManager
from core.event_handler_manager import EventHandlerManager
from core.file_load_manager import FileLoadManager
from core.table_manager import TableManager

logger = get_logger(__name__)

import contextlib


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        """Initializes the main window and sets up the layout."""
        super().__init__()

        # --- Core Application Context ---
        self.context = ApplicationContext.create_instance(parent=self)

        # --- Initialize DragManager ---
        self.drag_manager = DragManager.get_instance()

        # --- Initialize FileLoader ---
        self.file_loader = FileLoader(parent_window=self)

        # --- Initialize PreviewManager ---
        self.preview_manager = PreviewManager(parent_window=self)

        # --- Initialize FileOperationsManager ---
        self.file_operations_manager = FileOperationsManager(parent_window=self)

        # --- Initialize StatusManager ---
        self.status_manager = None  # Will be initialized after status label is created

        # --- Initialize MetadataManager ---
        self.metadata_manager = None  # Will be initialized after metadata components

        # --- Attributes initialization ---
        self.metadata_thread = None
        self.metadata_worker = None
        self.metadata_cache = MetadataCache()
        self.metadata_icon_map = load_metadata_icons()
        self.preview_icons = load_preview_status_icons()
        self.force_extended_metadata = False
        self.skip_metadata_mode = DEFAULT_SKIP_METADATA # Keeps state across folder reloads
        self.metadata_loader = MetadataLoader()
        self.file_model = FileTableModel(parent_window=self)
        self.metadata_loader.model = self.file_model

        # --- Initialize MetadataManager after dependencies are ready ---
        from core.metadata_manager import MetadataManager
        from core.selection_manager import SelectionManager
        self.metadata_manager = MetadataManager(parent_window=self)
        self.selection_manager = SelectionManager(parent_window=self)

        # Initialize theme icon loader with dark theme by default
        icons_loader.set_theme("dark")

        self.loading_dialog = None
        self.modifier_state = Qt.NoModifier # type: ignore[attr-defined]

        self.create_colored_icon = create_colored_icon
        self.icon_paths = prepare_status_icons()

        self.filename_validator = FilenameValidator()
        self.last_action = None  # Could be: 'folder_import', 'browse', 'rename', etc.
        self.current_folder_path = None
        self.files = []
        self.preview_map = {}  # preview_filename -> FileItem
        self._selection_sync_mode = "normal"  # values: "normal", "toggle"

        # --- Initialize managers first ---
        self.dialog_manager = DialogManager()
        self.event_handler_manager = EventHandlerManager(self)
        self.file_load_manager = FileLoadManager(self)
        self.table_manager = TableManager(self)

        # --- Initialize UIManager and setup all UI ---
        self.ui_manager = UIManager(parent_window=self)
        self.ui_manager.setup_all_ui()

        # --- Preview update debouncing timer ---
        self.preview_update_timer = QTimer(self)
        self.preview_update_timer.setSingleShot(True)
        self.preview_update_timer.setInterval(100)  # milliseconds (reduced from 250ms for better performance)
        self.preview_update_timer.timeout.connect(self.generate_preview_names)

    # --- Method definitions ---

    def _update_status_from_preview(self, status_html: str) -> None:
        """Update the status label from preview widget status updates."""
        self.status_manager.update_status_from_preview(status_html)

    def clear_file_table_shortcut(self) -> None:
        """
        Clear file table triggered by Ctrl+Escape shortcut.
        """
        logger.info("[MainWindow] CLEAR TABLE: Ctrl+Escape key pressed")

        if not self.file_model.files:
            logger.info("[MainWindow] CLEAR TABLE: No files to clear")
            self.set_status("No files to clear", color="gray", auto_reset=True, reset_delay=1000)
            return

        # Clear the file table
        self.clear_file_table("Press Escape to clear, or drag folders here")
        self.current_folder_path = None  # Reset current folder
        self.set_status("File table cleared", color="blue", auto_reset=True, reset_delay=1000)
        logger.info("[MainWindow] CLEAR TABLE: File table cleared successfully")

    def force_drag_cleanup(self) -> None:
        """
        Force cleanup of any active drag operations.
        Triggered by Escape key globally.
        """
        logger.info("[MainWindow] FORCE CLEANUP: Escape key pressed")

        drag_manager = DragManager.get_instance()

        # Check if there's any stuck cursor or drag state
        has_override_cursor = QApplication.overrideCursor() is not None
        has_active_drag = drag_manager.is_drag_active()

        if not has_override_cursor and not has_active_drag:
            logger.info("[MainWindow] FORCE CLEANUP: No cursors or drags to clean")
            return

        # Clean any stuck cursors first
        cursor_count = 0
        while QApplication.overrideCursor() and cursor_count < 5:
            QApplication.restoreOverrideCursor()
            cursor_count += 1

        # Clean drag manager state if needed
        if has_active_drag:
            drag_manager.force_cleanup()

        # Clean widget states
        self._cleanup_widget_drag_states()

        # Report what was cleaned
        if cursor_count > 0 or has_active_drag:
            self.set_status("Drag cancelled", color="blue", auto_reset=True, reset_delay=1000)
            logger.info(f"[MainWindow] FORCE CLEANUP: Cleaned {cursor_count} cursors, drag_active={has_active_drag}")
        else:
            logger.info("[MainWindow] FORCE CLEANUP: Nothing to clean")

    def _cleanup_widget_drag_states(self) -> None:
        """Clean up internal drag states in all widgets (lightweight version)."""
        # Only clean essential drag state, let widgets handle their own cleanup
        if hasattr(self, 'folder_tree'):
            if hasattr(self.folder_tree, '_dragging'):
                self.folder_tree._dragging = False

        if hasattr(self, 'file_table_view'):
            if hasattr(self.file_table_view, '_drag_start_pos'):
                self.file_table_view._drag_start_pos = None

        logger.debug("[MainWindow] Widget drag states cleaned")

    def _emergency_drag_cleanup(self) -> None:
        """
        Emergency cleanup that runs every 5 seconds to catch stuck cursors.
        Only acts if cursor has been stuck for multiple checks.
        """
        app = QApplication.instance()
        if not app:
            return

        # Check if cursor looks stuck in drag mode
        current_cursor = app.overrideCursor()
        if current_cursor:
            cursor_shape = current_cursor.shape()
            # Common drag cursor shapes that might be stuck
            drag_cursors = [Qt.DragMoveCursor, Qt.DragCopyCursor, Qt.DragLinkCursor, Qt.ClosedHandCursor]

            if cursor_shape in drag_cursors:
                drag_manager = DragManager.get_instance()
                if not drag_manager.is_drag_active():
                    # Initialize stuck count if not exists
                    if not hasattr(self, '_stuck_cursor_count'):
                        self._stuck_cursor_count = 0

                    self._stuck_cursor_count += 1

                    # Only cleanup after 2 consecutive detections (10 seconds total)
                    if self._stuck_cursor_count >= 2:
                        logger.warning(f"[Emergency] Stuck drag cursor detected for {self._stuck_cursor_count * 5}s, forcing cleanup")
                        drag_manager.force_cleanup()
                        self.set_status("Stuck cursor fixed", color="green", auto_reset=True, reset_delay=1000)
                        self._stuck_cursor_count = 0
                    else:
                        logger.debug(f"[Emergency] Suspicious cursor detected ({self._stuck_cursor_count}/2)")
                else:
                    # Reset count if drag is actually active
                    self._stuck_cursor_count = 0
            else:
                # Reset count if cursor is not drag-related
                self._stuck_cursor_count = 0
        else:
            # Reset count if no override cursor
            self._stuck_cursor_count = 0

    def eventFilter(self, obj, event):
        """
        Captures global keyboard modifier state (Ctrl, Shift).
        """
        if event.type() in (QEvent.KeyPress, QEvent.KeyRelease):
            self.modifier_state = QApplication.keyboardModifiers()
            logger.debug(f"[Modifiers] eventFilter saw: {event.type()} with modifiers={int(event.modifiers())}", extra={"dev_only": True})

        return super().eventFilter(obj, event)

    def request_preview_update(self) -> None:
        """
        Schedules a delayed update of the name previews.
        Instead of calling generate_preview_names directly every time something changes,
        the timer is restarted so that the actual update occurs only when
        changes stop for the specified duration (250ms).
        """
        if self.preview_update_timer.isActive():
            self.preview_update_timer.stop()
        self.preview_update_timer.start()

    def force_reload(self) -> None:
        """
        Triggered by Ctrl+R.
        If Ctrl is held, metadata scan is skipped (like Select/Browse).
        Otherwise, full reload with scan.
        """
        # Update current state of modifier keys
        self.modifier_state = QApplication.keyboardModifiers()

        if not self.current_folder_path:
            self.set_status("No folder loaded.", color="gray", auto_reset=True)
            return

        if not CustomMessageDialog.question(self, "Reload Folder", "Reload current folder?", yes_text="Reload", no_text="Cancel"):
            return

        # Use determine_metadata_mode method instead of deprecated resolve_skip_metadata
        skip_metadata, use_extended = self.determine_metadata_mode()
        self.force_extended_metadata = use_extended
        self.skip_metadata_mode = skip_metadata

        logger.info(
            f"[ForceReload] Reloading {self.current_folder_path}, skip_metadata={skip_metadata} "
            f"(use_extended={use_extended})"
        )

        self.load_files_from_folder(self.current_folder_path, skip_metadata=skip_metadata, force=True)

    def _find_consecutive_ranges(self, indices: list[int]) -> list[tuple[int, int]]:
        """
        Given a sorted list of indices, returns a list of (start, end) tuples for consecutive ranges.
        Example: [1,2,3,7,8,10] -> [(1,3), (7,8), (10,10)]
        """
        if not indices:
            return []
        ranges = []
        start = prev = indices[0]
        for idx in indices[1:]:
            if idx == prev + 1:
                prev = idx
            else:
                ranges.append((start, prev))
                start = prev = idx
        ranges.append((start, prev))
        return ranges

    def select_all_rows(self) -> None:
        """Delegates to SelectionManager."""
        self.selection_manager.select_all_rows()

    def clear_all_selection(self) -> None:
        """Delegates to SelectionManager."""
        self.selection_manager.clear_all_selection()

    def invert_selection(self) -> None:
        """Delegates to SelectionManager."""
        self.selection_manager.invert_selection()

    def sort_by_column(self, column: int, order: Qt.SortOrder = None, force_order: Qt.SortOrder = None) -> None:
        """Delegates to TableManager for column sorting."""
        self.table_manager.sort_by_column(column, order, force_order)

    def restore_fileitem_metadata_from_cache(self) -> None:
        """Delegates to TableManager for restoring metadata from cache."""
        self.table_manager.restore_fileitem_metadata_from_cache()

    def rename_files(self) -> None:
        """
        Execute the batch rename process for checked files using active rename modules.

        This method handles the complete rename workflow including validation,
        execution, folder reload, and state restoration.
        """
        selected_files = self.get_selected_files()
        rename_data = self.rename_modules_area.get_all_data()
        modules_data = rename_data.get("modules", [])
        post_transform = rename_data.get("post_transform", {})

        # Store checked paths for restoration
        checked_paths = {f.full_path for f in self.file_model.files if f.checked}

        # Use FileOperationsManager to perform rename
        renamed_count = self.file_operations_manager.rename_files(
            selected_files=selected_files,
            modules_data=modules_data,
            post_transform=post_transform,
            metadata_cache=self.metadata_cache,
            filename_validator=self.filename_validator,
            current_folder_path=self.current_folder_path
        )

        if renamed_count == 0:
            return

        # Post-rename workflow
        self.last_action = "rename"
        self.load_files_from_folder(self.current_folder_path, skip_metadata=True)

        # Restore checked state
        restored_count = 0
        for path in checked_paths:
            file = self.find_fileitem_by_path(path)
            if file:
                file.checked = True
                restored_count += 1

        # Restore metadata from cache
        self.restore_fileitem_metadata_from_cache()

        # Regenerate preview with new filenames
        if self.last_action == "rename":
            logger.debug("[PostRename] Regenerating preview with new filenames and restored checked state")
            self.request_preview_update()

        # Force update info icons in column 0
        for row in range(self.file_model.rowCount()):
            file_item = self.file_model.files[row]
            if self.metadata_cache.has(file_item.full_path):
                index = self.file_model.index(row, 0)
                rect = self.file_table_view.visualRect(index)
                self.file_table_view.viewport().update(rect)

        self.file_table_view.viewport().update()
        logger.debug(f"[Rename] Restored {restored_count} checked out of {len(self.file_model.files)} files")

    def should_skip_folder_reload(self, folder_path: str, force: bool = False) -> bool:
        """Delegates to FileOperationsManager for folder reload check."""
        return self.file_operations_manager.should_skip_folder_reload(
            folder_path, self.current_folder_path, force
        )

    def get_file_items_from_folder(self, folder_path: str) -> list[FileItem]:
        """Delegates to FileLoadManager for getting file items from folder."""
        return self.file_load_manager.get_file_items_from_folder(folder_path)

    def prepare_file_table(self, file_items: list[FileItem]) -> None:
        """Delegates to TableManager for file table preparation."""
        self.table_manager.prepare_file_table(file_items)

    def load_files_from_folder(self, folder_path: str, skip_metadata: bool = False, force: bool = False):
        """Delegates to FileLoadManager for folder loading."""
        self.file_load_manager.load_files_from_folder(folder_path, skip_metadata, force)

    def start_metadata_scan(self, file_paths: list[str]) -> None:
        """Delegates to MetadataManager for metadata scan initiation."""
        self.metadata_manager.start_metadata_scan(file_paths)

    def load_metadata_in_thread(self, file_paths: list[str]) -> None:
        """Delegates to MetadataManager for thread-based metadata loading."""
        self.metadata_manager.load_metadata_in_thread(file_paths)

    def start_metadata_scan_for_items(self, items: list[FileItem]) -> None:
        """Delegates to MetadataManager for FileItem-based metadata scanning."""
        self.metadata_manager.start_metadata_scan_for_items(items)

    def shortcut_load_metadata(self) -> None:
        """Delegates to MetadataManager for shortcut-based metadata loading."""
        self.metadata_manager.shortcut_load_metadata()

    def shortcut_load_extended_metadata(self) -> None:
        """Delegates to MetadataManager for extended metadata shortcut loading."""
        self.metadata_manager.shortcut_load_extended_metadata()

    def reload_current_folder(self) -> None:
        """Delegates to FileLoadManager for reloading current folder."""
        self.file_load_manager.reload_current_folder()

    def update_module_dividers(self) -> None:
        for index, module in enumerate(self.rename_modules):
            if hasattr(module, "divider"):
                module.divider.setVisible(index > 0)

    def handle_header_toggle(self, _) -> None:
        """Delegates to EventHandlerManager for header toggle handling."""
        self.event_handler_manager.handle_header_toggle(_)

    def generate_preview_names(self) -> None:
        """
        Generate new preview names for all selected files using current rename modules.
        Updates the preview map and UI elements accordingly.
        """
        selected_files = self.get_selected_files()
        logger.debug("[Preview] Triggered! Selected rows: %s", [f.filename for f in selected_files], extra={"dev_only": True})

        if not selected_files:
            logger.debug("[Preview] No selected files — skipping preview generation.", extra={"dev_only": True})
            self.update_preview_tables_from_pairs([])
            self.rename_button.setEnabled(False)
            return

        # Get rename data and modules
        rename_data = self.rename_modules_area.get_all_data()
        all_modules = self.rename_modules_area.get_all_module_instances()

        # Use PreviewManager to generate previews
        name_pairs, has_changes = self.preview_manager.generate_preview_names(
            selected_files, rename_data, self.metadata_cache, all_modules
        )

        # Update preview map from manager
        self.preview_map = self.preview_manager.get_preview_map()

        # Handle UI updates based on results
        if not name_pairs:
            # No modules at all → clear preview completely
            self.update_preview_tables_from_pairs([])
            self.rename_button.setEnabled(False)
            self.set_status("No rename modules defined.", color=STATUS_COLORS["loading"], auto_reset=True)
            return

        if not has_changes:
            # Modules exist but inactive → show identity mapping
            self.rename_button.setEnabled(False)
            self.rename_button.setToolTip("No changes to apply")
            self.update_preview_tables_from_pairs(name_pairs)
            self.set_status("Rename modules present but inactive.", color=STATUS_COLORS["loading"], auto_reset=True)
            return

        # Update preview tables with changes
        self.update_preview_tables_from_pairs(name_pairs)

        # Enable rename button and set tooltip
        valid_pairs = [p for p in name_pairs if p[0] != p[1]]
        self.rename_button.setEnabled(bool(valid_pairs))
        tooltip_msg = f"{len(valid_pairs)} files will be renamed." if valid_pairs else "No changes to apply"
        self.rename_button.setToolTip(tooltip_msg)

    def compute_max_filename_width(self, file_list: list[FileItem]) -> int:
        """Delegates to PreviewManager for filename width calculation."""
        return self.preview_manager.compute_max_filename_width(file_list)

    def center_window(self) -> None:
        """
        Centers the application window on the user's screen.

        It calculates the screen's center point and moves the window
        so its center aligns with that. This improves the initial UX
        by avoiding awkward off-center placement.

        Returns:
            None
        """
        # Get current geometry of the window
        window_geometry = self.frameGeometry()

        # Get the center point of the available screen
        screen_center = QDesktopWidget().availableGeometry().center()

        # Move the window geometry so that its center aligns with screen center
        window_geometry.moveCenter(screen_center)

        # Reposition the window's top-left corner to match the new centered geometry
        self.move(window_geometry.topLeft())

        logger.debug("Main window centered on screen.")

    def confirm_large_folder(self, file_list: list[str], folder_path: str) -> bool:
        """Delegates to FileOperationsManager for large folder confirmation."""
        return self.file_operations_manager.confirm_large_folder(file_list, folder_path)

    def check_large_files(self, files: list[FileItem]) -> list[FileItem]:
        """Delegates to FileOperationsManager for large file checking."""
        return self.file_operations_manager.check_large_files(files)

    def confirm_large_files(self, files: list[FileItem]) -> bool:
        """Delegates to FileOperationsManager for large file confirmation."""
        return self.file_operations_manager.confirm_large_files(files)

    def prompt_file_conflict(self, target_path: str) -> str:
        """Delegates to FileOperationsManager for file conflict resolution."""
        return self.file_operations_manager.prompt_file_conflict(target_path)

    def update_files_label(self) -> None:
        """
        Updates the UI label that displays the count of selected files.

        If no files are loaded, the label shows a default "Files".
        Otherwise, it shows how many files are currently selected
        out of the total number loaded.
        """
        total = len(self.file_model.files)
        selected = sum(1 for f in self.file_model.files if f.checked) if total else 0

        self.status_manager.update_files_label(self.files_label, total, selected)

    def fade_status_to_ready(self) -> None:
        """
        Fades out the current status, then shows 'Ready' without fading.
        """
        self.status_fade_anim.stop()
        self.status_fade_anim.start()

        def show_ready_clean():
            if hasattr(self, "status_fade_anim"):
                self.status_fade_anim.stop()
            if hasattr(self, "status_opacity_effect"):
                self.status_opacity_effect.setOpacity(1.0)
            self.status_label.setStyleSheet("")  # reset color
            self.status_label.setText("Ready")

        QTimer.singleShot(self.status_fade_anim.duration(), show_ready_clean)

    def set_status(self, text: str, color: str = "", auto_reset: bool = False, reset_delay: int = 3000) -> None:
        """
        Sets the status label text and optional color. Delegates to StatusManager.
        """
        self.status_manager.set_status(text, color, auto_reset, reset_delay)

    def get_identity_name_pairs(self) -> list[tuple[str, str]]:
        """Delegates to FileOperationsManager for identity name pairs."""
        return self.file_operations_manager.get_identity_name_pairs(self.file_model.files)

    def update_preview_tables_from_pairs(self, name_pairs: list[tuple[str, str]]) -> None:
        """
        Updates all three preview tables using the PreviewTablesView.

        Args:
            name_pairs (list[tuple[str, str]]): List of (old_name, new_name) pairs
                generated during preview generation.
        """
        # Delegate to the preview tables view
        self.preview_tables_view.update_from_pairs(
            name_pairs,
            self.preview_icons,
            self.icon_paths,
            self.filename_validator
        )

    def on_metadata_progress(self, current: int, total: int) -> None:
        """Delegates to MetadataManager for progress updates."""
        self.metadata_manager.on_metadata_progress(current, total)

    def handle_metadata_finished(self) -> None:
        """Delegates to MetadataManager for handling completion."""
        self.metadata_manager.handle_metadata_finished()

    def cleanup_metadata_worker(self) -> None:
        """Delegates to MetadataManager for worker cleanup."""
        self.metadata_manager.cleanup_metadata_worker()

    def get_selected_rows_files(self) -> list:
        """
        Returns a list of FileItem objects currently selected (blue-highlighted) in the table view.
        """
        selected_indexes = self.file_table_view.selectionModel().selectedRows()
        return [self.file_model.files[i.row()] for i in selected_indexes if 0 <= i.row() < len(self.file_model.files)]

    def find_fileitem_by_path(self, path: str) -> Optional[FileItem]:
        """Delegates to FileOperationsManager for finding FileItem by path."""
        return self.file_operations_manager.find_fileitem_by_path(self.file_model.files, path)

    def cancel_metadata_loading(self) -> None:
        """Delegates to MetadataManager for cancellation."""
        self.metadata_manager.cancel_metadata_loading()

    def on_metadata_error(self, message: str) -> None:
        """Delegates to MetadataManager for error handling."""
        self.metadata_manager.on_metadata_error(message)

    def is_running_metadata_task(self) -> bool:
        """Delegates to MetadataManager to check if metadata task is running."""
        return self.metadata_manager.is_running_metadata_task()

    def on_table_row_clicked(self, index: QModelIndex) -> None:
        """Delegates to EventHandlerManager for table row click handling."""
        self.event_handler_manager.on_table_row_clicked(index)

    def clear_file_table(self, message: str = "No folder selected") -> None:
        """Delegates to TableManager for clearing file table."""
        self.table_manager.clear_file_table(message)

    def get_common_metadata_fields(self) -> list[str]:
        """Delegates to TableManager for getting common metadata fields."""
        return self.table_manager.get_common_metadata_fields()

    def set_fields_from_list(self, field_names: list[str]) -> None:
        """Delegates to TableManager for setting fields from list."""
        self.table_manager.set_fields_from_list(field_names)

    def after_check_change(self) -> None:
        """Delegates to TableManager for handling check change."""
        self.table_manager.after_check_change()

    def get_selected_files(self) -> list[FileItem]:
        """Delegates to TableManager for getting selected files."""
        return self.table_manager.get_selected_files()

    def get_modifier_flags(self) -> tuple[bool, bool]:
        """
        Checks which keyboard modifiers are currently held down.

        Returns:
            tuple: (skip_metadata: bool, use_extended: bool)
                - skip_metadata: True if NO modifiers are pressed (default) or if Ctrl is NOT pressed
                - use_extended: True if Ctrl+Shift is pressed
        """
        modifiers = self.modifier_state
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)

        skip_metadata = not ctrl
        use_extended = ctrl and shift

        # [DEBUG] Modifiers: Ctrl=%s, Shift=%s", skip_metadata, use_extended
        return skip_metadata, use_extended

    def determine_metadata_mode(self) -> tuple[bool, bool]:
        """Delegates to MetadataManager for metadata mode determination."""
        return self.metadata_manager.determine_metadata_mode(self.modifier_state)

    def should_use_extended_metadata(self) -> bool:
        """Delegates to MetadataManager for extended metadata decision."""
        return self.metadata_manager.should_use_extended_metadata(self.modifier_state)

    def update_preview_from_selection(self, selected_rows: list[int]) -> None:
        """Delegates to SelectionManager."""
        self.selection_manager.update_preview_from_selection(selected_rows)

    def handle_table_context_menu(self, position) -> None:
        """Delegates to EventHandlerManager for table context menu handling."""
        self.event_handler_manager.handle_table_context_menu(position)

    def handle_file_double_click(self, index: QModelIndex, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """Delegates to EventHandlerManager for file double click handling."""
        self.event_handler_manager.handle_file_double_click(index, modifiers)

    def closeEvent(self, event) -> None:
        """
        Called when the main window is about to close.

        Ensures any background metadata threads are cleaned up
        properly before the application exits.
        """
        logger.info("Main window closing. Cleaning up metadata worker.")
        self.cleanup_metadata_worker()

        if hasattr(self.metadata_loader, "close"):
            self.metadata_loader.close()

        # Clean up application context
        if hasattr(self, 'context'):
            self.context.cleanup()

        super().closeEvent(event)

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """Delegates to FileLoadManager for folder load preparation."""
        return self.file_load_manager.prepare_folder_load(folder_path, clear=clear)

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
        """Delegates to FileLoadManager for loading files from paths."""
        self.file_load_manager.load_files_from_paths(file_paths, clear=clear)

    def load_metadata_from_dropped_files(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """Delegates to FileLoadManager for loading metadata from dropped files."""
        self.file_load_manager.load_metadata_from_dropped_files(paths, modifiers)

    def load_files_from_dropped_items(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """Delegates to FileLoadManager for loading files from dropped items."""
        self.file_load_manager.load_files_from_dropped_items(paths, modifiers)

    def handle_browse(self) -> None:
        """Delegates to EventHandlerManager for browse handling."""
        self.event_handler_manager.handle_browse()

    def handle_folder_import(self) -> None:
        """Delegates to EventHandlerManager for folder import handling."""
        self.event_handler_manager.handle_folder_import()

    def load_single_item_from_drop(self, path: str, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """Delegates to FileLoadManager for loading single item from drop."""
        self.file_load_manager.load_single_item_from_drop(path, modifiers)

    def _has_deep_content(self, folder_path: str) -> bool:
        """Delegates to FileLoadManager for checking deep content."""
        return self.file_load_manager._has_deep_content(folder_path)

    def _handle_folder_drop(self, folder_path: str, merge_mode: bool, recursive: bool) -> None:
        """Delegates to FileLoadManager for handling folder drop."""
        self.file_load_manager._handle_folder_drop(folder_path, merge_mode, recursive)

    def _handle_file_drop(self, file_path: str, merge_mode: bool) -> None:
        """Delegates to FileLoadManager for handling file drop."""
        self.file_load_manager._handle_file_drop(file_path, merge_mode)

    def load_metadata_for_items(
        self,
        items: list[FileItem],
        use_extended: bool = False,
        source: str = "unknown"
    ) -> None:
        """Delegates to MetadataManager for unified metadata loading."""
        self.metadata_manager.load_metadata_for_items(items, use_extended, source)

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Delegates to EventHandlerManager for horizontal splitter movement handling."""
        self.event_handler_manager.on_horizontal_splitter_moved(pos, index)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Delegates to EventHandlerManager for vertical splitter movement handling."""
        self.event_handler_manager.on_vertical_splitter_moved(pos, index)

    def show_metadata_status(self) -> None:
        """
        Shows a status bar message indicating the number of loaded files
        and the type of metadata scan performed (skipped, basic, extended).
        """
        num_files = len(self.file_model.files)
        self.status_manager.show_metadata_status(num_files, self.skip_metadata_mode, self.force_extended_metadata)

    def _enable_selection_store_mode(self):
        """Enable SelectionStore mode in FileTableView once ApplicationContext is ready."""
        try:
            self.file_table_view.enable_selection_store_mode()

            # Connect SelectionStore signals to MainWindow handlers
            from core.application_context import get_app_context
            context = get_app_context()
            if context and context.selection_store:
                # Connect selection changed signal to existing preview update
                context.selection_store.selection_changed.connect(self.update_preview_from_selection)
                logger.debug("[MainWindow] Connected SelectionStore signals", extra={"dev_only": True})

            logger.info("[MainWindow] SelectionStore mode enabled in FileTableView")
        except Exception as e:
            logger.warning(f"[MainWindow] Failed to enable SelectionStore mode: {e}")


