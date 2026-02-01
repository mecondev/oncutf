"""Module: advanced_cache_manager.py.

Author: Michael Economou
Date: 2025-05-01

Advanced Cache Manager - Simple but effective caching for speed and reliability.
"""

import hashlib
import pickle
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class LRUCache:
    """Simple LRU cache for speed optimization."""

    def __init__(self, maxsize: int = 1000) -> None:
        """Initialize LRU cache with maximum size."""
        self.maxsize = maxsize
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        """Get value with LRU update."""
        if key in self.cache:
            # Move to end (most recently used)
            value = self.cache.pop(key)
            self.cache[key] = value
            self.hits += 1
            return value

        self.misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value with LRU eviction."""
        if key in self.cache:
            # Update existing
            self.cache.pop(key)
        elif len(self.cache) >= self.maxsize:
            # Remove oldest (least recently used)
            self.cache.popitem(last=False)

        self.cache[key] = value

    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "size": len(self.cache),
            "maxsize": self.maxsize,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_requests": total,
        }


class DiskCache:
    """Simple disk cache for large datasets."""

    def __init__(self, cache_dir: str | None = None) -> None:
        """Initialize disk cache in the specified directory."""
        if cache_dir is None:
            cache_dir = str(Path.home() / ".oncutf" / "cache")

        self.cache_dir: str = cache_dir
        Path(cache_dir).mkdir(parents=True, exist_ok=True)

        self.hits = 0
        self.misses = 0

    def _get_cache_path(self, key: str) -> str:
        """Get cache file path."""
        # Use hash for safe filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return str(Path(self.cache_dir) / f"{key_hash}.cache")

    def get(self, key: str) -> Any | None:
        """Get value from disk cache."""
        cache_path = self._get_cache_path(key)

        try:
            cache_path_obj = Path(cache_path)
            if cache_path_obj.exists():
                # Check if cache is still valid (24 hours)
                if time.time() - cache_path_obj.stat().st_mtime < 86400:
                    with cache_path_obj.open("rb") as f:
                        value = pickle.load(f)
                    self.hits += 1
                    return value
                # Cache expired, remove it
                cache_path_obj.unlink()
        except Exception as e:
            logger.warning("[DiskCache] Error reading cache for %s: %s", key, e)

        self.misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value to disk cache."""
        cache_path = self._get_cache_path(key)

        try:
            with Path(cache_path).open("wb") as f:
                pickle.dump(value, f)
        except Exception as e:
            logger.warning("[DiskCache] Error writing cache for %s: %s", key, e)

    def clear(self) -> None:
        """Clear disk cache."""
        try:
            for entry in Path(self.cache_dir).iterdir():
                if entry.suffix == ".cache":
                    entry.unlink()
            self.hits = 0
            self.misses = 0
        except Exception as e:
            logger.error("[DiskCache] Error clearing cache: %s", e)

    def get_stats(self) -> dict[str, Any]:
        """Get disk cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        # Count cache files
        cache_files = 0
        cache_size = 0
        try:
            for entry in Path(self.cache_dir).iterdir():
                if entry.suffix == ".cache":
                    cache_files += 1
                    cache_size += entry.stat().st_size
        except Exception:
            pass

        return {
            "cache_files": cache_files,
            "cache_size_mb": cache_size / (1024 * 1024),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_requests": total,
        }


class AdvancedCacheManager:
    """Advanced cache manager with memory and disk caching."""

    def __init__(self, memory_cache_size: int = 1000) -> None:
        """Initialize cache manager with memory and disk backends."""
        self.memory_cache = LRUCache(memory_cache_size)
        self.disk_cache = DiskCache()
        self.compression_threshold = 1024 * 1024  # 1MB

    def get(self, key: str) -> Any | None:
        """Get value with memory-first strategy."""
        # Try memory cache first
        value = self.memory_cache.get(key)
        if value is not None:
            return value

        # Try disk cache
        value = self.disk_cache.get(key)
        if value is not None:
            # Cache in memory for next access
            self.memory_cache.set(key, value)
            return value

        return None

    def set(self, key: str, value: Any) -> None:
        """Set value with smart caching strategy."""
        # Always cache in memory
        self.memory_cache.set(key, value)

        # Cache in disk if value is large
        if self._estimate_size(value) > self.compression_threshold:
            self.disk_cache.set(key, value)

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value."""
        try:
            return len(pickle.dumps(value))
        except Exception:
            return 0

    def clear(self) -> None:
        """Clear all caches."""
        self.memory_cache.clear()
        self.disk_cache.clear()
        logger.debug("[AdvancedCacheManager] All caches cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        memory_stats = self.memory_cache.get_stats()
        disk_stats = self.disk_cache.get_stats()

        return {
            "memory_cache": memory_stats,
            "disk_cache": disk_stats,
            "overall_hit_rate": (memory_stats["hit_rate"] + disk_stats["hit_rate"]) / 2,
        }

    def smart_invalidation(self, changed_files: list[str]) -> None:
        """Smart cache invalidation for changed files."""
        if not changed_files:
            return

        # Create pattern for invalidation
        patterns = set()
        for file_path in changed_files:
            # Add file-specific patterns
            patterns.add(f"file_{file_path}")
            patterns.add(f"metadata_{file_path}")
            patterns.add(f"hash_{file_path}")

            # Add directory patterns
            dir_path = str(Path(file_path).parent)
            patterns.add(f"dir_{dir_path}")

        # Invalidate matching cache entries
        invalidated_count = 0
        for pattern in patterns:
            # check the actual internal cache keys
            keys_to_remove = [k for k in self.memory_cache.cache if pattern in k]
            for k in keys_to_remove:
                self.memory_cache.cache.pop(k, None)
                invalidated_count += 1

        if invalidated_count > 0:
            logger.debug("[AdvancedCacheManager] Invalidated %d cache entries", invalidated_count)

    def optimize_cache_size(self) -> None:
        """Optimize cache size."""
        # Reduce memory cache size if hit rate is low
        memory_stats = self.memory_cache.get_stats()
        if memory_stats["hit_rate"] < 50 and memory_stats["size"] > 100:
            # Reduce cache size
            new_size = max(100, memory_stats["size"] // 2)
            old_cache = self.memory_cache.cache
            self.memory_cache = LRUCache(new_size)

            # Keep most recent entries
            for key, value in list(old_cache.items())[-new_size:]:
                self.memory_cache.set(key, value)

            logger.debug("[AdvancedCacheManager] Optimized memory cache size to %d", new_size)
