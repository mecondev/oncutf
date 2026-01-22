"""Progress and user interaction ports.

Protocols for reporting progress and getting user input without Qt dependencies.

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

OperationType = Literal[
    "metadata_basic",
    "metadata_extended", 
    "metadata_save",
    "file_loading",
    "hash_calculation",
]


@runtime_checkable
class CursorPort(Protocol):
    """Protocol for cursor management without Qt dependencies."""

    def set_wait_cursor(self) -> None:
        """Set cursor to wait/busy state."""
        ...

    def restore_cursor(self) -> None:
        """Restore cursor to normal state."""
        ...

    def force_restore_cursor(self) -> None:
        """Force restore cursor (emergency cleanup)."""
        ...


class ProgressReporter(Protocol):
    """Protocol for reporting progress without Qt dependencies."""

    def report_progress(self, current: int, total: int, message: str = "") -> None:
        """Report progress update.
        
        Args:
            current: Current item number
            total: Total items
            message: Optional status message
        """
        ...

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled by user."""
        ...


@runtime_checkable
class ProgressDialogPort(Protocol):
    """Protocol for showing progress dialogs without Qt dependencies.
    
    This is a more complex protocol than ProgressReporter - it represents
    a full-featured progress dialog with visual feedback, cancellation,
    and status updates.
    """

    def set_status(self, message: str) -> None:
        """Update status message shown in dialog."""
        ...

    def show(self) -> None:
        """Show the progress dialog."""
        ...

    def close(self) -> None:
        """Close the progress dialog."""
        ...

    def set_progress(self, current: int, total: int) -> None:
        """Update progress indicator.
        
        Args:
            current: Current item number
            total: Total items
        """
        ...

    def set_count(self, current: int, total: int) -> None:
        """Set the current/total count display.
        
        Args:
            current: Current item number
            total: Total items
        """
        ...

    def set_filename(self, filename: str) -> None:
        """Set the filename being processed.
        
        Args:
            filename: Name of file currently being processed
        """
        ...

    def is_cancelled(self) -> bool:
        """Check if user cancelled the operation."""
        ...


class UserDialogPort(Protocol):
    """Protocol for showing dialogs to user without Qt dependencies."""

    def show_info(self, title: str, message: str) -> None:
        """Show information message."""
        ...

    def show_warning(self, title: str, message: str) -> None:
        """Show warning message."""
        ...

    def show_error(self, title: str, message: str) -> None:
        """Show error message."""
        ...

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Ask yes/no question. Returns True for yes, False for no."""
        ...

    def ask_ok_cancel(self, title: str, message: str) -> bool:
        """Ask ok/cancel question. Returns True for ok, False for cancel."""
        ...


class StatusReporter(Protocol):
    """Protocol for reporting status messages."""

    def show_status(self, message: str, timeout: int = 0) -> None:
        """Show status message.
        
        Args:
            message: Status message
            timeout: Timeout in milliseconds (0 = permanent)
        """
        ...
