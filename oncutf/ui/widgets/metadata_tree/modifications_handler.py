"""Handler for metadata tree modifications management.

This module handles modification tracking and management for the metadata tree view,
including staging, clearing, and checking for modified metadata.

Author: Michael Economou
Date: 2025-12-24
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.utils.filesystem.path_utils import paths_equal
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

logger = get_cached_logger(__name__)


class MetadataTreeModificationsHandler:
    """Handles modification tracking and management for metadata tree view."""

    def __init__(self, view: MetadataTreeView):
        """Initialize the modifications handler.

        Args:
            view: The metadata tree view instance

        """
        self._view = view

    def get_all_modified_metadata_for_files(self) -> dict[str, dict[str, str]]:
        """Collect all modified metadata for all files that have modifications.

        Returns:
            Dictionary mapping file paths to their modified metadata

        """
        # Get staging manager
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return {}

        return staging_manager.get_all_staged_changes()

    def clear_modifications(self) -> None:
        """Clear all modified metadata items for the current file.
        """
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        if staging_manager and self._view._current_file_path:
            staging_manager.clear_staged_changes(self._view._current_file_path)

        # Update the information label with current display data
        if hasattr(self._view, "_current_display_data") and self._view._current_display_data:
            self._view._update_information_label(self._view._current_display_data)

        self._view._update_file_icon_status()
        self._view.viewport().update()

    def clear_modifications_for_file(self, file_path: str) -> None:
        """Clear modifications for a specific file.

        Args:
            file_path: Full path of the file to clear modifications for

        """
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        if staging_manager:
            staging_manager.clear_staged_changes(file_path)

        # If this is the current file, also clear current modifications and update UI
        if paths_equal(file_path, self._view._current_file_path):
            # Refresh the view to remove italic style
            if hasattr(self._view, "display_metadata"):
                # Get current selection to refresh
                selected_files = self._view._get_current_selection()
                if selected_files and len(selected_files) == 1:
                    file_item = selected_files[0]
                    from oncutf.utils.filesystem.file_status_helpers import (
                        get_metadata_cache_entry,
                    )

                    metadata_entry = get_metadata_cache_entry(file_item.full_path)
                    if metadata_entry and hasattr(metadata_entry, "data"):
                        display_data = dict(metadata_entry.data)
                        display_data["FileName"] = file_item.filename
                        self._view.display_metadata(display_data, context="after_save")
            self._view._update_file_icon_status()
            self._view.viewport().update()

    def has_modifications_for_selected_files(self) -> bool:
        """Check if any of the currently selected files have modifications.

        Returns:
            bool: True if any selected file has modifications

        """
        # Get staging manager
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return False

        # Get selected files
        selected_files = self._view._get_current_selection()
        if not selected_files:
            return False

        # Check if any selected file has modifications
        for file_item in selected_files:
            if staging_manager.has_staged_changes(file_item.full_path):
                return True

        return False

    def has_any_modifications(self) -> bool:
        """Check if there are any modifications in any file.

        Returns:
            bool: True if any file has modifications

        """
        # Get staging manager
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return False

        return staging_manager.has_any_staged_changes()
