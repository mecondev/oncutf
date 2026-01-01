"""Module: path_store.py

Author: Michael Economou
Date: 2026-01-01

Path management for database operations.
Handles all file path CRUD operations.
"""

import os
import sqlite3
from datetime import datetime

from oncutf.utils.filesystem.path_normalizer import normalize_path
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class PathStore:
    """Manages file path storage and retrieval in the database."""

    def __init__(self, connection: sqlite3.Connection):
        """Initialize PathStore with a database connection.

        Args:
            connection: Active SQLite database connection

        """
        self.connection = connection

    def get_or_create_path_id(self, file_path: str) -> int:
        """Get path_id for a file, creating record if needed.

        This is the core method that ensures every file path has an ID.
        All other operations use this ID to reference files.

        Args:
            file_path: Path to the file

        Returns:
            path_id for the file

        """
        norm_path = self.normalize_path(file_path)
        filename = os.path.basename(norm_path)

        cursor = self.connection.cursor()

        # Try to get existing path_id
        cursor.execute("SELECT id FROM file_paths WHERE file_path = ?", (norm_path,))
        row = cursor.fetchone()
        if row:
            return row["id"]

        # Create new path record
        file_size = None
        modified_time = None
        try:
            if os.path.exists(norm_path):
                stat = os.stat(norm_path)
                file_size = stat.st_size
                modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
        except OSError:
            pass

        cursor.execute(
            """
            INSERT INTO file_paths
            (file_path, filename, file_size, modified_time, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
            (norm_path, filename, file_size, modified_time),
        )

        # Make sure to commit the transaction
        self.connection.commit()

        path_id = cursor.lastrowid
        if path_id is None:
            raise RuntimeError(f"Failed to create path record for: {norm_path}")

        return path_id

    def normalize_path(self, file_path: str) -> str:
        """Use the central normalize_path function."""
        return normalize_path(file_path)

    def get_path_id(self, file_path: str) -> int | None:
        """Get path_id for a file without creating it."""
        norm_path = self.normalize_path(file_path)

        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM file_paths WHERE file_path = ?", (norm_path,))
        row = cursor.fetchone()
        return row["id"] if row else None

    def update_file_path(self, old_path: str, new_path: str) -> bool:
        """Update file path in database (e.g., after rename operation).
        This preserves all associated data (metadata, hashes, color_tag, etc.)
        by keeping the same path_id.

        Args:
            old_path: Original file path
            new_path: New file path

        Returns:
            True if successful, False otherwise

        """
        try:
            old_norm_path = self.normalize_path(old_path)
            new_norm_path = self.normalize_path(new_path)
            new_filename = os.path.basename(new_norm_path)

            # Get file size and modified time for the new path
            file_size = None
            modified_time = None
            try:
                if os.path.exists(new_norm_path):
                    stat = os.stat(new_norm_path)
                    file_size = stat.st_size
                    modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except OSError:
                pass

            cursor = self.connection.cursor()

            # Update the path while preserving all other data (including color_tag)
            cursor.execute(
                """
                UPDATE file_paths
                SET file_path = ?, filename = ?, file_size = ?, modified_time = ?, updated_at = CURRENT_TIMESTAMP
                WHERE file_path = ?
                """,
                (new_norm_path, new_filename, file_size, modified_time, old_norm_path),
            )
            self.connection.commit()

            if cursor.rowcount > 0:
                logger.debug(
                    "[PathStore] Updated file path: %s -> %s",
                    os.path.basename(old_path),
                    os.path.basename(new_path),
                )
                return True
            else:
                logger.debug(
                    "[PathStore] No record found to update for: %s",
                    old_path,
                )
                return False

        except Exception as e:
            logger.error(
                "[PathStore] Error updating file path from %s to %s: %s",
                old_path,
                new_path,
                e,
            )
            return False
