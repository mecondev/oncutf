"""Module: drag_drop_behavior.py

Author: Michael Economou
Date: 2025-12-28

DragDropBehavior - Composition-based drag-and-drop functionality.

This is the behavioral replacement for DragDropMixin.
Uses protocol-based composition instead of inheritance.

Protocol contract:
    - Widget must implement DraggableWidget protocol
    - Widget owns behavior instance
    - Widget routes events to behavior
"""

from typing import TYPE_CHECKING, Protocol

from oncutf.core.drag.drag_manager import DragManager
from oncutf.core.drag.drag_visual_manager import (
    DragType,
    DragVisualManager,
    end_drag_visual,
    start_drag_visual,
    update_drag_feedback_for_widget,
)
from oncutf.core.pyqt_imports import (
    QApplication,
    QCursor,
    QDropEvent,
    QEvent,
    QModelIndex,
    QMouseEvent,
    Qt,
)
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import cancel_timer, schedule_ui_update
from oncutf.utils.ui.file_drop_helper import extract_file_paths

if TYPE_CHECKING:
    from oncutf.core.pyqt_imports import QRect

logger = get_cached_logger(__name__)


class DraggableWidget(Protocol):
    """Protocol defining requirements for widgets that can use DragDropBehavior.

    This protocol ensures widgets provide all necessary Qt methods and
    application-specific functionality needed for drag-and-drop operations.
    """

    def model(self):
        """Return Qt model."""
        ...

    def viewport(self):
        """Return viewport widget."""
        ...

    def visualRect(self, index: QModelIndex) -> "QRect":
        """Return visual rectangle for model index."""
        ...

    def rect(self) -> "QRect":
        """Return widget rectangle."""
        ...

    def mapFromGlobal(self, pos):
        """Map global position to widget coordinates."""
        ...

    def blockSignals(self, block: bool) -> bool:
        """Block/unblock signals."""
        ...

    def _get_current_selection_safe(self) -> set[int]:
        """Get current selection safely (fallback method)."""
        ...

    def _get_current_selection(self) -> set[int]:
        """Get current selection from SelectionStore."""
        ...

    def _get_selection_store(self):
        """Get SelectionStore instance."""
        ...

    def _force_cursor_cleanup(self) -> None:
        """Force cursor cleanup."""
        ...


class DragDropBehavior:
    """Behavior class providing drag-and-drop functionality.

    This is the composition-based replacement for DragDropMixin.
    Encapsulates all drag-drop logic in a testable, protocol-based class.

    State management:
    - All drag state is stored in this behavior instance
    - No state pollution in widget's __dict__
    - Clear lifecycle: start -> feedback -> end

    Usage:
        class MyTableView(QTableView):
            def __init__(self):
                super().__init__()
                self._drag_drop = DragDropBehavior(self)

            def mousePressEvent(self, event):
                if self._drag_drop.should_start_drag(event):
                    self._drag_drop.start_drag()
                super().mousePressEvent(event)
    """

    def __init__(self, widget: DraggableWidget):
        """Initialize behavior with widget reference.

        Args:
            widget: Widget implementing DraggableWidget protocol
        """
        self._widget = widget

        # Drag state
        self._is_dragging = False
        self._drag_data: list[str] | None = None
        self._drag_feedback_timer_id: int | None = None
        self._drag_end_time: float = 0.0
        self._successful_metadata_drop = False

        # Selection preservation flags
        self._preserve_selection_for_drag = False
        self._clicked_on_selected = False
        self._clicked_index: QModelIndex | None = None
        self._legacy_selection_mode = True

        # Large selection optimization
        self._drag_pending_rows: list[int] | None = None

    # =====================================
    # Public API
    # =====================================

    def start_drag(self) -> None:
        """Start custom drag operation with enhanced visual feedback."""
        if self._is_dragging:
            return

        # Clean up selection preservation flags
        self._preserve_selection_for_drag = False
        self._clicked_on_selected = False
        self._clicked_index = None

        # Get selected file data
        selected_rows = self._widget._get_current_selection_safe()
        if not selected_rows:
            return

        # Check if model and files are available
        model = self._widget.model()
        if not model or not hasattr(model, 'files'):
            logger.debug("[DragDropBehavior] Model or files not available, cannot start drag")
            return

        # Performance optimization: For large selections, collect paths lazily
        rows = sorted(selected_rows)
        file_count = len(rows)

        # For small selections (<100), collect all paths immediately
        if file_count < 100:
            file_items = [
                model.files[r]
                for r in rows
                if 0 <= r < len(model.files)
            ]
            file_paths = [f.full_path for f in file_items if f.full_path]
        else:
            # Large selection: collect only first 3 paths for preview
            preview_rows = rows[:3]
            preview_items = [
                model.files[r]
                for r in preview_rows
                if 0 <= r < len(model.files)
            ]
            file_paths = [f.full_path for f in preview_items if f.full_path]
            self._drag_pending_rows = rows

        if not file_paths:
            return

        # Activate drag cancel filter
        from oncutf.ui.widgets.file_tree_view import _drag_cancel_filter

        _drag_cancel_filter.activate()
        _drag_cancel_filter.preserve_selection(selected_rows)

        # Clear hover state before starting drag
        if hasattr(self._widget, "hover_delegate"):
            old_row = self._widget.hover_delegate.hovered_row
            self._widget.hover_delegate.update_hover_row(-1)
            if old_row >= 0:
                left = self._widget.model().index(old_row, 0)
                right = self._widget.model().index(old_row, self._widget.model().columnCount() - 1)
                row_rect = self._widget.visualRect(left).united(self._widget.visualRect(right))
                self._widget.viewport().update(row_rect)

        # Set drag state
        self._is_dragging = True
        self._drag_data = file_paths

        # Stop any existing drag feedback timer
        if self._drag_feedback_timer_id:
            cancel_timer(self._drag_feedback_timer_id)

        # Notify DragManager
        drag_manager = DragManager.get_instance()
        drag_manager.start_drag("file_table")

        # Start enhanced visual feedback
        visual_manager = DragVisualManager.get_instance()

        # Determine drag type and info string
        actual_count = file_count if self._drag_pending_rows else len(file_paths)

        if actual_count == 1:
            drag_type = visual_manager.get_drag_type_from_path(file_paths[0])
            import os

            source_info = os.path.basename(file_paths[0])
        else:
            drag_type = DragType.MULTIPLE
            source_info = f"{actual_count} files"

        start_drag_visual(drag_type, source_info, "file_table")

        # Start drag feedback loop
        self._start_drag_feedback_loop()

    def end_drag(self) -> None:
        """End custom drag operation."""
        if not self._is_dragging:
            return

        # Check if drag was cancelled
        drag_manager = DragManager.get_instance()
        drag_was_cancelled = not drag_manager.is_drag_active()

        if drag_was_cancelled:
            logger.info("[DragDropBehavior] Drag cancelled, cleaning up without drop")

        try:
            # Stop drag feedback timer
            if self._drag_feedback_timer_id:
                cancel_timer(self._drag_feedback_timer_id)
                self._drag_feedback_timer_id = None

            # Force cursor cleanup
            self._widget._force_cursor_cleanup()

            # Deactivate drag cancel filter
            from oncutf.ui.widgets.file_tree_view import _drag_cancel_filter

            if _drag_cancel_filter.is_active():
                _drag_cancel_filter.deactivate()

            # Only attempt drop detection if not cancelled
            if not drag_was_cancelled:
                cursor_pos = QCursor.pos()
                widget_under_cursor = QApplication.widgetAt(cursor_pos)

                if widget_under_cursor:
                    parent = widget_under_cursor
                    while parent:
                        if parent.__class__.__name__ == "MetadataTreeView":
                            self._handle_drop_on_metadata_tree()
                            break
                        parent = parent.parent()
            else:
                self._drag_data = None

        finally:
            # Clean up drag state
            self._is_dragging = False
            self._drag_data = None

            # Record drag end time
            import time

            self._drag_end_time = time.time() * 1000

            # Cleanup visual feedback
            end_drag_visual()

            # Notify DragManager
            drag_manager.end_drag("file_table")

            # Restore hover
            self._restore_hover_after_drag()

    def handle_drag_enter(self, event) -> bool:
        """Handle drag enter event.

        Returns:
            True if event was handled, False to delegate to parent
        """
        if event.mimeData().hasUrls() or event.mimeData().hasFormat(
            "application/x-oncutf-internal"
        ):
            event.acceptProposedAction()
            return True
        return False

    def handle_drag_move(self, event) -> bool:
        """Handle drag move event.

        Returns:
            True if event was handled, False to delegate to parent
        """
        if event.mimeData().hasUrls() or event.mimeData().hasFormat(
            "application/x-oncutf-internal"
        ):
            event.acceptProposedAction()
            return True
        return False

    def handle_drop(self, event: QDropEvent) -> tuple[list[str], object] | None:
        """Handle drop event.

        Returns:
            Tuple of (dropped_paths, modifiers) if successful, None otherwise
        """
        mime_data = event.mimeData()

        # Ignore internal drags
        if mime_data.hasFormat("application/x-oncutf-filetable"):
            return None

        # Extract dropped paths
        modifiers = event.keyboardModifiers()
        dropped_paths = extract_file_paths(mime_data)

        if not dropped_paths:
            return None

        # Filter out duplicates
        if self._widget.model() and hasattr(self._widget.model(), "files"):
            existing_paths = {f.full_path for f in self._widget.model().files}
            new_paths = [p for p in dropped_paths if p not in existing_paths]
            if not new_paths:
                return None
        else:
            new_paths = dropped_paths

        event.acceptProposedAction()
        return (new_paths, modifiers)

    # =====================================
    # State Query
    # =====================================

    @property
    def is_dragging(self) -> bool:
        """Check if drag is currently active."""
        return self._is_dragging

    @property
    def drag_end_time(self) -> float:
        """Get timestamp of last drag end (milliseconds)."""
        return self._drag_end_time

    @property
    def successful_metadata_drop(self) -> bool:
        """Check if last drag resulted in successful metadata drop."""
        return self._successful_metadata_drop

    # =====================================
    # Internal Implementation
    # =====================================

    def _start_drag_feedback_loop(self) -> None:
        """Start repeated drag feedback updates with adaptive delay."""
        if self._is_dragging:
            self._update_drag_feedback()

            # Adaptive delay based on selection size
            selected_count = len(self._widget._get_current_selection_safe())
            if selected_count > 500:
                delay = 200
            elif selected_count > 100:
                delay = 150
            else:
                delay = 100

            self._drag_feedback_timer_id = schedule_ui_update(
                self._start_drag_feedback_loop, delay=delay
            )

    def _update_drag_feedback(self) -> None:
        """Update visual feedback based on cursor position."""
        if not self._is_dragging:
            return

        should_continue = update_drag_feedback_for_widget(self._widget, "file_table")

        if not should_continue:
            self.end_drag()

    def _restore_hover_after_drag(self) -> None:
        """Restore hover state after drag ends."""
        if not hasattr(self._widget, "hover_delegate"):
            return

        global_pos = QCursor.pos()
        local_pos = self._widget.mapFromGlobal(global_pos)

        if self._widget.rect().contains(local_pos):
            fake_move_event = QMouseEvent(
                QEvent.MouseMove, local_pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier
            )
            QApplication.postEvent(self._widget, fake_move_event)

    def _handle_drop_on_metadata_tree(self) -> bool:
        """Handle drop on metadata tree.

        Returns:
            True if drop was successful
        """
        if not self._drag_data:
            logger.debug(
                "[DragDropBehavior] No drag data for metadata tree drop", extra={"dev_only": True}
            )
            return False

        selected_rows = self._widget._get_current_selection()
        if not selected_rows:
            logger.warning("[DragDropBehavior] No valid selection for metadata tree drop")
            return False

        # Get parent window
        parent_window = self._get_parent_with_metadata_tree()
        if not parent_window:
            logger.warning("[DragDropBehavior] Could not find parent window")
            return False

        # Get file items
        try:
            file_items = parent_window.get_selected_files_ordered()
            if not file_items:
                logger.warning("[DragDropBehavior] No valid file items for metadata tree drop")
                return False
        except (AttributeError, IndexError) as e:
            logger.error("[DragDropBehavior] Error getting selected files: %s", e)
            return False

        # Get modifiers
        modifiers = QApplication.keyboardModifiers()
        use_extended = bool(modifiers & Qt.ShiftModifier)

        # Verify app_service
        if not hasattr(parent_window, "app_service"):
            logger.warning("[DragDropBehavior] Could not find app_service")
            return False

        # Delegate to ApplicationService
        try:
            parent_window.app_service.load_metadata_for_items(
                file_items, use_extended=use_extended, source="drag_drop"
            )

            self._successful_metadata_drop = True
            logger.info(
                "[DragDropBehavior] Metadata load initiated: %d files (extended=%s)",
                len(file_items),
                use_extended,
            )

            # Immediately update selection to ensure metadata tree refreshes
            current_selection = self._widget._get_current_selection()
            if current_selection:
                selection_store = self._widget._get_selection_store()
                if selection_store:
                    # Emit signal to update metadata tree
                    selection_store.selection_changed.emit(list(current_selection))
                    logger.debug(
                        "[DragDropBehavior] Emitted selection_changed for %d items after metadata drop",
                        len(current_selection),
                        extra={"dev_only": True}
                    )

            return True

        except Exception as e:
            logger.error("[DragDropBehavior] Error initiating metadata load: %s", e)
            return False

    def _get_parent_with_metadata_tree(self):
        """Find parent window with metadata_tree_view attribute."""
        from oncutf.utils.filesystem.path_utils import find_parent_with_attribute

        return find_parent_with_attribute(self._widget, "metadata_tree_view")
