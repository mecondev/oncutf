"""Module: database_manager.py

Author: Michael Economou
Date: 2026-01-01

Refactored database manager - orchestrates specialized store classes.

This is the main entry point for database operations. It delegates to:
- PathStore: file_paths table operations
- MetadataStore: file_metadata, categories, fields, color tags
- HashStore: file_hashes table operations
- BackupStore: file_rename_history operations (TBD)
- migrations: Schema creation and migration functions

All public methods are preserved for backward compatibility.
"""

import contextlib
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from oncutf.core.database.backup_store import BackupStore
from oncutf.core.database.hash_store import HashStore
from oncutf.core.database.metadata_store import MetadataStore
from oncutf.core.database.migrations import create_indexes, create_schema, migrate_schema
from oncutf.core.database.path_store import PathStore
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class DatabaseManager:
    """Enhanced database management with composition-based architecture.

    This orchestrator delegates to specialized store classes:
    - PathStore: file_paths table
    - MetadataStore: metadata, categories, fields, color tags
    - HashStore: file hashes
    - BackupStore: rename history (future)

    Benefits:
    - Single responsibility per store
    - Easier testing and maintenance
    - Clear separation of concerns
    - Backward compatible API
    """

    SCHEMA_VERSION = 4

    def __init__(self, db_path: str | None = None):
        """Initialize database manager with store composition.

        Args:
            db_path: Optional custom database path

        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Use centralized path management
            from oncutf.utils.paths import AppPaths

            self.db_path = AppPaths.get_database_path()

        # Debug: Reset database if requested
        from oncutf.config import DEBUG_RESET_DATABASE

        if DEBUG_RESET_DATABASE:
            if self.db_path.exists():
                logger.info("[DatabaseManager] DEBUG_RESET_DATABASE enabled - deleting: %s", self.db_path)
                try:
                    self.db_path.unlink()
                    # Also remove WAL and SHM files if they exist
                    wal_path = self.db_path.with_suffix(".db-wal")
                    shm_path = self.db_path.with_suffix(".db-shm")
                    if wal_path.exists():
                        wal_path.unlink()
                    if shm_path.exists():
                        shm_path.unlink()
                    logger.info("[DatabaseManager] Database files deleted for fresh start")
                except Exception as e:
                    logger.error("[DatabaseManager] Failed to delete database: %s", e)

        # Thread safety lock for concurrent access from parallel workers
        self._write_lock = threading.RLock()

        # Create connection first (stores need it)
        self._conn = sqlite3.connect(
            str(self.db_path), timeout=30.0, check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
        self._conn.execute("PRAGMA temp_store = MEMORY")

        self._initialize_database()
        logger.info("[DatabaseManager] Initialized with database: %s", self.db_path)

    @contextmanager
    def _get_connection(self):
        """Get database connection (yields existing connection)."""
        yield self._conn

    @contextlib.contextmanager
    def transaction(self):
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

    def _initialize_database(self):
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
                cursor.execute(
                    f"UPDATE schema_version SET version = {self.SCHEMA_VERSION}"
                )
                self._conn.commit()

        # Initialize specialized stores (composition pattern)
        self.path_store = PathStore(self._conn)
        self.hash_store = HashStore(self._conn, self.path_store, self._write_lock)
        self.metadata_store = MetadataStore(self._conn, self.path_store, self._write_lock)
        self.backup_store = BackupStore(self._conn, self.path_store)

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
            return self.metadata_store.store_metadata(
                file_path, metadata, is_extended, is_modified
            )

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

    def store_structured_metadata(
        self, file_path: str, field_key: str, field_value: str
    ) -> bool:
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
        from oncutf.core.database.migrations import initialize_default_metadata_schema

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

    def get_database_stats(self) -> dict[str, int]:
        """Get database statistics across all tables.

        Returns:
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

    def close(self):
        """Close database connection and cleanup resources."""
        if hasattr(self, "_conn") and self._conn:
            try:
                self._conn.close()
                logger.debug("[DatabaseManager] Connection closed", extra={"dev_only": True})
            except Exception as e:
                logger.error("[DatabaseManager] Error closing connection: %s", e)


# ====================================================================
# Module-level functions for global instance
# ====================================================================

_db_manager_instance: DatabaseManager | None = None


def get_database_manager(db_path: str | None = None) -> DatabaseManager:
    """Get or create singleton DatabaseManager instance.

    Args:
        db_path: Optional custom database path (only used on first call)

    Returns:
        DatabaseManager instance

    """
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager(db_path)
    return _db_manager_instance


def init_database_with_custom_path(db_path: str) -> DatabaseManager:
    """Initialize database with custom path (replaces singleton).

    Args:
        db_path: Custom database path

    Returns:
        New DatabaseManager instance

    """
    global _db_manager_instance
    if _db_manager_instance:
        _db_manager_instance.close()
    _db_manager_instance = DatabaseManager(db_path)
    return _db_manager_instance
