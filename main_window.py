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

from datetime import datetime

from PyQt5.QtCore import Qt

# Import all config constants from centralized module
# Core application modules
from core.config_imports import *

# Import all PyQt5 classes from centralized module
from core.pyqt_imports import *

# Data models and business logic modules
from models.file_item import FileItem

# Utility functions and helpers
from utils.logger_factory import get_cached_logger

# UI widgets and custom components

logger = get_cached_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        """Initializes the main window and sets up the layout."""
        super().__init__()

        # Use InitializationOrchestrator for structured initialization (Phase 4)
        from core.initialization_orchestrator import InitializationOrchestrator

        orchestrator = InitializationOrchestrator(self)
        orchestrator.orchestrate_initialization()

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
        """Save all modified metadata via Application Service."""
        self.app_service.save_all_metadata()

    def shortcut_calculate_hash_selected(self) -> None:
        """Calculate hash for selected files via Application Service."""
        self.app_service.calculate_hash_selected()

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

    # =====================================
    # Backward Compatibility Properties
    # =====================================

    @property
    def files(self) -> list:
        """
        Backward compatibility property for accessing files.

        Returns files from FileTableModel (which is the source of truth for UI display).
        Use context.file_store.get_loaded_files() for centralized state access.
        """
        if hasattr(self, "file_model") and self.file_model:
            return self.file_model.files
        return []

    @property
    def current_folder_path(self) -> str | None:
        """
        Backward compatibility property for current folder path.

        Returns current folder from ApplicationContext.
        """
        if hasattr(self, "context") and self.context:
            return self.context.get_current_folder()
        return None

    @current_folder_path.setter
    def current_folder_path(self, value: str | None) -> None:
        """Set current folder path via ApplicationContext."""
        if hasattr(self, "context") and self.context:
            # Preserve recursive mode when setting folder
            recursive = self.context.is_recursive_mode()
            self.context.set_current_folder(value, recursive)

    @property
    def current_folder_is_recursive(self) -> bool:
        """
        Backward compatibility property for recursive mode flag.

        Returns recursive mode from ApplicationContext.
        """
        if hasattr(self, "context") and self.context:
            return self.context.is_recursive_mode()
        return False

    @current_folder_is_recursive.setter
    def current_folder_is_recursive(self, value: bool) -> None:
        """Set recursive mode via ApplicationContext."""
        if hasattr(self, "context") and self.context:
            self.context.set_recursive_mode(value)

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

    def load_files_from_folder(self, folder_path: str, force: bool = False) -> None:
        """Load files from folder via Application Service."""
        self.app_service.load_files_from_folder(folder_path, force)

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
        """Load files from paths via Application Service."""
        self.app_service.load_files_from_paths(file_paths, clear=clear)

    def load_files_from_dropped_items(
        self,
        paths: list[str],
        modifiers: Qt.KeyboardModifiers = Qt.NoModifier,  # type: ignore
    ) -> None:  # type: ignore
        """Load files from dropped items via Application Service."""
        self.app_service.load_files_from_dropped_items(paths, modifiers)

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """Prepare folder load via Application Service."""
        return self.app_service.prepare_folder_load(folder_path, clear=clear)

    def load_single_item_from_drop(
        self,
        path: str,
        modifiers: Qt.KeyboardModifiers = Qt.NoModifier,  # type: ignore
    ) -> None:  # type: ignore
        """Load single item from drop via Application Service."""
        self.app_service.load_single_item_from_drop(path, modifiers)

    def _handle_folder_drop(self, folder_path: str, merge_mode: bool, recursive: bool) -> None:
        """Handle folder drop via Application Service."""
        self.app_service.handle_folder_drop(folder_path, merge_mode, recursive)

    def _handle_file_drop(self, file_path: str, merge_mode: bool) -> None:
        """Handle file drop via Application Service."""
        self.app_service.handle_file_drop(file_path, merge_mode)

    def load_metadata_for_items(
        self, items: list[FileItem], use_extended: bool = False, source: str = "unknown"
    ) -> None:
        """Load metadata for items via Application Service."""
        self.app_service.load_metadata_for_items(items, use_extended, source)

    # =====================================
    # Table Operations via Application Service
    # =====================================

    def sort_by_column(
        self,
        column: int,
        order: Qt.SortOrder | None = None,
        force_order: Qt.SortOrder | None = None,
    ) -> None:
        """Sort by column via Application Service."""
        self.app_service.sort_by_column(column, order, force_order)  # type: ignore

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

    def handle_file_double_click(
        self,
        index: QModelIndex,
        modifiers: Qt.KeyboardModifiers = Qt.NoModifier,  # type: ignore
    ) -> None:  # type: ignore
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

    def find_fileitem_by_path(self, path: str) -> list[FileItem]:
        """Find FileItem by path via Application Service."""
        return self.app_service.find_fileitem_by_path(path)  # type: ignore

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

    def set_status(
        self, text: str, color: str = "", auto_reset: bool = False, reset_delay: int = 3000
    ) -> None:
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
        """
        Handle metadata value edited signal from metadata tree view.

        Args:
            key_path: The metadata key path (e.g. "EXIF/Rotation")
            old_value: The previous value
            new_value: The new value
        """
        logger.info(f"[MetadataEdit] Value changed: {key_path} = '{old_value}' -> '{new_value}'")

        # Use specialized metadata status method if status manager is available
        if hasattr(self, "status_manager") and self.status_manager:
            self.status_manager.set_metadata_status(
                f"Modified {key_path}: {old_value} -> {new_value}",
                operation_type="success",
                auto_reset=True,
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
        if hasattr(self, "status_manager") and self.status_manager:
            self.status_manager.set_metadata_status(
                f"Reset {key_path} to original value", operation_type="success", auto_reset=True
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
        if hasattr(self, "status_manager") and self.status_manager:
            self.status_manager.set_file_operation_status(
                f"Copied '{value}' to clipboard", success=True, auto_reset=True
            )

            # Override the reset delay for clipboard operations (shorter feedback)
            if hasattr(self.status_manager, "_status_timer") and self.status_manager._status_timer:
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
        if hasattr(self.window_config_manager, "set_smart_default_geometry"):
            self.window_config_manager.set_smart_default_geometry()  # type: ignore

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
        if hasattr(self, "file_table_view") and self.file_table_view.model():
            # Trigger the original, sophisticated column configuration
            if hasattr(self.file_table_view, "_configure_columns"):
                self.file_table_view._configure_columns()

            # Then trigger column adjustment using the existing logic

            logger.debug(
                "[MainWindow] Used original FileTableView column configuration",
                extra={"dev_only": True},
            )

        # Configure other table views with ColumnManager (they don't have the sophisticated logic)
        # Note: MetadataTreeView handles its own column configuration, so we skip it here

        if hasattr(self, "preview_tables_view") and self.preview_tables_view:
            # Configure preview tables
            if hasattr(self.preview_tables_view, "old_names_table"):
                self.column_manager.configure_table_columns(
                    self.preview_tables_view.old_names_table, "preview_old"
                )
            if hasattr(self.preview_tables_view, "new_names_table"):
                self.column_manager.configure_table_columns(
                    self.preview_tables_view.new_names_table, "preview_new"
                )

    def configure_table_columns(self, table_view, table_type: str) -> None:
        """Configure columns for a specific table view using ColumnManager."""
        self.column_manager.configure_table_columns(table_view, table_type)

    def adjust_columns_for_splitter_change(self, table_view, table_type: str) -> None:
        """Adjust columns when splitter position changes using ColumnManager."""
        self.column_manager.adjust_columns_for_splitter_change(table_view, table_type)

    def reset_column_preferences(self, table_type: str, column_index: int | None = None) -> None:
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
        if not (hasattr(self, "file_table_view") and hasattr(self, "file_model")):
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
        if (
            hasattr(self, "splitter_manager")
            and hasattr(self, "horizontal_splitter")
            and self.isVisible()
            and not self.isMinimized()
        ):
            # Get new window width
            new_width = self.width()

            # Use SplitterManager to update splitter sizes
            from utils.timer_manager import schedule_resize_adjust

            def update_splitters():
                self.splitter_manager.update_splitter_sizes_for_window_width(new_width)

            # Schedule the update to avoid conflicts with other resize operations
            schedule_resize_adjust(update_splitters, 50)

            # Also trigger column adjustment when window resizes
            if hasattr(self, "file_table_view"):

                def trigger_column_adjustment():
                    self.splitter_manager.trigger_column_adjustment_after_splitter_change()

                # Schedule column adjustment after splitter update
                schedule_resize_adjust(trigger_column_adjustment, 60)

    def _handle_window_state_change(self) -> None:
        """Handle maximize/restore geometry and file table refresh."""
        # Handle maximize: store appropriate geometry for restore
        if self.isMaximized() and not hasattr(self, "_restore_geometry"):
            current_geo = self.geometry()
            initial_size = self._initial_geometry.size()

            # Use current geometry if manually resized, otherwise use initial
            is_manually_resized = (
                abs(current_geo.width() - initial_size.width()) > 10
                or abs(current_geo.height() - initial_size.height()) > 10
            )

            self._restore_geometry = current_geo if is_manually_resized else self._initial_geometry
            logger.debug(
                f"[MainWindow] Stored {'manual' if is_manually_resized else 'initial'} geometry for restore"
            )

        # Handle restore: restore stored geometry
        elif not self.isMaximized() and hasattr(self, "_restore_geometry"):
            self.setGeometry(self._restore_geometry)
            delattr(self, "_restore_geometry")
            logger.debug("[MainWindow] Restored geometry")

        # Refresh file table after state change
        self._refresh_file_table_for_window_change()

    def _refresh_file_table_for_window_change(self) -> None:
        """Refresh file table after window state changes."""
        if not hasattr(self, "file_table_view") or not self.file_table_view.model():
            return

        from utils.timer_manager import schedule_resize_adjust

        def refresh():
            # Reset manual column preference for auto-sizing
            if not getattr(self.file_table_view, "_recent_manual_resize", False):
                self.file_table_view._has_manual_preference = False

            # Use existing splitter logic for column sizing
            if hasattr(self, "horizontal_splitter"):
                sizes = self.horizontal_splitter.sizes()
                self.file_table_view.on_horizontal_splitter_moved(sizes[1], 1)

        schedule_resize_adjust(refresh, 25)

    def closeEvent(self, event) -> None:
        """
        Handles application shutdown and cleanup using Shutdown Coordinator.

        Ensures all resources are properly released and threads are stopped.
        """
        # If shutdown is already in progress, ignore additional close events
        if hasattr(self, "_shutdown_in_progress") and self._shutdown_in_progress:
            event.ignore()
            return

        logger.info(
            f"Application shutting down at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}..."
        )

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
                    # Save all modified metadata with exit save flag
                    if hasattr(self, "metadata_manager") and self.metadata_manager:
                        if hasattr(self.metadata_manager, "save_all_modified_metadata"):
                            self.metadata_manager.save_all_modified_metadata(is_exit_save=True)
                            logger.info("[CloseEvent] Saved all metadata changes before closing")
                        else:
                            logger.warning(
                                "[CloseEvent] save_all_modified_metadata method not available"
                            )
                    else:
                        logger.warning("[CloseEvent] MetadataManager not available for saving")
                except Exception as e:
                    logger.error(f"[CloseEvent] Failed to save metadata before closing: {e}")
                    # Show error but continue closing anyway
                    from widgets.custom_message_dialog import CustomMessageDialog

                    CustomMessageDialog.information(
                        self,
                        "Save Error",
                        f"Failed to save metadata changes:\n{e}\n\nClosing anyway.",
                    )
            # If reply == "close_without_saving", we just continue with closing

        # Mark shutdown as in progress
        self._shutdown_in_progress = True

        # Save configuration immediately before shutdown
        try:
            from utils.json_config_manager import get_app_config_manager
            get_app_config_manager().save_immediate()
            logger.info("[CloseEvent] Configuration saved immediately before shutdown")
        except Exception as e:
            logger.error(f"[CloseEvent] Failed to save configuration: {e}")

        # Ignore this close event - we'll handle closing ourselves
        event.ignore()

        # Start coordinated shutdown process
        self._start_coordinated_shutdown()

    def _start_coordinated_shutdown(self):
        """Start the coordinated shutdown process using ShutdownCoordinator."""
        try:
            # Set wait cursor for the entire shutdown process
            QApplication.setOverrideCursor(Qt.WaitCursor)  # type: ignore

            # Create custom shutdown dialog
            from widgets.metadata_waiting_dialog import MetadataWaitingDialog

            class ShutdownDialog(MetadataWaitingDialog):
                """Custom dialog for shutdown that ignores ESC key."""

                def keyPressEvent(self, event):
                    if event.key() == Qt.Key_Escape:  # type: ignore
                        logger.debug("[ShutdownDialog] ESC key ignored during shutdown")
                        QApplication.setOverrideCursor(Qt.WaitCursor)  # type: ignore
                        return
                    super().keyPressEvent(event)

            self.shutdown_dialog = ShutdownDialog(self, is_extended=False)
            self.shutdown_dialog.setWindowTitle("Closing OnCutF...")
            self.shutdown_dialog.set_status("Preparing to close...")

            # Prevent dialog from being closed by user
            self.shutdown_dialog.setWindowFlags(
                self.shutdown_dialog.windowFlags() & ~Qt.WindowCloseButtonHint  # type: ignore
            )

            # Show dialog
            self.shutdown_dialog.show()

            # Position dialog on the same screen as the main window
            from utils.multiscreen_helper import center_dialog_on_parent_screen

            center_dialog_on_parent_screen(self.shutdown_dialog, self)

            # Single processEvents to show dialog, avoid multiple calls during shutdown
            QApplication.processEvents()

            logger.info("[CloseEvent] Shutdown dialog created, starting coordinated shutdown")

            # Define progress callback for shutdown coordinator
            def update_progress(message: str, progress: float):
                """Update shutdown dialog with progress."""
                if hasattr(self, "shutdown_dialog") and self.shutdown_dialog:
                    self.shutdown_dialog.set_status(message)
                    # Convert 0-1 progress to percentage
                    percent = int(progress * 100)
                    if hasattr(self.shutdown_dialog, "set_progress_percentage"):
                        self.shutdown_dialog.set_progress_percentage(percent)
                # Avoid excessive processEvents during shutdown
                # QApplication.processEvents()

            # Perform additional cleanup before coordinator shutdown
            self._pre_coordinator_cleanup()

            # Execute coordinated shutdown
            success = self.shutdown_coordinator.execute_shutdown(
                progress_callback=update_progress, emergency=False
            )

            # Perform final cleanup after coordinator
            self._post_coordinator_cleanup()

            # Log summary
            summary = self.shutdown_coordinator.get_summary()
            logger.info(f"[CloseEvent] Shutdown summary: {summary}")

            # Complete shutdown
            self._complete_shutdown(success)

        except Exception as e:
            logger.error(f"[CloseEvent] Error during coordinated shutdown: {e}", exc_info=True)
            # Fallback to emergency shutdown
            QApplication.restoreOverrideCursor()
            QApplication.quit()

    def _pre_coordinator_cleanup(self):
        """Perform cleanup before coordinator shutdown (UI-specific cleanup)."""
        try:
            # Create database backup
            if hasattr(self, "backup_manager") and self.backup_manager:
                try:
                    self.backup_manager.create_backup(reason="auto")  # type: ignore
                    logger.info("[CloseEvent] Database backup created")
                except Exception as e:
                    logger.warning(f"[CloseEvent] Database backup failed: {e}")

            # Save window configuration
            if hasattr(self, "window_config_manager") and self.window_config_manager:
                try:
                    self.window_config_manager.save_window_config()
                    logger.info("[CloseEvent] Window configuration saved")
                except Exception as e:
                    logger.warning(f"[CloseEvent] Failed to save window config: {e}")

            # Flush batch operations
            if hasattr(self, "batch_manager") and self.batch_manager:
                try:
                    if hasattr(self.batch_manager, "flush_operations"):
                        self.batch_manager.flush_operations()  # type: ignore
                        logger.info("[CloseEvent] Batch operations flushed")
                except Exception as e:
                    logger.warning(f"[CloseEvent] Batch flush failed: {e}")

            # Cleanup drag operations
            if hasattr(self, "drag_manager") and self.drag_manager:
                try:
                    self.drag_manager.force_cleanup()  # type: ignore
                    logger.info("[CloseEvent] Drag manager cleaned up")
                except Exception as e:
                    logger.warning(f"[CloseEvent] Drag cleanup failed: {e}")

            # Close dialogs
            if hasattr(self, "dialog_manager") and self.dialog_manager:
                try:
                    self.dialog_manager.cleanup()  # type: ignore
                    logger.info("[CloseEvent] All dialogs closed")
                except Exception as e:
                    logger.warning(f"[CloseEvent] Dialog cleanup failed: {e}")

            # Stop metadata operations
            if hasattr(self, "metadata_thread") and self.metadata_thread:
                try:
                    self.metadata_thread.quit()
                    if not self.metadata_thread.wait(2000):  # Wait max 2 seconds
                        logger.warning("[CloseEvent] Metadata thread did not stop, terminating...")
                        self.metadata_thread.terminate()
                        self.metadata_thread.wait(500)  # Wait another 500ms for termination
                    logger.info("[CloseEvent] Metadata thread stopped")
                except Exception as e:
                    logger.warning(f"[CloseEvent] Metadata thread cleanup failed: {e}")

        except Exception as e:
            logger.error(f"[CloseEvent] Error in pre-coordinator cleanup: {e}")

    def _post_coordinator_cleanup(self):
        """Perform final cleanup after coordinator shutdown."""
        try:
            # Clean up Qt resources
            if hasattr(self, "file_table_view") and self.file_table_view:
                self.file_table_view.clearSelection()
                self.file_table_view.setModel(None)

            # Additional cleanup
            from core.application_context import ApplicationContext

            context = ApplicationContext.get_instance()
            if context:
                context.cleanup()  # type: ignore
                logger.info("[CloseEvent] Application context cleaned up")

        except Exception as e:
            logger.error(f"[CloseEvent] Error in post-coordinator cleanup: {e}")

    def _complete_shutdown(self, success: bool = True):
        """Complete the shutdown process."""
        try:
            # Close shutdown dialog
            if hasattr(self, "shutdown_dialog") and self.shutdown_dialog:
                self.shutdown_dialog.close()

            # Restore cursor
            QApplication.restoreOverrideCursor()

            # Log completion
            status = "successfully" if success else "with errors"
            logger.info(f"[CloseEvent] Shutdown completed {status}")

            # Quit application (with guard against multiple calls)
            try:
                QApplication.quit()
            except RuntimeError as e:
                logger.debug(f"[CloseEvent] QApplication.quit() error (expected): {e}")

        except Exception as e:
            logger.error(f"[CloseEvent] Error completing shutdown: {e}")
            import contextlib
            with contextlib.suppress(RuntimeError):
                QApplication.quit()

    def _check_for_unsaved_changes(self) -> bool:
        """
        Check if there are any unsaved metadata changes.

        Returns:
            bool: True if there are unsaved changes, False otherwise
        """
        if not hasattr(self, "metadata_tree_view"):
            return False

        try:
            # Force save current file modifications to per-file storage first
            if (
                hasattr(self.metadata_tree_view, "_current_file_path")
                and self.metadata_tree_view._current_file_path
            ):
                if self.metadata_tree_view.modified_items:
                    self.metadata_tree_view._set_in_path_dict(
                        self.metadata_tree_view._current_file_path,
                        self.metadata_tree_view.modified_items.copy(),
                        self.metadata_tree_view.modified_items_per_file,
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

    def _force_cleanup_background_workers(self) -> None:
        """Force cleanup of any background workers/threads."""
        logger.info("[CloseEvent] Cleaning up background workers...")

        # 1. Cleanup HashWorker if it exists
        if hasattr(self, "event_handler_manager") and hasattr(
            self.event_handler_manager, "hash_worker"
        ):
            hash_worker = self.event_handler_manager.hash_worker
            if hash_worker and hash_worker.isRunning():
                logger.info("[CloseEvent] Cancelling and terminating HashWorker...")
                hash_worker.cancel()
                if not hash_worker.wait(1000):  # Wait max 1 second
                    logger.warning(
                        "[CloseEvent] HashWorker did not stop gracefully, terminating..."
                    )
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
                    logger.warning(
                        f"[CloseEvent] Thread {thread.__class__.__name__} did not quit gracefully, terminating..."
                    )
                    thread.terminate()
                    if not thread.wait(500):  # CRITICAL: Add timeout to prevent infinite hang
                        logger.error(
                            f"[CloseEvent] Thread {thread.__class__.__name__} did not terminate after 500ms"
                        )

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
            if dialog.isVisible() and dialog != getattr(self, "shutdown_dialog", None):
                logger.info("[CloseEvent] Force closing MetadataWaitingDialog")
                dialog.reject()  # Force close without waiting
                dialogs_closed += 1

        if dialogs_closed > 0:
            logger.info(
                f"[CloseEvent] Force closed {dialogs_closed} progress dialogs (excluding shutdown dialog)"
            )

    def refresh_metadata_widgets(self):
        """Refresh all active MetadataWidget instances and trigger preview update."""
        logger.debug(
            "[MainWindow] refresh_metadata_widgets CALLED (hash_worker signal or selection)"
        )
        try:
            from widgets.metadata_widget import MetadataWidget

            for module_widget in self.rename_modules_area.module_widgets:
                if hasattr(module_widget, "current_module_widget"):
                    widget = module_widget.current_module_widget
                    if isinstance(widget, MetadataWidget):
                        widget.trigger_update_options()
                        widget.emit_if_changed()
            # Force preview update after metadata widget changes using UnifiedRenameEngine
            self._trigger_unified_preview_update()
        except Exception:
            pass

    def _trigger_unified_preview_update(self):
        """Trigger preview update using UnifiedRenameEngine ONLY."""
        try:
            if hasattr(self, "unified_rename_engine") and self.unified_rename_engine:
                # Clear cache to force fresh preview
                self.unified_rename_engine.clear_cache()
                logger.debug("[MainWindow] Unified preview update triggered")
            else:
                logger.warning("[MainWindow] UnifiedRenameEngine not available")
        except Exception as e:
            logger.error(f"[MainWindow] Error in unified preview update: {e}")

    def update_active_metadata_widget_options(self):
        """Find the active MetadataWidget and call trigger_update_options and emit_if_changed (for selection change)."""
        try:
            from widgets.metadata_widget import MetadataWidget

            for module_widget in self.rename_modules_area.module_widgets:
                if hasattr(module_widget, "current_module_widget"):
                    widget = module_widget.current_module_widget
                    if isinstance(widget, MetadataWidget):
                        widget.trigger_update_options()
                        widget.emit_if_changed()
        except Exception as e:
            logger.warning(f"[MainWindow] Error updating metadata widget: {e}")

    def _register_managers_in_context(self):
        """
        Register all managers in ApplicationContext for centralized access.

        This eliminates the need for parent_window.some_manager traversal patterns.
        Components can access managers via context.get_manager('name') instead.

        Phase 2 of Application Context Migration.
        """
        try:
            # Core managers
            self.context.register_manager("table", self.table_manager)
            self.context.register_manager("metadata", self.metadata_manager)
            self.context.register_manager("selection", self.selection_manager)
            self.context.register_manager("rename", self.rename_manager)
            self.context.register_manager("preview", self.preview_manager)

            # UI managers
            self.context.register_manager("ui", self.ui_manager)
            self.context.register_manager("dialog", self.dialog_manager)
            self.context.register_manager("status", self.status_manager)
            self.context.register_manager("shortcut", self.shortcut_manager)
            self.context.register_manager("splitter", self.splitter_manager)
            self.context.register_manager("window_config", self.window_config_manager)
            self.context.register_manager("column", self.column_manager)

            # File operations managers
            self.context.register_manager("file_load", self.file_load_manager)
            self.context.register_manager("file_operations", self.file_operations_manager)
            self.context.register_manager("file_validation", self.file_validation_manager)

            # System managers
            self.context.register_manager("db", self.db_manager)
            self.context.register_manager("backup", self.backup_manager)
            self.context.register_manager("rename_history", self.rename_history_manager)

            # Utility managers
            self.context.register_manager("utility", self.utility_manager)
            self.context.register_manager("event_handler", self.event_handler_manager)
            self.context.register_manager("drag", self.drag_manager)
            self.context.register_manager("drag_cleanup", self.drag_cleanup_manager)
            self.context.register_manager("initialization", self.initialization_manager)

            # Service layer
            self.context.register_manager("app_service", self.app_service)
            self.context.register_manager("batch", self.batch_manager)
            self.context.register_manager("config", self.config_manager)

            # Coordinators
            self.context.register_manager("signal_coordinator", self.signal_coordinator)

            # Engines
            self.context.register_manager("rename_engine", self.unified_rename_engine)

            logger.info(
                f"[MainWindow] Registered {len(self.context.list_managers())} managers in ApplicationContext",
                extra={"dev_only": True},
            )
            logger.debug(
                f"[MainWindow] Available managers: {', '.join(self.context.list_managers())}",
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.error(f"[MainWindow] Error registering managers in context: {e}")

    def _register_shutdown_components(self):
        """Register all concurrent components with shutdown coordinator."""
        try:
            # Register timer manager
            from utils.timer_manager import get_timer_manager

            timer_mgr = get_timer_manager()
            self.shutdown_coordinator.register_timer_manager(timer_mgr)

            # Register thread pool manager (if exists)
            try:
                from core.thread_pool_manager import get_thread_pool_manager

                thread_pool_mgr = get_thread_pool_manager()
                self.shutdown_coordinator.register_thread_pool_manager(thread_pool_mgr)
            except Exception as e:
                logger.debug(f"[MainWindow] Thread pool manager not available: {e}")

            # Register database manager
            if hasattr(self, "db_manager") and self.db_manager:
                self.shutdown_coordinator.register_database_manager(self.db_manager)

            # Register ExifTool wrapper (get active instance if any)
            try:
                from utils.exiftool_wrapper import ExifToolWrapper

                # Get any active instance
                if ExifToolWrapper._instances:  # type: ignore
                    exiftool = next(iter(ExifToolWrapper._instances))  # type: ignore
                    self.shutdown_coordinator.register_exiftool_wrapper(exiftool)
            except Exception as e:
                logger.debug(f"[MainWindow] ExifTool wrapper not available: {e}")

            logger.info("[MainWindow] Shutdown components registered successfully")

        except Exception as e:
            logger.error(f"[MainWindow] Error registering shutdown components: {e}")
