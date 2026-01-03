"""Module: main_window.py

Author: Michael Economou
Date: 2025-05-01

Main application window for oncutf.

Provides the primary UI including:
- File table for loaded files display
- Metadata tree view
- Rename modules panel
- Folder tree navigation
"""

# type: ignore[attr-defined]

from PyQt5.QtCore import Qt

# Import all config constants from centralized module
# Core application modules
from oncutf.core.config_imports import *

# Import all PyQt5 classes from centralized module
from oncutf.core.pyqt_imports import *

# Data models and business logic modules
from oncutf.models.file_item import FileItem

# Phase 4A UI Handlers
from oncutf.ui.handlers.shutdown_lifecycle_handler import ShutdownLifecycleHandler  # noqa: F401

# Utility functions and helpers
from oncutf.utils.logging.logger_factory import get_cached_logger

# UI widgets and custom components

logger = get_cached_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, theme_callback=None) -> None:
        """Initializes the main window and sets up the layout.

        Args:
            theme_callback: Optional callback to apply theme before enabling updates

        """
        super().__init__()

        # Prevent repaints during initialization (seamless display)
        self.setUpdatesEnabled(False)

        # Preview debounce timer (Day 1-2 Performance Optimization)
        self._preview_debounce_timer: QTimer | None = None
        self._preview_pending = False

        # Use InitializationOrchestrator for structured initialization
        from oncutf.core.initialization.initialization_orchestrator import (
            InitializationOrchestrator,
        )

        orchestrator = InitializationOrchestrator(self)
        orchestrator.orchestrate_initialization(theme_callback)

    # --- Method definitions ---

    # =====================================
    # Application Service Delegates
    # (These methods now use the Application Service Layer)
    # =====================================

    def select_all_rows(self) -> None:
        """Select all rows via Application Service."""
        return self.shortcut_handler.select_all_rows()

    def clear_all_selection(self) -> None:
        """Clear all selection via Application Service."""
        return self.shortcut_handler.clear_all_selection()

    def invert_selection(self) -> None:
        """Invert selection via Application Service."""
        return self.shortcut_handler.invert_selection()

    def shortcut_load_metadata(self) -> None:
        """Load fast metadata via Application Service."""
        return self.shortcut_handler.shortcut_load_metadata()

    def shortcut_load_extended_metadata(self) -> None:
        """Load extended metadata via Application Service."""
        return self.shortcut_handler.shortcut_load_extended_metadata()

    def shortcut_save_selected_metadata(self) -> None:
        """Save selected metadata via Application Service."""
        return self.shortcut_handler.shortcut_save_selected_metadata()

    def shortcut_save_all_metadata(self) -> None:
        """Save all modified metadata via Application Service."""
        return self.shortcut_handler.shortcut_save_all_metadata()

    def shortcut_calculate_hash_selected(self) -> None:
        """Calculate hash for selected files via Application Service."""
        return self.shortcut_handler.shortcut_calculate_hash_selected()

    def rename_files(self) -> None:
        """Execute batch rename via Application Service."""
        return self.shortcut_handler.rename_files()

    def clear_file_table_shortcut(self) -> None:
        """Clear file table via Application Service."""
        return self.shortcut_handler.clear_file_table_shortcut()

    def force_drag_cleanup(self) -> None:
        """Force drag cleanup via Application Service."""
        return self.shortcut_handler.force_drag_cleanup()

    def global_undo(self) -> None:
        """Global undo handler (Ctrl+Z).

        Note: Unified undo/redo system not yet implemented.
        """
        return self.shortcut_handler.global_undo()

    def global_redo(self) -> None:
        """Global redo handler (Ctrl+Shift+Z).

        Note: Unified undo/redo system not yet implemented.
        """
        return self.shortcut_handler.global_redo()

    def show_command_history(self) -> None:
        """Show command history dialog (Ctrl+Y).

        Currently shows MetadataHistoryDialog for metadata operations.
        """
        return self.shortcut_handler.show_command_history()

    def auto_color_by_folder(self) -> None:
        """Auto-color files by their parent folder (Ctrl+Shift+C).

        Groups all files by folder and assigns unique random colors to each folder's files.
        Skips files that already have colors assigned (preserves user choices).
        Only works when 2+ folders are present.
        """
        return self.shortcut_handler.auto_color_by_folder()

    def request_preview_update(self) -> None:
        """Request preview update via UtilityManager."""
        self.utility_manager.request_preview_update()

    def request_preview_update_debounced(self) -> None:
        """Request preview update with 300ms debounce.

        Day 1-2 Performance Optimization: Prevents redundant preview recalculations
        during rapid user input (e.g., typing, slider adjustments).

        Usage:
        - Module parameter changes (typing, sliders, dropdowns)
        - Final transform changes (greeklish, case, separator)

        The timer resets on each call, so only the final state triggers preview.
        """
        self._preview_pending = True

        # Cancel existing timer
        if self._preview_debounce_timer and self._preview_debounce_timer.isActive():
            self._preview_debounce_timer.stop()

        # Create timer on first use
        if not self._preview_debounce_timer:
            self._preview_debounce_timer = QTimer(self)
            self._preview_debounce_timer.setSingleShot(True)
            self._preview_debounce_timer.timeout.connect(self._execute_pending_preview)

        # Start 300ms countdown
        self._preview_debounce_timer.start(300)

    def _execute_pending_preview(self) -> None:
        """Execute pending preview update after debounce delay."""
        if self._preview_pending:
            self._preview_pending = False
            self.utility_manager.request_preview_update()

    def generate_preview_names(self) -> None:
        """Generate preview names via UtilityManager."""
        self.utility_manager.generate_preview_names()

    def center_window(self) -> None:
        """Center window via Application Service."""
        return self.window_event_handler.center_window()

    def force_reload(self) -> None:
        """Force reload via UtilityManager."""
        self.utility_manager.force_reload()

    def handle_browse(self) -> None:
        """Handle browse via EventHandlerManager."""
        self.event_handler_manager.handle_browse()

    def handle_folder_import(self) -> None:
        """Handle folder import via EventHandlerManager."""
        self.event_handler_manager.handle_folder_import()

    def reload_current_folder(self) -> None:
        """Reload current folder via FileLoadManager."""
        self.file_load_manager.reload_current_folder()

    # =====================================
    # File Operations via Application Service
    # =====================================

    def load_files_from_folder(self, folder_path: str, force: bool = False) -> None:
        """Load files from folder via Application Service."""
        self.app_service.load_files_from_folder(folder_path, force)

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
        """Load files from paths via FileLoadController."""
        result = self.file_load_controller.load_files(file_paths, clear=clear)
        logger.debug("[FileLoadController] load_files result: %s", result, extra={"dev_only": True})

    def load_files_from_dropped_items(
        self,
        paths: list[str],
        modifiers: Qt.KeyboardModifiers = Qt.NoModifier,  # type: ignore[arg-type]
    ) -> None:
        """Load files from dropped items via FileLoadController."""
        result = self.file_load_controller.handle_drop(paths, modifiers)
        logger.debug(
            "[FileLoadController] handle_drop result: %s", result, extra={"dev_only": True}
        )

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """Prepare folder load via FileLoadManager."""
        return self.file_load_manager.prepare_folder_load(folder_path, clear=clear)

    def load_single_item_from_drop(
        self,
        path: str,
        modifiers: Qt.KeyboardModifiers = Qt.NoModifier,  # type: ignore[arg-type]
    ) -> None:
        """Load single item from drop via FileLoadController."""
        self.file_load_controller.handle_drop([path], modifiers)

    def load_metadata_for_items(
        self, items: list[FileItem], use_extended: bool = False, source: str = "unknown"
    ) -> None:
        """Load metadata for items via MetadataController."""
        result = self.metadata_controller.load_metadata(items, use_extended, source)
        logger.debug(
            "[MetadataController] load_metadata result: %s",
            result.get("success"),
            extra={"dev_only": True},
        )

    # =====================================
    # Table Operations via Application Service
    # =====================================

    def sort_by_column(
        self,
        column: int,
        order: Qt.SortOrder | None = None,
        force_order: Qt.SortOrder | None = None,
    ) -> None:
        """Sort by column via TableManager."""
        self.table_manager.sort_by_column(column, order, force_order)  # type: ignore[arg-type]

    def prepare_file_table(self, file_items: list[FileItem]) -> None:
        """Prepare file table via TableManager."""
        self.table_manager.prepare_file_table(file_items)

    def restore_fileitem_metadata_from_cache(self) -> None:
        """Restore metadata from cache via MetadataController."""
        result = self.metadata_controller.restore_metadata_from_cache()
        logger.debug(
            "[MetadataController] restore_metadata_from_cache result: %s",
            result.get("success"),
            extra={"dev_only": True},
        )

    def clear_file_table(self, message: str = "No folder selected") -> None:  # noqa: ARG002
        """Clear file table via FileLoadController."""
        success = self.file_load_controller.clear_files()
        logger.debug(
            "[FileLoadController] clear_files result: %s", success, extra={"dev_only": True}
        )

    def get_common_metadata_fields(self) -> list[str]:
        """Get common metadata fields via MetadataController."""
        return self.metadata_controller.get_common_metadata_fields()

    def set_fields_from_list(self, field_names: list[str]) -> None:
        """Set fields from list via TableManager."""
        self.table_manager.set_fields_from_list(field_names)

    def after_check_change(self) -> None:
        """Handle check change via TableManager."""
        self.table_manager.after_check_change()

    def get_selected_files(self) -> list[FileItem]:
        """Get selected files via TableManager."""
        return self.table_manager.get_selected_files()

    # =====================================
    # Event Handling via Application Service
    # =====================================

    def handle_table_context_menu(self, position) -> None:
        """Handle table context menu via EventHandlerManager."""
        self.event_handler_manager.handle_table_context_menu(position)

    def handle_file_double_click(
        self,
        index: QModelIndex,
        modifiers: Qt.KeyboardModifiers = Qt.NoModifier,  # type: ignore[arg-type]
    ) -> None:
        """Handle file double click via EventHandlerManager."""
        self.event_handler_manager.handle_file_double_click(index, modifiers)

    def on_table_row_clicked(self, index: QModelIndex) -> None:
        """Handle table row click via EventHandlerManager."""
        self.event_handler_manager.on_table_row_clicked(index)

    def handle_header_toggle(self, _) -> None:
        """Handle header toggle via EventHandlerManager."""
        self.event_handler_manager.handle_header_toggle(_)

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement via SplitterManager."""
        self.splitter_manager.on_horizontal_splitter_moved(pos, index)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement via SplitterManager."""
        self.splitter_manager.on_vertical_splitter_moved(pos, index)

    # =====================================
    # Preview Operations via Application Service
    # =====================================

    def get_identity_name_pairs(self) -> list[tuple[str, str]]:
        """Get identity name pairs via PreviewManager."""
        return self.preview_manager.get_identity_name_pairs(self.file_model.files)

    def update_preview_tables_from_pairs(self, name_pairs: list[tuple[str, str]]) -> None:
        """Update preview tables from pairs via PreviewManager."""
        self.preview_manager.update_preview_tables_from_pairs(name_pairs)

    def compute_max_filename_width(self, file_list: list[FileItem]) -> int:
        """Compute max filename width via PreviewManager."""
        return self.preview_manager.compute_max_filename_width(file_list)

    def update_preview_from_selection(self, selected_rows: list[int]) -> None:
        """Update preview from selection via SelectionManager."""
        self.selection_manager.update_preview_from_selection(selected_rows)

    # =====================================
    # Utility Operations via Application Service
    # =====================================

    def get_selected_rows_files(self) -> list:
        """Get selected rows as files via UtilityManager."""
        return self.utility_manager.get_selected_rows_files()

    def find_fileitem_by_path(self, path: str) -> list[FileItem]:
        """Find FileItem by path via FileOperationsManager."""
        return self.file_operations_manager.find_fileitem_by_path(self.file_model.files, path)  # type: ignore[return-value]

    def get_modifier_flags(self) -> tuple[bool, bool]:
        """Get modifier flags via UtilityManager."""
        return self.utility_manager.get_modifier_flags()

    def determine_metadata_mode(self) -> tuple[bool, bool]:
        """Determine metadata mode via MetadataController."""
        return self.metadata_controller.determine_metadata_mode()

    def should_use_extended_metadata(self) -> bool:
        """Determine if extended metadata should be used via MetadataController."""
        return self.metadata_controller.should_use_extended_metadata()

    def update_files_label(self) -> None:
        """Update files label via UtilityManager."""
        self.utility_manager.update_files_label()

    # =====================================
    # Validation & Dialog Operations via Application Service
    # =====================================

    def confirm_large_folder(self, file_list: list[str], folder_path: str) -> bool:
        """Confirm large folder via FileValidationManager and DialogManager."""
        return self.app_service.confirm_large_folder(file_list, folder_path)

    def check_large_files(self, files: list[FileItem]) -> list[FileItem]:
        """Check large files via FileValidationManager and DialogManager."""
        return self.app_service.check_large_files(files)

    def confirm_large_files(self, files: list[FileItem]) -> bool:
        """Confirm large files via FileValidationManager and DialogManager."""
        return self.app_service.confirm_large_files(files)

    def prompt_file_conflict(self, target_path: str) -> str:
        """Prompt file conflict via Application Service."""
        return self.app_service.prompt_file_conflict(target_path)

    def validate_operation_for_user(self, files: list[str], operation_type: str) -> dict:
        """Validate operation for user via Application Service."""
        return self.app_service.validate_operation_for_user(files, operation_type)

    def identify_moved_files(self, file_paths: list[str]) -> dict:
        """Identify moved files via FileValidationManager."""
        return self.app_service.identify_moved_files(file_paths)

    def set_status(
        self, text: str, color: str = "", auto_reset: bool = False, reset_delay: int = 3000
    ) -> None:
        """Set status text and color via StatusManager."""
        self.status_manager.set_status(text, color, auto_reset, reset_delay)

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
        return folder_path == self.context.get_current_folder() and not force

    def get_file_items_from_folder(self, folder_path: str) -> list[FileItem]:
        """Get file items from folder via FileLoadManager."""
        return self.file_load_manager.get_file_items_from_folder(folder_path)

    def update_module_dividers(self) -> None:
        """Delegates to RenameManager for module dividers update."""
        self.rename_manager.update_module_dividers()

    def show_metadata_status(self) -> None:
        """Delegates to InitializationManager for metadata status display."""
        self.initialization_manager.show_metadata_status()

    def _enable_selection_store_mode(self):
        """Enable SelectionStore mode in FileTableView."""
        if hasattr(self, "initialization_manager"):
            self.initialization_manager.enable_selection_store_mode()
        if hasattr(self, "file_table_view"):
            logger.debug(
                "[MainWindow] Enabling SelectionStore mode in FileTableView",
                extra={"dev_only": True},
            )
            self.file_table_view.enable_selection_store_mode()

    # =====================================
    # Metadata Editing Signal Handlers
    # =====================================

    def on_metadata_value_edited(self, key_path: str, old_value: str, new_value: str) -> None:
        """Handle metadata value edited signal from metadata tree view.

        Args:
            key_path: The metadata key path (e.g. "EXIF/Rotation")
            old_value: The previous value
            new_value: The new value

        """
        return self.metadata_signal_handler.on_metadata_value_edited(key_path, old_value, new_value)

    def on_metadata_value_reset(self, key_path: str) -> None:
        """Handle metadata value reset signal from metadata tree view.

        Args:
            key_path: The metadata key path that was reset

        """
        return self.metadata_signal_handler.on_metadata_value_reset(key_path)

    def on_metadata_value_copied(self, value: str) -> None:
        """Handle metadata value copied signal from metadata tree view.

        Args:
            value: The value that was copied to clipboard

        """
        return self.metadata_signal_handler.on_metadata_value_copied(value)

    # =====================================
    # Window Configuration Management
    # =====================================

    def _load_window_config(self) -> None:
        """Load and apply window configuration from config manager."""
        return self.window_event_handler._load_window_config()

    def _set_smart_default_geometry(self) -> None:
        """Set smart default window geometry based on screen size."""
        return self.window_event_handler._set_smart_default_geometry()

    def _save_window_config(self) -> None:
        """Save current window state to config manager."""
        return self.window_event_handler._save_window_config()

    def _apply_loaded_config(self) -> None:
        """Apply loaded configuration after UI is fully initialized."""
        return self.window_event_handler._apply_loaded_config()

    def _ensure_initial_column_sizing(self) -> None:
        """Ensure column widths are properly sized on startup, especially when no config exists."""
        return self.config_column_handler.ensure_initial_column_sizing()

    def configure_table_columns(self, table_view, table_type: str) -> None:
        """Configure columns for a specific table view using ColumnManager."""
        return self.config_column_handler.configure_table_columns(table_view, table_type)

    def adjust_columns_for_splitter_change(self, table_view, table_type: str) -> None:
        """Adjust columns when splitter position changes using ColumnManager."""
        return self.config_column_handler.adjust_columns_for_splitter_change(table_view, table_type)

    def reset_column_preferences(self, table_type: str, column_index: int | None = None) -> None:
        """Reset user preferences for columns to allow auto-sizing."""
        return self.config_column_handler.reset_column_preferences(table_type, column_index)

    def save_column_state(self, table_type: str) -> dict:
        """Save current column state for persistence."""
        return self.config_column_handler.save_column_state(table_type)

    def load_column_state(self, table_type: str, state_data: dict) -> None:
        """Load column state from persistence."""
        return self.config_column_handler.load_column_state(table_type, state_data)

    def restore_last_folder_if_available(self) -> None:
        """Restore the last folder if available and user wants it."""
        return self.config_column_handler.restore_last_folder_if_available()

    def get_selected_files_ordered(self) -> list[FileItem]:
        """Unified method to get selected files in table display order.

        Returns:
            List of FileItem objects sorted by their row position in the table

        """
        if not (hasattr(self, "file_table_view") and hasattr(self, "file_model")):
            return []

        if not self.file_model or not self.file_model.files:
            return []

        # Get current selection and sort to maintain display order
        selected_rows = self.file_table_view._selection_behavior.get_current_selection()
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
        return self.window_event_handler.changeEvent(event)

    def resizeEvent(self, event) -> None:
        """Handle window resize events to update splitter ratios for wide screens."""
        return self.window_event_handler.resizeEvent(event)

    def _handle_window_state_change(self) -> None:
        """Handle maximize/restore geometry and file table refresh."""
        return self.window_event_handler._handle_window_state_change()

    def _refresh_file_table_for_window_change(self) -> None:
        """Refresh file table after window state changes."""
        return self.window_event_handler._refresh_file_table_for_window_change()

    def closeEvent(self, event) -> None:
        """Handles application shutdown and cleanup using Shutdown Coordinator.

        Ensures all resources are properly released and threads are stopped.
        """
        return self.shutdown_handler.closeEvent(event)

    def _start_coordinated_shutdown(self):
        """Start the coordinated shutdown process using ShutdownCoordinator."""
        return self.shutdown_handler._start_coordinated_shutdown()

    def _pre_coordinator_cleanup(self):
        """Perform cleanup before coordinator shutdown (UI-specific cleanup)."""
        return self.shutdown_handler._pre_coordinator_cleanup()

    def _post_coordinator_cleanup(self):
        """Perform final cleanup after coordinator shutdown."""
        return self.shutdown_handler._post_coordinator_cleanup()

    def _complete_shutdown(self, success: bool = True):
        """Complete the shutdown process."""
        return self.shutdown_handler._complete_shutdown(success)

    def _check_for_unsaved_changes(self) -> bool:
        """Check if there are any unsaved metadata changes.

        Returns:
            bool: True if there are unsaved changes, False otherwise

        """
        return self.shutdown_handler._check_for_unsaved_changes()

    def _force_cleanup_background_workers(self) -> None:
        """Force cleanup of any background workers/threads."""
        return self.shutdown_handler._force_cleanup_background_workers()

    def _force_close_progress_dialogs(self) -> None:
        """Force close any active progress dialogs except the shutdown dialog."""
        return self.shutdown_handler._force_close_progress_dialogs()

    def refresh_metadata_widgets(self):
        """Refresh all active MetadataWidget instances and trigger preview update."""
        return self.metadata_signal_handler.refresh_metadata_widgets()

    def _trigger_unified_preview_update(self):
        """Trigger preview update using UnifiedRenameEngine ONLY."""
        return self.metadata_signal_handler._trigger_unified_preview_update()

    def update_active_metadata_widget_options(self):
        """Find the active MetadataWidget and call trigger_update_options and emit_if_changed (for selection change)."""
        return self.metadata_signal_handler.update_active_metadata_widget_options()

    def _register_managers_in_context(self):
        """Register all managers in ApplicationContext for centralized access.

        This eliminates the need for parent_window.some_manager traversal patterns.
        Components can access managers via context.get_manager('name') instead.
        """
        return self.config_column_handler._register_managers_in_context()

    def _register_shutdown_components(self):
        """Register all concurrent components with shutdown coordinator."""
        return self.shutdown_handler._register_shutdown_components()
