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
        self.waiting_widget = CompactWaitingWidget(self)
        layout.addWidget(self.waiting_widget)

        self.setFixedSize(300, 150)

    def load_files(self, paths: List[str], allowed_extensions: Set[str]):
        """Start loading files with the given paths and allowed extensions."""
        self.worker = FileLoadingWorker(paths, allowed_extensions)

        # Connect signals
        self.worker.progress_updated.connect(self.waiting_widget.set_progress)
        self.worker.file_loaded.connect(self.waiting_widget.set_filename)
        self.worker.status_updated.connect(self.waiting_widget.set_status)
        self.worker.finished_loading.connect(self._on_loading_finished)
        self.worker.error_occurred.connect(self._on_error)

        # Show wait cursor
        self.setCursor(Qt.WaitCursor)

        # Start loading
        self.worker.start()

    def _on_loading_finished(self, files: List[str]):
        """Handle loading completion."""
        self.setCursor(Qt.ArrowCursor)
        if self.on_files_loaded:
            self.on_files_loaded(files)
        self.accept()

    def _on_error(self, error_msg: str):
        """Handle loading error."""
        logger.error(f"Error loading files: {error_msg}")
        self.setCursor(Qt.ArrowCursor)
        self.waiting_widget.set_status(f"Error: {error_msg}")
        # Keep dialog open to show error

    def keyPressEvent(self, event):
        """Handle ESC key to cancel loading."""
        if event.key() == Qt.Key_Escape:
            if self.worker and self.worker.isRunning():
                self.worker.cancel()
                self.waiting_widget.set_status("Cancelling...")
            else:
                self.reject()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle dialog close."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            event.ignore()
        else:
            event.accept()
