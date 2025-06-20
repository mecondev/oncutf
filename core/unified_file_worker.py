"""
unified_file_worker.py

Author: Michael Economou
Date: 2025-05-01

🎯 UNIFIED QThread worker for background file scanning operations.

This module replaces and consolidates the functionality of:
- core/file_load_worker.py (DEPRECATED - removed)
- widgets/file_loading_worker.py (DEPRECATED - removed)

Provides thread-safe, cancellable file discovery with detailed progress updates.
Used by all file loading components across the application for consistent behavior.

Key Features:
- Thread-safe with QMutex protection
- Support for multiple paths or single folder scanning
- Configurable allowed extensions per operation
- Comprehensive progress and status updates
- Graceful cancellation support
- Both recursive and non-recursive scanning modes
- Optimized for both small and large file operations

Usage:
    worker = UnifiedFileWorker()
    worker.setup_scan(paths, allowed_extensions, recursive=True)
    worker.files_found.connect(handle_files)
    worker.start()
"""

import os
from typing import List, Optional, Set, Union

from PyQt5.QtCore import QMutex, QMutexLocker, QThread, pyqtSignal

from config import ALLOWED_EXTENSIONS
from utils.logger_factory import get_cached_logger
from utils.timer_manager import get_timer_manager

logger = get_cached_logger(__name__)


class UnifiedFileWorker(QThread):
    """
    Unified background worker for file scanning operations.

    Enhanced Features:
    - Improved cancellation responsiveness in both phases
    - Timer-based progress updates for better UX
    - Thread-safe with QMutex protection
    - Support for multiple paths or single folder
    - Configurable allowed extensions
    - Detailed progress and status updates
    - Graceful cancellation support
    - Both recursive and non-recursive scanning
    """

    # Signals - comprehensive set covering all use cases
    progress_updated = pyqtSignal(int, int)  # current, total (for progress feedback)
    status_updated = pyqtSignal(str)  # status message (e.g., "Scanning: folder/subfolder")
    file_loaded = pyqtSignal(str)  # current filename being processed
    files_found = pyqtSignal(list)  # List of file paths found (final result)
    finished_scanning = pyqtSignal(bool)  # success flag
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mutex = QMutex()
        self._paths = []
        self._allowed_extensions = set()
        self._recursive = False
        self._cancelled = False
        self.timer_manager = get_timer_manager()

        # Enhanced cancellation tracking
        self._cancel_check_counter = 0
        self._cancel_check_frequency = 1  # Check every 1 operation for immediate response

    def setup_scan(self,
                   paths: Union[str, List[str]],
                   allowed_extensions: Optional[Set[str]] = None,
                   recursive: bool = False):
        """
        Configure the worker for scanning.
        Thread-safe setup with mutex protection.
        """
        with QMutexLocker(self._mutex):
            # Handle both single path and list of paths
            if isinstance(paths, str):
                self._paths = [paths]
            else:
                self._paths = list(paths)

            # Set allowed extensions
            if allowed_extensions is not None:
                self._allowed_extensions = allowed_extensions
            else:
                self._allowed_extensions = set(ALLOWED_EXTENSIONS)

            self._recursive = recursive
            self._cancelled = False
            self._cancel_check_counter = 0

    def cancel(self):
        """Cancel the current scanning operation with immediate effect."""
        with QMutexLocker(self._mutex):
            self._cancelled = True
            logger.debug("[UnifiedFileWorker] Scan cancellation requested - immediate effect")

    def is_cancelled(self) -> bool:
        """Check if the operation has been cancelled."""
        with QMutexLocker(self._mutex):
            return self._cancelled

    def _check_cancellation_frequently(self) -> bool:
        """
        Enhanced cancellation check for phase 2 (file loading).
        Checks more frequently during file processing.
        """
        self._cancel_check_counter += 1
        if self._cancel_check_counter >= self._cancel_check_frequency:
            self._cancel_check_counter = 0
            return self.is_cancelled()
        return False

    def run(self):
        """Main thread execution - scan for files with enhanced cancellation."""
        try:
            if self.is_cancelled():
                self.finished_scanning.emit(False)
                return

            # Get configuration safely
            with QMutexLocker(self._mutex):
                paths = self._paths.copy()
                allowed_extensions = self._allowed_extensions.copy()
                recursive = self._recursive

            logger.debug(f"[UnifiedFileWorker] Starting scan: {len(paths)} paths (recursive={recursive})")

            all_files = []
            total_files = 0
            current_file = 0

            # Phase 1: Count total files for accurate progress
            self.status_updated.emit("Counting files...")

            for path in paths:
                if self.is_cancelled():
                    logger.debug("[UnifiedFileWorker] Cancelled during phase 1 (counting)")
                    self.finished_scanning.emit(False)
                    return

                if os.path.isfile(path):
                    if self._is_allowed_extension(path, allowed_extensions):
                        total_files += 1
                elif os.path.isdir(path):
                    total_files += self._count_files_in_directory(path, allowed_extensions, recursive)

            if self.is_cancelled():
                logger.debug("[UnifiedFileWorker] Cancelled after phase 1 (counting)")
                self.finished_scanning.emit(False)
                return

            logger.debug(f"[UnifiedFileWorker] Found {total_files} files to process")

            if total_files == 0:
                self.status_updated.emit("No matching files found")
                self.files_found.emit([])
                self.finished_scanning.emit(True)
                return

            # Phase 2: Collect files with detailed progress and enhanced cancellation
            self.status_updated.emit("Loading files...")
            self._cancel_check_counter = 0  # Reset counter for phase 2

            for path in paths:
                if self.is_cancelled():
                    logger.debug("[UnifiedFileWorker] Cancelled during phase 2 (loading)")
                    self.finished_scanning.emit(False)
                    return

                if os.path.isfile(path):
                    if self._is_allowed_extension(path, allowed_extensions):
                        all_files.append(path)
                        current_file += 1
                        self.progress_updated.emit(current_file, total_files)
                        self.file_loaded.emit(os.path.basename(path))

                        # Enhanced cancellation check for single files
                        if self._check_cancellation_frequently():
                            logger.debug("[UnifiedFileWorker] Cancelled during single file processing")
                            self.finished_scanning.emit(False)
                            return

                elif os.path.isdir(path):
                    found_files = self._scan_directory_with_enhanced_cancellation(
                        path, allowed_extensions, recursive, current_file, total_files
                    )
                    if found_files is None:  # Cancellation occurred
                        logger.debug("[UnifiedFileWorker] Cancelled during directory scanning")
                        self.finished_scanning.emit(False)
                        return

                    all_files.extend(found_files)
                    current_file += len(found_files)

            if not self.is_cancelled():
                logger.debug(f"[UnifiedFileWorker] Scan completed: {len(all_files)} files found")
                self.status_updated.emit(f"Loaded {len(all_files)} files")
                self.files_found.emit(all_files)
                self.finished_scanning.emit(True)
            else:
                logger.debug("[UnifiedFileWorker] Scan was cancelled during final phase")
                self.finished_scanning.emit(False)

        except Exception as e:
            logger.error(f"[UnifiedFileWorker] Error during scan: {e}")
            self.error_occurred.emit(str(e))
            self.finished_scanning.emit(False)

    def _count_files_in_directory(self, directory: str, allowed_extensions: Set[str], recursive: bool) -> int:
        """Count total files in directory for progress calculation with cancellation support."""
        count = 0

        try:
            if recursive:
                for root, _, files in os.walk(directory):
                    if self.is_cancelled():
                        break

                    for file in files:
                        if self.is_cancelled():
                            break
                        if self._is_allowed_extension(file, allowed_extensions):
                            count += 1
            else:
                files = os.listdir(directory)
                for file in files:
                    if self.is_cancelled():
                        break
                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path) and self._is_allowed_extension(file, allowed_extensions):
                        count += 1

        except (OSError, PermissionError) as e:
            logger.warning(f"[UnifiedFileWorker] Cannot access directory {directory}: {e}")

        return count

    def _scan_directory_with_enhanced_cancellation(self, directory: str, allowed_extensions: Set[str],
                                                  recursive: bool, current_progress: int, total_files: int) -> Optional[List[str]]:
        """
        Scan directory with enhanced cancellation support.
        Returns None if cancelled, otherwise returns list of files.
        """
        files_found = []
        scanned_items = 0

        try:
            if recursive:
                for root, _, files in os.walk(directory):
                    if self.is_cancelled():
                        return None

                    # Update status with current directory
                    relative_path = os.path.relpath(root, directory)
                    if relative_path != ".":
                        self.status_updated.emit(f"Scanning: {relative_path}")

                    for file in files:
                        if self.is_cancelled():
                            return None

                        # Enhanced cancellation check during file processing
                        if self._check_cancellation_frequently():
                            return None

                        scanned_items += 1

                        # Show progress for non-matching files too
                        if scanned_items % 50 == 0:  # More frequent updates
                            self.file_loaded.emit(f"Scanning... ({scanned_items} items)")

                        if self._is_allowed_extension(file, allowed_extensions):
                            full_path = os.path.join(root, file)
                            files_found.append(full_path)
                            current_progress += 1
                            self.progress_updated.emit(current_progress, total_files)
                            self.file_loaded.emit(file)
            else:
                files = os.listdir(directory)
                for file in files:
                    if self.is_cancelled():
                        return None

                    scanned_items += 1

                    # Enhanced cancellation check
                    if self._check_cancellation_frequently():
                        return None

                    if scanned_items % 25 == 0:  # More frequent updates for non-recursive
                        self.file_loaded.emit(f"Scanning... ({scanned_items} items)")

                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path) and self._is_allowed_extension(file, allowed_extensions):
                        files_found.append(file_path)
                        current_progress += 1
                        self.progress_updated.emit(current_progress, total_files)
                        self.file_loaded.emit(file)

        except (OSError, PermissionError) as e:
            logger.warning(f"[UnifiedFileWorker] Cannot access directory {directory}: {e}")

        return files_found

    def _is_allowed_extension(self, file_path: str, allowed_extensions: Set[str]) -> bool:
        """Check if file has an allowed extension."""
        _, ext = os.path.splitext(file_path)
        if ext.startswith('.'):
            ext = ext[1:].lower()
        return ext in allowed_extensions
