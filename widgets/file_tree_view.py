"""
file_tree_view.py

Author: Michael Economou
Date: 2025-06-05

Implements a custom tree view with modified drag & drop behavior
to prevent drag-out to external applications while preserving
internal drag & drop functionality. Also handles intelligent
horizontal scrolling with viewport width optimization.
"""

import os
from typing import Optional

from PyQt5.QtCore import QEvent, QMimeData, QObject, QPoint, Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QDrag, QKeyEvent, QMouseEvent
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


class DragCancelFilter(QObject):
    """
    Global event filter to forcefully cancel any lingering drag operations.
    This is installed on QApplication to catch events like Escape key presses
    and mouse clicks that should terminate drag operations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.setSingleShot(True)
        self._cleanup_timer.timeout.connect(self._delayed_cleanup)

    def activate(self):
        """Activate this filter to start monitoring for drag termination events"""
        self._active = True
        logger.debug("[DragFilter] Activated", extra={"dev_only": True})

    def deactivate(self):
        """Deactivate this filter when drag has properly terminated"""
        self._active = False
        if self._cleanup_timer.isActive():
            self._cleanup_timer.stop()
        logger.debug("[DragFilter] Deactivated", extra={"dev_only": True})

    def eventFilter(self, obj, event):
        """Filter events to catch drag termination signals"""
        if not self._active:
            return False

        event_type = event.type()

        # Mouse press or release should terminate drag
        if event_type in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            logger.debug("[DragFilter] Caught mouse event, scheduling cleanup", extra={"dev_only": True})
            # Schedule cleanup with reasonable delay to let events process
            self._cleanup_timer.start(50)
            return False  # Don't consume the event

        # Escape key should terminate drag immediately
        if event_type == QEvent.KeyPress:
            key_event = event  # type: QKeyEvent
            if key_event.key() == Qt.Key_Escape:
                logger.debug("[DragFilter] Caught Escape key, immediate cleanup", extra={"dev_only": True})
                self._cleanup_drag()
                return True  # Consume the escape key event

        # Window deactivation should also trigger cleanup
        if event_type in (QEvent.WindowDeactivate, QEvent.ApplicationDeactivate):
            logger.debug("[DragFilter] Window deactivated, scheduling cleanup", extra={"dev_only": True})
            self._cleanup_timer.start(100)

        return False  # Don't consume other events

    def _cleanup_drag(self):
        """Force cleanup all drag operations."""
        # Use DragManager for centralized cleanup
        drag_manager = DragManager.get_instance()
        if drag_manager.is_drag_active():
            logger.debug("[DragCancel] Forcing drag cleanup via DragManager")
            drag_manager.force_cleanup()

        # Additional cleanup
        cursor_count = 0
        while QApplication.overrideCursor() and cursor_count < 10:
            QApplication.restoreOverrideCursor()
            cursor_count += 1

        # Update all widgets
        app = QApplication.instance()
        if app:
            # Process pending events first
            app.processEvents()

            # Update visible widgets
            for widget in app.topLevelWidgets():
                if widget.isVisible():
                    widget.update()
                    if hasattr(widget, 'viewport'):
                        widget.viewport().update()

    def _delayed_cleanup(self):
        """Delayed cleanup to avoid interfering with active operations"""
        if self._active:
            self._cleanup_drag()


# Create a single global instance
_drag_cancel_filter = DragCancelFilter()


class FileTreeView(QTreeView):
    """
    Custom tree view that prevents drag-out to external applications
    while preserving internal drag & drop functionality.

    Features:
    - Intelligent horizontal scrolling (fills viewport when content is small,
      shows scrollbar when content is large)
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

        # Configure drag & drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDropIndicatorShown(True)

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

        # Initialize drag state
        self._drag_start_position: Optional[QPoint] = None
        self._dragging = False
        self._active_drag = None  # Store active QDrag object for cleanup

        # Install global drag cancel filter
        app = QApplication.instance()
        if app:
            app.installEventFilter(_drag_cancel_filter)

        logger.debug("[FileTreeView] Initialized with intelligent scrolling", extra={"dev_only": True})

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
        logger.debug(f"[FileTreeView] Model set: {type(model).__name__ if model else 'None'}", extra={"dev_only": True})

        # Configure header and trigger initial adjustment when model is set
        if model:
            self._configure_header()
            if hasattr(model, 'rowsInserted'):
                model.rowsInserted.connect(self._on_model_changed)
            QTimer.singleShot(50, self._adjust_column_width)

    def resizeEvent(self, event):
        """Override to handle intelligent column width adjustment on resize"""
        super().resizeEvent(event)
        # Delay adjustment to ensure layout is complete
        QTimer.singleShot(10, self._adjust_column_width)

    def _configure_header(self):
        """Configure header settings for optimal horizontal scrolling behavior"""
        header = self.header()
        if not header:
            return False

        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setMinimumSectionSize(100)
        header.setStretchLastSection(False)
        header.setMaximumSectionSize(16777215)  # Max value for unlimited width

        logger.debug("[FileTreeView] Header configured for intelligent scrolling", extra={"dev_only": True})
        return True

    def _adjust_column_width(self):
        """Intelligently adjust column width: fill viewport when content is small, allow scrolling when large"""
        if not self.model():
            return

        viewport_width = self.viewport().width()
        if viewport_width <= 50:  # Skip if too small
            return

        header = self.header()
        if not header:
            return

        # Get natural content width
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        natural_width = self.columnWidth(0)

        # Decide: expand to fill viewport or keep natural width for scrolling
        if natural_width < viewport_width:
            # Expand to fill viewport (prevents gaps in alternating colors)
            target_width = viewport_width - 2  # Small margin (reduced from 5px to 2px for more content space)
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            self.setColumnWidth(0, target_width)
            logger.debug(f"[FileTreeView] Expanded: {natural_width}px → {target_width}px", extra={"dev_only": True})
        else:
            # Keep natural width (allows horizontal scrolling)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            logger.debug(f"[FileTreeView] Natural width: {natural_width}px (viewport: {viewport_width}px)", extra={"dev_only": True})

    def _on_model_changed(self):
        """Handle model content changes"""
        if self.model():
            self._adjust_column_width()

    # =====================================
    # Multi-Selection Helper Methods
    # =====================================

    def get_selected_paths(self) -> list:
        """Get list of selected file/folder paths"""
        selected_paths = []
        for index in self.selectedIndexes():
            if self.model() and hasattr(self.model(), 'filePath'):
                path = self.model().filePath(index)
                if path and path not in selected_paths:
                    selected_paths.append(path)
        return selected_paths

    def select_paths(self, paths: list, clear_existing: bool = True):
        """Select specific paths in the tree view"""
        if not self.model() or not hasattr(self.model(), 'filePath'):
            return

        if clear_existing:
            self.clearSelection()

        selection_model = self.selectionModel()
        if not selection_model:
            return

        # Find and select the paths
        for path in paths:
            for i in range(self.model().rowCount()):
                index = self.model().index(i, 0)
                if self.model().filePath(index) == path:
                    selection_model.select(index, selection_model.Select)
                    break

    def select_range(self, from_index, to_index):
        """Select a range of items from one index to another"""
        if not self.model():
            return

        selection_model = self.selectionModel()
        if not selection_model:
            return

        # Ensure proper order
        start_row = min(from_index.row(), to_index.row())
        end_row = max(from_index.row(), to_index.row())

        # Select the range
        for row in range(start_row, end_row + 1):
            index = self.model().index(row, 0, from_index.parent())
            if index.isValid():
                selection_model.select(index, selection_model.Select)

    # =====================================
    # Drag & Drop Implementation
    # =====================================

    def mousePressEvent(self, event):
        """Store initial position for drag detection and handle multi-selection"""
        if event.button() == Qt.LeftButton:
            self._drag_start_position = event.pos()

            # Handle multi-selection with modifiers
            index = self.indexAt(event.pos())
            if index.isValid():
                modifiers = event.modifiers()
                selection_model = self.selectionModel()

                if modifiers & Qt.ControlModifier:
                    # Ctrl+Click: Toggle selection of this item
                    if selection_model.isSelected(index):
                        selection_model.select(index, selection_model.Deselect)
                    else:
                        selection_model.select(index, selection_model.Select)
                    logger.debug(f"[FileTreeView] Ctrl+Click selection toggle", extra={"dev_only": True})
                    return  # Don't call super() to prevent default behavior

                elif modifiers & Qt.ShiftModifier:
                    # Shift+Click: Select range from last selected to this item
                    current_selection = self.selectedIndexes()
                    if current_selection:
                        # Find the last selected item
                        last_selected = current_selection[-1]
                        # Clear current selection and select range
                        self.clearSelection()
                        self.select_range(last_selected, index)
                        logger.debug(f"[FileTreeView] Shift+Click range selection", extra={"dev_only": True})
                        return  # Don't call super() to prevent default behavior

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for internal drag & drop"""
        if not (event.buttons() & Qt.LeftButton) or not self._drag_start_position:
            return super().mouseMoveEvent(event)

        # Check if moved enough to start drag
        if (event.pos() - self._drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return super().mouseMoveEvent(event)

        # Prevent multiple drag events
        if self._dragging:
            return

        # Start internal drag
        self._dragging = True
        self._start_internal_drag(event.pos())
        self._reset_drag_state()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Ensure drag state is properly reset on mouse release"""
        self._reset_drag_state()

        # Force drag manager cleanup if active
        drag_manager = DragManager.get_instance()
        if drag_manager.is_drag_active():
            drag_manager.end_drag("file_tree_mouse_release")

        self.viewport().update()
        super().mouseReleaseEvent(event)
        QApplication.processEvents()

        # Force cleanup with delay and additional cleanup
        QTimer.singleShot(100, self._send_fake_release)
        QTimer.singleShot(200, self._final_emergency_cleanup)

    def _start_internal_drag(self, position):
        """Start internal drag operation for folders/files"""
        index = self.indexAt(position)
        if not index.isValid():
            index = self.currentIndex()
            if not index.isValid():
                return

        # Get file path
        model = self.model()
        if not hasattr(model, 'filePath'):
            logger.warning("Model does not support filePath method")
            return

        path = model.filePath(index)
        if not path:
            return

        # Validate file type for drag
        if not self._is_valid_drag_target(path):
            return

        # Perform drag operation
        self._execute_drag(path)

    def _is_valid_drag_target(self, path: str) -> bool:
        """Check if path is valid for dragging"""
        if os.path.isdir(path):
            return True

        # For files, check extension
        _, ext = os.path.splitext(path)
        if ext.startswith('.'):
            ext = ext[1:].lower()

        if ext not in ALLOWED_EXTENSIONS:
            logger.debug(f"Skipping drag for non-allowed extension: {ext}", extra={"dev_only": True})
            return False

        return True

    def _execute_drag(self, path: str):
        """Execute the drag operation with proper cleanup"""
        # Start drag operation with DragManager
        drag_manager = DragManager.get_instance()
        drag_manager.start_drag("file_tree")

        _drag_cancel_filter.activate()

        # Create drag with MIME data
        drag = QDrag(self)
        mimeData = QMimeData()
        mimeData.setData("application/x-oncutf-internal", path.encode())
        mimeData.setText(path)
        mimeData.setUrls([QUrl.fromLocalFile(path)])
        drag.setMimeData(mimeData)

        self._dragging = False  # Reset before execution
        self._active_drag = drag  # Store reference

        try:
            # Execute drag with timeout protection
            result = drag.exec(Qt.CopyAction | Qt.MoveAction | Qt.LinkAction)
            logger.debug(f"[FileTree] Drag completed with result: {result}", extra={"dev_only": True})
        except Exception as e:
            logger.error(f"Drag operation failed: {e}")
            result = Qt.IgnoreAction
        finally:
            # Immediate cleanup
            self._active_drag = None
            self._dragging = False

            # End drag operation with DragManager
            drag_manager.end_drag("file_tree")

            # Deactivate filter
            _drag_cancel_filter.deactivate()

            # Force cursor restoration
            while QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()

            # Update UI immediately
            self.viewport().update()
            QApplication.processEvents()

        # Schedule additional cleanup with reasonable delay
        QTimer.singleShot(100, self._aggressive_post_drag_cleanup)

    def _aggressive_post_drag_cleanup(self):
        """Aggressive post-drag cleanup to prevent ghost effects"""
        # Force DragManager cleanup
        drag_manager = DragManager.get_instance()
        if drag_manager.is_drag_active():
            logger.debug("[FileTree] Forcing DragManager cleanup in post-drag", extra={"dev_only": True})
            drag_manager.force_cleanup()

        # Reset all drag state
        self._reset_drag_state()

        # Force cursor cleanup again
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        # Deactivate filter if still active
        if _drag_cancel_filter._active:
            _drag_cancel_filter.deactivate()

        # Force UI update
        self.viewport().update()
        self.update()

        # Process events to clear any pending drag events
        QApplication.processEvents()

        # Send fake mouse release to self
        fake_event = QMouseEvent(
            QEvent.MouseButtonRelease,
            QPoint(0, 0),
            Qt.LeftButton,
            Qt.NoButton,
            Qt.NoModifier
        )
        QApplication.postEvent(self.viewport(), fake_event)

    def _final_drag_cleanup(self):
        """Complete cleanup of drag operation"""
        self._reset_drag_state()

        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        _drag_cancel_filter.deactivate()
        self.viewport().update()
        QApplication.processEvents()

        # Schedule more aggressive cleanup
        QTimer.singleShot(50, self._aggressive_post_drag_cleanup)

    def _reset_drag_state(self):
        """Reset internal drag state variables"""
        self._dragging = False
        self._drag_start_position = None
        # Clean up active drag reference if exists (Qt auto-deletes the QDrag)
        if hasattr(self, '_active_drag'):
            self._active_drag = None

    def _send_fake_release(self):
        """Send fake mouse release event to clean up Qt drag session"""
        fake_event = QMouseEvent(
            QEvent.MouseButtonRelease,
            QPoint(-1, -1),
            Qt.LeftButton,
            Qt.NoButton,
            Qt.NoModifier
        )
        QApplication.postEvent(self, fake_event)

    def _final_emergency_cleanup(self):
        """Perform final emergency cleanup"""
        self._reset_drag_state()
        self.viewport().update()
        QApplication.processEvents()

    # =====================================
    # Drop Events (Rejected)
    # =====================================

    def dragEnterEvent(self, event):
        """Reject all drag enter events - no drops allowed"""
        event.ignore()

    def dragMoveEvent(self, event):
        """Reject all drag move events - no drops allowed"""
        event.ignore()

    def dropEvent(self, event):
        """Reject all drop events - no drops allowed"""
        event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave with cleanup"""
        logger.debug("[DragDrop] dragLeaveEvent, forcing cleanup", extra={"dev_only": True})
        self._final_drag_cleanup()
        event.ignore()

    # =====================================
    # Keyboard & External Events
    # =====================================

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events - Enter/Return triggers folder selection"""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            logger.debug("[TreeView] Enter/Return pressed, triggering folder_selected", extra={"dev_only": True})
            self.folder_selected.emit()
        else:
            super().keyPressEvent(event)

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement (called from MainWindow)"""
        self._adjust_column_width()
        logger.debug("[FileTreeView] Splitter moved - adjusting column width", extra={"dev_only": True})

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement (for debugging)"""
        logger.debug(f"[FileTreeView] Vertical splitter moved - Pos: {pos}, Index: {index}", extra={"dev_only": True})

    def scrollTo(self, index, hint=None) -> None:
        """
        Override scrollTo to prevent automatic scrolling when selections change.
        This prevents the tree from moving when selecting folders.
        """
        # Allow minimal scrolling only if the selected item is completely out of view
        viewport_rect = self.viewport().rect()
        item_rect = self.visualRect(index)

        # Only scroll if item is completely outside the viewport
        if not viewport_rect.intersects(item_rect):
            super().scrollTo(index, hint)
        # Otherwise, do nothing - prevent automatic centering
