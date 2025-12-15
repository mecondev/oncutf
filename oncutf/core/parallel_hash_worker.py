"""
Module: parallel_hash_worker.py

Author: Michael Economou
Date: 2025-11-24

Parallel hash worker using ThreadPoolExecutor for concurrent hash calculation.
Replaces single-threaded HashWorker with multi-threaded approach for better performance.

Key Features:
    - Concurrent hash calculation using ThreadPoolExecutor
    - Thread-safe progress tracking with QMutex
    - Smart worker count based on CPU cores and I/O considerations
    - Cache-aware to avoid redundant calculations
    - Graceful cancellation support
    - Real-time progress updates via Qt signals
    - Compatible with existing HashOperationsManager interface

Architecture:
    - Main QThread manages ThreadPoolExecutor workers
    - Each worker thread calculates hash for one file
    - Progress aggregation happens in main thread
    - Signals emitted to Qt event loop for UI updates
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from oncutf.core.pyqt_imports import QMutex, QMutexLocker, QThread, pyqtSignal
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ParallelHashWorker(QThread):
    """
    Parallel hash worker using ThreadPoolExecutor for concurrent processing.

    Provides significant speedup for multiple files by utilizing all CPU cores
    while respecting I/O constraints.

    Compatibility:
        Drop-in replacement for HashWorker with same signal interface.
    """

    # Progress signals (same as HashWorker)
    progress_updated = pyqtSignal(int, int, str)  # current_file, total_files, current_filename
    size_progress = pyqtSignal("qint64", "qint64")  # bytes_processed, total_bytes
    status_updated = pyqtSignal(str)  # status message

    # Result signals (same as HashWorker)
    duplicates_found = pyqtSignal(dict)  # {hash: [file_paths]}
    comparison_result = pyqtSignal(dict)  # comparison results
    checksums_calculated = pyqtSignal(dict)  # {file_path: hash}

    # Control signals (same as HashWorker)
    finished_processing = pyqtSignal(bool)  # success flag
    error_occurred = pyqtSignal(str)  # error message

    # Real-time UI update signals (enhanced with hash value)
    file_hash_calculated = pyqtSignal(str, str)  # file_path, hash_value

    def __init__(self, parent=None, max_workers: int | None = None):
        """
        Initialize parallel hash worker.

        Args:
            parent: Parent QObject (usually main window)
            max_workers: Maximum worker threads (None = auto-detect optimal count)
        """
        super().__init__(parent)
        self._mutex = QMutex()
        self._cancelled = False
        self.main_window = parent

        # Determine optimal worker count
        if max_workers is None:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            # For I/O bound operations (hash calculation), use 2x CPU cores
            # but cap at 8 to avoid excessive overhead
            self._max_workers = min(cpu_count * 2, 8)
        else:
            self._max_workers = max(1, max_workers)

        logger.info(f"[ParallelHashWorker] Initialized with {self._max_workers} worker threads")

        # Shared hash manager for cache access
        from oncutf.core.hash_manager import HashManager
        self._hash_manager = HashManager()

        # Operation configuration
        self._operation_type: str | None = None
        self._file_paths: list[str] = []
        self._external_folder: str | None = None

        # Thread-safe progress tracking
        self._total_files = 0
        self._completed_files = 0
        self._total_bytes = 0
        self._cumulative_processed_bytes = 0

        # Thread-safe result storage
        self._results: dict = {}
        self._errors: list[tuple[str, str]] = []  # (file_path, error_msg)

        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0

        # Batch operations support
        self._batch_manager = None
        self._enable_batching = True
        self._batch_operations: list[dict] = []

    def enable_batch_operations(self, enabled: bool = True) -> None:
        """Enable or disable batch operations optimization."""
        self._enable_batching = enabled
        logger.debug(
            f"[ParallelHashWorker] Batch operations {'enabled' if enabled else 'disabled'}"
        )

    def setup_duplicate_scan(self, file_paths: list[str]) -> None:
        """Configure worker for duplicate detection."""
        with QMutexLocker(self._mutex):
            self._operation_type = "duplicates"
            self._file_paths = list(file_paths)
            self._external_folder = None
            self._reset_state()

    def setup_external_comparison(self, file_paths: list[str], external_folder: str) -> None:
        """Configure worker for external folder comparison."""
        with QMutexLocker(self._mutex):
            self._operation_type = "compare"
            self._file_paths = list(file_paths)
            self._external_folder = external_folder
            self._reset_state()

    def setup_checksum_calculation(self, file_paths: list[str]) -> None:
        """Configure worker for checksum calculation."""
        with QMutexLocker(self._mutex):
            self._operation_type = "checksums"
            self._file_paths = list(file_paths)
            self._external_folder = None
            self._reset_state()

    def set_total_size(self, total_size: int) -> None:
        """Set total size from external calculation."""
        with QMutexLocker(self._mutex):
            self._total_bytes = total_size
            logger.debug(f"[ParallelHashWorker] Total size set to: {total_size:,} bytes")

    def cancel(self) -> None:
        """Cancel the current operation."""
        with QMutexLocker(self._mutex):
            self._cancelled = True
            logger.debug("[ParallelHashWorker] Cancellation requested")

    def is_cancelled(self) -> bool:
        """Check if operation is cancelled."""
        with QMutexLocker(self._mutex):
            return self._cancelled

    def _reset_state(self) -> None:
        """Reset internal state for new operation (must be called with mutex locked)."""
        self._cancelled = False
        self._total_files = len(self._file_paths)
        self._completed_files = 0
        self._total_bytes = 0
        self._cumulative_processed_bytes = 0
        self._results = {}
        self._errors = []
        self._cache_hits = 0
        self._cache_misses = 0
        self._batch_operations = []

    def _calculate_total_size(self, file_paths: list[str]) -> int:
        """Calculate total size of all files for progress tracking."""
        total_size = 0
        files_counted = 0

        self.status_updated.emit("Calculating total file size...")

        for i, file_path in enumerate(file_paths):
            if self.is_cancelled():
                logger.debug("[ParallelHashWorker] Size calculation cancelled")
                return 0

            try:
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    total_size += size
                    files_counted += 1

                    if i % 50 == 0:  # Update every 50 files
                        progress = int((i / len(file_paths)) * 100)
                        self.status_updated.emit(
                            f"Calculating total size... {progress}% ({i}/{len(file_paths)})"
                        )

            except (OSError, PermissionError) as e:
                logger.debug(f"[ParallelHashWorker] Could not get size for {file_path}: {e}")
                continue

        logger.info(
            f"[ParallelHashWorker] Total size: {total_size:,} bytes for {files_counted} files"
        )
        return total_size

    def _process_single_file(self, file_path: str) -> tuple[str, str | None, int]:
        """
        Process a single file in worker thread (called concurrently).

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
            logger.debug(f"[ParallelHashWorker] Cache hit: {filename}")
            return (file_path, hash_value, file_size)

        # Cache miss - calculate hash
        with QMutexLocker(self._mutex):
            self._cache_misses += 1

        logger.debug(f"[ParallelHashWorker] Calculating hash: {filename}")

        try:
            hash_value = self._hash_manager.calculate_hash(file_path)

            if hash_value is not None:
                # Store hash (will use batch if enabled)
                self._store_hash_optimized(file_path, hash_value, "crc32")

            return (file_path, hash_value, file_size)

        except Exception as e:
            logger.warning(f"[ParallelHashWorker] Error processing {filename}: {e}")
            with QMutexLocker(self._mutex):
                self._errors.append((file_path, str(e)))
            return (file_path, None, file_size)

    def _store_hash_optimized(
        self, file_path: str, hash_value: str, algorithm: str = "crc32"
    ) -> None:
        """Store hash using batch operations if available (thread-safe)."""
        # NOTE: We do NOT store directly to DB here because this runs in a worker thread
        # and the HashManager/DB connection belongs to the main thread.
        # Instead, we rely on the file_hash_calculated signal to pass the hash
        # back to the main thread for storage.

        # We still queue for batch operations because batch manager might handle
        # thread safety or we might flush later from main thread.
        with QMutexLocker(self._mutex):
            if self._enable_batching and self._batch_manager:
                logger.debug(
                    f"[ParallelHashWorker] Queuing hash for batch: {os.path.basename(file_path)}"
                )
                self._batch_manager.queue_hash_store(
                    file_path=file_path,
                    hash_value=hash_value,
                    algorithm=algorithm,
                    priority=10,
                )
                self._batch_operations.append(
                    {"path": file_path, "hash": hash_value, "algorithm": algorithm}
                )

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
                    from oncutf.core.batch_operations_manager import get_batch_manager
                    self._batch_manager = get_batch_manager(self.main_window)
                    logger.debug("[ParallelHashWorker] Batch manager initialized")
                except Exception as e:
                    logger.warning(f"[ParallelHashWorker] Failed to init batch manager: {e}")
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
            elif operation_type == "compare":
                self._compare_external_parallel(file_paths, external_folder)
            elif operation_type == "checksums":
                self._calculate_checksums_parallel(file_paths)

        except Exception as e:
            logger.exception(f"[ParallelHashWorker] Unexpected error: {e}")
            self.error_occurred.emit(str(e))
            self.finished_processing.emit(False)
        finally:
            # Flush batch operations
            if self._enable_batching and self._batch_manager and self._batch_operations:
                logger.info(
                    f"[ParallelHashWorker] Flushing {len(self._batch_operations)} batched ops"
                )
                try:
                    flushed = self._batch_manager.flush_batch_type("hash_store")
                    logger.info(f"[ParallelHashWorker] Flushed {flushed} hash operations")

                    stats = self._batch_manager.get_stats()
                    logger.info(
                        f"[ParallelHashWorker] Batch stats: {stats.batched_operations} batched, "
                        f"avg: {stats.average_batch_size:.1f}, saved: {stats.total_time_saved:.2f}s"
                    )
                except Exception as e:
                    logger.error(f"[ParallelHashWorker] Error flushing batches: {e}")

    def _calculate_checksums_parallel(self, file_paths: list[str]) -> None:
        """Calculate checksums using parallel workers."""
        hash_results = {}
        total_files = len(file_paths)

        self.status_updated.emit("Calculating CRC32 checksums (parallel)...")

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(self._process_single_file, path): path
                for path in file_paths
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_path):
                if self.is_cancelled():
                    # Cancel remaining tasks
                    executor.shutdown(wait=False, cancel_futures=True)

                    if hash_results:
                        logger.info(
                            f"[ParallelHashWorker] Cancelled - showing {len(hash_results)} results"
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
                    logger.warning(f"[ParallelHashWorker] Task failed: {e}")

        # Report completion
        self.progress_updated.emit(total_files, total_files, "Complete")
        self.size_progress.emit(int(self._total_bytes), int(self._total_bytes))

        # Cache statistics
        cache_hit_rate = (
            (self._cache_hits / (self._cache_hits + self._cache_misses) * 100)
            if (self._cache_hits + self._cache_misses) > 0
            else 0
        )

        batch_info = (
            f", batch ops: {len(self._batch_operations)}" if self._batch_operations else ""
        )

        self.status_updated.emit(
            f"CRC32 checksums calculated for {len(hash_results)} files! "
            f"Cache hit rate: {cache_hit_rate:.1f}%{batch_info}"
        )

        logger.info(
            f"[ParallelHashWorker] Completed {len(hash_results)} files "
            f"(hits: {self._cache_hits}, misses: {self._cache_misses}, "
            f"rate: {cache_hit_rate:.1f}%)"
        )

        self.checksums_calculated.emit(hash_results)
        self.finished_processing.emit(True)

    def _find_duplicates_parallel(self, file_paths: list[str]) -> None:
        """Find duplicates using parallel hash calculation."""
        hash_to_files: dict[str, list[str]] = {}
        len(file_paths)

        self.status_updated.emit("Scanning for duplicates (parallel)...")

        # Calculate all hashes in parallel
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_path = {
                executor.submit(self._process_single_file, path): path
                for path in file_paths
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
                    logger.warning(f"[ParallelHashWorker] Duplicate scan task failed: {e}")

        # Filter to only duplicates (hash with multiple files)
        duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}

        logger.info(f"[ParallelHashWorker] Found {len(duplicates)} duplicate groups")

        self.duplicates_found.emit(duplicates)
        self.finished_processing.emit(True)

    def _compare_external_parallel(self, file_paths: list[str], external_folder: str) -> None:
        """Compare files with external folder using parallel processing."""
        comparison_results = {}
        external_path = Path(external_folder)

        self.status_updated.emit("Comparing files (parallel)...")

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
        def process_pair(pair: tuple[str, str | None]) -> tuple[str, dict]:
            source_path, external_path = pair

            if external_path is None:
                return (source_path, {"exists_in_external": False})

            # Calculate both hashes
            source_hash = self._hash_manager.calculate_hash(source_path)
            external_hash = self._hash_manager.calculate_hash(external_path)

            return (source_path, {
                "exists_in_external": True,
                "source_hash": source_hash,
                "external_hash": external_hash,
                "is_same": source_hash == external_hash if source_hash and external_hash else False
            })

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_pair = {
                executor.submit(process_pair, pair): pair
                for pair in file_pairs
            }

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
                    logger.warning(f"[ParallelHashWorker] Comparison task failed: {e}")

        logger.info(f"[ParallelHashWorker] Compared {len(comparison_results)} files")

        self.comparison_result.emit(comparison_results)
        self.finished_processing.emit(True)
