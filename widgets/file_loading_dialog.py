"""
file_loading_dialog.py

Author: Michael Economou
Date: 2025-06-14

Frameless waiting dialog for file loading operations.
Provides a clean, minimal UI for displaying file scanning progress with cancellation support.
"""

from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget

from widgets.compact_waiting_widget import CompactWaitingWidget
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileLoadingDialog(QDialog):
    """
    QDialog wrapper for file loading operations with cancellation support.

    This dialog:
    - Has no title bar (frameless)
    - Supports Esc key cancellation
    - Hosts a compact waiting UI to display file scanning progress
    - Emits cancelled signal when user presses Esc
    """

    # Signals
    cancelled = pyqtSignal()  # Emitted when user cancels with Esc

    def __init__(self, parent: Optional[QWidget] = None, operation_text: str = "Loading files...") -> None:
        super().__init__(parent)

        # Frameless and styled externally
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # CompactWaitingWidget with file loading colors
        self.waiting_widget = CompactWaitingWidget(
            self,
            bar_color="#4CAF50",  # Green for file operations
            bar_bg_color="#E8F5E8"  # Light green background
        )

        # Set initial status
        self.waiting_widget.set_status(operation_text)

        layout.addWidget(self.waiting_widget)
        self.setLayout(layout)

        logger.debug(f"[FileLoadingDialog] Created with operation: {operation_text}")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events, especially Esc for cancellation."""
        if event.key() == Qt.Key_Escape:
            logger.debug("[FileLoadingDialog] Esc key pressed - emitting cancelled signal")
            self.cancelled.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def set_progress(self, current: int, total: int) -> None:
        """Set progress bar value and total."""
        self.waiting_widget.set_progress(current, total)

    def set_filename(self, filename: str) -> None:
        """Set the filename being processed."""
        self.waiting_widget.set_filename(filename)

    def set_status(self, text: str) -> None:
        """Set the status text."""
        self.waiting_widget.set_status(text)

    def update_text(self, text: str) -> None:
        """Update the status text (alias for set_status for compatibility)."""
        self.set_status(text)
