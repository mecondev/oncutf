"""Qt UI events adapter.

Author: Michael Economou
Date: 2026-02-08
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication


class QtUiEventsAdapter:
    """Qt-backed UI event helper implementation."""

    def process_events(self) -> None:
        """Process pending Qt events if QApplication is active."""
        app = QApplication.instance()
        if app is not None:
            app.processEvents()

    def get_item_data_roles(self) -> dict[str, int]:
        """Return Qt ItemDataRole values for UI updates."""
        return {
            "DecorationRole": int(Qt.DecorationRole),
            "ToolTipRole": int(Qt.ToolTipRole),
            "DisplayRole": int(Qt.DisplayRole),
            "EditRole": int(Qt.EditRole),
        }
