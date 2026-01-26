"""Metadata editing port for user-driven metadata field editing.

This port decouples core metadata operations from UI dialog implementations.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import Any, Protocol


class MetadataEditPort(Protocol):
    """Protocol for editing metadata fields with user interaction."""

    def edit_metadata_field(
        self,
        parent: Any,
        selected_files: list[str],
        metadata_cache: dict[str, dict[str, Any]],
        field_name: str,
        current_value: str,
    ) -> tuple[bool, str, list[str]]:
        """Show metadata field editing dialog and get user input.

        Args:
            parent: Parent window for the dialog
            selected_files: List of selected file paths
            metadata_cache: Current metadata cache
            field_name: Name of the metadata field to edit
            current_value: Current value of the field (for single file)

        Returns:
            Tuple of (success, new_value, files_to_modify) where:
                - success: Whether user confirmed the edit
                - new_value: New value for the metadata field
                - files_to_modify: List of files to apply changes to

        """
        ...
