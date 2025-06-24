"""
hash_worker.py

Author: Michael Economou
Date: 2025-06-23

QThread worker for background hash calculation operations.

This module provides thread-safe, cancellable hash operations with detailed progress updates.
Used for operations that can be time-consuming, especially with large video files.

Key Features:
- Thread-safe with QMutex protection
- Support for multiple hash operations (duplicates, comparison, checksums)
- Comprehensive progress and status updates
- Graceful cancellation support
- Optimized for large file operations

Usage:
    worker = HashWorker()
    worker.setup_duplicate_scan(file_paths)
    worker.duplicates_found.connect(handle_duplicates)
    worker.start()
"""

import os
from pathlib import Path
from typing import List

from PyQt5.QtCore import QMutexLocker

from core.qt_imports import QMutex, QThread, pyqtSignal
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ProgressCallback:
    """Simple callback class to track progress correctly."""

    def __init__(self, worker, file_index, total_files, base_bytes):
        self.worker = worker
        self.file_index = file_index
        self.total_files = total_files
        self.base_bytes = base_bytes

    def __call__(self, bytes_read):
        """Called when hash calculation progresses."""
        current_total = self.base_bytes + bytes_read
        self.worker.enhanced_progress_updated.emit(self.file_index, self.total_files, current_total)


class HashWorker(QThread):
    """
    Background worker for hash calculation operations.

    Supports three main operations:
    1. Find duplicates in file list
    2. Compare files with external folder
    3. Calculate checksums for files
    """

    # Signals for different operations
    progress_updated = pyqtSignal(int, int)  # current, total
    enhanced_progress_updated = pyqtSignal(int, int, int)  # current, total, current_size
    status_updated = pyqtSignal(str)  # status message
    file_processing = pyqtSignal(str)  # current filename being processed

    # Result signals
    duplicates_found = pyqtSignal(dict)  # {hash: [file_paths]}
    comparison_result = pyqtSignal(dict)  # comparison results
    checksums_calculated = pyqtSignal(dict)  # {file_path: hash}

    # Control signals
    finished_processing = pyqtSignal(bool)  # success flag
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mutex = QMutex()
        self._cancelled = False

        # Operation configuration
        self._operation_type = None  # "duplicates", "compare", "checksums"
        self._file_paths = []
        self._external_folder = None

        # Progress tracking
        self._cancel_check_counter = 0
        self._cancel_check_frequency = 5  # Check every 5 operations

    def setup_duplicate_scan(self, file_paths: List[str]) -> None:
        """Configure worker for duplicate detection."""
        with QMutexLocker(self._mutex):
            self._operation_type = "duplicates"
            self._file_paths = list(file_paths)
            self._external_folder = None
            self._cancelled = False
            self._cancel_check_counter = 0

    def setup_external_comparison(self, file_paths: List[str], external_folder: str) -> None:
        """Configure worker for external folder comparison."""
        with QMutexLocker(self._mutex):
            self._operation_type = "compare"
            self._file_paths = list(file_paths)
            self._external_folder = external_folder
            self._cancelled = False
            self._cancel_check_counter = 0

    def setup_checksum_calculation(self, file_paths: List[str]) -> None:
        """Configure worker for checksum calculation."""
        with QMutexLocker(self._mutex):
            self._operation_type = "checksums"
            self._file_paths = list(file_paths)
            self._external_folder = None
            self._cancelled = False
            self._cancel_check_counter = 0

    def cancel(self) -> None:
        """Cancel the current operation."""
        with QMutexLocker(self._mutex):
            self._cancelled = True
            logger.debug("[HashWorker] Cancellation requested")

    def is_cancelled(self) -> bool:
        """Check if operation is cancelled."""
        with QMutexLocker(self._mutex):
            return self._cancelled

    def _check_cancellation(self) -> bool:
        """Check for cancellation periodically."""
        self._cancel_check_counter += 1
        if self._cancel_check_counter >= self._cancel_check_frequency:
            self._cancel_check_counter = 0
            return self.is_cancelled()
        return False

    def run(self) -> None:
        """Main thread execution."""
        try:
            if self.is_cancelled():
                self.finished_processing.emit(False)
                return

            # Get configuration safely
            with QMutexLocker(self._mutex):
                operation_type = self._operation_type
                file_paths = self._file_paths.copy()
                external_folder = self._external_folder

            if not operation_type or not file_paths:
                self.error_occurred.emit("Invalid operation configuration")
                self.finished_processing.emit(False)
                return

            logger.debug(f"[HashWorker] Starting {operation_type} operation for {len(file_paths)} files")

            # Execute appropriate operation
            if operation_type == "duplicates":
                self._find_duplicates(file_paths)
            elif operation_type == "compare":
                self._compare_external(file_paths, external_folder)
            elif operation_type == "checksums":
                self._calculate_checksums(file_paths)
            else:
                self.error_occurred.emit(f"Unknown operation type: {operation_type}")
                self.finished_processing.emit(False)

        except Exception as e:
            logger.exception(f"[HashWorker] Error during operation: {e}")
            self.error_occurred.emit(str(e))
            self.finished_processing.emit(False)

    def _calculate_checksums(self, file_paths: List[str]) -> None:
        """Calculate checksums for files."""
        from core.hash_manager import HashManager

        hash_manager = HashManager()
        hash_results = {}
        total_files = len(file_paths)
        total_processed_bytes = 0

        self.status_updated.emit("Calculating checksums...")

        for i, file_path in enumerate(file_paths):
            if self._check_cancellation():
                logger.debug("[HashWorker] Checksum calculation cancelled")
                self.finished_processing.emit(False)
                return

            # Get file size
            try:
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            except OSError:
                file_size = 0

            # Update basic progress
            self.progress_updated.emit(i, total_files)
            self.file_processing.emit(os.path.basename(file_path))

            # Create stable progress callback
            progress_callback = ProgressCallback(self, i, total_files, total_processed_bytes)

            # Calculate hash with progress tracking
            file_hash = hash_manager.calculate_hash(file_path, progress_callback)
            if file_hash:
                hash_results[file_path] = file_hash

            # Update total processed bytes after file completion
            total_processed_bytes += file_size

        # Complete progress
        self.progress_updated.emit(total_files, total_files)
        self.status_updated.emit("Checksums calculated!")

        logger.info(f"[HashWorker] Calculated checksums for {len(hash_results)} files")
        self.checksums_calculated.emit(hash_results)
        self.finished_processing.emit(True)

    def _find_duplicates(self, file_paths: List[str]) -> None:
        """Find duplicate files by comparing hashes."""
        from core.hash_manager import HashManager

        hash_manager = HashManager()
        hash_cache = {}
        total_files = len(file_paths)
        total_processed_bytes = 0

        self.status_updated.emit("Calculating file hashes for duplicate detection...")

        for i, file_path in enumerate(file_paths):
            if self._check_cancellation():
                logger.debug("[HashWorker] Duplicate scan cancelled")
                self.finished_processing.emit(False)
                return

            # Get file size
            try:
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            except OSError:
                file_size = 0

            # Update progress
            self.progress_updated.emit(i, total_files)
            self.file_processing.emit(os.path.basename(file_path))

            # Create stable progress callback
            progress_callback = ProgressCallback(self, i, total_files, total_processed_bytes)

            # Calculate hash with progress tracking
            file_hash = hash_manager.calculate_hash(file_path, progress_callback)
            if file_hash:
                if file_hash in hash_cache:
                    hash_cache[file_hash].append(file_path)
                else:
                    hash_cache[file_hash] = [file_path]

            # Update total processed bytes after file completion
            total_processed_bytes += file_size

        # Complete progress
        self.progress_updated.emit(total_files, total_files)
        self.status_updated.emit("Analysis complete!")

        # Find duplicates
        duplicates = {hash_val: paths for hash_val, paths in hash_cache.items() if len(paths) > 1}

        logger.info(f"[HashWorker] Found {len(duplicates)} duplicate groups from {total_files} files")
        self.duplicates_found.emit(duplicates)
        self.finished_processing.emit(True)

    def _compare_external(self, file_paths: List[str], external_folder: str) -> None:
        """Compare files with external folder."""
        from core.hash_manager import HashManager

        hash_manager = HashManager()
        comparison_results = {}
        total_files = len(file_paths)
        total_processed_bytes = 0

        self.status_updated.emit(f"Comparing files with {os.path.basename(external_folder)}...")

        for i, file_path in enumerate(file_paths):
            if self._check_cancellation():
                logger.debug("[HashWorker] External comparison cancelled")
                self.finished_processing.emit(False)
                return

            # Get file size
            try:
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            except OSError:
                file_size = 0

            # Update progress
            self.progress_updated.emit(i, total_files)
            filename = os.path.basename(file_path)
            self.file_processing.emit(filename)

            # Create stable progress callback
            progress_callback = ProgressCallback(self, i, total_files, total_processed_bytes)

            # Calculate hash of current file with progress tracking
            current_hash = hash_manager.calculate_hash(file_path, progress_callback)
            if current_hash is None:
                continue

            # Look for file with same name in external folder
            external_file_path = Path(external_folder) / filename
            if external_file_path.exists():
                external_hash = hash_manager.calculate_hash(str(external_file_path))
                if external_hash is not None:
                    is_same = current_hash == external_hash
                    comparison_results[filename] = {
                        'current_path': file_path,
                        'external_path': str(external_file_path),
                        'is_same': is_same,
                        'current_hash': current_hash,
                        'external_hash': external_hash
                    }

            # Update total processed bytes after file completion
            total_processed_bytes += file_size

        # Complete progress
        self.progress_updated.emit(total_files, total_files)
        self.status_updated.emit("Comparison complete!")

        logger.info(f"[HashWorker] Compared {len(file_paths)} files with external folder")
        self.comparison_result.emit(comparison_results)
        self.finished_processing.emit(True)
