"""Module: search_handler.py

Author: Michael Economou
Date: 2025-12-23

Search functionality handler for the metadata tree widget.

This module handles all search-related functionality:
- Enabling/disabling search field based on metadata availability
- Updating search suggestions from metadata
- Collecting suggestions from tree models and metadata dictionaries
- Managing search field styling and state

The handler operates on a MetadataTreeView instance passed to it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.core.theme_manager import get_theme_manager
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.ui.tooltip_helper import TooltipHelper, TooltipType

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

logger = get_cached_logger(__name__)


class MetadataTreeSearchHandler:
    """Handler for metadata tree search functionality.

    This class encapsulates all search-related logic:
    - Enabling/disabling search field
    - Updating search suggestions
    - Collecting suggestions from tree models
    - Collecting suggestions from metadata dictionaries
    - Managing search field styling

    Usage:
        handler = MetadataTreeSearchHandler(tree_view)
        handler.update_search_field_state(enabled=True)
    """

    def __init__(self, tree_view: MetadataTreeView) -> None:
        """Initialize the search handler.

        Args:
            tree_view: The MetadataTreeView instance this handler belongs to

        """
        self._tree_view = tree_view

    def update_search_field_state(self, enabled: bool) -> None:
        """Update the metadata search field enabled state and tooltip.

        Args:
            enabled: Whether to enable or disable the search field

        """
        parent_window = self._tree_view._get_parent_with_file_table()
        if not parent_window or not hasattr(parent_window, "metadata_search_field"):
            return

        search_field = parent_window.metadata_search_field

        if enabled:
            self._enable_search_field(search_field, parent_window)
        else:
            self._disable_search_field(search_field, parent_window)

    def _enable_search_field(self, search_field, parent_window) -> None:
        """Enable the search field with proper styling and suggestions."""
        search_field.setEnabled(True)
        search_field.setReadOnly(False)
        TooltipHelper.setup_tooltip(search_field, "Search metadata...", TooltipType.INFO)

        # Enable action icons
        if hasattr(parent_window, "search_action"):
            parent_window.search_action.setEnabled(True)
        if hasattr(parent_window, "clear_search_action"):
            parent_window.clear_search_action.setEnabled(True)

        # Enable completer
        if hasattr(parent_window, "metadata_search_completer"):
            parent_window.metadata_search_completer.setCompletionMode(
                parent_window.metadata_search_completer.PopupCompletion
            )

        # Apply enabled styling
        theme = get_theme_manager()
        search_field.setStyleSheet(
            f"""
            QLineEdit#metadataSearchField {{
                background-color: {theme.get_color('input_bg')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 4px;
                color: {theme.get_color('text')};
                padding: 2px 8px;
                min-height: 16px;
                max-height: 18px;
                margin-top: 0px;
                margin-bottom: 2px;
            }}
            QLineEdit#metadataSearchField:hover {{
                background-color: {theme.get_color('input_hover_bg')};
                border-color: {theme.get_color('border_hover')};
            }}
            QLineEdit#metadataSearchField:focus {{
                border-color: {theme.get_color('accent')};
                background-color: {theme.get_color('input_focus_bg')};
            }}
        """
        )

        # Update suggestions when enabled
        self.update_search_suggestions()

        # Restore any saved search text
        if hasattr(parent_window, "signal_controller"):
            parent_window.signal_controller.restore_metadata_search_text()

    def _disable_search_field(self, search_field, parent_window) -> None:
        """Disable the search field with proper styling."""
        search_field.setEnabled(False)
        search_field.setReadOnly(True)
        TooltipHelper.setup_tooltip(search_field, "No metadata available", TooltipType.WARNING)

        # Disable action icons
        if hasattr(parent_window, "search_action"):
            parent_window.search_action.setEnabled(False)
        if hasattr(parent_window, "clear_search_action"):
            parent_window.clear_search_action.setEnabled(False)

        # Disable completer
        if hasattr(parent_window, "metadata_search_completer"):
            parent_window.metadata_search_completer.setCompletionMode(
                parent_window.metadata_search_completer.UnfilteredPopupCompletion
            )

        # Apply disabled styling
        theme = get_theme_manager()
        search_field.setStyleSheet(
            f"""
            QLineEdit#metadataSearchField:disabled {{
                background-color: {theme.get_color('input_bg')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 4px;
                color: {theme.get_color('text_disabled')};
                padding: 2px 8px;
                min-height: 16px;
                max-height: 18px;
                margin-top: 0px;
                margin-bottom: 2px;
            }}
            QLineEdit#metadataSearchField:disabled:hover {{
                background-color: {theme.get_color('input_bg')};
                color: {theme.get_color('text_disabled')};
                border: 1px solid {theme.get_color('border')};
            }}
        """
        )

    def clear_search_field(self) -> None:
        """Clear the metadata search field."""
        parent_window = self._tree_view._get_parent_with_file_table()
        if not parent_window:
            return

        # Call the signal controller's clear method if available
        if hasattr(parent_window, "signal_controller"):
            parent_window.signal_controller._clear_metadata_search()
        elif hasattr(parent_window, "metadata_search_field"):
            # Fallback: clear the field directly
            parent_window.metadata_search_field.clear()
            if hasattr(parent_window, "clear_search_action"):
                parent_window.clear_search_action.setVisible(False)

    def update_search_suggestions(self) -> None:
        """Update search suggestions based on current metadata."""
        try:
            suggestions = set()

            # Get suggestions from current tree model
            model = self._tree_view.model()
            if model:
                self._collect_suggestions_from_tree_model(model, suggestions)

            # Get suggestions from all loaded files
            all_files = self._get_all_loaded_files()
            for file_item in all_files:
                if hasattr(file_item, "metadata") and file_item.metadata:
                    self._collect_suggestions_from_metadata(file_item.metadata, suggestions)

            # Update search field suggestions
            if hasattr(self._tree_view, "_search_field") and self._tree_view._search_field:
                self._tree_view._search_field.update_suggestions(sorted(suggestions))

            logger.debug(
                "[MetadataTreeSearchHandler] Updated search suggestions: %d items",
                len(suggestions),
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.exception("[MetadataTreeSearchHandler] Error updating search suggestions: %s", e)

    def _collect_suggestions_from_tree_model(self, model, suggestions: set) -> None:
        """Collect search suggestions from the current tree model.

        Args:
            model: The tree model to collect from
            suggestions: Set to add suggestions to

        """
        if not model:
            return

        # If it's a proxy model, get the source model
        source_model = model
        if hasattr(model, "sourceModel"):
            source_model = model.sourceModel()

        # Check if the source model has invisibleRootItem (QStandardItemModel)
        if not hasattr(source_model, "invisibleRootItem"):
            return

        # Traverse the tree model to collect keys and values
        root_item = source_model.invisibleRootItem()
        if not root_item:
            return

        for i in range(root_item.rowCount()):
            group_item = root_item.child(i)
            if not group_item:
                continue

            group_name = group_item.text()

            # Collect from group children
            for j in range(group_item.rowCount()):
                key_item = group_item.child(j, 0)  # Key column
                value_item = group_item.child(j, 1)  # Value column

                if key_item and value_item:
                    key = key_item.text()
                    value = value_item.text()

                    # Skip empty or internal keys
                    if not key or key.startswith("__"):
                        continue

                    # Add the key itself
                    suggestions.add(key)

                    # Add group:key format for grouped items
                    if group_name and group_name != "Other":
                        suggestions.add(f"{group_name}:{key}")

                    # Add values for simple strings (not too long)
                    if (
                        isinstance(value, str)
                        and len(value) < 100
                        and value not in ["-", "", "N/A"]
                    ):
                        # Add key=value format
                        suggestions.add(f"{key}={value}")

                        # Also add group:key=value for grouped items
                        if group_name and group_name != "Other":
                            suggestions.add(f"{group_name}:{key}={value}")

    def _collect_suggestions_from_metadata(self, metadata: dict, suggestions: set) -> None:
        """Collect search suggestions from a metadata dictionary.

        Args:
            metadata: The metadata dictionary to collect from
            suggestions: Set to add suggestions to

        """
        if not isinstance(metadata, dict):
            return

        for key, value in metadata.items():
            # Skip internal keys
            if key.startswith("__"):
                continue

            # Add the key itself
            suggestions.add(key)

            # Handle nested dictionaries (groups)
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    # Add group:key format
                    suggestions.add(f"{key}:{nested_key}")

                    # Add values for nested items (if they're simple strings)
                    if isinstance(nested_value, str) and len(nested_value) < 100:
                        # Add key=value format for easier searching
                        suggestions.add(f"{key}:{nested_key}={nested_value}")

            # Add values for top-level items (if they're simple strings)
            elif isinstance(value, str) and len(value) < 100:
                # Add key=value format
                suggestions.add(f"{key}={value}")

            # Add numeric values as strings
            elif isinstance(value, int | float) and abs(value) < 1000000:
                suggestions.add(f"{key}={value}")

    def _get_all_loaded_files(self):
        """Get all currently loaded files from the parent window."""
        parent_window = self._tree_view._get_parent_with_file_table()
        if not parent_window or not hasattr(parent_window, "file_model"):
            return []

        if parent_window.file_model and hasattr(parent_window.file_model, "files"):
            return parent_window.file_model.files

        return []
