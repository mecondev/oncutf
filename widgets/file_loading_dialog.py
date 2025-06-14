"""
file_loading_dialog.py

Author: Michael Economou
Date: 2025-05-01

Dialog that shows progress while loading files.
Handles ESC key to cancel loading and shows wait cursor.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from .compact_waiting_widget import CompactWaitingWidget
from .file_loading_worker import FileLoadingWorker
from typing import List, Set, Callable
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

class FileLoadingDialog(QDialog):
    """
    Dialog that shows progress while loading files.
    Handles ESC key to cancel loading and shows wait cursor.
    """
    def __init__(self, parent=None, on_files_loaded: Callable[[List[str]], None] = None):
        super().__init__(parent)
        self.on_files_loaded = on_files_loaded
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Loading Files")
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.waiting_widget = CompactWaitingWidget(
            self,
            bar_color="#64b5f6",  # pal blue
            bar_bg_color="#0a1a2a"  # darker blue bg
        )
        layout.addWidget(self.waiting_widget)

        self.setFixedSize(300, 150)

    def load_files(self, paths: List[str], allowed_extensions: Set[str]):
        """Start loading files with the given paths and allowed extensions."""
        logger.info(f"[FileLoadingDialog] Starting to load {len(paths)} paths")

        self.worker = FileLoadingWorker(paths, allowed_extensions)

        # Connect signals
        self.worker.progress_updated.connect(self._update_progress)
        self.worker.file_loaded.connect(self._update_filename)
        self.worker.status_updated.connect(self._update_status)
        self.worker.finished_loading.connect(self._on_loading_finished)
        self.worker.error_occurred.connect(self._on_error)

        # Show wait cursor
        self.setCursor(Qt.WaitCursor)

        # Initialize UI
        self.waiting_widget.set_status("Initializing...")
        self.waiting_widget.set_progress(0, 100)

        # Start loading
        self.worker.start()

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

        self.setCursor(Qt.ArrowCursor)

        if self.on_files_loaded:
            self.on_files_loaded(files)

        self.accept()

    def _on_error(self, error_msg: str):
        """Handle loading error."""
        logger.error(f"[FileLoadingDialog] Error loading files: {error_msg}")

        self.setCursor(Qt.ArrowCursor)
        self.waiting_widget.set_status(f"Error: {error_msg}")

        # Keep dialog open to show error for a moment
        # User can press ESC to close

    def keyPressEvent(self, event):
        """Handle ESC key to cancel loading."""
        if event.key() == Qt.Key_Escape:
            if self.worker and self.worker.isRunning():
                logger.info("[FileLoadingDialog] User cancelled loading")
                self.worker.cancel()
                self.waiting_widget.set_status("Cancelling...")
                self.setCursor(Qt.ArrowCursor)
                # Wait a bit for worker to finish
                self.worker.wait(1000)  # Wait max 1 second
                self.reject()
            else:
                self.reject()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle dialog close."""
        if self.worker and self.worker.isRunning():
            logger.info("[FileLoadingDialog] Dialog closing, cancelling worker")
            self.worker.cancel()
            self.worker.wait(1000)  # Wait max 1 second

        self.setCursor(Qt.ArrowCursor)
        event.accept()
