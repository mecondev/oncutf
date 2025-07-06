"""
Module: smart_icon_cache.py

Author: Michael Economou
Date: 2025-06-20

Smart Icon Cache Module
This module provides an advanced icon caching system with LRU eviction,
memory optimization, and intelligent loading patterns.
Features:
- LRU (Least Recently Used) eviction policy
- Memory-aware caching with size limits
- Async icon loading for better performance
- Theme-aware icon caching
- Preloading of commonly used icons
- Icon size optimization and scaling
- Integration with existing icon systems
"""
import os
import time
import threading
from typing import Dict, Optional, Tuple, List, Set, Any
from collections import OrderedDict
from pathlib import Path
from dataclasses import dataclass, field

from core.qt_imports import QIcon, QPixmap, QSize, QObject, QTimer, pyqtSignal
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class IconCacheEntry:
    """Represents a cached icon with metadata."""
    icon: QIcon
    size: QSize
    theme: str
    file_path: str
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    creation_time: float = field(default_factory=time.time)
    memory_size_bytes: int = 0

    def touch(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_access = time.time()

    def get_cache_key(self) -> str:
        """Generate cache key for this entry."""
        return f"{self.file_path}_{self.theme}_{self.size.width()}x{self.size.height()}"


class SmartIconCache(QObject):
    """
    Advanced icon caching system with LRU eviction and memory management.

    Features:
    - LRU eviction based on access patterns
    - Memory-aware caching with configurable limits
    - Theme-aware icon storage
    - Size-specific caching for different UI elements
    - Preloading of commonly used icons
    - Async loading capabilities
    - Integration with memory manager
    """

    # Signals
    cache_hit = pyqtSignal(str)      # cache_key
    cache_miss = pyqtSignal(str)     # cache_key
    cache_evicted = pyqtSignal(str)  # cache_key

    def __init__(self, max_entries: int = 500, max_memory_mb: float = 50.0, parent=None):
        """
        Initialize smart icon cache.

        Args:
            max_entries: Maximum number of cached icons
            max_memory_mb: Maximum memory usage in MB
            parent: Parent QObject
        """
        super().__init__(parent)

        self.max_entries = max_entries
        self.max_memory_mb = max_memory_mb

        # Cache storage
        self._cache: OrderedDict[str, IconCacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._preloads = 0

        # Common icon sizes for preloading
        self._common_sizes = [
            QSize(16, 16),   # Small icons (menu items, tree view)
            QSize(24, 24),   # Medium icons (toolbars, buttons)
            QSize(32, 32),   # Large icons (dialogs, headers)
            QSize(48, 48),   # Extra large icons (splash, about)
        ]

        # Commonly used icons for preloading
        self._common_icons = [
            'file', 'folder', 'image', 'video', 'audio', 'document',
            'valid', 'invalid', 'unchanged', 'duplicate',
            'plus', 'minus', 'edit', 'delete', 'save', 'open',
            'settings', 'info', 'warning', 'error', 'success'
        ]

        # Theme tracking
        self._current_theme = 'dark'

        # Cleanup timer
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._perform_cleanup)
        self._cleanup_timer.start(300000)  # 5 minutes

        logger.info(f"[SmartIconCache] Initialized with {max_entries} entries, {max_memory_mb}MB limit")

    def get_icon(self, name: str, size: QSize = None, theme: str = None) -> QIcon:
        """
        Get icon from cache or load it.

        Args:
            name: Icon name
            size: Desired icon size (default: 16x16)
            theme: Theme name (default: current theme)

        Returns:
            QIcon object
        """
        if size is None:
            size = QSize(16, 16)
        if theme is None:
            theme = self._current_theme

        cache_key = f"{name}_{theme}_{size.width()}x{size.height()}"

        with self._lock:
            # Check cache first
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                entry.touch()
                # Move to end (most recently used)
                self._cache.move_to_end(cache_key)
                self._hits += 1
                self.cache_hit.emit(cache_key)
                return entry.icon

            # Cache miss - load icon
            self._misses += 1
            self.cache_miss.emit(cache_key)

            icon = self._load_icon(name, size, theme)
            if not icon.isNull():
                self._store_icon(cache_key, icon, name, size, theme)

            return icon

    def _load_icon(self, name: str, size: QSize, theme: str) -> QIcon:
        """Load icon from file system."""
        try:
            # Try different icon loading strategies
            icon_path = self._find_icon_path(name, theme)

            if icon_path and os.path.exists(icon_path):
                # Load and scale icon
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    # Scale to desired size with smooth transformation
                    scaled_pixmap = pixmap.scaled(
                        size,
                        aspectRatioMode=1,  # Qt.KeepAspectRatio
                        transformMode=1     # Qt.SmoothTransformation
                    )
                    icon = QIcon(scaled_pixmap)
                    logger.debug(f"[SmartIconCache] Loaded icon: {name} ({size.width()}x{size.height()})")
                    return icon

            # Fallback to system icon or empty icon
            logger.warning(f"[SmartIconCache] Icon not found: {name}")
            return QIcon()

        except Exception as e:
            logger.error(f"[SmartIconCache] Error loading icon {name}: {e}")
            return QIcon()

    def _find_icon_path(self, name: str, theme: str) -> Optional[str]:
        """Find icon file path."""
        from utils.path_utils import get_icons_dir

        icons_dir = get_icons_dir()

        # Search patterns
        search_patterns = [
            f"feather_icons/{name}.svg",
            f"{name}.svg",
            f"{name}.png",
            f"{theme}/{name}.svg",
            f"{theme}/{name}.png"
        ]

        for pattern in search_patterns:
            path = icons_dir / pattern
            if path.exists():
                return str(path)

        return None

    def _store_icon(self, cache_key: str, icon: QIcon, name: str, size: QSize, theme: str):
        """Store icon in cache."""
        try:
            # Calculate approximate memory size
            memory_size = self._estimate_icon_memory_size(icon, size)

            # Create cache entry
            entry = IconCacheEntry(
                icon=icon,
                size=size,
                theme=theme,
                file_path=name,
                memory_size_bytes=memory_size
            )

            # Store in cache
            self._cache[cache_key] = entry

            # Check if eviction is needed
            self._evict_if_needed()

        except Exception as e:
            logger.error(f"[SmartIconCache] Error storing icon {cache_key}: {e}")

    def _estimate_icon_memory_size(self, icon: QIcon, size: QSize) -> int:
        """Estimate memory size of an icon."""
        # Rough estimation: 4 bytes per pixel (RGBA) + overhead
        pixels = size.width() * size.height()
        return pixels * 4 + 1024  # Add 1KB overhead

    def _evict_if_needed(self):
        """Evict entries if cache limits are exceeded."""
        # Check entry count limit
        while len(self._cache) > self.max_entries:
            self._evict_oldest()

        # Check memory limit
        current_memory_mb = self.get_memory_usage_mb()
        while current_memory_mb > self.max_memory_mb and self._cache:
            self._evict_oldest()
            current_memory_mb = self.get_memory_usage_mb()

    def _evict_oldest(self):
        """Evict the least recently used entry."""
        if self._cache:
            cache_key, entry = self._cache.popitem(last=False)
            self._evictions += 1
            self.cache_evicted.emit(cache_key)
            logger.debug(f"[SmartIconCache] Evicted: {cache_key}")

    def preload_common_icons(self, theme: str = None):
        """Preload commonly used icons."""
        if theme is None:
            theme = self._current_theme

        logger.info(f"[SmartIconCache] Preloading common icons for theme: {theme}")

        for icon_name in self._common_icons:
            for size in self._common_sizes:
                try:
                    self.get_icon(icon_name, size, theme)
                    self._preloads += 1
                except Exception as e:
                    logger.debug(f"[SmartIconCache] Could not preload {icon_name}: {e}")

        logger.info(f"[SmartIconCache] Preloaded {self._preloads} icons")

    def set_theme(self, theme: str):
        """Set current theme and optionally preload icons."""
        if theme != self._current_theme:
            logger.info(f"[SmartIconCache] Theme changed: {self._current_theme} -> {theme}")
            self._current_theme = theme

            # Optionally clear cache for old theme
            self._clear_theme_cache(self._current_theme)

            # Preload icons for new theme
            self.preload_common_icons(theme)

    def _clear_theme_cache(self, old_theme: str):
        """Clear cache entries for a specific theme."""
        with self._lock:
            keys_to_remove = []
            for key, entry in self._cache.items():
                if entry.theme == old_theme:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._cache[key]

            logger.debug(f"[SmartIconCache] Cleared {len(keys_to_remove)} entries for theme: {old_theme}")

    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        with self._lock:
            total_bytes = sum(entry.memory_size_bytes for entry in self._cache.values())
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
                'preloads': self._preloads,
                'hit_rate': hit_rate,
                'miss_rate': 1.0 - hit_rate,
                'memory_mb': self.get_memory_usage_mb(),
                'max_memory_mb': self.max_memory_mb,
                'max_entries': self.max_entries,
                'current_theme': self._current_theme
            }

    def _perform_cleanup(self):
        """Perform periodic cleanup."""
        try:
            current_time = time.time()
            max_age = 3600  # 1 hour

            with self._lock:
                keys_to_remove = []

                for key, entry in self._cache.items():
                    # Remove old entries with low access count
                    age = current_time - entry.last_access
                    if age > max_age and entry.access_count < 3:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self._cache[key]

                if keys_to_remove:
                    logger.debug(f"[SmartIconCache] Cleaned up {len(keys_to_remove)} old entries")

        except Exception as e:
            logger.error(f"[SmartIconCache] Error during cleanup: {e}")

    def clear(self):
        """Clear all cached icons."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._preloads = 0
            logger.info("[SmartIconCache] Cache cleared")

    def remove_icon(self, name: str, size: QSize = None, theme: str = None) -> bool:
        """Remove specific icon from cache."""
        if size is None:
            size = QSize(16, 16)
        if theme is None:
            theme = self._current_theme

        cache_key = f"{name}_{theme}_{size.width()}x{size.height()}"

        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                return True
            return False

    def shutdown(self):
        """Shutdown icon cache."""
        if self._cleanup_timer.isActive():
            self._cleanup_timer.stop()

        self.clear()
        logger.info("[SmartIconCache] Shutdown completed")


# Global smart icon cache instance
_smart_icon_cache_instance: Optional[SmartIconCache] = None


def get_smart_icon_cache() -> SmartIconCache:
    """Get global smart icon cache instance."""
    global _smart_icon_cache_instance
    if _smart_icon_cache_instance is None:
        _smart_icon_cache_instance = SmartIconCache()
    return _smart_icon_cache_instance


def initialize_smart_icon_cache(max_entries: int = 500, max_memory_mb: float = 50.0) -> SmartIconCache:
    """Initialize smart icon cache with configuration."""
    global _smart_icon_cache_instance
    _smart_icon_cache_instance = SmartIconCache(max_entries, max_memory_mb)
    return _smart_icon_cache_instance


# Convenience functions for easy integration
def get_cached_icon(name: str, size: QSize = None, theme: str = None) -> QIcon:
    """Get icon using the global smart cache."""
    return get_smart_icon_cache().get_icon(name, size, theme)


def preload_icons(theme: str = None):
    """Preload common icons using the global smart cache."""
    get_smart_icon_cache().preload_common_icons(theme)


def set_icon_theme(theme: str):
    """Set icon theme using the global smart cache."""
    get_smart_icon_cache().set_theme(theme)
