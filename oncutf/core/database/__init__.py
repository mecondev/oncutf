"""Database operations module.

This module provides database management functionality including:
- DatabaseManager: Main database operations and migrations

Author: Michael Economou
Date: 2025-12-20
"""

from __future__ import annotations

from oncutf.core.database.database_manager import DatabaseManager

__all__ = [
    "DatabaseManager",
    "initialize_database",
]


# Singleton instance
_db_manager_instance: DatabaseManager | None = None


def initialize_database(db_path: str | None = None) -> DatabaseManager:
    """Initialize database manager with custom path (backward compatibility).

    Args:
        db_path: Optional custom database path

    Returns:
        DatabaseManager instance

    """
    global _db_manager_instance
    _db_manager_instance = DatabaseManager(db_path)
    return _db_manager_instance
