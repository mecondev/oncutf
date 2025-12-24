"""Module: cursor_helper.py

Author: Michael Economou
Date: 2025-05-31

cursor_helper.py
Utility functions for cursor management across the application.
Provides safe cursor operations with emergency cleanup capabilities.
"""

import contextlib
import traceback

from oncutf.core.pyqt_imports import QApplication, Qt
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@contextlib.contextmanager
def wait_cursor(restore_after: bool = True):
    """Context manager that sets the cursor to wait and restores it after.
    Logs the file, line number, and function from where it was called.
    The logged path is shortened to start from 'oncutf/' for clarity.

    Parameters
    ----------
        restore_after: If True, the cursor will be restored after the context block.
                       If False, the cursor will remain as wait cursor.

    """
    QApplication.setOverrideCursor(Qt.WaitCursor)

    # Get full stack and reverse it (top frame is last)
    stack = traceback.extract_stack()
    # Remove the last frame (inside wait_cursor itself)
    trimmed_stack = stack[:-1]

    # Find last frame inside our project path ("oncutf/")
    caller_line = next((f for f in reversed(trimmed_stack) if "oncutf/" in f.filename), None)

    if caller_line:
        short_path = caller_line.filename[caller_line.filename.find("oncutf/") :]
        logger.debug(
            "[Cursor] Wait cursor activated. Called from: %s, line %d, in %s()",
            short_path,
            caller_line.lineno,
            caller_line.name,
            extra={"dev_only": True},
        )
    else:
        logger.debug(
            "[Cursor] Wait cursor activated. Caller path not in oncutf/", extra={"dev_only": True}
        )

    try:
        yield
    finally:
        if restore_after:
            QApplication.restoreOverrideCursor()
            logger.debug("[Cursor] Wait cursor restored.", extra={"dev_only": True})
        else:
            logger.debug(
                "[Cursor] Wait cursor NOT restored (as requested).", extra={"dev_only": True}
            )


def emergency_cursor_cleanup() -> int:
    """Emergency cleanup for stuck cursors.

    Returns:
        Number of cursors cleaned up

    """
    cursor_count = 0
    while QApplication.overrideCursor() and cursor_count < 10:
        QApplication.restoreOverrideCursor()
        cursor_count += 1

    if cursor_count > 0:
        logger.debug(
            "[Cursor] Emergency cleanup: Removed %d stuck cursors",
            cursor_count,
            extra={"dev_only": True},
        )

    return cursor_count


def force_restore_cursor() -> None:
    """Force restoration of cursor to default state.
    Removes all override cursors without limit checking.
    """
    count = 0
    while QApplication.overrideCursor():
        QApplication.restoreOverrideCursor()
        count += 1
        if count > 20:  # Safety break
            logger.warning(
                "[Cursor] Force restore: Stopped after %d cursors (possible infinite loop)",
                count,
            )
            break

    if count > 0:
        logger.debug("[Cursor] Force restore: Removed %d cursors", count, extra={"dev_only": True})


def get_current_cursor_info() -> str | None:
    """Get information about the current override cursor.

    Returns:
        String description of current cursor or None if no override

    """
    current = QApplication.overrideCursor()
    if not current:
        return None

    shape = current.shape()
    cursor_names = {
        Qt.ArrowCursor: "Arrow",
        Qt.WaitCursor: "Wait",
        Qt.BusyCursor: "Busy",
        Qt.DragMoveCursor: "DragMove",
        Qt.DragCopyCursor: "DragCopy",
        Qt.DragLinkCursor: "DragLink",
        Qt.ClosedHandCursor: "ClosedHand",
        Qt.OpenHandCursor: "OpenHand",
    }

    return cursor_names.get(shape, f"Unknown({shape})")


def is_drag_cursor_active() -> bool:
    """Check if a drag-related cursor is currently active.

    Returns:
        True if a drag cursor is active

    """
    current = QApplication.overrideCursor()
    if not current:
        return False

    shape = current.shape()
    drag_cursors = [Qt.DragMoveCursor, Qt.DragCopyCursor, Qt.DragLinkCursor, Qt.ClosedHandCursor]

    return shape in drag_cursors
