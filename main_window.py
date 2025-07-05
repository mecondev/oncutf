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

# Import all config constants from centralized module
from config import STATUS_COLORS

# Core application modules
from core.application_context import ApplicationContext
from core.config_imports import *
from core.dialog_manager import DialogManager
from core.drag_cleanup_manager import DragCleanupManager
from core.drag_manager import DragManager
from core.event_handler_manager import EventHandlerManager
from core.file_load_manager import FileLoadManager
from core.file_operations_manager import FileOperationsManager
from core.file_validation_manager import get_file_validation_manager
from core.initialization_manager import InitializationManager
from core.preview_manager import PreviewManager
from core.window_config_manager import WindowConfigManager

# Import all PyQt5 classes from centralized module
from core.qt_imports import *
from core.rename_manager import RenameManager
from core.shortcut_manager import ShortcutManager
from core.splitter_manager import SplitterManager
from core.table_manager import TableManager
from core.ui_manager import UIManager
from core.utility_manager import UtilityManager

# Data models and business logic modules
from models.file_item import FileItem
from models.file_table_model import FileTableModel

# Utility functions and helpers
# Filename validation utilities available as functions
from utils.icon_cache import load_preview_status_icons, prepare_status_icons
from utils.icons import create_colored_icon
from utils.icons_loader import icons_loader, load_metadata_icons
from utils.json_config_manager import get_app_config_manager
from utils.logger_factory import get_cached_logger
from utils.metadata_loader import MetadataLoader

# UI widgets and custom components

logger = get_cached_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        """Initializes the main window and sets up the layout."""
        super().__init__()

        # --- Core Application Context ---
        self.context = ApplicationContext.create_instance(parent=self)

        # --- Initialize DragManager ---
        self.drag_manager = DragManager.get_instance()



        # --- Initialize PreviewManager ---
        self.preview_manager = PreviewManager(parent_window=self)

        # --- Initialize FileOperationsManager ---
        self.file_operations_manager = FileOperationsManager(parent_window=self)

        # --- Initialize StatusManager ---
        self.status_manager = None  # Will be initialized after status label is created

        # --- Initialize MetadataManager ---
        self.metadata_manager = None  # Will be initialized after metadata components

        # --- Database System Initialization (V2 Architecture) ---
        from core.database_manager import initialize_database
        from core.persistent_metadata_cache import get_persistent_metadata_cache
        from core.persistent_hash_cache import get_persistent_hash_cache
        from core.rename_history_manager import get_rename_history_manager
        from core.backup_manager import get_backup_manager

        # Initialize V2 database system with improved architecture
        self.db_manager = initialize_database()

        # --- Attributes initialization ---
        self.metadata_thread = None
        self.metadata_worker = None
        # Use V2 persistent metadata cache with improved separation of concerns
        self.metadata_cache = get_persistent_metadata_cache()
        # Initialize V2 persistent hash cache with dedicated hash table
        self.hash_cache = get_persistent_hash_cache()
        # Initialize rename history manager (will be migrated to V2 later)
        self.rename_history_manager = get_rename_history_manager()
        # Initialize backup manager for database backups
        self.backup_manager = get_backup_manager(str(self.db_manager.db_path))

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

        # Filename validation utilities available as functions in utils.filename_validator
        self.last_action = None  # Could be: 'folder_import', 'browse', 'rename', etc.
        self.current_folder_path = None
        self.current_folder_is_recursive = False  # Track if current folder was loaded recursively
        self.current_sort_column = 1  # Track current sort column (default: filename)
        self.current_sort_order = Qt.AscendingOrder  # Track current sort order
        self.files = []
        self.preview_map = {}  # preview_filename -> FileItem
        self._selection_sync_mode = "normal"  # values: "normal", "toggle"

        # --- Initialize managers first ---
        self.dialog_manager = DialogManager()
        self.event_handler_manager = EventHandlerManager(self)
        self.file_load_manager = FileLoadManager(self)
        self.file_validation_manager = get_file_validation_manager()
        self.table_manager = TableManager(self)
        self.utility_manager = UtilityManager(self)
        self.rename_manager = RenameManager(self)
        self.drag_cleanup_manager = DragCleanupManager(self)
        self.shortcut_manager = ShortcutManager(self)
        self.splitter_manager = SplitterManager(self)
        self.initialization_manager = InitializationManager(self)

        # Initialize ColumnManager for centralized column management
        from core.column_manager import ColumnManager
        self.column_manager = ColumnManager(self)

        # --- Initialize UIManager and setup all UI ---
        self.ui_manager = UIManager(parent_window=self)
        self.ui_manager.setup_all_ui()

        # --- Initialize JSON Config Manager ---
        self.config_manager = get_app_config_manager()

        # --- Initialize WindowConfigManager ---
        self.window_config_manager = WindowConfigManager(self)

        # --- Load and apply window configuration ---
        self.window_config_manager.load_window_config()

        # Store initial geometry AFTER smart sizing for proper restore behavior
        self._initial_geometry = self.geometry()

        # --- Apply UI configuration after UI is initialized ---
        self.window_config_manager.apply_loaded_config()

        # --- Ensure column widths are properly initialized ---
        # This handles cases where no config exists (fresh start) or when config is deleted
        from utils.timer_manager import schedule_resize_adjust
        schedule_resize_adjust(self._ensure_initial_column_sizing, 50)

        # --- Preview update debouncing timer ---
        self.preview_update_timer = QTimer(self)
        self.preview_update_timer.setSingleShot(True)
        self.preview_update_timer.setInterval(100)  # milliseconds
        self.preview_update_timer.timeout.connect(self.generate_preview_names)

        # --- Initialize Application Service Layer ---
        from core.application_service import initialize_application_service
        self.app_service = initialize_application_service(self)
        logger.info("[MainWindow] Application Service Layer initialized")

    # --- Method definitions ---

    # =====================================
    # Application Service Delegates
    # (These methods now use the Application Service Layer)
    # =====================================

    def select_all_rows(self) -> None:
        """Select all rows via Application Service."""
        self.app_service.select_all_rows()

    def clear_all_selection(self) -> None:
        """Clear all selection via Application Service."""
        self.app_service.clear_all_selection()

    def invert_selection(self) -> None:
        """Invert selection via Application Service."""
        self.app_service.invert_selection()

    def shortcut_load_metadata(self) -> None:
        """Load fast metadata via Application Service."""
        self.app_service.load_metadata_fast()

    def shortcut_load_extended_metadata(self) -> None:
        """Load extended metadata via Application Service."""
        self.app_service.load_metadata_extended()

    def shortcut_save_selected_metadata(self) -> None:
        """Save selected metadata via Application Service."""
        self.app_service.save_selected_metadata()

    def shortcut_save_all_metadata(self) -> None:
        """Save all metadata via Application Service."""
        self.app_service.save_all_metadata()

    def rename_files(self) -> None:
        """Execute batch rename via Application Service."""
        self.app_service.rename_files()

    def clear_file_table_shortcut(self) -> None:
        """Clear file table via Application Service."""
        self.app_service.clear_file_table_shortcut()

    def force_drag_cleanup(self) -> None:
        """Force drag cleanup via Application Service."""
        self.app_service.force_drag_cleanup()

    def request_preview_update(self) -> None:
        """Request preview update via Application Service."""
        self.app_service.request_preview_update()

    def generate_preview_names(self) -> None:
        """Generate preview names via Application Service."""
        self.app_service.generate_preview_names()

    def center_window(self) -> None:
        """Center window via Application Service."""
        self.app_service.center_window()

    def force_reload(self) -> None:
        """Force reload via Application Service."""
        self.app_service.force_reload()

    def handle_browse(self) -> None:
        """Handle browse via Application Service."""
        self.app_service.handle_browse()

    def handle_folder_import(self) -> None:
        """Handle folder import via Application Service."""
        self.app_service.handle_folder_import()

    def reload_current_folder(self) -> None:
        """Reload current folder via Application Service."""
        self.app_service.reload_current_folder()

    # =====================================
    # File Operations via Application Service
    # =====================================

    def load_files_from_folder(self, folder_path: str, skip_metadata: bool = False, force: bool = False):
        """Load files from folder via Application Service."""
        self.app_service.load_files_from_folder(folder_path, skip_metadata, force)

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
        """Load files from paths via Application Service."""
        self.app_service.load_files_from_paths(file_paths, clear=clear)

    def load_files_from_dropped_items(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """Load files from dropped items via Application Service."""
        self.app_service.load_files_from_dropped_items(paths, modifiers)

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """Prepare folder load via Application Service."""
        return self.app_service.prepare_folder_load(folder_path, clear=clear)

    def load_single_item_from_drop(self, path: str, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """Load single item from drop via Application Service."""
        self.app_service.load_single_item_from_drop(path, modifiers)

    def _handle_folder_drop(self, folder_path: str, merge_mode: bool, recursive: bool) -> None:
        """Handle folder drop via Application Service."""
        self.app_service.handle_folder_drop(folder_path, merge_mode, recursive)

    def _handle_file_drop(self, file_path: str, merge_mode: bool) -> None:
        """Handle file drop via Application Service."""
        self.app_service.handle_file_drop(file_path, merge_mode)

    def load_metadata_for_items(
        self,
        items: list[FileItem],
        use_extended: bool = False,
        source: str = "unknown"
    ) -> None:
        """Load metadata for items via Application Service."""
        self.app_service.load_metadata_for_items(items, use_extended, source)

    # =====================================
    # Table Operations via Application Service
    # =====================================

    def sort_by_column(self, column: int, order: Qt.SortOrder = None, force_order: Qt.SortOrder = None) -> None:
        """Sort by column via Application Service."""
        self.app_service.sort_by_column(column, order, force_order)

    def prepare_file_table(self, file_items: list[FileItem]) -> None:
        """Prepare file table via Application Service."""
        self.app_service.prepare_file_table(file_items)

    def restore_fileitem_metadata_from_cache(self) -> None:
        """Restore metadata from cache via Application Service."""
        self.app_service.restore_fileitem_metadata_from_cache()

    def clear_file_table(self, message: str = "No folder selected") -> None:
        """Clear file table via Application Service."""
        self.app_service.clear_file_table(message)

    def get_common_metadata_fields(self) -> list[str]:
        """Get common metadata fields via Application Service."""
        return self.app_service.get_common_metadata_fields()

    def set_fields_from_list(self, field_names: list[str]) -> None:
        """Set fields from list via Application Service."""
        self.app_service.set_fields_from_list(field_names)

    def after_check_change(self) -> None:
        """Handle check change via Application Service."""
        self.app_service.after_check_change()

    def get_selected_files(self) -> list[FileItem]:
        """Get selected files via Application Service."""
        return self.app_service.get_selected_files()

    # =====================================
    # Event Handling via Application Service
    # =====================================

    def handle_table_context_menu(self, position) -> None:
        """Handle table context menu via Application Service."""
        self.app_service.handle_table_context_menu(position)

    def handle_file_double_click(self, index: QModelIndex, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """Handle file double click via Application Service."""
        self.app_service.handle_file_double_click(index, modifiers)

    def on_table_row_clicked(self, index: QModelIndex) -> None:
        """Handle table row click via Application Service."""
        self.app_service.on_table_row_clicked(index)

    def handle_header_toggle(self, _) -> None:
        """Handle header toggle via Application Service."""
        self.app_service.handle_header_toggle(_)

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement via Application Service."""
        self.app_service.on_horizontal_splitter_moved(pos, index)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement via Application Service."""
        self.app_service.on_vertical_splitter_moved(pos, index)

    # =====================================
    # Preview Operations via Application Service
    # =====================================

    def get_identity_name_pairs(self) -> list[tuple[str, str]]:
        """Get identity name pairs via Application Service."""
        return self.app_service.get_identity_name_pairs()

    def update_preview_tables_from_pairs(self, name_pairs: list[tuple[str, str]]) -> None:
        """Update preview tables from pairs via Application Service."""
        self.app_service.update_preview_tables_from_pairs(name_pairs)

    def compute_max_filename_width(self, file_list: list[FileItem]) -> int:
        """Compute max filename width via Application Service."""
        return self.app_service.compute_max_filename_width(file_list)

    def update_preview_from_selection(self, selected_rows: list[int]) -> None:
        """Update preview from selection via Application Service."""
        self.app_service.update_preview_from_selection(selected_rows)

    # =====================================
    # Utility Operations via Application Service
    # =====================================

    def get_selected_rows_files(self) -> list:
        """Get selected rows as files via Application Service."""
        return self.app_service.get_selected_rows_files()

    def find_fileitem_by_path(self, path: str) -> Optional[FileItem]:
        """Find FileItem by path via Application Service."""
        return self.app_service.find_fileitem_by_path(path)

    def get_modifier_flags(self) -> tuple[bool, bool]:
        """Get modifier flags via Application Service."""
        return self.app_service.get_modifier_flags()

    def determine_metadata_mode(self) -> tuple[bool, bool]:
        """Determine metadata mode via Application Service."""
        return self.app_service.determine_metadata_mode()

    def should_use_extended_metadata(self) -> bool:
        """Determine if extended metadata should be used via Application Service."""
        return self.app_service.should_use_extended_metadata()

    def update_files_label(self) -> None:
        """Update files label via Application Service."""
        self.app_service.update_files_label()

    # =====================================
    # Validation & Dialog Operations via Application Service
    # =====================================

    def confirm_large_folder(self, file_list: list[str], folder_path: str) -> bool:
        """Confirm large folder via Application Service."""
        return self.app_service.confirm_large_folder(file_list, folder_path)

    def check_large_files(self, files: list[FileItem]) -> list[FileItem]:
        """Check large files via Application Service."""
        return self.app_service.check_large_files(files)

    def confirm_large_files(self, files: list[FileItem]) -> bool:
        """Confirm large files via Application Service."""
        return self.app_service.confirm_large_files(files)

    def prompt_file_conflict(self, target_path: str) -> str:
        """Prompt file conflict via Application Service."""
        return self.app_service.prompt_file_conflict(target_path)

    def validate_operation_for_user(self, files: list[str], operation_type: str) -> dict:
        """Validate operation for user via Application Service."""
        return self.app_service.validate_operation_for_user(files, operation_type)

    def identify_moved_files(self, file_paths: list[str]) -> dict:
        """Identify moved files via Application Service."""
        return self.app_service.identify_moved_files(file_paths)

    def set_status(self, text: str, color: str = "", auto_reset: bool = False, reset_delay: int = 3000) -> None:
        """Set status text and color via Application Service."""
        self.app_service.set_status(text, color, auto_reset, reset_delay)

    # =====================================
    # Direct Manager Delegates
    # (These methods still delegate directly to managers)
    # =====================================

    def _update_status_from_preview(self, status_html: str) -> None:
        """Delegates to InitializationManager for status updates from preview."""
        self.initialization_manager.update_status_from_preview(status_html)

    def _cleanup_widget_drag_states(self) -> None:
        """Delegates to DragCleanupManager for widget drag states cleanup."""
        self.drag_cleanup_manager._cleanup_widget_drag_states()

    def _emergency_drag_cleanup(self) -> None:
        """Delegates to DragCleanupManager for emergency drag cleanup."""
        self.drag_cleanup_manager.emergency_drag_cleanup()

    def eventFilter(self, obj, event):
        """Delegates to UtilityManager for event filtering."""
        return self.utility_manager.event_filter(obj, event)

    def _find_consecutive_ranges(self, indices: list[int]) -> list[tuple[int, int]]:
        """Delegates to UtilityManager for consecutive ranges calculation."""
        return self.utility_manager.find_consecutive_ranges(indices)

    def should_skip_folder_reload(self, folder_path: str, force: bool = False) -> bool:
        """Delegates to FileOperationsManager for folder reload check."""
        return self.file_operations_manager.should_skip_folder_reload(
            folder_path, self.current_folder_path, force
        )

    def get_file_items_from_folder(self, folder_path: str) -> list[FileItem]:
        """Delegates to FileLoadManager for getting file items from folder."""
        return self.file_load_manager.get_file_items_from_folder(folder_path)

    def update_module_dividers(self) -> None:
        """Delegates to RenameManager for module dividers update."""
        self.rename_manager.update_module_dividers()

    def show_metadata_status(self) -> None:
        """Delegates to InitializationManager for metadata status display."""
        self.initialization_manager.show_metadata_status()

    def _enable_selection_store_mode(self):
        """Enable selection store mode in file table view after UI initialization."""
        if hasattr(self, 'file_table_view'):
            logger.debug("[MainWindow] Enabling SelectionStore mode in FileTableView")
            self.file_table_view.enable_selection_store_mode()

    # =====================================
    # Metadata Editing Signal Handlers
    # =====================================

    def on_metadata_value_edited(self, key_path: str, old_value: str, new_value: str) -> None:
        """
        Handle metadata value edited signal from metadata tree view.

        Args:
            key_path: The metadata key path (e.g. "EXIF/Rotation")
            old_value: The previous value
            new_value: The new value
        """
        logger.info(f"[MetadataEdit] Value changed: {key_path} = '{old_value}' -> '{new_value}'")

        # Use specialized metadata status method
        self.status_manager.set_metadata_status(
            f"Modified {key_path}: {old_value} → {new_value}",
            operation_type="success",
            auto_reset=True
        )

        # The file icon status update is already handled by MetadataTreeView._update_file_icon_status()
        # Just log the change for debugging
        logger.debug(f"[MetadataEdit] Modified metadata field: {key_path}")

    def on_metadata_value_reset(self, key_path: str) -> None:
        """
        Handle metadata value reset signal from metadata tree view.

        Args:
            key_path: The metadata key path that was reset
        """
        logger.info(f"[MetadataEdit] Value reset: {key_path}")

        # Use specialized metadata status method
        self.status_manager.set_metadata_status(
            f"Reset {key_path} to original value",
            operation_type="success",
            auto_reset=True
        )

        # The file icon status update is already handled by MetadataTreeView._update_file_icon_status()
        logger.debug(f"[MetadataEdit] Reset metadata field: {key_path}")

    def on_metadata_value_copied(self, value: str) -> None:
        """
        Handle metadata value copied signal from metadata tree view.

        Args:
            value: The value that was copied to clipboard
        """
        logger.debug(f"[MetadataEdit] Value copied to clipboard: {value}")

        # Use specialized file operation status method
        self.status_manager.set_file_operation_status(
            f"Copied '{value}' to clipboard",
            success=True,
            auto_reset=True
        )

        # Override the reset delay for clipboard operations (shorter feedback)
        if self.status_manager._status_timer:
            self.status_manager._status_timer.stop()
            self.status_manager._status_timer.start(2000)  # 2 seconds for clipboard feedback

    # =====================================
    # Window Configuration Management
    # =====================================

    def _load_window_config(self) -> None:
        """Load and apply window configuration from config manager."""
        # Delegate to WindowConfigManager
        self.window_config_manager.load_window_config()

    def _set_smart_default_geometry(self) -> None:
        """Set smart default window geometry based on screen size and aspect ratio."""
        # Delegate to WindowConfigManager
        self.window_config_manager.set_smart_default_geometry()

    def _save_window_config(self) -> None:
        """Save current window state to config manager."""
        # Delegate to WindowConfigManager
        self.window_config_manager.save_window_config()

    def _apply_loaded_config(self) -> None:
        """Apply loaded configuration after UI is fully initialized."""
        # Delegate to WindowConfigManager
        self.window_config_manager.apply_loaded_config()

    def _ensure_initial_column_sizing(self) -> None:
        """Ensure column widths are properly sized on startup, especially when no config exists."""
        # Use the original FileTableView column configuration logic instead of ColumnManager
        if hasattr(self, 'file_table_view') and self.file_table_view.model():
            # Trigger the original, sophisticated column configuration
            if hasattr(self.file_table_view, '_configure_columns'):
                self.file_table_view._configure_columns()

            # Then trigger column adjustment using the existing logic
            if hasattr(self.file_table_view, '_trigger_column_adjustment'):
                self.file_table_view._trigger_column_adjustment()

            logger.debug("[MainWindow] Used original FileTableView column configuration")

        # Configure other table views with ColumnManager (they don't have the sophisticated logic)
        if hasattr(self, 'metadata_tree_view') and self.metadata_tree_view:
            self.column_manager.configure_table_columns(self.metadata_tree_view, 'metadata_tree')

        if hasattr(self, 'preview_tables_view') and self.preview_tables_view:
            # Configure preview tables
            if hasattr(self.preview_tables_view, 'old_names_table'):
                self.column_manager.configure_table_columns(self.preview_tables_view.old_names_table, 'preview_old')
            if hasattr(self.preview_tables_view, 'new_names_table'):
                self.column_manager.configure_table_columns(self.preview_tables_view.new_names_table, 'preview_new')

    def configure_table_columns(self, table_view, table_type: str) -> None:
        """Configure columns for a specific table view using ColumnManager."""
        self.column_manager.configure_table_columns(table_view, table_type)

    def adjust_columns_for_splitter_change(self, table_view, table_type: str) -> None:
        """Adjust columns when splitter position changes using ColumnManager."""
        self.column_manager.adjust_columns_for_splitter_change(table_view, table_type)

    def reset_column_preferences(self, table_type: str, column_index: int = None) -> None:
        """Reset user preferences for columns to allow auto-sizing."""
        self.column_manager.reset_user_preferences(table_type, column_index)

    def save_column_state(self, table_type: str) -> dict:
        """Save current column state for persistence."""
        return self.column_manager.save_column_state(table_type)

    def load_column_state(self, table_type: str, state_data: dict) -> None:
        """Load column state from persistence."""
        self.column_manager.load_column_state(table_type, state_data)

    def restore_last_folder_if_available(self) -> None:
        """Restore the last folder if available and user wants it."""
        # Delegate to WindowConfigManager
        self.window_config_manager.restore_last_folder_if_available()

    def get_selected_files_ordered(self) -> list[FileItem]:
        """
        Unified method to get selected files in table display order.

        Returns:
            List of FileItem objects sorted by their row position in the table
        """
        if not (hasattr(self, 'file_table_view') and hasattr(self, 'file_model')):
            return []

        if not self.file_model or not self.file_model.files:
            return []

        # Get current selection and sort to maintain display order
        selected_rows = self.file_table_view._get_current_selection()
        selected_rows_sorted = sorted(selected_rows)

        # Convert to FileItem objects with bounds checking
        selected_files = []
        for row in selected_rows_sorted:
            if 0 <= row < len(self.file_model.files):
                selected_files.append(self.file_model.files[row])

        return selected_files
