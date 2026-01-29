"""Reset operations for metadata editing.

This module provides reset operations for metadata values,
restoring them to their original state.

Author: Michael Economou
Date: 2026-01-01
"""

from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ResetHandler:
    """Handles metadata reset operations.

    Provides methods for:
    - Resetting values to original
    - Fallback reset operations
    """

    def __init__(
        self,
        widget: Any,
        update_tree_item_callback: Any,
    ) -> None:
        """Initialize reset handler.

        Args:
            widget: The host widget
            update_tree_item_callback: Callback to update tree item value

        """
        self._widget = widget
        self._update_tree_item_value = update_tree_item_callback

    def reset_value(self, key_path: str) -> None:
        """Reset a metadata value to its original value.

        Args:
            key_path: Metadata key path to reset

        """
        if not key_path:
            return

        # Get current file
        selected_files = self._widget._get_current_selection()
        file_item = selected_files[0] if selected_files else None
        if not file_item:
            logger.warning("No file selected for reset")
            return

        # Get original value
        original_value = self._widget._cache_behavior.get_original_value_from_cache(key_path)
        if original_value is None:
            logger.warning("No original value found for %s", key_path)
            return

        # Use unified metadata manager if available
        if self._widget._direct_loader:
            try:
                # Reset to original value
                self._widget._direct_loader.set_metadata_value(
                    file_item.full_path, key_path, str(original_value)
                )

                # Update tree display
                self._update_tree_item_value(key_path, str(original_value))

                # Remove from staging
                from oncutf.core.metadata.metadata_service import get_metadata_service

                metadata_service = get_metadata_service()
                if self._widget._current_file_path:
                    metadata_service.staging_manager.clear_staged_change(
                        self._widget._current_file_path, key_path
                    )

                # Remove from modified items if it's there
                if key_path in self._widget.modified_items:
                    self._widget.modified_items.remove(key_path)

                # Update file icon status
                self._widget._cache_behavior.update_file_icon_status()

                # Emit signal
                if hasattr(self._widget, "value_reset"):
                    self._widget.value_reset.emit(key_path)

                logger.debug(
                    "Reset %s to original value via UnifiedMetadataManager",
                    key_path,
                )

                return
            except Exception as e:
                logger.exception(
                    "Failed to reset value via UnifiedMetadataManager: %s",
                    e,
                )

        # Fallback to manual method
        self._fallback_reset_value(key_path, original_value)

    def _fallback_reset_value(self, key_path: str, original_value: Any) -> None:
        """Fallback method for resetting metadata without unified manager.

        Args:
            key_path: Metadata key path
            original_value: Original value to restore

        """
        from oncutf.core.metadata.metadata_service import get_metadata_service

        metadata_service = get_metadata_service()

        # Clear staged change
        if self._widget._current_file_path:
            metadata_service.staging_manager.clear_staged_change(
                self._widget._current_file_path, key_path
            )

        # Remove from modified items
        if key_path in self._widget.modified_items:
            self._widget.modified_items.remove(key_path)

        # Update the file icon status
        self._widget._cache_behavior.update_file_icon_status()

        # Update the tree display
        self._update_tree_item_value(key_path, str(original_value))

        # Force viewport update
        self._widget.viewport().update()

        # Emit signal
        if hasattr(self._widget, "value_reset"):
            self._widget.value_reset.emit(key_path)
