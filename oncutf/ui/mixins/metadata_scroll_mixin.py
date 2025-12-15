"""
Mixin for MetadataTreeView scroll position management and state persistence.

This mixin handles:
- Scroll position memory per file
- Expand/collapse state per file
- Path-aware dictionary operations for cross-platform compatibility
- Smooth scroll restoration

Author: Michael Economou
Date: 2025-12-08
"""

from typing import Any

from oncutf.utils.path_utils import paths_equal
from oncutf.utils.timer_manager import schedule_ui_update


class MetadataScrollMixin:
    """
    Mixin providing scroll position management for metadata tree view.

    This mixin manages per-file scroll positions and expanded item states,
    with intelligent restoration when switching between files.

    Attributes managed:
        _scroll_positions: dict[str, int] - Scroll positions per file path
        _expanded_items_per_file: dict[str, list[str]] - Expanded items per file
        _current_file_path: str | None - Currently displayed file path
        _pending_restore_timer_id: Any | None - Timer for delayed scroll restoration
        _is_placeholder_mode: bool - Whether view is in placeholder mode
    """

    # =====================================
    # Path Dictionary Helpers
    # =====================================

    def _path_in_dict(self, path: str, path_dict: dict[str, Any]) -> bool:
        """
        Check if a path exists in dictionary using path-aware comparison.

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
        """
        Get value from dictionary using path-aware comparison.

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
        """
        Set value in dictionary using path-aware key management.

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
        """
        Remove path from dictionary using path-aware comparison.

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
        from oncutf.utils.path_normalizer import normalize_path

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
        model = self.model()
        if model:
            expanded_items = []
            for i in range(model.rowCount()):
                index = model.index(i, 0)
                if self.isExpanded(index):
                    expanded_items.append(index.data())
            self._expanded_items_per_file[self._current_file_path] = expanded_items

    def _load_file_state(self, file_path: str, _previous_file_path: str) -> None:
        """Load the state for a specific file with improved performance."""
        if not file_path:
            return

        # Load expanded state
        expanded_items = self._expanded_items_per_file.get(file_path, [])
        model = self.model()
        if model and expanded_items:
            for i in range(model.rowCount()):
                index = model.index(i, 0)
                if index.data() in expanded_items:
                    self.expand(index)

        # Restore scroll position immediately
        self._restore_scroll_position_for_current_file()

    # =====================================
    # Scroll Position Management
    # =====================================

    def _save_current_scroll_position(self) -> None:
        """Save the current scroll position for the current file."""
        if self._current_file_path and not self._is_placeholder_mode:
            scroll_value = self.verticalScrollBar().value()
            self._scroll_positions[self._current_file_path] = scroll_value

    def _restore_scroll_position_for_current_file(self) -> None:
        """Restore the scroll position for the current file with improved UX."""
        if not self._current_file_path or self._is_placeholder_mode:
            return

        scrollbar = self.verticalScrollBar()

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
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(target_position)

    def _apply_scroll_position_immediately(self, position: int) -> None:
        """
        Apply scroll position immediately without animation.

        Args:
            position: Target scroll position
        """
        scrollbar = self.verticalScrollBar()
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

