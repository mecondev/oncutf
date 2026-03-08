"""MetadataUIBridge -- protocol decoupling MetadataLoader from direct UI access.

MetadataLoader (core layer) must not access parent_window widgets directly.
This protocol defines the UI operations that MetadataLoader needs; the Qt
implementation lives in ``oncutf.ui.adapters.metadata_ui_bridge_qt``.

Author: Michael Economou
Date: 2026-03-08
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MetadataUIBridge(Protocol):
    """Interface for UI operations needed by MetadataLoader."""

    @property
    def dialog_parent(self) -> Any:
        """Return parent widget reference for dialog creation."""
        ...

    def cache_get_entries_batch(self, paths: list[str]) -> dict[str, Any]:
        """Get cache entries for multiple paths at once."""
        ...

    def cache_get_entry(self, path: str) -> Any:
        """Get single cache entry by normalized path."""
        ...

    def cache_set(self, path: str, data: dict[str, Any], *, is_extended: bool) -> None:
        """Store metadata in cache."""
        ...

    def refresh_model_icons(self) -> None:
        """Refresh file model icons after metadata update."""
        ...

    def emit_data_changed(self, full_path: str) -> None:
        """Emit dataChanged signal for a specific file in the model."""
        ...

    def get_selection_count(self) -> int:
        """Get current file selection count."""
        ...

    def display_metadata(
        self, metadata: dict[str, Any] | None, selection_count: int, context: str
    ) -> None:
        """Display metadata in the tree view respecting selection rules."""
        ...

    def set_metadata_status(
        self,
        message: str,
        *,
        operation_type: str = "",
        file_count: int = 0,
        auto_reset: bool = False,
    ) -> None:
        """Update metadata status bar."""
        ...


class NullMetadataUIBridge:
    """No-op bridge for headless / test usage."""

    @property
    def dialog_parent(self) -> None:
        """Return None -- no parent widget available."""
        return None

    def cache_get_entries_batch(self, paths: list[str]) -> dict[str, Any]:
        """Return empty dict -- no cache available."""
        return {}

    def cache_get_entry(self, path: str) -> Any:
        """Return None -- no cache available."""
        return None

    def cache_set(self, path: str, data: dict[str, Any], *, is_extended: bool) -> None:
        """No-op -- no cache available."""

    def refresh_model_icons(self) -> None:
        """No-op -- no model available."""

    def emit_data_changed(self, full_path: str) -> None:
        """No-op -- no model available."""

    def get_selection_count(self) -> int:
        """Return 0 -- no selection available."""
        return 0

    def display_metadata(
        self, metadata: dict[str, Any] | None, selection_count: int, context: str
    ) -> None:
        """No-op -- no tree view available."""

    def set_metadata_status(
        self,
        message: str,
        *,
        operation_type: str = "",
        file_count: int = 0,
        auto_reset: bool = False,
    ) -> None:
        """No-op -- no status manager available."""
