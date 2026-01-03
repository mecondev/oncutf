"""Module: event_handler.py - Qt event handlers for FileTableView.

Author: Michael Economou
Date: 2026-01-04

Handles Qt events for the table view:
- Mouse events (press, release, move, double-click)
- Keyboard events (press, release)
- Focus events (in, out)
- Enter/leave events for view and viewport
- Wheel events for scrolling
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.core.pyqt_imports import (
    QApplication,
    QCursor,
    QKeySequence,
    QMouseEvent,
    Qt,
)
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_ui_update

if TYPE_CHECKING:
    from oncutf.ui.widgets.file_table.view import FileTableView

logger = get_cached_logger(__name__)


class EventHandler:
    """Handles Qt events for FileTableView.

    This handler manages all Qt event overrides, delegating to
    specialized handlers (hover, tooltip, viewport) as needed.

    Attributes:
        _view: Reference to the parent FileTableView
    """

    def __init__(self, view: FileTableView) -> None:
        """Initialize event handler.

        Args:
            view: The parent FileTableView widget
        """
        self._view = view

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events for selection and drag initiation.

        Args:
            event: The mouse press event

        Returns:
            True if event was fully handled (skip super call)
        """
        index = self._view.indexAt(event.pos())
        modifiers = event.modifiers()

        # Store clicked index for potential drag
        self._view._clicked_index = index

        if event.button() == Qt.LeftButton:
            # Store drag start position
            self._view._drag_start_pos = event.pos()

            # Clicking on empty space - clear selection
            if not index.isValid():
                if modifiers == Qt.NoModifier:
                    self._view._set_anchor_row(None, emit_signal=False)
                    self._view.clearSelection()
                return True

            # Handle selection based on modifiers
            if modifiers in (Qt.NoModifier, Qt.ControlModifier):
                self._view._set_anchor_row(index.row(), emit_signal=False)
            elif modifiers == Qt.ShiftModifier:
                anchor = self._view._get_anchor_row()
                if anchor is not None:
                    self._view.select_rows_range(anchor, index.row())
                    return True
                else:
                    self._view._set_anchor_row(index.row(), emit_signal=False)

        return False  # Call super

    def handle_mouse_double_click(self, event: QMouseEvent) -> bool:
        """Handle double-click events.

        Args:
            event: The mouse double-click event

        Returns:
            True if event was fully handled
        """
        if self._view.is_empty():
            return True

        index = self._view.indexAt(event.pos())
        if not index.isValid():
            return False

        selection_model = self._view.selectionModel()
        from oncutf.core.pyqt_imports import QItemSelectionModel

        if event.modifiers() & Qt.ShiftModifier:
            # Cancel range selection for extended metadata on single file
            selection_model.clearSelection()
            selection_model.select(
                index,
                QItemSelectionModel.Clear | QItemSelectionModel.Select | QItemSelectionModel.Rows,
            )
            selection_model.setCurrentIndex(index, QItemSelectionModel.NoUpdate)
            self._view._manual_anchor_index = index
        else:
            self._view.ensure_anchor_or_select(index, event.modifiers())

        self._view._sync_selection_safely()
        return False

    def handle_mouse_release(self, event: QMouseEvent) -> bool:
        """Handle mouse release events.

        Args:
            event: The mouse release event

        Returns:
            True if super call should be skipped
        """
        was_dragging = False
        if event.button() == Qt.LeftButton:
            self._view._drag_start_pos = None

            if self._view._drag_drop_behavior.is_dragging:
                was_dragging = True
                self._view._end_custom_drag()

                # Final status update after drag ends
                def final_status_update():
                    current_selection = self._view._get_current_selection()
                    if current_selection:
                        selection_store = self._view._get_selection_store()
                        if selection_store and not self._view._legacy_selection_mode:
                            selection_store.selection_changed.emit(list(current_selection))

                schedule_ui_update(final_status_update, delay=50)

        return was_dragging

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events for drag and hover.

        Args:
            event: The mouse move event

        Returns:
            True if event was fully handled
        """
        if self._view.is_empty():
            return True

        index = self._view.indexAt(event.pos())
        hovered_row = index.row() if index.isValid() else -1

        # Handle drag operations
        if event.buttons() & Qt.LeftButton and self._view._drag_start_pos is not None:
            distance = (event.pos() - self._view._drag_start_pos).manhattanLength()

            if distance >= QApplication.startDragDistance():
                start_index = self._view.indexAt(self._view._drag_start_pos)
                if start_index.isValid():
                    start_row = start_index.row()
                    if start_row in self._view._get_current_selection_safe():
                        self._view._drag_start_pos = None
                        self._view._start_custom_drag()
                        return True

        # Skip hover updates if dragging
        if self._view._drag_drop_behavior.is_dragging:
            return True

        # Update hover highlighting
        self._view._hover_handler.handle_mouse_move(hovered_row)
        return False

    def handle_key_press(self, event) -> bool:
        """Handle keyboard events.

        Args:
            event: The key press event

        Returns:
            True if event was handled and should be accepted
        """
        # Handle F5 refresh
        if event.key() == Qt.Key_F5:
            self._view.refresh_requested.emit()
            return True

        # Handle column management shortcuts
        if hasattr(self._view, "_column_mgmt_behavior"):
            if self._view._column_mgmt_behavior.handle_keyboard_shortcut(
                event.key(), event.modifiers()
            ):
                return True

        # Skip key handling during drag
        if self._view._drag_drop_behavior.is_dragging:
            self._view._update_drag_feedback()
            return True

        return False

    def handle_key_release(self, event) -> bool:
        """Handle key release events.

        Args:
            event: The key release event

        Returns:
            True if super call should be skipped
        """
        if self._view._drag_drop_behavior.is_dragging:
            self._view._update_drag_feedback()
            return True
        return False

    def handle_focus_out(self, event) -> None:
        """Handle focus out events."""
        if self._view.context_focused_row is not None:
            self._view.context_focused_row = None

        # Clear hover state
        self._view._hover_handler.handle_leave()

        # Clear tooltips
        self._view._tooltip_handler.clear_for_widget()

        self._view.viewport().update()

    def handle_focus_in(self, event) -> None:
        """Handle focus in events."""
        selection_model = self._view.selectionModel()
        if selection_model is not None:
            from oncutf.utils.ui.selection_provider import get_selected_row_set

            selected_rows = get_selected_row_set(selection_model)
            self._view._update_selection_store(selected_rows, emit_signal=False)

        self._view.viewport().update()

    def handle_leave(self, event) -> None:
        """Handle mouse leave events."""
        self._view._hover_handler.handle_leave()
        self._view._tooltip_handler.clear_for_widget()

    def handle_enter(self, event) -> None:
        """Handle mouse enter events."""
        pos = self._view.viewport().mapFromGlobal(QCursor.pos())
        index = self._view.indexAt(pos)
        hovered_row = index.row() if index.isValid() else -1
        self._view._hover_handler.update_hover_row(hovered_row)

    def handle_viewport_leave(self, event) -> None:
        """Handle viewport leave events."""
        self._view._hover_handler.handle_leave()
        self._view._tooltip_handler.clear()

        # Call original viewport leaveEvent
        original = getattr(self._view.viewport(), "_original_leave_event", None)
        if original:
            original(event)

    def handle_viewport_enter(self, event) -> None:
        """Handle viewport enter events."""
        pos = self._view.viewport().mapFromGlobal(QCursor.pos())
        index = self._view.indexAt(pos)
        hovered_row = index.row() if index.isValid() else -1
        self._view._hover_handler.update_hover_row(hovered_row)

        # Call original viewport enterEvent
        original = getattr(self._view.viewport(), "_original_enter_event", None)
        if original:
            original(event)

    def handle_wheel(self, event) -> bool:
        """Handle wheel events.

        Args:
            event: The wheel event

        Returns:
            True if event was fully handled
        """
        # Standard wheel handling - can be extended
        return False

    def should_sync_selection_after_key(self, event) -> bool:
        """Check if selection should be synced after key event.

        Args:
            event: The key event

        Returns:
            True if selection sync is needed
        """
        return event.matches(QKeySequence.SelectAll) or event.key() in (
            Qt.Key_Space,
            Qt.Key_Return,
            Qt.Key_Enter,
            Qt.Key_Up,
            Qt.Key_Down,
            Qt.Key_Left,
            Qt.Key_Right,
        )
