"""Filesystem operations service implementation.

Author: Michael Economou
Date: December 18, 2025

This module provides a concrete implementation of FilesystemServiceProtocol
for filesystem operations. It abstracts file operations with proper error
handling and cross-platform compatibility.

Usage:
    from oncutf.services.filesystem_service import FilesystemService

    service = FilesystemService()
    if service.file_exists(Path("/path/to/file.txt")):
        info = service.get_file_info(Path("/path/to/file.txt"))
        service.rename_file(source, target)
"""

from __future__ import annotations

import shutil
from datetime import datetime
from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from pathlib import Path

    from oncutf.services.interfaces import FilesystemServiceProtocol

logger = get_cached_logger(__name__)


class FilesystemService:
    """Filesystem operations service.

    Implements FilesystemServiceProtocol for dependency injection.
    Provides safe file operations with proper error handling.

    This is a Qt-free service that can be tested in isolation.
    """

    def __init__(self, backup_on_overwrite: bool = False) -> None:
        """Initialize the filesystem service.

        Args:
            backup_on_overwrite: If True, create backup before overwriting files.

        """
        self._backup_on_overwrite = backup_on_overwrite

    def rename_file(self, source: Path, target: Path) -> bool:
        """Rename a file atomically.

        Args:
            source: Current file path.
            target: New file path.

        Returns:
            True if successful, False otherwise.

        """
        if not source.exists():
            logger.error("Source file does not exist: %s", source)
            return False

        if not source.is_file():
            logger.error("Source is not a file: %s", source)
            return False

        # Create target directory if needed
        target_dir = target.parent
        if not target_dir.exists():
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                logger.debug("Created target directory: %s", target_dir)
            except OSError as e:
                logger.error("Failed to create target directory %s: %s", target_dir, e)
                return False

        # Handle existing target
        if target.exists():
            if self._backup_on_overwrite:
                backup_path = self._create_backup_path(target)
                try:
                    shutil.copy2(target, backup_path)
                    logger.debug("Created backup: %s", backup_path)
                except OSError as e:
                    logger.error("Failed to create backup: %s", e)
                    return False

        try:
            source.rename(target)
            logger.debug("Renamed %s -> %s", source.name, target.name)
            return True
        except OSError as e:
            logger.error("Failed to rename %s to %s: %s", source, target, e)
            return False

    def file_exists(self, path: Path) -> bool:
        """Check if a file exists.

        Args:
            path: Path to check.

        Returns:
            True if file exists and is a file (not directory).

        """
        return path.exists() and path.is_file()

    def directory_exists(self, path: Path) -> bool:
        """Check if a directory exists.

        Args:
            path: Path to check.

        Returns:
            True if path exists and is a directory.

        """
        return path.exists() and path.is_dir()

    def get_file_info(self, path: Path) -> dict[str, Any]:
        """Get file information (size, dates, etc.).

        Args:
            path: Path to the file.

        Returns:
            Dictionary with file info. Empty dict if file not found.
            Keys: name, size, mtime, ctime, atime, extension, is_symlink

        """
        if not path.exists():
            logger.warning("File not found: %s", path)
            return {}

        if not path.is_file():
            logger.warning("Path is not a file: %s", path)
            return {}

        try:
            stat = path.stat()
            return {
                "name": path.name,
                "stem": path.stem,
                "extension": path.suffix,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "ctime": stat.st_ctime,
                "atime": stat.st_atime,
                "mtime_datetime": datetime.fromtimestamp(stat.st_mtime),
                "ctime_datetime": datetime.fromtimestamp(stat.st_ctime),
                "is_symlink": path.is_symlink(),
                "parent": str(path.parent),
                "full_path": str(path.absolute()),
            }
        except OSError as e:
            logger.error("Error getting file info for %s: %s", path, e)
            return {}

    def copy_file(self, source: Path, target: Path) -> bool:
        """Copy a file preserving metadata.

        Args:
            source: Source file path.
            target: Target file path.

        Returns:
            True if successful, False otherwise.

        """
        if not source.exists():
            logger.error("Source file does not exist: %s", source)
            return False

        if not source.is_file():
            logger.error("Source is not a file: %s", source)
            return False

        # Create target directory if needed
        target_dir = target.parent
        if not target_dir.exists():
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.error("Failed to create target directory %s: %s", target_dir, e)
                return False

        try:
            shutil.copy2(source, target)
            logger.debug("Copied %s -> %s", source, target)
            return True
        except OSError as e:
            logger.error("Failed to copy %s to %s: %s", source, target, e)
            return False

    def delete_file(self, path: Path) -> bool:
        """Delete a file.

        Args:
            path: Path to the file to delete.

        Returns:
            True if successful, False otherwise.

        """
        if not path.exists():
            logger.warning("File does not exist: %s", path)
            return True  # Already doesn't exist

        if not path.is_file():
            logger.error("Path is not a file: %s", path)
            return False

        try:
            path.unlink()
            logger.debug("Deleted file: %s", path)
            return True
        except OSError as e:
            logger.error("Failed to delete %s: %s", path, e)
            return False

    def list_directory(
        self,
        path: Path,
        pattern: str = "*",
        recursive: bool = False,
    ) -> list[Path]:
        """List files in a directory.

        Args:
            path: Directory path.
            pattern: Glob pattern for filtering files.
            recursive: Whether to search recursively.

        Returns:
            List of matching file paths.

        """
        if not path.exists():
            logger.warning("Directory does not exist: %s", path)
            return []

        if not path.is_dir():
            logger.warning("Path is not a directory: %s", path)
            return []

        try:
            if recursive:
                return list(path.rglob(pattern))
            else:
                return list(path.glob(pattern))
        except OSError as e:
            logger.error("Error listing directory %s: %s", path, e)
            return []

    def get_free_space(self, path: Path) -> int:
        """Get free space on the filesystem containing path.

        Args:
            path: Path on the target filesystem.

        Returns:
            Free space in bytes, or -1 on error.

        """
        try:
            if path.is_file():
                path = path.parent
            usage = shutil.disk_usage(path)
            return usage.free
        except OSError as e:
            logger.error("Error getting free space for %s: %s", path, e)
            return -1

    def _create_backup_path(self, path: Path) -> Path:
        """Create a unique backup path for a file.

        Args:
            path: Original file path.

        Returns:
            Backup path with timestamp suffix.

        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.stem}_backup_{timestamp}{path.suffix}"
        return path.parent / backup_name


# Type assertion to verify protocol compliance
def _verify_protocol_compliance() -> None:
    """Verify that FilesystemService implements FilesystemServiceProtocol."""
    service: FilesystemServiceProtocol = FilesystemService()
    _ = service  # Unused, just for type checking
