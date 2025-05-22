'''
custom_table_view.py

Author: Michael Economou
Date: 2025-05-21

This module defines the CustomTableView class, a QTableView subclass
used in the file listing of the Batch File Renamer GUI.

Key features:
- Full-row selection and keyboard navigation
- Drag & drop support for exporting file paths
- Synchronization between UI selection and internal state
- Mouse hover tracking (handled via QSS, no delegate required)

This implementation now relies solely on QSS for hover styling,
removing the need for a painting delegate. All hover colors and row
visual behavior are defined in table_view.qss for modular control.
'''

from PyQt5.QtWidgets import QAbstractItemView, QTableView, QApplication
from PyQt5.QtCore import QMimeData, QUrl, QItemSelection, Qt, QPoint
from PyQt5.QtGui import QKeySequence, QDrag
from widgets.hover_delegate import HoverItemDelegate


class CustomTableView(QTableView):
    def __init__(self, parent=None) -> None:
        """
        Initializes the custom file table with drag support,
        full-row selection, and mouse tracking for QSS-based hover effects.
        """
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._drag_start_pos = QPoint()
        self.setMouseTracking(True)  # Enables QSS ::item:hover support
        self.hover_delegate = HoverItemDelegate(self, hover_color="#2e3b4e")
        self.setItemDelegate(self.hover_delegate)
        self.setItemDelegateForColumn(0, self.hover_delegate)  # ensures col 0 uses it too

    def mousePressEvent(self, event) -> None:
        """
        Stores the position for potential drag and syncs row selection.
        """
        index = self.indexAt(event.pos())

        # click outside any row
        if not index.isValid() and event.button() == Qt.LeftButton:
            self.clearSelection()
            if hasattr(self.window(), "sync_selection_to_checked"):
                self.window().sync_selection_to_checked(self.selectionModel().selection(), None)

        super().mousePressEvent(event)

        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        self._sync_selection_safely()

    def mouseMoveEvent(self, event) -> None:
        index = self.indexAt(event.pos())
        hovered_row = index.row() if index.isValid() else -1

        if hasattr(self, "hover_delegate") and hovered_row != self.hover_delegate.hovered_row:
            old_row = self.hover_delegate.hovered_row
            self.hover_delegate.update_hover_row(hovered_row)

            for col in range(self.model().columnCount()):
                for r in (old_row, hovered_row):
                    if r >= 0:
                        idx = self.model().index(r, col)
                        self.viewport().update(self.visualRect(idx))

        # drag support
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        self.startDrag(Qt.CopyAction)

    def keyPressEvent(self, event) -> None:
        """
        Handles keyboard shortcuts and triggers selection sync when needed.
        """
        super().keyPressEvent(event)
        if event.matches(QKeySequence.SelectAll) or event.key() in (
            Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter,
            Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right
        ):
            self._sync_selection_safely()

    def _sync_selection_safely(self) -> None:
        """
        Calls sync_selection_to_checked() in the parent if it exists.
        This keeps internal selection state in sync with the visible UI.
        """
        parent = self.window()
        if hasattr(parent, "sync_selection_to_checked"):
            selection = self.selectionModel().selection()
            parent.sync_selection_to_checked(selection, QItemSelection())

    def startDrag(self, supportedActions: Qt.DropActions) -> None:
        """
        Prepares and initiates a drag operation using selected file paths.
        """
        indexes = self.selectedIndexes()
        if not indexes:
            return

        rows = sorted(set(index.row() for index in indexes))
        file_items = [self.model().files[r] for r in rows if 0 <= r < len(self.model().files)]
        file_paths = [f.full_path for f in file_items if f.full_path]

        if not file_paths:
            return

        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in file_paths]
        mime_data.setUrls(urls)

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)
