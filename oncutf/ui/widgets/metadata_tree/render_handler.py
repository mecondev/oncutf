"""Tree rendering handler for MetadataTreeView.

This module handles all tree model building and rendering operations
for the metadata tree view.

Author: Michael Economou
Date: 2026-01-02
"""

import os
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

logger = get_cached_logger(__name__)


class TreeRenderHandler:
    """Handles tree model building and rendering operations.

    This class manages:
    - Tree model building from metadata
    - Proxy model integration
    - Expand/collapse operations
    - File path extraction from metadata
    """

    def __init__(self, view: "MetadataTreeView") -> None:
        """Initialize the render handler.

        Args:
            view: The MetadataTreeView instance

        """
        self.view = view
        self._rebuild_in_progress = False
        self._pending_rebuild_request: tuple[dict[str, Any], str] | None = None

    @property
    def is_rebuilding(self) -> bool:
        """Check if a rebuild is currently in progress."""
        return self._rebuild_in_progress

    def emit_rebuild_tree(self, metadata: dict[str, Any], context: str = "") -> None:
        """Public interface for metadata tree rebuild.

        Emits rebuild_requested signal which is processed via QueuedConnection.
        This ensures all model operations happen in the main thread via Qt event queue.
        """
        logger.debug(
            "[TreeRenderHandler] Emitting rebuild_requested signal (context=%s)",
            context,
            extra={"dev_only": True},
        )
        self.view.rebuild_requested.emit(metadata, context)

    def rebuild_tree_from_metadata(self, metadata: dict[str, Any], context: str = "") -> None:
        """Build and display the metadata tree model.

        Called via QueuedConnection from rebuild_requested signal.
        Assumes metadata is a non-empty dict.

        Includes fallback protection in case called with invalid metadata.
        Uses rebuild lock to prevent concurrent model swaps that cause segfaults.
        """
        logger.debug(
            "[TreeRenderHandler] Processing queued rebuild request (context=%s)",
            context,
            extra={"dev_only": True},
        )

        # Check if a rebuild is already in progress
        if self._rebuild_in_progress:
            logger.debug(
                "[TreeRenderHandler] Rebuild already in progress, deferring request (context=%s)",
                context,
                extra={"dev_only": True},
            )
            # Store the pending request to process after current rebuild finishes
            self._pending_rebuild_request = (metadata, context)
            return

        if not isinstance(metadata, dict):
            logger.error(
                "[TreeRenderHandler] Called with invalid metadata: %s -> %s",
                type(metadata),
                metadata,
            )
            # Delegate to ui_state handler for clearing
            self.view._ui_state_handler.clear_tree()
            return

        try:
            # Try to determine file path for scroll position memory
            self._set_current_file_from_metadata(metadata)

            # Use controller for building tree model
            if self.view._controller is None:
                self.view._lazy_init_controller()

            # Prepare minimal display state - service handles all the logic
            from oncutf.ui.widgets.metadata_tree.model import MetadataDisplayState

            display_state = MetadataDisplayState(
                file_path=self.view._current_file_path,
                modified_keys=set(),  # Service will populate from staging manager
            )

            # Pass __extended__ flag to display state for service to handle
            if metadata.get("__extended__"):
                display_state.is_extended_metadata = True

            # Set rebuild lock BEFORE model operations
            self._rebuild_in_progress = True
            logger.debug(
                "[TreeRenderHandler] Rebuild lock acquired (context=%s)",
                context,
                extra={"dev_only": True},
            )

            # Build tree model using controller - delegates ALL logic to service
            tree_model = self.view._controller.build_qt_model(metadata, display_state)

            # Store display_data for later use (from metadata directly)
            self.view._current_display_data = dict(metadata)

            # Get filename for logging
            filename = metadata.get("FileName", "unknown")

            # Apply the model (with proxy if enabled)
            self._apply_model(tree_model, filename)

            # Always expand all - no collapse functionality
            self.view.expandAll()

            # Update header visibility for content mode
            self.view._update_header_visibility()

            # Trigger scroll position restore AFTER expandAll
            self.view._scroll_behavior.restore_scroll_after_expand()

        except Exception as e:
            logger.exception("[TreeRenderHandler] Unexpected error while rendering: %s", e)
            self.view._ui_state_handler.clear_tree()
        finally:
            # ALWAYS release rebuild lock, even on error
            self._rebuild_in_progress = False
            logger.debug(
                "[TreeRenderHandler] Rebuild lock released (context=%s)",
                context,
                extra={"dev_only": True},
            )

            # Process any pending rebuild request
            if self._pending_rebuild_request:
                pending_metadata, pending_context = self._pending_rebuild_request
                self._pending_rebuild_request = None
                logger.debug(
                    "[TreeRenderHandler] Emitting deferred rebuild signal (context=%s)",
                    pending_context,
                    extra={"dev_only": True},
                )
                # Emit signal - it will be queued automatically via QueuedConnection
                self.view.rebuild_requested.emit(pending_metadata, pending_context)

    def _apply_model(self, tree_model, filename: str) -> None:
        """Apply the tree model to the view, using proxy if available.

        Args:
            tree_model: The built QStandardItemModel
            filename: Filename for logging

        """
        parent_window = self.view._get_parent_with_file_table()
        use_proxy = (
            self.view._use_proxy
            and parent_window
            and hasattr(parent_window, "metadata_proxy_model")
        )

        if use_proxy:
            self._apply_model_with_proxy(tree_model, filename, parent_window)
        else:
            self._apply_model_directly(tree_model, filename)

    def _apply_model_with_proxy(self, tree_model, filename: str, parent_window) -> None:
        """Apply model through proxy model for filtering support."""
        # CRITICAL: Disconnect view from model BEFORE changing source model
        logger.debug(
            "[TreeRenderHandler] Disconnecting view before model swap for file '%s'",
            filename,
            extra={"dev_only": True},
        )

        # Clear delegate hover state when model changes
        delegate = self.view.itemDelegate()
        if delegate and hasattr(delegate, "hovered_index"):
            delegate.hovered_index = None

        self.view.setModel(None)  # Temporarily disconnect view from proxy model
        self.view._current_tree_model = None

        # Log and set the source model to the proxy model
        logger.debug(
            "[TreeRenderHandler] Setting source model on metadata_proxy_model for file '%s'",
            filename,
            extra={"dev_only": True},
        )
        logger.debug(
            "[TreeRenderHandler] setSourceModel stack:\n%s",
            "".join(traceback.format_stack(limit=8)),
            extra={"dev_only": True},
        )

        parent_window.metadata_proxy_model.setSourceModel(tree_model)
        self.view._current_tree_model = tree_model

        # Reconnect view to proxy model AFTER source model is set
        logger.debug(
            "[TreeRenderHandler] Reconnecting view (setModel metadata_proxy_model)",
            extra={"dev_only": True},
        )
        self.view.setModel(parent_window.metadata_proxy_model)

    def _apply_model_directly(self, tree_model, filename: str) -> None:
        """Apply model directly without proxy (fallback)."""
        logger.debug(
            "[TreeRenderHandler] Proxy disabled/unavailable - setting model directly for file '%s'",
            filename,
            extra={"dev_only": True},
        )

        # Clear delegate hover state when model changes
        delegate = self.view.itemDelegate()
        if delegate and hasattr(delegate, "hovered_index"):
            delegate.hovered_index = None

        self.view.setModel(None)
        self.view.setModel(tree_model)
        self.view._current_tree_model = tree_model

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
                full_path = str(Path(file_path) / filename)
                if Path(full_path).exists():
                    return full_path

            # Try alternative metadata fields
            for field in ["SourceFile", "File:FileName", "System:FileName"]:
                if field in metadata:
                    potential_path = metadata[field]
                    if Path(potential_path).exists():
                        return potential_path

        except Exception as e:
            logger.debug("Error determining file path: %s", e, extra={"dev_only": True})

        return None

    def _set_current_file_from_metadata(self, metadata: dict[str, Any]) -> None:
        """Set current file from metadata if available."""
        file_path = self.get_file_path_from_metadata(metadata)
        if file_path:
            self.view._scroll_behavior.set_current_file_path(file_path)
            logger.debug(
                "[TreeRenderHandler] Set current file from metadata: %s",
                file_path,
                extra={"dev_only": True},
            )

    def rebuild_metadata_tree_with_stats(self, display_data: dict[str, Any]) -> None:
        """Rebuild metadata tree and update information label with statistics.

        This is a convenience method that combines tree rebuild with stats update.
        """
        # Rebuild the tree
        self.rebuild_tree_from_metadata(display_data, context="rebuild_with_stats")

        # Update the information label via ui_state handler
        self.view._ui_state_handler.update_information_label(display_data)
