"""
file_tree_view.py

Author: Michael Economou
Date: 2025-06-05

Implements a custom tree view with clean single-item drag implementation.
No reliance on Qt built-in drag system - everything is manual and controlled.
Single item selection only - no multi-selection complexity.
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
from core.modifier_handler import decode_modifiers_to_flags
from core.drag_visual_manager import (
    DragVisualManager, DragType, DropZoneState, ModifierState,
    start_drag_visual, end_drag_visual, update_drop_zone_state,
    update_modifier_state, is_valid_drop_target
)
from utils.logger_helper import get_logger
from utils.cursor_helper import wait_cursor

logger = get_logger(__name__)


class FileTreeView(QTreeView):
    """
    Custom tree view with clean single-item drag & drop implementation.

    Features:
    - Manual drag control (no Qt built-in drag system)
    - Intelligent horizontal scrolling
    - Single item selection only (no multi-selection complexity)
    - 4 modifier combinations for drag behavior:
      * Normal: Replace + shallow
      * Ctrl: Replace + recursive
      * Shift: Merge + shallow
      * Ctrl+Shift: Merge + recursive
    - Automatic header configuration for optimal display
    """

    # Signals
    item_dropped = pyqtSignal(str, object)  # single path and keyboard modifiers
    folder_selected = pyqtSignal()  # Signal emitted when Return/Enter is pressed
    selection_changed = pyqtSignal(str)  # Signal emitted when selection changes (single path)

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

        # Configure SINGLE selection only
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Initialize custom drag state (simplified for single item)
        self._drag_start_pos: Optional[QPoint] = None
        self._is_dragging = False
        self._drag_path: Optional[str] = None

        logger.debug("[FileTreeView] Initialized with single-item drag system")

    def selectionChanged(self, selected, deselected):
        """Override to emit custom signal with selected path (single item only)"""
        super().selectionChanged(selected, deselected)

        # Get single selected path
        selected_path = ""
        indexes = self.selectedIndexes()
        if indexes and self.model() and hasattr(self.model(), 'filePath'):
            # Take first index (should be only one in single selection mode)
            path = self.model().filePath(indexes[0])
            if path:
                selected_path = path

        logger.debug(f"[FileTreeView] Selection changed: {selected_path if selected_path else 'None'}", extra={"dev_only": True})
        self.selection_changed.emit(selected_path)

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

    def get_selected_path(self) -> str:
        """Get the single selected file/folder path"""
        selection_model = self.selectionModel()
        if not selection_model:
            return ""

        # Use selectedRows() for clean single selection
        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return ""

        # Get first (and only) selected item
        index = selected_rows[0]
        if self.model() and hasattr(self.model(), 'filePath'):
            path = self.model().filePath(index)
            return path if path else ""

        return ""

    def select_path(self, path: str):
        """Select item by its file path"""
        if not self.model() or not hasattr(self.model(), 'index'):
            return

        selection_model = self.selectionModel()
        if not selection_model:
            return

        index = self.model().index(path)
        if index.isValid():
            selection_model.clearSelection()
            selection_model.select(index, selection_model.Select | selection_model.Rows)

    # =====================================
    # CUSTOM SINGLE-ITEM DRAG IMPLEMENTATION
    # =====================================

    def mousePressEvent(self, event):
        """Handle mouse press for custom drag detection"""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self._is_dragging = False
            self._drag_path = None

        # Call super() to handle normal selection
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for custom drag start and real-time drop zone validation"""
        # Only proceed if left button is pressed and we have a start position
        if not (event.buttons() & Qt.LeftButton) or not self._drag_start_pos:
            super().mouseMoveEvent(event)
            return

        # Check if we've moved enough to start drag
        distance = (event.pos() - self._drag_start_pos).manhattanLength()
        if distance < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        # Already dragging? Handle real-time validation but avoid hover changes
        if self._is_dragging:
            self._update_drag_feedback()
            # Don't call super().mouseMoveEvent() during drag to prevent hover changes
            return

        # Start our custom drag
        self._start_custom_drag()
        # Don't call super().mouseMoveEvent() after starting drag to prevent hover changes

    def mouseReleaseEvent(self, event):
        """Handle mouse release to end drag"""
        was_dragging = self._is_dragging
        self._end_custom_drag()
        super().mouseReleaseEvent(event)

        # If we were dragging, send a fake mouse move event to restore hover state
        if was_dragging:
            # Create a fake mouse move event at the current position
            fake_move_event = QMouseEvent(
                QEvent.MouseMove,
                event.pos(),
                Qt.NoButton,
                Qt.NoButton,
                Qt.NoModifier
            )
            QApplication.postEvent(self, fake_move_event)

    def _start_custom_drag(self):
        """Start our custom drag operation with enhanced visual feedback"""
        if not self._drag_start_pos:
            return

        # Get the item under the mouse
        index = self.indexAt(self._drag_start_pos)
        if not index.isValid():
            return

        # Get the path under mouse
        model = self.model()
        if not model or not hasattr(model, 'filePath'):
            return

        clicked_path = model.filePath(index)
        if not clicked_path or not self._is_valid_drag_target(clicked_path):
            return

        # Store the single item being dragged
        self._drag_path = clicked_path

        # Set drag state
        self._is_dragging = True

        # Disable mouse tracking to prevent hover effects during drag
        self._original_mouse_tracking = self.hasMouseTracking()
        self.setMouseTracking(False)

        # Notify DragManager
        drag_manager = DragManager.get_instance()
        drag_manager.start_drag("file_tree")

        # Start enhanced visual feedback
        visual_manager = DragVisualManager.get_instance()
        drag_type = visual_manager.get_drag_type_from_path(clicked_path)
        start_drag_visual(drag_type, clicked_path)

        logger.debug(f"[FileTreeView] Custom drag started: {clicked_path}", extra={"dev_only": True})

    def _update_drag_feedback(self):
        """Update visual feedback based on current cursor position during drag"""
        if not self._is_dragging:
            return

        # Update modifier state first (for Ctrl/Shift changes during drag)
        update_modifier_state()

        # Get widget under cursor
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        if not widget_under_cursor:
            # Cursor is outside application window - terminate drag
            logger.debug("[FileTreeView] Cursor outside application - terminating drag", extra={"dev_only": True})
            self._end_custom_drag()
            return

        # Check if current position is a valid drop target
        visual_manager = DragVisualManager.get_instance()

        # Walk up the parent hierarchy to find valid targets
        parent = widget_under_cursor
        valid_found = False

        while parent and not valid_found:
            # Check if this widget is a valid drop target
            if visual_manager.is_valid_drop_target(parent, "file_tree"):
                update_drop_zone_state(DropZoneState.VALID)
                valid_found = True
                logger.debug(f"[FileTreeView] Valid drop zone: {parent.__class__.__name__}", extra={"dev_only": True})
                break

            # Check for explicit invalid targets (policy violations)
            elif parent.__class__.__name__ in ['FileTreeView', 'MetadataTreeView']:
                update_drop_zone_state(DropZoneState.INVALID)
                valid_found = True
                logger.debug(f"[FileTreeView] Invalid drop zone: {parent.__class__.__name__}", extra={"dev_only": True})
                break

            parent = parent.parent()

        # If no specific target found, neutral state
        if not valid_found:
            update_drop_zone_state(DropZoneState.NEUTRAL)

    def _end_custom_drag(self):
        """End our custom drag operation with enhanced visual feedback"""
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

            # Restore mouse tracking to original state
            if hasattr(self, '_original_mouse_tracking'):
                self.setMouseTracking(self._original_mouse_tracking)
                delattr(self, '_original_mouse_tracking')

            # End visual feedback
            end_drag_visual()

            logger.debug(f"[FileTreeView] Custom drag ended (cancelled): {path}", extra={"dev_only": True})
            return

        # Check if we dropped on a valid target (only FileTableView allowed)
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        logger.debug(f"[FileTreeView] Widget under cursor: {widget_under_cursor}", extra={"dev_only": True})

        # Use visual manager to validate drop target
        visual_manager = DragVisualManager.get_instance()
        valid_drop = False

        # Check if dropped on file table (strict policy: only FileTableView)
        if widget_under_cursor:
            # Look for FileTableView in parent hierarchy
            parent = widget_under_cursor
            while parent:
                logger.debug(f"[FileTreeView] Checking parent: {parent.__class__.__name__}", extra={"dev_only": True})

                # Check with visual manager
                if visual_manager.is_valid_drop_target(parent, "file_tree"):
                    logger.debug(f"[FileTreeView] Valid drop target found: {parent.__class__.__name__}", extra={"dev_only": True})
                    self._handle_drop_on_table()
                    valid_drop = True
                    break

                # Also check viewport of FileTableView
                if hasattr(parent, 'parent') and parent.parent():
                    if visual_manager.is_valid_drop_target(parent.parent(), "file_tree"):
                        logger.debug(f"[FileTreeView] Valid drop target found via viewport: {parent.parent().__class__.__name__}", extra={"dev_only": True})
                        self._handle_drop_on_table()
                        valid_drop = True
                        break

                # Check for policy violations
                if parent.__class__.__name__ in ['FileTreeView', 'MetadataTreeView']:
                    logger.debug(f"[FileTreeView] Rejecting drop on {parent.__class__.__name__} (policy violation)", extra={"dev_only": True})
                    break

                parent = parent.parent()

        # Log drop result
        if not valid_drop:
            logger.debug("[FileTreeView] Drop on invalid target", extra={"dev_only": True})

        # Clean up drag state
        self._is_dragging = False
        path = self._drag_path
        self._drag_path = None
        self._drag_start_pos = None

        # Restore mouse tracking to original state
        if hasattr(self, '_original_mouse_tracking'):
            self.setMouseTracking(self._original_mouse_tracking)
            delattr(self, '_original_mouse_tracking')

        # End visual feedback
        end_drag_visual()

        # Notify DragManager
        drag_manager.end_drag("file_tree")

        logger.debug(f"[FileTreeView] Custom drag ended: {path} (valid_drop: {valid_drop})", extra={"dev_only": True})

    def _handle_drop_on_table(self):
        """Handle drop on file table with new 4-modifier logic"""
        if not self._drag_path:
            return

        # Use real-time modifiers at drop time (standard UX behavior)
        modifiers = QApplication.keyboardModifiers()

        # Emit signal with single path and modifiers
        self.item_dropped.emit(self._drag_path, modifiers)

        # Log the action for debugging using centralized logic
        _, _, action = decode_modifiers_to_flags(modifiers)

        logger.info(f"[FileTreeView] Dropped: {self._drag_path} ({action})")

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
        """Handle key press events, including modifier changes during drag"""
        # Update drag feedback if we're currently dragging
        if self._is_dragging:
            self._update_drag_feedback()

        # Handle Return/Enter key to emit folder_selected signal
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.folder_selected.emit()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        """Handle key release events, including modifier changes during drag"""
        # Update drag feedback if we're currently dragging
        if self._is_dragging:
            self._update_drag_feedback()

        super().keyReleaseEvent(event)

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
