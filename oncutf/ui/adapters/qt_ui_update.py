"""Qt adapter for UIUpdatePort - updates UI elements.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import Any


class QtUIUpdateAdapter:
    """Qt implementation of UIUpdatePort using view_helpers."""

    @staticmethod
    def update_file_icon(
        file_table_view: Any,
        file_model: Any,
        file_path: str,
    ) -> None:
        """Update the info icon in the file table.

        Args:
            file_table_view: The file table view widget
            file_model: The file table model
            file_path: Full path of the file to update icon for

        """
        from oncutf.ui.widgets.view_helpers import update_info_icon

        update_info_icon(file_table_view, file_model, file_path)
