"""
file_loading_progress_dialog.py

Author: Michael Economou
Date: 2025-06-23

Modernized file loading dialog that uses the new ProgressDialog.
This will eventually replace FileLoadingDialog to consolidate the codebase.
"""

from typing import Callable, List, Set

from core.unified_file_worker import UnifiedFileWorker
from utils.logger_factory import get_cached_logger
from utils.timer_manager import TimerPriority, TimerType, get_timer_manager

from .progress_dialog import ProgressDialog

logger = get_cached_logger(__name__)


class FileLoadingProgressDialog(ProgressDialog):
    """
    Modernized file loading dialog that extends ProgressDialog.

    Features:
    - Extends ProgressDialog with file loading specific behavior
    - Uses UnifiedFileWorker for consistent file loading
    - Enhanced cancellation support
    - Better error handling
    """

    def __init__(self, parent=None, on_files_loaded: Callable[[List[str]], None] = None):
        """
        Initialize the file loading dialog.

        Args:
            parent: Parent widget
            on_files_loaded: Callback function when files are loaded
        """
        # Initialize as file_loading operation type with cancellation support
        super().__init__(
            parent=parent,
            operation_type='file_loading',
            cancel_callback=self._handle_cancellation_callback
        )

        self.on_files_loaded = on_files_loaded
        self.worker = None
        self.timer_manager = get_timer_manager()
        self._cancellation_timer_id = None

        # Initialize with proper content
        self.set_status("Preparing to load files...")
        self.set_progress(0, 100)
        self.set_filename("Initializing...")

        logger.debug("[FileLoadingProgressDialog] Initialized")

    def load_files(self, paths: List[str], allowed_extensions: Set[str]):
        """Start loading files with the given paths and allowed extensions."""
        self.load_files_with_options(paths, allowed_extensions, recursive=True)

    def load_files_with_options(self, paths: List[str], allowed_extensions: Set[str], recursive: bool = True):
        """Start loading files with enhanced cancellation support."""
        logger.info(f"[FileLoadingProgressDialog] Starting to load {len(paths)} paths (recursive={recursive})")

        # Reset cancellation state
        self._is_cancelling = False
        if self._cancellation_timer_id:
            self.timer_manager.cancel(self._cancellation_timer_id)
            self._cancellation_timer_id = None

        # Update UI immediately before starting worker
        self.set_status("Counting files...")
        self.set_filename("Scanning directories...")
        self.set_progress(0, 100)

        # Force UI update
        self.repaint()

        # Create and setup unified worker
        self.worker = UnifiedFileWorker()
        self.worker.setup_scan(paths, allowed_extensions, recursive)

        # Connect signals - map unified worker signals to dialog methods
        self.worker.progress_updated.connect(self._update_progress)
        self.worker.file_loaded.connect(self._update_filename)
        self.worker.status_updated.connect(self._update_status)
        self.worker.files_found.connect(self._on_loading_finished)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished_scanning.connect(self._on_worker_finished)

        # Start loading with minimal delay using Timer Manager
        self.timer_manager.schedule(
            callback=self.worker.start,
            priority=TimerPriority.IMMEDIATE,
            timer_type=TimerType.UI_UPDATE,
            timer_id="file_loading_start"
        )

    def _update_progress(self, current: int, total: int):
        """Update progress display."""
        self.set_progress(current, total)
        logger.debug(f"[FileLoadingProgressDialog] Progress: {current}/{total}")

    def _update_filename(self, filename: str):
        """Update current filename display."""
        self.set_filename(filename)

    def _update_status(self, status: str):
        """Update status message."""
        self.set_status(status)
        logger.debug(f"[FileLoadingProgressDialog] Status: {status}")

    def _on_loading_finished(self, files: List[str]):
        """Handle loading completion."""
        logger.info(f"[FileLoadingProgressDialog] Loading finished with {len(files)} files")

        # Cancel any pending cancellation timer
        if self._cancellation_timer_id:
            self.timer_manager.cancel(self._cancellation_timer_id)
            self._cancellation_timer_id = None

        if self.on_files_loaded and not self._is_cancelling:
            self.on_files_loaded(files)

        self.accept()

    def _on_worker_finished(self, success: bool):
        """Handle worker completion (success or failure)."""
        logger.debug(f"[FileLoadingProgressDialog] Worker finished (success={success})")

    def _on_error(self, error_msg: str):
        """Handle loading error."""
        logger.error(f"[FileLoadingProgressDialog] Error loading files: {error_msg}")

        # Cancel any pending cancellation timer
        if self._cancellation_timer_id:
            self.timer_manager.cancel(self._cancellation_timer_id)
            self._cancellation_timer_id = None

        self.set_status(f"Error: {error_msg}")
        # Keep dialog open to show error for a moment
        # User can press ESC to close

    def _handle_cancellation_callback(self):
        """Handle cancellation from ProgressDialog's ESC handler."""
        if self._is_cancelling:
            return  # Already cancelling

        logger.info("[FileLoadingProgressDialog] User cancelled loading via ESC")

        if self.worker and self.worker.isRunning():
            # Cancel worker immediately
            self.worker.cancel()

            # Update UI immediately to show cancellation
            self.set_status("Cancelling...")
            self.set_filename("Please wait...")
            self.repaint()  # Force immediate UI update

            # Schedule finalization
            self._cancellation_timer_id = self.timer_manager.schedule(
                callback=self._finalize_cancellation,
                priority=TimerPriority.HIGH,
                timer_type=TimerType.UI_UPDATE,
                timer_id="file_loading_cancel_finalize"
            )
        else:
            # Worker not running, can close immediately
            self._finalize_cancellation()

    def _finalize_cancellation(self):
        """Finalize cancellation process."""
        logger.debug("[FileLoadingProgressDialog] Finalizing cancellation")

        # Clean up worker
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(1000)  # Wait up to 1 second

        # Cancel timer if active
        if self._cancellation_timer_id:
            self.timer_manager.cancel(self._cancellation_timer_id)
            self._cancellation_timer_id = None

        # Dialog will be closed by ProgressDialog's _handle_cancellation method

    def closeEvent(self, event):
        """Handle dialog close event with proper cleanup."""
        logger.info("[FileLoadingProgressDialog] Dialog closing, cancelling worker")

        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.quit()
            self.worker.wait(1000)  # Wait up to 1 second for worker to finish

        # Cancel any pending timers
        if self._cancellation_timer_id:
            self.timer_manager.cancel(self._cancellation_timer_id)
            self._cancellation_timer_id = None

        # Call parent's closeEvent
        super().closeEvent(event)
