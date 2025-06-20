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
from typing import Any, Dict, Optional, Set, Union

from PyQt5.QtCore import QModelIndex, Qt, QTimer, pyqtSignal, QSortFilterProxyModel
from PyQt5.QtGui import (
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
    QIcon,
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
from utils.path_utils import paths_equal
from utils.timer_manager import schedule_drag_cleanup, schedule_scroll_adjust
from widgets.file_tree_view import _drag_cancel_filter
from widgets.metadata_edit_dialog import MetadataEditDialog

# ApplicationContext integration
try:
    from core.application_context import get_app_context
except ImportError:
    get_app_context = None

logger = get_cached_logger(__name__)


class MetadataProxyModel(QSortFilterProxyModel):
    """Custom proxy model for metadata tree filtering."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setRecursiveFilteringEnabled(True)  # Enable hierarchical filtering

    def filterAcceptsRow(self, source_row, source_parent):
        """
        Custom filter logic for metadata tree.
        Shows a row if:
        1. The row itself matches the filter
        2. Any of its children match the filter
        3. Its parent matches the filter
        """
        if not self.filterRegExp().pattern():
            return True

        source_model = self.sourceModel()
        if not source_model:
            return True

        # Get the current item
        index = source_model.index(source_row, 0, source_parent)
        if not index.isValid():
            return True

        # Check if current item matches (key or value)
        key_index = source_model.index(source_row, 0, source_parent)
        value_index = source_model.index(source_row, 1, source_parent)

        key_text = source_model.data(key_index, Qt.DisplayRole) or ""
        value_text = source_model.data(value_index, Qt.DisplayRole) or ""

        pattern = self.filterRegExp().pattern()

        # Check if this item matches
        if (pattern.lower() in key_text.lower() or
            pattern.lower() in value_text.lower()):
            return True

        # Check if any child matches
        if source_model.hasChildren(index):
            for i in range(source_model.rowCount(index)):
                if self.filterAcceptsRow(i, index):
                    return True

        return False


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

        # Modified metadata items per file
        # Format: {file_path: set(modified_key_paths)}
        self.modified_items_per_file: Dict[str, Set[str]] = {}
        # Current file's modified items (cached for performance)
        self.modified_items: Set[str] = set()

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

        # Timer for update debouncing (use timer_manager)
        self._update_timer_id = None

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
        Process drops from the file table to load metadata.
        Only accepts drops with our custom MIME type.
        """
        logger.debug("[MetadataTreeView] Drop event received", extra={"dev_only": True})

        # Get the global drag cancel filter

        # Only process drops from our file table
        if event.mimeData().hasFormat("application/x-oncutf-filetable"):
            urls = event.mimeData().urls()
            files = [url.toLocalFile() for url in urls if url.isLocalFile()]
            if files:
                logger.debug(f"[MetadataTreeView] Processing drop of {len(files)} files", extra={"dev_only": True})
                # Accept the event BEFORE emitting the signal
                event.acceptProposedAction()
                self._perform_drag_cleanup(_drag_cancel_filter)
                # Then emit signal for processing
                logger.debug("[MetadataTreeView] Emitting files_dropped signal", extra={"dev_only": True})
                self.files_dropped.emit(files, event.keyboardModifiers())
            else:
                logger.debug("[MetadataTreeView] No valid files in drop", extra={"dev_only": True})
                event.ignore()
                self._perform_drag_cleanup(_drag_cancel_filter)
        else:
            logger.debug("[MetadataTreeView] Drop ignored - wrong MIME type", extra={"dev_only": True})
            event.ignore()
            self._perform_drag_cleanup(_drag_cancel_filter)

        # Schedule drag cleanup
        schedule_drag_cleanup(self._complete_drag_cleanup, 0)

    def _perform_drag_cleanup(self, drag_cancel_filter: Any) -> None:
        """Centralized drag cleanup logic."""
        # Force cleanup of any drag state
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
        self.viewport().update()

    def _complete_drag_cleanup(self) -> None:
        """Complete cleanup after drag operation."""
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

                    # Schedule scroll position restoration
                    schedule_scroll_adjust(lambda: self._apply_scroll_position_immediately(saved_position), 0)

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
        """
        Set the current file path and manage scroll position restoration.
        """
        # If it's the same file, don't do anything
        if paths_equal(self._current_file_path, file_path):
            logger.debug(f"[MetadataTreeView] Same file path, skipping: {file_path}", extra={"dev_only": True})
            return

        # Save current data before changing files (only if we have a previous file)
        if self._current_file_path is not None:
            self._save_current_scroll_position()
            # Save current modified items for the previous file
            if self.modified_items:
                self.modified_items_per_file[self._current_file_path] = self.modified_items.copy()
                logger.debug(f"[MetadataTree] Saved {len(self.modified_items)} modified items for {self._current_file_path}", extra={"dev_only": True})

        # Update current file
        self._current_file_path = file_path

        # Load modified items for the new file
        if file_path in self.modified_items_per_file:
            self.modified_items = self.modified_items_per_file[file_path].copy()
            logger.debug(f"[MetadataTree] Loaded {len(self.modified_items)} modified items for {file_path}", extra={"dev_only": True})
        else:
            self.modified_items = set()
            logger.debug(f"[MetadataTree] No modified items for {file_path}", extra={"dev_only": True})

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
            self._pending_restore_timer.stop()

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
        Uses consistent styling and icons like the specified text module.
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

        # Check if we have multiple files selected - disable Edit/Reset for multiple selection
        selected_files = self._get_current_selection()
        has_multiple_selection = len(selected_files) > 1

        # Create menu with consistent styling
        menu = QMenu(self)

        # Edit value action (with edit icon)
        edit_action = QAction("Edit Value", menu)
        edit_action.setIcon(self._get_menu_icon("edit"))
        edit_action.triggered.connect(lambda: self.edit_value(key_path, value))

        # Enable Edit only if:
        # 1. Single file selection (not multiple)
        # 2. Field is rotation
        can_edit = not has_multiple_selection and "Rotation" in key_path
        edit_action.setEnabled(can_edit)

        if has_multiple_selection:
            edit_action.setToolTip("Edit disabled for multiple file selection")
        elif "Rotation" not in key_path:
            edit_action.setToolTip("Edit only available for Rotation fields")
        else:
            edit_action.setToolTip("Edit this metadata value")

        menu.addAction(edit_action)

        # Set to 0 action (with refresh-cw icon)
        if "Rotation" in key_path:
            set_zero_action = QAction("Set Rotation to 0°", menu)
        else:
            set_zero_action = QAction("Set to 0", menu)
        set_zero_action.setIcon(self._get_menu_icon("refresh-cw"))
        set_zero_action.triggered.connect(lambda: self.set_rotation_to_zero(key_path))

        # Enable Set to 0 only if:
        # 1. Single file selection (not multiple)
        # 2. Field is rotation
        # 3. Current value is not already 0
        current_value_str = str(value) if value is not None else ""
        is_not_zero = current_value_str not in ["0", "0°", ""]
        can_set_zero = not has_multiple_selection and "Rotation" in key_path and is_not_zero
        set_zero_action.setEnabled(can_set_zero)

        if has_multiple_selection:
            set_zero_action.setToolTip("Set to 0 disabled for multiple file selection")
        elif "Rotation" not in key_path:
            set_zero_action.setToolTip("Set to 0 only available for Rotation fields")
        elif not is_not_zero:
            set_zero_action.setToolTip("Value is already 0")
        else:
            set_zero_action.setToolTip("Set rotation to 0° (no rotation)")

        menu.addAction(set_zero_action)

        # Reset value action (with rotate-ccw icon)
        reset_action = QAction("Reset Value", menu)
        reset_action.setIcon(self._get_menu_icon("rotate-ccw"))
        reset_action.triggered.connect(lambda: self.reset_value(key_path))

        # Enable Reset only if:
        # 1. Single file selection (not multiple)
        # 2. Field is rotation
        # 3. Field has been modified (is in modified_items)
        # Check both the exact key_path and normalized "Rotation" key
        normalized_key_path = "Rotation" if "rotation" in key_path.lower() else key_path
        has_been_modified = normalized_key_path in self.modified_items
        can_reset = not has_multiple_selection and "Rotation" in key_path and has_been_modified
        reset_action.setEnabled(can_reset)

        if has_multiple_selection:
            reset_action.setToolTip("Reset disabled for multiple file selection")
        elif "Rotation" not in key_path:
            reset_action.setToolTip("Reset only available for Rotation fields")
        elif not has_been_modified:
            reset_action.setToolTip("No changes to reset")
        else:
            reset_action.setToolTip("Reset this field to original value")

        menu.addAction(reset_action)
        menu.addSeparator()

        # Copy value action (with copy icon)
        copy_action = QAction("Copy", menu)
        copy_action.setIcon(self._get_menu_icon("copy"))
        copy_action.triggered.connect(lambda: self.copy_value(value))
        copy_action.setEnabled(bool(value))
        menu.addAction(copy_action)

        # Show menu
        menu.exec_(self.viewport().mapToGlobal(position))

    def _get_menu_icon(self, icon_name: str):
        """Get menu icon using the same system as specified text module."""
        try:
            from utils.icons_loader import get_menu_icon
            return get_menu_icon(icon_name)
        except ImportError:
            return None

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
        SIMPLIFIED: For rotation, always use "Rotation" as key_path.
        """
        # Normalize rotation key_path to be always "Rotation" (top-level)
        if "rotation" in key_path.lower():
            normalized_key_path = "Rotation"
        else:
            normalized_key_path = key_path

        accepted, new_value = MetadataEditDialog.get_value(
            parent=self,
            key_path=normalized_key_path,
            current_value=str(current_value)
        )

        if accepted and new_value != str(current_value):
            # Add to modified items (use normalized path)
            self.modified_items.add(normalized_key_path)

            # Update metadata in cache FIRST
            self._update_metadata_in_cache(normalized_key_path, new_value)

            # Update the file icon in the file table to show it's modified
            self._update_file_icon_status()

            # Emit signal with the new value
            self.value_edited.emit(normalized_key_path, str(current_value), new_value)

            # FORCE a complete refresh of the metadata display to show the change immediately
            self.update_from_parent_selection()

    def _get_original_value_from_cache(self, key_path: str) -> Optional[Any]:
        """
        Get the original value of a metadata field from the cache.
        This should be called before resetting to get the original value.
        """
        selected_files = self._get_current_selection()
        metadata_cache = self._get_metadata_cache()

        if not selected_files or not metadata_cache:
            logger.debug("[MetadataTree] No selected files or metadata cache available", extra={"dev_only": True})
            return None

        # Get the first selected file to get original value
        file_item = selected_files[0]
        full_path = file_item.full_path

        # Try to get original metadata (unmodified) from cache
        metadata_entry = metadata_cache.get_entry(full_path)
        if not metadata_entry or not hasattr(metadata_entry, 'data'):
            return None

        # If the entry is not modified, get value directly
        # If it is modified, we need to get the original value from the file system
        # For now, we'll reconstruct from the file's original metadata
        if hasattr(file_item, 'metadata') and file_item.metadata:
            # Get from file item's original metadata
            return self._get_value_from_metadata_dict(file_item.metadata, key_path)

        # Fallback: get from cache data
        return self._get_value_from_metadata_dict(metadata_entry.data, key_path)

    def _get_value_from_metadata_dict(self, metadata: Dict[str, Any], key_path: str) -> Optional[Any]:
        """
        Extract a value from metadata dictionary using key path.
        """
        parts = key_path.split('/')

        if len(parts) == 1:
            # Top-level key
            return metadata.get(parts[0])
        elif len(parts) == 2:
            # Nested key (group/key)
            group, key = parts
            if group in metadata and isinstance(metadata[group], dict):
                return metadata[group].get(key)

        return None

    def set_rotation_to_zero(self, key_path: str) -> None:
        """
        Set the rotation value to 0° (specifically for rotation fields).
        """
        # Get current value for the signal
        selected_files = self._get_current_selection()
        if not selected_files:
            return

        # Get current value from the first selected file
        current_value = None
        file_item = selected_files[0]
        if hasattr(file_item, 'metadata') and file_item.metadata:
            current_value = self._get_value_from_metadata_dict(file_item.metadata, key_path)

        # Normalize rotation key_path to be always "Rotation" (top-level)
        if "rotation" in key_path.lower():
            normalized_key_path = "Rotation"
        else:
            normalized_key_path = key_path

        new_value = "0"

        # Add to modified items
        self.modified_items.add(normalized_key_path)

        # Update metadata in cache
        self._update_metadata_in_cache(normalized_key_path, new_value)

        # Update the file icon in the file table to show it's modified
        self._update_file_icon_status()

        # Emit signal with the new value
        self.value_edited.emit(normalized_key_path, str(current_value) if current_value else "", new_value)

        # FORCE a complete refresh of the metadata display to show the change immediately
        self.update_from_parent_selection()

    def reset_value(self, key_path: str) -> None:
        """
        Reset the value to its original state.
        """
        # Get the original value before resetting
        original_value = self._get_original_value_from_cache(key_path)

        # Remove from modified items
        if key_path in self.modified_items:
            self.modified_items.remove(key_path)

        # Update the file icon in the file table
        self._update_file_icon_status()

        # Update the view
        self.viewport().update()

        # Reset value in cache
        self._reset_metadata_in_cache(key_path)

        # Update the tree view to show the original value
        if original_value is not None:
            self._update_tree_item_value(key_path, str(original_value))

        # Emit signal
        self.value_reset.emit(key_path)

    def _update_tree_item_value(self, key_path: str, new_value: str) -> None:
        """
        Update the display value of a tree item to reflect changes.
        This forces a refresh of the metadata display.
        """
        # For now, just trigger a complete refresh
        # This ensures the updated value is displayed correctly
        self.update_from_parent_selection()

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

    def _get_parent_with_file_table(self) -> Optional[QWidget]:
        """Find the parent window that has file_table_view attribute."""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'file_table_view') and hasattr(parent, 'file_model'):
                return parent
            parent = parent.parent()
        return None

    def _get_current_selection(self):
        """Get current selection via parent traversal."""
        parent_window = self._get_parent_with_file_table()

        if not parent_window:
            logger.debug("[MetadataTree] No parent window found", extra={"dev_only": True})
            return []

        # Get the current selected file
        selection = parent_window.file_table_view.selectionModel()
        if not selection or not selection.hasSelection():
            logger.debug("[MetadataTree] No selection found", extra={"dev_only": True})
            return []

        selected_rows = selection.selectedRows()
        if not selected_rows:
            logger.debug("[MetadataTree] No selected rows found", extra={"dev_only": True})
            return []

        # Get the file model
        file_model = parent_window.file_model
        if not file_model:
            logger.debug("[MetadataTree] No file model found", extra={"dev_only": True})
            return []

        selected_files = []
        for index in selected_rows:
            row = index.row()
            if 0 <= row < len(file_model.files):
                selected_files.append(file_model.files[row])

        logger.debug(f"[MetadataTree] Found {len(selected_files)} selected files", extra={"dev_only": True})
        return selected_files

    def _get_metadata_cache(self):
        """Get metadata cache via parent traversal."""
        parent_window = self._get_parent_with_file_table()
        if parent_window and hasattr(parent_window, 'metadata_cache'):
            logger.debug("[MetadataTree] Found metadata cache", extra={"dev_only": True})
            return parent_window.metadata_cache

        logger.debug("[MetadataTree] No metadata cache found", extra={"dev_only": True})
        return None

    def _update_file_icon_status(self) -> None:
        """
        Update the file icon in the file table to reflect modified status.
        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return

        # For each selected file, update its icon
        for file_item in selected_files:
            # Check if this specific file has modified items
            file_path = file_item.full_path

            # Check both current modified items and stored ones
            has_modifications = False
            if file_path == self._current_file_path and self.modified_items:
                has_modifications = True
            elif file_path in self.modified_items_per_file and self.modified_items_per_file[file_path]:
                has_modifications = True

            # Update icon based on whether we have modified items
            if has_modifications:
                # Set modified icon
                file_item.metadata_status = "modified"
            else:
                # Set normal loaded icon
                file_item.metadata_status = "loaded"

        # Get parent window and file model
        parent_window = self._get_parent_with_file_table()
        if not parent_window:
            return

        # Get the current selected file
        selection = parent_window.file_table_view.selectionModel()
        if not selection or not selection.hasSelection():
            return

        selected_rows = selection.selectedRows()
        if not selected_rows:
            return

        # Get the file model
        file_model = parent_window.file_model
        if not file_model:
            return

        # Emit dataChanged for all selected rows to update their icons
        for index in selected_rows:
            row = index.row()
            if 0 <= row < len(file_model.files):
                # Emit dataChanged specifically for the icon column (column 0)
                icon_index = file_model.index(row, 0)
                file_model.dataChanged.emit(
                    icon_index,
                    icon_index,
                    [Qt.DecorationRole]
                )
                logger.debug(f"[MetadataTree] Updated icon for row {row}", extra={"dev_only": True})

    def _reset_metadata_in_cache(self, key_path: str) -> None:
        """
        Reset the metadata value in the cache to its original state.
        """
        selected_files = self._get_current_selection()
        metadata_cache = self._get_metadata_cache()

        if not selected_files or not metadata_cache:
            logger.debug("[MetadataTree] No selected files or metadata cache available", extra={"dev_only": True})
            return

        # For each selected file, reset its metadata in cache
        for file_item in selected_files:
            full_path = file_item.full_path

            # Get the original value from file item's metadata
            original_value = None
            if hasattr(file_item, 'metadata') and file_item.metadata:
                original_value = self._get_value_from_metadata_dict(file_item.metadata, key_path)

            # Update the metadata in cache
            metadata_entry = metadata_cache.get_entry(full_path)
            if metadata_entry and hasattr(metadata_entry, 'data'):
                if original_value is not None:
                    # Restore the original value
                    self._set_metadata_in_cache(metadata_entry.data, key_path, str(original_value))
                    self._set_metadata_in_file_item(file_item, key_path, str(original_value))
                else:
                    # If no original value, remove the modified entry
                    self._remove_metadata_from_cache(metadata_entry.data, key_path)
                    self._remove_metadata_from_file_item(file_item, key_path)

                # Update file icon status based on remaining modified items
                if not self.modified_items:
                    file_item.metadata_status = "loaded"
                    metadata_entry.modified = False
                else:
                    file_item.metadata_status = "modified"

        # Trigger UI update
        self._update_file_icon_status()

    def _update_metadata_in_cache(self, key_path: str, new_value: str) -> None:
        """
        Update the metadata value in the cache to persist changes.
        SIMPLIFIED: Rotation is always a top-level field.
        """
        selected_files = self._get_current_selection()
        metadata_cache = self._get_metadata_cache()

        if not selected_files or not metadata_cache:
            logger.debug("[MetadataTree] No selected files or metadata cache available", extra={"dev_only": True})
            return

        # For each selected file, update its metadata in cache
        for file_item in selected_files:
            full_path = file_item.full_path

            # Update the metadata in cache
            metadata_entry = metadata_cache.get_entry(full_path)
            if metadata_entry and hasattr(metadata_entry, 'data'):
                parts = key_path.split('/')

                # Special handling for rotation - it's ALWAYS a top-level field
                if len(parts) == 2 and parts[1].lower() == "rotation":
                    # Remove any existing rotation entries from anywhere
                    if "Rotation" in metadata_entry.data:
                        del metadata_entry.data["Rotation"]
                    if "rotation" in metadata_entry.data:
                        del metadata_entry.data["rotation"]

                    # Remove from any groups too (cleanup)
                    for existing_group, existing_data in list(metadata_entry.data.items()):
                        if isinstance(existing_data, dict):
                            if "Rotation" in existing_data:
                                del existing_data["Rotation"]
                            if "rotation" in existing_data:
                                del existing_data["rotation"]

                    # Add as top-level field (this is how ExifTool stores it)
                    metadata_entry.data["Rotation"] = new_value
                    logger.debug(f"[MetadataTree] Set top-level Rotation = {new_value}", extra={"dev_only": True})

                    # Also update in file_item
                    if hasattr(file_item, 'metadata') and file_item.metadata:
                        # Clean up file_item metadata too
                        if "Rotation" in file_item.metadata:
                            del file_item.metadata["Rotation"]
                        if "rotation" in file_item.metadata:
                            del file_item.metadata["rotation"]

                        for existing_group, existing_data in list(file_item.metadata.items()):
                            if isinstance(existing_data, dict):
                                if "Rotation" in existing_data:
                                    del existing_data["Rotation"]
                                if "rotation" in existing_data:
                                    del existing_data["rotation"]

                        # Set as top-level
                        file_item.metadata["Rotation"] = new_value
                elif len(parts) == 1 and parts[0].lower() == "rotation":
                    # Direct top-level rotation
                    metadata_entry.data["Rotation"] = new_value
                    logger.debug(f"[MetadataTree] Set top-level Rotation = {new_value}", extra={"dev_only": True})

                    if hasattr(file_item, 'metadata') and file_item.metadata:
                        file_item.metadata["Rotation"] = new_value
                else:
                    # Normal handling for non-rotation fields
                    self._set_metadata_in_cache(metadata_entry.data, key_path, new_value)
                    self._set_metadata_in_file_item(file_item, key_path, new_value)

                # Mark the entry as modified
                metadata_entry.modified = True

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

    def _set_metadata_in_file_item(self, file_item: Any, key_path: str, new_value: str) -> None:
        """Set metadata entry in file item. SIMPLIFIED: Rotation is always top-level."""
        if hasattr(file_item, 'metadata') and file_item.metadata:
            # Special handling for rotation - it's always top-level
            if key_path.lower() == "rotation":
                # Clean up any existing rotation entries
                if "Rotation" in file_item.metadata:
                    del file_item.metadata["Rotation"]
                if "rotation" in file_item.metadata:
                    del file_item.metadata["rotation"]

                # Remove from any groups too
                for existing_group, existing_data in list(file_item.metadata.items()):
                    if isinstance(existing_data, dict):
                        if "Rotation" in existing_data:
                            del existing_data["Rotation"]
                        if "rotation" in existing_data:
                            del existing_data["rotation"]

                # Set as top-level
                file_item.metadata["Rotation"] = new_value
            else:
                # Normal handling for non-rotation fields
                self._set_metadata_in_cache(file_item.metadata, key_path, new_value)

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
            super().scrollTo(index, hint) # type: ignore
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

        # Use proxy model for consistency, even for placeholder content
        parent_window = self._get_parent_with_file_table()
        if parent_window and hasattr(parent_window, 'metadata_proxy_model'):
            # Set the placeholder model as source model to the proxy model
            parent_window.metadata_proxy_model.setSourceModel(model)
            # Make sure the tree view uses the proxy model
            if self.model() != parent_window.metadata_proxy_model:
                super().setModel(parent_window.metadata_proxy_model)
        else:
            # Fallback: set model directly if proxy model is not available
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
        # Disable search field when clearing view
        self._update_search_field_state(False)

    def display_metadata(self, metadata: Optional[Dict[str, Any]], context: str = "") -> None:
        """
        Display metadata in the tree view with simple, direct rendering.

        Args:
            metadata: Dictionary containing metadata to display
            context: Context string for debugging
        """
        if not isinstance(metadata, dict) or not metadata:
            logger.debug(f"[MetadataTree] No metadata to display (context: {context})", extra={"dev_only": True})
            self.clear_view()
            # Disable search field when no metadata
            self._update_search_field_state(False)
            return

        logger.debug(f"[MetadataTree] Displaying metadata for file (context: {context})", extra={"dev_only": True})
        # Enable search field when metadata is available
        self._update_search_field_state(True)
        self._render_metadata_view(metadata)

    def _update_search_field_state(self, enabled: bool):
        """Update the metadata search field enabled state and tooltip."""
        parent_window = self._get_parent_with_file_table()
        if not parent_window or not hasattr(parent_window, 'metadata_search_field'):
            return

        search_field = parent_window.metadata_search_field

        if enabled:
            search_field.setEnabled(True)
            search_field.setReadOnly(False)
            search_field.setToolTip("Search metadata...")
            # Clear any custom styling for enabled state
            search_field.setStyleSheet("")
            # Restore any saved search text
            if hasattr(parent_window, 'ui_manager'):
                parent_window.ui_manager.restore_metadata_search_text()
        else:
            # Don't disable the entire field - just make it read-only
            # This prevents the search icon from becoming lighter
            search_field.setEnabled(True)
            search_field.setReadOnly(True)
            search_field.setToolTip("No metadata available")
            # Apply custom styling to show it's disabled but keep icons normal
            search_field.setStyleSheet("""
                QLineEdit[readOnly="true"] {
                    color: #666;
                    background-color: #2b2b2b;
                    border: 1px solid #555;
                }
            """)
            # Don't clear the search text - preserve it for when metadata is available again



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

            # Apply any modified values that the user has changed in the UI
            self._apply_modified_values_to_display_data(display_data)

            # Try to determine file path for scroll position memory
            self._set_current_file_from_metadata(metadata)

            tree_model = build_metadata_tree_model(display_data, self.modified_items)

            # Use proxy model for filtering instead of setting model directly
            parent_window = self._get_parent_with_file_table()
            if parent_window and hasattr(parent_window, 'metadata_proxy_model'):
                # Set the source model to the proxy model
                parent_window.metadata_proxy_model.setSourceModel(tree_model)
                # Make sure the tree view uses the proxy model
                if self.model() != parent_window.metadata_proxy_model:
                    super().setModel(parent_window.metadata_proxy_model)
            else:
                # Fallback: set model directly if proxy model is not available
                self.setModel(tree_model)

            self.expandAll()

            # Trigger scroll position restore AFTER expandAll
            self.restore_scroll_after_expand()

            # Notify parent that we successfully rendered metadata
            # Groups are always expanded - no toggle functionality needed

        except Exception as e:
            logger.exception(f"[render_metadata_view] Unexpected error while rendering: {e}")
            self.clear_view()

    def _apply_modified_values_to_display_data(self, display_data: Dict[str, Any]) -> None:
        """
        Apply any modified values from the UI to the display data.
        SIMPLIFIED: Rotation is always top-level, no complex group logic.
        """
        if not self.modified_items:
            return

        # Get the current metadata cache to get the modified values
        selected_files = self._get_current_selection()
        metadata_cache = self._get_metadata_cache()

        if not selected_files or not metadata_cache:
            return

        # For single file selection only (for now)
        if len(selected_files) != 1:
            return

        file_item = selected_files[0]
        metadata_entry = metadata_cache.get_entry(file_item.full_path)

        if not metadata_entry or not hasattr(metadata_entry, 'data'):
            return

        # Apply each modified value to the display_data
        logger.debug(f"[MetadataTree] Applying {len(self.modified_items)} modified items", extra={"dev_only": True})

        for key_path in self.modified_items:
            logger.debug(f"[MetadataTree] Processing modified item: {key_path}", extra={"dev_only": True})

            # Special handling for rotation - it's always top-level
            if key_path.lower() == "rotation":
                if "Rotation" in metadata_entry.data:
                    current_rotation = metadata_entry.data["Rotation"]
                    display_data["Rotation"] = current_rotation
                    logger.debug(f"[MetadataTree] Applied Rotation: {current_rotation}", extra={"dev_only": True})
                else:
                    logger.warning("[MetadataTree] Rotation not found in cache data!")
                continue

            # Handle other fields normally
            parts = key_path.split('/')

            if len(parts) == 1:
                # Top-level key
                key = parts[0]
                if key in metadata_entry.data:
                    display_data[key] = metadata_entry.data[key]
                    logger.debug(f"[MetadataTree] Applied {key_path}: {metadata_entry.data[key]}", extra={"dev_only": True})
            elif len(parts) == 2:
                # Nested key (group/key)
                group, key = parts
                if group in metadata_entry.data and isinstance(metadata_entry.data[group], dict):
                    if key in metadata_entry.data[group]:
                        # Ensure the group exists in display_data
                        if group not in display_data:
                            display_data[group] = {}
                        elif not isinstance(display_data[group], dict):
                            display_data[group] = {}

                        display_data[group][key] = metadata_entry.data[group][key]
                        logger.debug(f"[MetadataTree] Applied {key_path}: {metadata_entry.data[group][key]}", extra={"dev_only": True})

        # Clean up any empty groups
        self._cleanup_empty_groups(display_data)

    def _cleanup_empty_groups(self, display_data: Dict[str, Any]) -> None:
        """
        Remove any empty groups from display_data.
        This prevents showing empty group headers in the tree.
        """
        empty_groups = []

        # Check which groups have modified items
        groups_with_modifications = set()
        for key_path in self.modified_items:
            if "/" in key_path:
                group_name = key_path.split("/")[0]
                groups_with_modifications.add(group_name)

        for group_name, group_data in display_data.items():
            if isinstance(group_data, dict) and len(group_data) == 0:
                # Don't remove groups that have modified items (they will be populated)
                if group_name not in groups_with_modifications:
                    empty_groups.append(group_name)
                    logger.debug(f"[MetadataTree] Found empty group to remove: {group_name}", extra={"dev_only": True})
            else:
                logger.debug(f"[MetadataTree] Keeping empty group {group_name} - has modifications", extra={"dev_only": True})

        for group_name in empty_groups:
            display_data.pop(group_name, None)
            logger.debug(f"[MetadataTree] Removed empty group: {group_name}", extra={"dev_only": True})

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
        Simple metadata display based on current selection - no complex logic.
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

        # Always use the last selected row - simple and predictable
        target_index = selected_rows[-1]

        if (hasattr(parent_window, 'file_model') and
            0 <= target_index.row() < len(parent_window.file_model.files)):

            file_item = parent_window.file_model.files[target_index.row()]

            # Get metadata from cache first (to preserve modifications), then fallback to file_item
            metadata = None
            if hasattr(parent_window, 'metadata_cache'):
                # Get metadata from cache - this includes any modifications
                cache_entry = parent_window.metadata_cache.get_entry(file_item.full_path)
                if cache_entry and hasattr(cache_entry, 'data'):
                    metadata = cache_entry.data
                    logger.debug(f"[MetadataTree] Got metadata from cache for {file_item.filename}", extra={"dev_only": True})
                else:
                    metadata = parent_window.metadata_cache.get(file_item.full_path)
                    if metadata:
                        logger.debug(f"[MetadataTree] Got raw metadata from cache for {file_item.filename}", extra={"dev_only": True})

            # Fallback to file_item metadata if cache is empty
            if not metadata and hasattr(file_item, 'metadata') and file_item.metadata:
                metadata = file_item.metadata
                logger.debug(f"[MetadataTree] Fallback to file_item metadata for {file_item.filename}", extra={"dev_only": True})

            if isinstance(metadata, dict) and metadata:
                # Create a fresh copy of the metadata for display
                display_metadata = dict(metadata)
                display_metadata["FileName"] = file_item.filename

                # Set current file path for scroll position memory
                self.set_current_file_path(file_item.full_path)

                self.display_metadata(display_metadata, context="update_from_parent_selection")

                # Update file icon status after loading metadata
                self._update_file_icon_status()
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

            logger.debug("[MetadataTreeView] Toggle button connected successfully", extra={"dev_only": True})
        else:
            logger.warning("[MetadataTreeView] Could not find toggle button to connect")

    def initialize_with_parent(self) -> None:
        """
        Performs initial setup that requires parent window to be available.
        Should be called after the tree view is added to its parent.
        """
        self.connect_toggle_button()
        self.show_empty_state("No file selected")
        # Initialize search field as disabled
        self._update_search_field_state(False)

    # =====================================
    # Unified Metadata Management Interface
    # =====================================

    def clear_for_folder_change(self) -> None:
        """
        Clears both view and scroll memory when changing folders.
        This is different from clear_view() which preserves scroll memory.
        """
        self.clear_scroll_memory()
        # Clear all modified items for all files
        self.modified_items_per_file.clear()
        self.modified_items.clear()
        logger.debug("[MetadataTree] Cleared all modified items for folder change", extra={"dev_only": True})
        self.clear_view()
        # Disable search field when changing folders
        self._update_search_field_state(False)

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

        # Get metadata from cache first (to preserve modifications), then fallback to file_item
        metadata = None
        parent_window = self._get_parent_with_file_table()
        if parent_window and hasattr(parent_window, 'metadata_cache'):
            # Try cache first - this includes modifications
            cache_entry = parent_window.metadata_cache.get_entry(file_item.full_path)
            if cache_entry and hasattr(cache_entry, 'data'):
                metadata = cache_entry.data
            else:
                metadata = parent_window.metadata_cache.get(file_item.full_path)

        # Fallback to file_item metadata if cache is empty
        if not metadata and hasattr(file_item, 'metadata') and file_item.metadata:
            metadata = file_item.metadata

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

    def get_modified_metadata(self) -> Dict[str, str]:
        """
        Collect all modified metadata items for the current file.

        Returns:
            Dict[str, str]: Dictionary of modified metadata in format {"EXIF/Rotation": "90"}
        """
        if not self.modified_items:
            return {}

        modified_metadata = {}

        # Get current file's metadata
        selected_files = self._get_current_selection()
        metadata_cache = self._get_metadata_cache()

        if not selected_files or not metadata_cache:
            logger.debug("[MetadataTree] No selected files or metadata cache for collecting modifications", extra={"dev_only": True})
            return {}

        # For now, only handle single file selection
        if len(selected_files) != 1:
            logger.warning("[MetadataTree] Multiple files selected - save not implemented yet")
            return {}

        file_item = selected_files[0]
        metadata_entry = metadata_cache.get_entry(file_item.full_path)

        if not metadata_entry or not hasattr(metadata_entry, 'data'):
            return {}

        # Collect modified values from metadata
        for key_path in self.modified_items:
            # Special handling for rotation - it's always top-level
            if key_path.lower() == "rotation":
                if "Rotation" in metadata_entry.data:
                    modified_metadata["Rotation"] = str(metadata_entry.data["Rotation"])
                    logger.debug(f"[MetadataTree] Found Rotation = {metadata_entry.data['Rotation']} in cache", extra={"dev_only": True})
                else:
                    logger.warning("[MetadataTree] Rotation not found in cache for current file")
                continue

            # Handle other fields normally
            parts = key_path.split('/')

            if len(parts) == 1:
                # Top-level key
                if parts[0] in metadata_entry.data:
                    modified_metadata[key_path] = str(metadata_entry.data[parts[0]])
            elif len(parts) == 2:
                # Nested key (group/key)
                group, key = parts
                if group in metadata_entry.data and isinstance(metadata_entry.data[group], dict):
                    if key in metadata_entry.data[group]:
                        modified_metadata[key_path] = str(metadata_entry.data[group][key])
                        logger.debug(f"[MetadataTree] Found {key_path} = {metadata_entry.data[group][key]} in cache", extra={"dev_only": True})

        logger.debug(f"[MetadataTree] Collected {len(modified_metadata)} modified items", extra={"dev_only": True})
        return modified_metadata

    def get_all_modified_metadata_for_files(self) -> Dict[str, Dict[str, str]]:
        """
        Collect all modified metadata for all files that have modifications.

        Returns:
            Dict[str, Dict[str, str]]: Dictionary mapping file paths to their modified metadata
        """
        all_modifications = {}

        # DEBUG: Log current state before saving
        logger.debug(f"[MetadataTree] BEFORE save - Current file: {self._current_file_path}", extra={"dev_only": True})
        logger.debug(f"[MetadataTree] BEFORE save - Current modified items: {list(self.modified_items) if self.modified_items else 'none'}", extra={"dev_only": True})
        logger.debug(f"[MetadataTree] BEFORE save - Stored files with mods: {list(self.modified_items_per_file.keys())}", extra={"dev_only": True})

        # Save current file's modifications first
        if self._current_file_path and self.modified_items:
            self.modified_items_per_file[self._current_file_path] = self.modified_items.copy()
            logger.debug(f"[MetadataTree] Saved current file modifications: {self._current_file_path} -> {len(self.modified_items)} items", extra={"dev_only": True})
        else:
            if not self._current_file_path:
                logger.debug("[MetadataTree] No current file path to save modifications for", extra={"dev_only": True})
            if not self.modified_items:
                logger.debug("[MetadataTree] No current modifications to save", extra={"dev_only": True})

        # DEBUG: Log state after saving current
        logger.debug(f"[MetadataTree] AFTER save - Stored files with mods: {list(self.modified_items_per_file.keys())}", extra={"dev_only": True})
        for file_path, mods in self.modified_items_per_file.items():
            logger.debug(f"[MetadataTree] AFTER save - {file_path}: {list(mods) if mods else 'none'}", extra={"dev_only": True})

        # Clean up any None keys that might exist in the dictionary
        none_keys = [k for k in self.modified_items_per_file.keys() if k is None]
        for none_key in none_keys:
            del self.modified_items_per_file[none_key]
            logger.debug("[MetadataTree] Cleaned up None key from modified_items_per_file", extra={"dev_only": True})

        # Get metadata cache
        metadata_cache = self._get_metadata_cache()
        if not metadata_cache:
            logger.debug("[MetadataTree] No metadata cache available for collecting all modifications", extra={"dev_only": True})
            return {}

        logger.debug(f"[MetadataTree] Processing modifications for {len(self.modified_items_per_file)} files", extra={"dev_only": True})

        # Collect modifications for each file
        for file_path, modified_keys in self.modified_items_per_file.items():
            # Skip None or empty file paths
            if not file_path or not modified_keys:
                continue

            logger.debug(f"[MetadataTree] Processing file: {file_path} with {len(modified_keys)} modified keys: {list(modified_keys)}", extra={"dev_only": True})

            metadata_entry = metadata_cache.get_entry(file_path)
            if not metadata_entry or not hasattr(metadata_entry, 'data'):
                logger.debug(f"[MetadataTree] No metadata entry found for {file_path}", extra={"dev_only": True})
                continue

            file_modifications = {}

            for key_path in modified_keys:
                # Special handling for rotation - it's always top-level
                if key_path.lower() == "rotation":
                    if "Rotation" in metadata_entry.data:
                        file_modifications["Rotation"] = str(metadata_entry.data["Rotation"])
                        logger.debug(f"[MetadataTree] Found rotation: {metadata_entry.data['Rotation']}", extra={"dev_only": True})
                    else:
                        logger.debug(f"[MetadataTree] Rotation not found in metadata for {file_path}", extra={"dev_only": True})
                    continue

                # Handle other fields normally
                parts = key_path.split('/')

                if len(parts) == 1:
                    # Top-level key
                    if parts[0] in metadata_entry.data:
                        file_modifications[key_path] = str(metadata_entry.data[parts[0]])
                        logger.debug(f"[MetadataTree] Found top-level key: {key_path} = {metadata_entry.data[parts[0]]}", extra={"dev_only": True})
                elif len(parts) == 2:
                    # Nested key (group/key)
                    group, key = parts
                    if group in metadata_entry.data and isinstance(metadata_entry.data[group], dict):
                        if key in metadata_entry.data[group]:
                            file_modifications[key_path] = str(metadata_entry.data[group][key])
                            logger.debug(f"[MetadataTree] Found nested key: {key_path} = {metadata_entry.data[group][key]}", extra={"dev_only": True})

            if file_modifications:
                all_modifications[file_path] = file_modifications
                logger.debug(f"[MetadataTree] Collected {len(file_modifications)} modifications for {file_path}", extra={"dev_only": True})
            else:
                logger.debug(f"[MetadataTree] No modifications found for {file_path}", extra={"dev_only": True})

        logger.info(f"[MetadataTree] Total files with modifications: {len(all_modifications)}")
        logger.debug(f"[MetadataTree] Final result: {list(all_modifications.keys())}", extra={"dev_only": True})
        return all_modifications

    def clear_modifications(self) -> None:
        """
        Clear all modified metadata items for the current file.
        """
        self.modified_items.clear()
        # Also clear from the per-file storage
        if self._current_file_path and self._current_file_path in self.modified_items_per_file:
            del self.modified_items_per_file[self._current_file_path]
            logger.debug(f"[MetadataTree] Cleared modifications for {self._current_file_path}", extra={"dev_only": True})
        self._update_file_icon_status()
        self.viewport().update()

    def clear_modifications_for_file(self, file_path: str) -> None:
        """
        Clear modifications for a specific file.

        Args:
            file_path: Full path of the file to clear modifications for
        """
                # Remove from per-file storage
        if file_path in self.modified_items_per_file:
            del self.modified_items_per_file[file_path]
            logger.debug(f"[MetadataTree] Cleared modifications for {file_path}", extra={"dev_only": True})

        # If this is the current file, also clear current modifications and update UI
        if paths_equal(file_path, self._current_file_path):
            self.modified_items.clear()
            # Refresh the view to remove italic style
            if hasattr(self, 'display_metadata'):
                # Get current selection to refresh
                selected_files = self._get_current_selection()
                if selected_files and len(selected_files) == 1:
                    file_item = selected_files[0]
                    metadata_cache = self._get_metadata_cache()
                    if metadata_cache:
                        metadata_entry = metadata_cache.get_entry(file_item.full_path)
                        if metadata_entry and hasattr(metadata_entry, 'data'):
                            display_data = dict(metadata_entry.data)
                            display_data["FileName"] = file_item.filename
                            self.display_metadata(display_data, context="after_save")
            self._update_file_icon_status()
            self.viewport().update()

    def has_modifications_for_selected_files(self) -> bool:
        """
        Check if any of the currently selected files have modifications.

        Returns:
            bool: True if any selected file has modifications
        """
        # Save current file's modifications first
        if self._current_file_path and self.modified_items:
            self.modified_items_per_file[self._current_file_path] = self.modified_items.copy()

        # Get selected files
        selected_files = self._get_current_selection()
        if not selected_files:
            return False

        # Check if any selected file has modifications
        for file_item in selected_files:
            file_path = file_item.full_path

            # Check both current modified items and stored ones
            if paths_equal(file_path, self._current_file_path) and self.modified_items:
                return True
            elif file_path in self.modified_items_per_file and self.modified_items_per_file[file_path]:
                return True

        return False

    def has_any_modifications(self) -> bool:
        """
        Check if there are any modifications in any file.

        Returns:
            bool: True if any file has modifications
        """
        # Save current file's modifications first
        if self._current_file_path and self.modified_items:
            self.modified_items_per_file[self._current_file_path] = self.modified_items.copy()

        # Check current file modifications
        if self.modified_items:
            return True

        # Check stored modifications for all files
        for file_path, modifications in self.modified_items_per_file.items():
            if modifications:  # Non-empty set
                return True

        return False

