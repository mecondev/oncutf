"""Rotation handling for metadata editing.

This module provides rotation-specific operations for metadata editing,
including setting rotation to zero degrees.

Author: Michael Economou
Date: 2026-01-01
"""

from typing import TYPE_CHECKING, Any

from oncutf.utils.filesystem.file_status_helpers import get_metadata_value
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.behaviors.metadata_edit.metadata_edit_behavior import (
        MetadataEditBehavior,
    )

logger = get_cached_logger(__name__)


class RotationHandler:
    """Handles rotation metadata operations.

    Provides methods for:
    - Setting rotation to zero degrees
    - Fallback rotation operations
    """

    def __init__(self, widget: Any, behavior: "MetadataEditBehavior") -> None:
        """Initialize rotation handler.

        Args:
            widget: The host widget
            behavior: The parent behavior for callbacks

        """
        self._widget = widget
        self._behavior = behavior

    def set_rotation_to_zero(self, key_path: str) -> None:
        """Set rotation metadata to 0 degrees.

        Args:
            key_path: Metadata key path for rotation field

        """
        if not key_path:
            return

        # Get current file
        selected_files = self._widget._get_current_selection()
        file_item = selected_files[0] if selected_files else None
        if not file_item:
            logger.warning("No file selected for rotation reset")
            return

        # Get current value
        current_value = get_metadata_value(file_item.full_path, key_path)

        # Early return if already at 0 or 1 (no rotation)
        if current_value in ("0", "1"):
            logger.debug(
                "Rotation already at 0 for %s, skipping",
                file_item.filename,
            )
            return

        # Use unified metadata manager if available
        if self._widget._direct_loader:
            try:
                # Set rotation to 0
                self._widget._direct_loader.set_metadata_value(file_item.full_path, key_path, "0")

                # Update tree display via behavior method (allows test mocking)
                self._behavior._update_tree_item_value(key_path, "0")

                # Mark as modified via behavior method (allows test mocking)
                self._behavior.mark_as_modified(key_path)

                logger.debug(
                    "Set rotation to 0 deg for %s via UnifiedMetadataManager",
                    file_item.filename,
                )

                # Emit signal
                if hasattr(self._widget, "value_edited"):
                    self._widget.value_edited.emit(
                        key_path, "0", str(current_value) if current_value else ""
                    )
            except Exception:
                logger.exception(
                    "Failed to set rotation via UnifiedMetadataManager",
                )
