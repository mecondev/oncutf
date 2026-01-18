"""Module: thumbnail_manager.py

Author: Michael Economou
Date: 2026-01-16

Thumbnail generation orchestrator with background worker coordination.

Provides:
- ThumbnailRequest: Data class for thumbnail generation requests
- ThumbnailManager: Orchestrator for thumbnail lifecycle

Workflow:
1. UI requests thumbnail via get_thumbnail(file_path, size)
2. Manager checks cache (memory -> disk -> DB)
3. If miss, queue for background generation
4. Worker generates thumbnail asynchronously
5. Manager emits thumbnail_ready signal to UI
6. Placeholder returned immediately, real thumbnail arrives via signal

Thread Safety:
- Queue operations are thread-safe (queue.Queue)
- Cache operations protected by internal locks
- Signal emission safe from worker threads
"""

from __future__ import annotations

import os
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from oncutf.core.pyqt_imports import QObject, QPixmap, pyqtSignal
from oncutf.core.thumbnail.thumbnail_cache import ThumbnailCache, ThumbnailCacheConfig
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.paths import AppPaths

if TYPE_CHECKING:
    from oncutf.core.database.thumbnail_store import ThumbnailStore
    from oncutf.core.thumbnail.thumbnail_worker import ThumbnailWorker

logger = get_cached_logger(__name__)


@dataclass
class ThumbnailRequest:
    """Thumbnail generation request.

    Attributes:
        file_path: Absolute path to source file
        folder_path: Parent folder for order tracking
        size_px: Requested thumbnail size (square dimension)
        priority: Higher values processed first (0=normal, 1=high)

    """

    file_path: str
    folder_path: str
    size_px: int = 128
    priority: int = 0


class ThumbnailManager(QObject):
    """Orchestrator for thumbnail generation and caching.

    Manages thumbnail lifecycle:
    - Cache lookup (memory + disk + DB)
    - Queue management for background generation
    - Worker coordination
    - Progress reporting

    Signals:
        thumbnail_ready: Emitted when thumbnail is generated/loaded (file_path, pixmap)
        generation_progress: Emitted periodically (completed, total)
        generation_error: Emitted on thumbnail generation failure (file_path, error_msg)

    Usage:
        manager = ThumbnailManager(db_store)
        manager.thumbnail_ready.connect(on_thumbnail_ready)
        pixmap = manager.get_thumbnail("/path/to/file.jpg", size_px=128)
        # Returns placeholder immediately, emits thumbnail_ready when ready

    """

    # Signals
    thumbnail_ready = pyqtSignal(str, QPixmap)  # file_path, pixmap
    generation_progress = pyqtSignal(int, int)  # completed, total
    generation_error = pyqtSignal(str, str)  # file_path, error_message

    def __init__(
        self,
        db_store: ThumbnailStore,
        cache_config: ThumbnailCacheConfig | None = None,
        max_workers: int = 2,
    ):
        """Initialize thumbnail manager.

        Args:
            db_store: Database store for cache index
            cache_config: Cache configuration (uses default if None)
            max_workers: Number of worker threads for generation

        """
        super().__init__()

        self._db_store = db_store

        # Initialize cache
        if cache_config is None:
            cache_config = ThumbnailCacheConfig(
                cache_dir=AppPaths.get_thumbnails_dir(),
                memory_cache_limit=500,
                thumbnail_size=128,
            )
        self._cache = ThumbnailCache(cache_config)

        # Request queue (thread-safe)
        self._request_queue: queue.Queue[ThumbnailRequest] = queue.Queue()

        # Track pending requests to avoid duplicates
        self._pending_requests: set[str] = set()
        self._pending_lock = threading.Lock()

        # Track files that failed thumbnail generation (to avoid retrying)
        self._failed_files: set[str] = set()

        # Worker threads
        self._workers: list[ThumbnailWorker] = []
        self._max_workers = max_workers
        self._shutdown_flag = False

        # Statistics
        self._total_requests = 0
        self._completed_requests = 0

        # Placeholder pixmap (lazily initialized when needed)
        self._placeholder: QPixmap | None = None

        logger.info(
            "ThumbnailManager initialized with %d workers, cache at %s",
            max_workers,
            cache_config.cache_dir,
        )

    def get_thumbnail(self, file_path: str, size_px: int = 128) -> QPixmap:
        """Get thumbnail for file (from cache or queue for generation).

        Args:
            file_path: Absolute path to source file
            size_px: Requested thumbnail size (square dimension)

        Returns:
            QPixmap: Cached thumbnail if available, placeholder otherwise.
                     Emits thumbnail_ready signal when real thumbnail is ready.

        Note:
            This method returns immediately. If thumbnail is not cached,
            a placeholder is returned and the real thumbnail arrives via
            the thumbnail_ready signal.

        """
        # Validate file exists
        logger.debug("[ThumbnailManager] get_thumbnail() called: %s (size=%d)", file_path, size_px)
        if not os.path.exists(file_path):
            logger.warning("[ThumbnailManager] File not found for thumbnail: %s", file_path)
            return self._get_placeholder()

        # Check cache first
        cached = self._check_cache(file_path, size_px)
        if cached:
            logger.debug("[ThumbnailManager] Cache hit: %s", file_path)
            return cached

        # Queue for generation
        logger.debug("[ThumbnailManager] Cache miss, queuing: %s", file_path)
        self._queue_request(file_path, size_px)
        logger.debug("[ThumbnailManager] Returning placeholder for: %s", file_path)

        return self._get_placeholder()

    def _check_cache(self, file_path: str, size_px: int) -> QPixmap | None:
        """Check cache for existing thumbnail.

        Args:
            file_path: Absolute path to source file
            size_px: Requested thumbnail size

        Returns:
            QPixmap if cached, None otherwise

        """
        try:
            # Get file stats for cache key
            stat = os.stat(file_path)
            mtime = stat.st_mtime
            size = stat.st_size

            # Check cache
            cached_pixmap = self._cache.get(file_path, mtime, size)
            if cached_pixmap:
                return cached_pixmap

            # Check DB for cache entry
            db_entry = self._db_store.get_cached_entry(file_path, mtime)
            if db_entry:
                # Load from disk cache
                cache_filename = db_entry["cache_filename"]
                cache_path = self._cache._config.cache_dir / cache_filename
                if cache_path.exists():
                    pixmap = QPixmap(str(cache_path))
                    if not pixmap.isNull():
                        # Store in memory cache
                        self._cache.put(file_path, mtime, size, pixmap)
                        return pixmap

        except (OSError, ValueError) as e:
            logger.warning("Error checking cache for %s: %s", file_path, e)

        return None

    def _queue_request(self, file_path: str, size_px: int) -> None:
        """Queue thumbnail generation request.

        Args:
            file_path: Absolute path to source file
            size_px: Requested thumbnail size

        """
        # Check if already pending or previously failed (avoid duplicate requests)
        with self._pending_lock:
            if file_path in self._pending_requests:
                logger.debug("[ThumbnailManager] Request already pending for: %s", file_path)
                return
            if file_path in self._failed_files:
                # Don't retry failed files until files are reloaded
                return
            self._pending_requests.add(file_path)

        logger.debug("[ThumbnailManager] _queue_request() called for: %s", file_path)
        folder_path = str(Path(file_path).parent)
        request = ThumbnailRequest(
            file_path=file_path, folder_path=folder_path, size_px=size_px
        )

        self._request_queue.put(request)
        self._total_requests += 1
        logger.debug("[ThumbnailManager] Request queued (queue size: %d, total requests: %d)", self._request_queue.qsize(), self._total_requests)

        # Start workers if not running
        self._ensure_workers_running()

    def _ensure_workers_running(self) -> None:
        """Start worker threads if not already running."""
        # Clean up dead workers
        initial_count = len(self._workers)
        self._workers = [w for w in self._workers if w.isRunning()]
        if len(self._workers) < initial_count:
            logger.debug("[ThumbnailManager] Cleaned up %d dead workers", initial_count - len(self._workers))

        # Start new workers if needed
        logger.debug("[ThumbnailManager] Current workers: %d, max: %d", len(self._workers), self._max_workers)
        while len(self._workers) < self._max_workers and not self._shutdown_flag:
            from oncutf.core.thumbnail.thumbnail_worker import ThumbnailWorker

            worker = ThumbnailWorker(
                request_queue=self._request_queue,
                cache=self._cache,
                db_store=self._db_store,
            )

            # Connect signals
            worker.thumbnail_ready.connect(self._on_worker_thumbnail_ready)
            worker.generation_error.connect(self._on_worker_error)
            worker.finished.connect(
                lambda w=worker: self._on_worker_finished(w)
            )  # Bind worker in closure

            worker.start()
            self._workers.append(worker)

            logger.debug("Started worker thread (total: %d)", len(self._workers))

    def _on_worker_thumbnail_ready(self, file_path: str, pixmap: QPixmap) -> None:
        """Handle thumbnail ready signal from worker.

        Args:
            file_path: Source file path
            pixmap: Generated thumbnail

        """
        logger.debug("[ThumbnailManager] _on_worker_thumbnail_ready() called: %s (valid=%s)", file_path, not pixmap.isNull())
        self._completed_requests += 1

        # Remove from pending set
        with self._pending_lock:
            self._pending_requests.discard(file_path)

        # Emit progress
        if self._total_requests > 0:
            self.generation_progress.emit(
                self._completed_requests, self._total_requests
            )

        # Forward to UI
        logger.debug("[ThumbnailManager] Emitting thumbnail_ready signal for: %s", file_path)
        self.thumbnail_ready.emit(file_path, pixmap)

        logger.debug(
            "[ThumbnailManager] Thumbnail ready: %s (progress: %d/%d)",
            file_path,
            self._completed_requests,
            self._total_requests,
        )

    def _on_worker_error(self, file_path: str, error_msg: str) -> None:
        """Handle generation error from worker.

        Args:
            file_path: Source file path
            error_msg: Error message

        """
        self._completed_requests += 1

        # Remove from pending set and add to failed set
        with self._pending_lock:
            self._pending_requests.discard(file_path)
            self._failed_files.add(file_path)

        self.generation_error.emit(file_path, error_msg)

        logger.warning("Thumbnail generation error for %s: %s", file_path, error_msg)

    def _on_worker_finished(self, worker: ThumbnailWorker) -> None:
        """Handle worker thread finish.

        Args:
            worker: Finished worker

        """
        if worker in self._workers:
            self._workers.remove(worker)
            logger.debug("Worker thread finished (remaining: %d)", len(self._workers))

    def _get_placeholder(self) -> QPixmap:
        """Get placeholder pixmap, creating it if needed.

        Returns:
            QPixmap with "Loading..." text

        """
        if self._placeholder is None:
            self._placeholder = self._create_placeholder()
        return self._placeholder

    def _create_placeholder(self) -> QPixmap:
        """Create placeholder pixmap for loading state.

        Returns:
            QPixmap with "Loading..." text

        """
        # Create simple 128x128 gray pixmap
        from oncutf.core.pyqt_imports import QColor, QPainter, Qt

        pixmap = QPixmap(128, 128)
        pixmap.fill(QColor(200, 200, 200))

        painter = QPainter(pixmap)
        painter.setPen(QColor(100, 100, 100))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Loading...")
        painter.end()

        return pixmap

    def invalidate_cache(self, file_path: str) -> None:
        """Invalidate cached thumbnail for file.

        Args:
            file_path: Absolute path to source file

        """
        try:
            stat = os.stat(file_path)
            self._cache.invalidate(file_path, stat.st_mtime, stat.st_size)
            self._db_store.invalidate_entry(file_path)
            logger.debug("Invalidated cache for: %s", file_path)
        except OSError as e:
            logger.warning("Error invalidating cache for %s: %s", file_path, e)

    def clear_cache(self) -> None:
        """Clear all cached thumbnails (memory + disk + DB)."""
        self._cache.clear()
        # Note: DB cleanup handled by ThumbnailStore.cleanup_orphaned_entries()
        logger.info("Cache cleared")

    def clear_pending_requests(self) -> None:
        """Clear all pending thumbnail requests from the queue.

        Call this when files are removed from the model to prevent
        'file not found' warnings from stale requests.
        Also clears the failed files set to allow retry on next load.
        """
        cleared_count = 0
        while not self._request_queue.empty():
            try:
                self._request_queue.get_nowait()
                self._request_queue.task_done()
                cleared_count += 1
            except Exception:
                break

        # Clear pending and failed sets
        with self._pending_lock:
            pending_count = len(self._pending_requests)
            failed_count = len(self._failed_files)
            self._pending_requests.clear()
            self._failed_files.clear()

        if cleared_count > 0 or pending_count > 0 or failed_count > 0:
            logger.debug(
                "Cleared %d queued, %d pending, %d failed thumbnail requests",
                cleared_count,
                pending_count,
                failed_count,
            )

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            dict with keys: memory_entries, disk_entries, total_requests, completed_requests

        """
        db_stats = self._db_store.get_cache_stats()
        return {
            "memory_entries": len(self._cache._memory_cache._cache),
            "disk_entries": db_stats["total_entries"],
            "total_requests": self._total_requests,
            "completed_requests": self._completed_requests,
            "queue_size": self._request_queue.qsize(),
            "active_workers": len(self._workers),
        }

    def shutdown(self) -> None:
        """Shutdown manager and stop all workers."""
        logger.info("Shutting down ThumbnailManager...")
        self._shutdown_flag = True

        # Stop all workers
        for worker in self._workers:
            worker.request_stop()

        # Wait for workers to finish (with timeout)
        for worker in self._workers:
            if not worker.wait(2000):  # 2 second timeout
                # Worker didn't finish in time, terminate it
                logger.warning("ThumbnailWorker did not stop in time, terminating")
                worker.terminate()
                worker.wait(500)  # Brief wait after terminate

        self._workers.clear()

        # Cleanup any orphan ffmpeg processes
        self._cleanup_ffmpeg_processes()

        logger.info("ThumbnailManager shutdown complete")

    def _cleanup_ffmpeg_processes(self) -> None:
        """Kill any orphan ffmpeg processes started by this application."""
        try:
            from oncutf.core.thumbnail.providers import VideoThumbnailProvider

            VideoThumbnailProvider.force_cleanup_all_ffmpeg_processes(
                max_scan_s=0.5,
                graceful_wait_s=0.5,
            )
        except Exception as e:
            logger.debug("Error cleaning up ffmpeg processes: %s", e)
