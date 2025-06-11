"""
file_tree_view.py

Author: Michael Economou
Date: 2025-06-05

Implements a custom tree view with clean custom drag implementation.
No reliance on Qt built-in drag system - everything is manual and controlled.
"""

import os
from typing import Optional

from PyQt5.QtCore import QEvent, QPoint, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeyEvent, QMouseEvent, QCursor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QTreeView,
)

from config import ALLOWED_EXTENSIONS
from core.drag_manager import DragManager
from utils.logger_helper import get_logger

logger = get_logger(__name__)


class FileTreeView(QTreeView):
    """
    Custom tree view with clean custom drag & drop implementation.

    Features:
    - Manual drag control (no Qt built-in drag system)
    - Intelligent horizontal scrolling
    - Proper drag & drop handling for internal use only
    - Automatic header configuration for optimal display
    - Multi-selection support with Ctrl+Click and Shift+Click
    """

    # Signals
    folder_dropped = pyqtSignal(list, object)  # list of paths and keyboard modifiers
    folder_selected = pyqtSignal()  # Signal emitted when Return/Enter is pressed
    selection_changed = pyqtSignal(list)  # Signal emitted when selection changes (list of paths)

    def __init__(self, parent=None):
        super().__init__(parent)

        # DISABLE all built-in drag functionality
        self.setDragEnabled(False)
        self.setAcceptDrops(True)  # We still need to accept drops
        self.setDragDropMode(QAbstractItemView.NoDragDrop)  # No built-in drag

        # Configure scrollbars for optimal horizontal scrolling
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        # Configure text display for horizontal scrolling
        self.setTextElideMode(Qt.ElideNone)  # Show full content
        self.setWordWrap(False)  # Allow horizontal overflow

        # Optimize for performance and appearance
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)

        # Configure multi-selection support
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Initialize custom drag state
        self._drag_start_pos: Optional[QPoint] = None
        self._is_dragging = False
        self._drag_path = None

        logger.debug("[FileTreeView] Initialized with custom drag system")

    def selectionChanged(self, selected, deselected):
        """Override to emit custom signal with selected paths"""
        super().selectionChanged(selected, deselected)

        # Get all selected paths
        selected_paths = []
        for index in self.selectedIndexes():
            if self.model() and hasattr(self.model(), 'filePath'):
                path = self.model().filePath(index)
                if path and path not in selected_paths:
                    selected_paths.append(path)

        logger.debug(f"[FileTreeView] Selection changed: {len(selected_paths)} items", extra={"dev_only": True})
        self.selection_changed.emit(selected_paths)

    def setModel(self, model):
        """Override to configure header when model is set"""
        super().setModel(model)
        self._configure_header()
        logger.debug(f"[FileTreeView] Model set: {type(model).__name__ if model else 'None'}", extra={"dev_only": True})

    def resizeEvent(self, event):
        """Handle resize to adjust column width for optimal horizontal scrolling"""
        super().resizeEvent(event)
        self._adjust_column_width()

    def _configure_header(self):
        """Configure header for optimal display"""
        header = self.header()
        if header:
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)

            # Hide all columns except the first (name)
            for col in range(1, self.model().columnCount() if self.model() else 4):
                self.setColumnHidden(col, True)

            logger.debug("[FileTreeView] Header configured for single column display", extra={"dev_only": True})

    def _adjust_column_width(self):
        """Adjust column width for optimal horizontal scrolling"""
        if not self.model():
            return

        header = self.header()
        if not header:
            return

        viewport_width = self.viewport().width()
        content_width = self.sizeHintForColumn(0)

        if content_width > 0:
            if content_width <= viewport_width:
                header.setSectionResizeMode(0, QHeaderView.Stretch)
                self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                logger.debug("[FileTreeView] Content fits viewport - stretching column", extra={"dev_only": True})
            else:
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                logger.debug(f"[FileTreeView] Content exceeds viewport ({content_width} > {viewport_width}) - enabling scrollbar", extra={"dev_only": True})

    def _on_model_changed(self):
        """Called when model data changes to update column width"""
        QTimer.singleShot(10, self._adjust_column_width)

    def get_selected_paths(self) -> list:
        """Get list of selected file/folder paths"""
        paths = []
        for index in self.selectedIndexes():
            if self.model() and hasattr(self.model(), 'filePath'):
                path = self.model().filePath(index)
                if path:
                    paths.append(path)
        return paths

    def select_paths(self, paths: list, clear_existing: bool = True):
        """Select items by their file paths"""
        if not self.model() or not hasattr(self.model(), 'index'):
            return

        selection_model = self.selectionModel()
        if not selection_model:
            return

        if clear_existing:
            selection_model.clearSelection()

        for path in paths:
            index = self.model().index(path)
            if index.isValid():
                selection_model.select(index, selection_model.Select | selection_model.Rows)

    def select_range(self, from_index, to_index):
        """Select a range of items (for Shift+Click behavior)"""
        selection_model = self.selectionModel()
        if not selection_model:
            return

        # Create selection from range
        from PyQt5.QtCore import QItemSelection
        selection = QItemSelection(from_index, to_index)
        selection_model.select(selection, selection_model.Select | selection_model.Rows)

    # =====================================
    # CUSTOM DRAG IMPLEMENTATION
    # =====================================

    def mousePressEvent(self, event):
        """Handle mouse press for custom drag detection"""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self._is_dragging = False
            self._drag_path = None

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for custom drag start"""
        # Only proceed if left button is pressed and we have a start position
        if not (event.buttons() & Qt.LeftButton) or not self._drag_start_pos:
            super().mouseMoveEvent(event)
            return

        # Check if we've moved enough to start drag
        distance = (event.pos() - self._drag_start_pos).manhattanLength()
        if distance < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        # Already dragging? Don't start another
        if self._is_dragging:
            return

        # Start our custom drag
        self._start_custom_drag()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release to end drag"""
        self._end_custom_drag()
        super().mouseReleaseEvent(event)

    def _start_custom_drag(self):
        """Start our custom drag operation"""
        if not self._drag_start_pos:
            return

        # Get the item under the mouse
        index = self.indexAt(self._drag_start_pos)
        if not index.isValid():
            return

        # Get the path
        model = self.model()
        if not model or not hasattr(model, 'filePath'):
            return

        path = model.filePath(index)
        if not path or not self._is_valid_drag_target(path):
            return

        # Set drag state
        self._is_dragging = True
        self._drag_path = path

        # Notify DragManager
        drag_manager = DragManager.get_instance()
        drag_manager.start_drag("file_tree")

        # Set visual cursor
        QApplication.setOverrideCursor(QCursor(Qt.ClosedHandCursor))

        logger.debug(f"[FileTreeView] Custom drag started: {path}", extra={"dev_only": True})

    def _end_custom_drag(self):
        """End our custom drag operation"""
        if not self._is_dragging:
            return

        # Check if drag has been cancelled by external force cleanup
        drag_manager = DragManager.get_instance()
        if not drag_manager.is_drag_active():
            logger.debug("[FileTreeView] Drag was cancelled, skipping drop", extra={"dev_only": True})
            # Clean up drag state without performing drop
            self._is_dragging = False
            path = self._drag_path
            self._drag_path = None
            self._drag_start_pos = None
            logger.debug(f"[FileTreeView] Custom drag ended (cancelled): {path}", extra={"dev_only": True})
            return

        # Check if we dropped on a valid target (only FileTableView allowed)
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        logger.debug(f"[FileTreeView] Widget under cursor: {widget_under_cursor}", extra={"dev_only": True})

        # Check if dropped on file table (strict policy: only FileTableView)
        if widget_under_cursor:
            # Look for FileTableView in parent hierarchy
            parent = widget_under_cursor
            while parent:
                logger.debug(f"[FileTreeView] Checking parent: {parent.__class__.__name__}", extra={"dev_only": True})

                # Only accept drops on FileTableView
                if parent.__class__.__name__ == 'FileTableView':
                    logger.debug(f"[FileTreeView] Found FileTableView: {parent}", extra={"dev_only": True})
                    self._handle_drop_on_table()
                    break

                # Also check viewport of FileTableView
                if hasattr(parent, 'parent') and parent.parent() and parent.parent().__class__.__name__ == 'FileTableView':
                    logger.debug(f"[FileTreeView] Found FileTableView via viewport: {parent.parent()}", extra={"dev_only": True})
                    self._handle_drop_on_table()
                    break

                # Reject drops on other targets (FileTreeView itself, MetadataTreeView, etc.)
                if parent.__class__.__name__ in ['FileTreeView', 'MetadataTreeView']:
                    logger.debug(f"[FileTreeView] Rejecting drop on {parent.__class__.__name__} (policy violation)", extra={"dev_only": True})
                    break

                parent = parent.parent()

        # Clean up drag state
        self._is_dragging = False
        path = self._drag_path
        self._drag_path = None
        self._drag_start_pos = None

        # Restore cursor
        QApplication.restoreOverrideCursor()

        # Notify DragManager
        drag_manager.end_drag("file_tree")

        logger.debug(f"[FileTreeView] Custom drag ended: {path}", extra={"dev_only": True})

    def _handle_drop_on_table(self):
        """Handle drop on file table"""
        if not self._drag_path:
            return

        # Emit the drop signal with modifiers
        modifiers = QApplication.keyboardModifiers()
        self.folder_dropped.emit([self._drag_path], modifiers)
        logger.debug(f"[FileTreeView] Dropped on table: {self._drag_path}", extra={"dev_only": True})

    def _is_valid_drag_target(self, path: str) -> bool:
        """Check if path is valid for dragging"""
        if os.path.isdir(path):
            return True

        # For files, check extension
        _, ext = os.path.splitext(path)
        if ext.startswith('.'):
            ext = ext[1:].lower()

        if ext not in ALLOWED_EXTENSIONS:
            logger.debug(f"[FileTreeView] Skipping drag for non-allowed extension: {ext}", extra={"dev_only": True})
            return False

        return True

    # =====================================
    # DROP HANDLING (unchanged)
    # =====================================

    def dragEnterEvent(self, event):
        """Accept internal drops only"""
        event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move"""
        event.ignore()

    def dropEvent(self, event):
        """Handle drop events"""
        event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave"""
        event.ignore()

    # =====================================
    # KEY HANDLING
    # =====================================

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle Return/Enter key to emit folder_selected signal"""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.folder_selected.emit()
        else:
            super().keyPressEvent(event)

    # =====================================
    # SPLITTER INTEGRATION (unchanged)
    # =====================================

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement to adjust column width"""
        QTimer.singleShot(50, self._adjust_column_width)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement (placeholder for future use)"""
        pass

    def scrollTo(self, index, hint=None) -> None:
        """Override to ensure optimal scrolling behavior"""
        super().scrollTo(index, hint or QAbstractItemView.EnsureVisible)
