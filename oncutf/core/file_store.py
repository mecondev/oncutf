"""
Module: file_store.py

Author: Michael Economou
Date: 2025-05-31

File Store - Centralized file management
This module handles all file-related operations, removing them from MainWindow
to improve performance and maintainability.
Manages:
- File scanning and loading
- Folder operations
- File validation and filtering
- Performance optimization for large folders
"""

import glob
import os
from typing import Any

from oncutf.config import ALLOWED_EXTENSIONS
from oncutf.core.pyqt_imports import QElapsedTimer, QObject, pyqtSignal
from oncutf.models.file_item import FileItem
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileStore(QObject):
    """
    Centralized file management and operations.

    Handles all file-related logic previously scattered across MainWindow
    and other components. Provides optimized file loading and caching.
    """

    # Signals for file operations
    files_loaded = pyqtSignal(list)  # Emitted when files are loaded
    folder_changed = pyqtSignal(str)  # Emitted when current folder changes
    files_filtered = pyqtSignal(list)  # Emitted when files are filtered

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # Current state
        self._current_folder: str | None = None
        self._loaded_files: list[FileItem] = []
        self._file_cache: dict[str, list[FileItem]] = {}

        # Performance tracking
        self._load_timer = QElapsedTimer()

        logger.debug("[FileStore] Initialized", extra={"dev_only": True})

    # =====================================
    # File Scanning Operations
    # =====================================

    def get_file_items_from_folder(
        self, folder_path: str, *, use_cache: bool = True
    ) -> list[FileItem]:
        """
        Scans a folder and returns FileItem objects for supported files.

        Moved from MainWindow.get_file_items_from_folder() with optimizations:
        - Caching for frequently accessed folders
        - Performance timing
        - Batch processing for large folders

        Args:
            folder_path: Absolute path to folder to scan
            use_cache: Whether to use cached results if available

        Returns:
            List of FileItem objects for supported files
        """
        self._load_timer.start()

        # Check cache first
        if use_cache and folder_path in self._file_cache:
            cached_items = self._file_cache[folder_path]
            logger.debug(
                "[FileStore] Using cached files for %s: %d items",
                folder_path,
                len(cached_items),
            )
            return cached_items.copy()

        # Scan folder
        all_files = glob.glob(os.path.join(folder_path, "*"))
        file_items = []

        for file_path in sorted(all_files):
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1][1:].lower()
                if ext in ALLOWED_EXTENSIONS:
                    filename = os.path.basename(file_path)
                    try:
                        file_items.append(FileItem.from_path(file_path))
                    except OSError as e:
                        logger.warning("Could not create FileItem for %s: %s", filename, e)
                        continue

        # Cache results
        if use_cache:
            self._file_cache[folder_path] = file_items.copy()

        elapsed = self._load_timer.elapsed()
        logger.info("[FileStore] Scanned %s: %d files in %dms", folder_path, len(file_items), elapsed)

        return file_items

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> list[FileItem]:
        """
        Loads a mix of files and folders into FileItem objects.

        Moved from MainWindow.load_files_from_paths() with optimizations:
        - Batch processing
        - Better error handling
        - Performance tracking

        Args:
            file_paths: List of absolute file or folder paths
            clear: Whether to clear existing loaded files

        Returns:
            List of FileItem objects loaded
        """
        self._load_timer.start()

        if clear:
            self._loaded_files.clear()

        if not file_paths:
            logger.debug("[FileStore] No file paths provided")
            return []

        file_items = []

        for path in file_paths:
            try:
                if os.path.isdir(path):
                    # Load folder contents
                    folder_items = self.get_file_items_from_folder(path)
                    file_items.extend(folder_items)
                    logger.debug(
                        "[FileStore] Loaded %d files from folder: %s",
                        len(folder_items),
                        path,
                    )

                elif os.path.isfile(path):
                    # Load individual file
                    ext = os.path.splitext(path)[1][1:].lower()
                    if ext in ALLOWED_EXTENSIONS:
                        file_items.append(FileItem.from_path(path))
                        logger.debug("[FileStore] Loaded file: %s", os.path.basename(path))
                    else:
                        logger.debug("[FileStore] Skipped unsupported file: %s", path)

            except OSError as e:
                logger.error("[FileStore] Error loading path %s: %s", path, e)
                continue

        # Update state
        if clear:
            self._loaded_files = file_items
        else:
            self._loaded_files.extend(file_items)

        elapsed = self._load_timer.elapsed()
        logger.info("[FileStore] Loaded %d total files in %dms", len(file_items), elapsed)

        # Emit signal
        self.files_loaded.emit(file_items)

        return file_items

    # =====================================
    # State Management
    # =====================================

    def get_loaded_files(self) -> list[FileItem]:
        """Get currently loaded files."""
        return self._loaded_files.copy()

    def set_loaded_files(self, files: list[FileItem]) -> None:
        """
        Set loaded files directly (used when files are loaded externally).

        Args:
            files: List of FileItem objects to set as loaded
        """
        self._loaded_files = files.copy() if files else []
        self.files_loaded.emit(self._loaded_files)
        logger.debug("[FileStore] Loaded files set directly: %d files", len(self._loaded_files))

    def get_current_folder(self) -> str | None:
        """Get current folder path."""
        return self._current_folder

    def set_current_folder(self, folder_path: str) -> None:
        """Set current folder and emit signal."""
        old_folder = self._current_folder
        self._current_folder = folder_path

        if old_folder != folder_path:
            self.folder_changed.emit(folder_path)
            logger.debug("[FileStore] Current folder changed: %s", folder_path)

    def clear_files(self) -> None:
        """Clear all loaded files."""
        self._loaded_files.clear()
        self.files_loaded.emit([])
        logger.debug("[FileStore] Files cleared")

    # =====================================
    # File Validation & Filtering
    # =====================================

    def is_supported_file(self, file_path: str) -> bool:
        """Check if file has supported extension."""
        if not os.path.isfile(file_path):
            return False

        ext = os.path.splitext(file_path)[1][1:].lower()
        return ext in ALLOWED_EXTENSIONS

    def filter_files_by_extension(self, extensions: set[str]) -> list[FileItem]:
        """Filter loaded files by extension."""
        filtered = [f for f in self._loaded_files if f.extension.lower() in extensions]
        self.files_filtered.emit(filtered)
        logger.debug("[FileStore] Filtered files: %d match extensions %s", len(filtered), extensions)
        return filtered

    # =====================================
    # Cache Management
    # =====================================

    def clear_cache(self) -> None:
        """Clear file cache."""
        self._file_cache.clear()
        logger.debug("[FileStore] File cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_folders": len(self._file_cache),
            "total_cached_files": sum(len(items) for items in self._file_cache.values()),
            "loaded_files": len(self._loaded_files),
        }

    # =====================================
    # Performance & Utilities
    # =====================================

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        cache_stats = self.get_cache_stats()
        return {
            "last_load_time_ms": self._load_timer.elapsed() if self._load_timer.isValid() else 0,
            **cache_stats,
        }
