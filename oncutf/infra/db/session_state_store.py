"""Module: session_state_store.py.

Author: Michael Economou
Date: 2026-01-15

Session state storage for database operations.
Handles session state CRUD operations with ACID guarantees.

This store manages volatile session data that changes frequently:
- Sort column and order
- Last folder and recursive mode
- Column visibility and widths
- Recent folders list

Benefits over JSON:
- Atomic writes (no corruption on crash)
- Transaction support
- Faster updates (no full file rewrite)
"""

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


# Keys that are stored in session_state table
SESSION_STATE_KEYS = {
    "sort_column",
    "sort_order",
    "last_folder",
    "recursive_mode",
    "column_order",
    "columns_locked",
    "file_table_column_widths",
    "file_table_columns",
    "recent_folders",
    "metadata_tree_column_widths",
}


class SessionStateStore:
    """Manages session state storage in the database.

    Provides atomic, transaction-safe storage for volatile session data.
    Uses key-value pattern with JSON serialization for complex values.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        write_lock: threading.RLock,
    ):
        """Initialize SessionStateStore with a database connection.

        Args:
            connection: Active SQLite database connection
            write_lock: Lock for thread-safe database access

        """
        self.connection = connection
        self._write_lock = write_lock
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create session_state table if it doesn't exist."""
        try:
            with self._write_lock:
                cursor = self.connection.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS session_state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        value_type TEXT NOT NULL DEFAULT 'string',
                        updated_at TEXT NOT NULL
                    )
                """)
                self.connection.commit()
                logger.debug("[SessionStateStore] Table ensured")
        except sqlite3.Error as e:
            logger.error("[SessionStateStore] Failed to create table: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        """Get session state value by key.

        Args:
            key: The state key to retrieve
            default: Default value if key doesn't exist

        Returns:
            The stored value, deserialized from JSON if needed

        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT value, value_type FROM session_state WHERE key = ?", (key,))
            row = cursor.fetchone()

            if row is None:
                return default

            value, value_type = row

            # Deserialize based on type
            if value_type == "json":
                return json.loads(value)
            if value_type == "int":
                return int(value)
            if value_type == "float":
                return float(value)
            if value_type == "bool":
                return value.lower() == "true"
        except sqlite3.Error as e:
            logger.error("[SessionStateStore] Failed to get key '%s': %s", key, e)
            return default
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("[SessionStateStore] Failed to deserialize '%s': %s", key, e)
            return default
        else:
            return value

    def set(self, key: str, value: Any) -> bool:
        """Set session state value.

        Args:
            key: The state key to store
            value: The value to store (will be serialized if needed)

        Returns:
            True if successful, False otherwise

        """
        try:
            # Determine value type and serialize
            if isinstance(value, bool):
                value_type = "bool"
                serialized = str(value).lower()
            elif isinstance(value, int):
                value_type = "int"
                serialized = str(value)
            elif isinstance(value, float):
                value_type = "float"
                serialized = str(value)
            elif isinstance(value, dict | list):
                value_type = "json"
                serialized = json.dumps(value, ensure_ascii=False)
            else:
                value_type = "string"
                serialized = str(value) if value is not None else ""

            timestamp = datetime.now().isoformat()

            with self._write_lock:
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO session_state (key, value, value_type, updated_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (key, serialized, value_type, timestamp),
                )
                self.connection.commit()

            logger.debug(
                "[SessionStateStore] Set '%s' = %s (type: %s)",
                key,
                serialized[:50] + "..." if len(serialized) > 50 else serialized,
                value_type,
            )
        except sqlite3.Error as e:
            logger.error("[SessionStateStore] Failed to set key '%s': %s", key, e)
            return False
        except TypeError as e:
            logger.error("[SessionStateStore] Failed to serialize '%s': %s", key, e)
            return False
        else:
            return True

    def delete(self, key: str) -> bool:
        """Delete session state value.

        Args:
            key: The state key to delete

        Returns:
            True if successful, False otherwise

        """
        try:
            with self._write_lock:
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM session_state WHERE key = ?", (key,))
                self.connection.commit()
                deleted = cursor.rowcount > 0

            if deleted:
                logger.debug("[SessionStateStore] Deleted key '%s'", key)
        except sqlite3.Error as e:
            logger.error("[SessionStateStore] Failed to delete key '%s': %s", key, e)
            return False
        else:
            return deleted

    def get_all(self) -> dict[str, Any]:
        """Get all session state values.

        Returns:
            Dictionary of all key-value pairs

        """
        result: dict[str, Any] = {}
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT key, value, value_type FROM session_state")

            for key, value, value_type in cursor.fetchall():
                try:
                    if value_type == "json":
                        result[key] = json.loads(value)
                    elif value_type == "int":
                        result[key] = int(value)
                    elif value_type == "float":
                        result[key] = float(value)
                    elif value_type == "bool":
                        result[key] = value.lower() == "true"
                    else:
                        result[key] = value
                except (json.JSONDecodeError, ValueError):
                    result[key] = value

        except sqlite3.Error as e:
            logger.error("[SessionStateStore] Failed to get all: %s", e)

        return result

    def set_many(self, data: dict[str, Any]) -> bool:
        """Set multiple session state values atomically.

        Args:
            data: Dictionary of key-value pairs to store

        Returns:
            True if all successful, False if any failed

        """
        try:
            timestamp = datetime.now().isoformat()

            with self._write_lock:
                cursor = self.connection.cursor()

                for key, value in data.items():
                    # Determine value type and serialize
                    if isinstance(value, bool):
                        value_type = "bool"
                        serialized = str(value).lower()
                    elif isinstance(value, int):
                        value_type = "int"
                        serialized = str(value)
                    elif isinstance(value, float):
                        value_type = "float"
                        serialized = str(value)
                    elif isinstance(value, dict | list):
                        value_type = "json"
                        serialized = json.dumps(value, ensure_ascii=False)
                    else:
                        value_type = "string"
                        serialized = str(value) if value is not None else ""

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO session_state (key, value, value_type, updated_at)
                        VALUES (?, ?, ?, ?)
                    """,
                        (key, serialized, value_type, timestamp),
                    )

                self.connection.commit()

            logger.debug("[SessionStateStore] Set %d keys atomically", len(data))
        except sqlite3.Error as e:
            logger.error("[SessionStateStore] Failed to set_many: %s", e)
            return False
        else:
            return True

    def clear(self) -> bool:
        """Clear all session state values.

        Returns:
            True if successful, False otherwise

        """
        try:
            with self._write_lock:
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM session_state")
                self.connection.commit()

            logger.info("[SessionStateStore] Cleared all session state")
        except sqlite3.Error as e:
            logger.error("[SessionStateStore] Failed to clear: %s", e)
            return False
        else:
            return True

    def exists(self, key: str) -> bool:
        """Check if a key exists in session state.

        Args:
            key: The state key to check

        Returns:
            True if key exists, False otherwise

        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1 FROM session_state WHERE key = ? LIMIT 1", (key,))
            return cursor.fetchone() is not None

        except sqlite3.Error as e:
            logger.error("[SessionStateStore] Failed to check key '%s': %s", key, e)
            return False
