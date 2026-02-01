"""Module: hash_store.py.

Author: Michael Economou
Date: 2026-01-01

Hash storage and retrieval for database operations.
Handles all file hash CRUD operations.
"""

import os
import sqlite3
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.infra.db.path_store import PathStore

logger = get_cached_logger(__name__)


class HashStore:
    """Manages file hash storage and retrieval in the database."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        path_store: "PathStore",
        write_lock: threading.RLock,
    ):
        """Initialize HashStore with a database connection and path store.

        Args:
            connection: Active SQLite database connection
            path_store: PathStore instance for path management
            write_lock: Lock for thread-safe database access

        """
        self.connection = connection
        self.path_store = path_store
        self._write_lock = write_lock

    def store_hash(self, file_path: str, hash_value: str, algorithm: str = "CRC32") -> bool:
        """Store file hash."""
        try:
            # Validate inputs
            if not file_path or not hash_value:
                logger.warning(
                    "[HashStore] Invalid input: file_path=%s, hash_value=%s",
                    file_path,
                    hash_value,
                )
                return False

            # Check for null bytes (SQLite doesn't support them)
            if "\x00" in file_path or "\x00" in hash_value:
                logger.warning(
                    "[HashStore] Null byte detected in path or hash, skipping: %s",
                    file_path,
                )
                return False

            with self._write_lock:
                path_id = self.path_store.get_or_create_path_id(file_path)

                # Get current file size
                file_size = None
                try:
                    if Path(file_path).exists():
                        file_size = Path(file_path).stat().st_size
                except OSError:
                    pass

                cursor = self.connection.cursor()

                # Remove existing hash for this path and algorithm
                cursor.execute(
                    """
                    DELETE FROM file_hashes
                    WHERE path_id = ? AND algorithm = ?
                """,
                    (path_id, algorithm),
                )

                # Store new hash
                cursor.execute(
                    """
                    INSERT INTO file_hashes
                    (path_id, algorithm, hash_value, file_size_at_hash)
                    VALUES (?, ?, ?, ?)
                """,
                    (path_id, algorithm, hash_value, file_size),
                )

                # Commit the transaction
                self.connection.commit()

                logger.debug(
                    "[HashStore] Stored %s hash for: %s",
                    algorithm,
                    Path(file_path).name,
                )
        except sqlite3.OperationalError as e:
            # Suppress errors during shutdown/cancellation
            logger.debug("[HashStore] Database locked/closing during store: %s", e)
            return False
        except Exception as e:
            logger.exception("[HashStore] Error storing hash for %s", file_path)
            return False
        else:
            return True

    def get_hash(self, file_path: str, algorithm: str = "CRC32") -> str | None:
        """Retrieve file hash."""
        try:
            # Validate input
            if not file_path:
                return None

            # Check for null bytes
            if "\x00" in file_path:
                logger.warning("[HashStore] Null byte detected in path, skipping: %s", file_path)
                return None

            with self._write_lock:
                path_id = self.path_store.get_path_id(file_path)
                if not path_id:
                    return None

                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    SELECT hash_value FROM file_hashes
                    WHERE path_id = ? AND algorithm = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """,
                    (path_id, algorithm),
                )

                row = cursor.fetchone()
                return row["hash_value"] if row else None

        except sqlite3.OperationalError as e:
            # Suppress errors during shutdown/cancellation
            # These happen when the connection is being closed by another thread
            logger.debug("[HashStore] Database locked/closing for %s: %s", file_path, e)
            return None
        except Exception as e:
            logger.exception("[HashStore] Error retrieving hash for %s", file_path)
            return None

    def has_hash(self, file_path: str, algorithm: str = "CRC32") -> bool:
        """Check if hash exists for a file."""
        norm_path = self.path_store.normalize_path(file_path)

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT 1 FROM file_hashes h
            JOIN file_paths p ON h.path_id = p.id
            WHERE p.file_path = ? AND h.algorithm = ?
            LIMIT 1
        """,
            (norm_path, algorithm),
        )

        return cursor.fetchone() is not None

    def get_files_with_hash_batch(
        self, file_paths: list[str], algorithm: str = "CRC32"
    ) -> list[str]:
        """Get all files from the list that have a hash stored using batch database query."""
        if not file_paths:
            return []

        # Normalize all paths
        norm_paths = [self.path_store.normalize_path(path) for path in file_paths]

        cursor = self.connection.cursor()

        # Create placeholders for the IN clause
        placeholders = ",".join(["?" for _ in norm_paths])

        cursor.execute(
            f"""
            SELECT p.file_path FROM file_paths p
            JOIN file_hashes h ON h.path_id = p.id
            WHERE p.file_path IN ({placeholders}) AND h.algorithm = ?
        """,
            [*norm_paths, algorithm],
        )

        # Get all file paths that have hashes
        files_with_hash = [row["file_path"] for row in cursor.fetchall()]

        logger.debug(
            "[HashStore] Batch hash check: %d/%d files have %s hashes",
            len(files_with_hash),
            len(file_paths),
            algorithm,
        )

        return files_with_hash
