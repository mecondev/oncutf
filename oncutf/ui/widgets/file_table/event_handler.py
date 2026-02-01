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

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QKeySequence, QMouseEvent
from PyQt5.QtWidgets import QApplication

from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_ui_update

if TYPE_CHECKING:
    from oncutf.ui.widgets.file_table.view import FileTableView

logger = get_cached_logger(__name__)


def _format_modifiers(modifiers: Qt.KeyboardModifiers) -> str:
    """Format Qt modifiers to readable string for logging.

    Args:
        modifiers: Qt keyboard modifiers

    Returns:
        Human-readable string like "Ctrl+Shift", "Ctrl", "Shift", or "None"

    """
    if modifiers == Qt.NoModifier:
        return "None"

    parts = []
    if modifiers & Qt.ControlModifier:
        parts.append("Ctrl")
    if modifiers & Qt.ShiftModifier:
        parts.append("Shift")
    if modifiers & Qt.AltModifier:
        parts.append("Alt")
    if modifiers & Qt.MetaModifier:
        parts.append("Meta")

    return "+".join(parts) if parts else "None"


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
        self._ctrl_drag_initial_selection: set[int] = set()
        self._ctrl_drag_active: bool = False
        self._ctrl_drag_start_row: int | None = None

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
        # Track if we're preserving selection for drag (will change on release if no drag happened)
        self._view._preserved_selection_for_drag = False

        if event.button() == Qt.LeftButton:
            # Allow drag start with no modifier or Shift (Shift = extended metadata)
            if modifiers in (Qt.NoModifier, Qt.ShiftModifier):
                self._view._drag_start_pos = event.pos()
            else:
                self._view._drag_start_pos = None

            # Clicking on empty space - clear selection
            if not index.isValid():
                if modifiers == Qt.NoModifier:
                    self._view._selection_behavior.set_anchor_row(None, emit_signal=False)
                    self._view.clearSelection()
                return True

            # Check if clicking on already selected item (for drag)
            current_selection = self._view._get_current_selection_safe()
            is_already_selected = index.row() in current_selection

            anchor_before = self._view._selection_behavior.get_anchor_row()
            logger.info(
                "[MOUSE PRESS] Row=%d, Modifiers=%s, AlreadySelected=%s, Selection=%s, Anchor=%s",
                index.row(),
                _format_modifiers(modifiers),
                is_already_selected,
                sorted(current_selection),
                anchor_before,
            )

            # Ctrl+drag lasso setup: store initial selection and start point, skip default handling
            if modifiers == Qt.ControlModifier:
                self._ctrl_drag_initial_selection = current_selection.copy()
                self._ctrl_drag_active = False
                self._ctrl_drag_start_row = index.row() if index.isValid() else None
                self._view._drag_start_pos = event.pos()
                self._view._preserved_selection_for_drag = False
                logger.info(
                    "[CTRL DRAG START] Start row=%s, selection=%s",
                    self._ctrl_drag_start_row,
                    sorted(self._ctrl_drag_initial_selection),
                )
                return True

            # If clicking on selected item without modifiers OR with Shift (extended drag), preserve selection for drag
            # Block selection changes by temporarily disconnecting selection model
            if (
                modifiers in (Qt.NoModifier, Qt.ShiftModifier)
                and is_already_selected
                and len(current_selection) > 1
            ):
                # Preserve selection without changing anchor (keep original anchor for correct drag behavior)
                logger.info(
                    "[PRESERVE] Preserving multi-selection for drag, clicked row=%d, keeping anchor=%s, selection=%s",
                    index.row(),
                    anchor_before,
                    sorted(current_selection),
                )
                self._view._preserved_selection_for_drag = True
                self._view._preserved_selection_rows = current_selection.copy()

                # Block signals to prevent selection model from changing selection
                selection_model = self._view.selectionModel()
                if selection_model:
                    # We want to PREVENT the default QTableView behavior which clears selection on click
                    # So we DON'T call super() at all for this specific case
                    # But we DO need to set the current index for focus purposes
                    from PyQt5.QtCore import QItemSelectionModel

                    selection_model.setCurrentIndex(index, QItemSelectionModel.Current)

                    # Ensure anchor is preserved (it might not change, but just in case)
                    self._view._selection_behavior.set_anchor_row(anchor_before, emit_signal=False)

                    logger.info(
                        "[PRESERVE] Skipped super(), set CurrentIndex=%d, selection=%s, anchor=%s",
                        index.row(),
                        sorted(self._view._get_current_selection_safe()),
                        self._view._selection_behavior.get_anchor_row(),
                    )
                    return True  # Prevent calling super
                return True

            # Handle selection based on modifiers
            if modifiers in (Qt.NoModifier, Qt.ControlModifier):
                self._view._selection_behavior.set_anchor_row(index.row(), emit_signal=False)
            elif modifiers == Qt.ShiftModifier:
                anchor = self._view._selection_behavior.get_anchor_row()
                if anchor is not None:
                    self._view._selection_behavior.select_rows_range(anchor, index.row())
                    return True
                self._view._selection_behavior.set_anchor_row(index.row(), emit_signal=False)

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

        # Double-click should NOT change selection - just use current state
        # Only sync the current selection to SelectionStore
        self._view._selection_behavior.sync_selection_safely()
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
            # Ctrl drag/toggle handling on release
            modifiers = event.modifiers()
            if modifiers == Qt.ControlModifier and self._view._drag_start_pos is not None:
                # Determine if drag happened
                actual_drag_happened = self._ctrl_drag_active
                if not actual_drag_happened:
                    from PyQt5.QtWidgets import QApplication

                    distance = (event.pos() - self._view._drag_start_pos).manhattanLength()
                    actual_drag_happened = distance >= QApplication.startDragDistance()

                start_index = self._view.indexAt(self._view._drag_start_pos)
                start_row = (
                    start_index.row() if start_index.isValid() else self._ctrl_drag_start_row
                )
                end_row = (
                    self._view.indexAt(event.pos()).row()
                    if self._view.indexAt(event.pos()).isValid()
                    else start_row
                )

                if start_row is not None and end_row is not None and actual_drag_happened:
                    range_rows = set(range(min(start_row, end_row), max(start_row, end_row) + 1))
                    toggled = self._ctrl_drag_initial_selection.symmetric_difference(range_rows)
                    logger.info(
                        "[CTRL DRAG END] range=%s-%s, initial=%s, final=%s",
                        start_row,
                        end_row,
                        sorted(self._ctrl_drag_initial_selection),
                        sorted(toggled),
                    )
                    self._view._selection_behavior.update_selection_store(toggled, emit_signal=True)
                    self._view._selection_behavior.set_anchor_row(start_row, emit_signal=False)
                    was_dragging = True
                # Treat as simple Ctrl toggle
                elif self._view._clicked_index is not None and self._view._clicked_index.isValid():
                    self._view._selection_behavior.ensure_anchor_or_select(
                        self._view._clicked_index, Qt.ControlModifier
                    )

                # Reset Ctrl drag state
                self._ctrl_drag_active = False
                self._ctrl_drag_initial_selection = set()
                self._ctrl_drag_start_row = None
                self._view._drag_start_pos = None
                self._view._preserved_selection_for_drag = False
                self._view._preserved_selection_rows = set()
                return True

            # Check if we preserved selection for drag but no drag happened
            # In this case, select only the clicked item
            current_selection = self._view._get_current_selection_safe()
            anchor_before = self._view._selection_behavior.get_anchor_row()

            # Check if user actually moved the mouse (real drag vs accidental micro-movement)
            actual_drag_happened = self._view._drag_drop_behavior.is_dragging
            if not actual_drag_happened and self._view._drag_start_pos is not None:
                from PyQt5.QtWidgets import QApplication

                distance = (event.pos() - self._view._drag_start_pos).manhattanLength()
                # Only consider it a real drag if moved at least the drag distance
                actual_drag_happened = distance >= QApplication.startDragDistance()

            logger.info(
                "[MOUSE RELEASE] Preserved=%s, IsDragging=%s, ActualDrag=%s, ClickedRow=%s, Selection=%s, Anchor=%s",
                self._view._preserved_selection_for_drag,
                self._view._drag_drop_behavior.is_dragging,
                actual_drag_happened,
                self._view._clicked_index.row()
                if self._view._clicked_index and self._view._clicked_index.isValid()
                else None,
                sorted(current_selection),
                anchor_before,
            )

            # If we preserved selection but no actual drag happened, select only clicked item
            if (
                self._view._preserved_selection_for_drag
                and not actual_drag_happened
                and self._view._clicked_index is not None
                and self._view._clicked_index.isValid()
            ):
                # User clicked on selected item but didn't drag - select only that item
                logger.info(
                    "[SINGLE SELECT] Converting multi-selection to single: %d",
                    self._view._clicked_index.row(),
                )
                from PyQt5.QtCore import QItemSelectionModel

                sm = self._view.selectionModel()
                if sm:
                    sm.select(
                        self._view._clicked_index,
                        QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
                    )
                    sm.setCurrentIndex(self._view._clicked_index, QItemSelectionModel.NoUpdate)
                    self._view._selection_behavior.set_anchor_row(
                        self._view._clicked_index.row(), emit_signal=False
                    )
                    # Sync to store
                    selection_store = self._view._selection_behavior.get_selection_store()
                    if selection_store:
                        selection_store.set_selected_rows(
                            {self._view._clicked_index.row()}, emit_signal=True
                        )
                    anchor_after = self._view._selection_behavior.get_anchor_row()
                    new_selection = self._view._get_current_selection_safe()
                    logger.info(
                        "[SINGLE SELECT] Done - Selection=%s, Anchor=%s -> %s",
                        sorted(new_selection),
                        anchor_before,
                        anchor_after,
                    )

            # Clear preserved selection cache
            self._view._preserved_selection_rows = set()

            self._view._drag_start_pos = None
            self._view._preserved_selection_for_drag = False

            if self._view._drag_drop_behavior.is_dragging:
                was_dragging = True
                self._view._drag_drop_behavior.end_drag()

                # Final status update after drag ends
                def final_status_update():
                    current_selection = self._view._selection_behavior.get_current_selection()
                    if current_selection:
                        selection_store = self._view._selection_behavior.get_selection_store()
                        if selection_store:
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

        # Handle drag operations (allow shift for extended metadata, but with higher threshold)
        if event.buttons() & Qt.LeftButton:
            # Ctrl+drag lasso toggle
            if event.modifiers() & Qt.ControlModifier:
                if self._view._drag_start_pos is None:
                    return True

                base_distance = QApplication.startDragDistance()
                distance = (event.pos() - self._view._drag_start_pos).manhattanLength()
                if distance < base_distance:
                    return True

                start_index = self._view.indexAt(self._view._drag_start_pos)
                start_row = (
                    start_index.row() if start_index.isValid() else self._ctrl_drag_start_row
                )
                end_row = index.row() if index.isValid() else start_row

                if start_row is None or end_row is None:
                    return True

                self._ctrl_drag_active = True
                range_rows = set(range(min(start_row, end_row), max(start_row, end_row) + 1))
                toggled = self._ctrl_drag_initial_selection.symmetric_difference(range_rows)
                self._view._selection_behavior.update_selection_store(toggled, emit_signal=True)
                self._view._selection_behavior.set_anchor_row(start_row, emit_signal=False)
                logger.info(
                    "[CTRL DRAG MOVE] start=%s end=%s range=%s selection=%s",
                    start_row,
                    end_row,
                    sorted(range_rows),
                    sorted(toggled),
                )
                return True

            # Don't allow drag with Ctrl/Alt modifiers (only Shift is allowed)
            if (
                self._view._drag_start_pos is not None
                and event.modifiers() & (Qt.ControlModifier | Qt.AltModifier)
            ):
                self._view._drag_start_pos = None
                return False

            # If drag start was cancelled (e.g., due to modifiers), skip drag detection
            if self._view._drag_start_pos is None:
                return True

            # Calculate required drag distance based on modifiers
            # Shift+drag for extended metadata needs 3x the normal distance to prevent accidental selection changes
            base_distance = QApplication.startDragDistance()
            required_distance = (
                base_distance * 3 if event.modifiers() & Qt.ShiftModifier else base_distance
            )

            distance = (event.pos() - self._view._drag_start_pos).manhattanLength()

            if distance >= required_distance:
                start_index = self._view.indexAt(self._view._drag_start_pos)
                if start_index.isValid():
                    start_row = start_index.row()
                    if start_row in self._view._selection_behavior.get_current_selection_safe():
                        # If selection was preserved for drag, ensure it is restored before starting drag
                        preserved_rows = getattr(self._view, "_preserved_selection_rows", set())
                        if preserved_rows:
                            current = self._view._selection_behavior.get_current_selection_safe()
                            if current != preserved_rows:
                                selection_store = (
                                    self._view._selection_behavior.get_selection_store()
                                )
                                if selection_store:
                                    selection_store.set_selected_rows(
                                        preserved_rows, emit_signal=False
                                    )
                                self._view._selection_behavior.set_anchor_row(
                                    self._view._selection_behavior.get_anchor_row(),
                                    emit_signal=False,
                                )
                                logger.info(
                                    "[DRAG] Restored preserved selection before drag: %s -> %s",
                                    sorted(current),
                                    sorted(preserved_rows),
                                )
                        self._view._drag_start_pos = None
                        self._view._drag_drop_behavior.start_drag()
                        return True

            # Left button held but drag not yet triggered: block default Qt rubber-band selection
            # to avoid accidental lasso selection when preparing to drag.
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
        if (
            hasattr(self._view, "_column_mgmt_behavior")
            and self._view._column_mgmt_behavior.handle_keyboard_shortcut(
                event.key(), event.modifiers()
            )
        ):
            return True

        # Skip key handling during drag
        if self._view._drag_drop_behavior.is_dragging:
            self._view._drag_drop_behavior._update_drag_feedback()
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
            self._view._drag_drop_behavior._update_drag_feedback()
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
            from oncutf.ui.helpers.selection_provider import get_selected_row_set

            selected_rows = get_selected_row_set(selection_model)
            self._view._selection_behavior.update_selection_store(selected_rows, emit_signal=False)

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
