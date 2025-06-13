"""
file_load_worker.py

Author: Michael Economou
Date: 2025-06-14

QThread worker for background file scanning operations.
Provides cancellable file discovery with progress updates.
"""

import os
from typing import List, Optional
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

from config import ALLOWED_EXTENSIONS
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileLoadWorker(QThread):
    """
    Background worker for file scanning operations.

    Provides cancellable file discovery from folders with progress updates.
    Designed to prevent UI blocking during large folder scans.
    """

    # Signals
    progress_updated = pyqtSignal(int, int)  # current, total (for progress feedback)
    files_found = pyqtSignal(list)  # List of file paths found
    finished_scanning = pyqtSignal(bool)  # success flag
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mutex = QMutex()
        self._cancelled = False
        self._folder_path = ""
        self._recursive = False

    def setup_scan(self, folder_path: str, recursive: bool = False):
        """
        Setup the scan parameters.

        Args:
            folder_path: Path to scan
            recursive: Whether to scan recursively
        """
        with QMutexLocker(self._mutex):
            self._folder_path = folder_path
            self._recursive = recursive
            self._cancelled = False

    def cancel(self):
        """Cancel the current scanning operation."""
        with QMutexLocker(self._mutex):
            self._cancelled = True
            logger.debug("[FileLoadWorker] Scan cancellation requested")

    def is_cancelled(self) -> bool:
        """Check if the operation has been cancelled."""
        with QMutexLocker(self._mutex):
            return self._cancelled

    def run(self):
        """Main thread execution - scan for files."""
        try:
            if self.is_cancelled():
                self.finished_scanning.emit(False)
                return

            folder_path = self._folder_path
            recursive = self._recursive

            logger.debug(f"[FileLoadWorker] Starting scan: {folder_path} (recursive={recursive})")

            file_paths = []

            if recursive:
                file_paths = self._scan_recursive(folder_path)
            else:
                file_paths = self._scan_shallow(folder_path)

            if self.is_cancelled():
                logger.debug("[FileLoadWorker] Scan was cancelled")
                self.finished_scanning.emit(False)
                return

            logger.debug(f"[FileLoadWorker] Scan completed: {len(file_paths)} files found")
            self.files_found.emit(file_paths)
            self.finished_scanning.emit(True)

        except Exception as e:
            logger.error(f"[FileLoadWorker] Error during scan: {e}")
            self.error_occurred.emit(str(e))
            self.finished_scanning.emit(False)

    def _scan_shallow(self, folder_path: str) -> List[str]:
        """Scan folder for files (non-recursive)."""
        file_paths = []

        try:
            items = os.listdir(folder_path)
            total_items = len(items)

            for i, item in enumerate(items):
                if self.is_cancelled():
                    break

                item_path = os.path.join(folder_path, item)

                if os.path.isfile(item_path):
                    # Check extension
                    _, ext = os.path.splitext(item_path)
                    if ext.startswith('.'):
                        ext = ext[1:].lower()

                    if ext in ALLOWED_EXTENSIONS:
                        file_paths.append(item_path)

                # Emit progress every 100 items or at the end
                if i % 100 == 0 or i == total_items - 1:
                    self.progress_updated.emit(i + 1, total_items)

        except (OSError, PermissionError) as e:
            logger.warning(f"[FileLoadWorker] Cannot access folder {folder_path}: {e}")

        return file_paths

    def _scan_recursive(self, folder_path: str) -> List[str]:
        """Scan folder recursively for files."""
        file_paths = []
        processed_count = 0

        try:
            # First pass: count total items for progress
            total_items = 0
            for root, dirs, files in os.walk(folder_path):
                if self.is_cancelled():
                    break
                total_items += len(files)

            if self.is_cancelled():
                return []

            # Second pass: collect files
            for root, dirs, files in os.walk(folder_path):
                if self.is_cancelled():
                    break

                for file in files:
                    if self.is_cancelled():
                        break

                    file_path = os.path.join(root, file)

                    # Check extension
                    _, ext = os.path.splitext(file_path)
                    if ext.startswith('.'):
                        ext = ext[1:].lower()

                    if ext in ALLOWED_EXTENSIONS:
                        file_paths.append(file_path)

                    processed_count += 1

                    # Emit progress every 1000 files or at the end
                    if processed_count % 1000 == 0 or processed_count == total_items:
                        self.progress_updated.emit(processed_count, total_items)

        except (OSError, PermissionError) as e:
            logger.warning(f"[FileLoadWorker] Cannot access folder {folder_path}: {e}")

        return file_paths
