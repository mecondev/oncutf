"""Module: shutdown_lifecycle_handler.py.

Author: Michael Economou
Date: 2026-01-01

Handler for application shutdown and lifecycle management in MainWindow.

CRITICAL: This handler manages the coordinated shutdown sequence.
All cleanup operations must execute in proper order to prevent data loss.
"""

from __future__ import annotations

import contextlib
import time
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QApplication

if TYPE_CHECKING:
    from collections.abc import Generator

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
        if (
            hasattr(self.main_window, "_shutdown_in_progress")
            and self.main_window._shutdown_in_progress
        ):
            event.ignore()
            return

        shutdown_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("=" * 70)
        logger.info("[SHUTDOWN] Application shutdown initiated at %s", shutdown_timestamp)
        logger.info("=" * 70)

        # 0. Check for unsaved metadata changes
        if self._check_for_unsaved_changes():
            reply = self.main_window.dialog_manager.confirm_unsaved_changes(self.main_window)

            if reply == "cancel":
                # User wants to cancel closing
                event.ignore()
                return
            if reply == "save_and_close":
                # User wants to save changes before closing
                try:
                    # Save all modified metadata with exit save flag
                    if (
                        hasattr(self.main_window, "metadata_manager")
                        and self.main_window.metadata_manager
                    ):
                        if hasattr(
                            self.main_window.metadata_manager,
                            "save_all_modified_metadata",
                        ):
                            self.main_window.metadata_manager.save_all_modified_metadata(
                                is_exit_save=True
                            )
                            logger.info("[CloseEvent] Saved all metadata changes before closing")
                        else:
                            logger.warning(
                                "[CloseEvent] save_all_modified_metadata method not available"
                            )
                    else:
                        logger.warning("[CloseEvent] MetadataManager not available for saving")
                except Exception as save_error:
                    logger.exception("[CloseEvent] Failed to save metadata before closing")
                    # Show error but continue closing anyway
                    from oncutf.ui.dialogs.custom_message_dialog import (
                        CustomMessageDialog,
                    )

                    CustomMessageDialog.information(
                        self.main_window,
                        "Save Error",
                        f"Failed to save metadata changes:\n{save_error}\n\nClosing anyway.",
                    )
            # If reply == "close_without_saving", we just continue with closing

        # Mark shutdown as in progress
        self.main_window._shutdown_in_progress = True

        # Save configuration immediately before shutdown
        try:
            from oncutf.utils.shared.json_config_manager import get_app_config_manager

            get_app_config_manager().save_immediate()
            logger.info("[SHUTDOWN] Configuration saved successfully")
        except Exception:
            logger.exception("[CloseEvent] Failed to save configuration")

        # Ignore this close event - we'll handle closing ourselves
        event.ignore()

        # Immediately hide/disable the window so Windows doesn't show
        # a "Not Responding" dialog while we perform shutdown work.
        with contextlib.suppress(Exception):
            self.main_window.setEnabled(False)
        with contextlib.suppress(Exception):
            self.main_window.hide()

        # Start coordinated shutdown on the next Qt tick so closeEvent returns
        # immediately (prevents Windows "Not Responding" during close handling).
        from PyQt5.QtCore import QTimer

        QTimer.singleShot(0, self._start_coordinated_shutdown)

    def _start_coordinated_shutdown(self):
        """Start the coordinated shutdown process using ShutdownCoordinator."""
        try:
            # Canonical helper (see project guidelines)
            from oncutf.ui.helpers.cursor_helper import wait_cursor
        except Exception:
            # Shutdown must never crash due to helper import issues.
            from contextlib import contextmanager

            @contextmanager
            def wait_cursor(_show_wait: bool = True) -> Generator[None, None, None]:
                yield

        # Watchdog disabled: user requested to stop creating temp watchdog logs.
        self._shutdown_watchdog_cancel = None
        self._shutdown_wait_cursor_cm = wait_cursor

        logger.info("[SHUTDOWN] Starting coordinated shutdown process")

        from PyQt5.QtCore import QTimer

        QTimer.singleShot(0, self._shutdown_step_pre_cleanup)

    def _shutdown_step_pre_cleanup(self) -> None:
        """Run UI pre-cleanup, then start async coordinator shutdown."""
        from PyQt5.QtCore import QTimer

        try:
            self._shutdown_pre_cleanup_steps = [
                self._pre_cleanup_stop_periodic_backups,
                self._pre_cleanup_save_window_config,
                self._pre_cleanup_flush_batch_operations,
                self._pre_cleanup_cleanup_drag_manager,
                self._pre_cleanup_cleanup_dialogs,
                self._pre_cleanup_cleanup_metadata_thread,
            ]
            self._shutdown_pre_cleanup_index = 0
            QTimer.singleShot(0, self._shutdown_run_pre_cleanup_step)
        except Exception:
            logger.exception("[CloseEvent] Error starting async shutdown")
            self._emergency_quit()
        else:
            return

    def _shutdown_run_pre_cleanup_step(self) -> None:
        """Execute one pre-cleanup step per Qt tick."""
        from PyQt5.QtCore import QTimer

        try:
            steps = getattr(self, "_shutdown_pre_cleanup_steps", [])
            idx = getattr(self, "_shutdown_pre_cleanup_index", 0)

            if idx >= len(steps):
                QTimer.singleShot(0, self._shutdown_start_async_coordinator)
                return

            step = steps[idx]
            self._shutdown_pre_cleanup_index = idx + 1

            with self._shutdown_wait_cursor_cm():
                step()

            QTimer.singleShot(0, self._shutdown_run_pre_cleanup_step)
        except Exception:
            logger.exception("[CloseEvent] Pre-cleanup step failed")
            QTimer.singleShot(0, self._shutdown_run_pre_cleanup_step)

    def _shutdown_start_async_coordinator(self) -> None:
        """Start the coordinator async shutdown after pre-cleanup finishes."""
        from PyQt5.QtCore import QTimer

        try:
            # Connect once; run post-cleanup when coordinator finishes.
            with contextlib.suppress(Exception):
                self.main_window.shutdown_coordinator.shutdown_completed.disconnect(
                    self._on_coordinator_shutdown_completed
                )
            self.main_window.shutdown_coordinator.shutdown_completed.connect(
                self._on_coordinator_shutdown_completed
            )

            started = self.main_window.shutdown_coordinator.execute_shutdown_async(
                progress_callback=None,
                emergency=False,
            )
            if not started:
                # If already in progress, re-check shortly.
                QTimer.singleShot(50, self._shutdown_start_async_coordinator)
        except Exception:
            logger.exception("[CloseEvent] Error starting async shutdown")
            self._emergency_quit()

    def _on_coordinator_shutdown_completed(self, success: bool) -> None:
        """Handle coordinator completion without blocking the event loop."""
        from PyQt5.QtCore import QTimer

        self._shutdown_coordinator_success = success
        QTimer.singleShot(0, self._shutdown_step_post_cleanup)

    def _shutdown_step_post_cleanup(self) -> None:
        """Run post-cleanup and schedule final quit on next tick."""
        from PyQt5.QtCore import QTimer

        try:
            with self._shutdown_wait_cursor_cm():
                self._post_coordinator_cleanup()

            summary = self.main_window.shutdown_coordinator.get_summary()
            if summary.get("executed", False):
                logger.info(
                    "[SHUTDOWN] Summary: %d/%d phases successful, %.2fs total, emergency=%s",
                    summary.get("successful_phases", 0),
                    summary.get("total_phases", 0),
                    summary.get("total_duration", 0.0),
                    summary.get("emergency_mode", False),
                )
            else:
                logger.info("[SHUTDOWN] Summary: coordinator not executed")

            QTimer.singleShot(0, self._shutdown_step_finalize)
        except Exception:
            logger.exception("[CloseEvent] Error during post-cleanup")
            self._emergency_quit()

    def _shutdown_step_finalize(self) -> None:
        """Finalize shutdown (cancel watchdog, quit)."""
        try:
            self._complete_shutdown(getattr(self, "_shutdown_coordinator_success", True))
        finally:
            with contextlib.suppress(Exception):
                if (
                    hasattr(self, "_shutdown_watchdog_cancel")
                    and self._shutdown_watchdog_cancel is not None
                ):
                    self._shutdown_watchdog_cancel()

            with contextlib.suppress(Exception):
                self.main_window.shutdown_coordinator.shutdown_completed.disconnect(
                    self._on_coordinator_shutdown_completed
                )

    def _emergency_quit(self) -> None:
        """Emergency fallback quit path - must never raise."""
        with contextlib.suppress(Exception):
            if QApplication.instance():
                QApplication.restoreOverrideCursor()
        with contextlib.suppress(Exception):
            if QApplication.instance():
                QApplication.quit()

    def _start_shutdown_watchdog(self, timeout_s: float, *, repeat: bool = False):
        """Start a watchdog that dumps stack traces if shutdown appears hung.

        Uses faulthandler.dump_traceback_later(), which is more reliable than a
        Python-level Timer when the main thread is blocked.

        Returns:
            Callable[[], None]: cancel function

        """
        import faulthandler
        import tempfile

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        dump_path = str(Path(tempfile.gettempdir()) / f"oncutf_shutdown_hang_{timestamp}.log")

        # Create the file early so the path is known even if we hard-hang.
        # Keep output ASCII-safe.
        try:
            with Path(dump_path).open("w", encoding="utf-8", errors="backslashreplace") as f:
                f.write("oncutf shutdown watchdog armed.\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Timeout: {timeout_s:.1f}s\n")
                f.write(f"Repeat: {repeat}\n")
                f.write("\nExpected: stack dump will be appended below during shutdown.\n")
                f.write("\n")
                f.flush()

                logger.info(
                    "[CloseEvent] Shutdown watchdog armed (%.1fs): %s",
                    timeout_s,
                    dump_path,
                )

                # Ensure faulthandler is enabled and configured to include all threads.
                # NOTE: enable() is idempotent.
                with contextlib.suppress(Exception):
                    faulthandler.enable(file=f, all_threads=True)

                # Schedule automatic stack dump(s) during shutdown.
                faulthandler.dump_traceback_later(timeout_s, repeat=repeat, file=f, exit=False)
        except Exception:
            logger.exception("[CloseEvent] Failed to open watchdog dump file")

            def _cancel_noop() -> None:
                return

            return _cancel_noop

        def _cancel() -> None:
            with contextlib.suppress(Exception):
                faulthandler.cancel_dump_traceback_later()
            with contextlib.suppress(Exception):
                f.flush()
            with contextlib.suppress(Exception):
                f.close()

        return _cancel

    def _complete_shutdown(self, success: bool = True):
        """Complete the shutdown process."""
        try:
            # Restore any remaining override cursors
            with contextlib.suppress(RuntimeError):
                if QApplication.instance():
                    while QApplication.overrideCursor():
                        QApplication.restoreOverrideCursor()

            # Single processEvents to clear pending events
            with contextlib.suppress(RuntimeError):
                if QApplication.instance():
                    QApplication.processEvents()

            # Log completion BEFORE shutting down logging system
            status = "successfully" if success else "with errors"
            logger.info("=" * 70)
            logger.info("[SHUTDOWN] Shutdown completed %s", status)
            logger.info("[SHUTDOWN] Application will now exit")
            logger.info("=" * 70)

            # Flush logs before shutdown to ensure all messages are written
            import logging
            import sys

            for handler in logging.getLogger().handlers:
                handler.flush()
            sys.stdout.flush()
            sys.stderr.flush()

            # Now shutdown logging system
            logging.shutdown()

            # Quit immediately - no delay
            with contextlib.suppress(RuntimeError):
                QApplication.quit()

        except Exception:
            logger.exception("[CloseEvent] Error completing shutdown")
            # Flush on error too
            import logging
            import sys

            for handler in logging.getLogger().handlers:
                handler.flush()
            sys.stdout.flush()
            sys.stderr.flush()

            with contextlib.suppress(RuntimeError):
                QApplication.quit()

    # ============================================================================
    # PRE/POST CLEANUP
    # ============================================================================

    def _pre_coordinator_cleanup(self):
        """Perform cleanup before coordinator shutdown (UI-specific cleanup)."""
        try:
            self._pre_cleanup_stop_periodic_backups()
            self._pre_cleanup_save_window_config()
            self._pre_cleanup_flush_batch_operations()
            self._pre_cleanup_cleanup_drag_manager()
            self._pre_cleanup_cleanup_dialogs()
            self._pre_cleanup_cleanup_metadata_thread()

        except Exception:
            logger.exception("[CloseEvent] Error in pre-coordinator cleanup")

    def _pre_cleanup_stop_periodic_backups(self) -> None:
        """Stop periodic backup timer to avoid blocking UI during shutdown."""
        # Database backup on shutdown can block the UI thread (large file copy).
        # We rely on periodic backups instead and only stop the timer here.
        backup_mgr = getattr(self.main_window, "backup_manager", None)
        if backup_mgr is not None:
            try:
                if hasattr(backup_mgr, "stop_periodic_backups"):
                    backup_mgr.stop_periodic_backups()
                logger.info("[CloseEvent] Periodic backups stopped (skipping shutdown backup)")
            except Exception as e:
                logger.warning("[CloseEvent] Failed to stop periodic backups: %s", e)

    def _pre_cleanup_save_window_config(self) -> None:
        """Save window configuration before shutdown."""
        logger.info("[CloseEvent] Starting window config save...")
        if (
            hasattr(self.main_window, "window_config_manager")
            and self.main_window.window_config_manager
        ):
            try:
                logger.debug(
                    "[CloseEvent] Calling save_window_config()",
                    extra={"dev_only": True},
                )
                self.main_window.window_config_manager.save_window_config()
                logger.info("[CloseEvent] Window configuration saved to config manager")

                # Force immediate save to disk after marking config as dirty
                try:
                    from oncutf.utils.shared.json_config_manager import (
                        get_app_config_manager,
                    )

                    config_mgr = get_app_config_manager()
                    logger.debug(
                        "[CloseEvent] Calling save_immediate()",
                        extra={"dev_only": True},
                    )
                    result = config_mgr.save_immediate()
                    logger.info(
                        "[CloseEvent] Configuration saved to disk immediately (result: %s)",
                        result,
                    )
                except Exception:
                    logger.exception("[CloseEvent] Failed to save config immediately")

            except Exception:
                logger.exception("[CloseEvent] Failed to save window config")
        else:
            logger.warning("[CloseEvent] window_config_manager not available")

    def _pre_cleanup_flush_batch_operations(self) -> None:
        """Flush pending batch operations before shutdown."""
        batch_mgr = getattr(self.main_window, "batch_manager", None)
        if batch_mgr is not None:
            try:
                if hasattr(batch_mgr, "flush_operations"):
                    batch_mgr.flush_operations()
                    logger.info("[CloseEvent] Batch operations flushed")
            except Exception as e:
                logger.warning("[CloseEvent] Batch flush failed: %s", e)

    def _pre_cleanup_cleanup_drag_manager(self) -> None:
        """Force cleanup of drag manager state."""
        drag_mgr = getattr(self.main_window, "drag_manager", None)
        if drag_mgr is not None:
            try:
                drag_mgr.force_cleanup()
                logger.info("[CloseEvent] Drag manager cleaned up")
            except Exception as e:
                logger.warning("[CloseEvent] Drag cleanup failed: %s", e)

    def _pre_cleanup_cleanup_dialogs(self) -> None:
        """Close all dialogs via dialog manager."""
        dialog_mgr = getattr(self.main_window, "dialog_manager", None)
        if dialog_mgr is not None:
            try:
                dialog_mgr.cleanup()
                logger.info("[CloseEvent] All dialogs closed")
            except Exception as e:
                logger.warning("[CloseEvent] Dialog cleanup failed: %s", e)

    def _pre_cleanup_cleanup_metadata_thread(self) -> None:
        """Cleanup metadata manager and thread before shutdown."""
        # First, cleanup the metadata manager (handles ParallelMetadataLoader)
        if hasattr(self.main_window, "metadata_manager") and self.main_window.metadata_manager:
            try:
                self.main_window.metadata_manager.cleanup()
                logger.info("[CloseEvent] Metadata manager cleaned up")
            except Exception as e:
                logger.warning("[CloseEvent] Metadata manager cleanup failed: %s", e)

        # Then cleanup the metadata thread if it exists separately
        if hasattr(self.main_window, "metadata_thread") and self.main_window.metadata_thread:
            try:
                # Disconnect all signals first to prevent crashes
                with suppress(RuntimeError, TypeError):
                    self.main_window.metadata_thread.disconnect()

                self.main_window.metadata_thread.quit()
                if not self.main_window.metadata_thread.wait(200):
                    logger.warning("[CloseEvent] Metadata thread did not stop, terminating...")
                    self.main_window.metadata_thread.terminate()
                    logger.info("[CloseEvent] Metadata thread terminated")
                else:
                    logger.info("[CloseEvent] Metadata thread stopped")

                # Set to None to prevent double cleanup
                self.main_window.metadata_thread = None
            except Exception as e:
                logger.warning("[CloseEvent] Metadata thread cleanup failed: %s", e)

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
                from oncutf.ui.adapters.qt_app_context import QtAppContext

                context = QtAppContext.get_instance()
                if context is not None:
                    context.cleanup()
                    logger.info("[CloseEvent] Application context cleaned up")
            except Exception as ctx_error:
                logger.warning("[CloseEvent] Context cleanup failed: %s", ctx_error)

        except Exception:
            logger.exception("[CloseEvent] Error in post-coordinator cleanup")

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
            ) and self.main_window.metadata_tree_view.modified_items:
                self.main_window.metadata_tree_view._scroll_behavior._set_in_path_dict(
                    self.main_window.metadata_tree_view._current_file_path,
                    self.main_window.metadata_tree_view.modified_items.copy(),
                    self.main_window.metadata_tree_view.modified_items_per_file,
                )

            # Get all modified metadata for all files
            all_modifications = (
                self.main_window.metadata_tree_view.get_all_modified_metadata_for_files()
            )

            # Check if there are any actual modifications
            has_modifications = any(modifications for modifications in all_modifications.values())

            if has_modifications:
                logger.info(
                    "[CloseEvent] Found unsaved changes in %d files",
                    len(all_modifications),
                )
                for file_path, modifications in all_modifications.items():
                    if modifications:
                        logger.debug(
                            "[CloseEvent] - %s: %s",
                            file_path,
                            list(modifications.keys()),
                        )
        except Exception as e:
            logger.warning("[CloseEvent] Error checking for unsaved changes: %s", e)
            return False
        else:
            return has_modifications

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
        from oncutf.ui.helpers.progress_dialog import ProgressDialog

        # Find and close any active progress dialogs
        dialogs_closed = 0

        # Close ProgressDialog instances (but NOT the shutdown dialog)
        progress_dialogs = self.main_window.findChildren(ProgressDialog)
        for dialog in progress_dialogs:
            if dialog.isVisible() and dialog != getattr(self.main_window, "shutdown_dialog", None):
                logger.info("[CloseEvent] Force closing ProgressDialog")
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
                self.main_window.shutdown_coordinator.register_database_manager(
                    self.main_window.db_manager
                )

            # Register thumbnail manager (must shutdown before database)
            if (
                hasattr(self.main_window, "thumbnail_manager")
                and self.main_window.thumbnail_manager
            ):
                self.main_window.shutdown_coordinator.register_thumbnail_manager(
                    self.main_window.thumbnail_manager
                )

            # Register ExifTool wrapper (get active instance if any)
            try:
                from oncutf.boot.infra_wiring import get_exiftool_wrapper

                exiftool_wrapper_class = get_exiftool_wrapper()
                # Get any active instance
                if exiftool_wrapper_class._instances:
                    exiftool = next(iter(exiftool_wrapper_class._instances))
                    self.main_window.shutdown_coordinator.register_exiftool_wrapper(exiftool)
            except Exception as e:
                logger.debug("[MainWindow] ExifTool wrapper not available: %s", e)

            logger.info("[MainWindow] Shutdown components registered successfully")

        except Exception:
            logger.exception("[MainWindow] Error registering shutdown components")
