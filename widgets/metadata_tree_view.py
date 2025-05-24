"""
metadata_tree_view.py

Author: Michael Economou
Date: 2025-05-20

This module defines a custom QTreeView widget that supports drag-and-drop functionality
for triggering metadata loading in the Batch File Renamer GUI.

The view accepts local file drops (from inside or outside the application), and emits
a signal (`files_dropped`) containing the dropped file paths.

Expected usage:
- Drag files from the file table or file explorer.
- Drop onto the metadata tree.
- The main window connects to `files_dropped` and triggers selective metadata loading.

Designed for integration with MainWindow and MetadataReader.
"""
from PyQt5.QtWidgets import QTreeView, QAbstractItemView
from PyQt5.QtCore import QUrl, Qt, QMimeData, pyqtSignal
from PyQt5.QtGui import QDropEvent, QDragEnterEvent, QDragMoveEvent


class MetadataTreeView(QTreeView):
    """
    Tree view that accepts file drag & drop to trigger metadata loading.
    Emits a signal with filenames to be processed.
    """
    files_dropped = pyqtSignal(list, Qt.KeyboardModifiers)  # Emits list of local file paths

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        files = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if files:
            self.files_dropped.emit(files, event.keyboardModifiers())
            event.acceptProposedAction()
            print("[DEBUG] Drop event triggered. Modifiers:", event.keyboardModifiers())

