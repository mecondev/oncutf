"""
custom_table_view.py

Author: Michael Economou
Date: 2025-05-20

This module defines a custom QTableView subclass used in the file listing
of the Batch File Renamer GUI. It enhances selection behavior by ensuring
synchronization between the visual row selection (blue highlight) and
internal checked state used for renaming and metadata operations.

Key features:
- Overrides mouse and keyboard interaction to trigger preview updates
- Emits selection changes to the parent window using the sync_selection_to_checked() method
- Handles full-row selection and reacts to Ctrl+A, arrow keys, Enter, etc.

Intended for use as the main file table in the application's central UI.
"""
from PyQt5.QtWidgets import QAbstractItemView, QTableView, QApplication
from PyQt5.QtCore import QMimeData, QUrl, QItemSelection, Qt, QPoint
from PyQt5.QtGui import QKeySequence, QDrag


class CustomTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._drag_start_pos = QPoint()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        self._sync_selection_safely()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
        self.startDrag(Qt.CopyAction)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.matches(QKeySequence.SelectAll) or event.key() in (
            Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter,
            Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right
        ):
            self._sync_selection_safely()

    def _sync_selection_safely(self):
        parent = self.window()
        if hasattr(parent, "sync_selection_to_checked"):
            selection = self.selectionModel().selection()
            parent.sync_selection_to_checked(selection, QItemSelection())

    def startDrag(self, supportedActions):
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




