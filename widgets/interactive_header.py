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

from core.qt_imports import QPoint, Qt, QAction, QHeaderView, QMenu

# ApplicationContext integration
try:
    from core.application_context import get_app_context
except ImportError:
    get_app_context = None


class InteractiveHeader(QHeaderView):
    """
    A custom QHeaderView that toggles selection on column 0 click,
    and performs manual sorting for other columns. Prevents accidental sort
    when user clicks near the edge to resize.
    """

    def __init__(self, orientation, parent=None, parent_window=None):
        super().__init__(orientation, parent)
        self.parent_window = parent_window  # Keep for backward compatibility
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setSortIndicatorShown(True)
        # self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenuEvent)

        self.header_enabled = True

        self._press_pos: QPoint = QPoint()
        self._pressed_index: int = -1

    def _get_app_context(self):
        """Get ApplicationContext with fallback to None."""
        if get_app_context is None:
            return None
        try:
            return get_app_context()
        except RuntimeError:
            # ApplicationContext not ready yet
            return None

    def _get_main_window_via_context(self):
        """Get main window via ApplicationContext with fallback to parent traversal."""
        # Try ApplicationContext first
        context = self._get_app_context()
        if context and hasattr(context, '_main_window'):
            return context._main_window

        # Fallback to legacy parent_window approach
        if self.parent_window:
            return self.parent_window

        # Last resort: traverse parents to find main window
        from utils.path_utils import find_parent_with_attribute
        return find_parent_with_attribute(self, 'handle_header_toggle')

    def mousePressEvent(self, event) -> None:
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
        main_window = self._get_main_window_via_context()

        if released_index == 0:
            if main_window and hasattr(main_window, 'handle_header_toggle'):
                # Qt.Checked may not always exist as attribute
                checked = getattr(Qt, 'Checked', 2)
                main_window.handle_header_toggle(checked)
        else:
            if main_window and hasattr(main_window, 'sort_by_column'):
                main_window.sort_by_column(released_index)

        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        """
        Show right-click context menu for sorting at header column.
        """
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

    def _sort(self, column: int, order: Qt.SortOrder) -> None:
        """
        Calls MainWindow.sort_by_column() with forced order from context menu.
        """
        main_window = self._get_main_window_via_context()
        if main_window and hasattr(main_window, 'sort_by_column'):
            main_window.sort_by_column(column, force_order=order)




