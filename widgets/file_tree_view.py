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

from PyQt5.QtCore import QEvent, QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QCursor, QKeyEvent, QMouseEvent
from PyQt5.QtWidgets import QApplication
from core.qt_imports import QAbstractItemView, QHeaderView, QTreeView

from config import ALLOWED_EXTENSIONS
from core.drag_manager import DragManager
from core.drag_visual_manager import (
    DragVisualManager,
    DropZoneState,
    end_drag_visual,
    start_drag_visual,
    update_drop_zone_state,
    update_modifier_state,
)
from core.modifier_handler import decode_modifiers_to_flags
from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_scroll_adjust

logger = get_cached_logger(__name__)


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

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Enable drag so Qt can call startDrag, but we'll override it
        self.setDragEnabled(True)
        self.setAcceptDrops(True)  # We still need to accept drops
        self.setDragDropMode(QAbstractItemView.DragDrop)  # Enable both drag and drop

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
        self._drag_preparation = False  # Flag to block hover during drag preparation

        logger.debug("[FileTreeView] Initialized with single-item drag system", extra={"dev_only": True})

    def selectionChanged(self, selected, deselected) -> None:
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

    def setModel(self, model) -> None:
        """Override to configure header when model is set"""
        super().setModel(model)
        self._configure_header()
        logger.debug(f"[FileTreeView] Model set: {type(model).__name__ if model else 'None'}", extra={"dev_only": True})

    def resizeEvent(self, event) -> None:
        """Handle resize to adjust column width for optimal horizontal scrolling"""
        super().resizeEvent(event)
        self._adjust_column_width()

    def _configure_header(self) -> None:
        """Configure header for optimal display"""
        header = self.header()
        if header:
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)

            # Hide all columns except the first (name)
            for col in range(1, self.model().columnCount() if self.model() else 4):
                self.setColumnHidden(col, True)

            logger.debug("[FileTreeView] Header configured for single column display", extra={"dev_only": True})

    def _adjust_column_width(self) -> None:
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

    def _on_model_changed(self) -> None:
        """Called when model data changes to update column width"""
        schedule_scroll_adjust(self._adjust_column_width, 10)

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

    def select_path(self, path: str) -> None:
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
        # If we're dragging, only handle drag feedback and block all other processing
        if self._is_dragging:
            self._update_drag_feedback()
            # Don't call super().mouseMoveEvent() during drag to prevent hover changes
            return

        # Only proceed if left button is pressed and we have a start position
        if not (event.buttons() & Qt.LeftButton) or not self._drag_start_pos:
            # Reset drag preparation if no drag is happening
            if self._drag_preparation:
                self._drag_preparation = False
            super().mouseMoveEvent(event)
            return

        # Check if we've moved enough to start drag
        distance = (event.pos() - self._drag_start_pos).manhattanLength()
        if distance < QApplication.startDragDistance():
            # We're in drag preparation - block hover
            if not self._drag_preparation:
                self._drag_preparation = True
                # Clear hover immediately
                self.viewport().update()
                self.update()
            # Don't call super() to prevent hover updates during preparation
            return

        # Start our custom drag
        self._start_custom_drag()
        # Don't call super().mouseMoveEvent() after starting drag to prevent hover changes

    def mouseReleaseEvent(self, event):
        """Handle mouse release to end drag"""
        was_dragging = self._is_dragging

        # End drag first
        self._end_custom_drag()

        # Call super() for normal processing
        super().mouseReleaseEvent(event)

        # Force cursor cleanup if we were dragging
        if was_dragging:
            # Ensure all override cursors are removed
            cursor_count = 0
            while QApplication.overrideCursor() and cursor_count < 5:
                QApplication.restoreOverrideCursor()
                cursor_count += 1

            if cursor_count > 0:
                logger.debug(f"[FileTreeView] Cleaned {cursor_count} stuck cursors after drag", extra={"dev_only": True})

            # Create a fake mouse move event to restore hover state
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

        # Clear any existing hover state more aggressively
        self.viewport().update()  # Force viewport repaint
        self.update()  # Force widget repaint

        # Disable hover attribute temporarily
        self._original_hover_enabled = self.testAttribute(Qt.WA_Hover)
        self.setAttribute(Qt.WA_Hover, False)

        # Also disable hover on viewport
        self._original_viewport_hover = self.viewport().testAttribute(Qt.WA_Hover)
        self.viewport().setAttribute(Qt.WA_Hover, False)

        # Disable mouse tracking on viewport too
        self._original_viewport_tracking = self.viewport().hasMouseTracking()
        self.viewport().setMouseTracking(False)

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
            self._drag_preparation = False  # Clear preparation flag
            path = self._drag_path
            self._drag_path = None
            self._drag_start_pos = None

            # Restore mouse tracking to original state
            if hasattr(self, '_original_mouse_tracking'):
                self.setMouseTracking(self._original_mouse_tracking)
                delattr(self, '_original_mouse_tracking')

            # Restore hover attribute
            if hasattr(self, '_original_hover_enabled'):
                self.setAttribute(Qt.WA_Hover, self._original_hover_enabled)
                delattr(self, '_original_hover_enabled')

            # Restore viewport attributes
            if hasattr(self, '_original_viewport_hover'):
                self.viewport().setAttribute(Qt.WA_Hover, self._original_viewport_hover)
                delattr(self, '_original_viewport_hover')

            if hasattr(self, '_original_viewport_tracking'):
                self.viewport().setMouseTracking(self._original_viewport_tracking)
                delattr(self, '_original_viewport_tracking')

            # End visual feedback
            end_drag_visual()

            # Restore hover state with fake mouse move event
            self._restore_hover_after_drag()

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
        self._drag_preparation = False  # Clear preparation flag
        path = self._drag_path
        self._drag_path = None
        self._drag_start_pos = None

        # Restore mouse tracking to original state
        if hasattr(self, '_original_mouse_tracking'):
            self.setMouseTracking(self._original_mouse_tracking)
            delattr(self, '_original_mouse_tracking')

        # Restore hover attribute
        if hasattr(self, '_original_hover_enabled'):
            self.setAttribute(Qt.WA_Hover, self._original_hover_enabled)
            delattr(self, '_original_hover_enabled')

        # Restore viewport attributes
        if hasattr(self, '_original_viewport_hover'):
            self.viewport().setAttribute(Qt.WA_Hover, self._original_viewport_hover)
            delattr(self, '_original_viewport_hover')

        if hasattr(self, '_original_viewport_tracking'):
            self.viewport().setMouseTracking(self._original_viewport_tracking)
            delattr(self, '_original_viewport_tracking')

        # End visual feedback
        end_drag_visual()

        # Notify DragManager
        drag_manager.end_drag("file_tree")

        # Restore hover state with fake mouse move event
        self._restore_hover_after_drag()

        logger.debug(f"[FileTreeView] Custom drag ended: {path} (valid_drop: {valid_drop})", extra={"dev_only": True})

    def _restore_hover_after_drag(self):
        """Restore hover state after drag ends by sending a fake mouse move event"""
        # Get current cursor position relative to this widget
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)

        # Only restore hover if cursor is still over this widget
        if self.rect().contains(local_pos):
            # Create and post a fake mouse move event
            fake_move_event = QMouseEvent(
                QEvent.MouseMove,
                local_pos,
                Qt.NoButton,
                Qt.NoButton,
                Qt.NoModifier
            )
            QApplication.postEvent(self, fake_move_event)

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

        logger.info(f"[FileTreeView] Dropped: {self._drag_path} ({action})", extra={"dev_only": True})

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
        schedule_scroll_adjust(self._adjust_column_width, 50)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement (placeholder for future use)"""
        pass

    def scrollTo(self, index, hint=None) -> None:
        """Override to ensure optimal scrolling behavior"""
        super().scrollTo(index, hint or QAbstractItemView.EnsureVisible)

    def event(self, event):
        """Override event handling to block hover events during drag"""
        # Block hover events during drag or drag preparation (with safe attribute check)
        if ((hasattr(self, '_is_dragging') and self._is_dragging) or
            (hasattr(self, '_drag_preparation') and self._drag_preparation)) and \
            event.type() in (QEvent.HoverEnter, QEvent.HoverMove, QEvent.HoverLeave):
            return True  # Consume the event without processing

        return super().event(event)

    def startDrag(self, supported_actions):
        """Override Qt's built-in drag to prevent it from interfering with our custom drag"""
        # Do nothing - we handle all drag operations through our custom system
        # This prevents Qt from starting its own drag which could cause hover issues
        logger.debug("[FileTreeView] Built-in startDrag called but ignored - using custom drag system", extra={"dev_only": True})
        return


# =====================================
# DRAG CANCEL FILTER (Global Instance)
# =====================================

class DragCancelFilter:
    """
    Filter that prevents selection clearing during drag operations.

    This is used to maintain file selection when dragging from FileTableView
    to MetadataTreeView, especially when no modifier keys are pressed.
    """

    def __init__(self):
        self._active = False
        self._preserved_selection = set()

    def activate(self):
        """Activate the filter to preserve current selection"""
        self._active = True
        logger.debug("[DragCancelFilter] Activated - preserving selection", extra={"dev_only": True})

    def deactivate(self):
        """Deactivate the filter"""
        if self._active:
            self._active = False
            self._preserved_selection.clear()
            logger.debug("[DragCancelFilter] Deactivated", extra={"dev_only": True})

    def preserve_selection(self, selection: set):
        """Store selection to preserve during drag"""
        self._preserved_selection = selection.copy()

    def get_preserved_selection(self) -> set:
        """Get preserved selection"""
        return self._preserved_selection.copy()

    def is_active(self) -> bool:
        """Check if filter is active"""
        return self._active


# Create global instance
_drag_cancel_filter = DragCancelFilter()
