"""
file_loading_dialog.py

Author: Michael Economou
Date: 2025-05-01

Dialog that shows progress while loading files.
Handles ESC key to cancel loading and shows wait cursor.
Uses UnifiedFileWorker for consistent file loading behavior.
"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from .compact_waiting_widget import CompactWaitingWidget
from core.unified_file_worker import UnifiedFileWorker
from typing import List, Set, Callable
from utils.dialog_utils import setup_dialog_size_and_center
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

class FileLoadingDialog(QDialog):
    """
    Dialog that shows progress while loading files.
    Handles ESC key to cancel loading and shows wait cursor.
    Uses UnifiedFileWorker for consistent file loading behavior.
    """
    def __init__(self, parent=None, on_files_loaded: Callable[[List[str]], None] = None):
        super().__init__(parent)
        self.on_files_loaded = on_files_loaded
        self.worker = None
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
        """Start loading files with the given paths, allowed extensions, and recursive option."""
        logger.info(f"[FileLoadingDialog] Starting to load {len(paths)} paths (recursive={recursive})")

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

        # Start loading with a small delay to ensure UI is ready
        QTimer.singleShot(10, self.worker.start)  # Reduced delay for faster response

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

        # Restore cursor on both parent and dialog
        self._restore_cursors()

        if self.on_files_loaded:
            self.on_files_loaded(files)

        self.accept()

    def _on_worker_finished(self, success: bool):
        """Handle worker completion (success or failure)."""
        logger.debug(f"[FileLoadingDialog] Worker finished (success={success})")

        # Only restore cursors if we haven't already done so
        if not success:
            self._restore_cursors()

    def _restore_cursors(self):
        """Restore normal cursors on both parent and dialog."""
        if self.parent():
            self.parent().setCursor(Qt.ArrowCursor)
        self.setCursor(Qt.ArrowCursor)

    def _on_error(self, error_msg: str):
        """Handle loading error."""
        logger.error(f"[FileLoadingDialog] Error loading files: {error_msg}")

        # Restore cursors
        self._restore_cursors()
        self.waiting_widget.set_status(f"Error: {error_msg}")

        # Keep dialog open to show error for a moment
        # User can press ESC to close

    def keyPressEvent(self, event):
        """Handle ESC key to cancel loading."""
        if event.key() == Qt.Key_Escape:
            if self.worker and self.worker.isRunning():
                logger.info("[FileLoadingDialog] User cancelled loading")

                # Update UI immediately to show cancellation
                self.waiting_widget.set_status("Cancelling...")
                self.waiting_widget.set_filename("Please wait...")
                self.repaint()  # Force immediate UI update

                # Cancel worker
                self.worker.cancel()

                # Restore cursors immediately
                self._restore_cursors()

                # Wait a bit for worker to finish, then close
                QTimer.singleShot(500, self.reject)  # Close after 500ms
            else:
                # No worker running, just close
                self._restore_cursors()
                self.reject()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle dialog close."""
        if self.worker and self.worker.isRunning():
            logger.info("[FileLoadingDialog] Dialog closing, cancelling worker")
            self.worker.cancel()
            self.worker.wait(1000)  # Wait max 1 second

        # Always restore cursors when closing
        self._restore_cursors()
        event.accept()
