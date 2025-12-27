"""Module: module_drag_drop_manager.py

Author: Michael Economou
Date: 2025-12-27

Manager for drag & drop operations on rename modules.
Extracted from RenameModuleWidget to separate UI concerns.
"""

from oncutf.core.pyqt_imports import QApplication, QCursor, Qt, QWidget
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ModuleDragDropManager:
    """Manages drag & drop state and operations for module reordering.

    Separated from UI widget to enable different UI implementations
    (current widget-based vs future node editor).
    """

    def __init__(self):
        """Initialize drag & drop manager."""
        self._dragged_widget: QWidget | None = None
        self._drag_start_position: tuple[int, int] | None = None
        self._is_dragging = False
        self._drag_threshold = 5  # Pixels before starting drag

    def start_drag(self, widget: QWidget, global_pos: tuple[int, int]) -> None:
        """Initiate drag tracking.

        Args:
            widget: Widget being dragged
            global_pos: Initial mouse position (x, y)
        """
        self._dragged_widget = widget
        self._drag_start_position = global_pos
        self._is_dragging = False
        logger.debug("[DragDropManager] Drag tracking started")

    def update_drag(self, global_pos: tuple[int, int]) -> bool:
        """Update drag state based on mouse movement.

        Args:
            global_pos: Current mouse position (x, y)

        Returns:
            True if drag started (crossed threshold)
        """
        if not self._drag_start_position:
            return False

        if self._is_dragging:
            return False

        # Calculate distance moved
        dx = global_pos[0] - self._drag_start_position[0]
        dy = global_pos[1] - self._drag_start_position[1]
        distance = (dx * dx + dy * dy) ** 0.5

        # Start dragging if moved beyond threshold
        if distance > self._drag_threshold:
            self._is_dragging = True
            logger.debug("[DragDropManager] Drag started (moved %.1f px)", distance)
            return True

        return False

    def end_drag(self) -> QWidget | None:
        """End drag operation and return dragged widget.

        Returns:
            Widget that was being dragged, or None
        """
        widget = self._dragged_widget
        self._dragged_widget = None
        self._drag_start_position = None
        self._is_dragging = False

        if widget:
            logger.debug("[DragDropManager] Drag ended")

        return widget

    def cancel_drag(self) -> None:
        """Cancel current drag operation."""
        if self._is_dragging or self._dragged_widget:
            logger.debug("[DragDropManager] Drag cancelled")
        self.end_drag()

    @property
    def is_dragging(self) -> bool:
        """Check if currently dragging.

        Returns:
            True if drag in progress
        """
        return self._is_dragging

    @property
    def dragged_widget(self) -> QWidget | None:
        """Get widget being dragged.

        Returns:
            Dragged widget or None
        """
        return self._dragged_widget

    @staticmethod
    def set_drag_cursor() -> None:
        """Set cursor to indicate dragging."""
        QApplication.setOverrideCursor(QCursor(Qt.ClosedHandCursor))

    @staticmethod
    def set_hover_cursor() -> None:
        """Set cursor to indicate drag handle hover."""
        QApplication.setOverrideCursor(QCursor(Qt.OpenHandCursor))

    @staticmethod
    def restore_cursor() -> None:
        """Restore normal cursor."""
        QApplication.restoreOverrideCursor()
