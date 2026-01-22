"""Qt adapters for user interaction ports.

Concrete implementations of app/ports user interaction interfaces using Qt.

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget


class QtUserDialogAdapter:
    """Qt implementation of UserDialogPort.
    
    This adapter breaks the core→ui cycle by implementing the port interface
    defined in app/ports/user_interaction.py.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize adapter with optional parent widget.
        
        Args:
            parent: Parent QWidget for dialogs
        """
        self._parent = parent

    def show_info(self, title: str, message: str) -> None:
        """Show information message."""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.information(self._parent, title, message)

    def show_warning(self, title: str, message: str) -> None:
        """Show warning message."""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.warning(self._parent, title, message)

    def show_error(self, title: str, message: str) -> None:
        """Show error message."""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.critical(self._parent, title, message)

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Ask yes/no question. Returns True for yes, False for no."""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        return CustomMessageDialog.question(self._parent, title, message)

    def ask_ok_cancel(self, title: str, message: str) -> bool:
        """Ask ok/cancel question. Returns True for ok, False for cancel."""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        return CustomMessageDialog.question(self._parent, title, message)


class QtStatusReporter:
    """Qt implementation of StatusReporter.
    
    Reports status messages to a QStatusBar.
    """

    def __init__(self, status_bar: object | None = None) -> None:
        """Initialize reporter with optional status bar.
        
        Args:
            status_bar: QStatusBar instance (typed as object to avoid Qt import)
        """
        self._status_bar = status_bar

    def show_status(self, message: str, timeout: int = 0) -> None:
        """Show status message.
        
        Args:
            message: Status message
            timeout: Timeout in milliseconds (0 = permanent)
        """
        if self._status_bar and hasattr(self._status_bar, "showMessage"):
            self._status_bar.showMessage(message, timeout)


class QtCursorAdapter:
    """Qt implementation of CursorPort.
    
    Delegates to utils/ui/cursor_helper.py for actual cursor management.
    This adapter provides a protocol-based interface without Qt dependencies
    in the calling code.
    """

    def set_wait_cursor(self) -> None:
        """Set cursor to wait/busy state."""
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QApplication

        QApplication.setOverrideCursor(Qt.WaitCursor)

    def restore_cursor(self) -> None:
        """Restore cursor to normal state."""
        from PyQt5.QtWidgets import QApplication

        QApplication.restoreOverrideCursor()

    def force_restore_cursor(self) -> None:
        """Force restore cursor (emergency cleanup)."""
        from oncutf.utils.ui.cursor_helper import force_restore_cursor

        force_restore_cursor()


class QtProgressDialogAdapter:
    """Qt implementation of ProgressDialogPort.
    
    Wraps ProgressDialog from utils/ui/progress_dialog.py to provide
    a protocol-based interface without Qt dependencies in core code.
    """

    def __init__(
        self,
        parent: object | None = None,
        operation_type: str = "metadata_basic",
        cancel_callback: object | None = None,
        show_enhanced_info: bool = False,
        is_exit_save: bool = False,
    ) -> None:
        """Initialize adapter with ProgressDialog parameters.
        
        Args:
            parent: Parent QWidget (typed as object to avoid Qt import)
            operation_type: Type of operation (metadata_basic, file_loading, etc.)
            cancel_callback: Callback function for cancellation
            show_enhanced_info: Whether to show enhanced information
            is_exit_save: Whether this is an exit save operation
        """
        from oncutf.utils.ui.progress_dialog import ProgressDialog

        self._dialog = ProgressDialog(
            parent=parent,
            operation_type=operation_type,  # type: ignore[arg-type]
            cancel_callback=cancel_callback,
            show_enhanced_info=show_enhanced_info,
            is_exit_save=is_exit_save,
        )

    def set_status(self, message: str) -> None:
        """Update status message shown in dialog."""
        self._dialog.set_status(message)

    def show(self) -> None:
        """Show the progress dialog with smooth appearance."""
        from oncutf.utils.ui.dialog_utils import show_dialog_smooth

        show_dialog_smooth(self._dialog)

    def close(self) -> None:
        """Close the progress dialog."""
        self._dialog.close()

    def set_progress(self, current: int, total: int) -> None:
        """Update progress indicator."""
        self._dialog.set_progress(current, total)

    def set_count(self, current: int, total: int) -> None:
        """Set the current/total count display."""
        self._dialog.set_count(current, total)

    def set_filename(self, filename: str) -> None:
        """Set the filename being processed."""
        self._dialog.set_filename(filename)

    def is_cancelled(self) -> bool:
        """Check if user cancelled the operation."""
        return self._dialog.is_cancelled()
