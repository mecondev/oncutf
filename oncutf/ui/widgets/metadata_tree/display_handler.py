"""Display handler for MetadataTreeView.

This module handles all display-related operations for the metadata tree view,
including metadata rendering, placeholder states, and information label updates.

Author: Michael Economou
Date: 2026-01-01
"""

import os
import traceback
from typing import TYPE_CHECKING, Any

from oncutf.core.pyqt_imports import QStandardItemModel
from oncutf.utils.filesystem.path_normalizer import normalize_path
from oncutf.utils.filesystem.path_utils import paths_equal
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

logger = get_cached_logger(__name__)


class DisplayHandler:
    """Handles all display operations for MetadataTreeView.

    This class manages:
    - Metadata display and rendering
    - Placeholder states and empty view handling
    - Information label updates
    - Tree rebuilding and model swapping
    """

    def __init__(self, view: "MetadataTreeView") -> None:
        """Initialize the display handler.

        Args:
            view: The MetadataTreeView instance
        """
        self.view = view
        self._rebuild_in_progress = False
        self._pending_rebuild_request = None

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
            self.view._use_proxy and parent_window and hasattr(parent_window, "metadata_proxy_model")
        )
        if use_proxy:
            logger.debug(
                "[MetadataTree] Setting empty placeholder source model on metadata_proxy_model",
                extra={"dev_only": True},
            )
            logger.debug(
                "[MetadataTree] setSourceModel (placeholder) stack:\n%s",
                "".join(traceback.format_stack(limit=8)),
                extra={"dev_only": True},
            )
            parent_window.metadata_proxy_model.setSourceModel(model)
            logger.debug(
                "[MetadataTree] Calling setModel(self, metadata_proxy_model) for placeholder",
                extra={"dev_only": True},
            )
            self.view.setModel(parent_window.metadata_proxy_model)
        else:
            logger.debug(
                "[MetadataTree] Proxy disabled - setting placeholder model directly",
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
        parent_window = self.view._get_parent_with_file_table()
        if parent_window and hasattr(parent_window, "information_label"):
            parent_window.information_label.setText("Information")
            parent_window.information_label.setStyleSheet("")

        # Update header visibility for empty state
        self.view._update_header_visibility()

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
        """Display metadata in the tree view."""
        if not metadata:
            self.display_placeholder("No metadata available")
            return

        try:
            # Render the metadata view (service will apply staged changes)
            self.emit_rebuild_tree(metadata, context=context)

            # Update information label
            self.update_information_label(metadata)

            # Enable search field
            self.view._update_search_field_state(True)

            logger.debug(
                "[MetadataTree] Displayed metadata for context: %s",
                context,
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.exception("[MetadataTree] Error displaying metadata: %s", e)
            self.display_placeholder("Error loading metadata")

        # Update header visibility after metadata display
        self.view._update_header_visibility()

    def emit_rebuild_tree(self, metadata: dict[str, Any], context: str = "") -> None:
        """Public interface for metadata tree rebuild.
        Emits rebuild_requested signal which is processed via QueuedConnection.
        This ensures all model operations happen in the main thread via Qt event queue.
        """
        logger.debug(
            "[MetadataTree] Emitting rebuild_requested signal (context=%s)",
            context,
            extra={"dev_only": True},
        )
        self.view.rebuild_requested.emit(metadata, context)

    def rebuild_tree_from_metadata(self, metadata: dict[str, Any], context: str = "") -> None:
        """Actually builds the metadata tree and displays it.
        Called via QueuedConnection from rebuild_requested signal.
        Assumes metadata is a non-empty dict.

        Includes fallback protection in case called with invalid metadata.
        Uses rebuild lock to prevent concurrent model swaps that cause segfaults.
        """
        logger.debug(
            "[MetadataTree] Processing queued rebuild request (context=%s)",
            context,
            extra={"dev_only": True},
        )

        # Check if a rebuild is already in progress
        if self._rebuild_in_progress:
            logger.debug(
                "[MetadataTree] Rebuild already in progress, deferring request (context=%s)",
                context,
                extra={"dev_only": True},
            )
            # Store the pending request to process after current rebuild finishes
            self._pending_rebuild_request = (metadata, context)
            return

        if not isinstance(metadata, dict):
            logger.error(
                "[render_metadata_view] Called with invalid metadata: %s -> %s",
                type(metadata),
                metadata,
            )
            self.clear_tree()
            return

        try:
            # Try to determine file path for scroll position memory
            self.set_current_file_from_metadata(metadata)

            # Use controller for building tree model
            # All business logic (display data prep, extended key detection)
            # is handled by the service layer
            if self.view._controller is None:
                self.view._lazy_init_controller()

            # Prepare minimal display state - service handles all the logic
            # NOTE: Do NOT pass self.modified_items here. The service's _prepare_display_data
            # will get modified_keys directly from the staging manager for the current file.
            # Passing stale view-local modified_items causes "yellow everywhere" state leak.
            from oncutf.ui.widgets.metadata_tree.model import MetadataDisplayState

            display_state = MetadataDisplayState(
                file_path=self.view._current_file_path,
                modified_keys=set()  # Service will populate from staging manager
            )

            # Pass __extended__ flag to display state for service to handle
            if metadata.get("__extended__"):
                display_state.is_extended_metadata = True

            # Set rebuild lock BEFORE model operations
            self._rebuild_in_progress = True
            logger.debug(
                "[MetadataTree] Rebuild lock acquired (context=%s)",
                context,
                extra={"dev_only": True},
            )

            # Build tree model using controller - delegates ALL logic to service
            tree_model = self.view._controller.build_qt_model(metadata, display_state)

            # Store display_data for later use (from metadata directly)
            self.view._current_display_data = dict(metadata)

            # Get filename for logging
            filename = metadata.get("FileName", "unknown")

            # Use proxy model for filtering instead of setting model directly
            parent_window = self.view._get_parent_with_file_table()
            use_proxy = (
                self.view._use_proxy and parent_window and hasattr(parent_window, "metadata_proxy_model")
            )
            if use_proxy:
                # CRITICAL: Disconnect view from model BEFORE changing source model
                # This prevents Qt internal race conditions during model swap
                logger.debug(
                    "[MetadataTree] Disconnecting view before model swap for file '%s'",
                    filename,
                    extra={"dev_only": True},
                )
                # Clear delegate hover state when model changes to prevent stale index references
                delegate = self.view.itemDelegate()
                if delegate and hasattr(delegate, "hovered_index"):
                    delegate.hovered_index = None
                self.view.setModel(None)  # Temporarily disconnect view from proxy model
                self.view._current_tree_model = None

                # Log and set the source model to the proxy model (debug help for race conditions)
                logger.debug(
                    "[MetadataTree] Setting source model on metadata_proxy_model for file '%s'",
                    filename,
                    extra={"dev_only": True},
                )
                logger.debug(
                    "[MetadataTree] setSourceModel stack:\n%s",
                    "".join(traceback.format_stack(limit=8)),
                    extra={"dev_only": True},
                )
                parent_window.metadata_proxy_model.setSourceModel(tree_model)
                self.view._current_tree_model = tree_model

                # Reconnect view to proxy model AFTER source model is set
                logger.debug(
                    "[MetadataTree] Reconnecting view (setModel metadata_proxy_model)",
                    extra={"dev_only": True},
                )
                self.view.setModel(parent_window.metadata_proxy_model)  # Use self.setModel() not super()
            else:
                # Fallback: set model directly if proxy model is disabled or unavailable
                logger.debug(
                    "[MetadataTree] Proxy disabled/unavailable - setting model directly for file '%s'",
                    filename,
                    extra={"dev_only": True},
                )
                # Clear delegate hover state when model changes to prevent stale index references
                delegate = self.view.itemDelegate()
                if delegate and hasattr(delegate, "hovered_index"):
                    delegate.hovered_index = None
                self.view.setModel(None)
                self.view.setModel(tree_model)
                self.view._current_tree_model = tree_model

            # Always expand all - no collapse functionality
            self.view.expandAll()

            # Update header visibility for content mode
            self.view._update_header_visibility()

            # Update information label with metadata count
            self.update_information_label(self.view._current_display_data)

            # Update header visibility for content mode
            self.view._update_header_visibility()

            # Trigger scroll position restore AFTER expandAll
            self.view.restore_scroll_after_expand()

            # Update header visibility for content mode
            self.view._update_header_visibility()

        except Exception as e:
            logger.exception("[render_metadata_view] Unexpected error while rendering: %s", e)
            self.clear_tree()
        finally:
            # ALWAYS release rebuild lock, even on error
            self._rebuild_in_progress = False
            logger.debug(
                "[MetadataTree] Rebuild lock released (context=%s)",
                context,
                extra={"dev_only": True},
            )

            # Process any pending rebuild request
            if self._pending_rebuild_request:
                pending_metadata, pending_context = self._pending_rebuild_request
                self._pending_rebuild_request = None
                logger.debug(
                    "[MetadataTree] Emitting deferred rebuild signal (context=%s)",
                    pending_context,
                    extra={"dev_only": True},
                )
                # Emit signal - it will be queued automatically via QueuedConnection
                self.view.rebuild_requested.emit(pending_metadata, pending_context)

    def get_file_path_from_metadata(self, metadata: dict[str, Any]) -> str | None:
        """Extract file path from metadata dictionary.

        Args:
            metadata: Metadata dictionary

        Returns:
            Full file path if found and exists, None otherwise
        """
        try:
            # Try to get file path from metadata
            file_path = metadata.get("File:Directory", "")
            filename = metadata.get("File:FileName", "")

            if file_path and filename:
                full_path = os.path.join(file_path, filename)
                if os.path.exists(full_path):
                    return full_path

            # Try alternative metadata fields
            for field in ["SourceFile", "File:FileName", "System:FileName"]:
                if field in metadata:
                    potential_path = metadata[field]
                    if os.path.exists(potential_path):
                        return potential_path

        except Exception as e:
            logger.debug("Error determining file path: %s", e, extra={"dev_only": True})

        return None

    def set_current_file_from_metadata(self, metadata: dict[str, Any]) -> None:
        """Set current file from metadata if available."""
        file_path = self.get_file_path_from_metadata(metadata)
        if file_path:
            self.view.set_current_file_path(file_path)
            logger.debug(
                "[MetadataTree] Set current file from metadata: %s",
                file_path,
                extra={"dev_only": True},
            )

    def rebuild_metadata_tree_with_stats(self, display_data: dict[str, Any]) -> None:
        """Rebuild metadata tree and update information label with statistics.

        This is a convenience method that combines tree rebuild with stats update.
        """
        # Rebuild the tree
        self.rebuild_tree_from_metadata(display_data, context="rebuild_with_stats")

        # Update the information label
        self.update_information_label(display_data)

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
        metadata = self.view._try_lazy_metadata_loading(file_item, context)

        if isinstance(metadata, dict) and metadata:
            display_metadata = dict(metadata)
            display_metadata["FileName"] = file_item.filename

            # Set current file path for scroll position memory
            self.view.set_current_file_path(file_item.full_path)

            # CRITICAL: Clear any stale modifications for this file when displaying fresh metadata
            # This prevents showing [MODIFIED] for fields that were never actually saved
            normalized_path = normalize_path(file_item.full_path)

            # Check if we have stale modifications
            if self.view._scroll_behavior._path_in_dict(normalized_path, self.view.modified_items_per_file):
                logger.debug(
                    "[MetadataTree] Clearing stale modifications for %s on metadata display",
                    file_item.filename,
                    extra={"dev_only": True},
                )
                self.view._scroll_behavior._remove_from_path_dict(normalized_path, self.view.modified_items_per_file)
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
        self.view.clear_scroll_memory()

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
        is_empty = self.view._is_placeholder_mode if hasattr(self.view, "_is_placeholder_mode") else False
        self.view.set_placeholder_visible(is_empty)
        # Update header visibility when placeholder visibility changes
        self.view._update_header_visibility()
