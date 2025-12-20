"""
Cache management module.

This module provides caching functionality including:
- AdvancedCacheManager: High-level cache coordination
- PersistentHashCache: File hash caching with LRU eviction
- PersistentMetadataCache: Metadata caching with LRU eviction

Author: Michael Economou
Date: 2025-12-20
"""

from __future__ import annotations

from oncutf.core.cache.advanced_cache_manager import AdvancedCacheManager
from oncutf.core.cache.persistent_hash_cache import PersistentHashCache
from oncutf.core.cache.persistent_metadata_cache import PersistentMetadataCache

__all__ = [
    "AdvancedCacheManager",
    "PersistentHashCache",
    "PersistentMetadataCache",
]
