"""Qt adapter for DragStatePort - manages drag-and-drop state.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations


class QtDragStateAdapter:
    """Qt implementation of DragStatePort for drag state management."""

    @staticmethod
    def is_dragging() -> bool:
        """Check if a drag operation is currently active."""
        from oncutf.ui.drag.drag_manager import is_dragging

        return is_dragging()

    @staticmethod
    def force_cleanup_drag() -> None:
        """Force cleanup of any active drag state."""
        from oncutf.ui.drag.drag_manager import force_cleanup_drag

        force_cleanup_drag()

    @staticmethod
    def end_drag_visual() -> None:
        """Stop any drag visual feedback."""
        from oncutf.ui.drag.drag_visual_manager import end_drag_visual

        end_drag_visual()

    @staticmethod
    def clear_drag_state(source: str) -> None:
        """Clear drag state for a specific source."""
        from oncutf.app.services.drag_state import clear_drag_state

        clear_drag_state(source)
