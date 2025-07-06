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
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logger_factory import get_cached_logger

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
    SCHEMA_VERSION = 2

    def __init__(self, db_path: Optional[str] = None):
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

        self._initialize_database()
        logger.info(f"[DatabaseManager] Initialized with database: {self.db_path}")

    def _get_user_data_directory(self) -> Path:
        """Get user data directory for storing database."""
        if os.name == 'nt':  # Windows
            data_dir = Path.home() / "AppData" / "Local" / "oncutf"
        else:  # Linux/macOS
            data_dir = Path.home() / ".local" / "share" / "oncutf"
        return data_dir

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper configuration."""
        conn = None
        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False
            )
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

    def _initialize_database(self):
        """Initialize database with schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check current schema version
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_info (
                    version INTEGER PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("SELECT version FROM schema_info ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            current_version = row['version'] if row else 0

            if current_version < self.SCHEMA_VERSION:
                if current_version == 0:
                    self._create_schema_v2(cursor)
                else:
                    self._migrate_schema(cursor, current_version)

                # Update schema version
                cursor.execute("""
                    INSERT OR REPLACE INTO schema_info (version, updated_at)
                    VALUES (?, CURRENT_TIMESTAMP)
                """, (self.SCHEMA_VERSION,))

            self._create_indexes(cursor)
            conn.commit()

        logger.debug(f"[DatabaseManager] Schema initialized (version {self.SCHEMA_VERSION})")

    def _create_schema_v2(self, cursor: sqlite3.Cursor):
        """Create the new v2 schema with separated tables."""

        # 1. Central file paths table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                file_size INTEGER,
                modified_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Dedicated metadata table
        cursor.execute("""
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
        """)

        # 3. Dedicated hash table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_id INTEGER NOT NULL,
                algorithm TEXT NOT NULL DEFAULT 'CRC32',
                hash_value TEXT NOT NULL,
                file_size_at_hash INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (path_id) REFERENCES file_paths (id) ON DELETE CASCADE
            )
        """)

        # 4. Dedicated rename history table
        cursor.execute("""
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
        """)

        logger.debug("[DatabaseManager] Schema v2 created")

    def _migrate_schema(self, cursor: sqlite3.Cursor, from_version: int):
        """Migrate from older schema versions."""
        # Future migrations will go here
        logger.info(f"[DatabaseManager] Migrating from version {from_version} to {self.SCHEMA_VERSION}")

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
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

        logger.debug("[DatabaseManager] Database indexes created")

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
                return row['id']

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

            cursor.execute("""
                INSERT INTO file_paths
                (file_path, filename, file_size, modified_time, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (norm_path, filename, file_size, modified_time))

            # Make sure to commit the transaction
            conn.commit()

            path_id = cursor.lastrowid
            if path_id is None:
                raise RuntimeError(f"Failed to create path record for: {norm_path}")

            return path_id

    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path for consistent storage."""
        try:
            abs_path = os.path.abspath(file_path)
            return os.path.normpath(abs_path)
        except Exception:
            return os.path.normpath(file_path)

    def get_path_id(self, file_path: str) -> Optional[int]:
        """Get path_id for a file without creating it."""
        norm_path = self._normalize_path(file_path)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM file_paths WHERE file_path = ?", (norm_path,))
            row = cursor.fetchone()
            return row['id'] if row else None

    # =====================================
    # Metadata Management
    # =====================================

    def store_metadata(self, file_path: str, metadata: Dict[str, Any],
                      is_extended: bool = False, is_modified: bool = False) -> bool:
        """Store metadata for a file."""
        try:
            path_id = self.get_or_create_path_id(file_path)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Remove existing metadata for this path
                cursor.execute("DELETE FROM file_metadata WHERE path_id = ?", (path_id,))

                # Store new metadata
                metadata_type = 'extended' if is_extended else 'fast'
                metadata_json = json.dumps(metadata, ensure_ascii=False, indent=None)

                cursor.execute("""
                    INSERT INTO file_metadata
                    (path_id, metadata_type, metadata_json, is_modified)
                    VALUES (?, ?, ?, ?)
                """, (path_id, metadata_type, metadata_json, is_modified))

                # Commit the transaction
                conn.commit()

                logger.debug(f"[DatabaseManager] Stored {metadata_type} metadata for: {os.path.basename(file_path)}")
                return True

        except Exception as e:
            logger.error(f"[DatabaseManager] Error storing metadata for {file_path}: {e}")
            return False

    def get_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a file."""
        try:
            path_id = self.get_path_id(file_path)
            if not path_id:
                return None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT metadata_json, metadata_type, is_modified
                    FROM file_metadata
                    WHERE path_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (path_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                metadata = json.loads(row['metadata_json'])

                # Add metadata flags
                if row['metadata_type'] == 'extended':
                    metadata['__extended__'] = True
                if row['is_modified']:
                    metadata['__modified__'] = True

                return metadata

        except Exception as e:
            logger.error(f"[DatabaseManager] Error retrieving metadata for {file_path}: {e}")
            return None

    def has_metadata(self, file_path: str, metadata_type: Optional[str] = None) -> bool:
        """Check if file has metadata stored."""
        try:
            path_id = self.get_path_id(file_path)
            if not path_id:
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()

                if metadata_type:
                    cursor.execute("""
                        SELECT 1 FROM file_metadata
                        WHERE path_id = ? AND metadata_type = ?
                        LIMIT 1
                    """, (path_id, metadata_type))
                else:
                    cursor.execute("""
                        SELECT 1 FROM file_metadata
                        WHERE path_id = ?
                        LIMIT 1
                    """, (path_id,))

                return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"[DatabaseManager] Error checking metadata for {file_path}: {e}")
            return False

    # =====================================
    # Hash Management
    # =====================================

    def store_hash(self, file_path: str, hash_value: str, algorithm: str = 'CRC32') -> bool:
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
                cursor.execute("""
                    DELETE FROM file_hashes
                    WHERE path_id = ? AND algorithm = ?
                """, (path_id, algorithm))

                # Store new hash
                cursor.execute("""
                    INSERT INTO file_hashes
                    (path_id, algorithm, hash_value, file_size_at_hash)
                    VALUES (?, ?, ?, ?)
                """, (path_id, algorithm, hash_value, file_size))

                # Commit the transaction
                conn.commit()

                logger.debug(f"[DatabaseManager] Stored {algorithm} hash for: {os.path.basename(file_path)}")
                return True

        except Exception as e:
            logger.error(f"[DatabaseManager] Error storing hash for {file_path}: {e}")
            return False

    def get_hash(self, file_path: str, algorithm: str = 'CRC32') -> Optional[str]:
        """Retrieve file hash."""
        try:
            path_id = self.get_path_id(file_path)
            if not path_id:
                return None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT hash_value FROM file_hashes
                    WHERE path_id = ? AND algorithm = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (path_id, algorithm))

                row = cursor.fetchone()
                return row['hash_value'] if row else None

        except Exception as e:
            logger.error(f"[DatabaseManager] Error retrieving hash for {file_path}: {e}")
            return None

    def has_hash(self, file_path: str, algorithm: str = 'CRC32') -> bool:
        """Check if file has hash stored."""
        try:
            path_id = self.get_path_id(file_path)
            if not path_id:
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM file_hashes
                    WHERE path_id = ? AND algorithm = ?
                    LIMIT 1
                """, (path_id, algorithm))

                return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"[DatabaseManager] Error checking hash for {file_path}: {e}")
            return False

    # =====================================
    # Utility Methods
    # =====================================

    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                stats = {}

                # Count records in each table
                tables = ['file_paths', 'file_metadata', 'file_hashes', 'file_rename_history']
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    row = cursor.fetchone()
                    stats[table] = row['count'] if row else 0

                return stats

        except Exception as e:
            logger.error(f"[DatabaseManager] Error getting database stats: {e}")
            return {}

    def close(self):
        """Close database connections."""
        # Connection pooling cleanup would go here if needed
        logger.debug("[DatabaseManager] Database connections closed")


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

def initialize_database(db_path: Optional[str] = None) -> DatabaseManager:
    """Initialize database manager with custom path."""
    global _db_manager_v2_instance
    _db_manager_v2_instance = DatabaseManager(db_path)
    return _db_manager_v2_instance
