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

import os
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
from utils.logger_factory import get_cached_logger
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
from core.utility_manager import UtilityManager
from core.rename_manager import RenameManager
from core.drag_cleanup_manager import DragCleanupManager
from core.shortcut_manager import ShortcutManager
from core.initialization_manager import InitializationManager

logger = get_cached_logger(__name__)


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
        self.utility_manager = UtilityManager(self)
        self.rename_manager = RenameManager(self)
        self.drag_cleanup_manager = DragCleanupManager(self)
        self.shortcut_manager = ShortcutManager(self)
        self.initialization_manager = InitializationManager(self)

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
        """Delegates to InitializationManager for status updates from preview."""
        self.initialization_manager.update_status_from_preview(status_html)

    def clear_file_table_shortcut(self) -> None:
        """Delegates to ShortcutManager for clear file table shortcut."""
        self.shortcut_manager.clear_file_table_shortcut()

    def force_drag_cleanup(self) -> None:
        """Delegates to DragCleanupManager for force drag cleanup."""
        self.drag_cleanup_manager.force_drag_cleanup()

    def _cleanup_widget_drag_states(self) -> None:
        """Delegates to DragCleanupManager for widget drag states cleanup."""
        self.drag_cleanup_manager._cleanup_widget_drag_states()

    def _emergency_drag_cleanup(self) -> None:
        """Delegates to DragCleanupManager for emergency drag cleanup."""
        self.drag_cleanup_manager.emergency_drag_cleanup()

    def eventFilter(self, obj, event):
        """Delegates to UtilityManager for event filtering."""
        return self.utility_manager.event_filter(obj, event)

    def request_preview_update(self) -> None:
        """Delegates to UtilityManager for preview update scheduling."""
        self.utility_manager.request_preview_update()

    def force_reload(self) -> None:
        """Delegates to UtilityManager for force reload functionality."""
        self.utility_manager.force_reload()

    def _find_consecutive_ranges(self, indices: list[int]) -> list[tuple[int, int]]:
        """Delegates to UtilityManager for consecutive ranges calculation."""
        return self.utility_manager.find_consecutive_ranges(indices)

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
        """Delegates to RenameManager for batch rename execution."""
        self.rename_manager.rename_files()

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
        """Delegates to RenameManager for module dividers update."""
        self.rename_manager.update_module_dividers()

    def handle_header_toggle(self, _) -> None:
        """Delegates to EventHandlerManager for header toggle handling."""
        self.event_handler_manager.handle_header_toggle(_)

    def generate_preview_names(self) -> None:
        """Delegates to UtilityManager for preview names generation."""
        self.utility_manager.generate_preview_names()

    def compute_max_filename_width(self, file_list: list[FileItem]) -> int:
        """Delegates to PreviewManager for filename width calculation."""
        return self.preview_manager.compute_max_filename_width(file_list)

    def center_window(self) -> None:
        """Delegates to UtilityManager for window centering."""
        self.utility_manager.center_window()

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
        """Delegates to UtilityManager for files label update."""
        self.utility_manager.update_files_label()

    def set_status(self, text: str, color: str = "", auto_reset: bool = False, reset_delay: int = 3000) -> None:
        """
        Sets the status label text and optional color. Delegates to StatusManager.
        """
        self.status_manager.set_status(text, color, auto_reset, reset_delay)

    def get_identity_name_pairs(self) -> list[tuple[str, str]]:
        """Delegates to PreviewManager for identity name pairs."""
        return self.preview_manager.get_identity_name_pairs(self.file_model.files)

    def update_preview_tables_from_pairs(self, name_pairs: list[tuple[str, str]]) -> None:
        """Delegates to PreviewManager for preview tables update."""
        self.preview_manager.update_preview_tables_from_pairs(name_pairs)

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
        """Delegates to UtilityManager for getting selected rows as files."""
        return self.utility_manager.get_selected_rows_files()

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
        """Delegates to UtilityManager for modifier flags checking."""
        return self.utility_manager.get_modifier_flags()

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
        """Delegates to UtilityManager for close event handling."""
        self.utility_manager.close_event(event)

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
        """Delegates to InitializationManager for metadata status display."""
        self.initialization_manager.show_metadata_status()

    def _enable_selection_store_mode(self):
        """Delegates to InitializationManager for SelectionStore mode initialization."""
        self.initialization_manager.enable_selection_store_mode()
