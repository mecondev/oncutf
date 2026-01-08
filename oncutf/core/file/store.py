"""Module: file_store.py

Author: Michael Economou
Date: 2025-05-31

Centralized state management for loaded files.

Provides single source of truth for:
- Loaded files list
- Current folder path
- File filtering by extension
- Folder cache (folder path → FileItem list)
- State change signals

Note: This is a state-only module. I/O operations are in FileLoadManager.
"""

import os
from typing import Any

from oncutf.core.pyqt_imports import QObject, pyqtSignal
from oncutf.models.file_item import FileItem
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileStore(QObject):
    """Centralized STATE management for loaded files.

    This class maintains the single source of truth for:
    - Currently loaded files (_loaded_files)
    - Current folder path (_current_folder)
    - Folder-to-FileItem cache (_file_cache)

    It does NOT perform I/O operations. File scanning/loading is done by FileLoadManager.
    This separation enables:
    - Better testability (mock state without I/O)
    - Clear backend/frontend separation
    - UI-agnostic state management
    """

    # Signals for file operations
    files_loaded = pyqtSignal(list)  # Emitted when files are loaded
    folder_changed = pyqtSignal(str)  # Emitted when current folder changes
    files_filtered = pyqtSignal(list)  # Emitted when files are filtered

    def __init__(self, parent: QObject | None = None):
        """Initialize the file store with empty state."""
        super().__init__(parent)

        # Current state
        self._current_folder: str | None = None
        self._loaded_files: list[FileItem] = []
        self._file_cache: dict[str, list[FileItem]] = {}

        logger.debug("[FileStore] Initialized (state-only mode)", extra={"dev_only": True})

    # =====================================
    # State Management (Core Responsibility)
    # =====================================

    def get_loaded_files(self) -> list[FileItem]:
        """Get currently loaded files (returns copy for immutability)."""
        return self._loaded_files.copy()

    def set_loaded_files(self, files: list[FileItem]) -> None:
        """Set loaded files and emit signal.

        Args:
            files: List of FileItem objects to set as loaded

        """
        self._loaded_files = files.copy() if files else []
        self.files_loaded.emit(self._loaded_files)
        logger.debug("[FileStore] Loaded files set: %d files", len(self._loaded_files))

    def get_current_folder(self) -> str | None:
        """Get current folder path."""
        return self._current_folder

    def set_current_folder(self, folder_path: str) -> None:
        """Set current folder and emit signal if changed."""
        old_folder = self._current_folder
        self._current_folder = folder_path

        if old_folder != folder_path:
            self.folder_changed.emit(folder_path)
            logger.debug("[FileStore] Current folder changed: %s", folder_path)

    def clear_files(self) -> None:
        """Clear all loaded files and emit signal."""
        self._loaded_files.clear()
        self.files_loaded.emit([])
        logger.debug("[FileStore] Files cleared")

    # =====================================
    # Filtering Operations (State-based)
    # =====================================

    def filter_files_by_extension(self, extensions: set[str]) -> list[FileItem]:
        """Filter loaded files by extension set.

        Args:
            extensions: Set of extensions to match (lowercase, without dot)

        Returns:
            Filtered list of FileItem objects

        """
        filtered = [f for f in self._loaded_files if f.extension.lower() in extensions]
        self.files_filtered.emit(filtered)
        logger.debug(
            "[FileStore] Filtered files: %d match extensions %s", len(filtered), extensions
        )
        return filtered

    # =====================================
    # Cache Management
    # =====================================

    def get_cached_files(self, folder_path: str) -> list[FileItem] | None:
        """Get cached files for a folder.

        Args:
            folder_path: Folder path to get cached files for

        Returns:
            List of cached FileItem objects, or None if not cached

        """
        if folder_path in self._file_cache:
            return self._file_cache[folder_path].copy()
        return None

    def set_cached_files(self, folder_path: str, files: list[FileItem]) -> None:
        """Cache files for a folder.

        Args:
            folder_path: Folder path to cache files for
            files: List of FileItem objects to cache

        """
        self._file_cache[folder_path] = files.copy()
        logger.debug("[FileStore] Cached %d files for %s", len(files), folder_path)

    def invalidate_folder_cache(self, folder_path: str) -> None:
        """Invalidate cache for a specific folder.

        Args:
            folder_path: Folder path to invalidate

        """
        if folder_path in self._file_cache:
            del self._file_cache[folder_path]
            logger.debug("[FileStore] Invalidated cache for %s", folder_path)

    def clear_cache(self) -> None:
        """Clear all cached files."""
        self._file_cache.clear()
        logger.debug("[FileStore] File cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics

        """
        return {
            "cached_folders": len(self._file_cache),
            "total_cached_files": sum(len(items) for items in self._file_cache.values()),
            "loaded_files": len(self._loaded_files),
        }

    # =====================================
    # Filesystem Change Handling (State Update)
    # =====================================

    def invalidate_missing_folders(self) -> bool:
        """Invalidate cache entries for folders that no longer exist.

        Returns:
            bool: True if any folders were invalidated

        """
        folders_to_remove = []
        for folder in self._file_cache:
            if not os.path.exists(folder):
                folders_to_remove.append(folder)

        for folder in folders_to_remove:
            del self._file_cache[folder]
            logger.info("[FileStore] Removed cache for non-existent folder: %s", folder)

        return len(folders_to_remove) > 0

    def remove_files_from_folder(self, folder_path: str) -> bool:
        """Remove all loaded files from a specific folder.

        Args:
            folder_path: Folder path to remove files from

        Returns:
            bool: True if any files were removed

        """
        folder_norm = os.path.normpath(folder_path)
        initial_count = len(self._loaded_files)

        self._loaded_files = [
            f for f in self._loaded_files if os.path.normpath(os.path.dirname(f.full_path)) != folder_norm
        ]

        removed_count = initial_count - len(self._loaded_files)
        if removed_count > 0:
            self.files_loaded.emit(self._loaded_files)
            logger.info("[FileStore] Removed %d files from folder %s", removed_count, folder_path)
            return True
        return False
