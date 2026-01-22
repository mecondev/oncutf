"""Active dialogs service - query running dialogs without direct UI dependencies.

Author: Michael Economou
Date: 2026-01-22

Provides facade for querying active dialogs in the application, allowing core
modules to check dialog state without direct coupling to UI classes.

Part of Phase A edge cases cleanup (250121_summary.md).

Usage:
    from oncutf.app.services.active_dialogs import has_active_progress_dialogs

    if has_active_progress_dialogs():
        # Don't interrupt if progress dialog is handling user input
        return
"""


def has_active_progress_dialogs() -> bool:
    """Check if any ProgressDialog instances are currently active and visible.

    Facade for checking top-level widgets without direct ProgressDialog import.

    Returns:
        True if at least one ProgressDialog is visible, False otherwise.
    """
    from oncutf.core.pyqt_imports import QApplication
    from oncutf.utils.ui.progress_dialog import ProgressDialog

    active_dialogs = [
        w
        for w in QApplication.topLevelWidgets()
        if isinstance(w, ProgressDialog) and w.isVisible()
    ]

    return len(active_dialogs) > 0
