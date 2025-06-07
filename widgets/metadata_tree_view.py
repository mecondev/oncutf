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

from PyQt5.QtWidgets import QTreeView, QAbstractItemView, QApplication, QHeaderView, QMenu, QAction
from PyQt5.QtCore import QUrl, Qt, QMimeData, pyqtSignal, QTimer
from PyQt5.QtGui import QDropEvent, QDragEnterEvent, QDragMoveEvent, QIcon, QColor
from utils.logger_helper import get_logger
from utils.metadata_validators import get_validator_for_key
from widgets.metadata_edit_dialog import MetadataEditDialog

logger = get_logger(__name__)

class MetadataTreeView(QTreeView):
    """
    Tree view that accepts file drag & drop to trigger metadata loading.
    Only accepts drops from the application's file table, not external sources.
    Emits a signal with filenames to be processed.
    """
    files_dropped = pyqtSignal(list, Qt.KeyboardModifiers)  # Emits list of local file paths

    # Σήματα για τις λειτουργίες metadata
    value_copied = pyqtSignal(str)  # Εκπέμπεται όταν αντιγράφεται μια τιμή
    value_edited = pyqtSignal(str, str, str)  # Εκπέμπεται με (key_path, old_value, new_value)
    value_reset = pyqtSignal(str)  # Εκπέμπεται με το key_path που έγινε reset

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        # Enable horizontal scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Disable wordwrap
        self.setTextElideMode(Qt.ElideRight)

        # Modified metadata items
        self.modified_items = set()  # Set of paths for modified items

        # Context menu setup
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def fix_horizontal_scroll(self):
        """
        Fixes the horizontal scrollbar to stay at the left position when selecting a new item.
        """
        # Reset horizontal scrollbar to beginning
        QTimer.singleShot(0, lambda: self.horizontalScrollBar().setValue(0))

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
        from widgets.file_tree_view import _drag_cancel_filter

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
        from widgets.file_tree_view import _drag_cancel_filter
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

        # Connect selection changed signal to fix horizontal scroll
        if self.selectionModel():
            self.selectionModel().selectionChanged.connect(self.fix_horizontal_scroll)

        # Then set column sizes if we have a header and model
        if model and self.header():
            # Check if this is a placeholder model (has only one item)
            is_placeholder = False
            if model.rowCount() == 1:
                root = model.invisibleRootItem()
                # Check if the first item has text "No file selected" or similar placeholder
                if root.rowCount() == 1:
                    item = root.child(0, 0)
                    if item and "No file" in item.text():
                        is_placeholder = True

            if is_placeholder:
                # Placeholder mode: Fixed columns, no selection, no hover
                self.header().setSectionResizeMode(0, QHeaderView.Fixed)
                self.header().setSectionResizeMode(1, QHeaderView.Fixed)
                self.header().resizeSection(0, 120)  # Key column fixed size
                self.header().resizeSection(1, 250)  # Value column fixed size

                # Make placeholder items non-selectable
                root = model.invisibleRootItem()
                item = root.child(0, 0)
                if item:
                    item.setSelectable(False)
                value_item = root.child(0, 1)
                if value_item:
                    value_item.setSelectable(False)

                # Disable selection - styling will be handled by QSS
                self.setSelectionMode(QAbstractItemView.NoSelection)
                # Add a property for QSS targeting
                self.setProperty("placeholder", True)
                # Disable hover completely
                self.setAttribute(Qt.WA_NoMousePropagation, True)

                # Force style update
                self.style().unpolish(self)
                self.style().polish(self)
            else:
                # Normal content mode: Resizable columns, selection enabled, hover enabled
                # Key column: min 80px, initial 120px, max 300px
                self.header().setSectionResizeMode(0, QHeaderView.Interactive)
                self.header().setMinimumSectionSize(80)
                self.header().resizeSection(0, 120)  # Initial size for Key column

                # Value column: min 250px, max 800px, stretches to fill space
                self.header().setSectionResizeMode(1, QHeaderView.Stretch)
                self.header().resizeSection(1, 250)  # Minimum size for Value column

                # Set specific min/max sizes per column
                header = self.header()
                header.setMinimumSectionSize(80)   # Key column minimum
                header.setMaximumSectionSize(300)  # Key column maximum (applies to section 0)

                # Enable normal selection and clear placeholder property
                self.setSelectionMode(QAbstractItemView.SingleSelection)
                self.setProperty("placeholder", False)
                # Enable hover
                self.setAttribute(Qt.WA_NoMousePropagation, False)

                # Force style update
                self.style().unpolish(self)
                self.style().polish(self)

                # Ensure horizontal scrollbar is at the start
                QTimer.singleShot(100, lambda: self.horizontalScrollBar().setValue(0))

    def show_context_menu(self, position):
        """
        Displays context menu with available options depending on the selected item.
        """
        # Check if we're in placeholder mode - don't show menu
        if self.property("placeholder"):
            return

        # Get the item at the click position
        index = self.indexAt(position)
        if not index.isValid():
            return

        # Get the key path (e.g. "EXIF/DateTimeOriginal")
        key_path = self.get_key_path(index)

        # Get the value of the item
        value = index.sibling(index.row(), 1).data()

        # Create menu
        menu = QMenu(self)

        # Copy value action
        copy_action = QAction("Copy Value", self)
        copy_action.triggered.connect(lambda: self.copy_value(value))
        menu.addAction(copy_action)

        # Edit value action (enabled for Rotation only for now)
        edit_action = QAction("Edit Value", self)
        edit_action.triggered.connect(lambda: self.edit_value(key_path, value))
        edit_action.setEnabled("Rotation" in key_path)  # Enable only for rotation fields
        menu.addAction(edit_action)

        # Reset value action (enabled for rotation)
        reset_action = QAction("Reset Value", self)
        reset_action.triggered.connect(lambda: self.reset_value(key_path))
        # Enable only for rotation for now
        reset_action.setEnabled("Rotation" in key_path)
        menu.addAction(reset_action)

        # Show menu
        menu.exec_(self.viewport().mapToGlobal(position))

    def get_key_path(self, index):
        """
        Returns the full key path for the given index.
        For example: "EXIF/DateTimeOriginal" or "XMP/Creator"
        """
        if not index.isValid():
            return ""

        # If on Value column, get the corresponding Key
        if index.column() == 1:
            index = index.sibling(index.row(), 0)

        # Get the text of the current item
        item_text = index.data()

        # Find the parent group
        parent_index = index.parent()
        if parent_index.isValid():
            parent_text = parent_index.data()
            return f"{parent_text}/{item_text}"

        return item_text

    def copy_value(self, value):
        """
        Copies the value to clipboard and emits the value_copied signal.
        """
        if not value:
            return

        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(str(value))

        # Emit signal
        self.value_copied.emit(str(value))
        logger.debug(f"[MetadataTree] Copied value: {value}")

    def edit_value(self, key_path, current_value):
        """
        Opens a dialog to edit the value of a metadata field.
        """
        logger.debug(f"[MetadataTree] Editing value for key: {key_path}")

        accepted, new_value = MetadataEditDialog.get_value(
            parent=self,
            key_path=key_path,
            current_value=str(current_value)
        )

        if accepted and new_value != str(current_value):
            # Add to modified items
            self.modified_items.add(key_path)

            # Update the file icon in the file table to show it's modified
            self._update_file_icon_status()

            # Update the view
            self.viewport().update()

            # Update metadata in cache
            self._update_metadata_in_cache(key_path, new_value)

            # Emit signal with the new value
            logger.debug(f"[MetadataTree] Value changed from '{current_value}' to '{new_value}'")
            self.value_edited.emit(key_path, str(current_value), new_value)

            # Find the item in the tree and update its value
            self._update_tree_item_value(key_path, new_value)

    def _update_tree_item_value(self, key_path, new_value):
        """
        Updates the value of an item in the tree view.
        """
        model = self.model()
        if not model:
            return

        # Split the key path into parent and child
        parts = key_path.split('/')

        # Handle top-level item
        if len(parts) == 1:
            for row in range(model.rowCount()):
                index = model.index(row, 0)
                if index.data() == key_path:
                    value_index = model.index(row, 1)
                    model.setData(value_index, new_value)
                    return
        # Handle child item
        elif len(parts) == 2:
            parent_name, child_name = parts

            # Find parent item
            for parent_row in range(model.rowCount()):
                parent_index = model.index(parent_row, 0)
                if parent_index.data() == parent_name:
                    # Find child item
                    for child_row in range(model.rowCount(parent_index)):
                        child_index = model.index(child_row, 0, parent_index)
                        if child_index.data() == child_name:
                            value_index = model.index(child_row, 1, parent_index)
                            model.setData(value_index, new_value)
                            return

    def reset_value(self, key_path):
        """
        Resets the value to its original state.
        """
        logger.debug(f"[MetadataTree] Resetting value for key: {key_path}")

        # Remove from modified items
        if key_path in self.modified_items:
            self.modified_items.remove(key_path)

        # Update the file icon in the file table
        self._update_file_icon_status()

        # Update the view
        self.viewport().update()

        # Reset value in cache
        self._reset_metadata_in_cache(key_path)

        # Emit signal
        self.value_reset.emit(key_path)

    def _reset_metadata_in_cache(self, key_path):
        """
        Resets the metadata value in the cache to its original state.
        """
        # Get parent window (MainWindow)
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'file_table_view'):
            parent_window = parent_window.parent()

        if not parent_window or not hasattr(parent_window, 'file_table_view'):
            logger.warning("[MetadataTree] Cannot find parent window with file_table_view")
            return

        # Get the current selected file
        selection = parent_window.file_table_view.selectionModel()
        if not selection or not selection.hasSelection():
            return

        selected_rows = selection.selectedRows()
        if not selected_rows:
            return

        # Get the file model
        file_model = parent_window.model
        if not file_model:
            return

        # For each selected file, reset its metadata in cache
        for index in selected_rows:
            row = index.row()
            if 0 <= row < len(file_model.files):
                file_item = file_model.files[row]
                full_path = file_item.full_path

                # Check if we have the metadata cache
                if not hasattr(parent_window, 'metadata_cache'):
                    logger.warning("[MetadataTree] Cannot find metadata_cache in parent window")
                    return

                # Update the metadata in cache
                metadata_entry = parent_window.metadata_cache.get_entry(full_path)
                if metadata_entry and metadata_entry.data:
                    # Parse key path (e.g. "EXIF/Rotation" -> ["EXIF", "Rotation"])
                    parts = key_path.split('/')

                    # Reset the value in the metadata by removing it
                    if len(parts) == 1:
                        # Top-level key
                        if parts[0] in metadata_entry.data:
                            metadata_entry.data.pop(parts[0], None)
                    elif len(parts) == 2:
                        # Nested key (group/key)
                        group, key = parts
                        if group in metadata_entry.data and isinstance(metadata_entry.data[group], dict):
                            if key in metadata_entry.data[group]:
                                metadata_entry.data[group].pop(key, None)

                    logger.debug(f"[MetadataTree] Reset metadata in cache for {full_path}: {key_path}")

                    # Update file icon status based on remaining modified items
                    if not self.modified_items:
                        file_item.metadata_status = "loaded"
                    else:
                        file_item.metadata_status = "modified"

    def mark_as_modified(self, key_path):
        """
        Marks an item as modified.
        """
        self.modified_items.add(key_path)

        # Update the file icon in the file table
        self._update_file_icon_status()

        # Update the view
        self.viewport().update()

    def _update_file_icon_status(self):
        """
        Updates the file icon in the file table to reflect modified status.
        """
        # Get parent window (MainWindow)
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'file_table_view'):
            parent_window = parent_window.parent()

        if not parent_window or not hasattr(parent_window, 'file_table_view'):
            logger.warning("[MetadataTree] Cannot find parent window with file_table_view")
            return

        # Get the current selected file
        selection = parent_window.file_table_view.selectionModel()
        if not selection or not selection.hasSelection():
            return

        selected_rows = selection.selectedRows()
        if not selected_rows:
            return

        # Get the file model
        file_model = parent_window.model
        if not file_model:
            return

        # For each selected file, update its icon
        for index in selected_rows:
            row = index.row()
            if 0 <= row < len(file_model.files):
                file_item = file_model.files[row]

                # Update icon based on whether we have modified items
                if self.modified_items:
                    # Set modified icon
                    file_item.metadata_status = "modified"
                else:
                    # Set normal loaded icon
                    file_item.metadata_status = "loaded"

                # Notify model the icon has changed
                file_model.dataChanged.emit(
                    file_model.index(row, 0),
                    file_model.index(row, 0),
                    [Qt.DecorationRole]
                )

    def currentChanged(self, current, previous):
        """
        Override to fix scrollbar position when changing selection.
        """
        super().currentChanged(current, previous)
        # Reset horizontal scrollbar to beginning
        self.horizontalScrollBar().setValue(0)

    def _update_metadata_in_cache(self, key_path, new_value):
        """
        Updates the metadata value in the cache to persist changes.
        """
        # Get parent window (MainWindow)
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'file_table_view'):
            parent_window = parent_window.parent()

        if not parent_window or not hasattr(parent_window, 'file_table_view'):
            logger.warning("[MetadataTree] Cannot find parent window with file_table_view")
            return

        # Get the current selected file
        selection = parent_window.file_table_view.selectionModel()
        if not selection or not selection.hasSelection():
            return

        selected_rows = selection.selectedRows()
        if not selected_rows:
            return

        # Get the file model
        file_model = parent_window.model
        if not file_model:
            return

        # For each selected file, update its metadata in cache
        for index in selected_rows:
            row = index.row()
            if 0 <= row < len(file_model.files):
                file_item = file_model.files[row]
                full_path = file_item.full_path

                # Get metadata from cache
                if not hasattr(parent_window, 'metadata_cache'):
                    logger.warning("[MetadataTree] Cannot find metadata_cache in parent window")
                    return

                # Update the metadata in cache
                metadata_entry = parent_window.metadata_cache.get_entry(full_path)
                if metadata_entry and hasattr(metadata_entry, 'data'):
                    # Parse key path (e.g. "EXIF/Rotation" -> ["EXIF", "Rotation"])
                    parts = key_path.split('/')

                    # Update the value in the metadata
                    if len(parts) == 1:
                        # Top-level key
                        metadata_entry.data[parts[0]] = new_value
                    elif len(parts) == 2:
                        # Nested key (group/key)
                        group, key = parts
                        if group not in metadata_entry.data:
                            metadata_entry.data[group] = {}
                        if not isinstance(metadata_entry.data[group], dict):
                            metadata_entry.data[group] = {}
                        metadata_entry.data[group][key] = new_value

                    logger.debug(f"[MetadataTree] Updated metadata in cache for {full_path}: {key_path}={new_value}")

                    # Mark metadata as modified
                    file_item.metadata_status = "modified"

