"""Database operations module.

This module provides database management functionality.
NOTE: DatabaseManager moved to infra/db/database_manager.py

Author: Michael Economou
Date: 2025-12-20
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.infra.db.database_manager import DatabaseManager as _DatabaseManager

__all__ = [
    "initialize_database",
]


def initialize_database(db_path: str | None = None) -> _DatabaseManager:
    """Initialize database manager with custom path (backward compatibility).

    Args:
        db_path: Optional custom database path

    Returns:
        DatabaseManager instance

    """
    from oncutf.infra.db.database_manager import DatabaseManager

    return DatabaseManager(db_path)
