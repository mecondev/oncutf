"""User interaction service - Application layer facade.

Provides Qt-independent functions for core modules to show dialogs,
progress indicators, and status messages. Delegates to UserDialogPort
implementations registered in QtAppContext.

This module breaks core->ui dependency cycles by inverting control:
- core/ imports this (app layer, no Qt)
- ui/ provides concrete implementations via ports

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget

    from oncutf.app.ports import UserDialogPort


def show_info_message(parent: QWidget | None, title: str, message: str) -> None:  # noqa: ARG001
    """Show information dialog using registered adapter.

    Args:
        parent: Parent widget (may be None) - currently unused, kept for API compatibility
        title: Dialog title
        message: Message to display

    Note:
        This function is a bridge - core modules can call it without
        importing Qt directly. The actual dialog is shown by the adapter
        registered in QtAppContext.

    Raises:
        RuntimeError: If user_dialog adapter is not registered

    """
    from oncutf.app.state.context import AppContext

    ctx = AppContext.get_instance()
    if not ctx.has_manager("user_dialog"):
        raise RuntimeError(
            "UserDialogPort adapter not registered. "
            "Call register_user_dialog_adapter() during initialization."
        )

    adapter = cast("UserDialogPort", ctx.get_manager("user_dialog"))
    adapter.show_info(title, message)


def show_error_message(parent: QWidget | None, title: str, message: str) -> None:  # noqa: ARG001
    """Show error dialog using registered adapter.

    Args:
        parent: Parent widget (may be None) - currently unused, kept for API compatibility
        title: Dialog title
        message: Error message to display

    Raises:
        RuntimeError: If user_dialog adapter is not registered

    """
    from oncutf.app.state.context import AppContext

    ctx = AppContext.get_instance()
    if not ctx.has_manager("user_dialog"):
        raise RuntimeError(
            "UserDialogPort adapter not registered. "
            "Call register_user_dialog_adapter() during initialization."
        )

    adapter = cast("UserDialogPort", ctx.get_manager("user_dialog"))
    adapter.show_error(title, message)


def show_warning_message(parent: QWidget | None, title: str, message: str) -> None:  # noqa: ARG001
    """Show warning dialog using registered adapter.

    Args:
        parent: Parent widget (may be None) - currently unused, kept for API compatibility
        title: Dialog title
        message: Warning message to display

    Raises:
        RuntimeError: If user_dialog adapter is not registered

    """
    from oncutf.app.state.context import AppContext

    ctx = AppContext.get_instance()
    if not ctx.has_manager("user_dialog"):
        raise RuntimeError(
            "UserDialogPort adapter not registered. "
            "Call register_user_dialog_adapter() during initialization."
        )

    adapter = cast("UserDialogPort", ctx.get_manager("user_dialog"))
    adapter.show_warning(title, message)


def show_question_message(parent: QWidget | None, title: str, message: str) -> bool:  # noqa: ARG001
    """Show yes/no question dialog using registered adapter.

    Args:
        parent: Parent widget (may be None) - currently unused, kept for API compatibility
        title: Dialog title
        message: Question to ask

    Returns:
        True if user clicked Yes, False otherwise

    Raises:
        RuntimeError: If user_dialog adapter is not registered

    """
    from oncutf.app.state.context import AppContext

    ctx = AppContext.get_instance()
    if not ctx.has_manager("user_dialog"):
        raise RuntimeError(
            "UserDialogPort adapter not registered. "
            "Call register_user_dialog_adapter() during initialization."
        )

    adapter = cast("UserDialogPort", ctx.get_manager("user_dialog"))
    return bool(adapter.ask_yes_no(title, message))


def get_dialog_adapter() -> UserDialogPort | None:
    """Get the registered UserDialogPort adapter.

    Returns:
        The registered adapter or None if not registered yet.

    Note:
        This is for advanced use cases where you need the adapter directly.
        Most code should use show_info_message(), show_error_message(), etc.

    """
    from oncutf.app.state.context import AppContext

    try:
        ctx = AppContext.get_instance()
        return ctx.get_manager("user_dialog") if ctx.has_manager("user_dialog") else None
    except RuntimeError:
        # AppContext not initialized (e.g., in tests)
        return None
