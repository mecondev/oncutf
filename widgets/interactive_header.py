"""
interactive_header.py

Author: Michael Economou
Date: 2025-05-22

This module defines InteractiveHeader, a subclass of QHeaderView that
adds interactive behavior to table headers in the oncutf application.

Features:
- Toggles selection of all rows when clicking on column 0
- Performs manual sort handling for sortable columns (excluding column 0)
"""

from typing import Optional
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import Qt


class InteractiveHeader(QHeaderView):
    """
    A custom QHeaderView that toggles selection on column 0 click,
    and performs manual sorting for other columns.
    """

    def __init__(self, orientation, parent=None, parent_window: Optional[object] = None):
        super().__init__(orientation, parent)
        self.parent_window = parent_window
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setSortIndicatorShown(True)

    def mousePressEvent(self, event) -> None:
        """
        Handle header click events:
        - Column 0 → toggles all selection via parent_window
        - Other columns → perform manual sort toggle via parent_window
        """
        index = self.logicalIndexAt(event.pos())

        if index == 0:
            # Column 0 click toggles check state
            if self.parent_window:
                self.parent_window.handle_header_toggle(Qt.Checked)  # uses checked as toggle flag
        else:
            if self.parent_window:
                self.parent_window.sort_by_column(index)

        super().mousePressEvent(event)
