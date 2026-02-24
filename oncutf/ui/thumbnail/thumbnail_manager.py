"""Module: thumbnail_manager.py.

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

import contextlib
import os
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QPixmap

from oncutf.ui.thumbnail.thumbnail_cache import ThumbnailCache, ThumbnailCacheConfig
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.paths import AppPaths

if TYPE_CHECKING:
    from oncutf.infra.db.thumbnail_store import ThumbnailStore
    from oncutf.ui.thumbnail.thumbnail_worker import ThumbnailWorker

logger = get_cached_logger(__name__)


@dataclass(order=False)
class ThumbnailRequest:
    """Thumbnail generation request.

    Attributes:
        file_path: Absolute path to source file
        folder_path: Parent folder for order tracking
        size_px: Requested thumbnail size (square dimension)
        priority: Higher values processed first (larger = higher)
        _counter: Internal counter for FIFO tiebreaking (auto-assigned)

    Priority Queue Behavior:
        - Higher priority values are processed first
        - Same priority: FIFO order (lower counter first)
        - Visible viewport items: priority=high
        - Background loading: priority=low

    """

    file_path: str
    folder_path: str
    size_px: int = 128
    priority: int = 0
    _counter: int = 0  # Auto-assigned for FIFO ordering
    is_sentinel: bool = False  # True for shutdown sentinel items (do not process)

    # Class variable for counter (shared across all instances)
    _global_counter: int = 0

    def __post_init__(self) -> None:
        """Assign unique counter for FIFO tiebreaking."""
        # Use class variable to ensure uniqueness
        ThumbnailRequest._global_counter += 1
        object.__setattr__(self, "_counter", ThumbnailRequest._global_counter)

    def __lt__(self, other: object) -> bool:
        """Compare requests for priority queue sorting.

        Args:
            other: Another ThumbnailRequest

        Returns:
            True if self has higher priority than other

        Priority Rules:
            1. Higher priority value wins (reversed for max-heap)
            2. Same priority: lower counter wins (FIFO)

        """
        if not isinstance(other, ThumbnailRequest):
            return NotImplemented
        # Higher priority first (reverse comparison for max-heap behavior)
        if self.priority != other.priority:
            return self.priority > other.priority
        # Same priority: FIFO order (lower counter = earlier request)
        return self._counter < other._counter


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

    Placeholder behavior:
        get_thumbnail() returns a null QPixmap() when the thumbnail is not yet ready.
        The delegate treats a null pixmap as "loading" state and renders a skeleton shimmer.
        When the real thumbnail is ready, thumbnail_ready signal is emitted.

    Usage:
        manager = ThumbnailManager(db_store)
        manager.thumbnail_ready.connect(on_thumbnail_ready)
        pixmap = manager.get_thumbnail("/path/to/file.jpg", size_px=128)
        # Returns null QPixmap immediately, emits thumbnail_ready when ready

    """

    # Extensions that support thumbnail generation.
    # Files with other extensions go to permanent "no preview" state in the delegate.
    PREVIEWABLE_EXTENSIONS: frozenset[str] = frozenset(
        {
            # Raster images
            "jpg",
            "jpeg",
            "png",
            "gif",
            "bmp",
            "tiff",
            "tif",
            "webp",
            "heic",
            "heif",
            # RAW camera formats
            "raw",
            "cr2",
            "cr3",
            "nef",
            "arw",
            "dng",
            "orf",
            "raf",
            "rw2",
            "pef",
            "nrw",
            "srw",
            "dcr",
            "fff",
            # Video (ffmpeg-based, future support)
            "mp4",
            "mov",
            "avi",
            "mkv",
            "wmv",
            "m4v",
            "flv",
            "webm",
            "m2ts",
            "ts",
            "mts",
            "3gp",
            "ogv",
        }
    )

    # Signals
    thumbnail_ready = pyqtSignal(str, QPixmap)  # file_path, pixmap
    generation_progress = pyqtSignal(int, int)  # completed, total
    generation_error = pyqtSignal(str, str)  # file_path, error_message

    @staticmethod
    def _calculate_worker_count() -> int:
        """Calculate optimal worker count based on CPU cores.

        Returns:
            Number of workers (min 2, max 8)

        """
        cpu_count = os.cpu_count() or 2
        # Use half of available cores, capped between 2-8
        return max(2, min(8, cpu_count // 2))

    def __init__(
        self,
        db_store: ThumbnailStore,
        cache_config: ThumbnailCacheConfig | None = None,
        max_workers: int | None = None,
    ):
        """Initialize thumbnail manager.

        Args:
            db_store: Database store for cache index
            cache_config: Cache configuration (uses default if None)
            max_workers: Number of worker threads (auto-calculated if None)

        """
        super().__init__()

        self._db_store = db_store

        # Calculate optimal worker count if not specified
        if max_workers is None:
            max_workers = self._calculate_worker_count()

        # Initialize cache
        if cache_config is None:
            cache_config = ThumbnailCacheConfig(
                cache_dir=AppPaths.get_thumbnails_dir(),
                memory_cache_limit=500,
                thumbnail_size=128,
            )
        self._cache = ThumbnailCache(cache_config)

        # Request queue (thread-safe priority queue)
        # Items sorted by: (higher priority first, then FIFO order)
        self._request_queue: queue.PriorityQueue[ThumbnailRequest] = queue.PriorityQueue()

        # Track pending requests with highest priority
        self._pending_requests: dict[str, int] = {}
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

        logger.info(
            "ThumbnailManager initialized with %d workers, cache at %s",
            max_workers,
            cache_config.cache_dir,
        )

    @property
    def max_workers(self) -> int:
        """Get maximum worker count.

        Returns:
            Maximum number of worker threads

        """
        return self._max_workers

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
        logger.debug(
            "[ThumbnailManager] get_thumbnail() called: %s (size=%d)",
            file_path,
            size_px,
        )
        if not Path(file_path).exists():
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

    def _check_cache(self, file_path: str, _size_px: int) -> QPixmap | None:
        """Check cache for existing thumbnail.

        Args:
            file_path: Absolute path to source file
            _size_px: Requested thumbnail size (unused - cache uses normalized path)

        Returns:
            QPixmap if cached, None otherwise

        """
        try:
            # Get file stats for cache key
            stat = Path(file_path).stat()
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

    def _queue_request(self, file_path: str, size_px: int, priority: int = 0) -> None:
        """Queue thumbnail generation request.

        Args:
            file_path: Absolute path to source file
            size_px: Requested thumbnail size
            priority: Priority for request (larger = higher)

        """
        # Check if already pending or previously failed (avoid duplicate requests)
        with self._pending_lock:
            if file_path in self._pending_requests:
                existing_priority = self._pending_requests[file_path]
                if priority <= existing_priority:
                    logger.debug(
                        "[ThumbnailManager] Request already pending for: %s",
                        file_path,
                    )
                    return
                self._pending_requests[file_path] = priority
            if file_path in self._failed_files:
                # Don't retry failed files until files are reloaded
                return
            if file_path not in self._pending_requests:
                self._pending_requests[file_path] = priority

        logger.debug("[ThumbnailManager] _queue_request() called for: %s", file_path)
        folder_path = str(Path(file_path).parent)
        request = ThumbnailRequest(
            file_path=file_path,
            folder_path=folder_path,
            size_px=size_px,
            priority=priority,
        )

        self._request_queue.put(request)
        self._total_requests += 1
        logger.debug(
            "[ThumbnailManager] Request queued (queue size: %d, total requests: %d)",
            self._request_queue.qsize(),
            self._total_requests,
        )

        # Start workers if not running
        self._ensure_workers_running()

    def _ensure_workers_running(self) -> None:
        """Start worker threads if not already running."""
        # Clean up dead workers
        initial_count = len(self._workers)
        self._workers = [w for w in self._workers if w.isRunning()]
        if len(self._workers) < initial_count:
            logger.debug(
                "[ThumbnailManager] Cleaned up %d dead workers",
                initial_count - len(self._workers),
            )

        # Start new workers if needed
        logger.debug(
            "[ThumbnailManager] Current workers: %d, max: %d",
            len(self._workers),
            self._max_workers,
        )
        while len(self._workers) < self._max_workers and not self._shutdown_flag:
            from oncutf.ui.thumbnail.thumbnail_worker import ThumbnailWorker

            worker = ThumbnailWorker(
                request_queue=self._request_queue,
                cache=self._cache,
                db_store=self._db_store,
                pending_requests=self._pending_requests,
                pending_lock=self._pending_lock,
                parent=self,  # Pass parent for proper Qt cleanup
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
        logger.debug(
            "[ThumbnailManager] _on_worker_thumbnail_ready() called: %s (valid=%s)",
            file_path,
            not pixmap.isNull(),
        )
        self._completed_requests += 1

        # Remove from pending map
        with self._pending_lock:
            self._pending_requests.pop(file_path, None)

        # Emit progress
        if self._total_requests > 0:
            self.generation_progress.emit(self._completed_requests, self._total_requests)

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

        # Remove from pending map and add to failed set
        with self._pending_lock:
            self._pending_requests.pop(file_path, None)
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
        """Return a null QPixmap signalling 'not yet ready'.

        The delegate interprets a null pixmap as "loading" and renders
        a skeleton shimmer. This avoids storing a gray placeholder in the
        memory/disk cache.

        Returns:
            Null QPixmap (isNull() == True)

        """
        return QPixmap()

    def is_previewable(self, file_path: str) -> bool:
        """Return True if the file extension supports thumbnail generation.

        Files not in PREVIEWABLE_EXTENSIONS will show a permanent file-type
        silhouette placeholder in the delegate instead of a loading skeleton.

        Args:
            file_path: Absolute path to the file

        Returns:
            True if a thumbnail can be generated for this file extension

        """
        ext = Path(file_path).suffix.lstrip(".").lower()
        return ext in self.PREVIEWABLE_EXTENSIONS

    def invalidate_cache(self, file_path: str) -> None:
        """Invalidate cached thumbnail for file.

        Args:
            file_path: Absolute path to source file

        """
        try:
            stat = Path(file_path).stat()
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

    def queue_all_thumbnails(
        self, file_paths: list[str], priority: int = 0, size_px: int = 128
    ) -> int:
        """Queue all file paths for thumbnail generation (background loading).

        This is the bulk loading API for loading all thumbnails when files are loaded.
        Use lower priority for background loading and higher for visible viewport items.

        Args:
            file_paths: List of absolute file paths to generate thumbnails for
            priority: Priority for all requests (larger = higher)
            size_px: Requested thumbnail size (square dimension)

        Returns:
            Number of items actually queued (0 if all cached or already pending).

        Note:
            - Only queues files that are not already cached or pending with higher priority
            - Use higher priority for visible viewport items (processed first)
            - Use lower priority for background loading (processed after visible)
            - Workers are started automatically if not running

        """
        queued_count = 0
        cached_count = 0
        with self._pending_lock:
            for file_path in file_paths:
                # Skip failed requests until reload
                if file_path in self._failed_files:
                    continue

                existing_priority = self._pending_requests.get(file_path)
                if existing_priority is not None and priority <= existing_priority:
                    continue

                # Skip if file doesn't exist
                if not Path(file_path).exists():
                    continue

                # Check if already cached (fast check without loading)
                try:
                    stat = Path(file_path).stat()
                    if self._cache.get(file_path, stat.st_mtime, stat.st_size):
                        cached_count += 1
                        continue
                except OSError:
                    continue  # Skip files with stat errors

                # Queue for generation
                folder_path = str(Path(file_path).parent)
                request = ThumbnailRequest(
                    file_path=file_path, folder_path=folder_path, size_px=size_px, priority=priority
                )
                self._request_queue.put(request)
                self._pending_requests[file_path] = priority
                self._total_requests += 1
                queued_count += 1

        # Update progress counters.
        # ACCUMULATE rather than replace -- multiple callers (initial queue,
        # scroll prioritize, view-switch) may invoke this method in the same
        # session.  Replacing counters causes the status bar to jump / reset.
        if queued_count > 0:
            # _total_requests was already incremented inside the loop above
            # (one +=1 per queued item), so it is already correct.
            # Emit progress so the UI shows the right starting point.
            self.generation_progress.emit(self._completed_requests, self._total_requests)
        elif cached_count > 0:
            # Everything cached, nothing to generate -- emit a "complete"
            # progress signal so the UI updates correctly without resetting
            # any in-flight counters from an earlier session.
            total = max(self._total_requests, cached_count)
            completed = max(self._completed_requests, cached_count)
            self.generation_progress.emit(completed, total)

        # Start workers if not running (after counters initialization to avoid
        # overwriting progress from worker-complete callbacks).
        if queued_count > 0:
            self._ensure_workers_running()
            logger.info(
                "Queued %d thumbnails (priority=%d, cached=%d, total_pending=%d)",
                queued_count,
                priority,
                cached_count,
                self._request_queue.qsize(),
            )

        return queued_count

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

        # Reset progress counters so each new load session starts from zero
        self._total_requests = 0
        self._completed_requests = 0

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

    def set_worker_count(self, count: int) -> None:
        """Dynamically adjust worker thread count for priority management.

        Used by hybrid loading system to scale workers based on viewport visibility:
        - HIGH priority (viewport visible): max_workers
        - BACKGROUND priority (viewport hidden): max_workers // 4 (min 1)
        - PAUSED (timeout reached): 0 workers

        Args:
            count: Number of workers (0 to pause, 1-max_workers for scaling)

        """
        import time

        t0 = time.time()

        if count < 0 or count > self._max_workers:
            logger.warning(
                "[ThumbnailManager] Invalid worker count %d (valid: 0-%d), ignoring",
                count,
                self._max_workers,
            )
            return

        current_count = len(self._workers)
        if current_count == count:
            return  # Already at target

        logger.info("[ThumbnailManager] Adjusting worker count: %d -> %d", current_count, count)

        if count == 0:
            # Pause all workers (stop and remove them)
            for worker in self._workers:
                worker.request_stop()
            for worker in self._workers:
                if worker.isRunning():
                    # Reduced timeout from 1000ms to 100ms for faster viewport switching
                    worker.wait(100)  # Wait up to 100ms for graceful stop (Windows optimization)
            self._workers.clear()
            logger.debug(
                "[ThumbnailManager] All workers stopped (paused) in %.3fms",
                (time.time() - t0) * 1000,
            )

        elif count > current_count:
            # Scale up: start additional workers
            workers_to_add = count - current_count
            for _ in range(workers_to_add):
                from oncutf.ui.thumbnail.thumbnail_worker import ThumbnailWorker

                worker = ThumbnailWorker(
                    request_queue=self._request_queue,
                    cache=self._cache,
                    db_store=self._db_store,
                    pending_requests=self._pending_requests,
                    pending_lock=self._pending_lock,
                    parent=self,
                )
                worker.thumbnail_ready.connect(self._on_worker_thumbnail_ready)
                worker.generation_error.connect(self._on_worker_error)
                worker.finished.connect(lambda w=worker: self._on_worker_finished(w))
                worker.start()
                self._workers.append(worker)
            logger.debug(
                "[ThumbnailManager] Scaled up: added %d workers (now %d active) in %.3fms",
                workers_to_add,
                len(self._workers),
                (time.time() - t0) * 1000,
            )

        else:
            # Scale down: stop excess workers
            workers_to_remove = current_count - count
            for _ in range(workers_to_remove):
                if self._workers:
                    worker = self._workers.pop()
                    worker.request_stop()
                    if worker.isRunning():
                        # Reduced timeout from 1000ms to 100ms for faster viewport switching
                        worker.wait(
                            100
                        )  # Wait up to 100ms for graceful stop (Windows optimization)
            logger.debug(
                "[ThumbnailManager] Scaled down: removed %d workers (now %d active) in %.3fms",
                workers_to_remove,
                len(self._workers),
                (time.time() - t0) * 1000,
            )

    def shutdown(self) -> None:
        """Shutdown manager and stop all workers gracefully.

        Shutdown order is critical to avoid 'QThread: Destroyed while thread is
        still running' crashes:
          1. Signal workers to stop.
          2. Kill active ffmpeg/ffprobe subprocesses -- this is the main blocker.
          3. Put sentinel items in queue to unblock any worker waiting in queue.get.
          4. Wait for each worker to exit.  After terminate(), wait() has NO timeout
             so we never call self._workers.clear() while a thread is alive.
        """
        logger.info("Shutting down ThumbnailManager...")
        self._shutdown_flag = True

        # Step 1: signal all workers to stop their loop.
        for worker in self._workers:
            worker.request_stop()

        # Step 2: kill active ffmpeg/ffprobe subprocesses FIRST.
        # Workers blocked inside VideoThumbnailProvider.generate() (subprocess.run)
        # will not check _stop_requested until the subprocess returns.  Killing them
        # here unblocks those workers immediately.
        self._cleanup_ffmpeg_processes()

        # Step 3: put one sentinel per worker into the queue so that workers
        # currently blocked on queue.get(timeout=0.5) wake up right away.
        sentinel = ThumbnailRequest(file_path="", folder_path="", is_sentinel=True)
        for _ in self._workers:
            with contextlib.suppress(Exception):
                self._request_queue.put_nowait(sentinel)

        # Step 4: wait for each worker; disconnect signals first to avoid callbacks
        # during teardown, then wait properly -- we MUST NOT destroy a QThread while
        # its OS thread is still alive or Qt will abort().
        for worker in self._workers:
            try:
                worker.thumbnail_ready.disconnect()
                worker.generation_error.disconnect()
            except (TypeError, RuntimeError):
                pass  # Already disconnected

            if not worker.isRunning():
                continue

            # Fast path: with ffmpeg killed workers should finish within ~1s.
            if not worker.wait(2000):
                logger.warning("ThumbnailWorker still running after 2s, forcing terminate")
                worker.terminate()
                # Must wait indefinitely -- never leave a thread running when we
                # clear _workers, or Qt will abort with 'Destroyed while running'.
                worker.wait()

        # Safe to release list only after all threads have actually stopped.
        self._workers.clear()

        logger.info("ThumbnailManager shutdown complete")

    def _cleanup_ffmpeg_processes(self) -> None:
        """Kill any orphan ffmpeg processes started by this application."""
        try:
            from oncutf.utils.process_cleanup import force_cleanup_ffmpeg_processes

            force_cleanup_ffmpeg_processes(
                max_scan_s=0.5,
                graceful_wait_s=0.5,
            )
        except Exception as e:
            logger.debug("Error cleaning up ffmpeg processes: %s", e)
