"""
progress_dialog.py

Author: Michael Economou
Date: 2025-06-23

Unified progress dialog for all background operations in the oncutf application.
Consolidates MetadataWaitingDialog and FileLoadingDialog functionality.

Features:
- Configurable colors for different operation types
- Proper wait cursor management
- Robust ESC key handling with cancellation
- Support for all operation types (metadata, file loading, hash calculation)
"""

from typing import Callable, Optional

from core.qt_imports import Qt, QDialog, QVBoxLayout, QWidget
from config import (
    EXTENDED_METADATA_BG_COLOR,
    EXTENDED_METADATA_COLOR,
    FAST_METADATA_BG_COLOR,
    FAST_METADATA_COLOR,
    FILE_LOADING_COLOR,
    FILE_LOADING_BG_COLOR,
    HASH_CALCULATION_COLOR,
    HASH_CALCULATION_BG_COLOR,
)
from utils.cursor_helper import force_restore_cursor
from utils.dialog_utils import setup_dialog_size_and_center
from utils.logger_factory import get_cached_logger
from widgets.compact_waiting_widget import CompactWaitingWidget

logger = get_cached_logger(__name__)


class ProgressDialog(QDialog):
    """
    Unified progress dialog for all background operations.

    Supports different operation types with configurable colors:
    - metadata_basic: Fast metadata loading (blue)
    - metadata_extended: Extended metadata loading (orange)
    - file_loading: File loading operations (blue)
    - hash_calculation: Hash/checksum operations (default)
    """

    # Predefined color schemes for different operations
    COLOR_SCHEMES = {
        'metadata_basic': {
            'bar_color': FAST_METADATA_COLOR,
            'bar_bg_color': FAST_METADATA_BG_COLOR
        },
        'metadata_extended': {
            'bar_color': EXTENDED_METADATA_COLOR,
            'bar_bg_color': EXTENDED_METADATA_BG_COLOR
        },
        'file_loading': {
            'bar_color': FILE_LOADING_COLOR,
            'bar_bg_color': FILE_LOADING_BG_COLOR
        },
        'hash_calculation': {
            'bar_color': HASH_CALCULATION_COLOR,
            'bar_bg_color': HASH_CALCULATION_BG_COLOR
        }
    }

    def __init__(self, parent: Optional[QWidget] = None,
                 operation_type: str = 'metadata_basic',
                 cancel_callback: Optional[Callable] = None) -> None:
        """
        Initialize the progress dialog.

        Args:
            parent: Parent widget
            operation_type: Type of operation ('metadata_basic', 'metadata_extended',
                          'file_loading', 'hash_calculation')
            cancel_callback: Function to call when user cancels operation
        """
        super().__init__(parent)
        self.cancel_callback = cancel_callback
        self.operation_type = operation_type
        self._is_cancelling = False

        # Setup the dialog
        self._setup_dialog()
        self._setup_wait_cursor()

        logger.debug(f"[ProgressDialog] Created for operation: {operation_type}")

    def _setup_dialog(self) -> None:
        """Setup the dialog UI and properties."""
        # Frameless dialog
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setModal(True)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Get color scheme for operation type
        color_scheme = self.COLOR_SCHEMES.get(self.operation_type, self.COLOR_SCHEMES['metadata_basic'])

        # Create the waiting widget with appropriate colors
        self.waiting_widget = CompactWaitingWidget(
            parent=self,
            bar_color=color_scheme['bar_color'],
            bar_bg_color=color_scheme['bar_bg_color']
        )

        layout.addWidget(self.waiting_widget)

        # Setup dialog size and centering
        setup_dialog_size_and_center(self, self.waiting_widget)

    def _setup_wait_cursor(self) -> None:
        """Setup wait cursor for the dialog and parent."""
        # Set wait cursor on parent if available
        if self.parent():
            self.parent().setCursor(Qt.WaitCursor)

        # Set wait cursor on the dialog itself
        self.setCursor(Qt.WaitCursor)

        logger.debug("[ProgressDialog] Wait cursor set")

    def _restore_cursors(self) -> None:
        """Restore normal cursors on dialog and parent."""
        # Force cleanup of all override cursors
        force_restore_cursor()

        # Set normal cursor on parent and dialog
        if self.parent():
            self.parent().setCursor(Qt.ArrowCursor)
        self.setCursor(Qt.ArrowCursor)

        logger.debug("[ProgressDialog] Cursors restored")

    def keyPressEvent(self, event) -> None:
        """Handle ESC key for cancellation with improved responsiveness."""
        if event.key() == Qt.Key_Escape and not self._is_cancelling:
            self._handle_cancellation()
        else:
            super().keyPressEvent(event)

    def _handle_cancellation(self) -> None:
        """Handle user cancellation with proper cleanup."""
        if self._is_cancelling:
            return  # Already cancelling

        self._is_cancelling = True
        logger.info(f"[ProgressDialog] User cancelled {self.operation_type} operation")

        # Update UI immediately
        self.waiting_widget.set_status("Cancelling...")
        self.waiting_widget.set_filename("Please wait...")
        self.repaint()  # Force immediate UI update

        # Call cancel callback if provided
        if self.cancel_callback:
            try:
                self.cancel_callback()
            except Exception as e:
                logger.error(f"[ProgressDialog] Error in cancel callback: {e}")

        # Restore cursors
        self._restore_cursors()

        # Close dialog
        self.reject()

    def closeEvent(self, event) -> None:
        """Handle dialog close event with proper cleanup."""
        if not self._is_cancelling:
            self._restore_cursors()
        super().closeEvent(event)

    def accept(self) -> None:
        """Handle dialog acceptance with proper cleanup."""
        self._restore_cursors()
        super().accept()

    def reject(self) -> None:
        """Handle dialog rejection with proper cleanup."""
        if not self._is_cancelling:
            self._restore_cursors()
        super().reject()

    # Delegation methods to waiting widget
    def set_progress(self, value: int, total: int) -> None:
        """Set progress bar value and total."""
        self.waiting_widget.set_progress(value, total)

    def set_filename(self, filename: str) -> None:
        """Set the filename being processed."""
        self.waiting_widget.set_filename(filename)

    def set_status(self, text: str) -> None:
        """Set the status text."""
        self.waiting_widget.set_status(text)

    def set_count(self, current: int, total: int) -> None:
        """Set the current/total count display."""
        self.waiting_widget.set_count(current, total)

    @classmethod
    def create_metadata_dialog(cls, parent: Optional[QWidget] = None,
                             is_extended: bool = False,
                             cancel_callback: Optional[Callable] = None) -> 'ProgressDialog':
        """
        Create a progress dialog for metadata operations.

        Args:
            parent: Parent widget
            is_extended: True for extended metadata, False for basic
            cancel_callback: Function to call when user cancels

        Returns:
            ProgressDialog configured for metadata operations
        """
        operation_type = 'metadata_extended' if is_extended else 'metadata_basic'
        return cls(parent=parent, operation_type=operation_type, cancel_callback=cancel_callback)

    @classmethod
    def create_file_loading_dialog(cls, parent: Optional[QWidget] = None,
                                 cancel_callback: Optional[Callable] = None) -> 'ProgressDialog':
        """
        Create a progress dialog for file loading operations.

        Args:
            parent: Parent widget
            cancel_callback: Function to call when user cancels

        Returns:
            ProgressDialog configured for file loading operations
        """
        return cls(parent=parent, operation_type='file_loading', cancel_callback=cancel_callback)

    @classmethod
    def create_hash_dialog(cls, parent: Optional[QWidget] = None,
                         cancel_callback: Optional[Callable] = None) -> 'ProgressDialog':
        """
        Create a progress dialog for hash/checksum operations.

        Args:
            parent: Parent widget
            cancel_callback: Function to call when user cancels

        Returns:
            ProgressDialog configured for hash operations
        """
        return cls(parent=parent, operation_type='hash_calculation', cancel_callback=cancel_callback)
