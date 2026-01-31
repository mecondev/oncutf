"""Module: metadata_store.py.

Author: Michael Economou
Date: 2026-01-01

Metadata storage and retrieval for database operations.
Handles all metadata CRUD operations including structured metadata,
categories, fields, and color tags.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.infra.db.path_store import PathStore

logger = get_cached_logger(__name__)


class MetadataStore:
    """Manages metadata storage and retrieval in the database."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        path_store: PathStore,
        write_lock: threading.RLock,
    ):
        """Initialize MetadataStore with a database connection and path store.

        Args:
            connection: Active SQLite database connection
            path_store: PathStore instance for path management
            write_lock: Lock for thread-safe database access

        """
        self.connection = connection
        self.path_store = path_store
        self._write_lock = write_lock

    def store_metadata(
        self,
        file_path: str,
        metadata: dict[str, Any],
        is_extended: bool = False,
        is_modified: bool = False,
    ) -> bool:
        """Store metadata for a file."""
        try:
            with self._write_lock:
                path_id = self.path_store.get_or_create_path_id(file_path)

                cursor = self.connection.cursor()

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
                self.connection.commit()

                logger.debug(
                    "[MetadataStore] Stored %s metadata for: %s",
                    metadata_type,
                    Path(file_path).name,
                )
                return True

        except sqlite3.OperationalError as e:
            # Suppress errors during shutdown/cancellation
            logger.debug("[MetadataStore] Database locked/closing during store: %s", e)
            return False
        except Exception as e:
            logger.error("[MetadataStore] Error storing metadata for %s: %s", file_path, e)
            return False

    def batch_store_metadata(
        self,
        metadata_items: list[tuple[str, dict[str, Any], bool, bool]],
    ) -> int:
        """Store metadata for multiple files in a single batch operation.

        Args:
            metadata_items: List of (file_path, metadata_dict, is_extended, is_modified) tuples

        Returns:
            Number of files successfully stored

        """
        if not metadata_items:
            return 0

        try:
            success_count = 0

            cursor = self.connection.cursor()

            for file_path, metadata, is_extended, is_modified in metadata_items:
                try:
                    path_id = self.path_store.get_or_create_path_id(file_path)

                    # Remove existing metadata
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
                    success_count += 1

                except Exception as e:
                    logger.error(
                        "[MetadataStore] Error in batch storing metadata for %s: %s",
                        file_path,
                        e,
                    )
                    continue

            # Commit all inserts in one transaction
            self.connection.commit()

            logger.debug(
                "[MetadataStore] Batch stored metadata for %d/%d files",
                success_count,
                len(metadata_items),
            )
            return success_count

        except Exception as e:
            logger.error("[MetadataStore] Error in batch store metadata: %s", e)
            return 0

    def get_metadata(self, file_path: str) -> dict[str, Any] | None:
        """Retrieve metadata for a file."""
        try:
            with self._write_lock:
                path_id = self.path_store.get_path_id(file_path)
                if not path_id:
                    return None

                cursor = self.connection.cursor()
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

                metadata: dict[str, Any] = json.loads(row["metadata_json"])

                # Add metadata flags
                if row["metadata_type"] == "extended":
                    metadata["__extended__"] = True
                if row["is_modified"]:
                    metadata["__modified__"] = True

                return metadata

        except sqlite3.OperationalError as e:
            # Suppress errors during shutdown/cancellation
            logger.debug("[MetadataStore] Database locked/closing for %s: %s", file_path, e)
            return None
        except Exception as e:
            logger.error("[MetadataStore] Error retrieving metadata for %s: %s", file_path, e)
            return None

    def get_metadata_batch(self, file_paths: list[str]) -> dict[str, dict[str, Any] | None]:
        """Retrieve metadata for multiple files in a single batch operation.

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
                path_id = self.path_store.get_path_id(file_path)
                if path_id:
                    path_ids[path_id] = file_path

            if not path_ids:
                return dict.fromkeys(file_paths)

            # Batch query metadata
            cursor = self.connection.cursor()

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
            results: dict[str, dict[str, Any] | None] = {}
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
            logger.error("[MetadataStore] Error in batch metadata retrieval: %s", e)
            return dict.fromkeys(file_paths)

    def has_metadata(self, file_path: str, metadata_type: str | None = None) -> bool:
        """Check if file has metadata stored."""
        try:
            path_id = self.path_store.get_path_id(file_path)
            if not path_id:
                return False

            cursor = self.connection.cursor()

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
            logger.error("[MetadataStore] Error checking metadata for %s: %s", file_path, e)
            return False

    def create_metadata_category(
        self,
        category_name: str,
        display_name: str,
        description: str | None = None,
        sort_order: int = 0,
    ) -> int | None:
        """Create a new metadata category."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO metadata_categories
                (category_name, display_name, description, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (category_name, display_name, description, sort_order),
            )
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(
                "[MetadataStore] Error creating metadata category '%s': %s",
                category_name,
                e,
            )
            return None

    def get_metadata_categories(self) -> list[dict[str, Any]]:
        """Get all metadata categories ordered by sort_order."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT id, category_name, display_name, description, sort_order
                FROM metadata_categories
                ORDER BY sort_order, display_name
                """
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error("[MetadataStore] Error getting metadata categories: %s", e)
            return []

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
        """Create a new metadata field."""
        try:
            cursor = self.connection.cursor()
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
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error("[MetadataStore] Error creating metadata field '%s': %s", field_key, e)
            return None

    def get_metadata_fields(self, category_id: int | None = None) -> list[dict[str, Any]]:
        """Get metadata fields, optionally filtered by category."""
        try:
            cursor = self.connection.cursor()

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
            logger.error("[MetadataStore] Error getting metadata fields: %s", e)
            return []

    def get_metadata_field_by_key(self, field_key: str) -> dict[str, Any] | None:
        """Get a metadata field by its key."""
        try:
            cursor = self.connection.cursor()
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
            logger.error("[MetadataStore] Error getting metadata field '%s': %s", field_key, e)
            return None

    def store_structured_metadata(self, file_path: str, field_key: str, field_value: str) -> bool:
        """Store structured metadata for a file."""
        try:
            path_id = self.path_store.get_or_create_path_id(file_path)

            # Get field info
            field_info = self.get_metadata_field_by_key(field_key)
            if not field_info:
                logger.warning("[MetadataStore] Field '%s' not found in metadata_fields", field_key)
                return False

            cursor = self.connection.cursor()

            # Use INSERT OR REPLACE to handle updates
            cursor.execute(
                """
                INSERT OR REPLACE INTO file_metadata_structured
                (path_id, field_id, field_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (path_id, field_info["id"], field_value),
            )
            self.connection.commit()
            return True

        except Exception as e:
            logger.error(
                "[MetadataStore] Error storing structured metadata for %s: %s",
                file_path,
                e,
            )
            return False

    def batch_store_structured_metadata(
        self, file_path: str, field_data: list[tuple[str, str]]
    ) -> int:
        """Store multiple structured metadata fields for a file in a single batch operation.

        Args:
            file_path: Path to the file
            field_data: List of (field_key, field_value) tuples

        Returns:
            Number of fields successfully stored

        """
        if not field_data:
            return 0

        try:
            path_id = self.path_store.get_or_create_path_id(file_path)

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
                        "[MetadataStore] Field '%s' not found in metadata_fields - skipping",
                        field_key,
                    )

            if not valid_data:
                return 0

            # Batch insert using executemany
            cursor = self.connection.cursor()
            cursor.executemany(
                """
                INSERT OR REPLACE INTO file_metadata_structured
                (path_id, field_id, field_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                valid_data,
            )
            self.connection.commit()

            logger.debug(
                "[MetadataStore] Batch stored %d structured metadata fields",
                len(valid_data),
            )
            return len(valid_data)

        except Exception as e:
            logger.error(
                "[MetadataStore] Error in batch store structured metadata for %s: %s",
                file_path,
                e,
            )
            return 0

    def get_structured_metadata(self, file_path: str) -> dict[str, Any]:
        """Get structured metadata for a file."""
        try:
            path_id = self.path_store.get_path_id(file_path)
            if not path_id:
                return {}

            cursor = self.connection.cursor()
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
                "[MetadataStore] Error getting structured metadata for %s: %s",
                file_path,
                e,
            )
            return {}

    def set_color_tag(self, file_path: str, color_hex: str) -> bool:
        """Set color tag for a file.

        Args:
            file_path: File path
            color_hex: Hex color string (e.g., "#ff00aa") or "none"

        Returns:
            True if successful, False otherwise

        """
        try:
            # Validate and normalize color
            if color_hex != "none":
                color_hex = color_hex.lower()
                if not color_hex.startswith("#") or len(color_hex) != 7:
                    logger.warning("[MetadataStore] Invalid color hex: %s", color_hex)
                    return False

            path_id = self.path_store.get_or_create_path_id(file_path)

            cursor = self.connection.cursor()
            cursor.execute(
                """
                UPDATE file_paths
                SET color_tag = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (color_hex, path_id),
            )
            self.connection.commit()

            logger.debug("[MetadataStore] Set color_tag=%s for: %s", color_hex, file_path)
            return True

        except Exception as e:
            logger.error("[MetadataStore] Error setting color tag: %s", e)
            return False

    def get_color_tag(self, file_path: str) -> str:
        """Get color tag for a file.

        Args:
            file_path: File path

        Returns:
            Hex color string or "none" if not set

        """
        try:
            path_id = self.path_store.get_path_id(file_path)
            if not path_id:
                return "none"

            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT color_tag FROM file_paths WHERE id = ?
                """,
                (path_id,),
            )
            row = cursor.fetchone()

            if row and row["color_tag"]:
                color_tag: str = row["color_tag"]
                return color_tag
            return "none"

        except Exception as e:
            logger.error("[MetadataStore] Error getting color tag: %s", e)
            return "none"
