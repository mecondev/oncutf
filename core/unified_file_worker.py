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
from PyQt5.QtWidgets import QApplication

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

        # Simplified cancellation tracking - just count operations
        self._operations_count = 0

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
            self._operations_count = 0

    def cancel(self):
        """Cancel the current scanning operation with immediate effect."""
        with QMutexLocker(self._mutex):
            self._cancelled = True
            logger.debug("[UnifiedFileWorker] Scan cancellation requested - immediate effect")

    def is_cancelled(self) -> bool:
        """Check if the operation has been cancelled."""
        with QMutexLocker(self._mutex):
            return self._cancelled

    def _should_process_events(self) -> bool:
        """
        Simple check to process UI events periodically.
        Every 5 operations for responsive cancellation.
        """
        self._operations_count += 1
        if self._operations_count % 5 == 0:
            QApplication.processEvents()
            return True
        return False

    def run(self):
        """Main thread execution - scan for files with enhanced cancellation."""
        try:
            logger.debug(f"[DEBUG] UnifiedFileWorker.run() started")
            if self.is_cancelled():
                logger.debug(f"[DEBUG] Worker was already cancelled, exiting")
                self.finished_scanning.emit(False)
                return

            # Get configuration safely
            with QMutexLocker(self._mutex):
                paths = self._paths.copy()
                allowed_extensions = self._allowed_extensions.copy()
                recursive = self._recursive

            logger.debug(f"[DEBUG] Worker configuration: paths={paths}, recursive={recursive}, extensions={allowed_extensions}")
            logger.debug(f"[UnifiedFileWorker] Starting scan: {len(paths)} paths (recursive={recursive})")

            all_files = []
            total_files = 0
            current_file = 0

            # Phase 1: Count total files for accurate progress
            logger.debug(f"[DEBUG] Starting Phase 1: Counting files...")
            self.status_updated.emit("Counting files...")

            for path in paths:
                logger.debug(f"[DEBUG] Processing path in Phase 1: {path}")
                if self.is_cancelled():
                    logger.debug("[UnifiedFileWorker] Cancelled during phase 1 (counting)")
                    self.finished_scanning.emit(False)
                    return

                if os.path.isfile(path):
                    logger.debug(f"[DEBUG] Path is file: {path}")
                    if self._is_allowed_extension(path, allowed_extensions):
                        total_files += 1
                        logger.debug(f"[DEBUG] File has allowed extension, total_files now: {total_files}")
                elif os.path.isdir(path):
                    logger.debug(f"[DEBUG] Path is directory: {path}, starting count...")
                    count = self._count_files_in_directory(path, allowed_extensions, recursive)
                    total_files += count
                    logger.debug(f"[DEBUG] Directory count completed: {count} files, total_files now: {total_files}")
                else:
                    logger.debug(f"[DEBUG] Path is neither file nor directory: {path}")

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

                        # Phase 2: Collect files with detailed progress
            self.status_updated.emit("Loading files...")
            # Signal to show progress bar now that we know the total
            self.progress_updated.emit(0, total_files)  # This will trigger show_progress()
            self._operations_count = 0  # Reset counter for phase 2

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

                elif os.path.isdir(path):
                    found_files = self._scan_directory_simplified(
                        path, allowed_extensions, recursive, current_file, total_files
                    )
                    if found_files is None:  # Cancellation occurred
                        logger.debug("[UnifiedFileWorker] Cancelled during directory scanning")
                        self.finished_scanning.emit(False)
                        return

                    all_files.extend(found_files)
                    current_file += len(found_files)

                    # Update progress after processing each directory
                    self.progress_updated.emit(current_file, total_files)
                    logger.debug(f"[DEBUG] Updated progress after directory: {current_file}/{total_files}")

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
        logger.debug(f"[DEBUG] _count_files_in_directory started for: {directory} (recursive={recursive})")
        count = 0
        processed_dirs = 0

        try:
            if recursive:
                logger.debug(f"[DEBUG] Using recursive os.walk for directory: {directory}")
                walk_count = 0
                for root, _, files in os.walk(directory):
                    walk_count += 1
                    processed_dirs += 1
                    logger.debug(f"[DEBUG] Walking directory #{walk_count}: {root}, found {len(files)} files")

                    # Check cancellation at directory level for immediate response
                    if self.is_cancelled():
                        logger.debug(f"[DEBUG] Cancelled during os.walk at directory: {root}")
                        break

                    # Update status with current directory for user feedback
                    relative_path = os.path.relpath(root, directory)
                    if relative_path != ".":
                        self.status_updated.emit(f"Counting files in: {relative_path}")
                    else:
                        self.status_updated.emit(f"Counting files in: {os.path.basename(directory)}")

                    # Process UI events periodically
                    if self._should_process_events():
                        # Check cancellation after processing events
                        if self.is_cancelled():
                            logger.debug(f"[DEBUG] Cancelled during counting in: {root}")
                            break

                    for file in files:
                        if self._is_allowed_extension(file, allowed_extensions):
                            count += 1

                    # Update progress more frequently during counting
                    if walk_count % 5 == 0:  # Every 5 directories instead of 10
                        logger.debug(f"[DEBUG] Processed {walk_count} directories, count so far: {count}")
                        # Don't emit progress during counting - it's misleading since we don't know total yet
                        # Just emit status updates for user feedback
            else:
                logger.debug(f"[DEBUG] Using non-recursive listdir for directory: {directory}")
                self.status_updated.emit(f"Counting files in: {os.path.basename(directory)}")
                files = os.listdir(directory)
                logger.debug(f"[DEBUG] Found {len(files)} items in directory")
                for file in files:
                    if self.is_cancelled():
                        logger.debug(f"[DEBUG] Cancelled during non-recursive file processing")
                        break
                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path) and self._is_allowed_extension(file, allowed_extensions):
                        count += 1

        except (OSError, PermissionError) as e:
            logger.warning(f"[UnifiedFileWorker] Cannot access directory {directory}: {e}")
            logger.debug(f"[DEBUG] Exception during directory access: {e}")

        logger.debug(f"[DEBUG] _count_files_in_directory completed for {directory}: {count} files")
        return count

    def _scan_directory_simplified(self, directory: str, allowed_extensions: Set[str],
                                   recursive: bool, current_progress: int, total_files: int) -> Optional[List[str]]:
        """
        Simplified directory scanning with balanced cancellation checks.
        Returns None if cancelled, otherwise returns list of files.
        """
        files_found = []

        try:
            if recursive:
                for root, _, files in os.walk(directory):
                    if self.is_cancelled():
                        return None

                    # Update status with current directory
                    relative_path = os.path.relpath(root, directory)
                    if relative_path != ".":
                        self.status_updated.emit(f"Scanning: {relative_path}")

                    # Process UI events and check cancellation periodically
                    if self._should_process_events() and self.is_cancelled():
                        return None

                    for file in files:
                        if self._is_allowed_extension(file, allowed_extensions):
                            full_path = os.path.join(root, file)
                            files_found.append(full_path)
                            current_progress += 1
                            self.progress_updated.emit(current_progress, total_files)
                            self.file_loaded.emit(file)

                            # Check cancellation periodically during file processing
                            if self._should_process_events() and self.is_cancelled():
                                return None
            else:
                files = os.listdir(directory)
                for file in files:
                    if self.is_cancelled():
                        return None

                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path) and self._is_allowed_extension(file, allowed_extensions):
                        files_found.append(file_path)
                        current_progress += 1
                        self.progress_updated.emit(current_progress, total_files)
                        self.file_loaded.emit(file)

                        # Check cancellation periodically
                        if self._should_process_events() and self.is_cancelled():
                            return None

        except (OSError, PermissionError) as e:
            logger.warning(f"[UnifiedFileWorker] Cannot access directory {directory}: {e}")

        return files_found

    def _is_allowed_extension(self, file_path: str, allowed_extensions: Set[str]) -> bool:
        """Check if file has an allowed extension."""
        _, ext = os.path.splitext(file_path)
        if ext.startswith('.'):
            ext = ext[1:].lower()
        return ext in allowed_extensions
