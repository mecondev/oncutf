"""
database_manager.py

Author: Michael Economou
Date: 2025-01-27

Comprehensive database management system for oncutf application.
Handles metadata storage, hash caching, and rename history tracking.

Features:
- SQLite backend for persistent storage
- Metadata caching with extended/fast mode tracking
- File hash storage with CRC32 algorithm support
- Rename history tracking for undo/redo operations
- Automatic schema migrations and maintenance
- Thread-safe operations with connection pooling
"""

import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class DatabaseManager:
    """
    Centralized database management for oncutf application.

    Manages three main data types:
    1. File metadata (EXIF, extended metadata)
    2. File hashes (CRC32 checksums)
    3. Rename history (for undo/redo operations)
    """

    # Database schema version for migrations
    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize DatabaseManager with SQLite backend.

        Args:
            db_path: Custom database path, defaults to user data directory
        """
        self._lock = threading.RLock()
        self._connections = {}  # Thread-local connections

        # Set up database path
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Default to user data directory
            data_dir = self._get_user_data_directory()
            self.db_path = data_dir / "oncutf_data.db"

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._initialize_database()

        logger.info(f"[DatabaseManager] Initialized with database: {self.db_path}")

    def _get_user_data_directory(self) -> Path:
        """Get appropriate user data directory for the current OS."""
        if os.name == 'nt':  # Windows
            data_dir = Path(os.environ.get('APPDATA', '')) / 'oncutf'
        else:  # Linux/macOS
            home = Path.home()
            data_dir = home / '.local' / 'share' / 'oncutf'

        return data_dir

    @contextmanager
    def _get_connection(self):
        """Get thread-safe database connection with automatic cleanup."""
        thread_id = threading.current_thread().ident

        with self._lock:
            if thread_id not in self._connections:
                conn = sqlite3.connect(
                    str(self.db_path),
                    check_same_thread=False,
                    timeout=30.0
                )
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
                conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
                self._connections[thread_id] = conn

            conn = self._connections[thread_id]

        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.commit()

    def _initialize_database(self):
        """Initialize database schema and perform migrations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create schema version table first
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Check current schema version
            cursor.execute("SELECT value FROM schema_info WHERE key = 'version'")
            row = cursor.fetchone()
            current_version = int(row['value']) if row else 0

            # Perform migrations if needed
            if current_version < self.SCHEMA_VERSION:
                self._migrate_schema(cursor, current_version)

                # Update schema version
                cursor.execute("""
                    INSERT OR REPLACE INTO schema_info (key, value)
                    VALUES ('version', ?)
                """, (str(self.SCHEMA_VERSION),))

            # Create indexes for performance
            self._create_indexes(cursor)

            logger.debug(f"[DatabaseManager] Schema initialized (version {self.SCHEMA_VERSION})")

    def _migrate_schema(self, cursor: sqlite3.Cursor, from_version: int):
        """Perform database schema migrations."""
        logger.info(f"[DatabaseManager] Migrating schema from version {from_version} to {self.SCHEMA_VERSION}")

        if from_version == 0:
            # Initial schema creation
            self._create_initial_schema(cursor)

        # Add future migration steps here as needed
        # if from_version < 2:
        #     self._migrate_to_version_2(cursor)

    def _create_initial_schema(self, cursor: sqlite3.Cursor):
        """Create initial database schema."""

        # Files table - tracks all files we've seen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                file_size INTEGER,
                modified_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Metadata table - stores file metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                metadata_type TEXT NOT NULL DEFAULT 'fast',  -- 'fast' or 'extended'
                metadata_json TEXT NOT NULL,  -- JSON blob of metadata
                is_modified BOOLEAN DEFAULT FALSE,  -- User modifications flag
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
            )
        """)

        # Hashes table - stores file hashes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                algorithm TEXT NOT NULL DEFAULT 'CRC32',
                hash_value TEXT NOT NULL,
                file_size_at_hash INTEGER,  -- File size when hash was calculated
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
            )
        """)

        # Rename history table - tracks rename operations for undo/redo
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rename_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT NOT NULL,  -- UUID for grouping related renames
                file_id INTEGER NOT NULL,
                old_path TEXT NOT NULL,
                new_path TEXT NOT NULL,
                old_filename TEXT NOT NULL,
                new_filename TEXT NOT NULL,
                operation_type TEXT NOT NULL DEFAULT 'rename',  -- 'rename', 'undo', 'redo'
                modules_data TEXT,  -- JSON of modules used for this rename
                post_transform_data TEXT,  -- JSON of post-transform settings
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
            )
        """)

        logger.debug("[DatabaseManager] Initial schema created")

    def _create_indexes(self, cursor: sqlite3.Cursor):
        """Create database indexes for performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_files_path ON files (file_path)",
            "CREATE INDEX IF NOT EXISTS idx_files_filename ON files (filename)",
            "CREATE INDEX IF NOT EXISTS idx_metadata_file_id ON metadata (file_id)",
            "CREATE INDEX IF NOT EXISTS idx_metadata_type ON metadata (metadata_type)",
            "CREATE INDEX IF NOT EXISTS idx_hashes_file_id ON hashes (file_id)",
            "CREATE INDEX IF NOT EXISTS idx_hashes_algorithm ON hashes (algorithm)",
            "CREATE INDEX IF NOT EXISTS idx_rename_history_operation_id ON rename_history (operation_id)",
            "CREATE INDEX IF NOT EXISTS idx_rename_history_file_id ON rename_history (file_id)",
            "CREATE INDEX IF NOT EXISTS idx_rename_history_created_at ON rename_history (created_at)",
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

        logger.debug("[DatabaseManager] Database indexes created")

    # =====================================
    # File Management
    # =====================================

    def add_or_update_file(self, file_path: str, filename: str, file_size: Optional[int] = None) -> int:
        """
        Add or update file record in database.

        Args:
            file_path: Full path to the file
            filename: Base filename
            file_size: File size in bytes

        Returns:
            File ID in database
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get file modification time
            modified_time = None
            try:
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    modified_time = datetime.fromtimestamp(stat.st_mtime)
                    if file_size is None:
                        file_size = stat.st_size
            except OSError:
                pass

            # Insert or update file record
            cursor.execute("""
                INSERT OR REPLACE INTO files
                (file_path, filename, file_size, modified_time, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (file_path, filename, file_size, modified_time))

            # Get the file ID
            cursor.execute("SELECT id FROM files WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            file_id = row['id'] if row else cursor.lastrowid

            return file_id

    def get_file_id(self, file_path: str) -> Optional[int]:
        """Get file ID for a given path."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM files WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            return row['id'] if row else None

    def remove_file(self, file_path: str) -> bool:
        """
        Remove file and all associated data from database.

        Args:
            file_path: Path to the file to remove

        Returns:
            True if file was removed, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE file_path = ?", (file_path,))
            return cursor.rowcount > 0

    # =====================================
    # Metadata Management
    # =====================================

    def store_metadata(self, file_path: str, metadata: Dict[str, Any],
                      is_extended: bool = False, is_modified: bool = False) -> bool:
        """
        Store metadata for a file.

        Args:
            file_path: Path to the file
            metadata: Metadata dictionary
            is_extended: Whether this is extended metadata
            is_modified: Whether metadata has been modified by user

        Returns:
            True if stored successfully
        """
        try:
            # Ensure file exists in database
            filename = os.path.basename(file_path)
            file_id = self.add_or_update_file(file_path, filename)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Remove existing metadata for this file
                cursor.execute("DELETE FROM metadata WHERE file_id = ?", (file_id,))

                # Store new metadata
                metadata_type = 'extended' if is_extended else 'fast'
                metadata_json = json.dumps(metadata, ensure_ascii=False, indent=None)

                cursor.execute("""
                    INSERT INTO metadata
                    (file_id, metadata_type, metadata_json, is_modified)
                    VALUES (?, ?, ?, ?)
                """, (file_id, metadata_type, metadata_json, is_modified))

                logger.debug(f"[DatabaseManager] Stored {metadata_type} metadata for: {filename}")
                return True

        except Exception as e:
            logger.error(f"[DatabaseManager] Error storing metadata for {file_path}: {e}")
            return False

    def get_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata for a file.

        Args:
            file_path: Path to the file

        Returns:
            Metadata dictionary or None if not found
        """
        try:
            file_id = self.get_file_id(file_path)
            if not file_id:
                return None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT metadata_json, metadata_type, is_modified
                    FROM metadata
                    WHERE file_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (file_id,))

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
        """
        Check if file has metadata stored.

        Args:
            file_path: Path to the file
            metadata_type: Optional filter by 'fast' or 'extended'

        Returns:
            True if metadata exists
        """
        try:
            file_id = self.get_file_id(file_path)
            if not file_id:
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()

                if metadata_type:
                    cursor.execute("""
                        SELECT 1 FROM metadata
                        WHERE file_id = ? AND metadata_type = ?
                        LIMIT 1
                    """, (file_id, metadata_type))
                else:
                    cursor.execute("""
                        SELECT 1 FROM metadata
                        WHERE file_id = ?
                        LIMIT 1
                    """, (file_id,))

                return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"[DatabaseManager] Error checking metadata for {file_path}: {e}")
            return False

    def update_metadata_modified_flag(self, file_path: str, is_modified: bool) -> bool:
        """
        Update the modified flag for file metadata.

        Args:
            file_path: Path to the file
            is_modified: New modified state

        Returns:
            True if updated successfully
        """
        try:
            file_id = self.get_file_id(file_path)
            if not file_id:
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE metadata
                    SET is_modified = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE file_id = ?
                """, (is_modified, file_id))

                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"[DatabaseManager] Error updating metadata flag for {file_path}: {e}")
            return False

    # =====================================
    # Hash Management
    # =====================================

    def store_hash(self, file_path: str, hash_value: str, algorithm: str = 'CRC32') -> bool:
        """
        Store file hash.

        Args:
            file_path: Path to the file
            hash_value: Calculated hash value
            algorithm: Hash algorithm used

        Returns:
            True if stored successfully
        """
        try:
            # Ensure file exists in database
            filename = os.path.basename(file_path)
            file_size = None
            try:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
            except OSError:
                pass

            file_id = self.add_or_update_file(file_path, filename, file_size)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Remove existing hash for this file and algorithm
                cursor.execute("""
                    DELETE FROM hashes
                    WHERE file_id = ? AND algorithm = ?
                """, (file_id, algorithm))

                # Store new hash
                cursor.execute("""
                    INSERT INTO hashes
                    (file_id, algorithm, hash_value, file_size_at_hash)
                    VALUES (?, ?, ?, ?)
                """, (file_id, algorithm, hash_value, file_size))

                logger.debug(f"[DatabaseManager] Stored {algorithm} hash for: {filename}")
                return True

        except Exception as e:
            logger.error(f"[DatabaseManager] Error storing hash for {file_path}: {e}")
            return False

    def get_hash(self, file_path: str, algorithm: str = 'CRC32') -> Optional[str]:
        """
        Retrieve file hash.

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm

        Returns:
            Hash value or None if not found
        """
        try:
            file_id = self.get_file_id(file_path)
            if not file_id:
                return None

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT hash_value FROM hashes
                    WHERE file_id = ? AND algorithm = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (file_id, algorithm))

                row = cursor.fetchone()
                return row['hash_value'] if row else None

        except Exception as e:
            logger.error(f"[DatabaseManager] Error retrieving hash for {file_path}: {e}")
            return None

    def has_hash(self, file_path: str, algorithm: str = 'CRC32') -> bool:
        """
        Check if file has hash stored.

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm

        Returns:
            True if hash exists
        """
        try:
            file_id = self.get_file_id(file_path)
            if not file_id:
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM hashes
                    WHERE file_id = ? AND algorithm = ?
                    LIMIT 1
                """, (file_id, algorithm))

                return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"[DatabaseManager] Error checking hash for {file_path}: {e}")
            return False

    # =====================================
    # Rename History Management
    # =====================================

    def record_rename_operation(self, operation_id: str, renames: List[Tuple[str, str]],
                              modules_data: Optional[List[Dict]] = None,
                              post_transform_data: Optional[Dict] = None) -> bool:
        """
        Record a batch rename operation for undo/redo functionality.

        Args:
            operation_id: Unique ID for this batch operation
            renames: List of (old_path, new_path) tuples
            modules_data: Modules configuration used
            post_transform_data: Post-transform settings used

        Returns:
            True if recorded successfully
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Convert data to JSON
                modules_json = json.dumps(modules_data) if modules_data else None
                post_transform_json = json.dumps(post_transform_data) if post_transform_data else None

                for old_path, new_path in renames:
                    # Ensure both old and new paths are in files table
                    old_filename = os.path.basename(old_path)
                    new_filename = os.path.basename(new_path)

                    old_file_id = self.add_or_update_file(old_path, old_filename)

                    # Record the rename operation
                    cursor.execute("""
                        INSERT INTO rename_history
                        (operation_id, file_id, old_path, new_path, old_filename, new_filename,
                         operation_type, modules_data, post_transform_data)
                        VALUES (?, ?, ?, ?, ?, ?, 'rename', ?, ?)
                    """, (operation_id, old_file_id, old_path, new_path,
                         old_filename, new_filename, modules_json, post_transform_json))

                logger.info(f"[DatabaseManager] Recorded rename operation {operation_id} with {len(renames)} files")
                return True

        except Exception as e:
            logger.error(f"[DatabaseManager] Error recording rename operation: {e}")
            return False

    def get_rename_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent rename operations for undo functionality.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of operation dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT operation_id,
                           MIN(created_at) as operation_time,
                           COUNT(*) as file_count,
                           operation_type
                    FROM rename_history
                    GROUP BY operation_id
                    ORDER BY operation_time DESC
                    LIMIT ?
                """, (limit,))

                operations = []
                for row in cursor.fetchall():
                    operations.append({
                        'operation_id': row['operation_id'],
                        'operation_time': row['operation_time'],
                        'file_count': row['file_count'],
                        'operation_type': row['operation_type']
                    })

                return operations

        except Exception as e:
            logger.error(f"[DatabaseManager] Error retrieving rename history: {e}")
            return []

    def get_operation_details(self, operation_id: str) -> List[Dict[str, Any]]:
        """
        Get detailed information about a specific rename operation.

        Args:
            operation_id: ID of the operation

        Returns:
            List of rename details
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT old_path, new_path, old_filename, new_filename,
                           modules_data, post_transform_data, created_at
                    FROM rename_history
                    WHERE operation_id = ?
                    ORDER BY created_at
                """, (operation_id,))

                details = []
                for row in cursor.fetchall():
                    modules_data = json.loads(row['modules_data']) if row['modules_data'] else None
                    post_transform_data = json.loads(row['post_transform_data']) if row['post_transform_data'] else None

                    details.append({
                        'old_path': row['old_path'],
                        'new_path': row['new_path'],
                        'old_filename': row['old_filename'],
                        'new_filename': row['new_filename'],
                        'modules_data': modules_data,
                        'post_transform_data': post_transform_data,
                        'created_at': row['created_at']
                    })

                return details

        except Exception as e:
            logger.error(f"[DatabaseManager] Error retrieving operation details: {e}")
            return []

    # =====================================
    # Maintenance and Utilities
    # =====================================

    def cleanup_orphaned_records(self) -> int:
        """
        Clean up database records for files that no longer exist.

        Returns:
            Number of records cleaned up
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get all file paths
                cursor.execute("SELECT id, file_path FROM files")
                files = cursor.fetchall()

                orphaned_ids = []
                for file_row in files:
                    if not os.path.exists(file_row['file_path']):
                        orphaned_ids.append(file_row['id'])

                if orphaned_ids:
                    # Delete orphaned files (cascade will handle related records)
                    placeholders = ','.join('?' * len(orphaned_ids))
                    cursor.execute(f"DELETE FROM files WHERE id IN ({placeholders})", orphaned_ids)

                    logger.info(f"[DatabaseManager] Cleaned up {len(orphaned_ids)} orphaned records")

                return len(orphaned_ids)

        except Exception as e:
            logger.error(f"[DatabaseManager] Error during cleanup: {e}")
            return 0

    def get_database_stats(self) -> Dict[str, int]:
        """
        Get database statistics.

        Returns:
            Dictionary with record counts
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                stats = {}
                tables = ['files', 'metadata', 'hashes', 'rename_history']

                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    row = cursor.fetchone()
                    stats[table] = row['count'] if row else 0

                return stats

        except Exception as e:
            logger.error(f"[DatabaseManager] Error getting database stats: {e}")
            return {}

    def close(self):
        """Close all database connections."""
        with self._lock:
            for conn in self._connections.values():
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()

        logger.debug("[DatabaseManager] All connections closed")


# Global instance for easy access
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get global DatabaseManager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def initialize_database(db_path: Optional[str] = None) -> DatabaseManager:
    """Initialize global DatabaseManager with custom path."""
    global _db_manager
    _db_manager = DatabaseManager(db_path)
    return _db_manager
