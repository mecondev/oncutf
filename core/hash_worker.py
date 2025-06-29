"""
hash_worker.py

Author: Michael Economou
Date: 2025-06-23

QThread worker for background hash calculation operations.

This module provides thread-safe, cancellable hash operations with accurate progress updates.

Key Features:
- Thread-safe with QMutex protection
- Support for multiple hash operations (duplicates, comparison, checksums)
- Accurate CRC32 progress tracking with total size calculation
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

from core.qt_imports import QMutexLocker

from core.qt_imports import QMutex, QThread, pyqtSignal
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class HashWorker(QThread):
    """
    Background worker for hash calculation operations.

    Supports three main operations:
    1. Find duplicates in file list
    2. Compare files with external folder
    3. Calculate checksums for files
    """

    # Progress signals
    progress_updated = pyqtSignal(int, int, str)  # current_file, total_files, current_filename
    size_progress = pyqtSignal('qint64', 'qint64')  # total_bytes_processed, total_bytes_size (64-bit integers)
    status_updated = pyqtSignal(str)  # status message

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

        # Size tracking
        self._total_bytes = 0
        self._cumulative_processed_bytes = 0  # Continuously increases, never resets per file

    def setup_duplicate_scan(self, file_paths: List[str]) -> None:
        """Configure worker for duplicate detection."""
        with QMutexLocker(self._mutex):
            self._operation_type = "duplicates"
            self._file_paths = list(file_paths)
            self._external_folder = None
            self._cancelled = False
            self._cancel_check_counter = 0
            self._total_bytes = 0
            self._cumulative_processed_bytes = 0

    def setup_external_comparison(self, file_paths: List[str], external_folder: str) -> None:
        """Configure worker for external folder comparison."""
        with QMutexLocker(self._mutex):
            self._operation_type = "compare"
            self._file_paths = list(file_paths)
            self._external_folder = external_folder
            self._cancelled = False
            self._cancel_check_counter = 0
            self._total_bytes = 0
            self._cumulative_processed_bytes = 0

    def setup_checksum_calculation(self, file_paths: List[str]) -> None:
        """Configure worker for checksum calculation."""
        with QMutexLocker(self._mutex):
            self._operation_type = "checksums"
            self._file_paths = list(file_paths)
            self._external_folder = None
            self._cancelled = False
            self._cancel_check_counter = 0
            self._total_bytes = 0
            self._cumulative_processed_bytes = 0

    def set_total_size(self, total_size: int) -> None:
        """Set the total size from external calculation to avoid duplicate work."""
        with QMutexLocker(self._mutex):
            self._total_bytes = total_size
            logger.debug(f"[HashWorker] Total size set to: {total_size:,} bytes")

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

    def _calculate_total_size(self, file_paths: List[str]) -> int:
        """Calculate total size of all files for accurate progress tracking."""
        total_size = 0
        files_counted = 0

        self.status_updated.emit("Calculating total file size...")

        for i, file_path in enumerate(file_paths):
            # Check for cancellation more frequently during size calculation
            if i % 10 == 0 and self.is_cancelled():
                logger.debug("[HashWorker] Size calculation cancelled")
                return 0

            try:
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    total_size += size
                    files_counted += 1

                    # Update progress during size calculation
                    if i % 50 == 0:  # Update every 50 files
                        progress = int((i / len(file_paths)) * 100)
                        self.status_updated.emit(f"Calculating total size... {progress}% ({i}/{len(file_paths)})")

            except (OSError, PermissionError) as e:
                logger.debug(f"[HashWorker] Could not get size for {file_path}: {e}")
                continue

        logger.info(f"[HashWorker] Total size calculated: {total_size:,} bytes for {files_counted} files")
        return total_size

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

            logger.info(f"[HashWorker] Starting {operation_type} operation for {len(file_paths)} files")

            # Execute appropriate operation
            if operation_type == "duplicates":
                self._find_duplicates(file_paths)
            elif operation_type == "compare":
                if external_folder is None:
                    self.error_occurred.emit("External folder not specified for comparison")
                    self.finished_processing.emit(False)
                    return
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

    def _process_file_with_progress(self, file_path: str, i: int, total_files: int) -> tuple[str | None, int]:
        """
        Helper method to process a single file with progress tracking.

        Returns:
            tuple: (file_hash, file_size) or (None, file_size) if hash failed
        """
        filename = os.path.basename(file_path)
        self.progress_updated.emit(i + 1, total_files, filename)

        # Get file size for progress tracking
        try:
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        except OSError:
            file_size = 0

        # For large files (>100MB), use real-time progress callback
        progress_callback = None
        if file_size > 100_000_000:  # 100MB threshold
            def update_progress(bytes_processed_in_file):
                """Real-time progress callback for large files."""
                with QMutexLocker(self._mutex):
                    current_total = self._cumulative_processed_bytes + bytes_processed_in_file
                    self.size_progress.emit(int(current_total), int(self._total_bytes))

            progress_callback = update_progress

        # Calculate hash with optional real-time progress for large files
        from core.hash_manager import HashManager
        hash_manager = HashManager()
        file_hash = hash_manager.calculate_hash(file_path, progress_callback=progress_callback)

        # Update cumulative bytes AFTER each file is completed
        with QMutexLocker(self._mutex):
            if file_size > 0:
                new_cumulative = self._cumulative_processed_bytes + file_size
                # Check for potential overflow (stay within safe 64-bit range)
                if new_cumulative > self._cumulative_processed_bytes:  # No overflow
                    self._cumulative_processed_bytes = new_cumulative
                else:
                    # Overflow detected - cap at current value and log warning
                    logger.warning(f"[HashWorker] Size overflow detected, capping progress at {self._cumulative_processed_bytes:,} bytes")

            # Emit with explicit 64-bit integers to prevent overflow
            self.size_progress.emit(int(self._cumulative_processed_bytes), int(self._total_bytes))

        return file_hash, file_size

    def _calculate_checksums(self, file_paths: List[str]) -> None:
        """Calculate checksums with file-by-file progress tracking."""
        hash_results = {}
        total_files = len(file_paths)

        self.status_updated.emit("Calculating CRC32 checksums...")

        # Reset cumulative tracking at start
        with QMutexLocker(self._mutex):
            self._cumulative_processed_bytes = 0

        for i, file_path in enumerate(file_paths):
            if self._check_cancellation():
                self.finished_processing.emit(False)
                return

            file_hash, file_size = self._process_file_with_progress(file_path, i, total_files)
            if file_hash:
                hash_results[file_path] = file_hash

        # Complete progress - final update
        self.progress_updated.emit(total_files, total_files, "Complete")
        self.size_progress.emit(int(self._total_bytes), int(self._total_bytes))
        self.status_updated.emit(f"CRC32 checksums calculated for {len(hash_results)} files!")

        logger.info(f"[HashWorker] Calculated checksums for {len(hash_results)} files")
        self.checksums_calculated.emit(hash_results)
        self.finished_processing.emit(True)

    def _find_duplicates(self, file_paths: List[str]) -> None:
        """Find duplicates with file-by-file progress tracking."""
        hash_cache = {}
        total_files = len(file_paths)

        self.status_updated.emit("Calculating CRC32 hashes for duplicate detection...")

        # Reset cumulative tracking at start
        with QMutexLocker(self._mutex):
            self._cumulative_processed_bytes = 0

        for i, file_path in enumerate(file_paths):
            if self._check_cancellation():
                self.finished_processing.emit(False)
                return

            file_hash, file_size = self._process_file_with_progress(file_path, i, total_files)
            if file_hash:
                if file_hash in hash_cache:
                    hash_cache[file_hash].append(file_path)
                else:
                    hash_cache[file_hash] = [file_path]

        # Complete progress with final updates
        self.progress_updated.emit(total_files, total_files, "Complete")
        self.size_progress.emit(int(self._total_bytes), int(self._total_bytes))
        self.status_updated.emit("Duplicate analysis complete!")

        # Find duplicates
        duplicates = {hash_val: paths for hash_val, paths in hash_cache.items() if len(paths) > 1}

        logger.info(f"[HashWorker] Found {len(duplicates)} duplicate groups from {total_files} files")
        self.duplicates_found.emit(duplicates)
        self.finished_processing.emit(True)

    def _compare_external(self, file_paths: List[str], external_folder: str) -> None:
        """Compare files with external folder using file-by-file progress tracking."""
        from core.hash_manager import HashManager

        hash_manager = HashManager()
        comparison_results = {}
        total_files = len(file_paths)

        self.status_updated.emit(f"Comparing files with {os.path.basename(external_folder)}...")

        # Reset cumulative tracking at start
        with QMutexLocker(self._mutex):
            self._cumulative_processed_bytes = 0

        for i, file_path in enumerate(file_paths):
            if self._check_cancellation():
                self.finished_processing.emit(False)
                return

            filename = os.path.basename(file_path)
            current_hash, file_size = self._process_file_with_progress(file_path, i, total_files)

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

        # Complete progress with final updates
        self.progress_updated.emit(total_files, total_files, "Complete")
        self.size_progress.emit(int(self._total_bytes), int(self._total_bytes))
        self.status_updated.emit("File comparison complete!")

        logger.info(f"[HashWorker] Compared {len(file_paths)} files with external folder")
        self.comparison_result.emit(comparison_results)
        self.finished_processing.emit(True)
