"""Protocol for drag state management operations.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import Protocol


class DragStatePort(Protocol):
    """Port for managing drag-and-drop state operations.

    Decouples core business logic from UI drag state management.
    """

    def is_dragging(self) -> bool:
        """Check if a drag operation is currently active.

        Returns:
            True if drag is in progress, False otherwise

        """
        ...

    def force_cleanup_drag(self) -> None:
        """Force cleanup of any active drag state.

        Ensures drag state is cleared even if drag wasn't properly terminated.
        """
        ...

    def end_drag_visual(self) -> None:
        """Stop any drag visual feedback (drop zones, highlights, etc.).

        Cleans up UI visual indicators associated with drag operations.
        """
        ...

    def clear_drag_state(self, source: str) -> None:
        """Clear drag state for a specific source.

        Args:
            source: Source identifier (e.g., "file_tree", "file_table")

        """
        ...
