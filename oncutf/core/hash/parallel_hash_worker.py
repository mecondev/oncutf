"""Module: parallel_hash_worker.py.

Author: Michael Economou
Date: 2025-11-24
Updated: 2026-01-19 (Refactored to use BaseHashWorker)

Parallel hash worker using ThreadPoolExecutor for concurrent hash calculation.

Key Features:
    - Concurrent hash calculation using ThreadPoolExecutor
    - Thread-safe progress tracking with QMutex
    - Smart worker count based on CPU cores and I/O considerations
    - Cache-aware to avoid redundant calculations
    - Inherits common infrastructure from BaseHashWorker
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from oncutf.core.hash.base_hash_worker import BaseHashWorker
from oncutf.core.pyqt_imports import QMutexLocker
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ParallelHashWorker(BaseHashWorker):
    """Parallel hash worker using ThreadPoolExecutor for concurrent processing.

    Provides significant speedup for multiple files by utilizing all CPU cores
    while respecting I/O constraints.
    """

    def __init__(self, parent=None, max_workers: int | None = None):
        """Initialize parallel hash worker.

        Args:
            parent: Parent QObject (usually main window)
            max_workers: Maximum worker threads (None = auto-detect optimal count)

        """
        super().__init__(parent)

        # Determine optimal worker count
        if max_workers is None:
            import multiprocessing

            cpu_count = multiprocessing.cpu_count()
            # For I/O bound operations (hash calculation), use 2x CPU cores
            # but cap at 8 to avoid excessive overhead
            self._max_workers = min(cpu_count * 2, 8)
        else:
            self._max_workers = max(1, max_workers)

        logger.info("[ParallelHashWorker] Initialized with %d worker threads", self._max_workers)

        # Initialize hash manager
        from oncutf.core.hash.hash_manager import HashManager

        self._hash_manager = HashManager()

        # Parallel-specific state
        self._total_files = 0
        self._completed_files = 0
        self._cumulative_processed_bytes = 0
        self._results: dict[str, Any] = {}
        self._errors: list[tuple[str, str]] = []  # (file_path, error_msg)

        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0

    def _reset_state(self) -> None:
        """Reset parallel-specific state (must be called with mutex locked)."""
        self._cancelled = False
        self._total_files = len(self._file_paths)
        self._completed_files = 0
        self._cumulative_processed_bytes = 0
        self._results = {}
        self._errors = []
        self._cache_hits = 0
        self._cache_misses = 0
        self._batch_operations = []

    def _process_single_file(self, file_path: str) -> tuple[str, str | None, int]:
        """Process a single file in worker thread (called concurrently).

        Args:
            file_path: Path to file to process

        Returns:
            tuple: (file_path, hash_value, file_size)

        """
        if self.is_cancelled():
            return (file_path, None, 0)

        filename = os.path.basename(file_path)

        # Get file size
        try:
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        except OSError:
            file_size = 0

        # Check cache first
        hash_value = self._hash_manager.get_cached_hash(file_path)

        if hash_value is not None:
            # Cache hit
            with QMutexLocker(self._mutex):
                self._cache_hits += 1
            logger.debug("[ParallelHashWorker] Cache hit: %s", filename)
            return (file_path, hash_value, file_size)

        # Cache miss - calculate hash
        with QMutexLocker(self._mutex):
            self._cache_misses += 1

        logger.debug("[ParallelHashWorker] Calculating hash: %s", filename)

        try:
            hash_value = self._hash_manager.calculate_hash(
                file_path, cancellation_check=self.is_cancelled
            )

            if hash_value is not None:
                # Store hash (will use batch if enabled)
                self._store_hash_optimized(file_path, hash_value, "crc32")

            return (file_path, hash_value, file_size)

        except Exception as e:
            logger.warning("[ParallelHashWorker] Error processing %s: %s", filename, e)
            with QMutexLocker(self._mutex):
                self._errors.append((file_path, str(e)))
            return (file_path, None, file_size)

    # Note: _store_hash_optimized is inherited from BaseHashWorker

    def _update_progress(self, file_path: str, file_size: int) -> None:
        """Update progress counters and emit signals (thread-safe)."""
        with QMutexLocker(self._mutex):
            self._completed_files += 1
            self._cumulative_processed_bytes += file_size

            current = self._completed_files
            total = self._total_files
            filename = os.path.basename(file_path)

            # Copy for signal emission (avoid holding mutex)
            bytes_processed = self._cumulative_processed_bytes
            total_bytes = self._total_bytes

        # Emit signals outside mutex to avoid deadlock
        self.progress_updated.emit(current, total, filename)
        self.size_progress.emit(int(bytes_processed), int(total_bytes))

    def run(self) -> None:
        """Main thread execution with parallel processing."""
        try:
            if self.is_cancelled():
                self.finished_processing.emit(False)
                return

            # Initialize batch manager if enabled
            if self._enable_batching:
                try:
                    from oncutf.core.batch import get_batch_manager

                    self._batch_manager = get_batch_manager(self.main_window)
                    logger.debug("[ParallelHashWorker] Batch manager initialized")
                except Exception as e:
                    logger.warning("[ParallelHashWorker] Failed to init batch manager: %s", e)
                    self._enable_batching = False

            # Get operation config
            with QMutexLocker(self._mutex):
                operation_type = self._operation_type
                file_paths = self._file_paths.copy()
                external_folder = self._external_folder

            if not operation_type or not file_paths:
                self.error_occurred.emit("Invalid operation configuration")
                self.finished_processing.emit(False)
                return

            # Calculate total size if not already set
            if self._total_bytes == 0:
                self._total_bytes = self._calculate_total_size(file_paths)

            # Execute operation with parallel workers
            if operation_type == "duplicates":
                self._find_duplicates_parallel(file_paths)
            elif operation_type == "compare" and external_folder:
                self._compare_external_parallel(file_paths, external_folder)
            elif operation_type == "checksums":
                self._calculate_checksums_parallel(file_paths)

        except Exception as e:
            logger.exception("[ParallelHashWorker] Unexpected error: %s", e)
            self.error_occurred.emit(str(e))
            self.finished_processing.emit(False)
        finally:
            # Flush batch operations
            if self._enable_batching and self._batch_manager and self._batch_operations:
                logger.info(
                    "[ParallelHashWorker] Flushing %d batched ops",
                    len(self._batch_operations),
                )
                try:
                    flushed = self._batch_manager.flush_batch_type("hash_store")
                    logger.info("[ParallelHashWorker] Flushed %d hash operations", flushed)

                    stats = self._batch_manager.get_stats()
                    logger.info(
                        "[ParallelHashWorker] Batch stats: %d batched, avg: %.1f, saved: %.2fs",
                        stats.batched_operations,
                        stats.average_batch_size,
                        stats.total_time_saved,
                    )
                except Exception as e:
                    logger.error("[ParallelHashWorker] Error flushing batches: %s", e)

    def _calculate_checksums_parallel(self, file_paths: list[str]) -> None:
        """Calculate checksums using parallel workers."""
        hash_results: dict[str, str] = {}
        total_files = len(file_paths)

        self.status_updated.emit("Calculating CRC32 checksums...")

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(self._process_single_file, path): path for path in file_paths
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_path):
                if self.is_cancelled():
                    # Cancel remaining tasks
                    executor.shutdown(wait=False, cancel_futures=True)

                    if hash_results:
                        logger.info(
                            "[ParallelHashWorker] Cancelled - showing %d results",
                            len(hash_results),
                        )
                        self.checksums_calculated.emit(hash_results)

                    self.finished_processing.emit(False)
                    return

                try:
                    file_path, hash_value, file_size = future.result()

                    if hash_value:
                        hash_results[file_path] = hash_value
                        # Emit real-time update signal with hash value
                        # This allows the main thread to store it safely
                        self.file_hash_calculated.emit(file_path, hash_value)

                    # Update progress
                    self._update_progress(file_path, file_size)

                except Exception as e:
                    logger.warning("[ParallelHashWorker] Task failed: %s", e)

        # Report completion
        self.progress_updated.emit(total_files, total_files, "Complete")
        self.size_progress.emit(int(self._total_bytes), int(self._total_bytes))

        # Cache statistics
        cache_hit_rate = (
            (self._cache_hits / (self._cache_hits + self._cache_misses) * 100)
            if (self._cache_hits + self._cache_misses) > 0
            else 0
        )

        batch_info = f", batch ops: {len(self._batch_operations)}" if self._batch_operations else ""

        self.status_updated.emit(
            f"CRC32 checksums calculated for {len(hash_results)} files! "
            f"Cache hit rate: {cache_hit_rate:.1f}%{batch_info}"
        )

        logger.info(
            "[ParallelHashWorker] Completed %d files (hits: %d, misses: %d, rate: %.1f%%)",
            len(hash_results),
            self._cache_hits,
            self._cache_misses,
            cache_hit_rate,
        )

        self.checksums_calculated.emit(hash_results)
        self.finished_processing.emit(True)

    def _find_duplicates_parallel(self, file_paths: list[str]) -> None:
        """Find duplicates using parallel hash calculation."""
        hash_to_files: dict[str, list[str]] = {}
        len(file_paths)

        self.status_updated.emit("Scanning for duplicates...")

        # Calculate all hashes in parallel
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_path = {
                executor.submit(self._process_single_file, path): path for path in file_paths
            }

            for future in as_completed(future_to_path):
                if self.is_cancelled():
                    executor.shutdown(wait=False, cancel_futures=True)
                    self.finished_processing.emit(False)
                    return

                try:
                    file_path, hash_value, file_size = future.result()

                    if hash_value:
                        if hash_value not in hash_to_files:
                            hash_to_files[hash_value] = []
                        hash_to_files[hash_value].append(file_path)

                    self._update_progress(file_path, file_size)

                except Exception as e:
                    logger.warning("[ParallelHashWorker] Duplicate scan task failed: %s", e)

        # Filter to only duplicates (hash with multiple files)
        duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}

        logger.info("[ParallelHashWorker] Found %d duplicate groups", len(duplicates))

        self.duplicates_found.emit(duplicates)
        self.finished_processing.emit(True)

    def _compare_external_parallel(self, file_paths: list[str], external_folder: str) -> None:
        """Compare files with external folder using parallel processing."""
        comparison_results = {}
        external_path = Path(external_folder)

        self.status_updated.emit("Comparing files...")

        # Build list of (source_file, external_file) pairs
        file_pairs: list[tuple[str, str | None]] = []
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            external_file = external_path / filename

            if external_file.exists() and external_file.is_file():
                file_pairs.append((file_path, str(external_file)))
            else:
                file_pairs.append((file_path, None))

        # Process pairs in parallel
        def process_pair(pair: tuple[str, str | None]) -> tuple[str, dict[str, Any]]:
            source_path, external_path = pair

            if external_path is None:
                return (source_path, {"exists_in_external": False})

            # Calculate both hashes
            source_hash = self._hash_manager.calculate_hash(source_path)
            external_hash = self._hash_manager.calculate_hash(external_path)

            return (
                source_path,
                {
                    "exists_in_external": True,
                    "source_hash": source_hash,
                    "external_hash": external_hash,
                    "is_same": (
                        source_hash == external_hash if source_hash and external_hash else False
                    ),
                },
            )

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_pair = {executor.submit(process_pair, pair): pair for pair in file_pairs}

            for future in as_completed(future_to_pair):
                if self.is_cancelled():
                    executor.shutdown(wait=False, cancel_futures=True)
                    self.finished_processing.emit(False)
                    return

                try:
                    source_path, result = future.result()
                    comparison_results[source_path] = result

                    # Update progress (approximate file size)
                    file_size = os.path.getsize(source_path) if os.path.exists(source_path) else 0
                    self._update_progress(source_path, file_size)

                except Exception as e:
                    logger.warning("[ParallelHashWorker] Comparison task failed: %s", e)

        logger.info("[ParallelHashWorker] Compared %d files", len(comparison_results))

        self.comparison_result.emit(comparison_results)
        self.finished_processing.emit(True)
