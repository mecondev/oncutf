"""
metadata_waiting_dialog.py

Author: Michael Economou
Date: 2025-05-01

Frameless waiting dialog for metadata extraction operations.
Provides a clean, minimal UI for displaying metadata loading progress.
"""

from typing import Callable, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget

from config import (
    EXTENDED_METADATA_BG_COLOR,
    EXTENDED_METADATA_COLOR,
    FAST_METADATA_BG_COLOR,
    FAST_METADATA_COLOR,
)
from utils.dialog_utils import setup_dialog_size_and_center
from utils.logger_factory import get_cached_logger
from widgets.progress_widget import ProgressWidget

logger = get_cached_logger(__name__)


class MetadataWaitingDialog(QDialog):
    """
    QDialog wrapper that contains a CompactWaitingWidget.

    This dialog:
    - Has no title bar (frameless)
    - Is styled via QSS using standard QWidget rules
    - Hosts a compact waiting UI to display metadata reading progress
    - Supports ESC key cancellation
    """
    def __init__(self, parent: Optional[QWidget] = None, is_extended: bool = False,
                 cancel_callback: Optional[Callable] = None) -> None:
        super().__init__(parent)
        self.cancel_callback = cancel_callback

        # Frameless and styled externally
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint) # type: ignore
        self.setAttribute(Qt.WA_TranslucentBackground, False) # type: ignore
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # CompactWaitingWidget
        # Use the is_extended parameter passed to the constructor
        if is_extended:
            bar_color = EXTENDED_METADATA_COLOR
            bar_bg_color = EXTENDED_METADATA_BG_COLOR
        else:
            bar_color = FAST_METADATA_COLOR
            bar_bg_color = FAST_METADATA_BG_COLOR
        self.waiting_widget = ProgressWidget(
            parent=self,
            bar_color=bar_color,
            bar_bg_color=bar_bg_color,
            show_size_info=False,
            show_time_info=False,
            fixed_width=400
        )

        layout.addWidget(self.waiting_widget)

        self.setLayout(layout)

        # Setup dialog size and centering using utility function
        setup_dialog_size_and_center(self, self.waiting_widget)

    def keyPressEvent(self, event):
        """Handle ESC key to cancel metadata loading."""
        if event.key() == Qt.Key_Escape: # type: ignore
            logger.info("[MetadataWaitingDialog] User cancelled metadata loading")
            self.waiting_widget.set_status("Cancelling...")

            # Call the cancel callback if provided
            if self.cancel_callback:
                self.cancel_callback()

            self.reject()
        else:
            super().keyPressEvent(event)

    def set_progress(self, value: int, total: int) -> None:
        """Set progress bar value and total."""
        self.waiting_widget.set_progress(value, total)

    def set_filename(self, filename: str) -> None:
        """Set the filename being processed."""
        self.waiting_widget.set_filename(filename)

    def set_status(self, text: str) -> None:
        """Set the status text."""
        self.waiting_widget.set_status(text)
