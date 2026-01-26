"""UI adapters - bridge between core/app and ui layers.

This module breaks core→ui cycles by providing interfaces that core can use
without directly importing ui modules.

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from oncutf.ui.adapters.application_context import ApplicationContext, get_app_context
from oncutf.ui.adapters.qt_app_context import QtAppContext, get_qt_app_context

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget

__all__ = [
    "ApplicationContext",
    "DialogAdapterProtocol",
    "QtAppContext",
    "get_app_context",
    "get_qt_app_context",
]


class DialogAdapterProtocol(Protocol):
    """Protocol for showing dialogs without Qt dependencies in core."""

    def show_info(
        self, parent: QWidget | None, title: str, message: str
    ) -> None:
        """Show information dialog."""
        ...

    def show_warning(
        self, parent: QWidget | None, title: str, message: str
    ) -> None:
        """Show warning dialog."""
        ...

    def show_error(
        self, parent: QWidget | None, title: str, message: str
    ) -> None:
        """Show error dialog."""
        ...

    def ask_yes_no(
        self, parent: QWidget | None, title: str, message: str
    ) -> bool:
        """Ask yes/no question. Returns True for yes, False for no."""
        ...

    def ask_ok_cancel(
        self, parent: QWidget | None, title: str, message: str
    ) -> bool:
        """Ask ok/cancel question. Returns True for ok, False for cancel."""
        ...


class DialogAdapter:
    """Concrete implementation of dialog adapter using Qt dialogs.

    This breaks the core→ui cycle by providing a single point of dialog creation.
    Core modules can depend on the Protocol, while UI provides the implementation.
    """

    def show_info(
        self, parent: QWidget | None, title: str, message: str
    ) -> None:
        """Show information dialog."""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.information(parent, title, message)

    def show_warning(
        self, parent: QWidget | None, title: str, message: str
    ) -> None:
        """Show warning dialog."""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.warning(parent, title, message)

    def show_error(
        self, parent: QWidget | None, title: str, message: str
    ) -> None:
        """Show error dialog."""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.critical(parent, title, message)

    def ask_yes_no(
        self, parent: QWidget | None, title: str, message: str
    ) -> bool:
        """Ask yes/no question. Returns True for yes, False for no."""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        return CustomMessageDialog.question(parent, title, message)

    def ask_ok_cancel(
        self, parent: QWidget | None, title: str, message: str
    ) -> bool:
        """Ask ok/cancel question. Returns True for ok, False for cancel."""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        # Using question for now - can be customized
        return CustomMessageDialog.question(parent, title, message)


# Global instance (singleton pattern)
_dialog_adapter: DialogAdapter | None = None


def get_dialog_adapter() -> DialogAdapter:
    """Get the global dialog adapter instance."""
    global _dialog_adapter
    if _dialog_adapter is None:
        _dialog_adapter = DialogAdapter()
    return _dialog_adapter


def set_dialog_adapter(adapter: DialogAdapter) -> None:
    """Set a custom dialog adapter (useful for testing)."""
    global _dialog_adapter
    _dialog_adapter = adapter
