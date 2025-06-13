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

Features:
- Drag & drop support from internal file table only
- Intelligent scroll position memory per file with smooth animation
- Context menu for metadata editing (copy, edit, reset)
- Placeholder mode for empty content
- Modified item tracking with visual indicators

Expected usage:
- Drag files from the file table (but not from external sources).
- Drop onto the metadata tree.
- The main window connects to `files_dropped` and triggers selective metadata loading.

Designed for integration with MainWindow and MetadataReader.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple, Union

from PyQt5.QtCore import QModelIndex, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QApplication,
    QHeaderView,
    QLabel,
    QMenu,
    QTreeView,
    QWidget,
)

from config import METADATA_TREE_COLUMN_WIDTHS
from utils.logger_factory import get_cached_logger
from widgets.metadata_edit_dialog import MetadataEditDialog

# ApplicationContext integration
try:
    from core.application_context import get_app_context
except ImportError:
    get_app_context = None

logger = get_cached_logger(__name__)


class MetadataTreeView(QTreeView):
    """
    Custom tree view that accepts file drag & drop to trigger metadata loading.
    Only accepts drops from the application's file table, not external sources.
    Includes intelligent scroll position memory per file with smooth animation.

    Signals:
        files_dropped: Emitted when files are dropped from file table
        value_copied: Emitted when a metadata value is copied to clipboard
        value_edited: Emitted when a metadata value is edited
        value_reset: Emitted when a metadata value is reset
    """
    files_dropped = pyqtSignal(list, Qt.KeyboardModifiers)  # Emits list of local file paths

    # Signals for metadata operations
    value_copied = pyqtSignal(str)  # Emitted when a value is copied
    value_edited = pyqtSignal(str, str, str)  # Emitted with (key_path, old_value, new_value)
    value_reset = pyqtSignal(str)  # Emitted with the key_path that was reset

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        # Initially hide horizontal scrollbar (will be enabled in normal mode)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Disable wordwrap
        self.setTextElideMode(Qt.ElideRight)

        # Modified metadata items
        self.modified_items: Set[str] = set()  # Set of paths for modified items

        # Context menu setup
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Track if we're in placeholder mode
        self._is_placeholder_mode: bool = True

        # Scroll position memory: {file_path: scroll_position}
        self._scroll_positions: Dict[str, int] = {}
        self._current_file_path: Optional[str] = None
        self._pending_restore_timer: Optional[QTimer] = None

        # Setup placeholder icon
        self.placeholder_label = QLabel(self.viewport())
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setVisible(False)

        icon_path = Path(__file__).parent.parent / "resources/images/metadata_tree_placeholder.png"
        self.placeholder_icon = QPixmap(str(icon_path))

        if not self.placeholder_icon.isNull():
            scaled = self.placeholder_icon.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.placeholder_label.setPixmap(scaled)
        else:
            logger.warning(f"[MetadataTree] Metadata tree placeholder icon could not be loaded from: {icon_path}")

        # Setup standard view properties
        self._setup_tree_view_properties()

    def _setup_tree_view_properties(self) -> None:
        """Configure standard tree view properties."""
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setUniformRowHeights(True)
        self.expandToDepth(1)
        self.setRootIsDecorated(False)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setAlternatingRowColors(True)  # Enable alternating row colors

    def resizeEvent(self, event):
        """Handle resize events to adjust placeholder label size."""
        super().resizeEvent(event)
        if self.placeholder_label:
            self.placeholder_label.resize(self.viewport().size())
            self.placeholder_label.move(0, 0)

    # =====================================
    # Drag & Drop Methods
    # =====================================

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        Accept drag only if it comes from our application's file table.
        This is identified by the presence of our custom MIME type.
        """
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

    def _perform_drag_cleanup(self, drag_cancel_filter: Any) -> None:
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

    def setModel(self, model: Any) -> None:
        """
        Override the setModel method to set minimum column widths after the model is set.
        """
        # NOTE: Do not save scroll position here - it's already handled in set_current_file_path()
        # The _current_file_path has already been changed to the new file at this point

        # Cancel any pending restore operation
        if self._pending_restore_timer is not None:
            self._pending_restore_timer.stop()
            self._pending_restore_timer = None

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

                # For non-placeholder mode, immediately restore scroll position
                # This prevents the "jump to 0 then scroll to final position" effect
                if self._current_file_path and self._current_file_path in self._scroll_positions:
                    # Get the saved position
                    saved_position = self._scroll_positions[self._current_file_path]

                    # Apply immediately without delay
                    QTimer.singleShot(0, lambda: self._apply_scroll_position_immediately(saved_position))
                    logger.debug(f"[MetadataTree] Scheduled immediate scroll to position {saved_position}", extra={"dev_only": True})

    def _apply_scroll_position_immediately(self, position: int) -> None:
        """Apply scroll position immediately without waiting for expandAll()."""
        if self._current_file_path and not self._is_placeholder_mode:
            scrollbar = self.verticalScrollBar()
            max_scroll = scrollbar.maximum()

            # Clamp position to valid range
            valid_position = min(position, max_scroll)
            valid_position = max(valid_position, 0)

            # Apply the position
            scrollbar.setValue(valid_position)
            logger.debug(f"[MetadataTree] Applied immediate scroll to position {valid_position}", extra={"dev_only": True})

    def _detect_placeholder_mode(self, model: Any) -> bool:
        """Detect if the model contains placeholder content."""
        # Empty model (for PNG placeholder) is also placeholder mode
        if model.rowCount() == 0:
            return True

        if model.rowCount() == 1:
            root = model.invisibleRootItem()
            if root.rowCount() == 1:
                item = root.child(0, 0)
                if item and "No file" in item.text():
                    return True
        return False

    def _configure_placeholder_mode(self, model: Any) -> None:
        """Configure view for placeholder mode with anti-flickering."""
        # Protection against repeated calls to placeholder mode - but only if ALL conditions are already met
        if (getattr(self, '_is_placeholder_mode', False) and
            self.placeholder_label and self.placeholder_label.isVisible() and
            not self.placeholder_icon.isNull()):
            return  # Already fully configured for placeholder mode, no need to reconfigure

        # Only reset current file path when entering placeholder mode
        # DO NOT clear scroll positions - we want to preserve them for other files
        self._current_file_path = None
        logger.debug("[MetadataTree] Entered placeholder mode - reset current file only", extra={"dev_only": True})

        # Use batch updates to prevent flickering during placeholder setup
        self.setUpdatesEnabled(False)

        try:
            # Show placeholder icon instead of text
            if self.placeholder_label and not self.placeholder_icon.isNull():
                self.placeholder_label.raise_()
                self.placeholder_label.show()
            else:
                logger.warning("[MetadataTree] Could not show placeholder icon - missing label or icon")

            # Placeholder mode: Fixed columns, no selection, no hover, NO HORIZONTAL SCROLLBAR
            self._update_scrollbar_policy_intelligently(Qt.ScrollBarAlwaysOff)

            header = self.header()
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.setSectionResizeMode(1, QHeaderView.Fixed)
            header.resizeSection(0, METADATA_TREE_COLUMN_WIDTHS["PLACEHOLDER_KEY_WIDTH"])
            header.resizeSection(1, METADATA_TREE_COLUMN_WIDTHS["PLACEHOLDER_VALUE_WIDTH"])

            # Disable header interactions
            header.setEnabled(False)
            header.setSectionsClickable(False)
            header.setSortIndicatorShown(False)

            # Disable tree interactions but keep drag & drop working
            self.setSelectionMode(QAbstractItemView.NoSelection)
            self.setItemsExpandable(False)
            self.setRootIsDecorated(False)
            self.setContextMenuPolicy(Qt.NoContextMenu)  # Disable context menu
            self.setMouseTracking(False)  # Disable hover effects

                        # Set placeholder property for styling
            self.setProperty("placeholder", True)

            logger.debug("[MetadataTree] Placeholder mode configured with anti-flickering", extra={"dev_only": True})

        finally:
            # Re-enable updates and force a single refresh
            self.setUpdatesEnabled(True)
            if hasattr(self, 'viewport') and callable(getattr(self.viewport(), 'update', None)):
                self.viewport().update()

    def _configure_normal_mode(self) -> None:
        """Configure view for normal content mode with anti-flickering."""
        # Use batch updates to prevent flickering during normal mode setup
        self.setUpdatesEnabled(False)

        try:
            # Hide placeholder icon when showing normal content
            if self.placeholder_label:
                self.placeholder_label.hide()

            # Normal content mode: HORIZONTAL SCROLLBAR enabled but controlled
            self._update_scrollbar_policy_intelligently(Qt.ScrollBarAsNeeded)

            header = self.header()

            # Re-enable header interactions
            header.setEnabled(True)
            header.setSectionsClickable(True)
            header.setSortIndicatorShown(False)  # Keep sorting disabled

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

            # Re-enable tree interactions
            self.setSelectionMode(QAbstractItemView.SingleSelection)
            self.setItemsExpandable(True)
            self.setRootIsDecorated(False)
            self.setContextMenuPolicy(Qt.CustomContextMenu)  # Re-enable context menu
            self.setMouseTracking(True)  # Re-enable hover effects

            # Clear placeholder property
            self.setProperty("placeholder", False)
            self.setAttribute(Qt.WA_NoMousePropagation, False)

                        # Force style update
            self._force_style_update()

            logger.debug("[MetadataTree] Normal mode configured with anti-flickering", extra={"dev_only": True})

        finally:
            # Re-enable updates and force a single refresh
            self.setUpdatesEnabled(True)
            if hasattr(self, 'viewport') and callable(getattr(self.viewport(), 'update', None)):
                self.viewport().update()

    def _update_scrollbar_policy_intelligently(self, target_policy: int) -> None:
        """Update scrollbar policy only if it differs from current to prevent unnecessary updates."""
        current_policy = self.horizontalScrollBarPolicy()
        if current_policy != target_policy:
            self.setHorizontalScrollBarPolicy(target_policy)
            logger.debug(f"[MetadataTree] Updated scrollbar policy: {current_policy} → {target_policy}", extra={"dev_only": True})

    def _make_placeholder_items_non_selectable(self, model: Any) -> None:
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
        logger.debug(f"[MetadataTree] >>> set_current_file_path called with: {file_path}", extra={"dev_only": True})

        # Skip if it's the same file (protect against duplicate calls)
        if self._current_file_path == file_path:
            logger.debug(f"[MetadataTree] Skipping duplicate call for same file: {file_path}", extra={"dev_only": True})
            return

        # Save current position before changing files (only if we have a previous file)
        if self._current_file_path is not None:
            self._save_current_scroll_position()

        # Update current file
        self._current_file_path = file_path

        logger.debug(f"[MetadataTree] Set current file: {file_path}", extra={"dev_only": True})

    def _save_current_scroll_position(self) -> None:
        """Save the current scroll position for the current file."""
        if self._current_file_path and not self._is_placeholder_mode:
            scroll_value = self.verticalScrollBar().value()
            self._scroll_positions[self._current_file_path] = scroll_value
            logger.debug(f"[MetadataTree] Saved scroll position {scroll_value} for {self._current_file_path}", extra={"dev_only": True})

    def _restore_scroll_position_for_current_file(self) -> None:
        """Restore the scroll position for the current file."""
        if self._current_file_path and not self._is_placeholder_mode:
            # Check if this is the first time viewing this file
            if self._current_file_path not in self._scroll_positions:
                # First time viewing - go to top with smooth animation
                self._smooth_scroll_to_position(0)
                logger.debug(f"[MetadataTree] First time viewing {self._current_file_path} - smooth scroll to top", extra={"dev_only": True})
                # Mark this file as visited with position 0
                self._scroll_positions[self._current_file_path] = 0
            else:
                # Restore saved position with smooth animation
                saved_position = self._scroll_positions[self._current_file_path]

                # Validate scroll position against current content
                scrollbar = self.verticalScrollBar()
                max_scroll = scrollbar.maximum()

                # Clamp the saved position to valid range
                valid_position = min(saved_position, max_scroll)
                valid_position = max(valid_position, 0)

                # Apply with smooth animation
                self._smooth_scroll_to_position(valid_position)

                if saved_position != valid_position:
                    logger.debug(f"[MetadataTree] Smooth scroll with clamped position {saved_position} -> {valid_position} (max: {max_scroll}) for {self._current_file_path}", extra={"dev_only": True})
                else:
                    logger.debug(f"[MetadataTree] Smooth scroll to restored position {valid_position} for {self._current_file_path}", extra={"dev_only": True})

        # Clean up the timer
        if self._pending_restore_timer is not None:
            self._pending_restore_timer = None

    def _smooth_scroll_to_position(self, target_position: int) -> None:
        """Smoothly scroll to the target position using animation."""
        scrollbar = self.verticalScrollBar()
        current_position = scrollbar.value()

        # If already at target position, no need to animate
        if current_position == target_position:
            return

        # Calculate animation duration based on distance
        distance = abs(target_position - current_position)
        # Base duration 150ms, with additional time for longer distances
        duration = min(150 + (distance // 10), 400)  # Max 400ms

        # Create animation
        if hasattr(self, '_scroll_animation'):
            self._scroll_animation.stop()

        from PyQt5.QtCore import QEasingCurve, QPropertyAnimation

        self._scroll_animation = QPropertyAnimation(scrollbar, b"value")
        self._scroll_animation.setDuration(duration)
        self._scroll_animation.setStartValue(current_position)
        self._scroll_animation.setEndValue(target_position)
        self._scroll_animation.setEasingCurve(QEasingCurve.OutCubic)  # Smooth deceleration
        # self._scroll_animation.setEasingCurve(QEasingCurve.InOutSine)  # Smooth sine wave motion

        # Start animation
        self._scroll_animation.start()

        logger.debug(f"[MetadataTree] Started smooth scroll animation from {current_position} to {target_position} (duration: {duration}ms)", extra={"dev_only": True})

    def clear_scroll_memory(self) -> None:
        """Clear all saved scroll positions (useful when changing folders)."""
        self._scroll_positions.clear()
        self._current_file_path = None

        # Cancel any pending restore
        if self._pending_restore_timer is not None:
            self._pending_restore_timer.stop()
            self._pending_restore_timer = None

        logger.debug("[MetadataTree] Cleared scroll position memory", extra={"dev_only": True})

    def restore_scroll_after_expand(self) -> None:
        """Trigger scroll position restore after expandAll() has completed."""
        if self._current_file_path and not self._is_placeholder_mode:
            # Use a shorter delay since we now do immediate restoration in setModel
            if self._pending_restore_timer is not None:
                self._pending_restore_timer.stop()

            self._pending_restore_timer = QTimer()
            self._pending_restore_timer.timeout.connect(self._restore_scroll_position_for_current_file)
            self._pending_restore_timer.setSingleShot(True)
            self._pending_restore_timer.start(25)  # Reduced from 100ms to 25ms for faster response

    # =====================================
    # Context Menu & Actions
    # =====================================

    def show_context_menu(self, position: QModelIndex) -> None:
        """
        Display context menu with available options depending on the selected item.
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

    def get_key_path(self, index: QModelIndex) -> str:
        """
        Return the full key path for the given index.
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

    def copy_value(self, value: Any) -> None:
        """
        Copy the value to clipboard and emit the value_copied signal.
        """
        if not value:
            return

        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(str(value))

        # Emit signal
        self.value_copied.emit(str(value))

    # =====================================
    # Metadata Editing Methods
    # =====================================

    def edit_value(self, key_path: str, current_value: Any) -> None:
        """
        Open a dialog to edit the value of a metadata field.
        """
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
            self.value_edited.emit(key_path, str(current_value), new_value)

            # Find the item in the tree and update its value
            self._update_tree_item_value(key_path, new_value)

    def _update_tree_item_value(self, key_path: str, new_value: str) -> None:
        """
        Update the value of an item in the tree view.
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

    def reset_value(self, key_path: str) -> None:
        """
        Reset the value to its original state.
        """
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

    def mark_as_modified(self, key_path: str) -> None:
        """
        Mark an item as modified.
        """
        self.modified_items.add(key_path)

        # Update the file icon in the file table
        self._update_file_icon_status()

        # Update the view
        self.viewport().update()

    # =====================================
    # Helper Methods
    # =====================================

    def _get_parent_window_with_file_table(self) -> Tuple[Optional[QWidget], Optional[Any], Optional[Any], Optional[Any]]:
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
        Update the file icon in the file table to reflect modified status.
        """
        selected_files = self._get_current_selection_via_context()
        if not selected_files:
            return

        # For each selected file, update its icon
        for file_item in selected_files:
            # Update icon based on whether we have modified items
            if self.modified_items:
                # Set modified icon
                file_item.metadata_status = "modified"
            else:
                # Set normal loaded icon
                file_item.metadata_status = "loaded"

        # Try to notify file model via ApplicationContext
        context = self._get_app_context()
        if context and hasattr(context, 'files_changed'):
            # Emit files changed signal to trigger UI updates
            context.files_changed.emit(context.get_files())
        else:
            # Fallback: use parent traversal to find file model
            parent_window, file_model, selection, selected_rows = self._get_parent_window_with_file_table()
            if file_model and selected_rows:
                for index in selected_rows:
                    row = index.row()
                    if 0 <= row < len(file_model.files):
                        # Notify model the icon has changed
                        file_model.dataChanged.emit(
                            file_model.index(row, 0),
                            file_model.index(row, 0),
                            [Qt.DecorationRole]
                        )

    def _reset_metadata_in_cache(self, key_path: str) -> None:
        """
        Reset the metadata value in the cache to its original state.
        """
        selected_files = self._get_current_selection_via_context()
        metadata_cache = self._get_metadata_cache_via_context()

        if not selected_files or not metadata_cache:
            logger.debug("[MetadataTree] No selected files or metadata cache available")
            return

        # For each selected file, reset its metadata in cache
        for file_item in selected_files:
            full_path = file_item.full_path

            # Update the metadata in cache
            metadata_entry = metadata_cache.get_entry(full_path)
            if metadata_entry and hasattr(metadata_entry, 'data'):
                self._remove_metadata_from_cache(metadata_entry.data, key_path)
                self._remove_metadata_from_file_item(file_item, key_path)

                # Update file icon status based on remaining modified items
                if not self.modified_items:
                    file_item.metadata_status = "loaded"
                else:
                    file_item.metadata_status = "modified"

        # Trigger UI update
        self._update_file_icon_status()

    def _update_metadata_in_cache(self, key_path: str, new_value: str) -> None:
        """
        Update the metadata value in the cache to persist changes.
        """
        selected_files = self._get_current_selection_via_context()
        metadata_cache = self._get_metadata_cache_via_context()

        if not selected_files or not metadata_cache:
            logger.debug("[MetadataTree] No selected files or metadata cache available")
            return

        # For each selected file, update its metadata in cache
        for file_item in selected_files:
            full_path = file_item.full_path

            # Update the metadata in cache
            metadata_entry = metadata_cache.get_entry(full_path)
            if metadata_entry and hasattr(metadata_entry, 'data'):
                self._set_metadata_in_cache(metadata_entry.data, key_path, new_value)
                self._set_metadata_in_file_item(file_item, key_path, new_value)

                # Mark file item as modified
                file_item.metadata_status = "modified"

        # Trigger UI update
        self._update_file_icon_status()

    def _remove_metadata_from_cache(self, metadata: Dict[str, Any], key_path: str) -> None:
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

    def _remove_metadata_from_file_item(self, file_item: Any, key_path: str) -> None:
        """Remove metadata entry from file item."""
        if hasattr(file_item, 'metadata') and file_item.metadata:
            self._remove_metadata_from_cache(file_item.metadata, key_path)

    def _set_metadata_in_cache(self, metadata: Dict[str, Any], key_path: str, new_value: str) -> None:
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

    def _set_metadata_in_file_item(self, file_item: Any, key_path: str, new_value: str) -> None:
        """Set metadata entry in file item."""
        if hasattr(file_item, 'metadata') and file_item.metadata:
            self._set_metadata_in_cache(file_item.metadata, key_path, new_value)

    def _handle_duplicate_rotation_entries(self, metadata: Dict[str, Any], group: str, key: str) -> None:
        """Handle duplicate rotation entries between EXIF and Other groups."""
        if key == "Rotation":
            if group == "EXIF" and "Other" in metadata and isinstance(metadata["Other"], dict) and "Rotation" in metadata["Other"]:
                del metadata["Other"]["Rotation"]
                logger.debug("[MetadataTree] Removed duplicate Other/Rotation entry", extra={"dev_only": True})
            elif group == "Other" and "EXIF" in metadata and isinstance(metadata["EXIF"], dict) and "Rotation" in metadata["EXIF"]:
                del metadata["EXIF"]["Rotation"]
                logger.debug("[MetadataTree] Removed duplicate EXIF/Rotation entry", extra={"dev_only": True})

    # =====================================
    # Scroll Override
    # =====================================

    def scrollTo(self, index: QModelIndex, hint: Union[QAbstractItemView.ScrollHint, None] = None) -> None:
        """
        Override scrollTo to prevent automatic scrolling when selections change.
        Scroll position is managed manually via the scroll position memory system.
        This prevents the table from moving when selecting cells from column 1.
        """
        if self._is_placeholder_mode:
            # In placeholder mode, use normal scrolling
            super().scrollTo(index, hint)
            return

        # In normal mode, do nothing - scroll position is managed manually
        # This prevents Qt from automatically scrolling when selections change
        return

    # =====================================
    # Metadata Display Management Methods
    # =====================================

    def show_empty_state(self, message: str = "No file selected") -> None:
        """
        Displays a placeholder in the metadata tree view.
        Uses PNG icon if available, otherwise shows text message.

        Args:
            message (str): The message to display if PNG is not available
        """
        # Create an empty model for placeholder mode
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Key", "Value"])

        # If we have a PNG placeholder, use empty model (PNG will be shown by _configure_placeholder_mode)
        # If no PNG, fallback to text placeholder
        if self.placeholder_icon.isNull():
            key_item = QStandardItem(message)
            key_item.setTextAlignment(Qt.AlignLeft)
            font = key_item.font()
            font.setItalic(True)
            key_item.setFont(font)
            key_item.setForeground(Qt.gray)
            key_item.setSelectable(False)  # Make placeholder non-selectable

            value_item = QStandardItem("-")
            value_item.setForeground(Qt.gray)
            value_item.setSelectable(False)  # Make placeholder non-selectable

            model.appendRow([key_item, value_item])

        # Model will handle selection mode and styling through setModel method
        self.setModel(model)

        # Notify parent about state change if it has the toggle button
        self._update_parent_toggle_button(expanded=False, enabled=False)

    def clear_view(self) -> None:
        """
        Clears the metadata tree view and shows a placeholder message.
        Does not clear scroll position memory when just showing placeholder.
        """
        # Don't clear scroll position memory when just showing placeholder
        # Only clear when actually changing folders
        self.show_empty_state("No file selected")

    def display_metadata(self, metadata: Optional[Dict[str, Any]], context: str = "") -> None:
        """
        Validates and displays metadata safely in the UI.

        Args:
            metadata (dict or None): The metadata to display.
            context (str): Optional source for logging (e.g. 'doubleclick', 'worker')
        """
        if not isinstance(metadata, dict) or not metadata:
            logger.warning(f"[display_metadata] Invalid metadata ({type(metadata)}) from {context}: {metadata}")
            self.clear_view()
            return

        self._render_metadata_view(metadata)

        # Notify parent about successful metadata display
        self._update_parent_toggle_button(expanded=True, enabled=True)

        # Enable header if it exists
        if hasattr(self, 'header') and callable(self.header):
            header = self.header()
            if header:
                header.setEnabled(True)

    def _render_metadata_view(self, metadata: Dict[str, Any]) -> None:
        """
        Actually builds the metadata tree and displays it.
        Assumes metadata is a non-empty dict.

        Includes fallback protection in case called with invalid metadata.
        """
        if not isinstance(metadata, dict):
            logger.error(f"[render_metadata_view] Called with invalid metadata: {type(metadata)} → {metadata}")
            self.clear_view()
            return

        try:
            # Import here to avoid circular imports
            from utils.build_metadata_tree_model import build_metadata_tree_model

            display_data = dict(metadata)
            filename = metadata.get("FileName")
            if filename:
                display_data["FileName"] = filename

            # Try to determine file path for scroll position memory
            self._set_current_file_from_metadata(metadata)

            tree_model = build_metadata_tree_model(display_data)
            self.setModel(tree_model)
            self.expandAll()

            # Trigger scroll position restore AFTER expandAll
            self.restore_scroll_after_expand()

            # Notify parent that we successfully rendered metadata
            self._update_parent_toggle_button(expanded=True, enabled=True)

        except Exception as e:
            logger.exception(f"[render_metadata_view] Unexpected error while rendering: {e}")
            self.clear_view()

    def _set_current_file_from_metadata(self, metadata: Dict[str, Any]) -> None:
        """Try to determine the current file path from metadata and set it for scroll position memory."""
        try:
            # Method 1: Try to get SourceFile from metadata
            source_file = metadata.get("SourceFile")
            if source_file:
                logger.debug(f"[ScrollMemory] Found SourceFile: {source_file}", extra={"dev_only": True})
                self.set_current_file_path(source_file)
                return

            # Method 2: Try to find current file from parent's selection
            parent_window = self._get_parent_with_file_table()
            if parent_window and hasattr(parent_window, 'file_table_view'):
                selection_model = parent_window.file_table_view.selectionModel()
                if selection_model and selection_model.hasSelection():
                    selected_rows = selection_model.selectedRows()
                    if selected_rows:
                        current_index = selection_model.currentIndex()
                        target_index = current_index if current_index.isValid() and current_index in selected_rows else selected_rows[0]

                        if hasattr(parent_window, 'file_model') and 0 <= target_index.row() < len(parent_window.file_model.files):
                            file_item = parent_window.file_model.files[target_index.row()]
                            logger.debug(f"[ScrollMemory] Found from selection: {file_item.full_path}", extra={"dev_only": True})
                            self.set_current_file_path(file_item.full_path)
                            return

            logger.debug("[ScrollMemory] Could not determine current file", extra={"dev_only": True})

        except Exception as e:
            logger.debug(f"[ScrollMemory] Error determining current file: {e}", extra={"dev_only": True})

    def _get_parent_with_file_table(self) -> Optional[QWidget]:
        """Find the parent window that has file_table_view attribute."""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'file_table_view') and hasattr(parent, 'file_model'):
                return parent
            parent = parent.parent()
        return None

    def _update_parent_toggle_button(self, expanded: bool, enabled: bool) -> None:
        """
        Updates the parent's toggle expand button state if it exists.

        Args:
            expanded (bool): Whether the tree is expanded
            enabled (bool): Whether the button should be enabled
        """
        parent_window = self._get_parent_with_file_table()
        if parent_window and hasattr(parent_window, 'toggle_expand_button'):
            button = parent_window.toggle_expand_button
            button.setEnabled(enabled)
            if enabled:
                button.setChecked(expanded)
                if expanded:
                    button.setText("Collapse All")
                    # Try to set icon if available
                    try:
                        from utils.icons_loader import get_menu_icon
                        button.setIcon(get_menu_icon("chevrons-up"))
                    except ImportError:
                        pass
                else:
                    button.setText("Expand All")
                    try:
                        from utils.icons_loader import get_menu_icon
                        button.setIcon(get_menu_icon("chevrons-down"))
                    except ImportError:
                        pass

    def toggle_expand_all(self, expand: Optional[bool] = None) -> None:
        """
        Toggles between expanding and collapsing all tree items.

        Args:
            expand (bool, optional): If provided, forces expand (True) or collapse (False).
                                   If None, toggles based on current state.
        """
        if expand is None:
            # Auto-detect current state by checking if first item is expanded
            model = self.model()
            if model and model.rowCount() > 0:
                first_index = model.index(0, 0)
                expand = not self.isExpanded(first_index)
            else:
                expand = True

        if expand:
            self.expandAll()
            self._update_parent_toggle_button(expanded=True, enabled=True)
        else:
            self.collapseAll()
            self._update_parent_toggle_button(expanded=False, enabled=True)

    # =====================================
    # Selection-based Metadata Management
    # =====================================

    def update_from_parent_selection(self) -> None:
        """
        Updates metadata display based on the current selection in the parent's file table.
        This replaces the functionality of check_selection_and_show_metadata from MainWindow.
        """
        parent_window = self._get_parent_with_file_table()
        if not parent_window:
            self.clear_view()
            return

        # Get selection from parent's file table
        if not hasattr(parent_window, 'file_table_view'):
            self.clear_view()
            return

        selection_model = parent_window.file_table_view.selectionModel()
        if not selection_model:
            self.clear_view()
            return

        selected_rows = selection_model.selectedRows()

        if not selected_rows:
            self.clear_view()
            return

        # Prefer currentIndex if it's valid and selected
        current_index = selection_model.currentIndex()
        target_index = None

        if (
            current_index.isValid()
            and current_index in selected_rows
            and hasattr(parent_window, 'file_model')
            and 0 <= current_index.row() < len(parent_window.file_model.files)
        ):
            target_index = current_index
        else:
            target_index = selected_rows[0]  # fallback

        if (hasattr(parent_window, 'file_model') and
            0 <= target_index.row() < len(parent_window.file_model.files)):

            file_item = parent_window.file_model.files[target_index.row()]

            # Get metadata from file_item or cache
            metadata = None
            if hasattr(file_item, 'metadata') and file_item.metadata:
                metadata = file_item.metadata
            elif hasattr(parent_window, 'metadata_cache'):
                metadata = parent_window.metadata_cache.get(file_item.full_path)

            if isinstance(metadata, dict) and metadata:
                display_metadata = dict(metadata)
                display_metadata["FileName"] = file_item.filename

                # Set current file path for scroll position memory
                self.set_current_file_path(file_item.full_path)

                self.display_metadata(display_metadata, context="update_from_parent_selection")
                return

        self.clear_view()

    def refresh_metadata_from_selection(self) -> None:
        """
        Convenience method that triggers metadata update from parent selection.
        Can be called from parent window when selection changes.
        """
        self.update_from_parent_selection()

    def connect_toggle_button(self) -> None:
        """
        Connects the parent's toggle expand button to this tree view's functionality.
        Should be called after the tree view is added to its parent.
        """
        parent_window = self._get_parent_with_file_table()
        if parent_window and hasattr(parent_window, 'toggle_expand_button'):
            button = parent_window.toggle_expand_button

            # Disconnect any existing connections to avoid double-connections
            try:
                button.toggled.disconnect()
            except TypeError:
                pass  # No connections to disconnect

            # Connect to our toggle method
            button.toggled.connect(self.toggle_expand_all)

            logger.debug("[MetadataTreeView] Toggle button connected successfully")
        else:
            logger.warning("[MetadataTreeView] Could not find toggle button to connect")

    def initialize_with_parent(self) -> None:
        """
        Performs initial setup that requires parent window to be available.
        Should be called after the tree view is added to its parent.
        """
        self.connect_toggle_button()
        self.show_empty_state("No file selected")

    # =====================================
    # Unified Metadata Management Interface
    # =====================================

    def clear_for_folder_change(self) -> None:
        """
        Clears both view and scroll memory when changing folders.
        This is different from clear_view() which preserves scroll memory.
        """
        self.clear_scroll_memory()
        self.clear_view()

    def display_file_metadata(self, file_item: Any, context: str = "file_display") -> None:
        """
        Display metadata for a specific file item.
        Handles metadata extraction from file_item or cache automatically.

        Args:
            file_item: FileItem object with metadata
            context: Context string for logging
        """
        if not file_item:
            self.clear_view()
            return

        # Get metadata from file_item or cache
        metadata = None
        if hasattr(file_item, 'metadata') and file_item.metadata:
            metadata = file_item.metadata
        else:
            # Try to get from parent's cache
            parent_window = self._get_parent_with_file_table()
            if parent_window and hasattr(parent_window, 'metadata_cache'):
                metadata = parent_window.metadata_cache.get(file_item.full_path)

        if isinstance(metadata, dict) and metadata:
            display_metadata = dict(metadata)
            display_metadata["FileName"] = file_item.filename

            # Set current file path for scroll position memory
            self.set_current_file_path(file_item.full_path)

            self.display_metadata(display_metadata, context=context)
        else:
            self.clear_view()

    def handle_selection_change(self) -> None:
        """
        Handle selection changes from the parent file table.
        This is a convenience method that can be connected to selection signals.
        """
        self.refresh_metadata_from_selection()

    def handle_invert_selection(self, metadata: Optional[Dict[str, Any]]) -> None:
        """
        Handle metadata display after selection inversion.

        Args:
            metadata: The metadata to display, or None to clear
        """
        if isinstance(metadata, dict) and metadata:
            self.display_metadata(metadata, context="invert_selection")
        else:
            self.clear_view()

    def handle_metadata_load_completion(self, metadata: Optional[Dict[str, Any]], source: str) -> None:
        """
        Handle metadata display after a metadata loading operation completes.

        Args:
            metadata: The loaded metadata, or None if loading failed
            source: Source of the metadata loading (e.g., "worker", "cache")
        """
        if isinstance(metadata, dict) and metadata:
            self.display_metadata(metadata, context=f"load_completion_from_{source}")
        else:
            self.clear_view()

    def _get_app_context(self):
        """Get ApplicationContext with fallback to None."""
        if get_app_context is None:
            return None
        try:
            return get_app_context()
        except RuntimeError:
            # ApplicationContext not ready yet
            return None

    def _get_current_selection_via_context(self):
        """Get current selection via ApplicationContext with fallback to parent traversal."""
        context = self._get_app_context()
        if context and context.selection_store:
            try:
                selected_rows = context.selection_store.get_selected_rows()
                if selected_rows and hasattr(context, '_files') and context._files:
                    # Convert row indices to file items
                    selected_files = []
                    for row in selected_rows:
                        if 0 <= row < len(context._files):
                            selected_files.append(context._files[row])
                    return selected_files
            except Exception as e:
                logger.debug(f"[MetadataTree] Failed to get selection via context: {e}")

        # Fallback to parent traversal
        return self._get_selection_via_parent_traversal()

    def _get_selection_via_parent_traversal(self):
        """Legacy method for getting selection via parent traversal."""
        parent_window, file_model, selection, selected_rows = self._get_parent_window_with_file_table()
        if not all([parent_window, file_model, selected_rows]):
            return []

        selected_files = []
        for index in selected_rows:
            row = index.row()
            if 0 <= row < len(file_model.files):
                selected_files.append(file_model.files[row])
        return selected_files

    def _get_metadata_cache_via_context(self):
        """Get metadata cache via ApplicationContext with fallback to parent traversal."""
        context = self._get_app_context()
        if context and hasattr(context, '_metadata_cache'):
            return context._metadata_cache

        # Fallback to parent traversal
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'metadata_cache'):
            parent_window = parent_window.parent()

        if parent_window and hasattr(parent_window, 'metadata_cache'):
            return parent_window.metadata_cache

        return None

