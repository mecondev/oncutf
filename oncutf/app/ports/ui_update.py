"""UI update port for visual feedback updates.

This port decouples core operations from UI update implementations.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import Any, Protocol


class UIUpdatePort(Protocol):
    """Protocol for updating UI elements from core operations."""

    def update_file_icon(
        self,
        file_list_view: Any,
        file_model: Any,
        file_path: str,
    ) -> None:
        """Update the info icon in the file table for a specific file.

        Args:
            file_list_view: The file table view widget
            file_model: The file table model
            file_path: Full path of the file to update icon for

        """
        ...
