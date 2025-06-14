"""
file_loading_worker.py

Author: Michael Economou
Date: 2025-05-01

Worker thread for loading files asynchronously.
Handles file scanning, filtering, and progress updates.
"""

from PyQt5.QtCore import QThread, pyqtSignal
import os
from typing import List, Set
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

class FileLoadingWorker(QThread):
    """
    Worker thread for loading files asynchronously.
    Emits signals for progress updates and completion.
    """
    progress_updated = pyqtSignal(int, int)  # current, total
    file_loaded = pyqtSignal(str)  # filename
    status_updated = pyqtSignal(str)  # status message
    finished_loading = pyqtSignal(list)  # list of loaded file paths
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self, paths: List[str], allowed_extensions: Set[str]):
        super().__init__()
        self.paths = paths
        self.allowed_extensions = allowed_extensions
        self.is_cancelled = False

    def run(self):
        try:
            all_files = []
            total_files = 0
            current_file = 0

            # First pass: count total files
            self.status_updated.emit("Counting files...")
            for path in self.paths:
                if self.is_cancelled:
                    return

                if os.path.isfile(path):
                    if self._is_allowed_extension(path):
                        total_files += 1
                elif os.path.isdir(path):
                    for root, _, files in os.walk(path):
                        if self.is_cancelled:
                            return
                        for file in files:
                            if self._is_allowed_extension(file):
                                total_files += 1

            logger.info(f"[FileLoadingWorker] Found {total_files} files to load")

            if total_files == 0:
                self.finished_loading.emit([])
                return

            # Second pass: load files
            self.status_updated.emit("Loading files...")
            for path in self.paths:
                if self.is_cancelled:
                    return

                if os.path.isfile(path):
                    if self._is_allowed_extension(path):
                        all_files.append(path)
                        current_file += 1
                        self.progress_updated.emit(current_file, total_files)
                        self.file_loaded.emit(os.path.basename(path))
                elif os.path.isdir(path):
                    for root, _, files in os.walk(path):
                        if self.is_cancelled:
                            return
                        for file in files:
                            if self.is_cancelled:
                                return
                            if self._is_allowed_extension(file):
                                full_path = os.path.join(root, file)
                                all_files.append(full_path)
                                current_file += 1
                                self.progress_updated.emit(current_file, total_files)
                                self.file_loaded.emit(file)

            if not self.is_cancelled:
                logger.info(f"[FileLoadingWorker] Successfully loaded {len(all_files)} files")
                self.finished_loading.emit(all_files)

        except Exception as e:
            logger.error(f"Error in FileLoadingWorker: {str(e)}")
            self.error_occurred.emit(str(e))

    def _is_allowed_extension(self, path: str) -> bool:
        """Check if file has an allowed extension."""
        ext = os.path.splitext(path)[1].lower()
        # Remove the dot from extension for comparison
        if ext.startswith('.'):
            ext = ext[1:]
        return ext in self.allowed_extensions

    def cancel(self):
        """Cancel the loading operation."""
        self.is_cancelled = True
        logger.info("[FileLoadingWorker] Loading cancelled by user")
