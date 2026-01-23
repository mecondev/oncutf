"""Module: config_column_handler.py.

Author: Michael Economou
Date: 2026-01-01

Handler for configuration and column management in MainWindow.
Manages column sizing, state persistence, and manager registration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.ui.main_window import MainWindow

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ConfigColumnHandler:
    """Handles configuration and column management operations."""

    def __init__(self, main_window: MainWindow) -> None:
        """Initialize handler with MainWindow reference."""
        self.main_window = main_window
        logger.debug("[ConfigColumnHandler] Initialized")

    # ========================================================================
    # Column Delegates
    # ========================================================================

    def configure_table_columns(self, table_view, table_type: str) -> None:
        """Configure columns for a specific table view using ColumnManager."""
        self.main_window.column_manager.configure_table_columns(table_view, table_type)

    def adjust_columns_for_splitter_change(self, table_view, table_type: str) -> None:
        """Adjust columns when splitter position changes using ColumnManager."""
        self.main_window.column_manager.adjust_columns_for_splitter_change(table_view, table_type)

    def reset_column_preferences(self, table_type: str, column_index: int | None = None) -> None:
        """Reset user preferences for columns to allow auto-sizing."""
        self.main_window.column_manager.reset_user_preferences(table_type, column_index)

    def save_column_state(self, table_type: str) -> dict:
        """Save current column state for persistence."""
        return self.main_window.column_manager.save_column_state(table_type)

    def load_column_state(self, table_type: str, state_data: dict) -> None:
        """Load column state from persistence."""
        self.main_window.column_manager.load_column_state(table_type, state_data)

    # ========================================================================
    # Initial Column Setup
    # ========================================================================

    def ensure_initial_column_sizing(self) -> None:
        """Ensure column widths are properly sized on startup, especially when no config exists."""
        # Use the original FileTableView column configuration logic instead of ColumnManager
        if hasattr(self.main_window, "file_table_view") and self.main_window.file_table_view.model():
            # Trigger the original, sophisticated column configuration
            if hasattr(self.main_window.file_table_view, "_column_mgmt_behavior"):
                self.main_window.file_table_view._column_mgmt_behavior.configure_columns()

            # Then trigger column adjustment using the existing logic

            logger.debug(
                "[ConfigColumnHandler] Used original FileTableView column configuration",
                extra={"dev_only": True},
            )

        # Configure other table views with ColumnManager (they don't have the sophisticated logic)
        # Note: MetadataTreeView handles its own column configuration, so we skip it here

        if hasattr(self.main_window, "preview_tables_view") and self.main_window.preview_tables_view:
            # Configure preview tables
            if hasattr(self.main_window.preview_tables_view, "old_names_table"):
                self.main_window.column_manager.configure_table_columns(
                    self.main_window.preview_tables_view.old_names_table, "preview_old"
                )
            if hasattr(self.main_window.preview_tables_view, "new_names_table"):
                self.main_window.column_manager.configure_table_columns(
                    self.main_window.preview_tables_view.new_names_table, "preview_new"
                )

    # ========================================================================
    # Folder Restore
    # ========================================================================

    def restore_last_folder_if_available(self) -> None:
        """Restore the last folder if available and user wants it."""
        # Delegate to WindowConfigManager
        self.main_window.window_config_manager.restore_last_folder_if_available()

    # ========================================================================
    # Manager Registration
    # ========================================================================

    def register_managers_in_context(self):
        """Register all managers in ApplicationContext for centralized access.

        This eliminates the need for parent_window.some_manager traversal patterns.
        Components can access managers via context.get_manager('name') instead.
        """
        try:
            # Core managers
            self.main_window.context.register_manager("table", self.main_window.table_manager)
            self.main_window.context.register_manager("metadata", self.main_window.metadata_manager)
            self.main_window.context.register_manager("selection", self.main_window.selection_manager)
            self.main_window.context.register_manager("rename", self.main_window.rename_manager)
            self.main_window.context.register_manager("preview", self.main_window.preview_manager)

            # UI managers (ui_manager removed - replaced by individual controllers)
            self.main_window.context.register_manager("dialog", self.main_window.dialog_manager)
            self.main_window.context.register_manager("status", self.main_window.status_manager)
            self.main_window.context.register_manager("shortcut", self.main_window.shortcut_manager)
            self.main_window.context.register_manager("splitter", self.main_window.splitter_manager)
            self.main_window.context.register_manager("window_config", self.main_window.window_config_manager)
            self.main_window.context.register_manager("column", self.main_window.column_manager)

            # File operations managers
            self.main_window.context.register_manager("file_load", self.main_window.file_load_manager)
            self.main_window.context.register_manager("file_operations", self.main_window.file_operations_manager)
            self.main_window.context.register_manager("file_validation", self.main_window.file_validation_manager)

            # System managers
            self.main_window.context.register_manager("db", self.main_window.db_manager)
            self.main_window.context.register_manager("backup", self.main_window.backup_manager)
            self.main_window.context.register_manager("rename_history", self.main_window.rename_history_manager)

            # Utility managers
            self.main_window.context.register_manager("utility", self.main_window.utility_manager)
            self.main_window.context.register_manager("event_handler", self.main_window.event_handler_manager)
            self.main_window.context.register_manager("drag", self.main_window.drag_manager)
            self.main_window.context.register_manager("drag_cleanup", self.main_window.drag_cleanup_manager)
            self.main_window.context.register_manager("initialization", self.main_window.initialization_manager)

            # Service layer
            self.main_window.context.register_manager("app_service", self.main_window.app_service)
            self.main_window.context.register_manager("batch", self.main_window.batch_manager)
            self.main_window.context.register_manager("config", self.main_window.config_manager)

            # Coordinators
            self.main_window.context.register_manager("signal_coordinator", self.main_window.signal_coordinator)

            # Engines
            self.main_window.context.register_manager("rename_engine", self.main_window.unified_rename_engine)

            logger.info(
                "[ConfigColumnHandler] Registered %d managers in ApplicationContext",
                len(self.main_window.context.list_managers()),
                extra={"dev_only": True},
            )
            logger.debug(
                "[ConfigColumnHandler] Available managers: %s",
                self.main_window.context.list_managers(),
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.error("[ConfigColumnHandler] Error registering managers in context: %s", e)
