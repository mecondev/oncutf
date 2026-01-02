"""UI state handler for MetadataTreeView.

This module handles all UI state operations for the metadata tree view,
including placeholder display, information label updates, and cleanup.

Author: Michael Economou
Date: 2026-01-02
"""

import traceback
from typing import TYPE_CHECKING, Any

from oncutf.core.pyqt_imports import QStandardItemModel
from oncutf.utils.filesystem.path_normalizer import normalize_path
from oncutf.utils.filesystem.path_utils import paths_equal
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

logger = get_cached_logger(__name__)


class TreeUiStateHandler:
    """Handles UI state operations for MetadataTreeView.

    This class manages:
    - Placeholder display and empty states
    - Information label updates
    - Display orchestration
    - Cleanup operations
    """

    def __init__(self, view: "MetadataTreeView") -> None:
        """Initialize the UI state handler.

        Args:
            view: The MetadataTreeView instance
        """
        self.view = view

    def display_placeholder(self, message: str = "No file selected") -> None:
        """Shows empty state using unified placeholder helper.

        No longer creates text model - uses only the placeholder helper.
        """
        # Create empty model to trigger placeholder mode
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["", ""])
        self.view._placeholder_model = model
        self.view._current_tree_model = None

        # Use proxy model for consistency (unless disabled via config)
        parent_window = self.view._get_parent_with_file_table()
        use_proxy = (
            self.view._use_proxy
            and parent_window
            and hasattr(parent_window, "metadata_proxy_model")
        )

        if use_proxy:
            logger.debug(
                "[TreeUiStateHandler] Setting empty placeholder source model on metadata_proxy_model",
                extra={"dev_only": True},
            )
            logger.debug(
                "[TreeUiStateHandler] setSourceModel (placeholder) stack:\n%s",
                "".join(traceback.format_stack(limit=8)),
                extra={"dev_only": True},
            )
            parent_window.metadata_proxy_model.setSourceModel(model)
            logger.debug(
                "[TreeUiStateHandler] Calling setModel(self, metadata_proxy_model) for placeholder",
                extra={"dev_only": True},
            )
            self.view.setModel(parent_window.metadata_proxy_model)
        else:
            logger.debug(
                "[TreeUiStateHandler] Proxy disabled - setting placeholder model directly",
                extra={"dev_only": True},
            )
            self.view.setModel(None)
            self.view.setModel(model)

        self.view._current_tree_model = self.view._placeholder_model

        # Update header visibility for placeholder mode
        self.view._update_header_visibility()

        # Disable search field when showing empty state
        self.view._update_search_field_state(False)

        # Reset information label
        if parent_window and hasattr(parent_window, "information_label"):
            parent_window.information_label.setText("Information")
            parent_window.information_label.setStyleSheet("")

    def clear_tree(self) -> None:
        """Clears the metadata tree view and shows a placeholder message.

        Does not clear scroll position memory when just showing placeholder.
        """
        self.display_placeholder("No file selected")
        # Update header visibility for placeholder mode
        self.view._update_header_visibility()
        # Disable search field when clearing view
        self.view._update_search_field_state(False)

    def display_metadata(self, metadata: dict[str, Any] | None, context: str = "") -> None:
        """Display metadata in the tree view.

        This is the main entry point for displaying metadata. It delegates
        to the render handler for actual tree building.
        """
        if not metadata:
            self.display_placeholder("No metadata available")
            return

        try:
            # Render the metadata view via render handler
            self.view._render_handler.emit_rebuild_tree(metadata, context=context)

            # Update information label
            self.update_information_label(metadata)

            # Enable search field
            self.view._update_search_field_state(True)

            logger.debug(
                "[TreeUiStateHandler] Displayed metadata for context: %s",
                context,
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.exception("[TreeUiStateHandler] Error displaying metadata: %s", e)
            self.display_placeholder("Error loading metadata")

        # Update header visibility after metadata display
        self.view._update_header_visibility()

    def update_information_label(self, display_data: dict[str, Any]) -> None:
        """Update the information label with metadata statistics."""
        try:
            from oncutf.config import METADATA_ICON_COLORS

            # Get parent window and information label
            parent_window = self.view._get_parent_with_file_table()
            if not parent_window or not hasattr(parent_window, "information_label"):
                return

            # Get staging manager for modified count
            from oncutf.core.metadata import get_metadata_staging_manager

            staging_manager = get_metadata_staging_manager()

            # Count total fields
            total_fields = 0

            def count_fields(data):
                nonlocal total_fields
                for _key, value in data.items():
                    if isinstance(value, dict):
                        count_fields(value)
                    else:
                        total_fields += 1

            count_fields(display_data)

            # Count modified fields from staging manager
            modified_fields = 0
            if staging_manager and self.view._current_file_path:
                staged_changes = staging_manager.get_staged_changes(self.view._current_file_path)
                modified_fields = len(staged_changes)

            # Build information label text with styling
            if total_fields == 0:
                # Empty state
                parent_window.information_label.setText("Information")
                parent_window.information_label.setStyleSheet("")
            elif modified_fields > 0:
                # Has modifications - show count with modified color
                info_text = f"Fields: {total_fields} | Modified: {modified_fields}"
                parent_window.information_label.setText(info_text)
                # Set yellow color for modified count
                label_style = f"color: {METADATA_ICON_COLORS['modified']};"
                parent_window.information_label.setStyleSheet(label_style)
            else:
                # No modifications
                info_text = f"Fields: {total_fields}"
                parent_window.information_label.setText(info_text)
                parent_window.information_label.setStyleSheet("")

        except Exception as e:
            logger.debug("Error updating information label: %s", e, extra={"dev_only": True})

    def set_current_file_from_metadata(self, metadata: dict[str, Any]) -> None:
        """Set current file from metadata if available.

        Delegates to render handler for file path extraction.
        """
        file_path = self.view._render_handler.get_file_path_from_metadata(metadata)
        if file_path:
            self.view.set_current_file_path(file_path)
            logger.debug(
                "[TreeUiStateHandler] Set current file from metadata: %s",
                file_path,
                extra={"dev_only": True},
            )

    def display_file_metadata(self, file_item: Any, context: str = "file_display") -> None:
        """Display metadata for a specific file item.

        Handles metadata extraction from file_item or cache automatically.

        Args:
            file_item: FileItem object with metadata
            context: Context string for logging
        """
        if not file_item:
            self.clear_tree()
            return

        # Try lazy loading first for better performance
        metadata = self.view._cache_behavior.try_lazy_metadata_loading(file_item, context)

        if isinstance(metadata, dict) and metadata:
            display_metadata = dict(metadata)
            display_metadata["FileName"] = file_item.filename

            # Set current file path for scroll position memory
            self.view._scroll_behavior.set_current_file_path(file_item.full_path)

            # CRITICAL: Clear any stale modifications for this file
            normalized_path = normalize_path(file_item.full_path)

            # Check if we have stale modifications
            if self.view._scroll_behavior._path_in_dict(
                normalized_path, self.view.modified_items_per_file
            ):
                logger.debug(
                    "[TreeUiStateHandler] Clearing stale modifications for %s on metadata display",
                    file_item.filename,
                    extra={"dev_only": True},
                )
                self.view._scroll_behavior._remove_from_path_dict(
                    normalized_path, self.view.modified_items_per_file
                )
                # Also clear current modifications if this is the current file
                if paths_equal(normalized_path, self.view._current_file_path):
                    self.view.modified_items.clear()

            self.display_metadata(display_metadata, context=context)
        else:
            self.clear_tree()

        # Update header visibility after file metadata display
        self.view._update_header_visibility()

    def cleanup_on_folder_change(self) -> None:
        """Clears both view and scroll memory when changing folders.

        This is different from clear_tree() which preserves scroll memory.
        """
        self.view._scroll_behavior.clear_scroll_memory()

        # Clear all staged changes
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()
        if staging_manager:
            staging_manager.clear_all()

        self.clear_tree()
        # Update header visibility for placeholder mode
        self.view._update_header_visibility()
        # Disable search field when changing folders
        self.view._update_search_field_state(False)

    def sync_placeholder_state(self) -> None:
        """Update placeholder visibility based on tree content."""
        is_empty = (
            self.view._is_placeholder_mode if hasattr(self.view, "_is_placeholder_mode") else False
        )
        self.view.set_placeholder_visible(is_empty)
        # Update header visibility when placeholder visibility changes
        self.view._update_header_visibility()
