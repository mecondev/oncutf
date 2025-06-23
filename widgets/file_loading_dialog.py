"""
file_loading_dialog.py

Author: Michael Economou
Date: 2025-05-01

Dialog that shows progress while loading files with enhanced cancellation.
Uses Timer Manager for better timeout handling and improved ESC responsiveness.
Handles ESC key to cancel loading and shows wait cursor.
Uses UnifiedFileWorker for consistent file loading behavior.
"""

from typing import Callable, List, Set

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout

from core.unified_file_worker import UnifiedFileWorker
from utils.cursor_helper import force_restore_cursor
from utils.dialog_utils import setup_dialog_size_and_center
from utils.logger_factory import get_cached_logger
from utils.timer_manager import TimerPriority, TimerType, get_timer_manager

from .progress_widget import CompactProgressWidget

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

        self.waiting_widget = CompactProgressWidget(
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
        logger.debug(f"[DEBUG] FileLoadingDialog.load_files_with_options called with paths: {paths}")
        logger.debug(f"[DEBUG] FileLoadingDialog allowed_extensions: {allowed_extensions}")
        logger.debug(f"[DEBUG] FileLoadingDialog recursive: {recursive}")

        # Reset cancellation state
        self._is_cancelling = False
        if self._cancellation_timer_id:
            self.timer_manager.cancel(self._cancellation_timer_id)
            self._cancellation_timer_id = None

        # Set wait cursor globally to prevent drag cursors from showing
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Also set wait cursor on both parent and dialog
        if self.parent():
            self.parent().setCursor(Qt.WaitCursor)
        self.setCursor(Qt.WaitCursor)

        # Update UI immediately before starting worker - show animated progress during counting
        self.waiting_widget.set_status("Counting files...")
        self.waiting_widget.set_filename("Scanning directories...")
        self.waiting_widget.set_indeterminate_mode()  # Show animated progress bar during counting phase

        # Force UI update
        self.repaint()

        # Create and setup unified worker
        logger.debug(f"[DEBUG] Creating UnifiedFileWorker...")
        self.worker = UnifiedFileWorker()
        logger.debug(f"[DEBUG] Setting up worker scan with paths: {paths}")
        self.worker.setup_scan(paths, allowed_extensions, recursive)
        logger.debug(f"[DEBUG] Worker setup completed")

        # Connect signals - map unified worker signals to dialog methods
        self.worker.progress_updated.connect(self._update_progress)
        self.worker.file_loaded.connect(self._update_filename)
        self.worker.status_updated.connect(self._update_status)
        self.worker.files_found.connect(self._on_loading_finished)  # files_found -> finished
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished_scanning.connect(self._on_worker_finished)  # Handle worker completion
        logger.debug(f"[DEBUG] All worker signals connected")

        # Start loading immediately - no timer delay needed
        logger.debug(f"[DEBUG] Starting worker immediately...")
        self.worker.start()
        logger.debug(f"[DEBUG] Worker.start() called")

    def _update_progress(self, current: int, total: int):
        """Update progress display."""
        # Switch to determinate mode when we get the first real progress update
        if self.waiting_widget.progress_bar.maximum() == 0:  # Currently in indeterminate mode
            self.waiting_widget.set_determinate_mode()

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

        # Also restore any global override cursors
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

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
        """Handle immediate cancellation with enhanced UX feedback."""
        if self._is_cancelling:
            return  # Already cancelling

        self._is_cancelling = True
        logger.info("[FileLoadingDialog] User cancelled loading - immediate response")

        # Immediate UX feedback: Set progress to 100% and show "Canceling..."
        self.waiting_widget.set_determinate_mode()  # Ensure we're not in indeterminate mode
        self.waiting_widget.set_progress(100, 100)  # Show 100% completion
        self.waiting_widget.set_status("Canceling...")
        self.waiting_widget.set_filename("Stopping file scan...")
        self.repaint()  # Force immediate UI update

        if self.worker and self.worker.isRunning():
            # Cancel worker immediately
            self.worker.cancel()

            # Show cancellation feedback for a brief moment (300ms) before closing
            self._cancellation_timer_id = self.timer_manager.schedule(
                self._finalize_cancellation_with_cleanup,
                delay=300,
                timer_type=TimerType.GENERIC
            )
        else:
            # No worker running, just close immediately after brief feedback
            self._cancellation_timer_id = self.timer_manager.schedule(
                self._finalize_cancellation_with_cleanup,
                delay=200,
                timer_type=TimerType.GENERIC
            )

    def _finalize_cancellation(self):
        """DEPRECATED: No longer used - cancellation is now immediate."""
        pass

    def _finalize_cancellation_with_cleanup(self):
        """Complete the cancellation process after showing UX feedback."""
        # Clear the timer reference
        self._cancellation_timer_id = None

        # Restore cursors
        self._restore_cursors()

        # Close the dialog
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
