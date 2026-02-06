"""Module: database_manager.py.

Author: Michael Economou
Date: 2026-01-01

Refactored database manager - orchestrates specialized store classes.

This is the main entry point for database operations. It delegates to:
- PathStore: file_paths table operations
- MetadataStore: file_metadata, categories, fields, color tags
- HashStore: file_hashes table operations
- migrations: Schema creation and migration functions

All public methods are preserved for backward compatibility.
"""

import contextlib
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from oncutf.infra.db.hash_store import HashStore
from oncutf.infra.db.metadata_store import MetadataStore
from oncutf.infra.db.migrations import create_indexes, create_schema, migrate_schema
from oncutf.infra.db.path_store import PathStore
from oncutf.infra.db.session_state_store import SessionStateStore
from oncutf.infra.db.thumbnail_store import ThumbnailStore
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

_FRESH_START_DONE = False


class DatabaseManager:
    """Enhanced database management with composition-based architecture.

    This orchestrator delegates to specialized store classes:
    - PathStore: file_paths table
    - MetadataStore: metadata, categories, fields, color tags
    - HashStore: file hashes

    Benefits:
    - Single responsibility per store
    - Easier testing and maintenance
    - Clear separation of concerns
    - Backward compatible API
    """

    SCHEMA_VERSION = 5

    def __init__(self, db_path: str | None = None):
        """Initialize database manager with store composition.

        Args:
        ----
            db_path: Optional custom database path

        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Use centralized path management
            from oncutf.utils.paths import AppPaths

            self.db_path = AppPaths.get_database_path()

        # Debug: Reset database if requested
        from oncutf.config import DEBUG_FRESH_START

        global _FRESH_START_DONE
        if DEBUG_FRESH_START and not _FRESH_START_DONE:
            if self.db_path.exists():
                logger.info(
                    "[DatabaseManager] DEBUG_FRESH_START enabled - deleting: %s",
                    self.db_path,
                )
                try:
                    # Force WAL checkpoint to merge WAL into main DB and release locks
                    try:
                        temp_conn = sqlite3.connect(str(self.db_path), timeout=1.0)
                        try:
                            # TRUNCATE mode: checkpoint + delete WAL file
                            temp_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                            temp_conn.commit()
                            logger.debug("[DatabaseManager] WAL checkpoint completed")
                        finally:
                            temp_conn.close()
                    except Exception as e:
                        logger.debug("[DatabaseManager] WAL checkpoint failed: %s", e)
                        # Continue anyway - WAL may not be enabled

                    # Delete WAL and SHM files first (they may hold locks)
                    wal_path = self.db_path.with_suffix(".db-wal")
                    shm_path = self.db_path.with_suffix(".db-shm")
                    if wal_path.exists():
                        wal_path.unlink()
                        logger.debug("[DatabaseManager] Deleted WAL file: %s", wal_path)
                    if shm_path.exists():
                        shm_path.unlink()
                        logger.debug("[DatabaseManager] Deleted SHM file: %s", shm_path)

                    # Now delete the main DB file
                    self.db_path.unlink()
                    logger.info("[DatabaseManager] Database files deleted successfully")
                except PermissionError as e:
                    logger.warning(
                        "[DatabaseManager] Could not delete database (file locked): %s - "
                        "Will use existing database. Close any DB browsers or other "
                        "oncutf instances and restart.",
                        e,
                    )
                except Exception:
                    logger.exception("[DatabaseManager] Failed to delete database")

            # Also reset JSON config to avoid stale references
            try:
                from oncutf.utils.paths import AppPaths

                config_path = AppPaths.get_config_path()
                if config_path.exists():
                    config_path.unlink()
                    logger.info("[DatabaseManager] Config file deleted for fresh start")
            except Exception:
                logger.exception("[DatabaseManager] Failed to delete config")

            # Also clean thumbnail cache to ensure fresh start
            try:
                import shutil

                from oncutf.utils.paths import AppPaths

                thumbnails_dir = AppPaths.get_thumbnails_dir()
                if thumbnails_dir.exists():
                    shutil.rmtree(thumbnails_dir)
                    thumbnails_dir.mkdir(parents=True, exist_ok=True)
                    logger.info("[DatabaseManager] Thumbnail cache cleared for fresh start")
            except Exception:
                logger.exception("[DatabaseManager] Failed to clear thumbnail cache")

            _FRESH_START_DONE = True
        # Thread safety lock for concurrent access from parallel workers
        self._write_lock = threading.RLock()

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Validate existing database before connecting
        if self.db_path.exists() and not self._validate_database_file():
            logger.warning(
                "[DatabaseManager] Corrupted database detected, backing up and recreating"
            )
            self._backup_corrupted_database()

        # Create connection with error handling
        try:
            self._conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA synchronous = NORMAL")
            self._conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
            self._conn.execute("PRAGMA temp_store = MEMORY")
        except sqlite3.Error:
            logger.exception("[DatabaseManager] Failed to connect to database")
            # Try to recover by removing corrupted database
            if self.db_path.exists():
                self._backup_corrupted_database()
            # Retry connection
            self._conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row

        self._initialize_database()
        logger.info("[DatabaseManager] Initialized with database: %s", self.db_path)

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get database connection (yields existing connection)."""
        yield self._conn

    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager for atomic transactions.

        Usage:
            with db_manager.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
                # Automatically commits on success, rolls back on exception
        """
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def _initialize_database(self) -> None:
        """Initialize database schema and store instances."""
        cursor = self._conn.cursor()

        # Get current schema version
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        if not cursor.fetchone():
            # New database - create schema
            logger.info("[DatabaseManager] Creating new database schema")
            create_schema(cursor)
            create_indexes(cursor)
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
            )
            cursor.execute(
                f"INSERT OR REPLACE INTO schema_version (version) VALUES ({self.SCHEMA_VERSION})"
            )
            self._conn.commit()
        else:
            # Existing database - check version and migrate if needed
            cursor.execute("SELECT version FROM schema_version")
            row = cursor.fetchone()
            current_version = row[0] if row else 1

            if current_version < self.SCHEMA_VERSION:
                logger.info(
                    "[DatabaseManager] Migrating database from v%d to v%d",
                    current_version,
                    self.SCHEMA_VERSION,
                )
                migrate_schema(cursor, current_version, self.SCHEMA_VERSION)
                create_indexes(cursor)
                cursor.execute(f"UPDATE schema_version SET version = {self.SCHEMA_VERSION}")
                self._conn.commit()

        # Initialize specialized stores (composition pattern)
        self.path_store = PathStore(self._conn)
        self.hash_store = HashStore(self._conn, self.path_store, self._write_lock)
        self.metadata_store = MetadataStore(self._conn, self.path_store, self._write_lock)
        self.session_state_store = SessionStateStore(self._conn, self._write_lock)
        self.thumbnail_store = ThumbnailStore(self._conn)

        logger.debug("[DatabaseManager] Store instances initialized", extra={"dev_only": True})

    # ====================================================================
    # PathStore delegation (4 methods)
    # ====================================================================

    def get_or_create_path_id(self, file_path: str) -> int:
        """Get or create path ID for a file path (thread-safe)."""
        with self._write_lock:
            return self.path_store.get_or_create_path_id(file_path)

    def get_path_id(self, file_path: str) -> int | None:
        """Get path ID for a file path."""
        return self.path_store.get_path_id(file_path)

    def update_file_path(self, old_path: str, new_path: str) -> bool:
        """Update file path after rename (thread-safe)."""
        with self._write_lock:
            return self.path_store.update_file_path(old_path, new_path)

    def normalize_path(self, file_path: str) -> str:
        """Normalize file path for database consistency."""
        return self.path_store.normalize_path(file_path)

    # ====================================================================
    # HashStore delegation (4 methods)
    # ====================================================================

    def store_hash(self, file_path: str, hash_value: str, algorithm: str = "CRC32") -> bool:
        """Store hash value for a file (thread-safe)."""
        with self._write_lock:
            return self.hash_store.store_hash(file_path, hash_value, algorithm)

    def get_hash(self, file_path: str, algorithm: str = "CRC32") -> str | None:
        """Get hash value for a file."""
        return self.hash_store.get_hash(file_path, algorithm)

    def has_hash(self, file_path: str, algorithm: str = "CRC32") -> bool:
        """Check if file has a hash value."""
        return self.hash_store.has_hash(file_path, algorithm)

    def get_files_with_hash_batch(
        self, file_paths: list[str], algorithm: str = "CRC32"
    ) -> list[str]:
        """Get hash values for multiple files."""
        return self.hash_store.get_files_with_hash_batch(file_paths, algorithm)

    # ====================================================================
    # MetadataStore delegation (15 methods)
    # ====================================================================

    def store_metadata(
        self,
        file_path: str,
        metadata: dict[str, Any],
        is_extended: bool = False,
        is_modified: bool = False,
    ) -> bool:
        """Store metadata for a file (thread-safe)."""
        with self._write_lock:
            return self.metadata_store.store_metadata(file_path, metadata, is_extended, is_modified)

    def batch_store_metadata(
        self,
        file_metadata_list: list[tuple[str, dict[str, Any], bool, bool]],
    ) -> int:
        """Batch store metadata for multiple files (thread-safe)."""
        with self._write_lock:
            return self.metadata_store.batch_store_metadata(file_metadata_list)

    def get_metadata(self, file_path: str) -> dict[str, Any] | None:
        """Get metadata for a file."""
        return self.metadata_store.get_metadata(file_path)

    def get_metadata_batch(self, file_paths: list[str]) -> dict[str, dict[str, Any] | None]:
        """Get metadata for multiple files."""
        return self.metadata_store.get_metadata_batch(file_paths)

    def has_metadata(self, file_path: str, metadata_type: str | None = None) -> bool:
        """Check if file has metadata."""
        return self.metadata_store.has_metadata(file_path, metadata_type)

    def create_metadata_category(
        self,
        category_key: str,
        category_name: str,
        description: str | None = None,
        display_order: int = 0,
    ) -> int | None:
        """Create or get metadata category (thread-safe)."""
        with self._write_lock:
            return self.metadata_store.create_metadata_category(
                category_key, category_name, description, display_order
            )

    def get_metadata_categories(self) -> list[dict[str, Any]]:
        """Get all metadata categories."""
        return self.metadata_store.get_metadata_categories()

    def create_metadata_field(
        self,
        field_key: str,
        field_name: str,
        category_id: int,
        data_type: str = "text",
        is_editable: bool = False,
        is_searchable: bool = True,
        display_format: str | None = None,
        sort_order: int = 0,
    ) -> int | None:
        """Create or get metadata field (thread-safe)."""
        with self._write_lock:
            return self.metadata_store.create_metadata_field(
                field_key,
                field_name,
                category_id,
                data_type,
                is_editable,
                is_searchable,
                display_format,
                sort_order,
            )

    def get_metadata_fields(self, category_id: int | None = None) -> list[dict[str, Any]]:
        """Get metadata fields, optionally filtered by category."""
        return self.metadata_store.get_metadata_fields(category_id)

    def get_metadata_field_by_key(self, field_key: str) -> dict[str, Any] | None:
        """Get metadata field by its unique key."""
        return self.metadata_store.get_metadata_field_by_key(field_key)

    def store_structured_metadata(self, file_path: str, field_key: str, field_value: str) -> bool:
        """Store structured metadata value for a file field (thread-safe)."""
        with self._write_lock:
            return self.metadata_store.store_structured_metadata(file_path, field_key, field_value)

    def batch_store_structured_metadata(
        self,
        file_path: str,
        field_data: list[tuple[str, str]],
    ) -> int:
        """Batch store structured metadata for a file (thread-safe)."""
        with self._write_lock:
            return self.metadata_store.batch_store_structured_metadata(file_path, field_data)

    def get_structured_metadata(self, file_path: str) -> dict[str, Any]:
        """Get structured metadata for a file."""
        return self.metadata_store.get_structured_metadata(file_path)

    def initialize_default_metadata_schema(self) -> bool:
        """Initialize default metadata categories and fields."""
        from oncutf.infra.db.migrations import initialize_default_metadata_schema

        return initialize_default_metadata_schema(
            self.get_metadata_categories,
            self.create_metadata_category,
            self.create_metadata_field,
        )

    def set_color_tag(self, file_path: str, color_hex: str) -> bool:
        """Set color tag for a file (thread-safe)."""
        with self._write_lock:
            return self.metadata_store.set_color_tag(file_path, color_hex)

    def get_color_tag(self, file_path: str) -> str:
        """Get color tag for a file."""
        return self.metadata_store.get_color_tag(file_path)

    # ====================================================================
    # Stats (kept in orchestrator - queries multiple tables)
    # ====================================================================

    # ====================================================================
    # SessionStateStore delegation (6 methods)
    # ====================================================================

    def get_session_state(self, key: str, default: Any = None) -> Any:
        """Get session state value by key."""
        return self.session_state_store.get(key, default)

    def set_session_state(self, key: str, value: Any) -> bool:
        """Set session state value."""
        return self.session_state_store.set(key, value)

    def get_all_session_state(self) -> dict[str, Any]:
        """Get all session state values."""
        return self.session_state_store.get_all()

    def set_many_session_state(self, data: dict[str, Any]) -> bool:
        """Set multiple session state values atomically."""
        return self.session_state_store.set_many(data)

    def delete_session_state(self, key: str) -> bool:
        """Delete session state value."""
        return self.session_state_store.delete(key)

    def session_state_exists(self, key: str) -> bool:
        """Check if session state key exists."""
        return self.session_state_store.exists(key)

    # ====================================================================
    # Statistics and maintenance
    # ====================================================================

    def get_database_stats(self) -> dict[str, int]:
        """Get database statistics across all tables.

        Returns
        -------
            dict with counts for paths, metadata, hashes, etc.

        """
        stats = {}
        cursor = self._conn.cursor()

        # Count file paths
        cursor.execute("SELECT COUNT(*) FROM file_paths")
        stats["total_paths"] = cursor.fetchone()[0]

        # Count metadata entries
        cursor.execute("SELECT COUNT(*) FROM file_metadata")
        stats["metadata_entries"] = cursor.fetchone()[0]

        # Count hash entries
        cursor.execute("SELECT COUNT(*) FROM file_hashes")
        stats["hash_entries"] = cursor.fetchone()[0]

        # Count color tags
        cursor.execute("SELECT COUNT(*) FROM file_color_tags")
        stats["color_tags"] = cursor.fetchone()[0]

        # Count metadata categories
        cursor.execute("SELECT COUNT(*) FROM metadata_categories")
        stats["metadata_categories"] = cursor.fetchone()[0]

        # Count metadata fields
        cursor.execute("SELECT COUNT(*) FROM metadata_fields")
        stats["metadata_fields"] = cursor.fetchone()[0]

        # Count structured metadata entries
        cursor.execute("SELECT COUNT(*) FROM file_metadata_structured")
        stats["structured_metadata_entries"] = cursor.fetchone()[0]

        return stats

    # ====================================================================
    # Lifecycle
    # ====================================================================

    def close(self) -> None:
        """Close database connection and cleanup resources."""
        if hasattr(self, "_conn") and self._conn:
            try:
                self._conn.close()
                logger.debug("[DatabaseManager] Connection closed", extra={"dev_only": True})
            except Exception:
                logger.exception("[DatabaseManager] Error closing connection")

    # ====================================================================
    # Database validation and recovery
    # ====================================================================

    def _validate_database_file(self) -> bool:
        """Validate database file integrity.

        Returns
        -------
            True if database is valid, False if corrupted

        """
        # Check if file is empty
        if self.db_path.stat().st_size == 0:
            logger.warning("[DatabaseManager] Database file is empty")
            return False

        # Try to open and check integrity
        try:
            test_conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            cursor = test_conn.cursor()
            # Quick integrity check using PRAGMA
            cursor.execute("PRAGMA quick_check")
            result = cursor.fetchone()
            test_conn.close()

            is_ok = bool(result and result[0] == "ok")
            if not is_ok:
                logger.warning("[DatabaseManager] Database integrity check failed: %s", result)
        except sqlite3.Error as e:
            logger.warning("[DatabaseManager] Database validation failed: %s", e)
            is_ok = False
        except Exception as e:
            logger.warning("[DatabaseManager] Unexpected error during validation: %s", e)
            is_ok = False
        return is_ok

    def _backup_corrupted_database(self) -> None:
        """Backup corrupted database and remove it."""
        import shutil
        from datetime import datetime

        try:
            # Create backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_path.with_suffix(f".corrupted.{timestamp}.db")

            # Backup main database file
            if self.db_path.exists():
                shutil.copy2(self.db_path, backup_path)
                self.db_path.unlink()
                logger.info("[DatabaseManager] Corrupted database backed up to: %s", backup_path)

            # Remove WAL and SHM files
            wal_path = self.db_path.with_suffix(".db-wal")
            shm_path = self.db_path.with_suffix(".db-shm")
            if wal_path.exists():
                wal_path.unlink()
            if shm_path.exists():
                shm_path.unlink()

        except Exception:
            logger.exception("[DatabaseManager] Failed to backup corrupted database")
            # Force remove even if backup fails
            try:
                if self.db_path.exists():
                    self.db_path.unlink()
            except Exception:
                logger.exception("[DatabaseManager] Failed to remove corrupted database")

    # ====================================================================
    # ThumbnailStore delegation (6 methods)
    # ====================================================================

    def get_cached_thumbnail(self, file_path: str, mtime: float) -> dict[str, Any] | None:
        """Get cached thumbnail metadata for a file.

        Args:
        ----
            file_path: Absolute file path
            mtime: File modification time

        Returns:
        -------
            Dict with cache metadata if found, None otherwise

        """
        return self.thumbnail_store.get_cached_entry(file_path, mtime)

    def save_thumbnail_cache(
        self,
        folder_path: str,
        file_path: str,
        file_mtime: float,
        file_size: int,
        cache_filename: str,
        video_frame_time: float | None = None,
    ) -> bool:
        """Save thumbnail cache metadata.

        Args:
        ----
            folder_path: Parent folder path
            file_path: Absolute file path
            file_mtime: File modification time
            file_size: File size in bytes
            cache_filename: Cached thumbnail filename
            video_frame_time: Video frame timestamp if applicable

        Returns:
        -------
            True if saved successfully

        """
        return self.thumbnail_store.save_cache_entry(
            folder_path,
            file_path,
            file_mtime,
            file_size,
            cache_filename,
            video_frame_time,
        )

    def get_thumbnail_folder_order(self, folder_path: str) -> list[str] | None:
        """Get manual file order for a folder.

        Args:
        ----
            folder_path: Absolute folder path

        Returns:
        -------
            Ordered list of file paths, or None if no manual order

        """
        return self.thumbnail_store.get_folder_order(folder_path)

    def save_thumbnail_folder_order(self, folder_path: str, file_paths: list[str]) -> bool:
        """Save manual file order for a folder.

        Args:
        ----
            folder_path: Absolute folder path
            file_paths: Ordered list of file paths

        Returns:
        -------
            True if saved successfully

        """
        return self.thumbnail_store.save_folder_order(folder_path, file_paths)

    def clear_thumbnail_folder_order(self, folder_path: str) -> bool:
        """Clear manual order for a folder.

        Args:
        ----
            folder_path: Absolute folder path

        Returns:
        -------
            True if entry was removed

        """
        return self.thumbnail_store.clear_folder_order(folder_path)

    def get_thumbnail_cache_stats(self) -> dict[str, int]:
        """Get thumbnail cache statistics.

        Returns
        -------
            Dict with cache stats (total_entries, total_folders, total_manual_orders)

        """
        return self.thumbnail_store.get_cache_stats()


# ====================================================================
# Module-level functions for global instance
# ====================================================================

_db_manager_instance: DatabaseManager | None = None


def get_database_manager(db_path: str | None = None) -> DatabaseManager:
    """Get or create singleton DatabaseManager instance.

    Args:
    ----
        db_path: Optional custom database path (only used on first call)

    Returns:
    -------
        DatabaseManager instance

    """
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager(db_path)
    return _db_manager_instance


def init_database_with_custom_path(db_path: str) -> DatabaseManager:
    """Initialize database with custom path (replaces singleton).

    Args:
    ----
        db_path: Custom database path

    Returns:
    -------
        New DatabaseManager instance

    """
    global _db_manager_instance
    if _db_manager_instance:
        _db_manager_instance.close()
    _db_manager_instance = DatabaseManager(db_path)
    return _db_manager_instance
