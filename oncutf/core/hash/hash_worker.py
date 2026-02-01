"""Module: hash_worker.py.

Author: Michael Economou
Date: 2025-06-10
Updated: 2026-01-19 (Refactored to use BaseHashWorker)

Sequential hash worker for background hash calculation operations.

This module provides thread-safe, cancellable hash operations with accurate progress updates.

Key Features:
- Inherits common infrastructure from BaseHashWorker
- Sequential file processing (legacy, simpler than parallel)
- Smart cache checking to avoid redundant hash calculations
- Batch operations optimization for better performance
- Real-time progress tracking with size-based updates

Usage:
    worker = HashWorker()
    worker.setup_duplicate_scan(file_paths)
    worker.duplicates_found.connect(handle_duplicates)
    worker.start()
"""

import os
from pathlib import Path
from typing import Any, Protocol

from PyQt5.QtCore import QMutexLocker

from oncutf.core.hash.base_hash_worker import BaseHashWorker
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class HashStore(Protocol):
    """Protocol for hash storage operations."""

    def store_hash(self, file_path: str, hash_value: str, algorithm: str) -> None:
        """Store hash value for file path."""
        ...

    def get_cached_hash(self, file_path: str) -> str | None:
        """Get cached hash for file path if available."""
        ...

    def calculate_hash(self, file_path: str, **kwargs: Any) -> str | None:
        """Calculate hash for file path."""
        ...


class HashWorker(BaseHashWorker):
    """Sequential background worker for hash calculation operations.

    Inherits signals, state management, and common methods from BaseHashWorker.
    Provides sequential processing (one file at a time) with real-time progress.

    Supports three main operations:
    1. Find duplicates in file list
    2. Compare files with external folder
    3. Calculate checksums for files
    """

    def __init__(self, parent: Any = None) -> None:
        """Initialize hash worker with hash manager and operation state."""
        super().__init__(parent)

        # Initialize hash manager
        from typing import cast

        from oncutf.core.hash.hash_manager import HashManager

        self._hash_manager: HashStore = cast("HashStore", HashManager())

        # Sequential-specific progress tracking
        self._cancel_check_counter = 0
        self._cancel_check_frequency = 5  # Check every 5 operations

        # Size tracking for progress
        self._cumulative_processed_bytes = 0

        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0

    def _reset_sequential_state(self) -> None:
        """Reset sequential-specific state (must be called with mutex locked)."""
        self._cancelled = False
        self._cancel_check_counter = 0
        self._total_bytes = 0
        self._cumulative_processed_bytes = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._batch_operations = []

    def setup_duplicate_scan(self, file_paths: list[str]) -> None:
        """Configure worker for duplicate detection."""
        super().setup_duplicate_scan(file_paths)
        with QMutexLocker(self._mutex):
            self._reset_sequential_state()

    def setup_external_comparison(self, file_paths: list[str], external_folder: str) -> None:
        """Configure worker for external folder comparison."""
        super().setup_external_comparison(file_paths, external_folder)
        with QMutexLocker(self._mutex):
            self._reset_sequential_state()

    def setup_checksum_calculation(self, file_paths: list[str]) -> None:
        """Configure worker for checksum calculation."""
        super().setup_checksum_calculation(file_paths)
        with QMutexLocker(self._mutex):
            self._reset_sequential_state()

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

            # Initialize batch manager if enabled
            if self._enable_batching:
                try:
                    from oncutf.infra.batch import get_batch_manager

                    self._batch_manager = get_batch_manager(self.main_window)
                    logger.debug("[HashWorker] Batch operations manager initialized")
                except Exception as e:
                    logger.warning("[HashWorker] Failed to initialize batch manager: %s", e)
                    self._enable_batching = False

            # Get configuration safely
            with QMutexLocker(self._mutex):
                operation_type = self._operation_type
                file_paths = self._file_paths.copy()
                external_folder = self._external_folder

            if not operation_type or not file_paths:
                self.error_occurred.emit("Invalid operation configuration")
                return

            # Calculate total size if not already set
            if self._total_bytes == 0:
                self._total_bytes = self._calculate_total_size(file_paths)

            # Execute the appropriate operation
            if operation_type == "duplicates":
                self._find_duplicates(file_paths)
            elif operation_type == "compare" and external_folder:
                self._compare_external(file_paths, external_folder)
            elif operation_type == "checksums":
                self._calculate_checksums(file_paths)

        except Exception as e:
            logger.exception("[HashWorker] Unexpected error")
            self.error_occurred.emit(str(e))
            self.finished_processing.emit(False)
        finally:
            # Flush any remaining batch operations
            if self._enable_batching and self._batch_manager and self._batch_operations:
                logger.info(
                    "[HashWorker] Flushing %d batched hash operations",
                    len(self._batch_operations),
                )

                try:
                    # Force flush all hash operations
                    flushed = self._batch_manager.flush_batch_type("hash_store")
                    logger.info("[HashWorker] Successfully flushed %d hash operations", flushed)

                    # Get batch statistics
                    stats = self._batch_manager.get_stats()
                    logger.info(
                        "[HashWorker] Batch stats: %d batched, avg batch size: %.1f, time saved: %.2fs",
                        stats.batched_operations,
                        stats.average_batch_size,
                        stats.total_time_saved,
                    )

                except Exception as e:
                    logger.error("[HashWorker] Error flushing batch operations: %s", e)

    def _check_cache_before_calculation(self, file_path: str) -> str | None:
        """Check if hash exists in cache before calculating.

        Returns:
            str: Hash value if found in cache, None otherwise

        """
        try:
            hash_value = self._hash_manager.get_cached_hash(file_path)
            if hash_value is not None:
                self._cache_hits += 1
                logger.debug("[HashWorker] Cache hit for: %s", Path(file_path).name)
                return hash_value
            self._cache_misses += 1
            logger.debug("[HashWorker] Cache miss for: %s", Path(file_path).name)
        except Exception as e:
            logger.debug("[HashWorker] Cache check failed for %s: %s", file_path, e)
            self._cache_misses += 1
            return None
        else:
            return None

    def _process_file_with_progress(
        self, file_path: str, i: int, total_files: int
    ) -> tuple[str | None, int]:
        """Helper method to process a single file with progress tracking.

        Checks cache first before calculating hash.

        Returns:
            tuple: (file_hash, file_size) or (None, file_size) if hash failed

        """
        filename = Path(file_path).name
        self.progress_updated.emit(i + 1, total_files, filename)

        # Get file size for progress tracking
        try:
            path = Path(file_path)
            file_size = path.stat().st_size if path.exists() else 0
        except OSError:
            file_size = 0

        # Check cache first before calculating
        file_hash = self._check_cache_before_calculation(file_path)

        if file_hash is not None:
            # Hash found in cache - update progress and return
            with QMutexLocker(self._mutex):
                if file_size > 0:
                    new_cumulative = self._cumulative_processed_bytes + file_size
                    if new_cumulative > self._cumulative_processed_bytes:
                        self._cumulative_processed_bytes = new_cumulative
                    else:
                        logger.warning(
                            "[HashWorker] Size overflow detected, capping progress at %s bytes",
                            format(self._cumulative_processed_bytes, ","),
                        )

                self.size_progress.emit(
                    int(self._cumulative_processed_bytes), int(self._total_bytes)
                )

            # Note: No signal emission for cache hits - icon should already be correct
            return file_hash, file_size

        # Hash not in cache - need to calculate
        logger.debug("[HashWorker] Calculating hash for: %s", filename)

        # For large files (>50MB), use real-time progress callback
        progress_callback = None
        if file_size > 50_000_000:  # 50MB threshold

            def update_progress(bytes_processed_in_file: int) -> None:
                """Real-time progress callback for large files."""
                with QMutexLocker(self._mutex):
                    current_total = self._cumulative_processed_bytes + bytes_processed_in_file
                    self.size_progress.emit(int(current_total), int(self._total_bytes))

            progress_callback = update_progress

        # Calculate hash with optional real-time progress for large files
        file_hash = self._hash_manager.calculate_hash(
            file_path, progress_callback=progress_callback
        )

        # Store hash using optimized batching if available
        if file_hash is not None:
            self._store_hash_optimized(file_path, file_hash, "crc32")

        # Update cumulative bytes AFTER each file is completed
        with QMutexLocker(self._mutex):
            if file_size > 0:
                new_cumulative = self._cumulative_processed_bytes + file_size
                # Check for potential overflow (stay within safe 64-bit range)
                if new_cumulative > self._cumulative_processed_bytes:  # No overflow
                    self._cumulative_processed_bytes = new_cumulative
                else:
                    # Overflow detected - cap at current value and log warning
                    logger.warning(
                        "[HashWorker] Size overflow detected, capping progress at %s bytes",
                        format(self._cumulative_processed_bytes, ","),
                    )

            # Emit with explicit 64-bit integers to prevent overflow
            self.size_progress.emit(int(self._cumulative_processed_bytes), int(self._total_bytes))

        # Emit signal for real-time UI update only when hash is newly calculated (not from cache)
        if file_hash is not None:
            self.file_hash_calculated.emit(file_path, file_hash)
            logger.debug("[HashWorker] Emitted file_hash_calculated signal for: %s", filename)

        return file_hash, file_size

    def _calculate_checksums(self, file_paths: list[str]) -> None:
        """Calculate checksums with file-by-file progress tracking and smart cache usage."""
        hash_results: dict[str, str] = {}
        total_files = len(file_paths)

        self.status_updated.emit("Calculating CRC32 checksums...")

        # Reset cumulative tracking at start
        with QMutexLocker(self._mutex):
            self._cumulative_processed_bytes = 0

        for i, file_path in enumerate(file_paths):
            if self._check_cancellation():
                # Show partial results if operation was cancelled
                if hash_results:
                    logger.info(
                        "[HashWorker] Operation cancelled - showing results for %d files that were processed",
                        len(hash_results),
                    )
                    self.checksums_calculated.emit(hash_results)
                self.finished_processing.emit(False)
                return

            file_hash, _file_size = self._process_file_with_progress(file_path, i, total_files)
            if file_hash:
                hash_results[file_path] = file_hash

        # Complete progress - final update
        self.progress_updated.emit(total_files, total_files, "Complete")
        self.size_progress.emit(int(self._total_bytes), int(self._total_bytes))

        # Report cache statistics
        cache_hit_rate = (
            (self._cache_hits / (self._cache_hits + self._cache_misses) * 100)
            if (self._cache_hits + self._cache_misses) > 0
            else 0
        )
        batch_info = f", batch ops: {len(self._batch_operations)}" if self._batch_operations else ""
        self.status_updated.emit(
            f"CRC32 checksums calculated for {len(hash_results)} files! Cache hit rate: {cache_hit_rate:.1f}%{batch_info}"
        )

        logger.info("[HashWorker] Calculated checksums for %d files", len(hash_results))
        logger.info(
            "[HashWorker] Cache performance - Hits: %d, Misses: %d, Hit rate: %.1f%%",
            self._cache_hits,
            self._cache_misses,
            cache_hit_rate,
        )
        if self._batch_operations:
            logger.info("[HashWorker] Batch operations queued: %d", len(self._batch_operations))
        self.checksums_calculated.emit(hash_results)
        self.finished_processing.emit(True)

    def _find_duplicates(self, file_paths: list[str]) -> None:
        """Find duplicates with file-by-file progress tracking and smart cache usage."""
        hash_to_files: dict[str, list[str]] = {}  # Use more descriptive name
        total_files = len(file_paths)

        self.status_updated.emit("Calculating CRC32 hashes for duplicate detection...")

        # Reset cumulative tracking at start
        with QMutexLocker(self._mutex):
            self._cumulative_processed_bytes = 0

        for i, file_path in enumerate(file_paths):
            if self._check_cancellation():
                # Show partial results if operation was cancelled
                if hash_to_files:
                    # Find duplicates from partial results
                    partial_duplicates = {
                        hash_val: paths
                        for hash_val, paths in hash_to_files.items()
                        if len(paths) > 1
                    }
                    if partial_duplicates:
                        logger.info(
                            "[HashWorker] Operation cancelled - showing partial duplicate results for %d groups",
                            len(partial_duplicates),
                        )
                        self.duplicates_found.emit(partial_duplicates)
                self.finished_processing.emit(False)
                return

            file_hash, _file_size = self._process_file_with_progress(file_path, i, total_files)
            if file_hash:
                if file_hash in hash_to_files:
                    hash_to_files[file_hash].append(file_path)
                else:
                    hash_to_files[file_hash] = [file_path]

        # Complete progress with final updates
        self.progress_updated.emit(total_files, total_files, "Complete")
        self.size_progress.emit(int(self._total_bytes), int(self._total_bytes))

        # Report cache statistics
        cache_hit_rate = (
            (self._cache_hits / (self._cache_hits + self._cache_misses) * 100)
            if (self._cache_hits + self._cache_misses) > 0
            else 0
        )
        batch_info = f", batch ops: {len(self._batch_operations)}" if self._batch_operations else ""
        self.status_updated.emit(
            f"Duplicate analysis complete! Cache hit rate: {cache_hit_rate:.1f}%{batch_info}"
        )

        # Find duplicates
        duplicates = {
            hash_val: paths for hash_val, paths in hash_to_files.items() if len(paths) > 1
        }

        logger.info(
            "[HashWorker] Found %d duplicate groups from %d files",
            len(duplicates),
            total_files,
        )
        logger.info(
            "[HashWorker] Cache performance - Hits: %d, Misses: %d, Hit rate: %.1f%%",
            self._cache_hits,
            self._cache_misses,
            cache_hit_rate,
        )
        if self._batch_operations:
            logger.info("[HashWorker] Batch operations queued: %d", len(self._batch_operations))
        self.duplicates_found.emit(duplicates)
        self.finished_processing.emit(True)

    def _compare_external(self, file_paths: list[str], external_folder: str) -> None:
        """Compare files with external folder using file-by-file progress tracking."""
        comparison_results: dict[str, Any] = {}
        total_files = len(file_paths)

        self.status_updated.emit(f"Comparing files with {Path(external_folder).name}...")

        # Reset cumulative tracking at start
        with QMutexLocker(self._mutex):
            self._cumulative_processed_bytes = 0

        for i, file_path in enumerate(file_paths):
            if self._check_cancellation():
                # Show partial results if operation was cancelled
                if comparison_results:
                    logger.info(
                        "[HashWorker] Operation cancelled - showing partial comparison results for %d files",
                        len(comparison_results),
                    )
                    self.comparison_result.emit(comparison_results)
                self.finished_processing.emit(False)
                return

            filename = Path(file_path).name
            current_hash, _file_size = self._process_file_with_progress(file_path, i, total_files)

            if current_hash is None:
                continue

            # Look for file with same name in external folder
            external_file_path = Path(external_folder) / filename
            if external_file_path.exists():
                # Check cache for external file too
                external_hash = self._check_cache_before_calculation(str(external_file_path))
                if external_hash is None:
                    # Calculate if not in cache
                    external_hash = self._hash_manager.calculate_hash(str(external_file_path))
                    # Store external hash using batch operations too
                    if external_hash is not None:
                        self._store_hash_optimized(str(external_file_path), external_hash, "crc32")

                if external_hash is not None:
                    is_same = current_hash == external_hash
                    comparison_results[filename] = {
                        "current_path": file_path,
                        "external_path": str(external_file_path),
                        "is_same": is_same,
                        "current_hash": current_hash,
                        "external_hash": external_hash,
                    }

        # Complete progress with final updates
        self.progress_updated.emit(total_files, total_files, "Complete")
        self.size_progress.emit(int(self._total_bytes), int(self._total_bytes))

        # Report cache statistics
        cache_hit_rate = (
            (self._cache_hits / (self._cache_hits + self._cache_misses) * 100)
            if (self._cache_hits + self._cache_misses) > 0
            else 0
        )
        batch_info = f", batch ops: {len(self._batch_operations)}" if self._batch_operations else ""
        self.status_updated.emit(
            f"File comparison complete! Cache hit rate: {cache_hit_rate:.1f}%{batch_info}"
        )

        logger.info("[HashWorker] Compared %d files with external folder", len(file_paths))
        logger.info(
            "[HashWorker] Cache performance - Hits: %d, Misses: %d, Hit rate: %.1f%%",
            self._cache_hits,
            self._cache_misses,
            cache_hit_rate,
        )
        if self._batch_operations:
            logger.info("[HashWorker] Batch operations queued: %d", len(self._batch_operations))
        self.comparison_result.emit(comparison_results)
        self.finished_processing.emit(True)
