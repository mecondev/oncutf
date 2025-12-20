"""
Database operations module.

This module provides database management functionality including:
- DatabaseManager: Main database operations and migrations
- OptimizedDatabaseManager: Performance-optimized queries

Author: Michael Economou
Date: 2025-12-20
"""

from __future__ import annotations

from oncutf.core.database.database_manager import DatabaseManager
from oncutf.core.database.optimized_database_manager import OptimizedDatabaseManager

__all__ = [
    "DatabaseManager",
    "OptimizedDatabaseManager",
]
