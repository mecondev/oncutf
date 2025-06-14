"""
file_loader.py

Author: Michael Economou
Date: 2025-05-01

Core file loading functionality with support for both synchronous and threaded loading.
Handles file scanning, filtering, and UI feedback during loading operations.
"""

import os
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication

from config import ALLOWED_EXTENSIONS
from models.file_item import FileItem
from utils.cursor_helper import wait_cursor
from utils.logger_factory import get_cached_logger
from widgets.compact_waiting_widget import CompactWaitingWidget

logger = get_cached_logger(__name__)


class FileLoadWorker(QThread):
    """
    Worker thread for file loading operations.
    Handles background file scanning with progress updates.
    """

    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(list)  # list of FileItem objects
    error = pyqtSignal(str)  # error message

    def __init__(self, path: str, recursive: bool = False):
        super().__init__()
        self.path = path
        self.recursive = recursive
        self._is_cancelled = False
        self.files = []  # Store loaded files

    def run(self):
        try:
            files = []
            total = self._count_files(self.path, self.recursive)
            current = 0

            for root, _, filenames in os.walk(self.path):
                if self._is_cancelled:
                    break

                for filename in filenames:
                    if self._is_cancelled:
                        break

                    if not self.recursive and root != self.path:
                        continue

                    if self._is_valid_file(filename):
                        full_path = os.path.join(root, filename)
                        files.append(FileItem(full_path))
                        current += 1
                        if current % 100 == 0:  # Update every 100 files
                            self.progress.emit(current, total)

            if not self._is_cancelled:
                self.files = files  # Store files before emitting signal
                self.finished.emit(files)

        except Exception as e:
            logger.error(f"Error in FileLoadWorker: {str(e)}")
            self.error.emit(str(e))

    def cancel(self):
        """Cancel the file loading operation."""
        self._is_cancelled = True

    def _count_files(self, path: str, recursive: bool) -> int:
        """Count total files to be processed."""
        count = 0
        for root, _, filenames in os.walk(path):
            if not recursive and root != path:
                continue
            count += sum(1 for f in filenames if self._is_valid_file(f))
        return count

    def _is_valid_file(self, filename: str) -> bool:
        """Check if file has allowed extension."""
        return os.path.splitext(filename)[1].lower()[1:] in ALLOWED_EXTENSIONS


class FileLoader:
    """
    Handles file loading operations with support for both synchronous and threaded loading.
    Provides progress feedback and cancellation support.
    """

    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.worker = None
        self.waiting_widget = None

    def load_files(self, path: str, recursive: bool = False) -> List[FileItem]:
        """
        Load files from the given path, optionally recursively.

        Args:
            path: Directory path to load files from
            recursive: Whether to load files from subdirectories

        Returns:
            List of FileItem objects
        """
        logger.info(f"[FileLoader] Loading files from {path} (recursive: {recursive})")

        # Check if path is a directory
        if not os.path.isdir(path):
            logger.error(f"[FileLoader] Path is not a directory: {path}")
            return []

        # Estimate folder size to decide on threading
        total_files = self._estimate_folder_size(path, recursive)
        use_threading = total_files > 1000  # Use threading for large folders

        if use_threading:
            return self._load_files_threaded(path, recursive)
        else:
            return self._load_files_sync(path, recursive)

    def _estimate_folder_size(self, path: str, recursive: bool) -> int:
        """Estimate total number of files in folder."""
        try:
            count = 0
            for root, _, files in os.walk(path):
                if not recursive and root != path:
                    continue
                count += len(files)
                if count > 1000:  # Stop counting if we know it's large
                    break
            return count
        except Exception as e:
            logger.error(f"Error estimating folder size: {str(e)}")
            return 0

    def _load_files_threaded(self, path: str, recursive: bool) -> List[FileItem]:
        """Load files using background thread with progress dialog."""
        self.worker = FileLoadWorker(path, recursive)
        self.waiting_widget = CompactWaitingWidget(
            self.parent_window,
            bar_color="#64b5f6",  # pal blue
            bar_bg_color="#0a1a2a"  # darker blue bg
        )
        self.waiting_widget.set_status("Scanning files...")
        self.waiting_widget.show()

        # Connect signals
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(self._handle_finished)
        self.worker.error.connect(self._handle_error)

        # Start worker
        self.worker.start()

        # Process events to show dialog
        QApplication.processEvents()

        # Wait for completion
        self.worker.wait()
        return self.worker.files if hasattr(self.worker, 'files') else []

    def _load_files_sync(self, path: str, recursive: bool) -> List[FileItem]:
        """Load files synchronously with wait cursor."""
        with wait_cursor():
            files = []
            total = self._estimate_folder_size(path, recursive)
            current = 0

            for root, _, filenames in os.walk(path):
                if not recursive and root != path:
                    continue

                for filename in filenames:
                    if os.path.splitext(filename)[1].lower()[1:] in ALLOWED_EXTENSIONS:
                        full_path = os.path.join(root, filename)
                        files.append(FileItem(full_path))
                        current += 1

            return files

    def _update_progress(self, current: int, total: int):
        """Update progress dialog."""
        if self.waiting_widget:
            self.waiting_widget.set_progress(current, total)
            self.waiting_widget.set_filename(f"Processing {current} of {total} items...")
            QApplication.processEvents()

    def _handle_finished(self, files: List[FileItem]):
        """Handle worker completion."""
        if self.waiting_widget:
            self.waiting_widget.close()
            self.waiting_widget = None

    def _handle_error(self, error_msg: str):
        """Handle worker error."""
        logger.error(f"[FileLoader] Error loading files: {error_msg}")
        if self.waiting_widget:
            self.waiting_widget.close()
            self.waiting_widget = None

    def cancel_loading(self):
        """Cancel ongoing file loading operation."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        if self.waiting_widget:
            self.waiting_widget.close()
            self.waiting_widget = None
