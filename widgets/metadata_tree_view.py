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

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PyQt5.QtWidgets import QAbstractItemView, QAction, QApplication, QHeaderView, QMenu, QTreeView

from config import METADATA_TREE_COLUMN_WIDTHS
from utils.logger_helper import get_logger
from widgets.metadata_edit_dialog import MetadataEditDialog

logger = get_logger(__name__)

class MetadataTreeView(QTreeView):
    """
    Tree view that accepts file drag & drop to trigger metadata loading.
    Only accepts drops from the application's file table, not external sources.
    Emits a signal with filenames to be processed.
    """
    files_dropped = pyqtSignal(list, Qt.KeyboardModifiers)  # Emits list of local file paths

    # Signals for metadata operations
    value_copied = pyqtSignal(str)  # Emitted when a value is copied
    value_edited = pyqtSignal(str, str, str)  # Emitted with (key_path, old_value, new_value)
    value_reset = pyqtSignal(str)  # Emitted with the key_path that was reset

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        # Initially hide horizontal scrollbar (will be enabled in normal mode)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Disable wordwrap
        self.setTextElideMode(Qt.ElideRight)

        # Modified metadata items
        self.modified_items = set()  # Set of paths for modified items

        # Context menu setup
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Track if we're in placeholder mode
        self._is_placeholder_mode = True

        # Scroll position memory: {file_path: scroll_position}
        self._scroll_positions = {}
        self._current_file_path = None

    # =====================================
    # Drag & Drop Methods
    # =====================================

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
                self._perform_drag_cleanup(_drag_cancel_filter)
                # Then emit signal for processing
                self.files_dropped.emit(files, event.keyboardModifiers())
            else:
                event.ignore()
                self._perform_drag_cleanup(_drag_cancel_filter)
        else:
            event.ignore()
            self._perform_drag_cleanup(_drag_cancel_filter)

        # Force additional cleanup through timer
        QTimer.singleShot(0, self._complete_drag_cleanup)

    def _perform_drag_cleanup(self, drag_cancel_filter) -> None:
        """Centralized drag cleanup logic."""
        # Force cleanup of any drag state
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
        # Ensure the filter is deactivated
        drag_cancel_filter.deactivate()
        # Process events immediately
        QApplication.processEvents()

    def _complete_drag_cleanup(self) -> None:
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

    # =====================================
    # Model & Column Management
    # =====================================

    def setModel(self, model) -> None:
        """
        Override the setModel method to set minimum column widths after the model is set.
        """
        # Save scroll position for current file before switching
        self._save_current_scroll_position()

        # First call the parent implementation
        super().setModel(model)

        # Then set column sizes if we have a header and model
        if model and self.header():
            is_placeholder = self._detect_placeholder_mode(model)
            self._is_placeholder_mode = is_placeholder

            if is_placeholder:
                self._configure_placeholder_mode(model)
                self._current_file_path = None  # No file selected
            else:
                self._configure_normal_mode()
                # Restore scroll position after model is set
                QTimer.singleShot(50, self._restore_scroll_position_for_current_file)

    def _detect_placeholder_mode(self, model) -> bool:
        """Detect if the model contains placeholder content."""
        if model.rowCount() == 1:
            root = model.invisibleRootItem()
            if root.rowCount() == 1:
                item = root.child(0, 0)
                if item and "No file" in item.text():
                    return True
        return False

    def _configure_placeholder_mode(self, model) -> None:
        """Configure view for placeholder mode."""
        # Placeholder mode: Fixed columns, no selection, no hover, NO HORIZONTAL SCROLLBAR
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.resizeSection(0, METADATA_TREE_COLUMN_WIDTHS["PLACEHOLDER_KEY_WIDTH"])
        header.resizeSection(1, METADATA_TREE_COLUMN_WIDTHS["PLACEHOLDER_VALUE_WIDTH"])

        # Make placeholder items non-selectable
        self._make_placeholder_items_non_selectable(model)

        # Disable selection and set properties for styling
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setProperty("placeholder", True)
        self.setAttribute(Qt.WA_NoMousePropagation, True)

        # Force style update
        self._force_style_update()

    def _configure_normal_mode(self) -> None:
        """Configure view for normal content mode."""
        # Normal content mode: HORIZONTAL SCROLLBAR enabled but controlled
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        header = self.header()

        # Key column: min 80px, initial 180px, max 800px
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setMinimumSectionSize(METADATA_TREE_COLUMN_WIDTHS["KEY_MIN_WIDTH"])
        header.resizeSection(0, METADATA_TREE_COLUMN_WIDTHS["NORMAL_KEY_INITIAL_WIDTH"])

        # Value column: min 250px, initial 500px, allows wide content without stretching
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.resizeSection(1, METADATA_TREE_COLUMN_WIDTHS["NORMAL_VALUE_INITIAL_WIDTH"])

        # Set specific min/max sizes per column
        header.setMinimumSectionSize(METADATA_TREE_COLUMN_WIDTHS["KEY_MIN_WIDTH"])
        header.setMaximumSectionSize(METADATA_TREE_COLUMN_WIDTHS["KEY_MAX_WIDTH"])

        # Enable normal selection and clear placeholder property
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setProperty("placeholder", False)
        self.setAttribute(Qt.WA_NoMousePropagation, False)

        # Force style update
        self._force_style_update()

    def _make_placeholder_items_non_selectable(self, model) -> None:
        """Make placeholder items non-selectable."""
        root = model.invisibleRootItem()
        item = root.child(0, 0)
        if item:
            item.setSelectable(False)
        value_item = root.child(0, 1)
        if value_item:
            value_item.setSelectable(False)

    def _force_style_update(self) -> None:
        """Force Qt style system to update."""
        self.style().unpolish(self)
        self.style().polish(self)

    # =====================================
    # Scroll Position Memory
    # =====================================

    def set_current_file_path(self, file_path: str) -> None:
        """Set the current file path for scroll position tracking."""
        # Save current position before changing files
        self._save_current_scroll_position()

        # Update current file
        self._current_file_path = file_path

        # Restore position for the new file (with a small delay to ensure model is ready)
        QTimer.singleShot(100, self._restore_scroll_position_for_current_file)

    def _save_current_scroll_position(self) -> None:
        """Save the current scroll position for the current file."""
        if self._current_file_path and not self._is_placeholder_mode:
            scroll_value = self.verticalScrollBar().value()
            self._scroll_positions[self._current_file_path] = scroll_value
            logger.debug(f"[MetadataTree] Saved scroll position {scroll_value} for {self._current_file_path}")

    def _restore_scroll_position_for_current_file(self) -> None:
        """Restore the scroll position for the current file."""
        if self._current_file_path and not self._is_placeholder_mode:
            saved_position = self._scroll_positions.get(self._current_file_path, 0)
            if saved_position > 0:
                self.verticalScrollBar().setValue(saved_position)
                logger.debug(f"[MetadataTree] Restored scroll position {saved_position} for {self._current_file_path}")
            else:
                # For new files, start at the top
                self.verticalScrollBar().setValue(0)

    def clear_scroll_memory(self) -> None:
        """Clear all saved scroll positions (useful when changing folders)."""
        self._scroll_positions.clear()
        self._current_file_path = None
        logger.debug("[MetadataTree] Cleared scroll position memory")

    # =====================================
    # Context Menu & Actions
    # =====================================

    def show_context_menu(self, position) -> None:
        """
        Displays context menu with available options depending on the selected item.
        """
        # Check if we're in placeholder mode - don't show menu
        if self._is_placeholder_mode or self.property("placeholder"):
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

    def get_key_path(self, index) -> str:
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

    def copy_value(self, value) -> None:
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

    # =====================================
    # Metadata Editing Methods
    # =====================================

    def edit_value(self, key_path, current_value) -> None:
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

    def _update_tree_item_value(self, key_path, new_value) -> None:
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
                            # Force a refresh
                            model.dataChanged.emit(value_index, value_index)
                            return

    def reset_value(self, key_path) -> None:
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

    def mark_as_modified(self, key_path) -> None:
        """
        Marks an item as modified.
        """
        self.modified_items.add(key_path)

        # Update the file icon in the file table
        self._update_file_icon_status()

        # Update the view
        self.viewport().update()

    # =====================================
    # Parent Window Helper Methods
    # =====================================

    def _get_parent_window_with_file_table(self):
        """
        Helper method to find the parent window that contains the file_table_view.
        Returns tuple: (parent_window, file_model, selection, selected_rows)
        """
        # Get parent window (MainWindow)
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'file_table_view'):
            parent_window = parent_window.parent()

        if not parent_window or not hasattr(parent_window, 'file_table_view'):
            logger.warning("[MetadataTree] Cannot find parent window with file_table_view")
            return None, None, None, None

        # Get the current selected file
        selection = parent_window.file_table_view.selectionModel()
        if not selection or not selection.hasSelection():
            return parent_window, None, None, None

        selected_rows = selection.selectedRows()
        if not selected_rows:
            return parent_window, None, selection, None

        # Get the file model
        file_model = parent_window.file_model
        if not file_model:
            return parent_window, None, selection, selected_rows

        return parent_window, file_model, selection, selected_rows

    # =====================================
    # Metadata Cache Management
    # =====================================

    def _update_file_icon_status(self) -> None:
        """
        Updates the file icon in the file table to reflect modified status.
        """
        parent_window, file_model, selection, selected_rows = self._get_parent_window_with_file_table()

        if not all([parent_window, file_model, selected_rows]):
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

    def _reset_metadata_in_cache(self, key_path) -> None:
        """
        Resets the metadata value in the cache to its original state.
        """
        parent_window, file_model, selection, selected_rows = self._get_parent_window_with_file_table()

        if not all([parent_window, file_model, selected_rows]):
            return

        # Check if we have the metadata cache
        if not hasattr(parent_window, 'metadata_cache'):
            logger.warning("[MetadataTree] Cannot find metadata_cache in parent window")
            return

        # For each selected file, reset its metadata in cache
        for index in selected_rows:
            row = index.row()
            if 0 <= row < len(file_model.files):
                file_item = file_model.files[row]
                full_path = file_item.full_path

                # Update the metadata in cache
                metadata_entry = parent_window.metadata_cache.get_entry(full_path)
                if metadata_entry and hasattr(metadata_entry, 'data'):
                    self._remove_metadata_from_cache(metadata_entry.data, key_path)
                    self._remove_metadata_from_file_item(file_item, key_path)

                    logger.debug(f"[MetadataTree] Reset metadata in cache for {full_path}: {key_path}")

                    # Update file icon status based on remaining modified items
                    if not self.modified_items:
                        file_item.metadata_status = "loaded"
                    else:
                        file_item.metadata_status = "modified"

                    # Force update of the icon in file table
                    file_model.dataChanged.emit(
                        file_model.index(row, 0),
                        file_model.index(row, 0),
                        [Qt.DecorationRole]
                    )

    def _update_metadata_in_cache(self, key_path, new_value) -> None:
        """
        Updates the metadata value in the cache to persist changes.
        """
        parent_window, file_model, selection, selected_rows = self._get_parent_window_with_file_table()

        if not all([parent_window, file_model, selected_rows]):
            return

        # Check if we have the metadata cache
        if not hasattr(parent_window, 'metadata_cache'):
            logger.warning("[MetadataTree] Cannot find metadata_cache in parent window")
            return

        # For each selected file, update its metadata in cache
        for index in selected_rows:
            row = index.row()
            if 0 <= row < len(file_model.files):
                file_item = file_model.files[row]
                full_path = file_item.full_path

                # Update the metadata in cache
                metadata_entry = parent_window.metadata_cache.get_entry(full_path)
                if metadata_entry and hasattr(metadata_entry, 'data'):
                    self._set_metadata_in_cache(metadata_entry.data, key_path, new_value)
                    self._set_metadata_in_file_item(file_item, key_path, new_value)

                    logger.debug(f"[MetadataTree] Updated metadata in cache for {full_path}: {key_path}={new_value}")

                    # Mark file item as modified
                    file_item.metadata_status = "modified"

                    # Force update of the icon in file table
                    file_model.dataChanged.emit(
                        file_model.index(row, 0),
                        file_model.index(row, 0),
                        [Qt.DecorationRole]
                    )

    def _remove_metadata_from_cache(self, metadata, key_path) -> None:
        """Remove metadata entry from cache dictionary."""
        parts = key_path.split('/')

        if len(parts) == 1:
            # Top-level key
            metadata.pop(parts[0], None)
        elif len(parts) == 2:
            # Nested key (group/key)
            group, key = parts
            if group in metadata and isinstance(metadata[group], dict):
                metadata[group].pop(key, None)

    def _remove_metadata_from_file_item(self, file_item, key_path) -> None:
        """Remove metadata entry from file item."""
        if hasattr(file_item, 'metadata') and file_item.metadata:
            self._remove_metadata_from_cache(file_item.metadata, key_path)

    def _set_metadata_in_cache(self, metadata, key_path, new_value) -> None:
        """Set metadata entry in cache dictionary."""
        parts = key_path.split('/')

        if len(parts) == 1:
            # Top-level key
            metadata[parts[0]] = new_value
        elif len(parts) == 2:
            # Nested key (group/key)
            group, key = parts
            if group not in metadata:
                metadata[group] = {}
            elif not isinstance(metadata[group], dict):
                metadata[group] = {}
            metadata[group][key] = new_value

            # Handle duplicate rotation entries
            self._handle_duplicate_rotation_entries(metadata, group, key)

    def _set_metadata_in_file_item(self, file_item, key_path, new_value) -> None:
        """Set metadata entry in file item."""
        if hasattr(file_item, 'metadata') and file_item.metadata:
            self._set_metadata_in_cache(file_item.metadata, key_path, new_value)

    def _handle_duplicate_rotation_entries(self, metadata, group, key) -> None:
        """Handle duplicate rotation entries between EXIF and Other groups."""
        if key == "Rotation":
            if group == "EXIF" and "Other" in metadata and isinstance(metadata["Other"], dict) and "Rotation" in metadata["Other"]:
                del metadata["Other"]["Rotation"]
                logger.debug("[MetadataTree] Removed duplicate Other/Rotation entry")
            elif group == "Other" and "EXIF" in metadata and isinstance(metadata["EXIF"], dict) and "Rotation" in metadata["EXIF"]:
                del metadata["EXIF"]["Rotation"]
                logger.debug("[MetadataTree] Removed duplicate EXIF/Rotation entry")

    # =====================================
    # Scroll Override
    # =====================================

    def scrollTo(self, index, hint=None) -> None:
        """
        Override scrollTo to prevent automatic scrolling.
        Scroll position is managed manually via the scroll position memory system.
        """
        if self._is_placeholder_mode:
            # In placeholder mode, use normal scrolling
            super().scrollTo(index, hint)
            return

        # In normal mode, do nothing - scroll position is managed manually
        # This prevents Qt from automatically scrolling when selections change
        return

