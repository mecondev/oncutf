"""Module: shutdown_lifecycle_handler.py

Author: Michael Economou
Date: 2026-01-01

Handler for application shutdown and lifecycle management in MainWindow.

CRITICAL: This handler manages the coordinated shutdown sequence.
All cleanup operations must execute in proper order to prevent data loss.
"""

from __future__ import annotations

import contextlib
from contextlib import suppress
from datetime import datetime
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QApplication

if TYPE_CHECKING:
    from PyQt5.QtGui import QCloseEvent

    from oncutf.ui.main_window import MainWindow

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ShutdownLifecycleHandler:
    """Handles application shutdown and lifecycle management.

    WARNING: Critical shutdown path - changes require extensive testing.
    """

    def __init__(self, main_window: MainWindow) -> None:
        """Initialize handler with MainWindow reference."""
        self.main_window = main_window
        logger.debug("[ShutdownLifecycleHandler] Initialized")

    # ============================================================================
    # MAIN SHUTDOWN FLOW
    # ============================================================================

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handles application shutdown and cleanup using Shutdown Coordinator.

        Ensures all resources are properly released and threads are stopped.
        """
        # If shutdown is already in progress, ignore additional close events
        if hasattr(self.main_window, "_shutdown_in_progress") and self.main_window._shutdown_in_progress:
            event.ignore()
            return

        shutdown_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("Application shutting down at %s...", shutdown_timestamp)

        # 0. Check for unsaved metadata changes
        if self._check_for_unsaved_changes():
            reply = self.main_window.dialog_manager.confirm_unsaved_changes(self.main_window)

            if reply == "cancel":
                # User wants to cancel closing
                event.ignore()
                return
            elif reply == "save_and_close":
                # User wants to save changes before closing
                try:
                    # Save all modified metadata with exit save flag
                    if hasattr(self.main_window, "metadata_manager") and self.main_window.metadata_manager:
                        if hasattr(self.main_window.metadata_manager, "save_all_modified_metadata"):
                            self.main_window.metadata_manager.save_all_modified_metadata(is_exit_save=True)
                            logger.info("[CloseEvent] Saved all metadata changes before closing")
                        else:
                            logger.warning(
                                "[CloseEvent] save_all_modified_metadata method not available"
                            )
                    else:
                        logger.warning("[CloseEvent] MetadataManager not available for saving")
                except Exception as e:
                    logger.error("[CloseEvent] Failed to save metadata before closing: %s", e)
                    # Show error but continue closing anyway
                    from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

                    CustomMessageDialog.information(
                        self.main_window,
                        "Save Error",
                        f"Failed to save metadata changes:\n{e}\n\nClosing anyway.",
                    )
            # If reply == "close_without_saving", we just continue with closing

        # Mark shutdown as in progress
        self.main_window._shutdown_in_progress = True

        # Save configuration immediately before shutdown
        try:
            from oncutf.utils.shared.json_config_manager import get_app_config_manager

            get_app_config_manager().save_immediate()
            logger.info("[CloseEvent] Configuration saved immediately before shutdown")
        except Exception as e:
            logger.error("[CloseEvent] Failed to save configuration: %s", e)

        # Ignore this close event - we'll handle closing ourselves
        event.ignore()

        # Start coordinated shutdown process
        self._start_coordinated_shutdown()

    def _start_coordinated_shutdown(self):
        """Start the coordinated shutdown process using ShutdownCoordinator."""
        from oncutf.utils.ui.cursor_helper import wait_cursor

        try:
            # Use wait cursor for the entire shutdown process (simpler than dialog)
            with wait_cursor(restore_after=False):
                logger.info("[CloseEvent] Starting coordinated shutdown with wait cursor")

                # Perform additional cleanup before coordinator shutdown
                self._pre_coordinator_cleanup()

                # Execute coordinated shutdown (no dialog progress needed)
                success = self.main_window.shutdown_coordinator.execute_shutdown(
                    progress_callback=None, emergency=False
                )

                # Perform final cleanup after coordinator
                self._post_coordinator_cleanup()

                # Log summary
                summary = self.main_window.shutdown_coordinator.get_summary()
                logger.info("[CloseEvent] Shutdown summary: %s", summary)

            # Complete shutdown (cursor restored by context manager exit)
            self._complete_shutdown(success)

        except Exception as e:
            logger.exception("[CloseEvent] Error during coordinated shutdown: %s", e)
            # Fallback to emergency shutdown
            QApplication.restoreOverrideCursor()
            QApplication.quit()

    def _complete_shutdown(self, success: bool = True):
        """Complete the shutdown process."""
        try:
            # Restore any remaining override cursors
            with contextlib.suppress(RuntimeError):
                while QApplication.overrideCursor():
                    QApplication.restoreOverrideCursor()

            # Process any pending deleteLater events
            with contextlib.suppress(RuntimeError):
                QApplication.processEvents()

            # Log completion
            status = "successfully" if success else "with errors"
            logger.info("[CloseEvent] Shutdown completed %s", status)

            # Quit application (with guard against multiple calls)
            with contextlib.suppress(RuntimeError):
                QApplication.quit()

        except Exception as e:
            logger.error("[CloseEvent] Error completing shutdown: %s", e)
            with contextlib.suppress(RuntimeError):
                QApplication.quit()

    # ============================================================================
    # PRE/POST CLEANUP
    # ============================================================================

    def _pre_coordinator_cleanup(self):
        """Perform cleanup before coordinator shutdown (UI-specific cleanup)."""
        try:
            # Create database backup
            if hasattr(self.main_window, "backup_manager") and self.main_window.backup_manager:
                try:
                    self.main_window.backup_manager.create_backup(reason="auto")  # type: ignore[union-attr]
                    logger.info("[CloseEvent] Database backup created")
                except Exception as e:
                    logger.warning("[CloseEvent] Database backup failed: %s", e)

            # Save window configuration
            if hasattr(self.main_window, "window_config_manager") and self.main_window.window_config_manager:
                try:
                    self.main_window.window_config_manager.save_window_config()
                    logger.info("[CloseEvent] Window configuration saved")
                except Exception as e:
                    logger.warning("[CloseEvent] Failed to save window config: %s", e)

            # Flush batch operations
            if hasattr(self.main_window, "batch_manager") and self.main_window.batch_manager:
                try:
                    if hasattr(self.main_window.batch_manager, "flush_operations"):
                        self.main_window.batch_manager.flush_operations()  # type: ignore[union-attr]
                        logger.info("[CloseEvent] Batch operations flushed")
                except Exception as e:
                    logger.warning("[CloseEvent] Batch flush failed: %s", e)

            # Cleanup drag operations
            if hasattr(self.main_window, "drag_manager") and self.main_window.drag_manager:
                try:
                    self.main_window.drag_manager.force_cleanup()  # type: ignore[union-attr]
                    logger.info("[CloseEvent] Drag manager cleaned up")
                except Exception as e:
                    logger.warning("[CloseEvent] Drag cleanup failed: %s", e)

            # Close dialogs
            if hasattr(self.main_window, "dialog_manager") and self.main_window.dialog_manager:
                try:
                    self.main_window.dialog_manager.cleanup()  # type: ignore[union-attr]
                    logger.info("[CloseEvent] All dialogs closed")
                except Exception as e:
                    logger.warning("[CloseEvent] Dialog cleanup failed: %s", e)

            # Stop metadata operations
            if hasattr(self.main_window, "metadata_thread") and self.main_window.metadata_thread:
                try:
                    # Disconnect all signals first to prevent crashes
                    with suppress(RuntimeError, TypeError):
                        self.main_window.metadata_thread.disconnect()

                    self.main_window.metadata_thread.quit()
                    if not self.main_window.metadata_thread.wait(1500):  # Wait max 1.5 seconds
                        logger.warning("[CloseEvent] Metadata thread did not stop, terminating...")
                        self.main_window.metadata_thread.terminate()
                        if not self.main_window.metadata_thread.wait(500):  # Wait 500ms for termination
                            logger.error("[CloseEvent] Metadata thread failed to terminate")
                    logger.info("[CloseEvent] Metadata thread stopped")
                    # Set to None to prevent double cleanup
                    self.main_window.metadata_thread = None
                except Exception as e:
                    logger.warning("[CloseEvent] Metadata thread cleanup failed: %s", e)

        except Exception as e:
            logger.error("[CloseEvent] Error in pre-coordinator cleanup: %s", e)

    def _post_coordinator_cleanup(self):
        """Perform final cleanup after coordinator shutdown."""
        try:
            # Clean up Qt resources with defensive checks
            if hasattr(self.main_window, "file_table_view") and self.main_window.file_table_view:
                with suppress(RuntimeError, AttributeError):
                    self.main_window.file_table_view.clearSelection()
                with suppress(RuntimeError, AttributeError):
                    self.main_window.file_table_view.setModel(None)

            # Additional cleanup
            try:
                from oncutf.core.application_context import ApplicationContext

                context = ApplicationContext.get_instance()
                if context:
                    context.cleanup()  # type: ignore[union-attr]
                    logger.info("[CloseEvent] Application context cleaned up")
            except Exception as ctx_error:
                logger.warning("[CloseEvent] Context cleanup failed: %s", ctx_error)

        except Exception as e:
            logger.error("[CloseEvent] Error in post-coordinator cleanup: %s", e)

    # ============================================================================
    # UNSAVED CHANGES CHECK
    # ============================================================================

    def _check_for_unsaved_changes(self) -> bool:
        """Check if there are any unsaved metadata changes.

        Returns:
            bool: True if there are unsaved changes, False otherwise

        """
        if not hasattr(self.main_window, "metadata_tree_view"):
            return False

        try:
            # Force save current file modifications to per-file storage first
            if (
                hasattr(self.main_window.metadata_tree_view, "_current_file_path")
                and self.main_window.metadata_tree_view._current_file_path
            ):
                if self.main_window.metadata_tree_view.modified_items:
                    self.main_window.metadata_tree_view._set_in_path_dict(
                        self.main_window.metadata_tree_view._current_file_path,
                        self.main_window.metadata_tree_view.modified_items.copy(),
                        self.main_window.metadata_tree_view.modified_items_per_file,
                    )

            # Get all modified metadata for all files
            all_modifications = self.main_window.metadata_tree_view.get_all_modified_metadata_for_files()

            # Check if there are any actual modifications
            has_modifications = any(modifications for modifications in all_modifications.values())

            if has_modifications:
                logger.info(
                    "[CloseEvent] Found unsaved changes in %d files", len(all_modifications)
                )
                for file_path, modifications in all_modifications.items():
                    if modifications:
                        logger.debug("[CloseEvent] - %s: %s", file_path, list(modifications.keys()))

            return has_modifications

        except Exception as e:
            logger.warning("[CloseEvent] Error checking for unsaved changes: %s", e)
            return False

    # ============================================================================
    # BACKGROUND CLEANUP
    # ============================================================================

    def _force_cleanup_background_workers(self) -> None:
        """Force cleanup of any background workers/threads."""
        logger.info("[CloseEvent] Cleaning up background workers...")

        # 1. Cleanup HashWorker if it exists
        if hasattr(self.main_window, "event_handler_manager") and hasattr(
            self.main_window.event_handler_manager, "hash_worker"
        ):
            hash_worker = self.main_window.event_handler_manager.hash_worker
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

        threads = self.main_window.findChildren(QThread)
        for thread in threads:
            if thread.isRunning():
                logger.info("[CloseEvent] Terminating QThread: %s", thread.__class__.__name__)
                thread.quit()
                if not thread.wait(1000):  # Wait max 1 second
                    logger.warning(
                        "[CloseEvent] Thread %s did not quit gracefully, terminating...",
                        thread.__class__.__name__,
                    )
                    thread.terminate()
                    if not thread.wait(500):  # CRITICAL: Add timeout to prevent infinite hang
                        logger.error(
                            "[CloseEvent] Thread %s did not terminate after 500ms",
                            thread.__class__.__name__,
                        )

    def _force_close_progress_dialogs(self) -> None:
        """Force close any active progress dialogs except the shutdown dialog."""
        from oncutf.ui.dialogs.metadata_waiting_dialog import OperationDialog
        from oncutf.utils.ui.progress_dialog import ProgressDialog

        # Find and close any active progress dialogs
        dialogs_closed = 0

        # Close ProgressDialog instances
        progress_dialogs = self.main_window.findChildren(ProgressDialog)
        for dialog in progress_dialogs:
            if dialog.isVisible():
                logger.info("[CloseEvent] Force closing ProgressDialog")
                dialog.reject()  # Force close without waiting
                dialogs_closed += 1

        # Close OperationDialog instances (but NOT the shutdown dialog)
        metadata_dialogs = self.main_window.findChildren(OperationDialog)
        for dialog in metadata_dialogs:
            if dialog.isVisible() and dialog != getattr(self.main_window, "shutdown_dialog", None):
                logger.info("[CloseEvent] Force closing OperationDialog")
                dialog.reject()  # Force close without waiting
                dialogs_closed += 1

        if dialogs_closed > 0:
            logger.info(
                "[CloseEvent] Force closed %d progress dialogs (excluding shutdown dialog)",
                dialogs_closed,
            )

    # ============================================================================
    # REGISTRATION
    # ============================================================================

    def _register_shutdown_components(self):
        """Register all concurrent components with shutdown coordinator."""
        try:
            # Register timer manager
            from oncutf.utils.shared.timer_manager import get_timer_manager

            timer_mgr = get_timer_manager()
            self.main_window.shutdown_coordinator.register_timer_manager(timer_mgr)

            # Register thread pool manager (if exists)
            try:
                from oncutf.core.thread_pool_manager import get_thread_pool_manager

                thread_pool_mgr = get_thread_pool_manager()
                self.main_window.shutdown_coordinator.register_thread_pool_manager(thread_pool_mgr)
            except Exception as e:
                logger.debug("[MainWindow] Thread pool manager not available: %s", e)

            # Register database manager
            if hasattr(self.main_window, "db_manager") and self.main_window.db_manager:
                self.main_window.shutdown_coordinator.register_database_manager(self.main_window.db_manager)

            # Register ExifTool wrapper (get active instance if any)
            try:
                from oncutf.utils.shared.exiftool_wrapper import ExifToolWrapper

                # Get any active instance
                if ExifToolWrapper._instances:  # type: ignore[attr-defined]
                    exiftool = next(iter(ExifToolWrapper._instances))  # type: ignore[attr-defined]
                    self.main_window.shutdown_coordinator.register_exiftool_wrapper(exiftool)
            except Exception as e:
                logger.debug("[MainWindow] ExifTool wrapper not available: %s", e)

            logger.info("[MainWindow] Shutdown components registered successfully")

        except Exception as e:
            logger.error("[MainWindow] Error registering shutdown components: %s", e)
