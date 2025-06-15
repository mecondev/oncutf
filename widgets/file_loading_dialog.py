"""
file_loading_dialog.py

Author: Michael Economou
Date: 2025-05-01

Dialog that shows progress while loading files with enhanced cancellation.
Uses Timer Manager for better timeout handling and improved ESC responsiveness.
Handles ESC key to cancel loading and shows wait cursor.
Uses UnifiedFileWorker for consistent file loading behavior.
"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from .compact_waiting_widget import CompactWaitingWidget
from core.unified_file_worker import UnifiedFileWorker
from typing import List, Set, Callable
from utils.dialog_utils import setup_dialog_size_and_center
from utils.cursor_helper import force_restore_cursor
from utils.timer_manager import get_timer_manager, TimerType, TimerPriority
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

class FileLoadingDialog(QDialog):
    """
    Dialog that shows progress while loading files with enhanced cancellation.

    Enhanced Features:
    - Timer Manager integration for better timeout handling
    - Improved ESC key responsiveness during both phases
    - Better cursor management with immediate feedback
    - Enhanced cancellation during file loading phase
    """
    def __init__(self, parent=None, on_files_loaded: Callable[[List[str]], None] = None):
        super().__init__(parent)
        self.on_files_loaded = on_files_loaded
        self.worker = None
        self.timer_manager = get_timer_manager()
        self._cancellation_timer_id = None
        self._is_cancelling = False
        self.setup_ui()

    def setup_ui(self):
        # No window title - designed to be compact
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # No margins - let widget handle its own spacing
        layout.setSpacing(0)

        self.waiting_widget = CompactWaitingWidget(
            self,
            bar_color="#64b5f6",  # blue
            bar_bg_color="#0a1a2a"  # darker blue bg
        )

        # Initialize with proper content to avoid empty appearance
        self.waiting_widget.set_status("Preparing to load files...")
        self.waiting_widget.set_progress(0, 100)
        self.waiting_widget.set_filename("Initializing...")

        layout.addWidget(self.waiting_widget)

        # Setup dialog size and centering using utility function
        setup_dialog_size_and_center(self, self.waiting_widget)

    def load_files(self, paths: List[str], allowed_extensions: Set[str]):
        """Start loading files with the given paths and allowed extensions."""
        self.load_files_with_options(paths, allowed_extensions, recursive=True)

    def load_files_with_options(self, paths: List[str], allowed_extensions: Set[str], recursive: bool = True):
        """Start loading files with enhanced cancellation support."""
        logger.info(f"[FileLoadingDialog] Starting to load {len(paths)} paths (recursive={recursive})")

        # Reset cancellation state
        self._is_cancelling = False
        if self._cancellation_timer_id:
            self.timer_manager.cancel(self._cancellation_timer_id)
            self._cancellation_timer_id = None

        # Set wait cursor on both parent and dialog immediately
        if self.parent():
            self.parent().setCursor(Qt.WaitCursor)
        self.setCursor(Qt.WaitCursor)

        # Update UI immediately before starting worker
        self.waiting_widget.set_status("Counting files...")
        self.waiting_widget.set_filename("Scanning directories...")
        self.waiting_widget.set_progress(0, 100)

        # Force UI update
        self.repaint()

        # Create and setup unified worker
        self.worker = UnifiedFileWorker()
        self.worker.setup_scan(paths, allowed_extensions, recursive)

        # Connect signals - map unified worker signals to dialog methods
        self.worker.progress_updated.connect(self._update_progress)
        self.worker.file_loaded.connect(self._update_filename)
        self.worker.status_updated.connect(self._update_status)
        self.worker.files_found.connect(self._on_loading_finished)  # files_found -> finished
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished_scanning.connect(self._on_worker_finished)  # Handle worker completion

        # Start loading with minimal delay using Timer Manager
        self.timer_manager.schedule(
            callback=self.worker.start,
            priority=TimerPriority.IMMEDIATE,
            timer_type=TimerType.UI_UPDATE,
            timer_id="file_loading_start"
        )

    def _update_progress(self, current: int, total: int):
        """Update progress display."""
        self.waiting_widget.set_progress(current, total)
        logger.debug(f"[FileLoadingDialog] Progress: {current}/{total}")

    def _update_filename(self, filename: str):
        """Update current filename display."""
        self.waiting_widget.set_filename(filename)

    def _update_status(self, status: str):
        """Update status message."""
        self.waiting_widget.set_status(status)
        logger.debug(f"[FileLoadingDialog] Status: {status}")

    def _on_loading_finished(self, files: List[str]):
        """Handle loading completion."""
        logger.info(f"[FileLoadingDialog] Loading finished with {len(files)} files")

        # Cancel any pending cancellation timer
        if self._cancellation_timer_id:
            self.timer_manager.cancel(self._cancellation_timer_id)
            self._cancellation_timer_id = None

        # Restore cursor on both parent and dialog
        self._restore_cursors()

        if self.on_files_loaded and not self._is_cancelling:
            self.on_files_loaded(files)

        self.accept()

    def _on_worker_finished(self, success: bool):
        """Handle worker completion (success or failure)."""
        logger.debug(f"[FileLoadingDialog] Worker finished (success={success})")

        # Only restore cursors if we haven't already done so
        if not success and not self._is_cancelling:
            self._restore_cursors()

    def _restore_cursors(self):
        """Restore normal cursors on both parent and dialog."""
        # Force cleanup of all override cursors (including drag cursors)
        force_restore_cursor()

        # Set normal cursor on parent and dialog
        if self.parent():
            self.parent().setCursor(Qt.ArrowCursor)
        self.setCursor(Qt.ArrowCursor)

    def _on_error(self, error_msg: str):
        """Handle loading error."""
        logger.error(f"[FileLoadingDialog] Error loading files: {error_msg}")

        # Cancel any pending cancellation timer
        if self._cancellation_timer_id:
            self.timer_manager.cancel(self._cancellation_timer_id)
            self._cancellation_timer_id = None

        # Restore cursors
        self._restore_cursors()
        self.waiting_widget.set_status(f"Error: {error_msg}")

        # Keep dialog open to show error for a moment
        # User can press ESC to close

    def _handle_cancellation_immediate(self):
        """Handle immediate cancellation with enhanced responsiveness."""
        if self._is_cancelling:
            return  # Already cancelling

        self._is_cancelling = True
        logger.info("[FileLoadingDialog] User cancelled loading - immediate response")

        if self.worker and self.worker.isRunning():
            # Cancel worker immediately
            self.worker.cancel()

            # Update UI immediately to show cancellation
            self.waiting_widget.set_status("Cancelling...")
            self.waiting_widget.set_filename("Please wait...")
            self.repaint()  # Force immediate UI update

            # Restore cursors immediately
            self._restore_cursors()

            # Schedule dialog close with very short delay using Timer Manager
            self._cancellation_timer_id = self.timer_manager.schedule(
                callback=lambda: self._finalize_cancellation(),
                priority=TimerPriority.HIGH,  # High priority for immediate response
                timer_type=TimerType.UI_UPDATE,
                timer_id="cancellation_finalize"
            )
        else:
            # No worker running, just close immediately
            self._restore_cursors()
            self.reject()

    def _finalize_cancellation(self):
        """Finalize cancellation and close dialog."""
        logger.debug("[FileLoadingDialog] Finalizing cancellation")

        # Force worker to stop if still running
        if self.worker and self.worker.isRunning():
            self.worker.wait(50)  # Very brief wait

        # Clear timer reference
        self._cancellation_timer_id = None

        # Close dialog
        self.reject()

    def keyPressEvent(self, event):
        """Handle ESC key with enhanced cancellation using Timer Manager."""
        if event.key() == Qt.Key_Escape:
            self._handle_cancellation_immediate()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle dialog close with proper cleanup."""
        # Cancel any pending timers
        if self._cancellation_timer_id:
            self.timer_manager.cancel(self._cancellation_timer_id)
            self._cancellation_timer_id = None

        if self.worker and self.worker.isRunning():
            logger.info("[FileLoadingDialog] Dialog closing, cancelling worker")
            self.worker.cancel()
            self.worker.wait(500)  # Wait reasonable time for cleanup

        # Always restore cursors when closing
        self._restore_cursors()
        event.accept()
