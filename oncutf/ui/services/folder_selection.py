"""Folder selection service - Application layer facade.

Provides Qt-independent folder selection dialogs for core modules.
Delegates to multiscreen-aware implementations.

This module breaks core→ui dependency cycles by inverting control:
- core/ imports this (app layer, no UI coupling)
- ui/ provides concrete implementations via multiscreen_helper

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget


def select_folder(
    parent: QWidget | None = None, title: str = "Select Folder", start_dir: str = ""
) -> str:
    """Show folder selection dialog.

    This is a Qt-independent facade that delegates to multiscreen-aware
    QFileDialog implementation.

    Args:
        parent: Parent widget (for multiscreen positioning)
        title: Dialog title
        start_dir: Initial directory path

    Returns:
        Selected folder path (empty string if cancelled)

    """
    from oncutf.ui.helpers.multiscreen_helper import (
        get_existing_directory_on_parent_screen,
    )

    return get_existing_directory_on_parent_screen(parent, title, start_dir)
