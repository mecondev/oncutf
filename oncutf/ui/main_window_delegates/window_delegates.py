"""Window lifecycle and configuration delegates for MainWindow.

Author: Michael Economou
Date: 2026-01-10
"""


class WindowDelegates:
    """Delegate class for window lifecycle and configuration operations.

    All methods delegate to window_event_handler or config_column_handler.

    NOTE: changeEvent and resizeEvent are NOT overridden here to avoid
    infinite recursion with MRO. The handlers call super() which resolves
    to QMainWindow methods. If we override here, super() would resolve back
    to WindowDelegates creating an infinite loop.

    closeEvent IS overridden because it doesn't call super() - it performs
    shutdown logic and calls event.ignore(), so no recursion occurs.
    """

    def center_window(self) -> None:
        """Center window via Application Service."""
        return self.window_event_handler.center_window()

    def closeEvent(self, event) -> None:
        """Handles application shutdown and cleanup using Shutdown Coordinator.

        Ensures all resources are properly released and threads are stopped.
        """
        return self.shutdown_handler.closeEvent(event)

    def _handle_window_state_change(self) -> None:
        """Handle maximize/restore geometry and file table refresh."""
        return self.window_event_handler._handle_window_state_change()

    def _refresh_file_table_for_window_change(self) -> None:
        """Refresh file table after window state changes."""
        return self.window_event_handler._refresh_file_table_for_window_change()

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

    def _register_managers_in_context(self):
        """Register all managers in ApplicationContext for centralized access.

        This eliminates the need for parent_window.some_manager traversal patterns.
        Components can access managers via context.get_manager('name') instead.
        """
        return self.config_column_handler._register_managers_in_context()

    def _register_shutdown_components(self):
        """Register all concurrent components with shutdown coordinator."""
        return self.shutdown_handler._register_shutdown_components()
