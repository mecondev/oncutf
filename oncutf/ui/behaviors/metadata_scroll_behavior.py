"""Module: metadata_scroll_behavior.py.

Author: Michael Economou
Date: 2025-12-28

MetadataScrollBehavior - Composition-based scroll position management.

This is the behavioral replacement for MetadataScrollMixin.
Uses protocol-based composition instead of inheritance.

Provides:
- Scroll position memory per file
- Expand/collapse state per file
- Path-aware dictionary operations for cross-platform compatibility
- Smooth scroll restoration
"""

from typing import TYPE_CHECKING, Any, Protocol

from oncutf.utils.filesystem.path_normalizer import normalize_path
from oncutf.utils.filesystem.path_utils import paths_equal
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_ui_update

if TYPE_CHECKING:
    from PyQt5.QtCore import QModelIndex

logger = get_cached_logger(__name__)


class ScrollableTreeWidget(Protocol):
    """Protocol defining requirements for widgets that can use MetadataScrollBehavior."""

    def model(self):
        """Return Qt model."""
        ...

    def verticalScrollBar(self):
        """Return vertical scrollbar."""
        ...

    def isExpanded(self, index: "QModelIndex") -> bool:
        """Check if index is expanded."""
        ...

    def expand(self, index: "QModelIndex") -> None:
        """Expand index."""
        ...


class MetadataScrollBehavior:
    """Behavior class providing scroll position management for tree views.

    This is the composition-based replacement for MetadataScrollMixin.
    Manages per-file scroll positions and expanded item states,
    with intelligent restoration when switching between files.

    State management:
    - All scroll state is stored in this behavior instance
    - Path-aware dictionaries for cross-platform compatibility
    - No state pollution in widget's __dict__

    Usage:
        class MyTreeView(QTreeView):
            def __init__(self):
                super().__init__()
                self._scroll_behavior = MetadataScrollBehavior(self)
    """

    def __init__(self, widget: ScrollableTreeWidget):
        """Initialize behavior with widget reference.

        Args:
            widget: Widget implementing ScrollableTreeWidget protocol

        """
        self._widget = widget

        # Scroll state
        self._scroll_positions: dict[str, int] = {}
        self._expanded_items_per_file: dict[str, list[str]] = {}
        self._current_file_path: str | None = None
        self._pending_restore_timer_id: Any | None = None
        self._is_placeholder_mode: bool = False

    # =====================================
    # Path Dictionary Helpers
    # =====================================

    def _path_in_dict(self, path: str, path_dict: dict[str, Any]) -> bool:
        """Check if a path exists in dictionary using path-aware comparison.

        Args:
            path: Path to look for
            path_dict: Dictionary with path keys

        Returns:
            bool: True if path exists in dictionary

        """
        if not path or not path_dict:
            return False

        # First try direct lookup (fastest)
        if path in path_dict:
            return True

        # If not found, try normalized path comparison
        return any(paths_equal(path, existing_path) for existing_path in path_dict)

    def _get_from_path_dict(self, path: str, path_dict: dict[str, Any]) -> Any:
        """Get value from dictionary using path-aware comparison.

        Args:
            path: Path key to look for
            path_dict: Dictionary with path keys

        Returns:
            Any: Value if found, None otherwise

        """
        if not path or not path_dict:
            return None

        # First try direct lookup (fastest)
        if path in path_dict:
            return path_dict[path]

        # If not found, try normalized path comparison
        for existing_path, value in path_dict.items():
            if paths_equal(path, existing_path):
                return value

        return None

    def _set_in_path_dict(self, path: str, value: Any, path_dict: dict[str, Any]) -> None:
        """Set value in dictionary using path-aware key management.

        Args:
            path: Path key to set
            value: Value to set
            path_dict: Dictionary with path keys

        """
        if not path:
            return

        # Remove any existing equivalent paths first
        keys_to_remove = []
        for existing_path in path_dict:
            if paths_equal(path, existing_path):
                keys_to_remove.append(existing_path)

        for key in keys_to_remove:
            del path_dict[key]

        # Set with the new path
        path_dict[path] = value

    def _remove_from_path_dict(self, path: str, path_dict: dict[str, Any]) -> bool:
        """Remove path from dictionary using path-aware comparison.

        Args:
            path: Path key to remove
            path_dict: Dictionary with path keys

        Returns:
            bool: True if something was removed

        """
        if not path or not path_dict:
            return False

        removed = False
        keys_to_remove = []

        # Find all equivalent paths
        for existing_path in path_dict:
            if paths_equal(path, existing_path):
                keys_to_remove.append(existing_path)

        # Remove them
        for key in keys_to_remove:
            del path_dict[key]
            removed = True

        return removed

    # =====================================
    # File State Management
    # =====================================

    def set_current_file_path(self, file_path: str) -> None:
        """Set the current file path and manage scroll position restoration."""
        # If it's the same file, don't do anything
        if paths_equal(self._current_file_path, file_path):
            return

        # Save current file state before switching
        self._save_current_file_state()

        # Update current file (normalize for consistent cache lookups)
        previous_file_path = self._current_file_path
        self._current_file_path = normalize_path(file_path) if file_path else None

        # Load state for the new file
        self._load_file_state(file_path, previous_file_path)

    def _save_current_file_state(self) -> None:
        """Save the current file's state (scroll position, expanded items)."""
        if not self._current_file_path:
            return

        # Save scroll position
        self._save_current_scroll_position()

        # Save expanded state
        model = self._widget.model()
        if model:
            expanded_items = []
            for i in range(model.rowCount()):
                index = model.index(i, 0)
                if self._widget.isExpanded(index):
                    expanded_items.append(index.data())
            self._expanded_items_per_file[self._current_file_path] = expanded_items

    def _load_file_state(self, file_path: str, _previous_file_path: str) -> None:
        """Load the state for a specific file with improved performance."""
        if not file_path:
            return

        # Load expanded state
        expanded_items = self._expanded_items_per_file.get(file_path, [])
        model = self._widget.model()
        if model and expanded_items:
            for i in range(model.rowCount()):
                index = model.index(i, 0)
                if index.data() in expanded_items:
                    self._widget.expand(index)

        # Restore scroll position immediately
        self._restore_scroll_position_for_current_file()

    # =====================================
    # Scroll Position Management
    # =====================================

    def _save_current_scroll_position(self) -> None:
        """Save the current scroll position for the current file."""
        if self._current_file_path and not self._is_placeholder_mode:
            scroll_value = self._widget.verticalScrollBar().value()
            self._scroll_positions[self._current_file_path] = scroll_value

    def _restore_scroll_position_for_current_file(self) -> None:
        """Restore the scroll position for the current file with improved UX."""
        if not self._current_file_path or self._is_placeholder_mode:
            return

        scrollbar = self._widget.verticalScrollBar()

        # Check if this is the first time viewing this file
        if self._current_file_path not in self._scroll_positions:
            # First time viewing - go to top immediately (no animation for better UX)
            scrollbar.setValue(0)
            self._scroll_positions[self._current_file_path] = 0
        else:
            # Restore saved position
            saved_position = self._scroll_positions[self._current_file_path]

            # Validate scroll position against current content
            max_scroll = scrollbar.maximum()
            valid_position = max(0, min(saved_position, max_scroll))

            # Apply immediately for better responsiveness
            scrollbar.setValue(valid_position)

        # Clean up the timer
        if self._pending_restore_timer_id is not None:
            self._pending_restore_timer_id = None

    def _smooth_scroll_to_position(self, target_position: int) -> None:
        """Immediate scroll to position for better performance."""
        scrollbar = self._widget.verticalScrollBar()
        scrollbar.setValue(target_position)

    def _apply_scroll_position_immediately(self, position: int) -> None:
        """Apply scroll position immediately without animation.

        Args:
            position: Target scroll position

        """
        scrollbar = self._widget.verticalScrollBar()
        max_scroll = scrollbar.maximum()
        valid_position = max(0, min(position, max_scroll))
        scrollbar.setValue(valid_position)

    # =====================================
    # Scroll Memory Management
    # =====================================

    def clear_scroll_memory(self) -> None:
        """Clear all saved scroll positions (useful when changing folders)."""
        self._scroll_positions.clear()
        self._current_file_path = None

        # Cancel any pending restore
        if self._pending_restore_timer_id is not None:
            self._pending_restore_timer_id = None

    def restore_scroll_after_expand(self) -> None:
        """Trigger scroll position restore after expandAll() has completed."""
        if self._current_file_path and not self._is_placeholder_mode:
            # Use a shorter delay since we now do immediate restoration in setModel
            if self._pending_restore_timer_id is not None:
                self._pending_restore_timer_id = None

            self._pending_restore_timer_id = schedule_ui_update(
                self._restore_scroll_position_for_current_file, delay=25
            )

    def set_placeholder_mode(self, enabled: bool) -> None:
        """Set placeholder mode state.

        Args:
            enabled: True to enable placeholder mode, False to disable

        """
        self._is_placeholder_mode = enabled


__all__ = ["MetadataScrollBehavior", "ScrollableTreeWidget"]
