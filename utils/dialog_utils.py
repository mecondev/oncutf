"""
Module: dialog_utils.py

Author: Michael Economou
Date: 2025-05-31

dialog_utils.py
Utility functions for dialog and widget positioning and management.
Provides centralized logic for common dialog operations like centering.
"""
from typing import Optional

from core.pyqt_imports import QWidget


def center_widget_on_parent(widget: QWidget, parent: Optional[QWidget] = None) -> None:
    """
    Center a widget on its parent window.

    Args:
        widget: The widget to center
        parent: The parent widget to center on. If None, uses widget.parent()
    """
    target_parent = parent or widget.parent()

    if target_parent:
        parent_rect = target_parent.geometry() # type: ignore
        widget_size = widget.sizeHint()
        x = parent_rect.x() + (parent_rect.width() - widget_size.width()) // 2
        y = parent_rect.y() + (parent_rect.height() - widget_size.height()) // 2
        widget.move(x, y)


def setup_dialog_size_and_center(dialog: QWidget, content_widget: QWidget) -> None:
    """
    Set dialog size to match content widget and center it on parent.

    Args:
        dialog: The dialog to setup
        content_widget: The content widget to size the dialog to
    """
    # Use the same size as the content widget - no extra padding
    widget_size = content_widget.sizeHint()
    dialog.setFixedSize(widget_size.width(), widget_size.height())

    # Center the dialog on parent
    center_widget_on_parent(dialog)


def show_dialog_smooth(dialog: QWidget) -> None:
    """
    Show dialog with smooth appearance to prevent shadow flicker.

    Args:
        dialog: The dialog to show
    """
    # Force layout completion before showing
    dialog.adjustSize()
    dialog.updateGeometry()

    # Use the global timer manager to show dialog after layout is complete
    # This prevents the shadow-first appearance issue
    from utils.timer_manager import schedule_ui_update
    schedule_ui_update(dialog.show, delay=1)  # 1ms delay allows layout to complete


def show_info_message(parent: Optional[QWidget], title: str, message: str) -> None:
    """
    Show an information message dialog.

    Args:
        parent: Parent widget for the dialog
        title: Dialog title
        message: Message to display
    """
    from widgets.custom_message_dialog import CustomMessageDialog
    CustomMessageDialog.information(parent, title, message)


def show_error_message(parent: Optional[QWidget], title: str, message: str) -> None:
    """
    Show an error message dialog.

    Args:
        parent: Parent widget for the dialog
        title: Dialog title
        message: Message to display
    """
    from widgets.custom_message_dialog import CustomMessageDialog
    CustomMessageDialog.information(parent, title, message)
