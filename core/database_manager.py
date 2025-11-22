"""
Module: database_manager.py

Author: Michael Economou
Date: 2025-06-10

database_manager.py
Enhanced database management with improved architecture.
Separates concerns into dedicated tables while maintaining referential integrity.
Architecture:
- file_paths: Central table for file path management
- file_metadata: Dedicated metadata storage
- file_hashes: Dedicated hash storage
- file_rename_history: Dedicated rename history
- Future: file_thumbnails, file_tags, etc.
"""

import contextlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.logger_factory import get_cached_logger
from utils.path_normalizer import normalize_path

logger = get_cached_logger(__name__)


class DatabaseManager:
    """
    Enhanced database management with improved separation of concerns.

    Architecture:
    - file_paths: Central registry of all file paths
    - file_metadata: Metadata storage (references file_paths)
    - file_hashes: Hash storage (references file_paths)
    - file_rename_history: Rename history (references file_paths)

    Benefits:
    - Better separation of concerns
    - Easier to add new features (thumbnails, tags, etc.)
    - More maintainable and extensible
    - Better performance with focused tables
    """

    # Database schema version for migrations
    SCHEMA_VERSION = 3

    def __init__(self, db_path: str | None = None):
        """
        Initialize database manager.

        Args:
            db_path: Optional custom database path
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Use user data directory
            data_dir = self._get_user_data_directory()
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "oncutf_data.db"

        # Debug: Reset database if requested
        from config import DEBUG_RESET_DATABASE

        if DEBUG_RESET_DATABASE:
            if self.db_path.exists():
                logger.info(f"[DEBUG] Deleting database for fresh start: {self.db_path}")
                try:
                    self.db_path.unlink()
                    # Also remove WAL and SHM files if they exist
                    wal_path = self.db_path.with_suffix(".db-wal")
                    shm_path = self.db_path.with_suffix(".db-shm")
                    if wal_path.exists():
                        wal_path.unlink()
                    if shm_path.exists():
                        shm_path.unlink()
                    logger.info("[DEBUG] Database files deleted successfully")
                except Exception as e:
                    logger.error(f"[DEBUG] Failed to delete database: {e}")

        self._initialize_database()
        logger.info(f"[DatabaseManager] Initialized with database: {self.db_path}")

    def _get_user_data_directory(self) -> Path:
        """Get user data directory for storing database."""
        if os.name == "nt":  # Windows
            data_dir = Path.home() / "AppData" / "Local" / "oncutf"
        else:  # Linux/macOS
            data_dir = Path.home() / ".local" / "share" / "oncutf"
        return data_dir

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper configuration."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
            conn.execute("PRAGMA temp_store = MEMORY")
            yield conn
        finally:
            if conn:
                conn.close()

    @contextlib.contextmanager
    def transaction(self):
        """
        Context manager for atomic transactions.

        Usage:
            with db_manager.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
                # Automatically commits on success, rolls back on exception
        """
        with self._get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def _initialize_database(self):
        """Initialize database with schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check current schema version
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_info (
                    version INTEGER PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute("SELECT version FROM schema_info ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            current_version = row["version"] if row else 0

            if current_version < self.SCHEMA_VERSION:
                if current_version == 0:
                    self._create_schema_v2(cursor)
                else:
                    self._migrate_schema(cursor, current_version)

                # Update schema version
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO schema_info (version, updated_at)
                    VALUES (?, CURRENT_TIMESTAMP)
                """,
                    (self.SCHEMA_VERSION,),
                )

            self._create_indexes(cursor)
            conn.commit()

        # Initialize default metadata schema after database setup
        self.initialize_default_metadata_schema()

        logger.debug(
            f"[DatabaseManager] Schema initialized (version {self.SCHEMA_VERSION})",
            extra={"dev_only": True},
        )

    def _create_schema_v2(self, cursor: sqlite3.Cursor):
        """Create the new v2 schema with separated tables."""

        # 1. Central file paths table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                file_size INTEGER,
                modified_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 2. Dedicated metadata table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_id INTEGER NOT NULL,
                metadata_type TEXT NOT NULL DEFAULT 'fast',
                metadata_json TEXT NOT NULL,
                is_modified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (path_id) REFERENCES file_paths (id) ON DELETE CASCADE
            )
        """
        )

        # 3. Dedicated hash table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_id INTEGER NOT NULL,
                algorithm TEXT NOT NULL DEFAULT 'CRC32',
                hash_value TEXT NOT NULL,
                file_size_at_hash INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (path_id) REFERENCES file_paths (id) ON DELETE CASCADE
            )
        """
        )

        # 4. Dedicated rename history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_rename_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT NOT NULL,
                path_id INTEGER NOT NULL,
                old_path TEXT NOT NULL,
                new_path TEXT NOT NULL,
                old_filename TEXT NOT NULL,
                new_filename TEXT NOT NULL,
                operation_type TEXT NOT NULL DEFAULT 'rename',
                modules_data TEXT,
                post_transform_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (path_id) REFERENCES file_paths (id) ON DELETE CASCADE
            )
        """
        )

        # 5. Metadata categories table for organizing metadata groups
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 6. Metadata fields table for individual metadata fields
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field_key TEXT NOT NULL UNIQUE,
                field_name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                data_type TEXT NOT NULL DEFAULT 'text',
                is_editable BOOLEAN DEFAULT FALSE,
                is_searchable BOOLEAN DEFAULT TRUE,
                display_format TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES metadata_categories (id) ON DELETE CASCADE
            )
        """
        )

        # 7. Structured metadata storage table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_metadata_structured (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_id INTEGER NOT NULL,
                field_id INTEGER NOT NULL,
                field_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (path_id) REFERENCES file_paths (id) ON DELETE CASCADE,
                FOREIGN KEY (field_id) REFERENCES metadata_fields (id) ON DELETE CASCADE,
                UNIQUE(path_id, field_id)
            )
        """
        )

        logger.debug("[DatabaseManager] Schema v2 created")

    def _migrate_schema(self, cursor: sqlite3.Cursor, from_version: int):
        """Migrate from older schema versions."""
        logger.info(
            f"[DatabaseManager] Migrating from version {from_version} to {self.SCHEMA_VERSION}"
        )

        # Migration from version 2 to 3: Add structured metadata tables
        if from_version == 2 and self.SCHEMA_VERSION >= 3:
            logger.info("[DatabaseManager] Adding structured metadata tables...")

            # Add metadata categories table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_name TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    description TEXT,
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Add metadata fields table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    field_key TEXT NOT NULL UNIQUE,
                    field_name TEXT NOT NULL,
                    category_id INTEGER NOT NULL,
                    data_type TEXT NOT NULL DEFAULT 'text',
                    is_editable BOOLEAN DEFAULT FALSE,
                    is_searchable BOOLEAN DEFAULT TRUE,
                    display_format TEXT,
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES metadata_categories (id) ON DELETE CASCADE
                )
            """
            )

            # Add structured metadata storage table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS file_metadata_structured (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path_id INTEGER NOT NULL,
                    field_id INTEGER NOT NULL,
                    field_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (path_id) REFERENCES file_paths (id) ON DELETE CASCADE,
                    FOREIGN KEY (field_id) REFERENCES metadata_fields (id) ON DELETE CASCADE,
                    UNIQUE(path_id, field_id)
                )
            """
            )

            logger.info("[DatabaseManager] Structured metadata tables added successfully")

    def _create_indexes(self, cursor: sqlite3.Cursor):
        """Create database indexes for performance."""
        indexes = [
            # File paths indexes
            "CREATE INDEX IF NOT EXISTS idx_file_paths_path ON file_paths (file_path)",
            "CREATE INDEX IF NOT EXISTS idx_file_paths_filename ON file_paths (filename)",
            # Metadata indexes
            "CREATE INDEX IF NOT EXISTS idx_file_metadata_path_id ON file_metadata (path_id)",
            "CREATE INDEX IF NOT EXISTS idx_file_metadata_type ON file_metadata (metadata_type)",
            # Hash indexes
            "CREATE INDEX IF NOT EXISTS idx_file_hashes_path_id ON file_hashes (path_id)",
            "CREATE INDEX IF NOT EXISTS idx_file_hashes_algorithm ON file_hashes (algorithm)",
            "CREATE INDEX IF NOT EXISTS idx_file_hashes_value ON file_hashes (hash_value)",
            # Rename history indexes
            "CREATE INDEX IF NOT EXISTS idx_file_rename_history_operation_id ON file_rename_history (operation_id)",
            "CREATE INDEX IF NOT EXISTS idx_file_rename_history_path_id ON file_rename_history (path_id)",
            "CREATE INDEX IF NOT EXISTS idx_file_rename_history_created_at ON file_rename_history (created_at)",
            # Metadata categories indexes
            "CREATE INDEX IF NOT EXISTS idx_metadata_categories_name ON metadata_categories (category_name)",
            "CREATE INDEX IF NOT EXISTS idx_metadata_categories_sort_order ON metadata_categories (sort_order)",
            # Metadata fields indexes
            "CREATE INDEX IF NOT EXISTS idx_metadata_fields_key ON metadata_fields (field_key)",
            "CREATE INDEX IF NOT EXISTS idx_metadata_fields_category_id ON metadata_fields (category_id)",
            "CREATE INDEX IF NOT EXISTS idx_metadata_fields_sort_order ON metadata_fields (sort_order)",
            # Structured metadata indexes
            "CREATE INDEX IF NOT EXISTS idx_file_metadata_structured_path_id ON file_metadata_structured (path_id)",
            "CREATE INDEX IF NOT EXISTS idx_file_metadata_structured_field_id ON file_metadata_structured (field_id)",
            "CREATE INDEX IF NOT EXISTS idx_file_metadata_structured_path_field ON file_metadata_structured (path_id, field_id)",
            # Composite indexes for faster common queries
            "CREATE INDEX IF NOT EXISTS idx_metadata_path_type ON file_metadata (path_id, metadata_type)",
            "CREATE INDEX IF NOT EXISTS idx_hashes_path_algo ON file_hashes (path_id, algorithm)",
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

        logger.debug("[DatabaseManager] Database indexes created", extra={"dev_only": True})

    # =====================================
    # File Path Management
    # =====================================

    def get_or_create_path_id(self, file_path: str) -> int:
        """
        Get path_id for a file, creating record if needed.

        This is the core method that ensures every file path has an ID.
        All other operations use this ID to reference files.

        Args:
            file_path: Path to the file

        Returns:
            path_id for the file
        """
        norm_path = self._normalize_path(file_path)
        filename = os.path.basename(norm_path)

        with self._get_connection() as conn:
            cursor = conn.cursor()

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
            conn.commit()

            path_id = cursor.lastrowid
            if path_id is None:
                raise RuntimeError(f"Failed to create path record for: {norm_path}")

            return path_id

    def _normalize_path(self, file_path: str) -> str:
        """Use the central normalize_path function."""
        return normalize_path(file_path)

    def get_path_id(self, file_path: str) -> int | None:
        """Get path_id for a file without creating it."""
        norm_path = self._normalize_path(file_path)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM file_paths WHERE file_path = ?", (norm_path,))
            row = cursor.fetchone()
            return row["id"] if row else None

    # =====================================
    # Metadata Management
    # =====================================

    def store_metadata(
        self,
        file_path: str,
        metadata: dict[str, Any],
        is_extended: bool = False,
        is_modified: bool = False,
    ) -> bool:
        """Store metadata for a file."""
        try:
            path_id = self.get_or_create_path_id(file_path)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Remove existing metadata for this path
                cursor.execute("DELETE FROM file_metadata WHERE path_id = ?", (path_id,))

                # Store new metadata
                metadata_type = "extended" if is_extended else "fast"
                metadata_json = json.dumps(metadata, ensure_ascii=False, indent=None)

                cursor.execute(
                    """
                    INSERT INTO file_metadata
                    (path_id, metadata_type, metadata_json, is_modified)
                    VALUES (?, ?, ?, ?)
                """,
                    (path_id, metadata_type, metadata_json, is_modified),
                )

                # Commit the transaction
                conn.commit()

                logger.debug(
                    f"[DatabaseManager] Stored {metadata_type} metadata for: {os.path.basename(file_path)}"
                )
                return True

        except Exception as e:
            logger.error(f"[DatabaseManager] Error storing metadata for {file_path}: {e}")
            return False

    def batch_store_metadata(
        self,
        metadata_items: list[tuple[str, dict[str, Any], bool, bool]],
    ) -> int:
        """
        Store metadata for multiple files in a single batch operation.

        Args:
            metadata_items: List of (file_path, metadata_dict, is_extended, is_modified) tuples

        Returns:
            Number of files successfully stored
        """
        if not metadata_items:
            return 0

        try:
            success_count = 0

            with self._get_connection() as conn:
                cursor = conn.cursor()

                for file_path, metadata, is_extended, is_modified in metadata_items:
                    try:
                        path_id = self.get_or_create_path_id(file_path)

                        # Remove existing metadata
                        cursor.execute(
                            "DELETE FROM file_metadata WHERE path_id = ?", (path_id,)
                        )

                        # Store new metadata
                        metadata_type = "extended" if is_extended else "fast"
                        metadata_json = json.dumps(metadata, ensure_ascii=False, indent=None)

                        cursor.execute(
                            """
                            INSERT INTO file_metadata
                            (path_id, metadata_type, metadata_json, is_modified)
                            VALUES (?, ?, ?, ?)
                            """,
                            (path_id, metadata_type, metadata_json, is_modified),
                        )
                        success_count += 1

                    except Exception as e:
                        logger.error(
                            f"[DatabaseManager] Error in batch storing metadata for {file_path}: {e}"
                        )
                        continue

                # Commit all inserts in one transaction
                conn.commit()

                logger.debug(
                    f"[DatabaseManager] Batch stored metadata for {success_count}/{len(metadata_items)} files"
                )
                return success_count

        except Exception as e:
            logger.error(f"[DatabaseManager] Error in batch store metadata: {e}")
            return 0

    def get_metadata(self, file_path: str) -> dict[str, Any] | None:
        """Retrieve metadata for a file."""
        try:
            path_id = self.get_path_id(file_path)
            if not path_id:
                return None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT metadata_json, metadata_type, is_modified
                    FROM file_metadata
                    WHERE path_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """,
                    (path_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                metadata = json.loads(row["metadata_json"])

                # Add metadata flags
                if row["metadata_type"] == "extended":
                    metadata["__extended__"] = True
                if row["is_modified"]:
                    metadata["__modified__"] = True

                return metadata

        except Exception as e:
            logger.error(f"[DatabaseManager] Error retrieving metadata for {file_path}: {e}")
            return None

    def get_metadata_batch(self, file_paths: list[str]) -> dict[str, dict[str, Any] | None]:
        """
        Retrieve metadata for multiple files in a single batch operation.

        Args:
            file_paths: List of file paths to get metadata for

        Returns:
            dict: Mapping of file_path -> metadata dict (or None if not found)
        """
        if not file_paths:
            return {}

        try:
            # Get path IDs for all files
            path_ids = {}
            for file_path in file_paths:
                path_id = self.get_path_id(file_path)
                if path_id:
                    path_ids[path_id] = file_path

            if not path_ids:
                return dict.fromkeys(file_paths)

            # Batch query metadata
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Create placeholders for IN clause
                placeholders = ",".join("?" * len(path_ids))

                cursor.execute(
                    f"""
                    SELECT path_id, metadata_json, metadata_type, is_modified
                    FROM file_metadata
                    WHERE path_id IN ({placeholders})
                    AND (path_id, updated_at) IN (
                        SELECT path_id, MAX(updated_at)
                        FROM file_metadata
                        WHERE path_id IN ({placeholders})
                        GROUP BY path_id
                    )
                    """,
                    list(path_ids.keys()) * 2,  # placeholders appear twice in query
                )

                # Process results
                results = {}
                for file_path in file_paths:
                    results[file_path] = None

                for row in cursor.fetchall():
                    file_path = path_ids[row["path_id"]]
                    metadata = json.loads(row["metadata_json"])

                    # Add metadata flags
                    if row["metadata_type"] == "extended":
                        metadata["__extended__"] = True
                    if row["is_modified"]:
                        metadata["__modified__"] = True

                    results[file_path] = metadata

                return results

        except Exception as e:
            logger.error(f"[DatabaseManager] Error in batch metadata retrieval: {e}")
            return dict.fromkeys(file_paths)

    def has_metadata(self, file_path: str, metadata_type: str | None = None) -> bool:
        """Check if file has metadata stored."""
        try:
            path_id = self.get_path_id(file_path)
            if not path_id:
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()

                if metadata_type:
                    cursor.execute(
                        """
                        SELECT 1 FROM file_metadata
                        WHERE path_id = ? AND metadata_type = ?
                        LIMIT 1
                    """,
                        (path_id, metadata_type),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT 1 FROM file_metadata
                        WHERE path_id = ?
                        LIMIT 1
                    """,
                        (path_id,),
                    )

                return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"[DatabaseManager] Error checking metadata for {file_path}: {e}")
            return False

    # =====================================
    # Hash Management
    # =====================================

    def store_hash(self, file_path: str, hash_value: str, algorithm: str = "CRC32") -> bool:
        """Store file hash."""
        try:
            path_id = self.get_or_create_path_id(file_path)

            # Get current file size
            file_size = None
            try:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
            except OSError:
                pass

            with self._get_connection() as conn:
                cursor = conn.cursor()

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
                conn.commit()

                logger.debug(
                    f"[DatabaseManager] Stored {algorithm} hash for: {os.path.basename(file_path)}"
                )
                return True

        except Exception as e:
            logger.error(f"[DatabaseManager] Error storing hash for {file_path}: {e}")
            return False

    def get_hash(self, file_path: str, algorithm: str = "CRC32") -> str | None:
        """Retrieve file hash."""
        try:
            path_id = self.get_path_id(file_path)
            if not path_id:
                return None

            with self._get_connection() as conn:
                cursor = conn.cursor()
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

        except Exception as e:
            logger.error(f"[DatabaseManager] Error retrieving hash for {file_path}: {e}")
            return None

    def has_hash(self, file_path: str, algorithm: str = "CRC32") -> bool:
        """Check if hash exists for a file."""
        norm_path = self._normalize_path(file_path)

        with self._get_connection() as conn:
            cursor = conn.cursor()

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
        norm_paths = [self._normalize_path(path) for path in file_paths]

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create placeholders for the IN clause
            placeholders = ",".join(["?" for _ in norm_paths])

            cursor.execute(
                f"""
                SELECT p.file_path FROM file_paths p
                JOIN file_hashes h ON h.path_id = p.id
                WHERE p.file_path IN ({placeholders}) AND h.algorithm = ?
            """,
                norm_paths + [algorithm],
            )

            # Get all file paths that have hashes
            files_with_hash = [row["file_path"] for row in cursor.fetchall()]

            logger.debug(
                f"[DatabaseManager] Batch hash check: {len(files_with_hash)}/{len(file_paths)} files have {algorithm} hashes"
            )

            return files_with_hash

    # =====================================
    # Metadata Categories & Fields Management
    # =====================================

    def create_metadata_category(
        self, category_name: str, display_name: str, description: str = None, sort_order: int = 0
    ) -> int | None:
        """Create a new metadata category."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO metadata_categories
                    (category_name, display_name, description, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (category_name, display_name, description, sort_order),
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(
                f"[DatabaseManager] Error creating metadata category '{category_name}': {e}"
            )
            return None

    def get_metadata_categories(self) -> list[dict[str, Any]]:
        """Get all metadata categories ordered by sort_order."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, category_name, display_name, description, sort_order
                    FROM metadata_categories
                    ORDER BY sort_order, display_name
                    """
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"[DatabaseManager] Error getting metadata categories: {e}")
            return []

    def create_metadata_field(
        self,
        field_key: str,
        field_name: str,
        category_id: int,
        data_type: str = "text",
        is_editable: bool = False,
        is_searchable: bool = True,
        display_format: str = None,
        sort_order: int = 0,
    ) -> int | None:
        """Create a new metadata field."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO metadata_fields
                    (field_key, field_name, category_id, data_type, is_editable,
                     is_searchable, display_format, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        field_key,
                        field_name,
                        category_id,
                        data_type,
                        is_editable,
                        is_searchable,
                        display_format,
                        sort_order,
                    ),
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"[DatabaseManager] Error creating metadata field '{field_key}': {e}")
            return None

    def get_metadata_fields(self, category_id: int = None) -> list[dict[str, Any]]:
        """Get metadata fields, optionally filtered by category."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if category_id:
                    cursor.execute(
                        """
                        SELECT f.id, f.field_key, f.field_name, f.category_id, f.data_type,
                               f.is_editable, f.is_searchable, f.display_format, f.sort_order,
                               c.category_name, c.display_name as category_display_name
                        FROM metadata_fields f
                        JOIN metadata_categories c ON f.category_id = c.id
                        WHERE f.category_id = ?
                        ORDER BY f.sort_order, f.field_name
                        """,
                        (category_id,),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT f.id, f.field_key, f.field_name, f.category_id, f.data_type,
                               f.is_editable, f.is_searchable, f.display_format, f.sort_order,
                               c.category_name, c.display_name as category_display_name
                        FROM metadata_fields f
                        JOIN metadata_categories c ON f.category_id = c.id
                        ORDER BY c.sort_order, f.sort_order, f.field_name
                        """
                    )

                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"[DatabaseManager] Error getting metadata fields: {e}")
            return []

    def get_metadata_field_by_key(self, field_key: str) -> dict[str, Any] | None:
        """Get a metadata field by its key."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT f.id, f.field_key, f.field_name, f.category_id, f.data_type,
                           f.is_editable, f.is_searchable, f.display_format, f.sort_order,
                           c.category_name, c.display_name as category_display_name
                    FROM metadata_fields f
                    JOIN metadata_categories c ON f.category_id = c.id
                    WHERE f.field_key = ?
                    """,
                    (field_key,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"[DatabaseManager] Error getting metadata field '{field_key}': {e}")
            return None

    def store_structured_metadata(self, file_path: str, field_key: str, field_value: str) -> bool:
        """Store structured metadata for a file."""
        try:
            path_id = self.get_or_create_path_id(file_path)

            # Get field info
            field_info = self.get_metadata_field_by_key(field_key)
            if not field_info:
                logger.warning(
                    f"[DatabaseManager] Field '{field_key}' not found in metadata_fields"
                )
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Use INSERT OR REPLACE to handle updates
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO file_metadata_structured
                    (path_id, field_id, field_value, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (path_id, field_info["id"], field_value),
                )
                conn.commit()
                return True

        except Exception as e:
            logger.error(
                f"[DatabaseManager] Error storing structured metadata for {file_path}: {e}"
            )
            return False

    def batch_store_structured_metadata(
        self, file_path: str, field_data: list[tuple[str, str]]
    ) -> int:
        """
        Store multiple structured metadata fields for a file in a single batch operation.

        Args:
            file_path: Path to the file
            field_data: List of (field_key, field_value) tuples

        Returns:
            Number of fields successfully stored
        """
        if not field_data:
            return 0

        try:
            path_id = self.get_or_create_path_id(file_path)

            # Build field_id mapping
            field_ids = []
            valid_data = []
            for field_key, field_value in field_data:
                field_info = self.get_metadata_field_by_key(field_key)
                if field_info:
                    field_ids.append(field_info["id"])
                    valid_data.append((path_id, field_info["id"], field_value))
                else:
                    logger.debug(
                        f"[DatabaseManager] Field '{field_key}' not found in metadata_fields - skipping"
                    )

            if not valid_data:
                return 0

            # Batch insert using executemany
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO file_metadata_structured
                    (path_id, field_id, field_value, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    valid_data,
                )
                conn.commit()

                logger.debug(
                    f"[DatabaseManager] Batch stored {len(valid_data)} structured metadata fields"
                )
                return len(valid_data)

        except Exception as e:
            logger.error(
                f"[DatabaseManager] Error in batch store structured metadata for {file_path}: {e}"
            )
            return 0

    def get_structured_metadata(self, file_path: str) -> dict[str, Any]:
        """Get structured metadata for a file."""
        try:
            path_id = self.get_path_id(file_path)
            if not path_id:
                return {}

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT f.field_key, f.field_name, f.data_type, f.display_format,
                           c.category_name, c.display_name as category_display_name,
                           s.field_value
                    FROM file_metadata_structured s
                    JOIN metadata_fields f ON s.field_id = f.id
                    JOIN metadata_categories c ON f.category_id = c.id
                    WHERE s.path_id = ?
                    ORDER BY c.sort_order, f.sort_order
                    """,
                    (path_id,),
                )

                result = {}
                for row in cursor.fetchall():
                    result[row["field_key"]] = {
                        "value": row["field_value"],
                        "field_name": row["field_name"],
                        "data_type": row["data_type"],
                        "display_format": row["display_format"],
                        "category_name": row["category_name"],
                        "category_display_name": row["category_display_name"],
                    }

                return result

        except Exception as e:
            logger.error(
                f"[DatabaseManager] Error getting structured metadata for {file_path}: {e}"
            )
            return {}

    def initialize_default_metadata_schema(self) -> bool:
        """Initialize default metadata categories and fields."""
        try:
            # Check if already initialized
            categories = self.get_metadata_categories()
            if categories:
                logger.debug("[DatabaseManager] Metadata schema already initialized")
                return True

            # Create default categories
            category_mapping = {}

            # Basic File Information
            cat_id = self.create_metadata_category(
                "file_basic", "File Information", "Basic file properties and information", 0
            )
            category_mapping["file_basic"] = cat_id

            # Image Information
            cat_id = self.create_metadata_category(
                "image", "Image Properties", "Image-specific metadata and properties", 1
            )
            category_mapping["image"] = cat_id

            # Camera/Device Information
            cat_id = self.create_metadata_category(
                "camera", "Camera & Device", "Camera settings and device information", 2
            )
            category_mapping["camera"] = cat_id

            # Video Information
            cat_id = self.create_metadata_category(
                "video", "Video Properties", "Video-specific metadata and properties", 3
            )
            category_mapping["video"] = cat_id

            # Audio Information
            cat_id = self.create_metadata_category(
                "audio", "Audio Properties", "Audio-specific metadata and properties", 4
            )
            category_mapping["audio"] = cat_id

            # GPS/Location Information
            cat_id = self.create_metadata_category(
                "location", "Location & GPS", "GPS coordinates and location information", 5
            )
            category_mapping["location"] = cat_id

            # Technical Information
            cat_id = self.create_metadata_category(
                "technical", "Technical Details", "Technical metadata and processing information", 6
            )
            category_mapping["technical"] = cat_id

            # Create default fields
            default_fields = [
                # File Basic
                ("System:FileName", "Filename", "file_basic", "text", False, True, None, 0),
                ("System:FileSize", "File Size", "file_basic", "size", False, True, "bytes", 1),
                (
                    "System:FileModifyDate",
                    "Modified Date",
                    "file_basic",
                    "datetime",
                    False,
                    True,
                    None,
                    2,
                ),
                (
                    "System:FileCreateDate",
                    "Created Date",
                    "file_basic",
                    "datetime",
                    False,
                    True,
                    None,
                    3,
                ),
                ("File:FileType", "File Type", "file_basic", "text", False, True, None, 4),
                ("File:MIMEType", "MIME Type", "file_basic", "text", False, True, None, 5),
                # Image
                ("EXIF:ImageWidth", "Image Width", "image", "number", False, True, "pixels", 0),
                ("EXIF:ImageHeight", "Image Height", "image", "number", False, True, "pixels", 1),
                ("EXIF:Orientation", "Orientation", "image", "text", True, True, None, 2),
                ("EXIF:ColorSpace", "Color Space", "image", "text", False, True, None, 3),
                (
                    "EXIF:BitsPerSample",
                    "Bits Per Sample",
                    "image",
                    "number",
                    False,
                    True,
                    "bits",
                    4,
                ),
                ("EXIF:Compression", "Compression", "image", "text", False, True, None, 5),
                # Camera
                ("EXIF:Make", "Camera Make", "camera", "text", True, True, None, 0),
                ("EXIF:Model", "Camera Model", "camera", "text", True, True, None, 1),
                ("EXIF:LensModel", "Lens Model", "camera", "text", True, True, None, 2),
                ("EXIF:ISO", "ISO", "camera", "number", True, True, None, 3),
                ("EXIF:FNumber", "F-Number", "camera", "number", True, True, "f/", 4),
                ("EXIF:ExposureTime", "Exposure Time", "camera", "text", True, True, "sec", 5),
                ("EXIF:FocalLength", "Focal Length", "camera", "text", True, True, "mm", 6),
                ("EXIF:WhiteBalance", "White Balance", "camera", "text", True, True, None, 7),
                ("EXIF:Flash", "Flash", "camera", "text", True, True, None, 8),
                # Video
                (
                    "QuickTime:ImageWidth",
                    "Video Width",
                    "video",
                    "number",
                    False,
                    True,
                    "pixels",
                    0,
                ),
                (
                    "QuickTime:ImageHeight",
                    "Video Height",
                    "video",
                    "number",
                    False,
                    True,
                    "pixels",
                    1,
                ),
                ("QuickTime:Duration", "Duration", "video", "duration", False, True, "seconds", 2),
                (
                    "QuickTime:VideoFrameRate",
                    "Frame Rate",
                    "video",
                    "number",
                    False,
                    True,
                    "fps",
                    3,
                ),
                ("QuickTime:VideoCodec", "Video Codec", "video", "text", False, True, None, 4),
                (
                    "QuickTime:AvgBitrate",
                    "Average Bitrate",
                    "video",
                    "number",
                    False,
                    True,
                    "kbps",
                    5,
                ),
                # Audio
                (
                    "QuickTime:AudioChannels",
                    "Audio Channels",
                    "audio",
                    "number",
                    False,
                    True,
                    None,
                    0,
                ),
                (
                    "QuickTime:AudioSampleRate",
                    "Sample Rate",
                    "audio",
                    "number",
                    False,
                    True,
                    "Hz",
                    1,
                ),
                ("QuickTime:AudioFormat", "Audio Format", "audio", "text", False, True, None, 2),
                (
                    "QuickTime:AudioBitrate",
                    "Audio Bitrate",
                    "audio",
                    "number",
                    False,
                    True,
                    "kbps",
                    3,
                ),
                # Location
                ("GPS:GPSLatitude", "Latitude", "location", "coordinate", True, True, "degrees", 0),
                (
                    "GPS:GPSLongitude",
                    "Longitude",
                    "location",
                    "coordinate",
                    True,
                    True,
                    "degrees",
                    1,
                ),
                ("GPS:GPSAltitude", "Altitude", "location", "number", True, True, "meters", 2),
                ("GPS:GPSMapDatum", "Map Datum", "location", "text", True, True, None, 3),
                # Technical
                (
                    "ExifTool:ExifToolVersion",
                    "ExifTool Version",
                    "technical",
                    "text",
                    False,
                    False,
                    None,
                    0,
                ),
                (
                    "File:FilePermissions",
                    "File Permissions",
                    "technical",
                    "text",
                    False,
                    False,
                    None,
                    1,
                ),
            ]

            for (
                field_key,
                field_name,
                category_name,
                data_type,
                is_editable,
                is_searchable,
                display_format,
                sort_order,
            ) in default_fields:
                category_id = category_mapping.get(category_name)
                if category_id:
                    self.create_metadata_field(
                        field_key,
                        field_name,
                        category_id,
                        data_type,
                        is_editable,
                        is_searchable,
                        display_format,
                        sort_order,
                    )

            logger.info("[DatabaseManager] Default metadata schema initialized")
            return True

        except Exception as e:
            logger.error(f"[DatabaseManager] Error initializing default metadata schema: {e}")
            return False

    # =====================================
    # Utility Methods
    # =====================================

    def get_database_stats(self) -> dict[str, int]:
        """Get database statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                stats = {}

                # Count records in each table
                tables = [
                    "file_paths",
                    "file_metadata",
                    "file_hashes",
                    "file_rename_history",
                    "metadata_categories",
                    "metadata_fields",
                    "file_metadata_structured",
                ]
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    row = cursor.fetchone()
                    stats[table] = row["count"] if row else 0

                return stats

        except Exception as e:
            logger.error(f"[DatabaseManager] Error getting database stats: {e}")
            return {}

    def close(self):
        """Close database connections."""
        # Connection pooling cleanup would go here if needed
        logger.debug("[DatabaseManager] Database connections closed", extra={"dev_only": True})


# =====================================
# Global Instance Management
# =====================================

_db_manager_v2_instance = None


def get_database_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager_v2_instance
    if _db_manager_v2_instance is None:
        _db_manager_v2_instance = DatabaseManager()
    return _db_manager_v2_instance


def initialize_database(db_path: str | None = None) -> DatabaseManager:
    """Initialize database manager with custom path."""
    global _db_manager_v2_instance
    _db_manager_v2_instance = DatabaseManager(db_path)
    return _db_manager_v2_instance
