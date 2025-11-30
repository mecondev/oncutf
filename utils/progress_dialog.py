"""
Module: progress_dialog.py

Author: Michael Economou
Date: 2025-06-01

progress_dialog.py
Unified progress dialog for all background operations in the oncutf application.
Consolidates MetadataWaitingDialog and FileLoadingDialog functionality.
Features:
- Configurable colors for different operation types
- Proper wait cursor management
- Robust ESC key handling with cancellation
- Support for all operation types (metadata, file loading, hash calculation)
"""

from collections.abc import Callable

from config import (
    EXTENDED_METADATA_BG_COLOR,
    EXTENDED_METADATA_COLOR,
    FAST_METADATA_BG_COLOR,
    FAST_METADATA_COLOR,
    FILE_LOADING_BG_COLOR,
    FILE_LOADING_COLOR,
    HASH_CALCULATION_BG_COLOR,
    HASH_CALCULATION_COLOR,
    SAVE_BG_COLOR,
    SAVE_COLOR,
)
from core.pyqt_imports import QDialog, Qt, QVBoxLayout, QWidget
from utils.cursor_helper import force_restore_cursor
from utils.dialog_utils import setup_dialog_size_and_center
from utils.logger_factory import get_cached_logger
from widgets.progress_widget import ProgressWidget

logger = get_cached_logger(__name__)


class ProgressDialog(QDialog):
    """
    Unified progress dialog for all background operations.

    Supports different operation types with configurable colors:
    - metadata_basic: Fast metadata loading (blue)
    - metadata_extended: Extended metadata loading (orange)
    - metadata_save: Metadata save operations (blue)
    - file_loading: File loading operations (blue)
    - hash_calculation: Hash/checksum operations (default)
    """

    # Predefined color schemes for different operations
    COLOR_SCHEMES = {
        "metadata_basic": {
            "bar_color": FAST_METADATA_COLOR,
            "bar_bg_color": FAST_METADATA_BG_COLOR,
        },
        "metadata_extended": {
            "bar_color": EXTENDED_METADATA_COLOR,
            "bar_bg_color": EXTENDED_METADATA_BG_COLOR,
        },
        "metadata_save": {
            "bar_color": SAVE_COLOR,
            "bar_bg_color": SAVE_BG_COLOR,
        },
        "file_loading": {"bar_color": FILE_LOADING_COLOR, "bar_bg_color": FILE_LOADING_BG_COLOR},
        "hash_calculation": {
            "bar_color": HASH_CALCULATION_COLOR,
            "bar_bg_color": HASH_CALCULATION_BG_COLOR,
        },
    }

    def __init__(
        self,
        parent: QWidget | None = None,
        operation_type: str = "metadata_basic",
        cancel_callback: Callable | None = None,
        show_enhanced_info: bool = True,
        is_exit_save: bool = False,
    ) -> None:
        """
        Initialize the progress dialog.

        Args:
            parent: Parent widget
            operation_type: Type of operation ('metadata_basic', 'metadata_extended',
                          'metadata_save', 'file_loading', 'hash_calculation')
            cancel_callback: Function to call when user cancels operation
            show_enhanced_info: Whether to show enhanced size/time tracking
            is_exit_save: If True, ESC is always blocked (save on exit scenario)
        """
        super().__init__(parent)
        self.cancel_callback = cancel_callback
        self.operation_type = operation_type
        self.show_enhanced_info = show_enhanced_info
        self._is_cancelling = False
        self.is_exit_save = is_exit_save

        # Setup the dialog
        self._setup_dialog()
        self._setup_wait_cursor()

        logger.debug(
            f"[ProgressDialog] Created for operation: {operation_type} (enhanced: {show_enhanced_info}, exit_save: {is_exit_save})"
        )

    def _setup_dialog(self) -> None:
        """Setup the dialog UI and properties."""
        # Frameless dialog
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)  # type: ignore
        self.setAttribute(Qt.WA_TranslucentBackground, False)  # type: ignore
        self.setModal(True)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Get color scheme for operation type
        color_scheme = self.COLOR_SCHEMES.get(
            self.operation_type, self.COLOR_SCHEMES["metadata_basic"]
        )

        # Create the unified progress widget
        self.waiting_widget = ProgressWidget(
            parent=self,
            bar_color=color_scheme["bar_color"],
            bar_bg_color=color_scheme["bar_bg_color"],
            show_size_info=self.show_enhanced_info,
            show_time_info=self.show_enhanced_info,
            fixed_width=400,  # Original compact width
        )

        layout.addWidget(self.waiting_widget)

        # Setup dialog size and centering
        setup_dialog_size_and_center(self, self.waiting_widget)

    def _setup_wait_cursor(self) -> None:
        """Setup wait cursor for the parent window only, not the dialog."""
        # Set wait cursor on parent if available (main window)
        if self.parent():
            self.parent().setCursor(Qt.WaitCursor)  # type: ignore

        # Set normal cursor on the dialog itself to avoid wait cursor on dialog
        self.setCursor(Qt.ArrowCursor)  # type: ignore

        logger.debug("[ProgressDialog] Wait cursor set on parent, normal cursor on dialog")

    def _restore_cursors(self) -> None:
        """Restore normal cursors on parent window and dialog."""
        # Force cleanup of all override cursors
        force_restore_cursor()

        # Set normal cursor on parent (main window) and dialog
        if self.parent():
            self.parent().setCursor(Qt.ArrowCursor)  # type: ignore
        self.setCursor(Qt.ArrowCursor)  # type: ignore

        logger.debug("[ProgressDialog] Cursors restored on parent and dialog")

    def keyPressEvent(self, event) -> None:
        """Handle ESC key for cancellation with improved responsiveness and save protection."""
        if event.key() == Qt.Key_Escape and not self._is_cancelling:  # type: ignore
            # Check if ESC should be blocked for this operation
            if self._should_block_esc():
                logger.debug(
                    f"[ProgressDialog] ESC blocked for {self.operation_type} (exit_save: {self.is_exit_save})"
                )
                event.ignore()
                return

            self._handle_cancellation()
        else:
            super().keyPressEvent(event)

    def _should_block_esc(self) -> bool:
        """Determine if ESC should be blocked based on operation type and config."""
        # Always block ESC for exit saves (critical data safety)
        if self.is_exit_save:
            return True

        # For save operations, check config flag
        if self.operation_type == "metadata_save":
            from config import SAVE_OPERATION_SETTINGS

            allow_cancel = SAVE_OPERATION_SETTINGS.get("ALLOW_CANCEL_NORMAL_SAVE", False)
            return not allow_cancel  # Block if NOT allowed

        # Allow ESC for non-save operations (metadata loading, hash calc, etc.)
        return False

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

        # Clean up progress widget timer to prevent orphaned timers
        if hasattr(self.waiting_widget, "reset"):
            self.waiting_widget.reset()

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

    # Enhanced progress methods (only available with enhanced widget)
    def start_progress_tracking(self, total_size: int = 0) -> None:
        """Start progress tracking with optional total size."""
        if hasattr(self.waiting_widget, "start_progress_tracking"):
            self.waiting_widget.start_progress_tracking(total_size)
            logger.debug(f"[ProgressDialog] Started progress tracking (total_size: {total_size})")

    def update_progress_with_size(self, current: int, total: int, current_size: int = 0) -> None:
        """Update progress with size tracking."""
        if hasattr(self.waiting_widget, "update_progress_with_size"):
            self.waiting_widget.update_progress_with_size(current, total, current_size)
        else:
            # Fallback to standard progress update
            self.set_progress(current, total)

    def set_size_info(self, processed_size: int, total_size: int = 0) -> None:
        """Set size information manually."""
        if hasattr(self.waiting_widget, "set_size_info"):
            self.waiting_widget.set_size_info(processed_size, total_size)

    def set_time_info(self, elapsed: float, estimated_total: float | None = None) -> None:
        """Set time information manually."""
        if hasattr(self.waiting_widget, "set_time_info"):
            self.waiting_widget.set_time_info(elapsed, estimated_total)  # type: ignore

    def update_progress(
        self,
        file_count: int = 0,
        total_files: int = 0,
        processed_bytes: int = 0,
        total_bytes: int = 0,
    ) -> None:
        """
        Unified method to update progress regardless of mode.

        This method automatically selects the appropriate progress calculation
        based on the progress widget's current mode setting.

        Args:
            file_count: Current number of files processed
            total_files: Total number of files to process
            processed_bytes: Current bytes processed (cumulative)
            total_bytes: Total bytes to process (optional, uses stored value if 0)
        """
        if hasattr(self.waiting_widget, "update_progress"):
            self.waiting_widget.update_progress(
                file_count, total_files, processed_bytes, total_bytes
            )
        else:
            # Fallback to standard progress update
            if total_files > 0:
                self.set_progress(file_count, total_files)

    def get_progress_summary(self) -> dict:
        """Get comprehensive progress summary (enhanced widget only)."""
        if hasattr(self.waiting_widget, "get_progress_summary"):
            return self.waiting_widget.get_progress_summary()
        return {}

    @classmethod
    def create_metadata_dialog(
        cls,
        parent: QWidget | None = None,
        is_extended: bool = False,
        cancel_callback: Callable | None = None,
        show_enhanced_info: bool = True,
        use_size_based_progress: bool = True,
    ) -> "ProgressDialog":
        """
        Create a progress dialog for metadata operations.

        Args:
            parent: Parent widget
            is_extended: True for extended metadata, False for basic
            cancel_callback: Function to call when user cancels
            show_enhanced_info: Whether to show enhanced size/time tracking
            use_size_based_progress: Whether to use size-based progress bar (recommended for consistency)

        Returns:
            ProgressDialog configured for metadata operations with optional size-based progress
        """
        operation_type = "metadata_extended" if is_extended else "metadata_basic"
        dialog = cls(
            parent=parent,
            operation_type=operation_type,
            cancel_callback=cancel_callback,
            show_enhanced_info=show_enhanced_info,
        )

        # If size-based progress is requested, update the progress widget mode
        if use_size_based_progress and hasattr(dialog.waiting_widget, "set_progress_mode"):
            dialog.waiting_widget.set_progress_mode("size")
            logger.debug(
                f"[ProgressDialog] Metadata dialog configured with size-based progress (extended: {is_extended})"
            )

        return dialog

    @classmethod
    def create_file_loading_dialog(
        cls,
        parent: QWidget | None = None,
        cancel_callback: Callable | None = None,
        show_enhanced_info: bool = True,
    ) -> "ProgressDialog":
        """
        Create a progress dialog for file loading operations.

        Args:
            parent: Parent widget
            cancel_callback: Function to call when user cancels
            show_enhanced_info: Whether to show enhanced size/time tracking

        Returns:
            ProgressDialog configured for file loading operations
        """
        return cls(
            parent=parent,
            operation_type="file_loading",
            cancel_callback=cancel_callback,
            show_enhanced_info=show_enhanced_info,
        )

    @classmethod
    def create_hash_dialog(
        cls,
        parent: QWidget | None = None,
        cancel_callback: Callable | None = None,
        show_enhanced_info: bool = True,
        use_size_based_progress: bool = True,
    ) -> "ProgressDialog":
        """
        Create a progress dialog for hash/checksum operations.

        Args:
            parent: Parent widget
            cancel_callback: Function to call when user cancels
            show_enhanced_info: Whether to show enhanced size/time tracking
            use_size_based_progress: Whether to use size-based progress bar (recommended for hash operations)

        Returns:
            ProgressDialog configured for hash operations with optional size-based progress
        """
        dialog = cls(
            parent=parent,
            operation_type="hash_calculation",
            cancel_callback=cancel_callback,
            show_enhanced_info=show_enhanced_info,
        )

        # If size-based progress is requested, update the progress widget mode
        if use_size_based_progress and hasattr(dialog.waiting_widget, "set_progress_mode"):
            dialog.waiting_widget.set_progress_mode("size")
            logger.debug("[ProgressDialog] Hash dialog configured with size-based progress")

        return dialog
