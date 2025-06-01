'''
custom_tree_view.py

Author: Michael Economou
Date: 2025-06-05

Implements a custom tree view with modified drag & drop behavior
to prevent drag-out to external applications while preserving
internal drag & drop functionality.
'''

import os
from PyQt5.QtWidgets import QTreeView, QAbstractItemView, QApplication, QFileSystemModel
from PyQt5.QtCore import Qt, QMimeData, QEvent, QPoint, QUrl, pyqtSignal
from PyQt5.QtGui import QDrag
from utils.logger_helper import get_logger
from config import ALLOWED_EXTENSIONS

logger = get_logger(__name__)

class CustomTreeView(QTreeView):
    """
    Custom tree view that prevents drag-out to external applications
    while preserving internal drag & drop functionality.
    """
    # Signal emitted when files are dropped onto the tree view
    files_dropped = pyqtSignal(list, object)  # list of paths and keyboard modifiers

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        # Επιτρέπουμε εσωτερικό drag & drop, όχι μόνο DragOnly
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDropIndicatorShown(True)
        self._drag_start_position = None
        self._dragging = False

    def mousePressEvent(self, event):
        """Store initial position for drag detection"""
        if event.button() == Qt.LeftButton:
            self._drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Custom implementation to allow internal drag & drop but prevent external"""
        if not (event.buttons() & Qt.LeftButton) or not self._drag_start_position:
            return super().mouseMoveEvent(event)

        # Αν δεν έχουμε κινηθεί αρκετά, δεν ξεκινάμε drag
        if (event.pos() - self._drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return super().mouseMoveEvent(event)

        # Αποτρέπουμε πολλαπλά drag events
        if self._dragging:
            return

        # Ξεκινάμε custom drag αντί για το προεπιλεγμένο
        self._dragging = True
        self.startInternalDrag(event.pos())
        self._dragging = False
        return

    def startInternalDrag(self, position):
        """
        Start a drag operation that works within the application.
        Allow dragging folders and files from tree view to other components like file table.
        """
        index = self.indexAt(position)
        if not index.isValid():
            index = self.currentIndex()
            if not index.isValid():
                return

        # Get model and file path of the selected item
        model = self.model()
        if not hasattr(model, 'filePath'):
            logger.warning("Model does not support filePath method")
            return

        path = model.filePath(index)
        if not path:
            return

        # Check if it's a directory or file
        is_dir = os.path.isdir(path)

        # For files, check if it has an allowed extension
        if not is_dir:
            _, ext = os.path.splitext(path)
            if ext.startswith('.'):
                ext = ext[1:].lower()
            if ext not in ALLOWED_EXTENSIONS:
                logger.debug(f"Skipping drag for non-allowed file extension: {ext}")
                return

        # Create drag object with MIME data
        drag = QDrag(self)
        mimeData = QMimeData()

        # Always include our internal custom MIME type
        mimeData.setData("application/x-oncutf-internal", path.encode())

        # Also include standard formats for internal drops to file table
        # Unlike before, we DO want to allow drag to other internal components
        mimeData.setText(path)
        mimeData.setUrls([QUrl.fromLocalFile(path)])

        # Set the MIME data to the drag object
        drag.setMimeData(mimeData)

        # Execute the drag with CopyAction
        result = drag.exec_(Qt.CopyAction)
        logger.debug(f"Drag completed with result: {result}")

    def dragEnterEvent(self, event):
        """
        Override to reject all drag enter events. No drops are allowed on the tree view.
        """
        event.ignore()

    def dragMoveEvent(self, event):
        """
        Override to reject all drag move events. No drops are allowed on the tree view.
        """
        event.ignore()

    def dropEvent(self, event):
        """
        Override to reject all drop events. No drops are allowed on the tree view.
        """
        event.ignore()
