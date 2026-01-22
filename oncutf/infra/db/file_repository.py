"""File repository for database operations.

Extracts database operations from FileItem model to break models→core cycle.

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileRepository:
    """Repository for file-related database operations.

    This repository breaks the models→core cycle by moving database
    operations out of FileItem and into the infrastructure layer.

    FileItem becomes a pure data model, while this repository handles
    persistence concerns.
    """

    def __init__(self, db_manager: Any) -> None:
        """Initialize repository with database manager.

        Args:
            db_manager: Database manager instance (typed as Any to avoid import)
        """
        self._db = db_manager

    def get_folder_id(self, folder_path: str | Path) -> int | None:
        """Get folder ID for a given path.

        Args:
            folder_path: Path to folder

        Returns:
            Folder ID or None if not found
        """
        try:
            return self._db.get_folder_id(str(folder_path))
        except Exception as e:
            logger.warning("Error getting folder ID for %s: %s", folder_path, e)
            return None

    def ensure_folder_exists(self, folder_path: str | Path) -> int | None:
        """Ensure folder exists in database, creating if needed.

        Args:
            folder_path: Path to folder

        Returns:
            Folder ID or None on error
        """
        try:
            folder_id = self.get_folder_id(folder_path)
            if folder_id is not None:
                return folder_id

            # Create folder in database
            return self._db.add_folder(str(folder_path))
        except Exception as e:
            logger.error("Error ensuring folder exists for %s: %s", folder_path, e)
            return None

    def get_file_hash(self, file_path: str | Path) -> str | None:
        """Get stored hash for a file.

        Args:
            file_path: Path to file

        Returns:
            File hash or None if not found
        """
        try:
            return self._db.get_file_hash(str(file_path))
        except Exception as e:
            logger.warning("Error getting file hash for %s: %s", file_path, e)
            return None

    def store_file_hash(self, file_path: str | Path, hash_value: str) -> bool:
        """Store file hash in database.

        Args:
            file_path: Path to file
            hash_value: Hash value to store

        Returns:
            True if successful, False otherwise
        """
        try:
            self._db.store_file_hash(str(file_path), hash_value)
            return True
        except Exception as e:
            logger.error("Error storing file hash for %s: %s", file_path, e)
            return False

    def get_color_tag(self, file_path: str | Path) -> str:
        """Get color tag for a file.

        Args:
            file_path: Path to file

        Returns:
            Color tag (hex color) or "none" if not found
        """
        try:
            return self._db.get_color_tag(str(file_path))
        except Exception as e:
            logger.warning("Error getting color tag for %s: %s", file_path, e)
            return "none"

    def set_color_tag(self, file_path: str | Path, color: str) -> bool:
        """Set color tag for a file.

        Args:
            file_path: Path to file
            color: Color tag (hex color or "none")

        Returns:
            True if successful, False otherwise
        """
        try:
            self._db.set_color_tag(str(file_path), color)
            return True
        except Exception as e:
            logger.error("Error setting color tag for %s: %s", file_path, e)
            return False


# Global instance (singleton pattern)
_file_repository: FileRepository | None = None


def get_file_repository() -> FileRepository:
    """Get the global file repository instance.

    Lazy initialization - creates repository when first accessed.

    Returns:
        Singleton FileRepository instance
    """
    global _file_repository
    if _file_repository is None:
        # Import here to avoid circular dependency
        from oncutf.core.database.database_manager import get_database_manager

        _file_repository = FileRepository(get_database_manager())
    return _file_repository


def set_file_repository(repository: FileRepository) -> None:
    """Set a custom file repository (useful for testing).

    Args:
        repository: Custom FileRepository instance
    """
    global _file_repository
    _file_repository = repository
