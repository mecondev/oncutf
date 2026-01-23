"""Module: session_state_manager.py.

Author: Michael Economou
Date: 2026-01-15

High-level session state management with typed accessors.

This manager provides a clean API for session state operations,
wrapping the low-level SessionStateStore with typed methods.

Usage:
    from oncutf.core.session_state_manager import get_session_state_manager

    manager = get_session_state_manager()
    manager.set_sort_column(3)
    column = manager.get_sort_column()
"""

from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


# Default values for session state
SESSION_STATE_DEFAULTS = {
    "sort_column": 2,  # Filename column
    "sort_order": 0,   # Ascending
    "last_folder": "",
    "recursive_mode": False,
    "column_order": None,
    "columns_locked": False,
    "file_table_column_widths": {},
    "file_table_columns": {},
    "recent_folders": [],
    "metadata_tree_column_widths": {},
}


class SessionStateManager:
    """High-level session state manager with typed accessors.

    Provides atomic, type-safe access to session state stored in SQLite.
    All operations are transaction-safe and survive application crashes.
    """

    def __init__(self):
        """Initialize SessionStateManager."""
        self._db_manager = None
        logger.debug("[SessionStateManager] Initialized")

    @property
    def db_manager(self):
        """Lazy-load database manager to avoid circular imports."""
        if self._db_manager is None:
            from oncutf.core.database.database_manager import get_database_manager
            self._db_manager = get_database_manager()
        return self._db_manager

    # ====================================================================
    # Sort State
    # ====================================================================

    def get_sort_column(self) -> int:
        """Get current sort column index."""
        return self.db_manager.get_session_state(
            "sort_column",
            SESSION_STATE_DEFAULTS["sort_column"]
        )

    def set_sort_column(self, column: int) -> bool:
        """Set sort column index."""
        return self.db_manager.set_session_state("sort_column", column)

    def get_sort_order(self) -> int:
        """Get current sort order (0=Ascending, 1=Descending)."""
        return self.db_manager.get_session_state(
            "sort_order",
            SESSION_STATE_DEFAULTS["sort_order"]
        )

    def set_sort_order(self, order: int) -> bool:
        """Set sort order (0=Ascending, 1=Descending)."""
        return self.db_manager.set_session_state("sort_order", order)

    def set_sort_state(self, column: int, order: int) -> bool:
        """Set both sort column and order atomically."""
        return self.db_manager.set_many_session_state({
            "sort_column": column,
            "sort_order": order,
        })

    # ====================================================================
    # Folder State
    # ====================================================================

    def get_last_folder(self) -> str:
        """Get last opened folder path."""
        return self.db_manager.get_session_state(
            "last_folder",
            SESSION_STATE_DEFAULTS["last_folder"]
        )

    def set_last_folder(self, folder: str) -> bool:
        """Set last opened folder path."""
        return self.db_manager.set_session_state("last_folder", folder)

    def get_recursive_mode(self) -> bool:
        """Get recursive mode setting."""
        return self.db_manager.get_session_state(
            "recursive_mode",
            SESSION_STATE_DEFAULTS["recursive_mode"]
        )

    def set_recursive_mode(self, recursive: bool) -> bool:
        """Set recursive mode setting."""
        return self.db_manager.set_session_state("recursive_mode", recursive)

    # ====================================================================
    # Column State
    # ====================================================================

    def get_column_order(self) -> list[str] | None:
        """Get column order list."""
        return self.db_manager.get_session_state(
            "column_order",
            SESSION_STATE_DEFAULTS["column_order"]
        )

    def set_column_order(self, order: list[str]) -> bool:
        """Set column order list."""
        return self.db_manager.set_session_state("column_order", order)

    def get_columns_locked(self) -> bool:
        """Get columns locked setting."""
        return self.db_manager.get_session_state(
            "columns_locked",
            SESSION_STATE_DEFAULTS["columns_locked"]
        )

    def set_columns_locked(self, locked: bool) -> bool:
        """Set columns locked setting."""
        return self.db_manager.set_session_state("columns_locked", locked)

    def get_file_table_column_widths(self) -> dict[str, int]:
        """Get file table column widths."""
        return self.db_manager.get_session_state(
            "file_table_column_widths",
            SESSION_STATE_DEFAULTS["file_table_column_widths"]
        )

    def set_file_table_column_widths(self, widths: dict[str, int]) -> bool:
        """Set file table column widths."""
        return self.db_manager.set_session_state("file_table_column_widths", widths)

    def get_file_table_columns(self) -> dict[str, bool]:
        """Get file table column visibility."""
        return self.db_manager.get_session_state(
            "file_table_columns",
            SESSION_STATE_DEFAULTS["file_table_columns"]
        )

    def set_file_table_columns(self, columns: dict[str, bool]) -> bool:
        """Set file table column visibility."""
        return self.db_manager.set_session_state("file_table_columns", columns)

    # ====================================================================
    # Recent Folders
    # ====================================================================

    def get_recent_folders(self) -> list[str]:
        """Get recent folders list."""
        return self.db_manager.get_session_state(
            "recent_folders",
            SESSION_STATE_DEFAULTS["recent_folders"]
        )

    def set_recent_folders(self, folders: list[str]) -> bool:
        """Set recent folders list."""
        return self.db_manager.set_session_state("recent_folders", folders)

    def add_recent_folder(self, folder: str, max_recent: int = 10) -> bool:
        """Add folder to recent folders list."""
        recent = self.get_recent_folders()

        if folder in recent:
            recent.remove(folder)

        recent.insert(0, folder)

        if len(recent) > max_recent:
            recent = recent[:max_recent]

        return self.set_recent_folders(recent)

    # ====================================================================
    # Metadata Tree State
    # ====================================================================

    def get_metadata_tree_column_widths(self) -> dict[str, int]:
        """Get metadata tree column widths."""
        return self.db_manager.get_session_state(
            "metadata_tree_column_widths",
            SESSION_STATE_DEFAULTS["metadata_tree_column_widths"]
        )

    def set_metadata_tree_column_widths(self, widths: dict[str, int]) -> bool:
        """Set metadata tree column widths."""
        return self.db_manager.set_session_state("metadata_tree_column_widths", widths)

    # ====================================================================
    # Bulk Operations
    # ====================================================================

    def get_all(self) -> dict[str, Any]:
        """Get all session state values with defaults for missing keys."""
        stored = self.db_manager.get_all_session_state()
        # Merge with defaults
        result = SESSION_STATE_DEFAULTS.copy()
        result.update(stored)
        return result

    def set_all(self, data: dict[str, Any]) -> bool:
        """Set multiple session state values atomically."""
        return self.db_manager.set_many_session_state(data)

    def reset_to_defaults(self) -> bool:
        """Reset all session state to default values."""
        return self.db_manager.set_many_session_state(SESSION_STATE_DEFAULTS)


# ====================================================================
# Module-level singleton
# ====================================================================

_session_state_manager: SessionStateManager | None = None


def get_session_state_manager() -> SessionStateManager:
    """Get singleton SessionStateManager instance.

    Returns:
        SessionStateManager instance

    """
    global _session_state_manager
    if _session_state_manager is None:
        _session_state_manager = SessionStateManager()
    return _session_state_manager
