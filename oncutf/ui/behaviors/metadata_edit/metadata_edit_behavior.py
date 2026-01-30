"""Metadata editing behavior for MetadataTreeView.

This behavior handles all metadata editing operations including:
- Value editing with dialogs
- Date/time field editing
- Rotation metadata
- Reset operations
- Undo/redo support
- Modified item tracking

This module acts as the main orchestrator, delegating to specialized handlers:
- FieldDetector: Field type detection
- TreeNavigator: Tree path operations
- EditOperations: Edit dialogs and operations
- RotationHandler: Rotation-specific operations
- ResetHandler: Reset operations
- UndoRedoHandler: Undo/redo support

Author: Michael Economou
Date: December 28, 2025
Refactored: January 1, 2026
"""

from typing import Any, Protocol

from PyQt5.QtCore import QModelIndex, pyqtSignal
from PyQt5.QtWidgets import QApplication

from oncutf.ui.behaviors.metadata_edit.edit_operations import EditOperations
from oncutf.ui.behaviors.metadata_edit.field_detector import (
    is_date_time_field,
    is_editable_metadata_field,
    normalize_metadata_field_name,
)
from oncutf.ui.behaviors.metadata_edit.reset_handler import ResetHandler
from oncutf.ui.behaviors.metadata_edit.rotation_handler import RotationHandler
from oncutf.ui.behaviors.metadata_edit.tree_navigator import TreeNavigator
from oncutf.ui.behaviors.metadata_edit.undo_redo_handler import UndoRedoHandler
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_ui_update

logger = get_cached_logger(__name__)


class EditableWidget(Protocol):
    """Protocol defining the interface required for metadata edit behavior.

    This protocol specifies what methods a widget must provide to use
    MetadataEditBehavior for editing operations.
    """

    # From MetadataTreeView
    modified_items: set[str]
    _current_file_path: str | None
    _direct_loader: Any | None
    _current_display_data: dict[str, Any] | None

    # Signals
    value_edited: pyqtSignal
    value_reset: pyqtSignal
    value_copied: pyqtSignal

    def model(self) -> Any:
        """Get the tree model."""
        ...

    def setCurrentIndex(self, index: QModelIndex) -> None:
        """Set current index/selection."""
        ...

    def scrollTo(self, index: QModelIndex) -> None:
        """Scroll to make index visible."""
        ...

    def viewport(self) -> Any:
        """Get the viewport widget."""
        ...

    def _get_current_selection(self) -> list[Any]:
        """Get the currently selected file items."""
        ...

    def _get_metadata_cache(self) -> dict[str, Any] | None:
        """Get metadata cache dictionary."""
        ...

    def _get_parent_with_file_table(self) -> Any | None:
        """Get the parent window that has a file table."""
        ...

    def _update_file_icon_status(self) -> None:
        """Update file icon status indicator."""
        ...

    def _get_original_value_from_cache(self, key_path: str) -> Any | None:
        """Get original value from metadata cache."""
        ...

    def _get_original_metadata_value(self, key_path: str) -> Any | None:
        """Get original metadata value for comparison."""
        ...

    def _update_information_label(self, display_data: dict[str, Any]) -> None:
        """Update information label with display data."""
        ...


class MetadataEditBehavior:
    """Behavior for metadata editing operations in tree views.

    This behavior encapsulates all logic related to editing metadata:
    - Opening edit dialogs (text, datetime)
    - Handling edit commands with undo/redo
    - Marking items as modified
    - Resetting values to original
    - Tree navigation and selection restoration

    Acts as thin orchestrator, delegating to specialized handlers.
    """

    def __init__(self, widget: EditableWidget) -> None:
        """Initialize the metadata edit behavior.

        Args:
            widget: The host widget that provides edit operations

        """
        self._widget = widget

        # Initialize handlers - rotation handler needs self reference for callbacks
        self._tree_navigator = TreeNavigator(widget)
        self._edit_ops = EditOperations(widget, self._tree_navigator, self._update_tree_item_value)
        self._rotation_handler = RotationHandler(widget, self)
        self._reset_handler = ResetHandler(widget, self._update_tree_item_value)
        self._undo_redo = UndoRedoHandler(widget)

    # =====================================
    # Field Type Detection (delegated)
    # =====================================

    def _is_date_time_field(self, key_path: str) -> bool:
        """Check if a metadata field is a date/time field."""
        return is_date_time_field(key_path)

    def _is_editable_metadata_field(self, key_path: str) -> bool:
        """Check if a metadata field can be edited directly."""
        return is_editable_metadata_field(key_path)

    def _normalize_metadata_field_name(self, key_path: str) -> str:
        """Normalize metadata field name for consistency."""
        return normalize_metadata_field_name(key_path)

    # =====================================
    # Tree Navigation (delegated)
    # =====================================

    def _get_item_path(self, index: QModelIndex) -> list[str]:
        """Get the path from root to the given index."""
        return self._tree_navigator.get_item_path(index)

    def _find_item_by_path(self, path: list[str]) -> QModelIndex | None:
        """Find an item in the tree by its path from root."""
        return self._tree_navigator.find_item_by_path(path)

    def _find_path_by_key(self, key_path: str) -> list[str] | None:
        """Find the tree path for a given metadata key path."""
        return self._tree_navigator.find_path_by_key(key_path)

    def _restore_selection(self, path: list[str]) -> None:
        """Restore selection to the given path."""
        self._tree_navigator.restore_selection(path)

    def get_key_path(self, index: QModelIndex) -> str:
        """Return the full key path for the given index."""
        return self._tree_navigator.get_key_path(index)

    # =====================================
    # Main Edit Operations (delegated)
    # =====================================

    def edit_value(self, key_path: str, current_value: Any) -> None:
        """Open a dialog to edit the value of a metadata field."""
        self._edit_ops.edit_value(key_path, current_value)

    def _fallback_edit_value(
        self, key_path: str, new_value: str, old_value: str, files_to_modify: list
    ) -> None:
        """Fallback method for editing metadata without command system."""
        self._edit_ops._fallback_edit_value(key_path, new_value, old_value, files_to_modify)

    # =====================================
    # Rotation Operations (delegated)
    # =====================================

    def set_rotation_to_zero(self, key_path: str) -> None:
        """Set rotation metadata to 0 degrees."""
        self._rotation_handler.set_rotation_to_zero(key_path)

    def _fallback_set_rotation_to_zero(
        self, key_path: str, new_value: str, current_value: Any
    ) -> None:
        """Fallback method for setting rotation to zero."""
        self._rotation_handler._fallback_set_rotation_to_zero(key_path, new_value, current_value)

    # =====================================
    # Reset Operations (delegated)
    # =====================================

    def reset_value(self, key_path: str) -> None:
        """Reset a metadata value to its original value."""
        self._reset_handler.reset_value(key_path)

    # =====================================
    # Undo/Redo Operations (delegated)
    # =====================================

    def _undo_metadata_operation(self) -> None:
        """Undo the last metadata operation."""
        self._undo_redo.undo_metadata_operation()

    def _redo_metadata_operation(self) -> None:
        """Redo the last undone metadata operation."""
        self._undo_redo.redo_metadata_operation()

    def _show_history_dialog(self) -> None:
        """Show metadata history dialog."""
        self._undo_redo.show_history_dialog()

    # =====================================
    # Tree Item Updates
    # =====================================

    def _update_tree_item_value(self, key_path: str, new_value: str) -> None:
        """Update the tree item value display by delegating to widget.

        Args:
            key_path: Metadata key path
            new_value: New value to display

        """
        # Delegate to widget method if available (allows mocking in tests)
        if hasattr(self._widget, "_update_tree_item_value"):
            widget_method = self._widget._update_tree_item_value
            # Only call if it's not the behavior's own method (avoid recursion)
            if callable(widget_method) and widget_method != self._update_tree_item_value:
                widget_method(key_path, new_value)

    # =====================================
    # Modified Item Tracking
    # =====================================

    def mark_as_modified(self, key_path: str) -> None:
        """Mark a field as modified.

        Args:
            key_path: Metadata key path

        """
        if not key_path:
            return

        self._widget.modified_items.add(key_path)

        # Schedule UI update
        schedule_ui_update(self._widget._cache_behavior.update_file_icon_status, delay=0)

        # Update information label if available
        if hasattr(self._widget, "_current_display_data") and self._widget._current_display_data:
            self._widget._update_information_label(self._widget._current_display_data)

        # Update the view
        self._widget.viewport().update()

    def smart_mark_modified(self, key_path: str, new_value: Any) -> None:
        """Mark a field as modified only if it differs from the original value.

        Args:
            key_path: Metadata key path
            new_value: New value to compare with original

        """
        # Get original value from ORIGINAL metadata cache, not staging
        original_value = self._widget._cache_behavior.get_original_metadata_value(key_path)

        # Convert values to strings for comparison
        new_str = str(new_value) if new_value is not None else ""
        original_str = str(original_value) if original_value is not None else ""

        if new_str != original_str:
            self.mark_as_modified(key_path)
            logger.debug(
                "Marked as modified: %s ('%s' -> '%s')",
                key_path,
                original_str,
                new_str,
            )
        # Remove from modifications if values are the same
        elif key_path in self._widget.modified_items:
            self._widget.modified_items.remove(key_path)
            logger.debug(
                "Removed modification mark: %s (value restored to original)",
                key_path,
            )

    # =====================================
    # Utility Methods
    # =====================================

    def copy_value(self, value: Any) -> None:
        """Copy the value to clipboard and emit the value_copied signal.

        Args:
            value: Value to copy to clipboard

        """
        if not value:
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(str(value))

        if hasattr(self._widget, "value_copied"):
            self._widget.value_copied.emit(str(value))
