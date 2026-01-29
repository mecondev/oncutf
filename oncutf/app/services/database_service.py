"""Database service for file color operations.

Author: Michael Economou
Date: 2026-01-24

This service provides a clean interface to database operations,
isolating UI components from direct database dependencies.

Architecture:
- UI components → DatabaseService → Core database manager
- No direct imports of database classes in UI layer
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from oncutf.app.ports.infra_protocols import DatabaseManagerProtocol


# Factory function - registered during bootstrap
_database_manager_factory: Any = None


def register_database_manager_factory(factory: Any) -> None:
    """Register factory for creating database manager instances."""
    global _database_manager_factory
    _database_manager_factory = factory


class DatabaseService:
    """Service for database operations.

    This service wraps database manager and provides a clean
    interface for UI components to perform database operations
    without directly importing database classes.

    Usage:
        service = DatabaseService()
        service.set_file_color(file_path, color_hex)
        color = service.get_file_color(file_path)
    """

    def __init__(self) -> None:
        """Initialize database service."""
        self._db_manager: DatabaseManagerProtocol | None = None

    def _get_db_manager(self) -> DatabaseManagerProtocol | None:
        """Get database manager instance (lazy loading via factory)."""
        if self._db_manager is None and _database_manager_factory is not None:
            self._db_manager = _database_manager_factory()
        return self._db_manager

    def set_file_color(self, file_path: str, color_hex: str | None) -> bool:
        """Set color for a file.

        Args:
            file_path: Path to the file
            color_hex: Hex color code (e.g., "#FF0000") or None to clear

        Returns:
            True if successful

        """
        db_manager = self._get_db_manager()
        if not db_manager:
            return False

        try:
            if hasattr(db_manager, "set_file_color"):
                result = db_manager.set_file_color(file_path, color_hex)
                return bool(result) if result is not None else False
            return False
        except Exception:
            return False

    def get_file_color(self, file_path: str) -> str | None:
        """Get color for a file.

        Args:
            file_path: Path to the file

        Returns:
            Hex color code or None if not set

        """
        db_manager = self._get_db_manager()
        if not db_manager:
            return None

        try:
            if hasattr(db_manager, "get_file_color"):
                result = db_manager.get_file_color(file_path)
                return str(result) if result is not None else None
            return None
        except Exception:
            return None

    def get_files_by_color(self, color_hex: str) -> list[str]:
        """Get all files with a specific color.

        Args:
            color_hex: Hex color code to search for

        Returns:
            List of file paths with that color

        """
        db_manager = self._get_db_manager()
        if not db_manager:
            return []

        try:
            if hasattr(db_manager, "get_files_by_color"):
                return cast("list[str]", db_manager.get_files_by_color(color_hex))
            return []
        except Exception:
            return []

    def execute_query(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """Execute a database query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query result

        """
        db_manager = self._get_db_manager()
        if not db_manager:
            return None

        try:
            if hasattr(db_manager, "execute_query"):
                return db_manager.execute_query(query, params)
            return None
        except Exception:
            return None


# Singleton instance
_database_service: DatabaseService | None = None


def get_database_service() -> DatabaseService:
    """Get the global DatabaseService instance.

    Returns:
        Singleton DatabaseService instance

    """
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service
