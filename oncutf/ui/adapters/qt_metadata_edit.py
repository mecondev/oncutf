"""Qt adapter for MetadataEditPort - shows metadata editing dialog.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import Any


class QtMetadataEditAdapter:
    """Qt implementation of MetadataEditPort using MetadataEditDialog."""

    @staticmethod
    def edit_metadata_field(
        parent: Any,
        selected_files: list[str],
        metadata_cache: dict[str, dict[str, Any]],
        field_name: str,
        current_value: str,
    ) -> tuple[bool, str, list[str]]:
        """Show metadata field editing dialog.

        Args:
            parent: Parent window for the dialog
            selected_files: List of selected file paths
            metadata_cache: Current metadata cache
            field_name: Name of the metadata field to edit
            current_value: Current value of the field

        Returns:
            Tuple of (success, new_value, files_to_modify)

        """
        from oncutf.ui.dialogs.metadata_edit_dialog import MetadataEditDialog

        return MetadataEditDialog.edit_metadata_field(
            parent=parent,
            selected_files=selected_files,
            metadata_cache=metadata_cache,
            field_name=field_name,
            current_value=current_value,
        )
