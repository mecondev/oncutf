"""Module: thumbnail_store.py.

Author: Michael Economou
Date: 2026-01-16

Database operations for thumbnail cache index and manual order persistence.

Provides:
- ThumbnailStore: SQLite operations for thumbnail metadata

Tables:
- thumbnail_cache: Index of cached thumbnails (file identity, cache path, video frame time)
- thumbnail_order: Manual ordering per folder (persists across sessions)

Schema managed by migrations.py (v4 -> v5).
"""

import contextlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ThumbnailStore:
    """Database operations for thumbnail cache and manual order.

    Responsibilities:
    - Query cached thumbnail metadata
    - Save cache entries after generation
    - Invalidate entries when files change
    - Load/save manual folder ordering
    - Cleanup orphaned entries

    Attributes:
        _connection: SQLite connection (managed by DatabaseManager)

    """

    def __init__(self, connection: sqlite3.Connection):
        """Initialize thumbnail store with database connection.

        Args:
            connection: Active SQLite connection

        """
        self._connection = connection
        logger.debug("[ThumbnailStore] Initialized")

    def _is_connection_open(self) -> bool:
        """Check if database connection is open.

        Returns:
            True if connection is open and usable

        """
        try:
            # Try to execute a simple query
            self._connection.execute("SELECT 1")
        except (sqlite3.ProgrammingError, AttributeError):
            return False
        else:
            return True

    def get_cached_entry(self, file_path: str, mtime: float) -> dict[str, Any] | None:
        """Retrieve cached thumbnail metadata for a file.

        Args:
            file_path: Absolute file path
            mtime: File modification time

        Returns:
            Dict with cache metadata if found:
            {
                'cache_filename': str,
                'file_size': int,
                'video_frame_time': float | None,
                'created_at': str
            }
            None if not cached or file changed

        """
        # Check if connection is still open
        if not self._is_connection_open():
            logger.debug(
                "[ThumbnailStore] Database closed, skipping cache lookup for: %s",
                Path(file_path).name,
            )
            return None

        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT cache_filename, file_size, video_frame_time, created_at
            FROM thumbnail_cache
            WHERE file_path = ? AND file_mtime = ?
            """,
            (file_path, mtime),
        )

        row = cursor.fetchone()
        if not row:
            logger.debug("[ThumbnailStore] No cache entry for: %s", Path(file_path).name)
            return None

        entry = {
            "cache_filename": row[0],
            "file_size": row[1],
            "video_frame_time": row[2],
            "created_at": row[3],
        }

        logger.debug(
            "[ThumbnailStore] Found cache entry: %s -> %s",
            Path(file_path).name,
            entry["cache_filename"],
        )
        return entry

    def save_cache_entry(
        self,
        folder_path: str,
        file_path: str,
        file_mtime: float,
        file_size: int,
        cache_filename: str,
        video_frame_time: float | None = None,
    ) -> bool:
        """Save thumbnail cache metadata to database.

        Args:
            folder_path: Parent folder path
            file_path: Absolute file path
            file_mtime: File modification time
            file_size: File size in bytes
            cache_filename: Cached thumbnail filename (hash.png)
            video_frame_time: Video frame timestamp (seconds) if applicable

        Returns:
            True if saved successfully

        """
        # Check if connection is still open (may be closed during shutdown)
        if not self._is_connection_open():
            logger.debug(
                "[ThumbnailStore] Database closed, skipping cache save for: %s",
                Path(file_path).name,
            )
            return False

        cursor = self._connection.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO thumbnail_cache
                (folder_path, file_path, file_mtime, file_size, cache_filename, video_frame_time)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    folder_path,
                    file_path,
                    file_mtime,
                    file_size,
                    cache_filename,
                    video_frame_time,
                ),
            )
            self._connection.commit()

            logger.debug(
                "[ThumbnailStore] Saved cache entry: %s -> %s",
                Path(file_path).name,
                cache_filename,
            )
        except sqlite3.Error as e:
            # Rollback to prevent "cannot commit - no transaction is active" errors
            with contextlib.suppress(sqlite3.Error):
                self._connection.rollback()

            logger.error(
                "[ThumbnailStore] Failed to save cache entry for %s: %s",
                Path(file_path).name,
                e,
            )
            return False
        else:
            return True

    def invalidate_entry(self, file_path: str) -> bool:
        """Remove cached thumbnail metadata for a file.

        Args:
            file_path: Absolute file path

        Returns:
            True if entry was removed

        """
        cursor = self._connection.cursor()

        try:
            cursor.execute(
                """
                DELETE FROM thumbnail_cache
                WHERE file_path = ?
                """,
                (file_path,),
            )
            self._connection.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.debug("[ThumbnailStore] Invalidated entry: %s", Path(file_path).name)
        except sqlite3.Error as e:
            logger.error("[ThumbnailStore] Failed to invalidate entry: %s", e)
            return False
        else:
            return deleted

    def get_folder_order(self, folder_path: str) -> list[str] | None:
        """Retrieve manual file order for a folder.

        Args:
            folder_path: Absolute folder path

        Returns:
            Ordered list of file paths, or None if no manual order saved

        """
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT file_paths
            FROM thumbnail_order
            WHERE folder_path = ?
            """,
            (folder_path,),
        )

        row = cursor.fetchone()
        if not row:
            logger.debug(
                "[ThumbnailStore] No manual order for folder: %s",
                Path(folder_path).name,
            )
            return None

        try:
            file_paths: list[str] = json.loads(row[0])
            logger.debug(
                "[ThumbnailStore] Loaded manual order: %d files in %s",
                len(file_paths),
                Path(folder_path).name,
            )
        except json.JSONDecodeError as e:
            logger.error("[ThumbnailStore] Failed to decode file_paths JSON: %s", e)
            return None
        else:
            return file_paths

    def save_folder_order(self, folder_path: str, file_paths: list[str]) -> bool:
        """Save manual file order for a folder.

        Args:
            folder_path: Absolute folder path
            file_paths: Ordered list of file paths

        Returns:
            True if saved successfully

        """
        cursor = self._connection.cursor()

        try:
            file_paths_json = json.dumps(file_paths)
            cursor.execute(
                """
                INSERT OR REPLACE INTO thumbnail_order
                (folder_path, file_paths, updated_at)
                VALUES (?, ?, datetime('now'))
                """,
                (folder_path, file_paths_json),
            )
            self._connection.commit()

            logger.info(
                "[ThumbnailStore] Saved manual order: %d files in %s",
                len(file_paths),
                Path(folder_path).name,
            )
        except (sqlite3.Error, TypeError) as e:
            logger.error("[ThumbnailStore] Failed to save folder order: %s", e)
            return False
        else:
            return True

    def clear_folder_order(self, folder_path: str) -> bool:
        """Clear manual order for a folder (return to automatic sort).

        Args:
            folder_path: Absolute folder path

        Returns:
            True if entry was removed

        """
        cursor = self._connection.cursor()

        try:
            cursor.execute(
                """
                DELETE FROM thumbnail_order
                WHERE folder_path = ?
                """,
                (folder_path,),
            )
            self._connection.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(
                    "[ThumbnailStore] Cleared manual order for: %s",
                    Path(folder_path).name,
                )
        except sqlite3.Error as e:
            logger.error("[ThumbnailStore] Failed to clear folder order: %s", e)
            return False
        else:
            return deleted

    def cleanup_orphaned_entries(self, valid_folder_paths: list[str]) -> int:
        """Remove cache entries for folders that no longer exist.

        Args:
            valid_folder_paths: List of currently valid folder paths

        Returns:
            Number of entries removed

        """
        cursor = self._connection.cursor()

        try:
            # Build placeholders for SQL IN clause
            placeholders = ",".join("?" * len(valid_folder_paths))
            query = f"""
                DELETE FROM thumbnail_cache
                WHERE folder_path NOT IN ({placeholders})
            """

            cursor.execute(query, valid_folder_paths)
            cache_deleted = cursor.rowcount

            cursor.execute(
                f"""
                DELETE FROM thumbnail_order
                WHERE folder_path NOT IN ({placeholders})
                """,
                valid_folder_paths,
            )
            order_deleted = cursor.rowcount

            self._connection.commit()

            total_deleted = cache_deleted + order_deleted
            if total_deleted > 0:
                logger.info(
                    "[ThumbnailStore] Cleaned up %d orphaned entries (%d cache, %d order)",
                    total_deleted,
                    cache_deleted,
                    order_deleted,
                )
        except sqlite3.Error as e:
            logger.error("[ThumbnailStore] Failed to cleanup orphaned entries: %s", e)
            return 0
        else:
            return total_deleted

    def get_cache_stats(self) -> dict[str, int]:
        """Get statistics about thumbnail cache usage.

        Returns:
            Dict with cache statistics:
            {
                'total_entries': int,
                'total_folders': int,
                'total_manual_orders': int
            }

        """
        cursor = self._connection.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM thumbnail_cache")
            total_entries = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT folder_path) FROM thumbnail_cache")
            total_folders = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM thumbnail_order")
            total_manual_orders = cursor.fetchone()[0]

            stats = {
                "total_entries": total_entries,
                "total_folders": total_folders,
                "total_manual_orders": total_manual_orders,
            }

            logger.debug("[ThumbnailStore] Cache stats: %s", stats)
        except sqlite3.Error as e:
            logger.error("[ThumbnailStore] Failed to get cache stats: %s", e)
            return {"total_entries": 0, "total_folders": 0, "total_manual_orders": 0}
        else:
            return stats
