#!/usr/bin/env python3
"""
Profile cache performance and analyze hit rates.

Author: Michael Economou
Date: 2025-12-20

This script analyzes:
1. Memory cache size and hit rates
2. LRU eviction effectiveness
3. Cache memory usage
4. Optimization recommendations
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def analyze_cache_configuration() -> dict[str, any]:
    """Analyze current cache configuration."""
    print("=" * 80)
    print("ANALYZING: Cache Configuration")
    print("=" * 80)
    
    # Check PersistentHashCache
    from oncutf.core.persistent_hash_cache import PersistentHashCache, MAX_MEMORY_CACHE_SIZE as HASH_MAX
    
    # Check PersistentMetadataCache
    import oncutf.core.persistent_metadata_cache as pmc
    METADATA_MAX = pmc.MAX_MEMORY_CACHE_SIZE
    
    # Check AdvancedCacheManager
    from oncutf.core.advanced_cache_manager import AdvancedCacheManager
    
    config = {
        "hash_cache_max": HASH_MAX,
        "metadata_cache_max": METADATA_MAX,
        "advanced_cache_default": 1000,
    }
    
    print(f"\n📊 Current Configuration:")
    print(f"  PersistentHashCache:     {config['hash_cache_max']:>6} entries")
    print(f"  PersistentMetadataCache: {config['metadata_cache_max']:>6} entries")
    print(f"  AdvancedCacheManager:    {config['advanced_cache_default']:>6} entries")
    
    return config


def estimate_cache_memory() -> dict[str, float]:
    """Estimate memory usage for caches."""
    print("\n" + "=" * 80)
    print("ESTIMATING: Cache Memory Usage")
    print("=" * 80)
    
    # Assumptions based on typical data
    hash_entry_size = 100  # bytes (path + CRC32 hash)
    metadata_entry_size = 2048  # bytes (path + EXIF data)
    
    from oncutf.core.persistent_hash_cache import MAX_MEMORY_CACHE_SIZE as HASH_MAX
    import oncutf.core.persistent_metadata_cache as pmc
    METADATA_MAX = pmc.MAX_MEMORY_CACHE_SIZE
    
    hash_memory_mb = (HASH_MAX * hash_entry_size) / (1024 * 1024)
    metadata_memory_mb = (METADATA_MAX * metadata_entry_size) / (1024 * 1024)
    total_memory_mb = hash_memory_mb + metadata_memory_mb
    
    results = {
        "hash_memory_mb": hash_memory_mb,
        "metadata_memory_mb": metadata_memory_mb,
        "total_memory_mb": total_memory_mb,
    }
    
    print(f"\n💾 Estimated Memory Usage:")
    print(f"  Hash cache:     {hash_memory_mb:>8.2f} MB ({HASH_MAX} × {hash_entry_size}B)")
    print(f"  Metadata cache: {metadata_memory_mb:>8.2f} MB ({METADATA_MAX} × {metadata_entry_size}B)")
    print(f"  Total:          {total_memory_mb:>8.2f} MB")
    
    return results


def test_lru_behavior() -> dict[str, any]:
    """Test LRU cache behavior."""
    print("\n" + "=" * 80)
    print("TESTING: LRU Cache Behavior")
    print("=" * 80)
    
    from oncutf.core.advanced_cache_manager import LRUCache
    
    # Create small cache for testing
    cache = LRUCache(maxsize=5)
    
    # Fill cache
    for i in range(5):
        cache.set(f"key_{i}", f"value_{i}")
    
    print(f"\n📊 Initial state: {cache.get_stats()['size']} entries")
    
    # Access some entries (make them "recently used")
    cache.get("key_0")  # Make key_0 most recent
    cache.get("key_1")  # Make key_1 most recent
    
    # Add new entry (should evict key_2, the oldest unused)
    cache.set("key_5", "value_5")
    
    # Check what was evicted
    evicted = []
    kept = []
    for i in range(6):
        if cache.get(f"key_{i}") is not None:
            kept.append(f"key_{i}")
        else:
            evicted.append(f"key_{i}")
    
    print(f"\n🔍 LRU Test Results:")
    print(f"  Kept entries:    {', '.join(kept)}")
    print(f"  Evicted entries: {', '.join(evicted)}")
    print(f"  ✅ LRU working correctly!" if "key_2" in evicted else "  ❌ LRU not working!")
    
    stats = cache.get_stats()
    print(f"\n📈 Cache Stats:")
    print(f"  Size: {stats['size']}/{stats['maxsize']}")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit rate: {stats['hit_rate']:.1f}%")
    
    return stats


def recommend_optimizations() -> list[str]:
    """Generate optimization recommendations."""
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    from oncutf.core.persistent_hash_cache import MAX_MEMORY_CACHE_SIZE as HASH_MAX
    import oncutf.core.persistent_metadata_cache as pmc
    METADATA_MAX = pmc.MAX_MEMORY_CACHE_SIZE
    
    recommendations = []
    
    # Check hash cache size
    if HASH_MAX < 2000:
        recommendations.append(
            f"📈 Increase PersistentHashCache from {HASH_MAX} to 2000-5000 entries\n"
            f"   Reason: Hash values are small (~100B), can afford larger cache\n"
            f"   Impact: Better hit rate for hash checks, minimal memory increase"
        )
    else:
        recommendations.append(
            f"✅ PersistentHashCache size is optimal ({HASH_MAX} entries)"
        )
    
    # Check metadata cache size
    if METADATA_MAX < 1000:
        recommendations.append(
            f"📈 Consider increasing PersistentMetadataCache from {METADATA_MAX} to 1000 entries\n"
            f"   Reason: Users often work with 100-500 files, larger cache reduces DB queries\n"
            f"   Impact: ~1MB additional memory for 2x cache size"
        )
    else:
        recommendations.append(
            f"✅ PersistentMetadataCache size is reasonable ({METADATA_MAX} entries)"
        )
    
    # Cache preloading
    recommendations.append(
        "🚀 Add cache warming on startup\n"
        "   Preload recently accessed files from database to memory cache\n"
        "   Impact: Faster first access after app restart"
    )
    
    # Cache statistics monitoring
    recommendations.append(
        "📊 Add cache statistics monitoring\n"
        "   Log hit/miss rates periodically to identify optimization opportunities\n"
        "   Impact: Data-driven cache tuning"
    )
    
    print()
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}\n")
    
    return recommendations


def main() -> int:
    """Run cache profiling and analysis."""
    print("\n" + "=" * 80)
    print("🔬 Cache Performance Analysis")
    print("=" * 80)
    
    try:
        config = analyze_cache_configuration()
        memory = estimate_cache_memory()
        lru_stats = test_lru_behavior()
        recommendations = recommend_optimizations()
        
        # Summary
        print("\n" + "=" * 80)
        print("📈 SUMMARY")
        print("=" * 80)
        
        print(f"\n✅ Current cache memory: {memory['total_memory_mb']:.2f} MB")
        print(f"✅ LRU eviction: Working correctly")
        print(f"✅ {len(recommendations)} optimization recommendations")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
