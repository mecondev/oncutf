"""User interaction service - Application layer facade.

Provides Qt-independent functions for core modules to show dialogs,
progress indicators, and status messages. Delegates to UserDialogPort
implementations registered in ApplicationContext.

This module breaks core→ui dependency cycles by inverting control:
- core/ imports this (app layer, no Qt)
- ui/ provides concrete implementations via ports

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget


def show_info_message(parent: QWidget | None, title: str, message: str) -> None:
    """Show information dialog using registered adapter.

    Args:
        parent: Parent widget (may be None)
        title: Dialog title
        message: Message to display

    Note:
        This function is a bridge - core modules can call it without
        importing Qt directly. The actual dialog is shown by the adapter
        registered in ApplicationContext.
    """
    from oncutf.core.application_context import ApplicationContext

    ctx = ApplicationContext.get_instance()
    if ctx.has_manager("user_dialog"):
        adapter = ctx.get_manager("user_dialog")
        adapter.show_info(title, message)
    else:
        # Fallback: direct Qt import (legacy behavior)
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog
        if parent is not None:
            CustomMessageDialog.information(parent, title, message)
        else:
            # If no parent, use QApplication.activeWindow() or create temporary parent
            from oncutf.core.pyqt_imports import QApplication
            active_parent = QApplication.activeWindow()
            if active_parent:
                CustomMessageDialog.information(active_parent, title, message)


def show_error_message(parent: QWidget | None, title: str, message: str) -> None:
    """Show error dialog using registered adapter.

    Args:
        parent: Parent widget (may be None)
        title: Dialog title
        message: Error message to display
    """
    from oncutf.core.application_context import ApplicationContext

    ctx = ApplicationContext.get_instance()
    if ctx.has_manager("user_dialog"):
        adapter = ctx.get_manager("user_dialog")
        adapter.show_error(title, message)
    else:
        # Fallback: direct Qt import (legacy behavior)
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog
        if parent is not None:
            CustomMessageDialog.information(parent, title, message)
        else:
            from oncutf.core.pyqt_imports import QApplication
            active_parent = QApplication.activeWindow()
            if active_parent:
                CustomMessageDialog.information(active_parent, title, message)


def show_warning_message(parent: QWidget | None, title: str, message: str) -> None:
    """Show warning dialog using registered adapter.

    Args:
        parent: Parent widget (may be None)
        title: Dialog title
        message: Warning message to display
    """
    from oncutf.core.application_context import ApplicationContext

    ctx = ApplicationContext.get_instance()
    if ctx.has_manager("user_dialog"):
        adapter = ctx.get_manager("user_dialog")
        adapter.show_warning(title, message)
    else:
        # Fallback: direct Qt import (legacy behavior)
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog
        if parent is not None:
            CustomMessageDialog.information(parent, title, message)
        else:
            from oncutf.core.pyqt_imports import QApplication
            active_parent = QApplication.activeWindow()
            if active_parent:
                CustomMessageDialog.information(active_parent, title, message)


def show_question_message(parent: QWidget | None, title: str, message: str) -> bool:
    """Show yes/no question dialog using registered adapter.

    Args:
        parent: Parent widget (may be None)
        title: Dialog title
        message: Question to ask

    Returns:
        True if user clicked Yes, False otherwise
    """
    from oncutf.core.application_context import ApplicationContext

    ctx = ApplicationContext.get_instance()
    if ctx.has_manager("user_dialog"):
        adapter = ctx.get_manager("user_dialog")
        return adapter.ask_yes_no(title, message)

    # Fallback: direct Qt import (legacy behavior)
    from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog
    if parent is not None:
        return CustomMessageDialog.question(parent, title, message)

    # If no parent, use active window or default to False
    from oncutf.core.pyqt_imports import QApplication
    active_parent = QApplication.activeWindow()
    if active_parent:
        return CustomMessageDialog.question(active_parent, title, message)
    return False  # Default response when no parent available


def get_dialog_adapter():
    """Get the registered UserDialogPort adapter.

    Returns:
        The registered adapter or None if not registered yet.

    Note:
        This is for advanced use cases where you need the adapter directly.
        Most code should use show_info_message(), show_error_message(), etc.
    """
    from oncutf.core.application_context import ApplicationContext

    try:
        ctx = ApplicationContext.get_instance()
        return ctx.get_manager("user_dialog") if ctx.has_manager("user_dialog") else None
    except RuntimeError:
        # ApplicationContext not initialized (e.g., in tests)
        return None

