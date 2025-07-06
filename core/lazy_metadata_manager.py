"""
Module: lazy_metadata_manager.py

Author: Michael Economou
Date: 2025-07-06

core/lazy_metadata_manager.py
Lazy Metadata Manager for intelligent on-demand metadata loading.
Implements smart prefetching, background loading, and memory optimization.
Features:
- On-demand metadata loading only when needed
- Smart prefetching based on user selection patterns
- Background metadata loading for visible files
- LRU cache management for memory optimization
- Viewport-aware loading priorities
"""
import logging
from typing import Optional, List, Dict, Set, Any, Tuple
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QThread
from PyQt5.QtWidgets import QAbstractItemView

from models.file_item import FileItem
from utils.metadata_cache_helper import MetadataCacheHelper
from utils.timer_manager import schedule_metadata_load
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class LoadingRequest:
    """Represents a metadata loading request with priority and timing."""
    file_item: FileItem
    use_extended: bool
    priority: int  # 0=highest, 100=lowest
    requested_at: datetime
    source: str
    viewport_visible: bool = False


@dataclass
class LoadingStats:
    """Statistics for lazy loading performance monitoring."""
    total_requests: int = 0
    cache_hits: int = 0
    background_loads: int = 0
    on_demand_loads: int = 0
    prefetch_loads: int = 0
    average_load_time: float = 0.0


class LazyMetadataManager(QObject):
    """
    Intelligent lazy metadata loading manager.

    Manages on-demand metadata loading with smart prefetching and background processing.
    Optimizes memory usage and loading performance based on user interaction patterns.
    Uses a shared ExifTool instance for better performance.
    """

    # Signals
    metadata_loaded = pyqtSignal(str, dict)  # file_path, metadata
    loading_started = pyqtSignal(str)  # file_path
    cache_updated = pyqtSignal()

    def __init__(self, parent_window=None):
        super().__init__(parent_window)
        self.parent_window = parent_window

        # Cache management
        self._cache_helper: Optional[MetadataCacheHelper] = None
        self._memory_cache: OrderedDict[str, dict] = OrderedDict()  # LRU cache
        self._max_memory_cache_size = 50  # Maximum files in memory cache

        # Loading queue and management
        self._loading_queue: Dict[str, LoadingRequest] = {}
        self._currently_loading: set = set()
        self._loading_stats = LoadingStats()

        # Timers and background processing
        self._background_timer = QTimer()
        self._background_timer.timeout.connect(self._process_background_queue)
        self._background_timer.setSingleShot(False)
        self._background_timer.setInterval(100)  # Check every 100ms

        self._prefetch_timer = QTimer()
        self._prefetch_timer.timeout.connect(self._process_prefetch_requests)
        self._prefetch_timer.setSingleShot(True)
        self._prefetch_timer.setInterval(500)  # Check every 500ms

        # User interaction tracking
        self._last_selection_time = datetime.now()
        self._selection_pattern: List[str] = []  # Track recent selections for pattern detection
        self._viewport_visible_files: Set[str] = set()

        # Configuration
        self._enable_background_loading = True
        self._enable_smart_prefetching = True
        self._max_queue_size = 100
        self._prefetch_radius = 3  # Files around selection to prefetch

        # Shared ExifTool instance for better performance
        self._shared_exiftool = None
        self._exiftool_lock = None

        logger.info("[LazyMetadataManager] Initialized with shared ExifTool support")

    def _get_shared_exiftool(self):
        """Get or create the shared ExifTool instance."""
        if self._shared_exiftool is None:
            from utils.exiftool_wrapper import ExifToolWrapper
            import threading

            self._shared_exiftool = ExifToolWrapper()
            self._exiftool_lock = threading.Lock()
            logger.info("[LazyMetadataManager] Created shared ExifTool instance")

        return self._shared_exiftool

    def initialize_cache_helper(self) -> None:
        """Initialize the cache helper if parent window is available."""
        if self.parent_window and hasattr(self.parent_window, 'metadata_cache'):
            self._cache_helper = MetadataCacheHelper(self.parent_window.metadata_cache)
            logger.debug("[LazyMetadataManager] Cache helper initialized")

    def request_metadata(
        self,
        file_item: FileItem,
        use_extended: bool = False,
        priority: int = 50,
        source: str = "user_request",
        force_reload: bool = False
    ) -> Optional[dict]:
        """
        Request metadata for a file with intelligent caching and loading.

        Args:
            file_item: The file to load metadata for
            use_extended: Whether to use extended metadata extraction
            priority: Loading priority (0=highest, 100=lowest)
            source: Source of the request for analytics
            force_reload: Force reload even if cached

        Returns:
            Metadata dict if immediately available, None if loading in background
        """
        file_path = file_item.full_path

        # Check memory cache first
        if not force_reload and file_path in self._memory_cache:
            self._loading_stats.cache_hits += 1
            logger.debug(f"[LazyMetadataManager] Memory cache hit for {file_item.filename}")
            return self._memory_cache[file_path]

        # Check persistent cache
        if not force_reload and self._cache_helper:
            cached_metadata = self._cache_helper.get_metadata_for_file(file_item)
            if cached_metadata:
                # Add to memory cache
                self._add_to_memory_cache(file_path, cached_metadata)
                self._loading_stats.cache_hits += 1
                logger.debug(f"[LazyMetadataManager] Persistent cache hit for {file_item.filename}")
                return cached_metadata

        # Queue for background loading
        self._queue_loading_request(file_item, use_extended, priority, source)

        # Start background processing if not already running
        if not self._background_timer.isActive():
            self._background_timer.start()

        return None

    def request_metadata_for_viewport(self, visible_files: List[FileItem]) -> None:
        """
        Request metadata for files visible in the viewport.

        This method prioritizes loading metadata for files that are currently visible
        to the user, improving perceived performance.
        """
        if not self._enable_background_loading:
            return

        # Update viewport tracking
        self._viewport_visible_files = {f.full_path for f in visible_files}

        # Queue visible files with high priority
        for file_item in visible_files:
            if file_item.full_path not in self._currently_loading:
                self._queue_loading_request(
                    file_item,
                    use_extended=False,  # Use fast loading for viewport
                    priority=10,  # High priority
                    source="viewport",
                    viewport_visible=True
                )

        # Start background processing
        if not self._background_timer.isActive():
            self._background_timer.start()

        logger.debug(f"[LazyMetadataManager] Queued {len(visible_files)} viewport files for loading")

    def request_smart_prefetch(self, selected_file: FileItem, file_list: List[FileItem]) -> None:
        """
        Request smart prefetching based on selection patterns.

        Args:
            selected_file: Currently selected file
            file_list: List of all files in the current view
        """
        if not self._enable_smart_prefetching:
            return

        # Update selection pattern
        self._update_selection_pattern(selected_file.full_path)

        # Find files around the selected file
        try:
            current_index = file_list.index(selected_file)
            start_index = max(0, current_index - self._prefetch_radius)
            end_index = min(len(file_list), current_index + self._prefetch_radius + 1)

            prefetch_files = file_list[start_index:end_index]

            for file_item in prefetch_files:
                if file_item.full_path in self._memory_cache:
                    continue

                # Queue with lower priority for prefetch
                self._queue_loading_request(
                    file_item,
                    use_extended=False,
                    priority=70,  # Lower priority
                    source="prefetch"
                )

            # Start prefetch processing
            if not self._prefetch_timer.isActive():
                self._prefetch_timer.start()

            logger.debug(f"[LazyMetadataManager] Queued {len(prefetch_files)} files for prefetch")

        except ValueError:
            logger.warning(f"[LazyMetadataManager] Selected file not found in file list: {selected_file.filename}")

    def _queue_loading_request(
        self,
        file_item: FileItem,
        use_extended: bool,
        priority: int,
        source: str,
        viewport_visible: bool = False
    ) -> None:
        """Queue a loading request with priority management."""
        file_path = file_item.full_path

        # Skip if already loading
        if file_path in self._currently_loading:
            return

        # Manage queue size
        if len(self._loading_queue) >= self._max_queue_size:
            self._remove_lowest_priority_request()

        # Create request
        request = LoadingRequest(
            file_item=file_item,
            use_extended=use_extended,
            priority=priority,
            requested_at=datetime.now(),
            source=source,
            viewport_visible=viewport_visible
        )

        # Add to queue (replace if exists with higher priority)
        if file_path in self._loading_queue:
            existing_request = self._loading_queue[file_path]
            if priority < existing_request.priority:  # Lower number = higher priority
                self._loading_queue[file_path] = request
        else:
            self._loading_queue[file_path] = request

        self._loading_stats.total_requests += 1
        logger.debug(f"[LazyMetadataManager] Queued {source} request for {file_item.filename} (priority: {priority})")

    def _process_background_queue(self) -> None:
        """Process the loading queue in background."""
        if not self._loading_queue or len(self._currently_loading) >= 2:  # Limit concurrent loads
            return

        # Get highest priority request
        request = self._get_highest_priority_request()
        if not request:
            self._background_timer.stop()
            return

        # Start loading
        self._start_loading(request)

    def _process_prefetch_requests(self) -> None:
        """Process prefetch requests with lower priority."""
        prefetch_requests = [
            req for req in self._loading_queue.values()
            if req.source == "prefetch" and req.file_item.full_path not in self._currently_loading
        ]

        # Process up to 2 prefetch requests
        for i, request in enumerate(prefetch_requests[:2]):
            self._start_loading(request)

    def _start_loading(self, request: LoadingRequest) -> None:
        """Start loading metadata for a request."""
        file_path = request.file_item.full_path

        # Mark as currently loading
        self._currently_loading.add(file_path)
        self._loading_queue.pop(file_path, None)

        # Emit signal
        self.loading_started.emit(file_path)

        # Start actual loading in background thread
        self._load_metadata_async(request)

        # Update stats
        if request.source == "viewport":
            self._loading_stats.background_loads += 1
        elif request.source == "prefetch":
            self._loading_stats.prefetch_loads += 1
        else:
            self._loading_stats.on_demand_loads += 1

    def _load_metadata_async(self, request: LoadingRequest) -> None:
        """Load metadata asynchronously using shared ExifTool."""
        def load_and_emit():
            try:
                start_time = datetime.now()

                # Use shared ExifTool instance with thread safety
                shared_exiftool = self._get_shared_exiftool()

                with self._exiftool_lock:
                    metadata = shared_exiftool.get_metadata(
                        request.file_item.full_path,
                        request.use_extended
                    )

                if metadata:
                    # Cache the result
                    self._add_to_memory_cache(request.file_item.full_path, metadata)

                    if self._cache_helper:
                        self._cache_helper.set_metadata_for_file(
                            request.file_item,
                            metadata,
                            request.use_extended
                        )

                    # Update file item
                    request.file_item.metadata = metadata
                    request.file_item.metadata_status = "loaded"

                    # Emit success signal
                    self.metadata_loaded.emit(request.file_item.full_path, metadata)

                    # Update loading time stats
                    load_time = (datetime.now() - start_time).total_seconds()
                    self._update_loading_stats(load_time)

                    logger.debug(f"[LazyMetadataManager] Loaded metadata for {request.file_item.filename} in {load_time:.2f}s")

            except Exception as e:
                logger.error(f"[LazyMetadataManager] Error loading metadata for {request.file_item.filename}: {e}")

            finally:
                # Remove from currently loading
                self._currently_loading.discard(request.file_item.full_path)

        # Schedule the loading
        schedule_metadata_load(load_and_emit, 10)

    def _add_to_memory_cache(self, file_path: str, metadata: dict) -> None:
        """Add metadata to memory cache with LRU management."""
        # Remove if already exists (to update position)
        if file_path in self._memory_cache:
            del self._memory_cache[file_path]

        # Add to end (most recently used)
        self._memory_cache[file_path] = metadata

        # Trim cache if too large
        while len(self._memory_cache) > self._max_memory_cache_size:
            self._memory_cache.popitem(last=False)  # Remove least recently used

    def _get_highest_priority_request(self) -> Optional[LoadingRequest]:
        """Get the highest priority request from the queue."""
        if not self._loading_queue:
            return None

        # Sort by priority (lower number = higher priority)
        sorted_requests = sorted(
            self._loading_queue.values(),
            key=lambda r: (r.priority, r.requested_at)
        )

        return sorted_requests[0]

    def _remove_lowest_priority_request(self) -> None:
        """Remove the lowest priority request from the queue."""
        if not self._loading_queue:
            return

        # Find lowest priority (highest number)
        lowest_priority_path = max(
            self._loading_queue.keys(),
            key=lambda path: self._loading_queue[path].priority
        )

        del self._loading_queue[lowest_priority_path]

    def _update_selection_pattern(self, file_path: str) -> None:
        """Update selection pattern for smart prefetching."""
        self._selection_pattern.append(file_path)

        # Keep only recent selections (last 10)
        if len(self._selection_pattern) > 10:
            self._selection_pattern = self._selection_pattern[-10:]

        self._last_selection_time = datetime.now()

    def _update_loading_stats(self, load_time: float) -> None:
        """Update loading time statistics."""
        if self._loading_stats.average_load_time == 0:
            self._loading_stats.average_load_time = load_time
        else:
            # Moving average
            self._loading_stats.average_load_time = (
                self._loading_stats.average_load_time * 0.8 + load_time * 0.2
            )

    def get_loading_stats(self) -> LoadingStats:
        """Get current loading statistics."""
        return self._loading_stats

    def clear_cache(self) -> None:
        """Clear memory cache."""
        self._memory_cache.clear()
        logger.info("[LazyMetadataManager] Memory cache cleared")

    def set_config(
        self,
        enable_background: bool = None,
        enable_prefetching: bool = None,
        max_cache_size: int = None,
        prefetch_radius: int = None
    ) -> None:
        """Configure lazy loading behavior."""
        if enable_background is not None:
            self._enable_background_loading = enable_background

        if enable_prefetching is not None:
            self._enable_smart_prefetching = enable_prefetching

        if max_cache_size is not None:
            self._max_memory_cache_size = max_cache_size
            # Trim cache if needed
            while len(self._memory_cache) > self._max_memory_cache_size:
                self._memory_cache.popitem(last=False)

        if prefetch_radius is not None:
            self._prefetch_radius = prefetch_radius

        logger.info(f"[LazyMetadataManager] Configuration updated: bg={self._enable_background_loading}, prefetch={self._enable_smart_prefetching}")

    def cleanup(self) -> None:
        """Clean up resources and stop background processing."""
        logger.info("[LazyMetadataManager] Starting cleanup...")

        # Stop timers
        if hasattr(self, '_background_timer'):
            self._background_timer.stop()
        if hasattr(self, '_prefetch_timer'):
            self._prefetch_timer.stop()

        # Clear queues
        self._loading_queue.clear()
        self._currently_loading.clear()

        # Clear memory cache
        self._memory_cache.clear()

        # Close shared ExifTool instance
        if self._shared_exiftool:
            try:
                self._shared_exiftool.close()
                logger.info("[LazyMetadataManager] Shared ExifTool closed")
            except Exception as e:
                logger.warning(f"[LazyMetadataManager] Error closing shared ExifTool: {e}")
            finally:
                self._shared_exiftool = None
                self._exiftool_lock = None

        logger.info("[LazyMetadataManager] Cleanup completed")
