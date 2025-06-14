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

    def __init__(self, paths: List[str], allowed_extensions: Set[str], recursive: bool = True):
        super().__init__()
        self.paths = paths
        self.allowed_extensions = allowed_extensions
        self.recursive = recursive
        self.is_cancelled = False

    def run(self):
        try:
            all_files = []
            total_files = 0
            current_file = 0
            scanned_items = 0  # Track all items scanned, not just valid files

            # First pass: count total files
            self.status_updated.emit("Counting files...")
            for path in self.paths:
                if self.is_cancelled:
                    return

                if os.path.isfile(path):
                    if self._is_allowed_extension(path):
                        total_files += 1
                elif os.path.isdir(path):
                    if self.recursive:
                        # Recursive: scan all subdirectories
                        for root, _, files in os.walk(path):
                            if self.is_cancelled:
                                return
                            # Update status periodically during counting
                            scanned_items += len(files)
                            if scanned_items % 100 == 0:  # Update every 100 items
                                self.status_updated.emit(f"Counting files... ({scanned_items} items scanned)")

                            for file in files:
                                if self._is_allowed_extension(file):
                                    total_files += 1
                    else:
                        # Non-recursive: scan only the immediate directory
                        try:
                            files = os.listdir(path)
                            scanned_items += len(files)
                            self.status_updated.emit(f"Counting files... ({scanned_items} items scanned)")

                            for file in files:
                                if self.is_cancelled:
                                    return
                                file_path = os.path.join(path, file)
                                if os.path.isfile(file_path) and self._is_allowed_extension(file):
                                    total_files += 1
                        except OSError:
                            pass

            logger.info(f"[FileLoadingWorker] Found {total_files} files to load from {scanned_items} total items")

            if total_files == 0:
                self.status_updated.emit("No video files found")
                self.finished_loading.emit([])
                return

            # Second pass: load files
            self.status_updated.emit("Loading files...")
            scanned_items = 0  # Reset counter for loading phase

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
                    if self.recursive:
                        # Recursive: scan all subdirectories
                        for root, _, files in os.walk(path):
                            if self.is_cancelled:
                                return

                            # Update status with current directory being processed
                            relative_path = os.path.relpath(root, path)
                            if relative_path != ".":
                                self.status_updated.emit(f"Scanning: {relative_path}")

                            for file in files:
                                if self.is_cancelled:
                                    return

                                scanned_items += 1

                                # Show progress even for non-video files
                                if scanned_items % 50 == 0:  # Update every 50 files
                                    self.file_loaded.emit(f"Scanning... ({scanned_items} items)")

                                if self._is_allowed_extension(file):
                                    full_path = os.path.join(root, file)
                                    all_files.append(full_path)
                                    current_file += 1
                                    self.progress_updated.emit(current_file, total_files)
                                    self.file_loaded.emit(file)
                    else:
                        # Non-recursive: scan only the immediate directory
                        try:
                            files = os.listdir(path)
                            for file in files:
                                if self.is_cancelled:
                                    return

                                scanned_items += 1

                                # Show progress even for non-video files
                                if scanned_items % 20 == 0:  # Update every 20 files for non-recursive
                                    self.file_loaded.emit(f"Scanning... ({scanned_items} items)")

                                file_path = os.path.join(path, file)
                                if os.path.isfile(file_path) and self._is_allowed_extension(file):
                                    all_files.append(file_path)
                                    current_file += 1
                                    self.progress_updated.emit(current_file, total_files)
                                    self.file_loaded.emit(file)
                        except OSError:
                            pass

            if not self.is_cancelled:
                logger.info(f"[FileLoadingWorker] Successfully loaded {len(all_files)} files")
                self.status_updated.emit(f"Loaded {len(all_files)} video files")
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
