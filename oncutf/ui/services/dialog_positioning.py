"""Dialog positioning service - Application layer facade.

Provides Qt-independent dialog positioning utilities.
Delegates to multiscreen-aware implementations.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget


def ensure_dialog_centered(dialog: QWidget, parent: QWidget | None = None) -> None:
    """Ensure dialog is positioned correctly on parent's screen.

    This is a Qt-independent facade that delegates to multiscreen-aware
    positioning logic.

    Args:
        dialog: Dialog widget to position
        parent: Parent widget (for multiscreen positioning)

    """
    from oncutf.ui.helpers.multiscreen_helper import ensure_dialog_on_parent_screen

    ensure_dialog_on_parent_screen(dialog, parent)
