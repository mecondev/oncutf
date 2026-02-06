"""Module: thumbnail_worker.py.

Author: Michael Economou
Date: 2026-01-16

Background worker thread for thumbnail generation.

Provides:
- ThumbnailWorker: QThread-based worker for asynchronous thumbnail generation

Workflow:
1. Worker pulls requests from shared queue
2. Determines appropriate provider (image vs video)
3. Generates thumbnail using provider
4. Saves to disk cache + updates DB
5. Emits thumbnail_ready signal to manager
6. Batch progress updates (every 10 items)

Thread Safety:
- Queue operations are thread-safe (queue.Queue)
- Provider operations are stateless (safe)
- Signal emission thread-safe via Qt event system
"""

from __future__ import annotations

import os
import queue
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

from oncutf.ui.thumbnail.providers import (
    ImageThumbnailProvider,
    ThumbnailGenerationError,
    VideoThumbnailProvider,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.infra.db.thumbnail_store import ThumbnailStore
    from oncutf.ui.thumbnail.thumbnail_cache import ThumbnailCache
    from oncutf.ui.thumbnail.thumbnail_manager import ThumbnailRequest

logger = get_cached_logger(__name__)


class ThumbnailWorker(QThread):
    """Background worker for thumbnail generation.

    Processes queued thumbnail requests in background thread:
    - Pulls requests from shared queue
    - Generates thumbnails using appropriate provider
    - Saves to cache and DB
    - Emits signals for UI updates

    Signals:
        thumbnail_ready: Emitted when thumbnail generated (file_path, pixmap)
        generation_error: Emitted on generation failure (file_path, error_msg)

    """

    # Signals
    thumbnail_ready = pyqtSignal(str, QPixmap)  # file_path, pixmap
    generation_error = pyqtSignal(str, str)  # file_path, error_message

    def __init__(
        self,
        request_queue: queue.Queue[ThumbnailRequest],
        cache: ThumbnailCache,
        db_store: ThumbnailStore,
        parent: QObject | None = None,
    ):
        """Initialize worker.

        Args:
            request_queue: Shared queue of thumbnail requests
            cache: Thumbnail cache for storage
            db_store: Database store for cache index
            parent: Parent QObject for proper cleanup

        """
        super().__init__(parent)

        self._request_queue = request_queue
        self._cache = cache
        self._db_store = db_store

        # Providers (reused for efficiency)
        self._image_provider = ImageThumbnailProvider()
        self._video_provider = VideoThumbnailProvider()

        # Control flags
        self._stop_requested = False
        self._processed_count = 0

        # File type detection
        self._image_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".tiff",
            ".tif",
            ".webp",
            ".heic",
            ".heif",
            # RAW formats (supported via rawpy)
            ".cr2",
            ".cr3",
            ".nef",
            ".orf",
            ".rw2",
            ".arw",
            ".dng",
            ".raf",
            ".pef",
            ".srw",
        }
        self._video_extensions = {
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".mts",
            ".m2ts",
            ".mxf",
        }

    def run(self) -> None:
        """Main worker loop - process requests until stopped."""
        logger.debug("ThumbnailWorker started")

        while not self._stop_requested:
            try:
                # Get request with timeout (allows checking stop flag)
                request = self._request_queue.get(timeout=0.5)
            except queue.Empty:
                # No requests, check stop flag and retry
                continue

            # Process request
            self._process_request(request)

            # Mark task done
            self._request_queue.task_done()

        logger.debug("ThumbnailWorker stopped (processed: %d)", self._processed_count)

        # Ensure thread is properly terminated
        self.quit()

    def _process_request(self, request: ThumbnailRequest) -> None:
        """Process single thumbnail request.

        Args:
            request: Thumbnail generation request

        """
        # Check if stop requested before processing
        if self._stop_requested:
            return

        file_path = request.file_path
        size_px = request.size_px

        def _raise_file_not_found() -> None:
            raise ThumbnailGenerationError(f"File not found: {file_path}")

        def _raise_unsupported_type() -> None:
            raise ThumbnailGenerationError(f"Unsupported file type: {ext} for {file_path}")

        def _raise_null_pixmap() -> None:
            raise ThumbnailGenerationError(f"Generated null pixmap for {file_path}")

        try:
            # Validate file exists
            if not Path(file_path).exists():
                _raise_file_not_found()

            # Get file stats
            file_stat = Path(file_path).stat()
            mtime = file_stat.st_mtime
            size = file_stat.st_size

            # Determine file type and select provider
            ext = Path(file_path).suffix.lower()
            provider: ImageThumbnailProvider | VideoThumbnailProvider
            if ext in self._image_extensions:
                provider = self._image_provider
                video_frame_time = None
            elif ext in self._video_extensions:
                provider = self._video_provider
                video_frame_time = None  # Will be set by provider
            else:
                _raise_unsupported_type()

            # Check again before expensive operation
            if self._stop_requested:
                logger.debug("Skipping thumbnail generation (shutdown): %s", file_path)
                return

            # Generate thumbnail
            logger.debug("Generating thumbnail: %s (size: %d)", file_path, size_px)
            pixmap = provider.generate(file_path)

            # Check if stopped during generation
            if self._stop_requested:
                logger.debug("Discarding thumbnail (shutdown): %s", file_path)
                return

            if pixmap.isNull():
                _raise_null_pixmap()

            # Save to disk cache
            cache_filename = self._cache.generate_cache_key(file_path, mtime, size)
            cache_path = self._cache._config.cache_dir / f"{cache_filename}.png"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            pixmap.save(str(cache_path), "PNG")

            # Update memory cache
            self._cache.put(file_path, mtime, size, pixmap)

            # Update DB
            # For video, extract frame time if available (provider-specific)
            if ext in self._video_extensions and hasattr(provider, "last_frame_time"):
                video_frame_time = getattr(provider, "last_frame_time", None)

            folder_path = str(Path(file_path).parent)
            self._db_store.save_cache_entry(
                folder_path=folder_path,
                file_path=file_path,
                file_mtime=mtime,
                file_size=size,
                cache_filename=f"{cache_filename}.png",
                video_frame_time=video_frame_time,
            )

            # Emit success signal
            self.thumbnail_ready.emit(file_path, pixmap)

            self._processed_count += 1
            logger.debug("Thumbnail generated successfully: %s", file_path)

        except ThumbnailGenerationError as e:
            # Expected errors (unsupported formats, corrupted files, etc.)
            # Logged as warning in manager when signal is received
            logger.debug("Thumbnail generation failed for %s: %s", file_path, e)
            self.generation_error.emit(file_path, str(e))

        except Exception as e:
            # Unexpected errors - log as exception here for debugging
            logger.exception("Unexpected error generating thumbnail for %s", file_path)
            self.generation_error.emit(file_path, f"Unexpected error: {e}")

    def request_stop(self) -> None:
        """Request worker to stop processing."""
        self._stop_requested = True
        logger.debug("Stop requested for ThumbnailWorker")
