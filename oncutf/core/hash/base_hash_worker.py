"""Module: base_hash_worker.py.

Author: Michael Economou
Date: 2026-01-19

Base class for hash calculation workers.

Provides common infrastructure for both sequential and parallel hash workers:
- Qt signals for progress, status, and results
- Thread-safe cancellation support
- Operation setup methods
- Progress tracking state management
- Batch operations support

Subclasses must implement:
- run(): Main thread execution logic
- _calculate_checksums_impl(): Checksum calculation
- _find_duplicates_impl(): Duplicate detection
- _compare_external_impl(): External folder comparison
"""

from abc import ABCMeta, abstractmethod
from typing import Any

from PyQt5 import sip

from oncutf.core.pyqt_imports import QMutex, QMutexLocker, QThread, pyqtSignal
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


# Create combined metaclass to resolve QThread (sip.wrappertype) + ABC (ABCMeta) conflict
class QThreadABCMeta(sip.wrappertype, ABCMeta):
    """Combined metaclass for QThread and ABC compatibility."""


class BaseHashWorker(QThread, metaclass=QThreadABCMeta):
    """Abstract base class for hash calculation workers.

    Provides common signals, state management, and setup methods.
    Subclasses implement specific execution strategies (sequential vs parallel).
    """

    # =========================================================================
    # Signals (Common to all hash workers)
    # =========================================================================

    # Progress signals
    progress_updated = pyqtSignal(int, int, str)  # current_file, total_files, current_filename
    size_progress = pyqtSignal("qint64", "qint64")  # bytes_processed, total_bytes
    status_updated = pyqtSignal(str)  # status message

    # Result signals
    duplicates_found = pyqtSignal(dict)  # {hash: [file_paths]}
    comparison_result = pyqtSignal(dict)  # comparison results
    checksums_calculated = pyqtSignal(dict)  # {file_path: hash}

    # Control signals
    finished_processing = pyqtSignal(bool)  # success flag
    error_occurred = pyqtSignal(str)  # error message
    file_hash_calculated = pyqtSignal(str, str)  # file_path, hash_value

    # =========================================================================
    # Initialization
    # =========================================================================

    def __init__(self, parent: Any = None) -> None:
        """Initialize base hash worker.

        Args:
            parent: Parent QObject (usually main window)

        """
        super().__init__(parent)

        # Thread safety
        self._mutex = QMutex()
        self._cancelled = False

        # Parent reference
        self.main_window = parent

        # Hash manager (lazy-initialized by subclasses)
        self._hash_manager: Any = None

        # Operation configuration
        self._operation_type: str | None = None  # "duplicates", "compare", "checksums"
        self._file_paths: list[str] = []
        self._external_folder: str | None = None  # for comparison

        # Progress tracking
        self._total_bytes = 0

        # Batch operations support
        self._batch_manager: Any = None
        self._enable_batching = True
        self._batch_operations: list[dict[str, Any]] = []

    # =========================================================================
    # Configuration Methods (Common)
    # =========================================================================

    def enable_batch_operations(self, enabled: bool = True) -> None:
        """Enable or disable batch operations optimization."""
        self._enable_batching = enabled
        batch_state = "enabled" if enabled else "disabled"
        logger.debug(
            "[%s] Batch operations %s",
            self.__class__.__name__,
            batch_state,
        )

    def setup_duplicate_scan(self, file_paths: list[str]) -> None:
        """Configure worker for duplicate detection."""
        with QMutexLocker(self._mutex):
            self._operation_type = "duplicates"
            self._file_paths = list(file_paths)
            self._external_folder = None

    def setup_external_comparison(self, file_paths: list[str], external_folder: str) -> None:
        """Configure worker for external folder comparison."""
        with QMutexLocker(self._mutex):
            self._operation_type = "compare"
            self._file_paths = list(file_paths)
            self._external_folder = external_folder

    def setup_checksum_calculation(self, file_paths: list[str]) -> None:
        """Configure worker for checksum calculation."""
        with QMutexLocker(self._mutex):
            self._operation_type = "checksums"
            self._file_paths = list(file_paths)
            self._external_folder = None

    def set_total_size(self, total_size: int) -> None:
        """Set total size from external calculation."""
        with QMutexLocker(self._mutex):
            self._total_bytes = total_size
            logger.debug("[%s] Total size set to: %d bytes", self.__class__.__name__, total_size)

    # =========================================================================
    # Cancellation (Common)
    # =========================================================================

    def cancel(self) -> None:
        """Cancel the current operation."""
        with QMutexLocker(self._mutex):
            self._cancelled = True
            logger.debug("[%s] Cancellation requested", self.__class__.__name__)

    def is_cancelled(self) -> bool:
        """Check if operation is cancelled."""
        with QMutexLocker(self._mutex):
            return self._cancelled

    # =========================================================================
    # Helper Methods (Common)
    # =========================================================================

    def _calculate_total_size(self, file_paths: list[str]) -> int:
        """Calculate total size of all files for progress tracking.

        Args:
            file_paths: List of file paths

        Returns:
            Total size in bytes

        """
        import os

        total_size = 0
        files_counted = 0

        self.status_updated.emit("Calculating total file size...")

        for i, file_path in enumerate(file_paths):
            if self.is_cancelled():
                logger.debug("[%s] Size calculation cancelled", self.__class__.__name__)
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
                logger.debug(
                    "[%s] Could not get size for %s: %s", self.__class__.__name__, file_path, e
                )
                continue

        logger.info(
            "[%s] Total size: %s bytes for %d files",
            self.__class__.__name__,
            format(total_size, ","),
            files_counted,
        )
        return total_size

    def _store_hash_optimized(
        self, file_path: str, hash_value: str, algorithm: str = "crc32"
    ) -> None:
        """Store hash using batch operations if available (thread-safe).

        Note: In multi-threaded workers, this queues for later batch flush
        from main thread to avoid DB thread-safety issues.

        Falls back to direct storage via hash manager if batching is not available.
        """
        import os

        with QMutexLocker(self._mutex):
            if self._enable_batching and self._batch_manager:
                logger.debug(
                    "[%s] Queuing hash for batch: %s",
                    self.__class__.__name__,
                    os.path.basename(file_path),
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
            elif self._hash_manager:
                # Fallback to direct storage
                logger.debug(
                    "[%s] Storing hash directly: %s",
                    self.__class__.__name__,
                    os.path.basename(file_path),
                )
                self._hash_manager.store_hash(file_path, hash_value, algorithm)

    # =========================================================================
    # Abstract Methods (Must be implemented by subclasses)
    # =========================================================================

    @abstractmethod
    def run(self) -> None:
        """Main thread execution logic.

        Must be implemented by subclasses to provide sequential or parallel execution.
        """
        ...
