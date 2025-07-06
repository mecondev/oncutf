"""
Module: metadata_waiting_dialog.py

Author: Michael Economou
Date: 2025-07-06

operation_dialog.py
Frameless waiting dialog for background operations (metadata, hash, file loading).
Provides a clean, minimal UI for displaying operation progress.
Note: This is the legacy dialog - new code should use utils.progress_dialog.ProgressDialog
"""
from typing import Callable, Optional

from core.qt_imports import Qt, QDialog, QVBoxLayout, QWidget

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


class OperationDialog(QDialog):
    """
    QDialog wrapper for background operations (legacy).

    This dialog:
    - Has no title bar (frameless)
    - Is styled via QSS using standard QWidget rules
    - Hosts a compact waiting UI to display operation progress
    - Supports ESC key cancellation

    Note: For new code, use utils.progress_dialog.ProgressDialog instead
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
        """Handle ESC key to cancel operation."""
        if event.key() == Qt.Key_Escape: # type: ignore
            logger.info("[OperationDialog] User cancelled operation")
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


# Backward compatibility alias
MetadataWaitingDialog = OperationDialog
