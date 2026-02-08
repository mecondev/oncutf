"""Module: drag_handler.py.

Author: Michael Economou
Date: 2026-01-02

Drag and drop handler for file tree view.

Implements custom single-item drag system with visual feedback,
drop zone validation, and modifier key support for different
drag behaviors (replace/merge, shallow/recursive).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QCursor, QMouseEvent
from PyQt5.QtWidgets import QApplication

from oncutf.config import ALLOWED_EXTENSIONS
from oncutf.core.modifier_handler import decode_modifiers_to_flags
from oncutf.ui.adapters.qt_keyboard import qt_modifiers_to_domain
from oncutf.ui.drag.drag_manager import DragManager
from oncutf.ui.drag.drag_visual_manager import (
    DragVisualManager,
    end_drag_visual,
    start_drag_visual,
    update_drag_feedback_for_widget,
)
from oncutf.ui.helpers.drag_zone_validator import DragZoneValidator
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.file_tree.view import FileTreeView

logger = get_cached_logger(__name__)


class DragHandler:
    """Handles drag and drop operations for the file tree view.

    Implements a custom drag system that:
    - Uses manual drag detection instead of Qt's built-in system
    - Provides real-time visual feedback during drag
    - Supports 4 modifier combinations for different behaviors
    - Validates drop targets (only FileTableView allowed)
    """

    def __init__(self, view: FileTreeView) -> None:
        """Initialize drag handler.

        Args:
            view: The file tree view widget to handle drag for

        """
        self._view = view
        self._is_dragging = False
        self._drag_path: str | None = None
        self._drag_start_pos = None
        self._drag_feedback_timer_id = None
        self._last_recursive_state: bool | None = None
        self._has_subfolders: bool | None = None

        # Original state to restore after drag
        self._original_mouse_tracking: bool = False
        self._original_hover_enabled: bool = False
        self._original_viewport_hover: bool = False
        self._original_viewport_tracking: bool = False

    @property
    def is_dragging(self) -> bool:
        """Check if drag operation is in progress."""
        return self._is_dragging

    @property
    def drag_start_pos(self):
        """Get the drag start position."""
        return self._drag_start_pos

    @drag_start_pos.setter
    def drag_start_pos(self, value) -> None:
        """Set the drag start position."""
        self._drag_start_pos = value

    @property
    def drag_path(self) -> str | None:
        """Get the path being dragged."""
        return self._drag_path

    def handle_mouse_press(self, event) -> None:
        """Handle mouse press event for drag detection.

        Args:
            event: Mouse press event

        """
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self._is_dragging = False
            self._drag_path = None

    def handle_mouse_move(self, event) -> bool:
        """Handle mouse move event for drag start and feedback.

        Args:
            event: Mouse move event

        Returns:
            True if event was handled (don't call super), False otherwise

        """
        if self._is_dragging:
            self._handle_drag_move(event)
            return True

        if not (event.buttons() & Qt.LeftButton) or not self._drag_start_pos:
            if self._drag_start_pos:
                self._drag_start_pos = None
            return False

        # Check drag distance threshold
        if (
            event.pos() - self._drag_start_pos
        ).manhattanLength() < QApplication.startDragDistance():
            return False

        logger.debug("[DragHandler] About to start custom drag", extra={"dev_only": True})
        self._start_custom_drag()
        return True

    def _handle_drag_move(self, event) -> None:
        """Handle mouse move during active drag.

        Args:
            event: Mouse move event

        """
        if not self._drag_start_pos:
            self._drag_start_pos = event.pos()
        else:
            cursor_pos = QCursor.pos()
            widget_under_cursor = QApplication.widgetAt(cursor_pos)

            current_widget = widget_under_cursor
            still_over_source = False

            while current_widget:
                if current_widget is self._view:
                    still_over_source = True
                    break
                current_widget = current_widget.parent()

            if not still_over_source:
                self._drag_start_pos = event.pos()
                self._update_drag_feedback()

    def handle_mouse_release(self, event) -> bool:
        """Handle mouse release event to end drag.

        Args:
            event: Mouse release event

        Returns:
            True if we were dragging (cleanup needed), False otherwise

        """
        was_dragging = self._is_dragging
        self._end_custom_drag()

        if was_dragging:
            cursor_count = 0
            while QApplication.overrideCursor() and cursor_count < 5:
                QApplication.restoreOverrideCursor()
                cursor_count += 1

            if cursor_count > 0:
                logger.debug(
                    "[DragHandler] Cleaned %d stuck cursors after drag",
                    cursor_count,
                    extra={"dev_only": True},
                )

            fake_move_event = QMouseEvent(
                QEvent.MouseMove, event.pos(), Qt.NoButton, Qt.NoButton, Qt.NoModifier
            )
            QApplication.postEvent(self._view, fake_move_event)

        return was_dragging

    def _start_custom_drag(self) -> None:
        """Start custom drag operation with enhanced visual feedback."""
        if not self._drag_start_pos:
            return

        index = self._view.indexAt(self._drag_start_pos)
        if not index.isValid():
            return

        model = self._view.model()
        if not model or not hasattr(model, "filePath"):
            return

        clicked_path = model.filePath(index)
        if not clicked_path or not self._is_valid_drag_target(clicked_path):
            return

        # Block drag on mount points and root drives
        from oncutf.utils.filesystem.folder_counter import is_mount_point_or_root

        if Path(clicked_path).is_dir() and is_mount_point_or_root(clicked_path):
            logger.warning(
                "[DragHandler] Blocked drag on mount point/root: %s",
                clicked_path,
                extra={"dev_only": True},
            )
            return

        self._drag_path = clicked_path
        self._is_dragging = True
        self._last_recursive_state = None
        self._has_subfolders = None

        # Disable mouse tracking and hover during drag
        self._original_mouse_tracking = self._view.hasMouseTracking()
        self._view.setMouseTracking(False)

        self._original_hover_enabled = self._view.testAttribute(Qt.WA_Hover)
        self._view.setAttribute(Qt.WA_Hover, False)

        self._original_viewport_hover = self._view.viewport().testAttribute(Qt.WA_Hover)
        self._view.viewport().setAttribute(Qt.WA_Hover, False)

        self._original_viewport_tracking = self._view.viewport().hasMouseTracking()
        self._view.viewport().setMouseTracking(False)

        # Notify DragManager
        drag_manager = DragManager.get_instance()
        drag_manager.start_drag("file_tree")

        # Determine initial display info
        is_folder = Path(clicked_path).is_dir()
        initial_info = Path(clicked_path).name if is_folder else "1 file"

        # Start enhanced visual feedback
        visual_manager = DragVisualManager.get_instance()
        drag_type = visual_manager.get_drag_type_from_path(clicked_path)
        if not is_folder:
            visual_manager.update_recursive_support(False)
        start_drag_visual(drag_type, initial_info, "file_tree")

        # For folders, schedule async count update
        if is_folder:
            from oncutf.utils.shared.timer_manager import schedule_ui_update

            schedule_ui_update(lambda: self._update_folder_count(clicked_path), delay=10)

        # Set initial drag widget for zone validation
        DragZoneValidator.set_initial_drag_widget("file_tree", "FileTreeView")

        # Start drag feedback timer
        if self._drag_feedback_timer_id:
            from oncutf.utils.shared.timer_manager import cancel_timer

            cancel_timer(self._drag_feedback_timer_id)

        self._start_drag_feedback_loop()

        logger.debug(
            "[DragHandler] Custom drag started: %s",
            clicked_path,
            extra={"dev_only": True},
        )

    def _start_drag_feedback_loop(self) -> None:
        """Start repeated drag feedback updates using timer_manager."""
        from oncutf.utils.shared.timer_manager import schedule_ui_update

        if self._is_dragging:
            self._update_drag_feedback()
            self._drag_feedback_timer_id = schedule_ui_update(
                self._start_drag_feedback_loop, delay=50
            )

    def _update_drag_feedback(self) -> None:
        """Update visual feedback based on current cursor position during drag."""
        if not self._is_dragging:
            return

        if self._drag_path and Path(self._drag_path).is_dir():
            modifiers = QApplication.keyboardModifiers()
            is_recursive = bool(modifiers & Qt.ControlModifier)
            if self._has_subfolders is None or (
                self._has_subfolders and self._last_recursive_state != is_recursive
            ):
                self._update_folder_count(self._drag_path)

        should_continue = update_drag_feedback_for_widget(self._view, "file_tree")

        if not should_continue:
            self._end_custom_drag()

    def _end_custom_drag(self) -> None:
        """End custom drag operation with enhanced visual feedback."""
        if not self._is_dragging:
            return

        drag_manager = DragManager.get_instance()
        if not drag_manager.is_drag_active():
            logger.debug(
                "[DragHandler] Drag was cancelled, skipping drop",
                extra={"dev_only": True},
            )
            self._cleanup_drag_state()
            return

        # Check if we dropped on a valid target
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        logger.debug(
            "[DragHandler] Widget under cursor: %s",
            widget_under_cursor,
            extra={"dev_only": True},
        )

        visual_manager = DragVisualManager.get_instance()
        valid_drop = False
        target_widget = None

        if widget_under_cursor:
            parent = widget_under_cursor
            while parent:
                logger.debug(
                    "[DragHandler] Checking parent: %s",
                    parent.__class__.__name__,
                    extra={"dev_only": True},
                )

                if visual_manager.is_valid_drop_target(parent, "file_tree"):
                    logger.debug(
                        "[DragHandler] Valid drop target found: %s",
                        parent.__class__.__name__,
                        extra={"dev_only": True},
                    )
                    target_widget = parent
                    valid_drop = True
                    break

                if (
                    hasattr(parent, "parent")
                    and parent.parent()
                    and visual_manager.is_valid_drop_target(parent.parent(), "file_tree")
                ):
                    logger.debug(
                        "[DragHandler] Valid drop target found via viewport: %s",
                        parent.parent().__class__.__name__,
                        extra={"dev_only": True},
                    )
                    target_widget = parent.parent()
                    valid_drop = True
                    break

                if parent.__class__.__name__ in ["FileTreeView", "MetadataTreeView"]:
                    logger.debug(
                        "[DragHandler] Rejecting drop on %s (policy violation)",
                        parent.__class__.__name__,
                        extra={"dev_only": True},
                    )
                    break

                parent = parent.parent()

        if valid_drop and target_widget:
            self._handle_drop_on_target(target_widget)
        else:
            logger.debug("[DragHandler] Drop on invalid target", extra={"dev_only": True})

        self._cleanup_drag_state()

        # Clear initial drag widget tracking
        DragZoneValidator.clear_initial_drag_widget("file_tree")

        # Notify DragManager
        drag_manager.end_drag("file_tree")

        # Restore hover state
        self._restore_hover_after_drag()

        # Restore folder selection if it was lost during drag
        if self._drag_path and Path(self._drag_path).is_dir():
            current_selection = self._view.get_selected_path()
            if current_selection != self._drag_path:
                self._view.select_path(self._drag_path)
                logger.debug(
                    "[DragHandler] Restored folder selection: %s",
                    self._drag_path,
                    extra={"dev_only": True},
                )

        logger.debug(
            "[DragHandler] Custom drag ended: %s (valid_drop: %s)",
            self._drag_path,
            valid_drop,
            extra={"dev_only": True},
        )

    def _cleanup_drag_state(self) -> None:
        """Clean up drag state after drag ends."""
        self._is_dragging = False
        self._drag_start_pos = None

        # Stop drag feedback timer
        if self._drag_feedback_timer_id:
            from oncutf.utils.shared.timer_manager import cancel_timer

            cancel_timer(self._drag_feedback_timer_id)
            self._drag_feedback_timer_id = None

        # Restore mouse tracking
        self._view.setMouseTracking(self._original_mouse_tracking)
        self._view.setAttribute(Qt.WA_Hover, self._original_hover_enabled)
        self._view.viewport().setAttribute(Qt.WA_Hover, self._original_viewport_hover)
        self._view.viewport().setMouseTracking(self._original_viewport_tracking)

        # End visual feedback
        end_drag_visual()

    def _restore_hover_after_drag(self) -> None:
        """Restore hover state after drag ends by sending a fake mouse move event."""
        global_pos = QCursor.pos()
        local_pos = self._view.mapFromGlobal(global_pos)

        if self._view.rect().contains(local_pos):
            fake_move_event = QMouseEvent(
                QEvent.MouseMove, local_pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier
            )
            QApplication.postEvent(self._view, fake_move_event)

    def _update_folder_count(self, folder_path: str) -> None:
        """Update drag cursor with folder contents count.

        Args:
            folder_path: Path of the folder being dragged

        """
        if not self._is_dragging or self._drag_path != folder_path:
            return

        from oncutf.ui.drag.drag_visual_manager import update_source_info
        from oncutf.utils.filesystem.folder_counter import count_folder_contents

        modifiers = QApplication.keyboardModifiers()
        is_recursive = bool(modifiers & Qt.ControlModifier)

        count = count_folder_contents(
            folder_path,
            recursive=is_recursive,
            timeout_ms=100.0,
        )

        self._has_subfolders = count.folders > 0
        self._last_recursive_state = is_recursive

        visual_manager = DragVisualManager.get_instance()
        visual_manager.update_recursive_support(count.folders > 0)

        display_text = count.format_display(recursive=is_recursive)
        update_source_info(display_text)

        logger.debug(
            "[DragHandler] Updated drag count: %s (recursive=%s, timeout=%s, %.1fms)",
            display_text,
            is_recursive,
            count.timed_out,
            count.elapsed_ms,
            extra={"dev_only": True},
        )

    def _handle_drop_on_target(self, target_widget) -> None:
        """Handle drop on target widget (FileTableView or ThumbnailViewportWidget).

        Args:
            target_widget: The target widget that received the drop

        """
        if not self._drag_path:
            return

        qt_mods = QApplication.keyboardModifiers()
        target_class = target_widget.__class__.__name__

        # For FileTableView, use the original file tree behavior
        if target_class == "FileTableView":
            self._view.item_dropped.emit(self._drag_path, qt_mods)
            logger.info(
                "[DragHandler] Dropped on FileTableView: %s",
                self._drag_path,
                extra={"dev_only": True},
            )
        # For ThumbnailViewportWidget, emit files_dropped signal
        elif target_class == "ThumbnailViewportWidget":
            # Emit files_dropped signal like normal drop sources do
            target_widget.files_dropped.emit([self._drag_path], qt_mods)
            logger.info(
                "[DragHandler] Dropped on ThumbnailViewportWidget: %s",
                self._drag_path,
                extra={"dev_only": True},
            )
        else:
            logger.warning(
                "[DragHandler] Unknown drop target: %s",
                target_class,
                extra={"dev_only": True},
            )

        domain_mods = qt_modifiers_to_domain(qt_mods)
        _, _, action = decode_modifiers_to_flags(domain_mods)
        logger.info(
            "[DragHandler] Drop action: %s",
            action,
            extra={"dev_only": True},
        )

    def _handle_drop_on_table(self) -> None:
        """Handle drop on file table with modifier logic.

        Deprecated: Use _handle_drop_on_target instead.
        """
        if not self._drag_path:
            return

        qt_mods = QApplication.keyboardModifiers()
        self._view.item_dropped.emit(self._drag_path, qt_mods)

        domain_mods = qt_modifiers_to_domain(qt_mods)
        _, _, action = decode_modifiers_to_flags(domain_mods)

        logger.info(
            "[DragHandler] Dropped: %s (%s)",
            self._drag_path,
            action,
            extra={"dev_only": True},
        )

    def _is_valid_drag_target(self, path: str) -> bool:
        """Check if path is valid for dragging.

        Args:
            path: File or folder path to check

        Returns:
            True if path can be dragged

        """
        if Path(path).is_dir():
            from oncutf.utils.filesystem.folder_counter import is_mount_point_or_root

            if is_mount_point_or_root(path):
                logger.warning(
                    "[DragHandler] Blocked drag of mount point/root: %s",
                    path,
                    extra={"dev_only": True},
                )
                return False
            return True

        ext = Path(path).suffix
        if ext.startswith("."):
            ext = ext[1:].lower()

        if ext not in ALLOWED_EXTENSIONS:
            logger.debug(
                "[DragHandler] Skipping drag for non-allowed extension: %s",
                ext,
                extra={"dev_only": True},
            )
            return False

        return True
