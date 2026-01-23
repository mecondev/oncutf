"""Module: thumbnail_cache.py.

Author: Michael Economou
Date: 2026-01-16

Thumbnail caching system with disk persistence and LRU memory cache.

Provides:
- ThumbnailCacheConfig: Configuration for cache behavior
- ThumbnailMemoryCache: LRU in-memory cache for fast access
- ThumbnailDiskCache: Persistent disk storage for thumbnails
- ThumbnailCache: Orchestrator combining both layers

Cache Strategy:
1. Check memory cache (LRU, 500 entries max)
2. If miss, check disk cache
3. If miss, return None (caller generates thumbnail)
4. On generation, save to disk + memory

File Identity:
- Cache key: hash(file_path + mtime + size)
- Ensures invalidation on file modification
"""

import hashlib
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from oncutf.core.pyqt_imports import QPixmap
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.paths import AppPaths

logger = get_cached_logger(__name__)


@dataclass
class ThumbnailCacheConfig:
    """Configuration for thumbnail cache behavior.

    Attributes:
        cache_dir: Directory for disk cache storage
        memory_cache_limit: Maximum entries in LRU memory cache
        thumbnail_size: Default thumbnail size in pixels (width/height)
        disk_cache_enabled: Enable disk cache (vs memory-only)

    """

    cache_dir: Path
    memory_cache_limit: int = 500
    thumbnail_size: int = 128
    disk_cache_enabled: bool = True

    @classmethod
    def default(cls) -> "ThumbnailCacheConfig":
        """Create default configuration using app paths.

        Returns:
            ThumbnailCacheConfig with default settings

        """
        cache_dir = AppPaths.get_thumbnails_dir()
        return cls(cache_dir=cache_dir)


class ThumbnailMemoryCache:
    """LRU memory cache for thumbnails.

    Thread-safe LRU cache using OrderedDict. When limit is reached,
    evicts least recently used entries.

    Attributes:
        _cache: OrderedDict storing file_path -> QPixmap
        _max_size: Maximum entries before LRU eviction
        _lock: Thread safety lock

    """

    def __init__(self, max_size: int = 500):
        """Initialize memory cache with size limit.

        Args:
            max_size: Maximum entries before LRU eviction

        """
        self._cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()
        logger.debug("[ThumbnailMemoryCache] Initialized with max_size=%d", max_size)

    def get(self, cache_key: str) -> QPixmap | None:
        """Retrieve thumbnail from memory cache.

        Args:
            cache_key: Unique identifier for cached thumbnail

        Returns:
            QPixmap if found, None otherwise

        """
        with self._lock:
            if cache_key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(cache_key)
                logger.debug("[ThumbnailMemoryCache] Cache HIT for key: %s", cache_key[:16])
                return self._cache[cache_key]
            logger.debug("[ThumbnailMemoryCache] Cache MISS for key: %s", cache_key[:16])
            return None

    def put(self, cache_key: str, pixmap: QPixmap) -> None:
        """Store thumbnail in memory cache with LRU eviction.

        Args:
            cache_key: Unique identifier for thumbnail
            pixmap: Thumbnail image to cache

        """
        with self._lock:
            # Remove if already exists (to update position)
            if cache_key in self._cache:
                del self._cache[cache_key]

            # Add to end (most recently used)
            self._cache[cache_key] = pixmap

            # Evict oldest if over limit
            if len(self._cache) > self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(
                    "[ThumbnailMemoryCache] Evicted oldest entry: %s (size: %d/%d)",
                    oldest_key[:16],
                    len(self._cache),
                    self._max_size,
                )

            logger.debug(
                "[ThumbnailMemoryCache] Stored key: %s (size: %d/%d)",
                cache_key[:16],
                len(self._cache),
                self._max_size,
            )

    def clear(self) -> None:
        """Clear all entries from memory cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("[ThumbnailMemoryCache] Cleared %d entries", count)

    def size(self) -> int:
        """Get current number of cached entries.

        Returns:
            Number of entries in cache

        """
        with self._lock:
            return len(self._cache)


class ThumbnailDiskCache:
    """Persistent disk storage for thumbnail images.

    Stores thumbnails as PNG files in cache directory.
    File naming: {cache_key}.png

    Attributes:
        _cache_dir: Directory for thumbnail storage
        _lock: Thread safety lock

    """

    def __init__(self, cache_dir: Path):
        """Initialize disk cache with directory.

        Args:
            cache_dir: Directory for thumbnail storage

        """
        self._cache_dir = cache_dir
        self._lock = threading.RLock()

        # Create cache directory if not exists
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("[ThumbnailDiskCache] Initialized at: %s", self._cache_dir)

    def get(self, cache_key: str) -> QPixmap | None:
        """Load thumbnail from disk cache.

        Args:
            cache_key: Unique identifier for cached thumbnail

        Returns:
            QPixmap if file exists and loads successfully, None otherwise

        """
        cache_path = self._cache_dir / f"{cache_key}.png"

        if not cache_path.exists():
            logger.debug("[ThumbnailDiskCache] Cache MISS (no file): %s", cache_key[:16])
            return None

        try:
            pixmap = QPixmap(str(cache_path))
            if pixmap.isNull():
                logger.warning("[ThumbnailDiskCache] Failed to load pixmap: %s", cache_path)
                return None

            logger.debug("[ThumbnailDiskCache] Cache HIT: %s", cache_key[:16])
            return pixmap

        except Exception as e:
            logger.warning("[ThumbnailDiskCache] Error loading thumbnail: %s - %s", cache_path, e)
            return None

    def put(self, cache_key: str, pixmap: QPixmap) -> bool:
        """Save thumbnail to disk cache.

        Args:
            cache_key: Unique identifier for thumbnail
            pixmap: Thumbnail image to save

        Returns:
            True if save successful, False otherwise

        """
        cache_path = self._cache_dir / f"{cache_key}.png"

        try:
            success = pixmap.save(str(cache_path), "PNG")
            if success:
                logger.debug("[ThumbnailDiskCache] Saved: %s", cache_key[:16])
            else:
                logger.warning("[ThumbnailDiskCache] Failed to save: %s", cache_key[:16])
            return success

        except Exception as e:
            logger.error("[ThumbnailDiskCache] Error saving thumbnail: %s - %s", cache_path, e)
            return False

    def remove(self, cache_key: str) -> bool:
        """Remove thumbnail from disk cache.

        Args:
            cache_key: Unique identifier for cached thumbnail

        Returns:
            True if removed, False if not found or error

        """
        cache_path = self._cache_dir / f"{cache_key}.png"

        if not cache_path.exists():
            return False

        try:
            cache_path.unlink()
            logger.debug("[ThumbnailDiskCache] Removed: %s", cache_key[:16])
            return True

        except Exception as e:
            logger.warning("[ThumbnailDiskCache] Error removing thumbnail: %s - %s", cache_path, e)
            return False

    def clear(self) -> int:
        """Clear all thumbnails from disk cache.

        Returns:
            Number of files removed

        """
        count = 0
        try:
            for cache_file in self._cache_dir.glob("*.png"):
                cache_file.unlink()
                count += 1
            logger.info("[ThumbnailDiskCache] Cleared %d files", count)
        except Exception as e:
            logger.error("[ThumbnailDiskCache] Error clearing cache: %s", e)

        return count


class ThumbnailCache:
    """Orchestrator for thumbnail caching with memory and disk layers.

    Cache Strategy:
    1. Check memory cache (fast, limited size)
    2. If miss, check disk cache (slower, persistent)
    3. If miss, return None (caller generates)
    4. On put: save to both memory and disk

    Attributes:
        _config: Cache configuration
        _memory_cache: LRU memory cache
        _disk_cache: Persistent disk cache

    """

    def __init__(self, config: ThumbnailCacheConfig | None = None):
        """Initialize thumbnail cache with configuration.

        Args:
            config: Cache configuration (uses default if None)

        """
        self._config = config or ThumbnailCacheConfig.default()
        self._memory_cache = ThumbnailMemoryCache(max_size=self._config.memory_cache_limit)
        self._disk_cache = (
            ThumbnailDiskCache(self._config.cache_dir) if self._config.disk_cache_enabled else None
        )

        logger.info(
            "[ThumbnailCache] Initialized - memory_limit=%d, disk_enabled=%s, cache_dir=%s",
            self._config.memory_cache_limit,
            self._config.disk_cache_enabled,
            self._config.cache_dir if self._disk_cache else "N/A",
        )

    @staticmethod
    def generate_cache_key(file_path: str, mtime: float, file_size: int) -> str:
        """Generate unique cache key from file identity.

        Cache key ensures invalidation when file is modified.

        Args:
            file_path: Absolute file path
            mtime: File modification time (timestamp)
            file_size: File size in bytes

        Returns:
            SHA256 hash string (hex)

        """
        identity = f"{file_path}|{mtime}|{file_size}"
        return hashlib.sha256(identity.encode()).hexdigest()

    def get(self, file_path: str, mtime: float, file_size: int) -> QPixmap | None:
        """Retrieve thumbnail from cache (memory → disk).

        Args:
            file_path: Absolute file path
            mtime: File modification time
            file_size: File size in bytes

        Returns:
            QPixmap if cached, None if not found

        """
        cache_key = self.generate_cache_key(file_path, mtime, file_size)

        # Try memory cache first
        pixmap = self._memory_cache.get(cache_key)
        if pixmap:
            return pixmap

        # Try disk cache
        if self._disk_cache:
            pixmap = self._disk_cache.get(cache_key)
            if pixmap:
                # Promote to memory cache
                self._memory_cache.put(cache_key, pixmap)
                return pixmap

        return None

    def put(self, file_path: str, mtime: float, file_size: int, pixmap: QPixmap) -> bool:
        """Store thumbnail in cache (memory + disk).

        Args:
            file_path: Absolute file path
            mtime: File modification time
            file_size: File size in bytes
            pixmap: Thumbnail image to cache

        Returns:
            True if successfully stored in at least one cache layer

        """
        cache_key = self.generate_cache_key(file_path, mtime, file_size)

        # Store in memory cache (always)
        self._memory_cache.put(cache_key, pixmap)

        # Store in disk cache (if enabled)
        disk_success = True
        if self._disk_cache:
            disk_success = self._disk_cache.put(cache_key, pixmap)

        return disk_success

    def invalidate(self, file_path: str, mtime: float, file_size: int) -> None:
        """Invalidate cached thumbnail for a file.

        Args:
            file_path: Absolute file path
            mtime: File modification time
            file_size: File size in bytes

        """
        cache_key = self.generate_cache_key(file_path, mtime, file_size)

        # Remove from disk cache
        if self._disk_cache:
            self._disk_cache.remove(cache_key)

        # Memory cache will naturally evict via LRU
        logger.debug("[ThumbnailCache] Invalidated: %s", file_path)

    def clear(self) -> None:
        """Clear all cached thumbnails from memory and disk."""
        self._memory_cache.clear()
        if self._disk_cache:
            self._disk_cache.clear()
        logger.info("[ThumbnailCache] Cache cleared")

    def get_memory_size(self) -> int:
        """Get current memory cache size.

        Returns:
            Number of entries in memory cache

        """
        return self._memory_cache.size()

    def get_cache_dir(self) -> Path:
        """Get disk cache directory path.

        Returns:
            Path to cache directory

        """
        return self._config.cache_dir
