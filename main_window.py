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

from typing import Optional

# Import all config constants from centralized module
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

# Import all PyQt5 classes from centralized module
from core.pyqt_imports import *
from core.rename_manager import RenameManager
from core.shortcut_manager import ShortcutManager
from core.splitter_manager import SplitterManager
from core.table_manager import TableManager
from core.ui_manager import UIManager
from core.utility_manager import UtilityManager
from core.window_config_manager import WindowConfigManager

# Data models and business logic modules
from models.file_item import FileItem
from models.file_table_model import FileTableModel

# Utility functions and helpers
from utils.icon_cache import load_preview_status_icons, prepare_status_icons
from utils.icon_utilities import create_colored_icon
from utils.icons_loader import icons_loader, load_metadata_icons
from utils.json_config_manager import get_app_config_manager
from utils.logger_factory import get_cached_logger

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
        from core.backup_manager import get_backup_manager
        from core.database_manager import initialize_database
        from core.persistent_hash_cache import get_persistent_hash_cache
        from core.persistent_metadata_cache import get_persistent_metadata_cache
        from core.rename_history_manager import get_rename_history_manager

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
        self.file_model = FileTableModel(parent_window=self)

        # --- Initialize UnifiedMetadataManager after dependencies are ready ---
        from core.selection_manager import SelectionManager
        from core.unified_metadata_manager import get_unified_metadata_manager
        self.metadata_manager = get_unified_metadata_manager(self)
        self.metadata_manager.initialize_cache_helper()
        self.selection_manager = SelectionManager(parent_window=self)

        # Initialize theme icon loader with dark theme by default
        icons_loader.set_theme("dark")

        self.loading_dialog = None
        self.modifier_state = Qt.NoModifier  # type: ignore

        self.create_colored_icon = create_colored_icon
        self.icon_paths = prepare_status_icons()

        # Filename validation utilities available as functions in utils.filename_validator
        self.last_action = None  # Could be: 'folder_import', 'browse', 'rename', etc.
        self.current_folder_path = None
        self.current_folder_is_recursive = False  # Track if current folder was loaded recursively
        self.current_sort_column = 1  # Track current sort column (default: filename)
        self.current_sort_order = Qt.AscendingOrder  # type: ignore
        self.files = []
        self.preview_map = {}  # preview_filename -> FileItem
        self._selection_sync_mode = "normal"  # values: "normal", "toggle"
        self.pending_completion_dialog = None  # For delayed completion dialog execution

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

        # --- Initialize Batch Operations Manager ---
        from core.batch_operations_manager import get_batch_manager
        self.batch_manager = get_batch_manager(self)
        logger.info("[MainWindow] Batch Operations Manager initialized")

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

    def shortcut_load_metadata_all(self) -> None:
        """Load basic metadata for all files via Application Service."""
        self.app_service.load_metadata_all_fast()

    def shortcut_load_extended_metadata_all(self) -> None:
        """Load extended metadata for all files via Application Service."""
        self.app_service.load_metadata_all_extended()

    def shortcut_calculate_hash_selected(self) -> None:
        """Calculate hash for selected files via Application Service."""
        self.app_service.calculate_hash_selected()

    def shortcut_calculate_hash_all(self) -> None:
        """Calculate hash for all files via Application Service."""
        self.app_service.calculate_hash_all()

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

    def load_files_from_folder(self, folder_path: str, force: bool = False):
        """Load files from folder via Application Service."""
        self.app_service.load_files_from_folder(folder_path, force)

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
        """Load files from paths via Application Service."""
        self.app_service.load_files_from_paths(file_paths, clear=clear)

    def load_files_from_dropped_items(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:  # type: ignore
        """Load files from dropped items via Application Service."""
        self.app_service.load_files_from_dropped_items(paths, modifiers)

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """Prepare folder load via Application Service."""
        return self.app_service.prepare_folder_load(folder_path, clear=clear)

    def load_single_item_from_drop(self, path: str, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:  # type: ignore
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

    def sort_by_column(self, column: int, order: Optional[Qt.SortOrder] = None, force_order: Optional[Qt.SortOrder] = None) -> None:
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

    def handle_file_double_click(self, index: QModelIndex, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:  # type: ignore
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
        """Check if folder reload should be skipped."""
        # Legacy method - logic moved to Application Service
        return folder_path == self.current_folder_path and not force

    def get_file_items_from_folder(self, folder_path: str) -> list[FileItem]:
        """Get file items from folder."""
        # Legacy method - logic moved to Application Service
        return self.app_service.get_file_items_from_folder(folder_path)

    def update_module_dividers(self) -> None:
        """Delegates to RenameManager for module dividers update."""
        self.rename_manager.update_module_dividers()

    def show_metadata_status(self) -> None:
        """Delegates to InitializationManager for metadata status display."""
        self.initialization_manager.show_metadata_status()

    def _enable_selection_store_mode(self):
        """Enable SelectionStore mode in FileTableView."""
        print("[DEBUG] _enable_selection_store_mode called")
        if hasattr(self, 'initialization_manager'):
            self.initialization_manager.enable_selection_store_mode()
        if hasattr(self, 'file_table_view'):
            logger.debug("[MainWindow] Enabling SelectionStore mode in FileTableView", extra={"dev_only": True})
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

        # Use specialized metadata status method if status manager is available
        if hasattr(self, 'status_manager') and self.status_manager:
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

        # Use specialized metadata status method if status manager is available
        if hasattr(self, 'status_manager') and self.status_manager:
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

        # Use specialized file operation status method if status manager is available
        if hasattr(self, 'status_manager') and self.status_manager:
            self.status_manager.set_file_operation_status(
                f"Copied '{value}' to clipboard",
                success=True,
                auto_reset=True
            )

            # Override the reset delay for clipboard operations (shorter feedback)
            if hasattr(self.status_manager, '_status_timer') and self.status_manager._status_timer:
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
        # Legacy method - logic moved to WindowConfigManager
        if hasattr(self.window_config_manager, 'set_smart_default_geometry'):
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
            # No longer need column adjustment - columns maintain fixed widths from config

            logger.debug("[MainWindow] Used original FileTableView column configuration", extra={"dev_only": True})

        # Configure other table views with ColumnManager (they don't have the sophisticated logic)
        # Note: MetadataTreeView handles its own column configuration, so we skip it here
        # if hasattr(self, 'metadata_tree_view') and self.metadata_tree_view:
        #     self.column_manager.configure_table_columns(self.metadata_tree_view, 'metadata_tree')

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

    def reset_column_preferences(self, table_type: str, column_index: Optional[int] = None) -> None:
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

    # =====================================
    # Application Shutdown System
    # =====================================

    def changeEvent(self, event) -> None:
        """Handle window state changes (maximize, minimize, restore)."""
        super().changeEvent(event)

        if event.type() == QEvent.WindowStateChange:  # type: ignore
            self._handle_window_state_change()

    def resizeEvent(self, event) -> None:
        """Handle window resize events to update splitter ratios for wide screens."""
        super().resizeEvent(event)

        # Only update splitters if UI is fully initialized and window is visible
        if (hasattr(self, 'splitter_manager') and
            hasattr(self, 'horizontal_splitter') and
            self.isVisible() and
            not self.isMinimized()):

            # Get new window width
            new_width = self.width()

            # Use SplitterManager to update splitter sizes
            from utils.timer_manager import schedule_resize_adjust

            def update_splitters():
                self.splitter_manager.update_splitter_sizes_for_window_width(new_width)

            # Schedule the update to avoid conflicts with other resize operations
            schedule_resize_adjust(update_splitters, 50)

            # Also trigger column adjustment when window resizes
            if hasattr(self, 'file_table_view'):
                def trigger_column_adjustment():
                    self.splitter_manager.trigger_column_adjustment_after_splitter_change()

                # Schedule column adjustment after splitter update
                schedule_resize_adjust(trigger_column_adjustment, 60)

    def _handle_window_state_change(self) -> None:
        """Handle maximize/restore geometry and file table refresh."""
        # Handle maximize: store appropriate geometry for restore
        if self.isMaximized() and not hasattr(self, '_restore_geometry'):
            current_geo = self.geometry()
            initial_size = self._initial_geometry.size()

            # Use current geometry if manually resized, otherwise use initial
            is_manually_resized = (
                abs(current_geo.width() - initial_size.width()) > 10 or
                abs(current_geo.height() - initial_size.height()) > 10
            )

            self._restore_geometry = current_geo if is_manually_resized else self._initial_geometry
            logger.debug(f"[MainWindow] Stored {'manual' if is_manually_resized else 'initial'} geometry for restore")

        # Handle restore: restore stored geometry
        elif not self.isMaximized() and hasattr(self, '_restore_geometry'):
            self.setGeometry(self._restore_geometry)
            delattr(self, '_restore_geometry')
            logger.debug("[MainWindow] Restored geometry")

        # Refresh file table after state change
        self._refresh_file_table_for_window_change()

    def _refresh_file_table_for_window_change(self) -> None:
        """Refresh file table after window state changes."""
        if not hasattr(self, 'file_table_view') or not self.file_table_view.model():
            return

        from utils.timer_manager import schedule_resize_adjust

        def refresh():
            # Reset manual column preference for auto-sizing
            if not getattr(self.file_table_view, '_recent_manual_resize', False):
                self.file_table_view._has_manual_preference = False

            # Use existing splitter logic for column sizing
            if hasattr(self, 'horizontal_splitter'):
                sizes = self.horizontal_splitter.sizes()
                self.file_table_view.on_horizontal_splitter_moved(sizes[1], 1)

        schedule_resize_adjust(refresh, 25)

    def closeEvent(self, event) -> None:
        """
        Handles application shutdown and cleanup with graceful progress dialog.

        Ensures all resources are properly released and threads are stopped.
        """
        # If shutdown is already in progress, ignore additional close events
        if hasattr(self, '_shutdown_in_progress') and self._shutdown_in_progress:
            event.ignore()
            return

        logger.info("Application shutting down...")

        # 0. Check for unsaved metadata changes
        if self._check_for_unsaved_changes():
            reply = self.dialog_manager.confirm_unsaved_changes(self)

            if reply == "cancel":
                # User wants to cancel closing
                event.ignore()
                return
            elif reply == "save_and_close":
                # User wants to save changes before closing
                try:
                    # Save all modified metadata
                    if hasattr(self, 'metadata_manager') and self.metadata_manager:
                        if hasattr(self.metadata_manager, 'save_all_modified_metadata'):
                            self.metadata_manager.save_all_modified_metadata()
                            logger.info("[CloseEvent] Saved all metadata changes before closing")
                        else:
                            logger.warning("[CloseEvent] save_all_modified_metadata method not available")
                    else:
                        logger.warning("[CloseEvent] MetadataManager not available for saving")
                except Exception as e:
                    logger.error(f"[CloseEvent] Failed to save metadata before closing: {e}")
                    # Show error but continue closing anyway
                    from widgets.custom_message_dialog import CustomMessageDialog
                    CustomMessageDialog.information(
                        self,
                        "Save Error",
                        f"Failed to save metadata changes:\n{e}\n\nClosing anyway."
                    )
            # If reply == "close_without_saving", we just continue with closing

        # Mark shutdown as in progress
        self._shutdown_in_progress = True

        # Ignore this close event - we'll handle closing ourselves
        event.ignore()

        # Start async shutdown process
        self._start_async_shutdown()

    def _start_async_shutdown(self):
        """Start the async shutdown process with progress updates."""
        try:
            # Set wait cursor for the entire shutdown process
            QApplication.setOverrideCursor(Qt.WaitCursor)  # type: ignore

            # Create custom shutdown dialog that doesn't respond to ESC
            from widgets.metadata_waiting_dialog import MetadataWaitingDialog

            class ShutdownDialog(MetadataWaitingDialog):
                """Custom dialog for shutdown that ignores ESC key."""
                def keyPressEvent(self, event):
                    # Ignore ESC key during shutdown and maintain wait cursor
                    if event.key() == Qt.Key_Escape:  # type: ignore
                        logger.debug("[ShutdownDialog] ESC key ignored during shutdown")
                        # Ensure wait cursor is maintained
                        QApplication.setOverrideCursor(Qt.WaitCursor)  # type: ignore
                        return
                    # Handle other keys normally
                    super().keyPressEvent(event)

            self.shutdown_dialog = ShutdownDialog(self, is_extended=False)

            # Make dialog more visible and prevent it from closing
            self.shutdown_dialog.setWindowTitle("Closing OnCutF...")
            # Remove WindowStaysOnTopHint to prevent focus stealing
            # The dialog will be visible but won't force itself on top
            self.shutdown_dialog.set_status("Preparing to close...")

            # Prevent dialog from being closed by user
            self.shutdown_dialog.setWindowFlags(
                self.shutdown_dialog.windowFlags() & ~Qt.WindowCloseButtonHint  # type: ignore
            )

            # Show dialog but don't force focus
            self.shutdown_dialog.show()

            # Move dialog to center of screen
            screen = QApplication.desktop().screenGeometry()  # type: ignore
            dialog_geometry = self.shutdown_dialog.geometry()
            x = (screen.width() - dialog_geometry.width()) // 2
            y = (screen.height() - dialog_geometry.height()) // 2
            self.shutdown_dialog.move(x, y)

            QApplication.processEvents()

            logger.info("[CloseEvent] Shutdown dialog created and shown (ESC disabled, no focus stealing)")

            # Setup shutdown steps
            self.shutdown_steps = [
                ("Creating database backup...", self._shutdown_step_backup),
                ("Saving window configuration...", self._shutdown_step_config),
                ("Flushing batch operations...", self._shutdown_step_batch_operations),
                ("Cleaning up drag operations...", self._shutdown_step_drag),
                ("Closing dialogs...", self._shutdown_step_dialogs),
                ("Stopping metadata operations...", self._shutdown_step_metadata),
                ("Stopping background tasks...", self._shutdown_step_background),
                ("Cleaning up application context...", self._shutdown_step_context),
                ("Closing progress dialogs...", self._shutdown_step_progress_dialogs),
                ("Stopping timers...", self._shutdown_step_timers),
                ("Cleaning up Qt resources...", self._shutdown_step_qt_resources),
                ("Closing database connections...", self._shutdown_step_database),
                ("Cleaning up backup manager...", self._shutdown_step_backup_manager),
                ("Finalizing shutdown...", self._shutdown_step_finalize),
            ]

            self.current_shutdown_step = 0
            self.total_shutdown_steps = len(self.shutdown_steps)

            # Update progress to show we're starting
            self.shutdown_dialog.set_progress(0, self.total_shutdown_steps)
            QApplication.processEvents()

            logger.info(f"[CloseEvent] Starting shutdown with {self.total_shutdown_steps} steps")

            # Start the first step with shorter initial delay
            from PyQt5.QtCore import QTimer
            self.shutdown_timer = QTimer()
            self.shutdown_timer.setSingleShot(True)
            self.shutdown_timer.timeout.connect(self._execute_next_shutdown_step)
            self.shutdown_timer.start(500)  # Reduced from 1000ms to 500ms

        except Exception as e:
            logger.error(f"[CloseEvent] Error starting async shutdown: {e}")
            # Restore cursor and fallback to immediate close
            QApplication.restoreOverrideCursor()
            QApplication.quit()

    def _execute_next_shutdown_step(self):
        """Execute the next shutdown step."""
        try:
            if self.current_shutdown_step >= self.total_shutdown_steps:
                # All steps completed
                self._complete_shutdown()
                return

            # Ensure wait cursor is still active (reapply if needed)
            QApplication.setOverrideCursor(Qt.WaitCursor)  # type: ignore

            # Get current step
            step_name, step_function = self.shutdown_steps[self.current_shutdown_step]

            logger.info(f"[CloseEvent] Executing step {self.current_shutdown_step + 1}/{self.total_shutdown_steps}: {step_name}")

            # Update progress and status - make sure dialog is still visible
            if hasattr(self, 'shutdown_dialog') and self.shutdown_dialog and self.shutdown_dialog.isVisible():
                self.shutdown_dialog.set_status(step_name)
                self.shutdown_dialog.set_progress(self.current_shutdown_step, self.total_shutdown_steps)

                # Keep dialog visible but don't force focus
                self.shutdown_dialog.show()
                QApplication.processEvents()
            else:
                logger.warning("[CloseEvent] Shutdown dialog is not visible, recreating...")
                # Try to recreate dialog if it disappeared
                self._recreate_shutdown_dialog()

            try:
                # Execute the step
                step_function()
            except Exception as e:
                logger.error(f"[CloseEvent] Error in shutdown step '{step_name}': {e}")

            # Reapply wait cursor after step execution (in case it was changed)
            QApplication.setOverrideCursor(Qt.WaitCursor)  # type: ignore

            # Move to next step
            self.current_shutdown_step += 1

            # Schedule next step with shorter delays - faster but still visible
            delay = 500 if self.current_shutdown_step in [4, 5] else 350  # Reduced from 800/600 to 500/350
            if hasattr(self, 'shutdown_timer'):
                self.shutdown_timer.start(delay)

        except Exception as e:
            logger.error(f"[CloseEvent] Error in shutdown step execution: {e}")
            # Fallback to immediate close if something goes wrong
            self._complete_shutdown()

    def _recreate_shutdown_dialog(self):
        """Recreate shutdown dialog if it disappeared."""
        try:
            from widgets.metadata_waiting_dialog import MetadataWaitingDialog

            class ShutdownDialog(MetadataWaitingDialog):
                """Custom dialog for shutdown that ignores ESC key."""
                def keyPressEvent(self, event):
                    # Ignore ESC key during shutdown and maintain wait cursor
                    if event.key() == Qt.Key_Escape:  # type: ignore
                        logger.debug("[ShutdownDialog] ESC key ignored during shutdown")
                        # Ensure wait cursor is maintained
                        QApplication.setOverrideCursor(Qt.WaitCursor)  # type: ignore
                        return
                    # Handle other keys normally
                    super().keyPressEvent(event)

            self.shutdown_dialog = ShutdownDialog(self, is_extended=False)

            # Make dialog more visible and prevent it from closing
            self.shutdown_dialog.setWindowTitle("Closing OnCutF...")
            # Remove WindowStaysOnTopHint to prevent focus stealing
            # The dialog will be visible but won't force itself on top

            # Prevent dialog from being closed by user
            self.shutdown_dialog.setWindowFlags(
                self.shutdown_dialog.windowFlags() & ~Qt.WindowCloseButtonHint  # type: ignore
            )

            # Show dialog but don't force focus
            self.shutdown_dialog.show()

            # Move dialog to center of screen
            screen = QApplication.desktop().screenGeometry()  # type: ignore
            dialog_geometry = self.shutdown_dialog.geometry()
            x = (screen.width() - dialog_geometry.width()) // 2
            y = (screen.height() - dialog_geometry.height()) // 2
            self.shutdown_dialog.move(x, y)

            QApplication.processEvents()
            logger.info("[CloseEvent] Shutdown dialog recreated (ESC disabled, no focus stealing)")

        except Exception as e:
            logger.error(f"[CloseEvent] Error recreating shutdown dialog: {e}")

    def _complete_shutdown(self):
        """Complete the shutdown process."""
        try:
            logger.info("[CloseEvent] Completing shutdown process")

            # Ensure wait cursor is still active
            QApplication.setOverrideCursor(Qt.WaitCursor)  # type: ignore

            # Show completion - make sure dialog is visible
            if hasattr(self, 'shutdown_dialog') and self.shutdown_dialog:
                if not self.shutdown_dialog.isVisible():
                    self._recreate_shutdown_dialog()

                if self.shutdown_dialog and self.shutdown_dialog.isVisible():
                    self.shutdown_dialog.set_status("Cleanup complete!")
                    self.shutdown_dialog.set_progress(self.total_shutdown_steps, self.total_shutdown_steps)

                    # Keep dialog visible but don't force focus
                    self.shutdown_dialog.show()
                    QApplication.processEvents()

                    logger.info("[CloseEvent] Shutdown completion status shown")

            # Stop the shutdown timer
            if hasattr(self, 'shutdown_timer'):
                self.shutdown_timer.stop()

            # Schedule final close with shorter delay
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(800, self._final_close)  # Reduced from 1500ms to 800ms

        except Exception as e:
            logger.error(f"[CloseEvent] Error completing shutdown: {e}")
            # Fallback to immediate close
            self._final_close()

    def _final_close(self):
        """Final application close."""
        try:
            logger.info("[CloseEvent] Final close initiated")

            # Restore cursor
            QApplication.restoreOverrideCursor()

            # Close the shutdown dialog
            if hasattr(self, 'shutdown_dialog') and self.shutdown_dialog:
                self.shutdown_dialog.close()
                logger.info("[CloseEvent] Shutdown dialog closed")
        except Exception as e:
            logger.warning(f"[CloseEvent] Error closing shutdown dialog: {e}")

        try:
            # Force quit the application
            logger.info("[CloseEvent] Forcing application quit")
            QApplication.quit()

        except Exception as e:
            logger.warning(f"[CloseEvent] Error in final close: {e}")
            # Force quit the application as fallback
            import sys
            sys.exit(0)

    def _shutdown_step_backup(self):
        """Step 1: Create database backup."""
        if hasattr(self, 'backup_manager'):
            try:
                backup_path = self.backup_manager.backup_on_shutdown()
                if backup_path:
                    logger.info(f"[CloseEvent] Database backup created: {backup_path}")
                else:
                    logger.warning("[CloseEvent] Failed to create database backup")
            except Exception as e:
                logger.error(f"[CloseEvent] Error creating database backup: {e}")

    def _shutdown_step_config(self):
        """Step 2: Save window configuration and column changes."""
        # Save window configuration
        self.window_config_manager.save_window_config()

        # Force save any pending column width changes
        try:
            file_table = getattr(self, 'file_table', None)
            if file_table and hasattr(file_table, '_force_save_column_changes'):
                file_table._force_save_column_changes()
                logger.info("[CloseEvent] Forced save of pending column changes")
        except Exception as e:
            logger.warning(f"[CloseEvent] Error saving pending column changes: {e}")

    def _shutdown_step_batch_operations(self):
        """Step 3: Flush all pending batch operations."""
        if hasattr(self, 'batch_manager') and self.batch_manager:
            try:
                # Get pending operations before flushing
                pending = self.batch_manager.get_pending_operations()
                if pending:
                    logger.info(f"[CloseEvent] Flushing pending batch operations: {pending}")

                    # Flush all batch types
                    results = self.batch_manager.flush_all()

                    # Log results
                    total_flushed = sum(results.values())
                    if total_flushed > 0:
                        logger.info(f"[CloseEvent] Flushed {total_flushed} batch operations: {results}")

                    # Get final statistics
                    stats = self.batch_manager.get_stats()
                    logger.info(f"[CloseEvent] Batch operations stats: {stats.batched_operations} total batched, "
                               f"avg batch size: {stats.average_batch_size:.1f}, "
                               f"estimated time saved: {stats.total_time_saved:.2f}s")
                else:
                    logger.info("[CloseEvent] No pending batch operations to flush")

                # Clean up batch manager
                self.batch_manager.cleanup()
                logger.info("[CloseEvent] Batch operations manager cleaned up")

            except Exception as e:
                logger.error(f"[CloseEvent] Error during batch operations cleanup: {e}")
        else:
            logger.warning("[CloseEvent] Batch operations manager not available")

    def _shutdown_step_drag(self):
        """Step 4: Clean up drag operations."""
        self.drag_cleanup_manager.emergency_drag_cleanup()

    def _shutdown_step_dialogs(self):
        """Step 5: Clean up dialogs (but not the shutdown dialog)."""
        if hasattr(self, 'dialog_manager'):
            # Don't call dialog_manager.cleanup() as it closes ALL dialogs including shutdown dialog
            # Instead, manually close specific dialogs
            try:
                # Close any open message dialogs (but not shutdown dialog)
                for widget in QApplication.topLevelWidgets():
                    if (hasattr(widget, 'close') and 'Dialog' in widget.__class__.__name__
                        and widget != getattr(self, 'shutdown_dialog', None)):
                        widget.close()

                # Close any open file dialogs
                from core.pyqt_imports import QFileDialog
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget, QFileDialog):
                        widget.close()

                # Process any pending events
                QApplication.processEvents()

                logger.debug("[CloseEvent] Closed dialogs (excluding shutdown dialog)")
            except Exception as e:
                logger.warning(f"[CloseEvent] Error closing dialogs: {e}")

    def _shutdown_step_metadata(self):
        """Step 6: Clean up metadata operations."""
        if hasattr(self, 'metadata_manager') and self.metadata_manager:
            self.metadata_manager.cleanup()

        # Clean up global UnifiedMetadataManager
        from core.unified_metadata_manager import cleanup_unified_metadata_manager
        cleanup_unified_metadata_manager()

        # Force cleanup any remaining ExifTool processes
        try:
            from utils.exiftool_wrapper import ExifToolWrapper
            ExifToolWrapper.force_cleanup_all_exiftool_processes()
            logger.info("[Shutdown] ExifTool processes cleaned up")
        except Exception as e:
            logger.warning(f"[Shutdown] Error cleaning up ExifTool processes: {e}")

    def _shutdown_step_background(self):
        """Step 7: Clean up background workers."""
        self._force_cleanup_background_workers()

    def _shutdown_step_context(self):
        """Step 8: Clean up application context."""
        if hasattr(self, 'context'):
            try:
                self.context.cleanup()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error cleaning application context: {e}")

    def _shutdown_step_progress_dialogs(self):
        """Step 8: Close progress dialogs."""
        self._force_close_progress_dialogs()

    def _shutdown_step_timers(self):
        """Step 9: Stop timers."""
        # First stop TimerManager timers
        try:
            from utils.timer_manager import cleanup_all_timers
            cleaned_timers = cleanup_all_timers()
            if cleaned_timers > 0:
                logger.info(f"[CloseEvent] Cleaned up {cleaned_timers} scheduled timers")
        except Exception as e:
            logger.warning(f"[CloseEvent] Error cleaning TimerManager: {e}")

        # Then find and stop any remaining QTimer instances (except our shutdown timer)
        try:
            from PyQt5.QtCore import QTimer
            remaining_timers = self.findChildren(QTimer)
            for timer in remaining_timers:
                if timer != self.shutdown_timer and timer.isActive():
                    timer.stop()
                    logger.debug(f"[CloseEvent] Stopped QTimer: {timer.objectName() or 'unnamed'}")

            active_timers = [t for t in remaining_timers if t != self.shutdown_timer and t.isActive()]
            if active_timers:
                logger.info(f"[CloseEvent] Stopped {len(active_timers)} QTimer instances")
        except Exception as e:
            logger.warning(f"[CloseEvent] Error stopping QTimer instances: {e}")

    def _shutdown_step_qt_resources(self):
        """Step 10: Clean up Qt resources."""
        try:
            QApplication.processEvents()
        except Exception as e:
            logger.warning(f"[CloseEvent] Error processing events during cleanup: {e}")

    def _shutdown_step_database(self):
        """Step 11: Close database connections."""
        if hasattr(self, 'db_manager'):
            try:
                self.db_manager.close()
                logger.info("[CloseEvent] Database connections closed")
            except Exception as e:
                logger.warning(f"[CloseEvent] Error closing database: {e}")

    def _shutdown_step_backup_manager(self):
        """Step 12: Clean up backup manager."""
        if hasattr(self, 'backup_manager'):
            try:
                from core.backup_manager import cleanup_backup_manager
                cleanup_backup_manager()
                logger.info("[CloseEvent] Backup manager cleaned up")
            except Exception as e:
                logger.warning(f"[CloseEvent] Error cleaning backup manager: {e}")

    def _shutdown_step_finalize(self):
        """Step 13: Final cleanup."""
        logger.info("[CloseEvent] Final cleanup - forcing application termination")

    def _force_cleanup_background_workers(self) -> None:
        """Force cleanup of any background workers/threads."""
        logger.info("[CloseEvent] Cleaning up background workers...")

        # 1. Cleanup HashWorker if it exists
        if hasattr(self, 'event_handler_manager') and hasattr(self.event_handler_manager, 'hash_worker'):
            hash_worker = self.event_handler_manager.hash_worker
            if hash_worker and hash_worker.isRunning():
                logger.info("[CloseEvent] Cancelling and terminating HashWorker...")
                hash_worker.cancel()
                if not hash_worker.wait(1000):  # Wait max 1 second
                    logger.warning("[CloseEvent] HashWorker did not stop gracefully, terminating...")
                    hash_worker.terminate()
                    hash_worker.wait(500)  # Wait another 500ms for termination

        # 2. Find and terminate any other QThread instances
        from PyQt5.QtCore import QThread
        threads = self.findChildren(QThread)
        for thread in threads:
            if thread.isRunning():
                logger.info(f"[CloseEvent] Terminating QThread: {thread.__class__.__name__}")
                thread.quit()
                if not thread.wait(1000):  # Wait max 1 second
                    thread.terminate()
                    thread.wait(500)

    def _force_close_progress_dialogs(self) -> None:
        """Force close any active progress dialogs except the shutdown dialog."""
        from utils.progress_dialog import ProgressDialog
        from widgets.metadata_waiting_dialog import MetadataWaitingDialog

        # Find and close any active progress dialogs
        dialogs_closed = 0

        # Close ProgressDialog instances
        progress_dialogs = self.findChildren(ProgressDialog)
        for dialog in progress_dialogs:
            if dialog.isVisible():
                logger.info("[CloseEvent] Force closing ProgressDialog")
                dialog.reject()  # Force close without waiting
                dialogs_closed += 1

        # Close MetadataWaitingDialog instances (but NOT the shutdown dialog)
        metadata_dialogs = self.findChildren(MetadataWaitingDialog)
        for dialog in metadata_dialogs:
            if dialog.isVisible() and dialog != getattr(self, 'shutdown_dialog', None):
                logger.info("[CloseEvent] Force closing MetadataWaitingDialog")
                dialog.reject()  # Force close without waiting
                dialogs_closed += 1

        if dialogs_closed > 0:
            logger.info(f"[CloseEvent] Force closed {dialogs_closed} progress dialogs (excluding shutdown dialog)")

    def _check_for_unsaved_changes(self) -> bool:
        """
        Check if there are any unsaved metadata changes.

        Returns:
            bool: True if there are unsaved changes, False otherwise
        """
        if not hasattr(self, 'metadata_tree_view'):
            return False

        try:
            # Force save current file modifications to per-file storage first
            if hasattr(self.metadata_tree_view, '_current_file_path') and self.metadata_tree_view._current_file_path:
                if self.metadata_tree_view.modified_items:
                    self.metadata_tree_view._set_in_path_dict(
                        self.metadata_tree_view._current_file_path,
                        self.metadata_tree_view.modified_items.copy(),
                        self.metadata_tree_view.modified_items_per_file
                    )

            # Get all modified metadata for all files
            all_modifications = self.metadata_tree_view.get_all_modified_metadata_for_files()

            # Check if there are any actual modifications
            has_modifications = any(modifications for modifications in all_modifications.values())

            if has_modifications:
                logger.info(f"[CloseEvent] Found unsaved changes in {len(all_modifications)} files")
                for file_path, modifications in all_modifications.items():
                    if modifications:
                        logger.debug(f"[CloseEvent] - {file_path}: {list(modifications.keys())}")

            return has_modifications

        except Exception as e:
            logger.warning(f"[CloseEvent] Error checking for unsaved changes: {e}")
            return False
