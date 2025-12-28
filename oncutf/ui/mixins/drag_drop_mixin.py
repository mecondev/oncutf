"""Module: drag_drop_mixin.py

Author: Michael Economou
Date: 2025-12-04

DragDropMixin - Reusable drag-and-drop functionality for QTableView-based widgets.

Provides:
- Custom drag operation with enhanced visual feedback
- Drag lifecycle management (start, feedback, end)
- Drop handling on metadata tree
- Hover state restoration after drag
- Integration with DragManager and DragVisualManager
"""

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
    QMouseEvent,
    Qt,
)
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import cancel_timer, schedule_ui_update
from oncutf.utils.ui.file_drop_helper import extract_file_paths

logger = get_cached_logger(__name__)


class DragDropMixin:
    """Mixin providing drag-and-drop functionality for QTableView widgets.

    This mixin handles:
    - Custom drag operations with visual feedback
    - Drag lifecycle (start, feedback loop, end)
    - Integration with DragManager and DragVisualManager
    - Drop handling on metadata tree
    - Hover state restoration after drag
    - External file/folder drops into table

    Required attributes on parent class:
    - self._is_dragging: bool - Flag indicating active drag
    - self._drag_data: list[str] | None - List of file paths being dragged
    - self._drag_feedback_timer_id: int | None - Timer ID for feedback loop
    - self._drag_end_time: float - Timestamp of drag end
    - self._successful_metadata_drop: bool - Flag for successful metadata drop
    - self._preserve_selection_for_drag: bool - Flag to preserve selection
    - self._clicked_on_selected: bool - Flag for click on selected item
    - self._clicked_index: QModelIndex | None - Index of clicked item
    - self._legacy_selection_mode: bool - Flag for legacy mode
    - self.files_dropped: pyqtSignal - Signal emitted on file drop

    Required methods on parent class:
    - self.model() - Qt model getter
    - self.viewport() - Viewport getter
    - self.visualRect() - Visual rect getter
    - self.rect() - Widget rect getter
    - self.mapFromGlobal() - Map global pos to local
    - self.blockSignals() - Signal blocking
    - self._get_current_selection_safe() - Get current selection safely
    - self._get_current_selection() - Get current selection from SelectionStore
    - self._get_selection_store() - Get SelectionStore
    - self._force_cursor_cleanup() - Force cursor cleanup
    """

    def _ensure_drag_drop_mixin_attrs(self) -> None:
        """Ensure required attributes exist with default values.

        This provides defensive initialization to prevent AttributeError
        if mixin methods are called before parent class __init__ completes.
        """
        if not hasattr(self, "_is_dragging"):
            self._is_dragging = False
        if not hasattr(self, "_drag_data"):
            self._drag_data = None
        if not hasattr(self, "_drag_feedback_timer_id"):
            self._drag_feedback_timer_id = None
        if not hasattr(self, "_drag_end_time"):
            self._drag_end_time = 0.0
        if not hasattr(self, "_successful_metadata_drop"):
            self._successful_metadata_drop = False
        if not hasattr(self, "_preserve_selection_for_drag"):
            self._preserve_selection_for_drag = False
        if not hasattr(self, "_clicked_on_selected"):
            self._clicked_on_selected = False
        if not hasattr(self, "_clicked_index"):
            self._clicked_index = None
        if not hasattr(self, "_legacy_selection_mode"):
            self._legacy_selection_mode = True

    def _start_custom_drag(self):
        """Start custom drag operation with enhanced visual feedback."""
        self._ensure_drag_drop_mixin_attrs()
        if self._is_dragging:
            return

        # Clean up selection preservation flags since we're starting a drag
        self._preserve_selection_for_drag = False
        self._clicked_on_selected = False
        self._clicked_index = None

        # Get selected file data using safe method
        selected_rows = self._get_current_selection_safe()

        if not selected_rows:
            return

        # Performance optimization: For large selections, collect paths lazily
        rows = sorted(selected_rows)
        file_count = len(rows)

        # For small selections (<100), collect all paths immediately
        # For large selections, collect only first few for display + defer rest
        if file_count < 100:
            file_items = [self.model().files[r] for r in rows if 0 <= r < len(self.model().files)]
            file_paths = [f.full_path for f in file_items if f.full_path]
        else:
            # Large selection: collect only first 3 paths for preview
            preview_rows = rows[:3]
            preview_items = [
                self.model().files[r] for r in preview_rows if 0 <= r < len(self.model().files)
            ]
            file_paths = [f.full_path for f in preview_items if f.full_path]
            # Store row indices for lazy collection later if needed
            self._drag_pending_rows = rows

        if not file_paths:
            return

        # Activate drag cancel filter to preserve selection (especially for no-modifier drags)
        from oncutf.ui.widgets.file_tree_view import _drag_cancel_filter

        _drag_cancel_filter.activate()
        _drag_cancel_filter.preserve_selection(selected_rows)

        # Clear hover state before starting drag
        if hasattr(self, "hover_delegate"):
            old_row = self.hover_delegate.hovered_row
            self.hover_delegate.update_hover_row(-1)
            if old_row >= 0:
                left = self.model().index(old_row, 0)
                right = self.model().index(old_row, self.model().columnCount() - 1)
                row_rect = self.visualRect(left).united(self.visualRect(right))
                self.viewport().update(row_rect)

        # Set drag state
        self._is_dragging = True
        self._drag_data = file_paths

        # Stop any existing drag feedback timer
        if hasattr(self, "_drag_feedback_timer_id") and self._drag_feedback_timer_id:
            cancel_timer(self._drag_feedback_timer_id)

        # Notify DragManager
        drag_manager = DragManager.get_instance()
        drag_manager.start_drag("file_table")

        # Start enhanced visual feedback
        visual_manager = DragVisualManager.get_instance()

        # Determine drag type and info string based on selection
        # Use actual selection count, not just collected paths
        actual_count = file_count if hasattr(self, "_drag_pending_rows") else len(file_paths)

        if actual_count == 1:
            drag_type = visual_manager.get_drag_type_from_path(file_paths[0])
            # For single file, show just the filename
            import os

            source_info = os.path.basename(file_paths[0])
        else:
            drag_type = DragType.MULTIPLE
            # For multiple files, show count (using actual selection count)
            source_info = f"{actual_count} files"

        start_drag_visual(drag_type, source_info, "file_table")

        # Start drag feedback loop for real-time visual updates
        self._start_drag_feedback_loop()

    def _start_drag_feedback_loop(self):
        """Start repeated drag feedback updates using timer_manager with adaptive delay."""
        if self._is_dragging:
            self._update_drag_feedback()

            # Adaptive delay based on selection size for better performance
            # Large selections: slower updates (less CPU), small selections: faster updates (smoother)
            selected_count = (
                len(self._get_current_selection_safe())
                if hasattr(self, "_get_current_selection_safe")
                else 1
            )
            if selected_count > 500:
                delay = 200  # Very large: 200ms
            elif selected_count > 100:
                delay = 150  # Large: 150ms
            else:
                delay = 100  # Normal: 100ms

            # Schedule next update with adaptive delay
            self._drag_feedback_timer_id = schedule_ui_update(
                self._start_drag_feedback_loop, delay=delay
            )

    def _update_drag_feedback(self):
        """Update visual feedback based on current cursor position during drag."""
        if not self._is_dragging:
            return

        # Use common drag feedback logic
        should_continue = update_drag_feedback_for_widget(self, "file_table")

        # If cursor is outside application, end drag
        if not should_continue:
            self._end_custom_drag()

    def _end_custom_drag(self):
        """End custom drag operation."""
        if not self._is_dragging:
            return

        # Check if drag was cancelled (e.g., by ESC key press) BEFORE doing anything
        drag_manager = DragManager.get_instance()
        drag_was_cancelled = not drag_manager.is_drag_active()

        if drag_was_cancelled:
            logger.info(
                "[DragDropMixin] Drag was cancelled (ESC pressed), cleaning up without drop"
            )

        try:
            # Stop and cleanup drag feedback timer
            if hasattr(self, "_drag_feedback_timer_id") and self._drag_feedback_timer_id:
                cancel_timer(self._drag_feedback_timer_id)
                self._drag_feedback_timer_id = None

            # Force immediate cursor cleanup
            self._force_cursor_cleanup()

            # Deactivate drag cancel filter
            from oncutf.ui.widgets.file_tree_view import _drag_cancel_filter

            if _drag_cancel_filter.is_active():
                _drag_cancel_filter.deactivate()

            # Only attempt drop detection if drag was NOT cancelled
            if not drag_was_cancelled:
                # Get widget under cursor for drop detection
                cursor_pos = QCursor.pos()
                widget_under_cursor = QApplication.widgetAt(cursor_pos)

                dropped_successfully = False

                if widget_under_cursor:
                    # Walk up parent hierarchy to find drop targets
                    parent = widget_under_cursor
                    while parent and not dropped_successfully:
                        if parent.__class__.__name__ == "MetadataTreeView":
                            dropped_successfully = self._handle_drop_on_metadata_tree()
                            break
                        parent = parent.parent()
            else:
                # Drag was cancelled - clear drag data immediately
                self._drag_data = None

        finally:
            # Clean up drag state
            self._is_dragging = False
            self._drag_data = None

            # Record drag end time for selection protection
            import time

            self._drag_end_time = time.time() * 1000  # Store in milliseconds

            # Cleanup visual feedback
            end_drag_visual()

            # Notify DragManager
            drag_manager = DragManager.get_instance()
            drag_manager.end_drag("file_table")

            # Always restore hover after drag ends
            self._restore_hover_after_drag()

    def _restore_hover_after_drag(self):
        """Restore hover state after drag ends by sending a fake mouse move event."""
        if not hasattr(self, "hover_delegate"):
            return

        # Get current cursor position relative to this widget
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)

        # Only restore hover if cursor is still over this widget
        if self.rect().contains(local_pos):
            # Create and post a fake mouse move event
            fake_move_event = QMouseEvent(
                QEvent.MouseMove, local_pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier
            )
            QApplication.postEvent(self, fake_move_event)

    def _handle_drop_on_metadata_tree(self):
        """Handle drop on metadata tree - single entry point for FileTable->MetadataTree drops.

        Behavior:
        - No modifier: Fast metadata loading
        - Shift: Extended metadata loading
        - Pre-checks cache to avoid redundant loading
        - Single file: wait_cursor (immediate)
        - Multiple files: ProgressDialog with ESC cancel support
        """
        if not self._drag_data:
            logger.debug(
                "[DragDropMixin] No drag data available for metadata tree drop",
                extra={"dev_only": True},
            )
            return False

        # Get current selection - this is what the user sees and expects
        selected_rows = self._get_current_selection()

        if not selected_rows:
            logger.warning("[DragDropMixin] No valid selection found for metadata tree drop")
            return False

        # Get parent window for file items and metadata operations
        parent_window = self._get_parent_with_metadata_tree()
        if not parent_window:
            logger.warning("[DragDropMixin] Could not find parent window")
            return False

        # Convert to FileItem objects using unified selection method
        try:
            file_items = parent_window.get_selected_files_ordered()
            if not file_items:
                logger.warning("[DragDropMixin] No valid file items found for metadata tree drop")
                return False
        except (AttributeError, IndexError) as e:
            logger.error("[DragDropMixin] Error getting selected files: %s", e)
            return False

        # Get modifiers for metadata loading decision (Shift = extended)
        modifiers = QApplication.keyboardModifiers()
        use_extended = bool(modifiers & Qt.ShiftModifier)

        # Verify we have the required services
        if not hasattr(parent_window, "app_service"):
            logger.warning("[DragDropMixin] Could not find app_service on parent window")
            return False

        # Delegate to ApplicationService which handles:
        # - Cache pre-check (skip already-loaded files)
        # - Single file: wait_cursor
        # - Multiple files: ProgressDialog with ESC cancel
        # - Progressive updates
        try:
            parent_window.app_service.load_metadata_for_items(
                file_items, use_extended=use_extended, source="drag_drop"
            )

            # Set flag to indicate successful metadata drop
            self._successful_metadata_drop = True
            logger.info(
                "[DragDropMixin] Metadata load initiated: %d files (extended=%s)",
                len(file_items),
                use_extended,
            )

            # Schedule final status update
            def final_status_update():
                current_selection = self._get_current_selection()
                if current_selection:
                    selection_store = self._get_selection_store()
                    if selection_store and not self._legacy_selection_mode:
                        selection_store.selection_changed.emit(list(current_selection))

            schedule_ui_update(final_status_update, delay=100)
            return True

        except Exception as e:
            logger.error("[DragDropMixin] Error initiating metadata load: %s", e)
            return False

    def _get_parent_with_metadata_tree(self):
        """Find parent window that has metadata_tree_view attribute."""
        from oncutf.utils.filesystem.path_utils import find_parent_with_attribute

        return find_parent_with_attribute(self, "metadata_tree_view")

    # =====================================
    # Qt Drag & Drop Event Handlers
    # =====================================

    def dragEnterEvent(self, event):
        """Accept drag events with URLs or internal format."""
        if event.mimeData().hasUrls() or event.mimeData().hasFormat(
            "application/x-oncutf-internal"
        ):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)  # type: ignore

    def dragMoveEvent(self, event):
        """Accept drag move events with URLs or internal format."""
        if event.mimeData().hasUrls() or event.mimeData().hasFormat(
            "application/x-oncutf-internal"
        ):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)  # type: ignore

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle file/folder drops into the table."""
        mime_data = event.mimeData()

        # Ignore internal drags from this table
        if mime_data.hasFormat("application/x-oncutf-filetable"):
            return

        # Extract and process dropped paths
        modifiers = event.keyboardModifiers()
        dropped_paths = extract_file_paths(mime_data)

        if not dropped_paths:
            return

        # Filter out duplicates
        if self.model() and hasattr(self.model(), "files"):
            existing_paths = {f.full_path for f in self.model().files}
            new_paths = [p for p in dropped_paths if p not in existing_paths]
            if not new_paths:
                return
        else:
            new_paths = dropped_paths

        # Emit signal for processing
        self.files_dropped.emit(new_paths, modifiers)
        event.acceptProposedAction()
