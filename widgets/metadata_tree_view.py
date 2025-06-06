#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_tree_view.py

Author: Michael Economou
Date: 2025-05-20

This module defines a custom QTreeView widget that supports drag-and-drop functionality
for triggering metadata loading in the Batch File Renamer GUI.

The view accepts file drops ONLY from the internal file table of the application,
and emits a signal (`files_dropped`) containing the dropped file paths.

Expected usage:
- Drag files from the file table (but not from external sources).
- Drop onto the metadata tree.
- The main window connects to `files_dropped` and triggers selective metadata loading.

Designed for integration with MainWindow and MetadataReader.
"""
import json
from typing import Optional, Dict, Any, List, Union

from PyQt5.QtWidgets import QTreeView, QAbstractItemView, QApplication, QHeaderView
from PyQt5.QtCore import QUrl, Qt, QMimeData, pyqtSignal, QTimer
from PyQt5.QtGui import QDropEvent, QDragEnterEvent, QDragMoveEvent
from utils.logger_helper import get_logger

logger = get_logger(__name__)

class MetadataTreeView(QTreeView):
    """
    Tree view that accepts file drag & drop to trigger metadata loading.
    Only accepts drops from the application's file table, not external sources.
    Emits a signal with filenames to be processed.
    """
    files_dropped = pyqtSignal(list, Qt.KeyboardModifiers)  # Emits list of local file paths

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        # Ενεργοποίηση οριζόντιου scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Απενεργοποίηση wordwrap
        self.setTextElideMode(Qt.ElideRight)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        Accept drag only if it comes from our application's file table.
        This is identified by the presence of our custom MIME type.
        """
        # Debug MIME formats for troubleshooting
        logger.debug(f"[DragDrop] dragEnterEvent! formats={event.mimeData().formats()}")

        # Accept ONLY if the drag contains our custom application MIME type
        if event.mimeData().hasFormat("application/x-oncutf-filetable"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """
        Continue accepting drag move events only for items from our file table.
        """
        if event.mimeData().hasFormat("application/x-oncutf-filetable"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Process the drop, but only if it comes from our file table.
        Emit signal with the list of file paths.
        """
        logger.debug("[DragDrop] dropEvent called!")

        # Get the global drag cancel filter
        from widgets.custom_tree_view import _drag_cancel_filter

        # Only process drops from our file table
        if event.mimeData().hasFormat("application/x-oncutf-filetable"):
            urls = event.mimeData().urls()
            files = [url.toLocalFile() for url in urls if url.isLocalFile()]
            if files:
                # Accept the event BEFORE emitting the signal
                event.acceptProposedAction()
                # Force cleanup of any drag state
                while QApplication.overrideCursor():
                    QApplication.restoreOverrideCursor()
                # Ensure the filter is deactivated
                _drag_cancel_filter.deactivate()
                # Process events immediately
                QApplication.processEvents()
                # Then emit signal for processing
                self.files_dropped.emit(files, event.keyboardModifiers())
            else:
                event.ignore()
                _drag_cancel_filter.deactivate()
                QApplication.restoreOverrideCursor()
                QApplication.processEvents()
        else:
            event.ignore()
            _drag_cancel_filter.deactivate()
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()

        # Force additional cleanup through timer
        QTimer.singleShot(0, self._complete_drag_cleanup)

    def _complete_drag_cleanup(self):
        """
        Additional cleanup method called after drop operation to ensure
        all drag state is completely reset.
        """
        # Get the global drag cancel filter to ensure it's deactivated
        from widgets.custom_tree_view import _drag_cancel_filter
        _drag_cancel_filter.deactivate()

        # Restore cursor if needed
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        QApplication.processEvents()
        if hasattr(self, 'viewport') and callable(getattr(self.viewport(), 'update', None)):
            self.viewport().update()

    def setModel(self, model):
        """
        Override the setModel method to set minimum column widths after the model is set.
        """
        # First call the parent implementation
        super().setModel(model)

        # Then set column sizes if we have a header and model
        if model and self.header():
            # Set minimum/maximum width for all columns
            # Column 0 (Key): Initial width 200px, Column 1 (Value): Initial width 500px
            self.header().setMinimumSectionSize(80)  # Global minimum size for all columns
            self.header().setMaximumSectionSize(800)  # Global maximum size for all columns

            # Resize mode for the first column (Key) - will adapt to content within limits
            self.header().setSectionResizeMode(0, QHeaderView.Interactive)
            self.header().setDefaultSectionSize(50)  # Default size for Key column (increased from 120)

            # Explicitly set Key column width to ensure it's applied
            self.header().resizeSection(0, 120)  # Force Key column width to 200px
            self.header().resizeSection(1, 500)

            # Resize mode for the second column (Value) - will stretch to fill available space
            self.header().setSectionResizeMode(1, QHeaderView.Stretch)

            # Initial column width adaptation based on content
            self.header().resizeSections(QHeaderView.ResizeToContents)

            # Set explicit initial width for Value column if needed
            if self.header().count() > 1:
                self.header().resizeSection(1, 500)  # Set Value column width
                # Reset Key column again after content resize to ensure it's applied

            # Check if this is a placeholder model (has only one item)
            if model.rowCount() == 1:
                root = model.invisibleRootItem()
                # Check if the first item has text "No file selected" or similar placeholder
                if root.rowCount() == 1:
                    item = root.child(0, 0)
                    if item and "No file" in item.text():
                        # Make the placeholder non-selectable
                        item.setSelectable(False)
                        value_item = root.child(0, 1)
                        if value_item:
                            value_item.setSelectable(False)

                        # Disable selection in the tree view while in placeholder mode
                        self.setSelectionMode(QAbstractItemView.NoSelection)

                        # Disable hover effect for placeholder by applying a stylesheet
                        self.setStyleSheet("""
                            QTreeView::item:hover {
                                background-color: transparent;
                                color: inherit;
                            }
                        """)
                        return

            # If we're not in placeholder mode, ensure normal selection is enabled and clear stylesheet
            self.setSelectionMode(QAbstractItemView.SingleSelection)
            self.setStyleSheet("")  # Reset any previously applied stylesheet

