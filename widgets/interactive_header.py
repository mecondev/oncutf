"""
interactive_header.py

Author: Michael Economou
Date: 2025-05-22

This module defines InteractiveHeader, a subclass of QHeaderView that
adds interactive behavior to table headers in the oncutf application.

Features:
- Toggles selection of all rows when clicking on column 0
- Performs manual sort handling for sortable columns (excluding column 0)
- Prevents accidental sort when resizing (Explorer-like behavior)
"""

from typing import Optional
from PyQt5.QtWidgets import QHeaderView, QMenu, QAction
from PyQt5.QtCore import Qt, QPoint


class InteractiveHeader(QHeaderView):
    """
    A custom QHeaderView that toggles selection on column 0 click,
    and performs manual sorting for other columns. Prevents accidental sort
    when user clicks near the edge to resize.
    """

    def __init__(self, orientation, parent=None, parent_window=None):
        super().__init__(orientation, parent)
        self.parent_window = parent_window
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setSortIndicatorShown(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self._press_pos: QPoint = QPoint()
        self._pressed_index: int = -1

    def mousePressEvent(self, event) -> None:
        print(f"[DEBUG] Header: mouse press {event.pos()}, button={event.button()}")
        self._press_pos = event.pos()
        self._pressed_index = self.logicalIndexAt(event.pos())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        released_index = self.logicalIndexAt(event.pos())

        if released_index != self._pressed_index:
            super().mouseReleaseEvent(event)
            return

        if (event.pos() - self._press_pos).manhattanLength() > 4:
            super().mouseReleaseEvent(event)
            return

        # Section was clicked without drag or resize intent
        if released_index == 0:
            if self.parent_window and hasattr(self.parent_window, 'handle_header_toggle'):
                # Qt.Checked μπορεί να μην υπάρχει πάντα ως attribute
                checked = getattr(Qt, 'Checked', 2)
                self.parent_window.handle_header_toggle(checked)
        else:
            if self.parent_window and hasattr(self.parent_window, 'sort_by_column'):
                self.parent_window.sort_by_column(released_index)

        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        """
        Show right-click context menu for sorting at header column.
        """
        print("[DEBUG] Header: context menu event triggered")

        logical_index = self.logicalIndexAt(event.pos())
        if logical_index <= 0:
            return  # skip column 0 (toggle column)

        menu = QMenu(self)

        sort_asc = QAction("Sort Ascending", self)
        sort_desc = QAction("Sort Descending", self)

        asc = getattr(Qt, 'AscendingOrder', 0)
        desc = getattr(Qt, 'DescendingOrder', 1)
        sort_asc.triggered.connect(lambda: self._sort(logical_index, asc))
        sort_desc.triggered.connect(lambda: self._sort(logical_index, desc))

        menu.addAction(sort_asc)
        menu.addAction(sort_desc)

        menu.exec_(event.globalPos())

    def _sort(self, index: int, order):
        """
        Calls sort_by_column on parent with specified order.
        """
        if self.parent_window and hasattr(self.parent_window, 'sort_by_column'):
            self.parent_window.sort_by_column(index, order)

    def setSectionMinimumSize(self, logicalIndex: int, size: int) -> None:
        super().setSectionMinimumSize(logicalIndex, size)

    def setSectionMaximumSize(self, logicalIndex: int, size: int) -> None:
        super().setSectionMaximumSize(logicalIndex, size)
