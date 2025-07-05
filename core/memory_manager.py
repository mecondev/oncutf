"""
Memory Manager Module

This module provides comprehensive memory management for the OnCutF application.
It handles automatic cleanup of unused cache entries, memory optimization,
and smart cache management with LRU eviction policies.

Features:
- Automatic cache cleanup based on usage patterns
- Memory threshold monitoring
- LRU eviction policies
- Cache statistics and monitoring
- Integration with existing cache systems

Author: OnCutF Development Team
Date: 2025-01-31
"""

import gc
import time
import psutil
import threading
from typing import Dict, List, Optional, Any, Callable, Set
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from core.qt_imports import QObject, QTimer, pyqtSignal
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class CacheEntry:
    """Represents a cache entry with usage statistics."""
    key: str
    data: Any
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    creation_time: float = field(default_factory=time.time)
    size_bytes: int = 0

    def touch(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_access = time.time()


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    total_memory_mb: float
    used_memory_mb: float
    available_memory_mb: float
    cache_memory_mb: float
    cache_entries: int
    evicted_entries: int
    hit_rate: float
    miss_rate: float


class LRUCache:
    """
    LRU (Least Recently Used) cache implementation with memory management.

    Features:
    - Automatic eviction based on size or count limits
    - Access pattern tracking
    - Memory usage monitoring
    - Thread-safe operations
    """

    def __init__(self, max_size: int = 1000, max_memory_mb: float = 100.0):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory_mb = max_memory_mb
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                entry.touch()
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                return entry.data
            else:
                self._misses += 1
                return None

    def set(self, key: str, value: Any, size_bytes: int = 0) -> None:
        """Set item in cache."""
        with self._lock:
            if key in self._cache:
                # Update existing entry
                entry = self._cache[key]
                entry.data = value
                entry.size_bytes = size_bytes
                entry.touch()
                self._cache.move_to_end(key)
            else:
                # Add new entry
                entry = CacheEntry(key=key, data=value, size_bytes=size_bytes)
                self._cache[key] = entry

            # Check if eviction is needed
            self._evict_if_needed()

    def remove(self, key: str) -> bool:
        """Remove item from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def _evict_if_needed(self) -> None:
        """Evict entries if limits are exceeded."""
        # Check size limit
        while len(self._cache) > self.max_size:
            self._evict_oldest()

        # Check memory limit
        current_memory = self.get_memory_usage_mb()
        while current_memory > self.max_memory_mb and self._cache:
            self._evict_oldest()
            current_memory = self.get_memory_usage_mb()

    def _evict_oldest(self) -> None:
        """Evict the least recently used entry."""
        if self._cache:
            key, _ = self._cache.popitem(last=False)
            self._evictions += 1
            logger.debug(f"[MemoryManager] Evicted cache entry: {key}")

    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        with self._lock:
            total_bytes = sum(entry.size_bytes for entry in self._cache.values())
            return total_bytes / (1024 * 1024)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                'entries': len(self._cache),
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'hit_rate': hit_rate,
                'miss_rate': 1.0 - hit_rate,
                'memory_mb': self.get_memory_usage_mb(),
                'max_memory_mb': self.max_memory_mb
            }


class MemoryManager(QObject):
    """
    Comprehensive memory management system for OnCutF.

    Features:
    - Automatic cache cleanup
    - Memory threshold monitoring
    - Integration with existing cache systems
    - Performance statistics
    - Configurable cleanup policies
    """

    # Signals
    memory_warning = pyqtSignal(float)  # memory_usage_percent
    cache_cleaned = pyqtSignal(int)     # cleaned_entries_count

    def __init__(self, parent=None):
        """Initialize memory manager."""
        super().__init__(parent)

        # Configuration
        self.memory_threshold_percent = 85.0  # Trigger cleanup at 85% memory usage
        self.cleanup_interval_seconds = 300   # Check every 5 minutes
        self.cache_max_age_seconds = 3600     # Remove entries older than 1 hour
        self.min_access_count = 2             # Keep entries accessed at least twice

        # Cache registry
        self._registered_caches: Dict[str, Any] = {}
        self._cleanup_callbacks: List[Callable] = []

        # Statistics
        self._cleanup_count = 0
        self._last_cleanup = time.time()
        self._total_freed_mb = 0.0

        # Monitoring timer
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._perform_cleanup)
        self._cleanup_timer.start(self.cleanup_interval_seconds * 1000)

        logger.info("[MemoryManager] Initialized with automatic cleanup")

    def register_cache(self, name: str, cache_object: Any) -> None:
        """
        Register a cache object for monitoring and cleanup.

        Args:
            name: Cache identifier
            cache_object: Cache object (must have cleanup methods)
        """
        self._registered_caches[name] = cache_object
        logger.debug(f"[MemoryManager] Registered cache: {name}")

    def register_cleanup_callback(self, callback: Callable) -> None:
        """
        Register a cleanup callback function.

        Args:
            callback: Function to call during cleanup
        """
        self._cleanup_callbacks.append(callback)
        logger.debug("[MemoryManager] Registered cleanup callback")

    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        try:
            # System memory
            memory = psutil.virtual_memory()

            # Cache memory (approximate)
            cache_memory_mb = 0.0
            cache_entries = 0

            for cache_name, cache_obj in self._registered_caches.items():
                if hasattr(cache_obj, 'get_memory_usage_mb'):
                    cache_memory_mb += cache_obj.get_memory_usage_mb()
                if hasattr(cache_obj, '__len__'):
                    cache_entries += len(cache_obj)

            return MemoryStats(
                total_memory_mb=memory.total / (1024 * 1024),
                used_memory_mb=memory.used / (1024 * 1024),
                available_memory_mb=memory.available / (1024 * 1024),
                cache_memory_mb=cache_memory_mb,
                cache_entries=cache_entries,
                evicted_entries=self._cleanup_count,
                hit_rate=0.0,  # Will be calculated from individual caches
                miss_rate=0.0
            )
        except Exception as e:
            logger.error(f"[MemoryManager] Error getting memory stats: {e}")
            return MemoryStats(0, 0, 0, 0, 0, 0, 0, 0)

    def _perform_cleanup(self) -> None:
        """Perform automatic cleanup based on memory usage."""
        try:
            stats = self.get_memory_stats()
            memory_usage_percent = (stats.used_memory_mb / stats.total_memory_mb) * 100

            # Check if cleanup is needed
            if memory_usage_percent > self.memory_threshold_percent:
                logger.info(f"[MemoryManager] Memory usage {memory_usage_percent:.1f}% exceeds threshold {self.memory_threshold_percent}%")

                cleaned_entries = self._cleanup_caches()

                # Force garbage collection
                gc.collect()

                self._cleanup_count += cleaned_entries
                self._last_cleanup = time.time()

                # Emit signals
                self.memory_warning.emit(memory_usage_percent)
                self.cache_cleaned.emit(cleaned_entries)

                logger.info(f"[MemoryManager] Cleanup completed, freed {cleaned_entries} entries")

        except Exception as e:
            logger.error(f"[MemoryManager] Error during cleanup: {e}")

    def _cleanup_caches(self) -> int:
        """Clean up registered caches."""
        total_cleaned = 0
        current_time = time.time()

        # Clean registered caches
        for cache_name, cache_obj in self._registered_caches.items():
            try:
                cleaned = self._cleanup_cache_object(cache_obj, current_time)
                total_cleaned += cleaned
                logger.debug(f"[MemoryManager] Cleaned {cleaned} entries from {cache_name}")
            except Exception as e:
                logger.error(f"[MemoryManager] Error cleaning cache {cache_name}: {e}")

        # Call cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"[MemoryManager] Error in cleanup callback: {e}")

        return total_cleaned

    def _cleanup_cache_object(self, cache_obj: Any, current_time: float) -> int:
        """Clean up a specific cache object."""
        cleaned = 0

        # Try different cleanup strategies based on cache type
        if hasattr(cache_obj, '_cache') and isinstance(cache_obj._cache, dict):
            # Dictionary-based cache
            keys_to_remove = []

            for key, entry in cache_obj._cache.items():
                should_remove = False

                # Check age
                if hasattr(entry, 'last_access'):
                    age = current_time - entry.last_access
                    if age > self.cache_max_age_seconds:
                        should_remove = True

                # Check access count
                if hasattr(entry, 'access_count'):
                    if entry.access_count < self.min_access_count:
                        should_remove = True

                if should_remove:
                    keys_to_remove.append(key)

            # Remove identified entries
            for key in keys_to_remove:
                if hasattr(cache_obj, 'remove'):
                    cache_obj.remove(key)
                else:
                    del cache_obj._cache[key]
                cleaned += 1

        elif hasattr(cache_obj, 'clear') and len(cache_obj) > 1000:
            # Large cache - clear if too big
            cache_obj.clear()
            cleaned = 1000  # Estimate

        return cleaned

    def force_cleanup(self) -> int:
        """Force immediate cleanup of all caches."""
        logger.info("[MemoryManager] Forcing immediate cleanup")
        cleaned = self._cleanup_caches()
        gc.collect()
        return cleaned

    def get_cleanup_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics."""
        return {
            'total_cleanups': self._cleanup_count,
            'last_cleanup': self._last_cleanup,
            'registered_caches': len(self._registered_caches),
            'cleanup_callbacks': len(self._cleanup_callbacks),
            'memory_threshold': self.memory_threshold_percent,
            'cleanup_interval': self.cleanup_interval_seconds
        }

    def configure(self, **kwargs) -> None:
        """Configure memory manager settings."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.debug(f"[MemoryManager] Set {key} = {value}")

    def shutdown(self) -> None:
        """Shutdown memory manager."""
        if self._cleanup_timer.isActive():
            self._cleanup_timer.stop()

        # Final cleanup
        self.force_cleanup()

        logger.info("[MemoryManager] Shutdown completed")


# Global memory manager instance
_memory_manager_instance: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get global memory manager instance."""
    global _memory_manager_instance
    if _memory_manager_instance is None:
        _memory_manager_instance = MemoryManager()
    return _memory_manager_instance


def initialize_memory_manager(**config) -> MemoryManager:
    """Initialize memory manager with configuration."""
    global _memory_manager_instance
    _memory_manager_instance = MemoryManager()
    if config:
        _memory_manager_instance.configure(**config)
    return _memory_manager_instance
