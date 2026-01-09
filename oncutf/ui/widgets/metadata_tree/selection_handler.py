"""Handler for metadata tree selection management.

This module handles selection-related operations for the metadata tree view,
including parent selection sync, selection change handling, and metadata display logic.

Author: Michael Economou
Date: 2025-12-23
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

logger = get_cached_logger(__name__)


class MetadataTreeSelectionHandler:
    """Handles selection management for metadata tree view."""

    def __init__(self, view: MetadataTreeView):
        """Initialize the selection handler.

        Args:
            view: The metadata tree view instance

        """
        self._view = view

    def get_current_selection_count(self) -> int:
        """Get current selection count from parent file table.

        Returns:
            Number of currently selected files

        """
        parent_window = self._view._get_parent_with_file_table()
        if not parent_window:
            return 0

        # Try SelectionStore first (most reliable)
        try:
            from oncutf.core.application_context import get_app_context

            context = get_app_context()
            if context and hasattr(context, "selection_store"):
                return len(context.selection_store.get_selected_rows())
        except Exception:
            pass

        # Fallback: check file_table_view selection
        if hasattr(parent_window, "file_table_view"):
            selection_model = parent_window.file_table_view.selectionModel()
            if selection_model:
                return len(selection_model.selectedRows())

        return 0

    def get_current_selection(self):
        """Get current selection via parent traversal."""
        parent_window = self._view._get_parent_with_file_table()

        if not parent_window:
            return []

        # Try multiple methods to get selection
        selected_files = []

        # Method 1: Use selection model directly
        try:
            selection = parent_window.file_table_view.selectionModel()
            if selection and selection.hasSelection():
                selected_rows = selection.selectedRows()
                if selected_rows and hasattr(parent_window, "file_model"):
                    file_model = parent_window.file_model
                    for index in selected_rows:
                        row = index.row()
                        if 0 <= row < len(file_model.files):
                            selected_files.append(file_model.files[row])
        except Exception as e:
            logger.debug("[MetadataTree] Method 1 failed: %s", e, extra={"dev_only": True})

        # Method 2: Use file table view's internal selection method
        if not selected_files:
            try:
                if hasattr(parent_window.file_table_view, "_selection_behavior"):
                    selected_rows = parent_window.file_table_view._selection_behavior.get_current_selection()
                    if selected_rows and hasattr(parent_window, "file_model"):
                        file_model = parent_window.file_model
                        for row in selected_rows:
                            if 0 <= row < len(file_model.files):
                                selected_files.append(file_model.files[row])
            except Exception as e:
                logger.debug("[MetadataTree] Method 2 failed: %s", e, extra={"dev_only": True})

        return selected_files

    def update_from_parent_selection(self) -> None:
        """Update metadata display based on parent selection."""
        try:
            # Get current selection from parent
            selection = self.get_current_selection()
            if not selection:
                # Try alternative method to get selection if first method failed
                parent_window = self._view._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "file_table_view"):
                    file_table_view = parent_window.file_table_view
                    if hasattr(file_table_view, "_selection_behavior"):
                        selected_rows = file_table_view._selection_behavior.get_current_selection()
                        if selected_rows and hasattr(parent_window, "file_model"):
                            file_model = parent_window.file_model
                            selection = [
                                file_model.files[row]
                                for row in selected_rows
                                if 0 <= row < len(file_model.files)
                            ]

                if not selection:
                    self._view.show_empty_state("No file selected")
                    return

            # Handle single file selection
            if len(selection) == 1:
                file_item = selection[0]
                metadata = self._view._cache_behavior.try_lazy_metadata_loading(file_item, "parent_selection")
                if metadata:
                    self._view.display_metadata(metadata, "parent_selection")
                    logger.debug(
                        "[MetadataTree] Updated from parent selection: %s",
                        file_item.filename,
                        extra={"dev_only": True},
                    )
                else:
                    self._view.show_empty_state("No metadata available")
            else:
                # Multiple files selected
                self._view.show_empty_state(f"{len(selection)} files selected")
                logger.debug(
                    "[MetadataTree] Multiple files selected: %d",
                    len(selection),
                    extra={"dev_only": True},
                )

        except Exception as e:
            logger.exception("[MetadataTree] Error updating from parent selection: %s", e)
            self._view.show_empty_state("Error loading metadata")

    def refresh_metadata_from_selection(self) -> None:
        """Convenience method that triggers metadata update from parent selection.
        Can be called from parent window when selection changes.
        """
        logger.debug("[MetadataTree] Refreshing metadata from selection", extra={"dev_only": True})
        self.update_from_parent_selection()

    def handle_selection_change(self) -> None:
        """Handle selection changes from the parent file table.
        This is a convenience method that can be connected to selection signals.
        """
        self.refresh_metadata_from_selection()

    def handle_invert_selection(self, metadata: dict[str, Any] | None) -> None:
        """Handle metadata display after selection inversion.

        Args:
            metadata: The metadata to display, or None to clear

        """
        if isinstance(metadata, dict) and metadata:
            self._view.display_metadata(metadata, context="invert_selection")
        else:
            self._view.clear_view()

        # Update header visibility after selection inversion
        self._view._update_header_visibility()

    def should_display_metadata_for_selection(self, selected_files_count: int) -> bool:
        """Central logic to determine if metadata should be displayed based on selection count.

        Args:
            selected_files_count: Number of currently selected files

        Returns:
            bool: True if metadata should be displayed, False if empty state should be shown

        """
        # Only display metadata for single file selection
        return selected_files_count == 1

    def smart_display_metadata_or_empty_state(
        self, metadata: dict[str, Any] | None, selected_count: int, context: str = ""
    ) -> None:
        """Smart display logic for metadata or empty state."""
        try:
            logger.debug(
                "[MetadataTree] smart_display called: metadata=%s, count=%d, ctx=%s",
                bool(metadata),
                selected_count,
                context,
                extra={"dev_only": True},
            )

            if metadata and self.should_display_metadata_for_selection(selected_count):
                logger.debug(
                    "[MetadataTree] Displaying metadata for %d selected file(s)",
                    selected_count,
                    extra={"dev_only": True},
                )
                self._view.display_metadata(metadata, context)
                logger.debug(
                    "[MetadataTree] Smart display: showing metadata (context: %s)",
                    context,
                    extra={"dev_only": True},
                )
            else:
                if selected_count == 0:
                    self._view.show_empty_state("No file selected")
                elif selected_count > 1:
                    self._view.show_empty_state(f"{selected_count} files selected")
                else:
                    self._view.show_empty_state("No metadata available")

                logger.debug(
                    "[MetadataTree] Smart display: showing empty state (selected: %d)",
                    selected_count,
                    extra={"dev_only": True},
                )

        except Exception as e:
            logger.exception("[MetadataTree] Error in smart display: %s", e)
            self._view.show_empty_state("Error loading metadata")

        # Update header visibility after smart display
        self._view._update_header_visibility()

    def get_modified_metadata(self) -> dict[str, str]:
        """Collect all modified metadata items for the current file.

        Returns:
            Dictionary of modified metadata in format {"EXIF/Rotation": "90"}

        """
        # Get staging manager
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return {}

        # Get current file
        selected_files = self.get_current_selection()
        if not selected_files or len(selected_files) != 1:
            return {}

        file_path = selected_files[0].full_path
        return staging_manager.get_staged_changes(file_path)
