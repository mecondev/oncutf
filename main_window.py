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
from core.initialization_manager import InitializationManager
from core.preview_manager import PreviewManager

# Import all PyQt5 classes from centralized module
from core.qt_imports import *
from core.rename_manager import RenameManager
from core.shortcut_manager import ShortcutManager
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
        self.table_manager = TableManager(self)
        self.utility_manager = UtilityManager(self)
        self.rename_manager = RenameManager(self)
        self.drag_cleanup_manager = DragCleanupManager(self)
        self.shortcut_manager = ShortcutManager(self)
        self.initialization_manager = InitializationManager(self)

        # --- Initialize UIManager and setup all UI ---
        self.ui_manager = UIManager(parent_window=self)
        self.ui_manager.setup_all_ui()

        # --- Initialize JSON Config Manager ---
        self.config_manager = get_app_config_manager()

        # --- Load and apply window configuration ---
        self._load_window_config()

        # Store initial geometry AFTER smart sizing for proper restore behavior
        self._initial_geometry = self.geometry()

        # --- Apply UI configuration after UI is initialized ---
        self._apply_loaded_config()

        # --- Ensure column widths are properly initialized ---
        # This handles cases where no config exists (fresh start) or when config is deleted
        from utils.timer_manager import schedule_resize_adjust
        schedule_resize_adjust(self._ensure_initial_column_sizing, 50)

        # --- Preview update debouncing timer ---
        self.preview_update_timer = QTimer(self)
        self.preview_update_timer.setSingleShot(True)
        self.preview_update_timer.setInterval(100)  # milliseconds
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
        # Use the remembered recursive state for consistent behavior
        recursive = getattr(self, 'current_folder_is_recursive', False)
        logger.info(f"[MainWindow] load_files_from_folder: {folder_path} (recursive={recursive}, remembered from previous load)")
        self.file_load_manager.load_folder(folder_path, merge_mode=False, recursive=recursive)

    def shortcut_load_metadata(self) -> None:
        """Delegates to MetadataManager for shortcut-based metadata loading."""
        self.metadata_manager.shortcut_load_metadata()

    def shortcut_load_extended_metadata(self) -> None:
        """Delegates to MetadataManager for extended metadata shortcut loading."""
        self.metadata_manager.shortcut_load_extended_metadata()

    def shortcut_save_selected_metadata(self) -> None:
        """Delegates to MetadataManager for saving metadata of selected files."""
        self.metadata_manager.save_metadata_for_selected()

    def shortcut_save_all_metadata(self) -> None:
        """Delegates to MetadataManager for saving all modified metadata."""
        self.metadata_manager.save_all_modified_metadata()

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



    def get_selected_rows_files(self) -> list:
        """Delegates to UtilityManager for getting selected rows as files."""
        return self.utility_manager.get_selected_rows_files()

    def find_fileitem_by_path(self, path: str) -> Optional[FileItem]:
        """Delegates to FileOperationsManager for finding FileItem by path."""
        return self.file_operations_manager.find_fileitem_by_path(self.file_model.files, path)

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

    def changeEvent(self, event) -> None:
        """Handle window state changes (maximize, minimize, restore)."""
        super().changeEvent(event)

        if event.type() == QEvent.WindowStateChange:  # type: ignore
            self._handle_window_state_change()

    def resizeEvent(self, event) -> None:
        """Handle window resize events to update splitter ratios for wide screens."""
        super().resizeEvent(event)

        # Only update splitters if UI is fully initialized and window is visible
        if (hasattr(self, 'ui_manager') and
            hasattr(self, 'horizontal_splitter') and
            self.isVisible() and
            not self.isMinimized()):

            # Get new window width
            new_width = self.width()

            # Calculate new optimal splitter sizes
            optimal_sizes = self.ui_manager._calculate_optimal_splitter_sizes(new_width)

            # Only update if the sizes would be significantly different
            current_sizes = self.horizontal_splitter.sizes()
            if len(current_sizes) == 3 and len(optimal_sizes) == 3:
                # Check if any panel size differs by more than 50px
                size_differences = [abs(current - optimal) for current, optimal in zip(current_sizes, optimal_sizes)]
                if any(diff > 50 for diff in size_differences):
                    # Update splitter sizes with smooth transition
                    from utils.timer_manager import schedule_resize_adjust

                    def update_splitters():
                        self.horizontal_splitter.setSizes(optimal_sizes)
                        logger.debug(f"[ResizeEvent] Updated splitter sizes for {new_width}px: {optimal_sizes}")

                    # Schedule the update to avoid conflicts with other resize operations
                    schedule_resize_adjust(update_splitters, 50)

            # Also trigger column adjustment when window resizes
            if hasattr(self, 'file_table_view'):
                from utils.timer_manager import schedule_resize_adjust

                def trigger_column_adjustment():
                    if hasattr(self.file_table_view, '_trigger_column_adjustment'):
                        self.file_table_view._trigger_column_adjustment()

                # Schedule column adjustment after splitter update (reduced delay for smoother response)
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
        Handles application shutdown and cleanup.

        Ensures all resources are properly released and threads are stopped.
        """
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
                    if hasattr(self, 'metadata_manager'):
                        self.metadata_manager.save_all_modified_metadata()
                        logger.info("[CloseEvent] Saved all metadata changes before closing")
                    else:
                        logger.warning("[CloseEvent] MetadataManager not available for saving")
                except Exception as e:
                    logger.error(f"[CloseEvent] Failed to save metadata before closing: {e}")
                    # Show error but continue closing anyway
                    from widgets.custom_msgdialog import CustomMessageDialog
                    CustomMessageDialog.information(
                        self,
                        "Save Error",
                        f"Failed to save metadata changes:\n{e}\n\nClosing anyway."
                    )
            # If reply == "close_without_saving", we just continue with closing

        # 1. Create database backup before cleanup
        if hasattr(self, 'backup_manager'):
            try:
                backup_path = self.backup_manager.backup_on_shutdown()
                if backup_path:
                    logger.info(f"[CloseEvent] Database backup created: {backup_path}")
                else:
                    logger.warning("[CloseEvent] Failed to create database backup")
            except Exception as e:
                logger.error(f"[CloseEvent] Error creating database backup: {e}")

        # 2. Save window configuration before cleanup
        self._save_window_config()

        # 3. Clean up any active drag operations
        self.drag_cleanup_manager.emergency_drag_cleanup()

        # 4. Clean up any open dialogs
        if hasattr(self, 'dialog_manager'):
            self.dialog_manager.cleanup()

        # 5. Force cleanup any background workers/threads
        self._force_cleanup_background_workers()

        # 6. Clean up application context
        if hasattr(self, 'context'):
            try:
                self.context.cleanup()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error cleaning application context: {e}")

        # 7. Force close any active progress dialogs first
        self._force_close_progress_dialogs()

        # 8. Stop any running timers
        # First stop TimerManager timers (which include scheduled operations)
        try:
            from utils.timer_manager import cleanup_all_timers
            cleaned_timers = cleanup_all_timers()
            if cleaned_timers > 0:
                logger.info(f"[CloseEvent] Cleaned up {cleaned_timers} scheduled timers")
        except Exception as e:
            logger.warning(f"[CloseEvent] Error cleaning TimerManager: {e}")

        # Then find and stop any remaining QTimer instances
        try:
            from PyQt5.QtCore import QTimer
            remaining_timers = self.findChildren(QTimer)
            for timer in remaining_timers:
                if timer.isActive():
                    timer.stop()
                    logger.debug(f"[CloseEvent] Stopped QTimer: {timer.objectName() or 'unnamed'}")

            if remaining_timers:
                logger.info(f"[CloseEvent] Stopped {len(remaining_timers)} QTimer instances")
        except Exception as e:
            logger.warning(f"[CloseEvent] Error stopping QTimer instances: {e}")

        # 9. Clean up any remaining Qt resources
        try:
            QApplication.processEvents()
        except Exception as e:
            logger.warning(f"[CloseEvent] Error processing events during cleanup: {e}")

        # 10. Call parent closeEvent
        try:
            super().closeEvent(event)
        except Exception as e:
            logger.warning(f"[CloseEvent] Error in parent closeEvent: {e}")

        # 11. Close database connections before final cleanup
        if hasattr(self, 'db_manager'):
            try:
                self.db_manager.close()
                logger.info("[CloseEvent] Database connections closed")
            except Exception as e:
                logger.warning(f"[CloseEvent] Error closing database: {e}")

        # Clean up backup manager
        if hasattr(self, 'backup_manager'):
            try:
                from core.backup_manager import cleanup_backup_manager
                cleanup_backup_manager()
                logger.info("[CloseEvent] Backup manager cleaned up")
            except Exception as e:
                logger.warning(f"[CloseEvent] Error cleaning backup manager: {e}")

        # 12. Final cleanup - force terminate any remaining background processes
        logger.info("[CloseEvent] Final cleanup - forcing application termination")

        # Force quit the application immediately
        QApplication.quit()

        # Don't schedule any more timers after QApplication.quit()
        # The application should exit gracefully at this point

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

        # 3. Clean up metadata manager operations and ExifTool
        if hasattr(self, 'metadata_manager'):
            try:
                # Force stop any ongoing metadata operations
                if hasattr(self.metadata_manager, '_running_operations'):
                    self.metadata_manager._running_operations = False

                # Close ExifTool wrapper if it exists
                if hasattr(self.metadata_manager, '_exiftool_wrapper') and self.metadata_manager._exiftool_wrapper:
                    logger.info("[CloseEvent] Closing ExifTool wrapper...")
                    self.metadata_manager._exiftool_wrapper.close()
                    logger.info("[CloseEvent] ExifTool wrapper closed")

                # Also close metadata loader ExifTool if it exists
                if hasattr(self.metadata_manager, 'metadata_loader') and self.metadata_manager.metadata_loader:
                    if hasattr(self.metadata_manager.metadata_loader, 'exiftool'):
                        logger.info("[CloseEvent] Closing metadata loader ExifTool...")
                        self.metadata_manager.metadata_loader.close()
                        logger.info("[CloseEvent] Metadata loader ExifTool closed")

                # Force cleanup any remaining ExifTool processes
                logger.info("[CloseEvent] Force cleaning up any remaining ExifTool processes...")
                from utils.exiftool_wrapper import ExifToolWrapper
                ExifToolWrapper.force_cleanup_all_exiftool_processes()

                logger.debug("[CloseEvent] Cleaned up metadata manager")
            except Exception as e:
                logger.warning(f"[CloseEvent] Error cleaning metadata manager: {e}")

    def _force_close_progress_dialogs(self) -> None:
        """Force close any active progress dialogs."""
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

        # Close MetadataWaitingDialog instances
        metadata_dialogs = self.findChildren(MetadataWaitingDialog)
        for dialog in metadata_dialogs:
            if dialog.isVisible():
                logger.info("[CloseEvent] Force closing MetadataWaitingDialog")
                dialog.reject()  # Force close without waiting
                dialogs_closed += 1

        if dialogs_closed > 0:
            logger.info(f"[CloseEvent] Force closed {dialogs_closed} progress dialogs")

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

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """Delegates to FileLoadManager for folder load preparation."""
        return self.file_load_manager.prepare_folder_load(folder_path, clear=clear)

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
        """Delegates to FileLoadManager for loading files from paths."""
        self.file_load_manager.load_files_from_paths(file_paths, clear=clear)

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
        """Delegates to MetadataManager for intelligent metadata loading with cache checking."""
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

        # Update status to show the change
        self.set_status(f"Modified {key_path}: {old_value} → {new_value}", color=STATUS_COLORS["action_completed"], auto_reset=True)

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

        # Update status to show the reset
        self.set_status(f"Reset {key_path} to original value", color=STATUS_COLORS["alert_notice"], auto_reset=True)

        # The file icon status update is already handled by MetadataTreeView._update_file_icon_status()
        logger.debug(f"[MetadataEdit] Reset metadata field: {key_path}")

    def on_metadata_value_copied(self, value: str) -> None:
        """
        Handle metadata value copied signal from metadata tree view.

        Args:
            value: The value that was copied to clipboard
        """
        logger.debug(f"[MetadataEdit] Value copied to clipboard: {value}")

        # Show a brief status message
        self.set_status(f"Copied '{value}' to clipboard", color=STATUS_COLORS["operation_success"], auto_reset=True, reset_delay=2000)

    # =====================================
    # Window Configuration Management
    # =====================================

    def _load_window_config(self) -> None:
        """Load and apply window configuration from config manager."""
        try:
            window_config = self.config_manager.get_category('window')

            # Load geometry
            geometry = window_config.get('geometry')
            logger.debug(f"[Config] Loaded geometry from config: {geometry}", extra={"dev_only": True})

            if geometry:
                self.setGeometry(
                    geometry['x'], geometry['y'],
                    geometry['width'], geometry['height']
                )
                logger.info(f"[Config] Applied saved window geometry: {geometry}")
            else:
                # No saved geometry - set smart defaults based on screen size
                logger.info("[Config] No saved geometry found, applying smart defaults")
                self._set_smart_default_geometry()

            # Load window state
            window_state = window_config.get('window_state', 'normal')
            if window_state == 'maximized':
                self.showMaximized()
            elif window_state == 'minimized':
                self.showMinimized()
            else:
                self.showNormal()

            # Store last folder and other settings for later use
            self._last_folder_from_config = window_config.get('last_folder', '')
            self._recursive_mode_from_config = window_config.get('recursive_mode', False)
            self._sort_column_from_config = window_config.get('sort_column', 1)
            self._sort_order_from_config = window_config.get('sort_order', 0)

            logger.info("[Config] Window configuration loaded successfully", extra={"dev_only": True})

        except Exception as e:
            logger.error(f"[Config] Failed to load window configuration: {e}")
            # If config loading fails, still set smart defaults
            logger.info("[Config] Exception occurred, applying smart defaults as fallback")
            self._set_smart_default_geometry()

    def _set_smart_default_geometry(self) -> None:
        """Set smart default window geometry based on screen size and aspect ratio."""
        try:
            # Use modern QScreen API instead of deprecated QDesktopWidget
            app = QApplication.instance()
            if not app:
                raise RuntimeError("No QApplication instance found")

            # Get the primary screen using modern API
            primary_screen = app.primaryScreen() # type: ignore[attr-defined]
            if not primary_screen:
                raise RuntimeError("No primary screen found")

            # Get screen geometry (available area excluding taskbars, docks, etc.)
            screen_geometry = primary_screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            screen_aspect = screen_width / screen_height if screen_height > 0 else 1.0

            logger.info(f"[Config] Primary screen detected: {screen_width}x{screen_height} (aspect: {screen_aspect:.2f})")
            logger.info(f"[Config] Screen name: {primary_screen.name()}, DPI: {primary_screen.logicalDotsPerInch():.1f}")

            # Log all available screens for debugging multi-monitor setups
            all_screens = app.screens() # type: ignore[attr-defined]
            if len(all_screens) > 1:
                total_width = sum(screen.geometry().width() for screen in all_screens)
                total_height = max(screen.geometry().height() for screen in all_screens)
                logger.info(f"[Config] Multi-monitor setup detected: {len(all_screens)} screens, total desktop: {total_width}x{total_height}")
                for i, screen in enumerate(all_screens):
                    geo = screen.geometry()
                    logger.debug(f"[Config] Screen {i}: {screen.name()} - {geo.width()}x{geo.height()} at ({geo.x()}, {geo.y()})")

            # Import screen size configuration from config
            from core.config_imports import (
                DEV_SIMULATE_SCREEN,
                DEV_SIMULATED_SCREEN,
                SCREEN_SIZE_BREAKPOINTS,
                SCREEN_SIZE_PERCENTAGES,
                WINDOW_MIN_SMART_WIDTH,
                WINDOW_MIN_SMART_HEIGHT,
                LARGE_SCREEN_MIN_WIDTH,
                LARGE_SCREEN_MIN_HEIGHT
            )

            # Check if we should simulate a different screen size (DEV ONLY)
            if DEV_SIMULATE_SCREEN:
                screen_width = DEV_SIMULATED_SCREEN["width"]
                screen_height = DEV_SIMULATED_SCREEN["height"]
                screen_name = DEV_SIMULATED_SCREEN["name"]
                logger.warning(f"[Config] 🚧 DEV MODE: Simulating screen: {screen_name} - {screen_width}x{screen_height}")
                # Override the real screen values for testing
                screen_geometry = type('MockGeometry', (), {
                    'x': lambda: 0,
                    'y': lambda: 0,
                    'width': lambda: screen_width,
                    'height': lambda: screen_height
                })()

            # Calculate smart window dimensions based on primary screen size using configurable breakpoints
            if screen_width >= SCREEN_SIZE_BREAKPOINTS["large_4k"]:  # 4K or large single screen
                # Large screens: use configurable percentages, with configurable minimum
                percentages = SCREEN_SIZE_PERCENTAGES["large_4k"]
                window_width = max(int(screen_width * percentages["width"]), LARGE_SCREEN_MIN_WIDTH)
                window_height = max(int(screen_height * percentages["height"]), LARGE_SCREEN_MIN_HEIGHT)
                logger.info(f"[Config] Large screen detected (>={SCREEN_SIZE_BREAKPOINTS['large_4k']}px), using {percentages['width']*100}%x{percentages['height']*100}%: {window_width}x{window_height}")
            elif screen_width >= SCREEN_SIZE_BREAKPOINTS["full_hd"]:  # Full HD single screen
                # Standard large screens: use configurable percentages
                percentages = SCREEN_SIZE_PERCENTAGES["full_hd"]
                window_width = int(screen_width * percentages["width"])
                window_height = int(screen_height * percentages["height"])
                logger.info(f"[Config] Full HD screen detected (>={SCREEN_SIZE_BREAKPOINTS['full_hd']}px), using {percentages['width']*100}%x{percentages['height']*100}%: {window_width}x{window_height}")
            elif screen_width >= SCREEN_SIZE_BREAKPOINTS["laptop"]:  # Common laptop resolution
                # Medium screens: use configurable percentages
                percentages = SCREEN_SIZE_PERCENTAGES["laptop"]
                window_width = int(screen_width * percentages["width"])
                window_height = int(screen_height * percentages["height"])
                logger.info(f"[Config] Medium screen detected (>={SCREEN_SIZE_BREAKPOINTS['laptop']}px), using {percentages['width']*100}%x{percentages['height']*100}%: {window_width}x{window_height}")
            else:  # Small screens (below laptop breakpoint)
                # Small screens: use configurable percentages, but ensure minimum usability
                percentages = SCREEN_SIZE_PERCENTAGES["small"]
                window_width = max(int(screen_width * percentages["width"]), WINDOW_MIN_SMART_WIDTH)
                window_height = max(int(screen_height * percentages["height"]), WINDOW_MIN_SMART_HEIGHT)
                logger.info(f"[Config] Small screen detected (<{SCREEN_SIZE_BREAKPOINTS['laptop']}px), using {percentages['width']*100}%x{percentages['height']*100}%: {window_width}x{window_height}")

            # Ensure minimum dimensions for usability
            original_width, original_height = window_width, window_height
            window_width = max(window_width, WINDOW_MIN_SMART_WIDTH)
            window_height = max(window_height, WINDOW_MIN_SMART_HEIGHT)
            if window_width != original_width or window_height != original_height:
                logger.info(f"[Config] Applied minimum constraints: {original_width}x{original_height} -> {window_width}x{window_height}")

            # Ensure window doesn't exceed primary screen bounds
            original_width, original_height = window_width, window_height
            window_width = min(window_width, screen_width - 100)
            window_height = min(window_height, screen_height - 100)
            if window_width != original_width or window_height != original_height:
                logger.info(f"[Config] Applied screen bounds: {original_width}x{original_height} -> {window_width}x{window_height}")

            # Calculate centered position on primary screen
            x = screen_geometry.x() + (screen_width - window_width) // 2
            y = screen_geometry.y() + (screen_height - window_height) // 2

            # Apply the geometry
            logger.info(f"[Config] Setting geometry: {window_width}x{window_height} at ({x}, {y}) on primary screen")
            self.setGeometry(x, y, window_width, window_height)

            # Verify what was actually set (some window managers might override)
            actual_geo = self.geometry()
            if actual_geo.width() != window_width or actual_geo.height() != window_height or actual_geo.x() != x or actual_geo.y() != y:
                logger.warning(f"[Config] Window manager overrode geometry! Requested: {window_width}x{window_height} at ({x}, {y}), Got: {actual_geo.width()}x{actual_geo.height()} at ({actual_geo.x()}, {actual_geo.y()})")
            else:
                logger.info(f"[Config] Geometry set successfully: {window_width}x{window_height} at ({x}, {y})")

        except Exception as e:
            logger.error(f"[Config] Failed to set smart default geometry: {e}")
            # Ultimate fallback - fixed reasonable size
            self.setGeometry(100, 100, 1200, 800)
            logger.info("[Config] Used fallback geometry: 1200x800 at (100, 100)")

    def _save_window_config(self) -> None:
        """Save current window state to config manager."""
        try:
            window_config = self.config_manager.get_category('window')

            # Save geometry (use normal geometry if maximized)
            if self.isMaximized():
                # Use stored restore geometry if available, otherwise use initial
                if hasattr(self, '_restore_geometry'):
                    geo = self._restore_geometry
                else:
                    geo = self._initial_geometry
            else:
                geo = self.geometry()

            window_config.set('geometry', {
                'x': geo.x(),
                'y': geo.y(),
                'width': geo.width(),
                'height': geo.height()
            })

            # Save window state
            if self.isMaximized():
                window_state = 'maximized'
            elif self.isMinimized():
                window_state = 'minimized'
            else:
                window_state = 'normal'
            window_config.set('window_state', window_state)

            # Save splitter states
            splitter_states = {}
            if hasattr(self, 'horizontal_splitter'):
                splitter_states['horizontal'] = self.horizontal_splitter.sizes()
            if hasattr(self, 'vertical_splitter'):
                splitter_states['vertical'] = self.vertical_splitter.sizes()
            window_config.set('splitter_states', splitter_states)

            # Save column widths
            column_widths = {}
            if hasattr(self, 'file_table_view') and self.file_table_view.model():
                header = self.file_table_view.horizontalHeader()
                file_table_widths = []
                for i in range(header.count()):
                    file_table_widths.append(header.sectionSize(i))
                column_widths['file_table'] = file_table_widths

            if hasattr(self, 'metadata_tree_view'):
                header = self.metadata_tree_view.header()
                metadata_tree_widths = []
                for i in range(header.count()):
                    metadata_tree_widths.append(header.sectionSize(i))
                column_widths['metadata_tree'] = metadata_tree_widths

            window_config.set('column_widths', column_widths)

            # Save current folder and settings
            if hasattr(self, 'current_folder_path') and self.current_folder_path:
                window_config.set('last_folder', self.current_folder_path)
                app_config = self.config_manager.get_category('app')
                app_config.add_recent_folder(self.current_folder_path)

            if hasattr(self, 'current_folder_is_recursive'):
                window_config.set('recursive_mode', self.current_folder_is_recursive)

            if hasattr(self, 'current_sort_column'):
                window_config.set('sort_column', self.current_sort_column)

            if hasattr(self, 'current_sort_order'):
                window_config.set('sort_order', int(self.current_sort_order))

            # Save configuration to file
            self.config_manager.save()

            logger.info("[Config] Window configuration saved successfully", extra={"dev_only": True})

        except Exception as e:
            logger.error(f"[Preferences] Failed to save window preferences: {e}")

    def _apply_loaded_config(self) -> None:
        """Apply loaded configuration after UI is fully initialized."""
        try:
            window_config = self.config_manager.get_category('window')

            # Apply splitter states
            splitter_states = window_config.get('splitter_states', {})
            if 'horizontal' in splitter_states and hasattr(self, 'horizontal_splitter'):
                self.horizontal_splitter.setSizes(splitter_states['horizontal'])
                logger.debug(f"[Config] Applied horizontal splitter: {splitter_states['horizontal']}", extra={"dev_only": True})

            if 'vertical' in splitter_states and hasattr(self, 'vertical_splitter'):
                self.vertical_splitter.setSizes(splitter_states['vertical'])
                logger.debug(f"[Config] Applied vertical splitter: {splitter_states['vertical']}", extra={"dev_only": True})

            # Apply column widths
            column_widths = window_config.get('column_widths', {})
            if 'file_table' in column_widths and hasattr(self, 'file_table_view'):
                widths = column_widths['file_table']
                header = self.file_table_view.horizontalHeader()
                for i, width in enumerate(widths):
                    if i < header.count():
                        header.resizeSection(i, width)
                logger.debug(f"[Config] Applied file table column widths: {widths}", extra={"dev_only": True})

            if 'metadata_tree' in column_widths and hasattr(self, 'metadata_tree_view'):
                widths = column_widths['metadata_tree']
                header = self.metadata_tree_view.header()
                for i, width in enumerate(widths):
                    if i < header.count():
                        header.resizeSection(i, width)
                logger.debug(f"[Config] Applied metadata tree column widths: {widths}", extra={"dev_only": True})

            logger.info("[Config] UI configuration applied successfully", extra={"dev_only": True})

        except Exception as e:
            logger.error(f"[Config] Failed to apply UI configuration: {e}")

    def _ensure_initial_column_sizing(self) -> None:
        """Ensure column widths are properly sized on startup, especially when no config exists."""
        if hasattr(self, 'file_table_view') and self.file_table_view.model():
            # Trigger column adjustment using the existing logic
            self.file_table_view._trigger_column_adjustment()
            logger.debug("[Config] Ensured initial column sizing", extra={"dev_only": True})

    def restore_last_folder_if_available(self) -> None:
        """Restore the last folder if available and user wants it."""
        if hasattr(self, '_last_folder_from_config') and self._last_folder_from_config:
            last_folder = self._last_folder_from_config
            if os.path.exists(last_folder):
                logger.info(f"[Config] Restoring last folder: {last_folder}")
                # Use the file load manager to load the folder
                recursive = getattr(self, '_recursive_mode_from_config', False)
                self.file_load_manager.load_folder(last_folder, merge=False, recursive=recursive)

                # Apply sort configuration after loading
                if hasattr(self, '_sort_column_from_config') and hasattr(self, '_sort_order_from_config'):
                    sort_order = Qt.AscendingOrder if self._sort_order_from_config == 0 else Qt.DescendingOrder
                    self.sort_by_column(self._sort_column_from_config, sort_order)
            else:
                logger.warning(f"[Config] Last folder no longer exists: {last_folder}")
