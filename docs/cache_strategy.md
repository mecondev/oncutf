# OnCutF Cache Strategy Documentation

**Author:** Development Team  
**Date:** 2025-12-04  
**Version:** 1.0  
**Status:** Complete  

---

## Table of Contents

1. [Overview](#overview)
2. [Cache Architecture](#cache-architecture)
3. [Advanced Cache Manager](#advanced-cache-manager)
4. [Persistent Hash Cache](#persistent-hash-cache)
5. [Persistent Metadata Cache](#persistent-metadata-cache)
6. [Usage Patterns](#usage-patterns)
7. [Cache Invalidation Strategies](#cache-invalidation-strategies)
8. [Performance Tuning](#performance-tuning)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Best Practices](#best-practices)

---

## Overview

OnCutF uses a **multi-layered caching strategy** to provide optimal performance when working with large file sets and metadata operations. The cache system consists of three main components:

1. **AdvancedCacheManager** - Multi-tier memory + disk caching
2. **PersistentHashCache** - Database-backed hash storage
3. **PersistentMetadataCache** - Database-backed metadata storage

### Key Benefits

- **Performance:** 500x faster for cached operations
- **Persistence:** Data survives application restarts
- **Scalability:** Handles thousands of files efficiently
- **Reliability:** Automatic cache invalidation and cleanup

---

## Cache Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│   Advanced   │ │   Hash   │ │   Metadata   │
│    Cache     │ │  Cache   │ │    Cache     │
│   Manager    │ │          │ │              │
└──────┬───────┘ └────┬─────┘ └──────┬───────┘
       │              │               │
       ▼              ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│  Memory  │   │  Memory  │   │  Memory  │
│   Cache  │   │   Cache  │   │   Cache  │
│  (LRU)   │   │  (Dict)  │   │  (Dict)  │
└──────┬───┘   └────┬─────┘   └────┬─────┘
       │            │               │
       ▼            └───────┬───────┘
┌──────────┐               │
│   Disk   │               ▼
│  Cache   │        ┌──────────────┐
│ (Files)  │        │   SQLite     │
└──────────┘        │   Database   │
                    └──────────────┘
```

### Cache Layers

| Layer | Purpose | Lifetime | Max Size |
|-------|---------|----------|----------|
| **Memory Cache (LRU)** | Hot data access | Session | 1000 items |
| **Memory Cache (Dict)** | Active files | Session | Unlimited |
| **Disk Cache** | Large datasets | 24 hours | ~100MB |
| **Database Cache** | Persistent data | Permanent | Unlimited |

---

## Advanced Cache Manager

### Purpose

`AdvancedCacheManager` provides a **two-tier caching system** optimized for speed and reliability:
- **Memory cache** (LRU) for frequently accessed data
- **Disk cache** for large datasets that don't fit in memory

### Location

**Module:** `core/advanced_cache_manager.py`

### Components

#### 1. LRU Cache

**Least Recently Used** memory cache with automatic eviction.

```python
from core.advanced_cache_manager import AdvancedCacheManager

# Initialize cache
cache = AdvancedCacheManager(memory_cache_size=1000)

# Store value
cache.set("my_key", {"data": "value"})

# Retrieve value
value = cache.get("my_key")  # Memory hit - fast!
```

**Features:**
- Automatic eviction when full
- Move-to-end on access (LRU)
- Hit/miss statistics tracking

#### 2. Disk Cache

Persistent cache for large datasets with 24-hour expiry.

```python
# Large data automatically cached to disk
large_data = {"files": [...1000 items...]}
cache.set("large_dataset", large_data)  # Stored to disk if > 1MB
```

**Features:**
- Automatic expiry (24 hours)
- MD5-based safe filenames
- Pickle serialization
- Size threshold: 1MB

### Configuration

```python
# Custom memory size
cache = AdvancedCacheManager(memory_cache_size=2000)

# Custom compression threshold
cache.compression_threshold = 512 * 1024  # 512KB
```

### Statistics

```python
stats = cache.get_stats()
print(stats)
# {
#     "memory_cache": {
#         "size": 450,
#         "maxsize": 1000,
#         "hits": 1250,
#         "misses": 150,
#         "hit_rate": 89.3,
#         "total_requests": 1400
#     },
#     "disk_cache": {
#         "cache_files": 15,
#         "cache_size_mb": 24.5,
#         "hits": 50,
#         "misses": 10,
#         "hit_rate": 83.3,
#         "total_requests": 60
#     },
#     "overall_hit_rate": 86.3
# }
```

### Smart Invalidation

```python
# Invalidate specific files
changed_files = ["/path/to/file1.jpg", "/path/to/file2.mp4"]
cache.smart_invalidation(changed_files)
# Invalidates:
#   - file_/path/to/file1.jpg
#   - metadata_/path/to/file1.jpg
#   - hash_/path/to/file1.jpg
#   - dir_/path/to/
```

### Auto-Optimization

```python
# Optimize cache size based on hit rate
cache.optimize_cache_size()
# If hit rate < 50%, reduces cache size by 50%
```

---

## Persistent Hash Cache

### Purpose

`PersistentHashCache` provides **database-backed hash storage** for file checksums with memory caching for performance.

### Location

**Module:** `core/persistent_hash_cache.py`

### Features

- **CRC32 hash storage** (default algorithm)
- **Database persistence** (SQLite)
- **Memory cache** for hot data
- **Batch operations** for efficiency
- **Duplicate detection**

### Basic Usage

```python
from core.persistent_hash_cache import get_persistent_hash_cache

# Get global instance
hash_cache = get_persistent_hash_cache()

# Store hash
hash_cache.store_hash("/path/to/file.jpg", "A1B2C3D4")

# Retrieve hash
hash_value = hash_cache.get_hash("/path/to/file.jpg")
if hash_value:
    print(f"Hash: {hash_value}")

# Check if hash exists
if hash_cache.has_hash("/path/to/file.jpg"):
    print("Hash is cached!")
```

### Batch Operations

```python
# Get multiple files with hashes
file_paths = ["/path/file1.jpg", "/path/file2.jpg", "/path/file3.jpg"]
files_with_hash = hash_cache.get_files_with_hash_batch(file_paths)
print(f"Cached: {len(files_with_hash)} / {len(file_paths)}")
```

### Duplicate Detection

```python
# Find duplicate files by hash
all_files = ["/path/file1.jpg", "/path/file2.jpg", "/path/copy.jpg"]
duplicates = hash_cache.find_duplicates(all_files)

for hash_value, file_list in duplicates.items():
    print(f"Hash {hash_value}: {len(file_list)} duplicates")
    for file_path in file_list:
        print(f"  - {file_path}")
```

### Cache Statistics

```python
stats = hash_cache.get_cache_stats()
print(stats)
# {
#     "memory_entries": 350,
#     "cache_hits": 1200,
#     "cache_misses": 150,
#     "hit_rate_percent": 88.89
# }
```

### Clearing Cache

```python
# Clear memory cache only (database intact)
hash_cache.clear_memory_cache()

# Remove specific file hash
hash_cache.remove_hash("/path/to/file.jpg")
```

---

## Persistent Metadata Cache

### Purpose

`PersistentMetadataCache` provides **database-backed metadata storage** with EXIF data persistence and memory caching.

### Location

**Module:** `core/persistent_metadata_cache.py`

### Features

- **Database persistence** (SQLite)
- **Memory cache** for active files
- **Extended metadata support** (EXIF data)
- **Batch operations**
- **Modification tracking**

### Basic Usage

```python
from core.persistent_metadata_cache import get_persistent_metadata_cache

# Get global instance
meta_cache = get_persistent_metadata_cache()

# Store metadata
metadata = {
    "File:FileName": "image.jpg",
    "File:FileSize": "2.5 MB",
    "EXIF:DateTimeOriginal": "2024:12:04 10:30:00",
    "EXIF:Model": "Canon EOS 5D"
}
meta_cache.set("/path/to/image.jpg", metadata, is_extended=True)

# Retrieve metadata
data = meta_cache.get("/path/to/image.jpg")
print(data.get("EXIF:Model"))  # "Canon EOS 5D"

# Check if metadata exists
if meta_cache.has("/path/to/image.jpg"):
    print("Metadata cached!")
```

### Working with Entries

```python
# Get metadata entry (includes flags)
entry = meta_cache.get_entry("/path/to/image.jpg")
if entry:
    print(f"Extended: {entry.is_extended}")
    print(f"Modified: {entry.modified}")
    print(f"Keys: {len(entry.data)}")
    print(f"Timestamp: {entry.timestamp}")
```

### Batch Operations

```python
# Get multiple entries at once
file_paths = ["/path/file1.jpg", "/path/file2.jpg", "/path/file3.jpg"]
entries = meta_cache.get_entries_batch(file_paths)

for path, entry in entries.items():
    if entry:
        print(f"{path}: {len(entry.data)} metadata fields")
    else:
        print(f"{path}: No cached metadata")
```

### Modified Metadata

```python
# Store modified metadata
modified_metadata = metadata.copy()
modified_metadata["EXIF:Artist"] = "John Doe"
meta_cache.set("/path/to/image.jpg", modified_metadata, 
               is_extended=True, modified=True)

# Retrieve entry to check modification status
entry = meta_cache.get_entry("/path/to/image.jpg")
if entry.modified:
    print("Metadata has been modified!")
```

### Cache Statistics

```python
stats = meta_cache.get_cache_stats()
print(stats)
# {
#     "memory_entries": 450,
#     "cache_hits": 2500,
#     "cache_misses": 250,
#     "hit_rate_percent": 90.91
# }
```

### Dictionary-like Interface

```python
# Backward compatibility
metadata = meta_cache["/path/to/file.jpg"]  # __getitem__
if "/path/to/file.jpg" in meta_cache:       # __contains__
    print("Cached!")
```

---

## Usage Patterns

### Pattern 1: File Loading with Cache

```python
from core.persistent_metadata_cache import get_persistent_metadata_cache
from core.direct_metadata_loader import load_metadata

meta_cache = get_persistent_metadata_cache()

def load_file_metadata(file_path: str) -> dict:
    """Load metadata with cache check."""
    
    # Check cache first
    if meta_cache.has(file_path):
        logger.debug(f"Cache hit: {file_path}")
        return meta_cache.get(file_path)
    
    # Load from disk
    logger.debug(f"Cache miss: {file_path}")
    metadata = load_metadata(file_path)
    
    # Store in cache
    meta_cache.set(file_path, metadata, is_extended=True)
    
    return metadata
```

### Pattern 2: Hash Calculation with Cache

```python
from core.persistent_hash_cache import get_persistent_hash_cache
import zlib

hash_cache = get_persistent_hash_cache()

def calculate_file_hash(file_path: str) -> str:
    """Calculate CRC32 hash with cache check."""
    
    # Check cache first
    cached_hash = hash_cache.get_hash(file_path)
    if cached_hash:
        logger.debug(f"Cache hit: {file_path}")
        return cached_hash
    
    # Calculate hash
    logger.debug(f"Cache miss: {file_path}")
    with open(file_path, 'rb') as f:
        data = f.read()
        hash_value = format(zlib.crc32(data) & 0xFFFFFFFF, '08X')
    
    # Store in cache
    hash_cache.store_hash(file_path, hash_value)
    
    return hash_value
```

### Pattern 3: Batch Processing

```python
def process_files_batch(file_paths: list[str]) -> dict:
    """Process multiple files with batch caching."""
    
    meta_cache = get_persistent_metadata_cache()
    hash_cache = get_persistent_hash_cache()
    
    # Batch query caches
    cached_metadata = meta_cache.get_entries_batch(file_paths)
    cached_hashes = hash_cache.get_files_with_hash_batch(file_paths)
    
    results = {}
    files_to_process = []
    
    for file_path in file_paths:
        # Check if fully cached
        if file_path in cached_hashes and cached_metadata.get(file_path):
            results[file_path] = {
                "metadata": cached_metadata[file_path].data,
                "hash": hash_cache.get_hash(file_path),
                "cached": True
            }
        else:
            files_to_process.append(file_path)
    
    # Process uncached files
    for file_path in files_to_process:
        metadata = load_metadata(file_path)
        hash_value = calculate_file_hash(file_path)
        
        meta_cache.set(file_path, metadata, is_extended=True)
        hash_cache.store_hash(file_path, hash_value)
        
        results[file_path] = {
            "metadata": metadata,
            "hash": hash_value,
            "cached": False
        }
    
    return results
```

### Pattern 4: Smart Cache Invalidation

```python
from core.advanced_cache_manager import AdvancedCacheManager

cache = AdvancedCacheManager()

def handle_file_modification(modified_files: list[str]):
    """Handle file modifications with cache invalidation."""
    
    # Invalidate related caches
    cache.smart_invalidation(modified_files)
    
    # Clear metadata and hash caches for modified files
    meta_cache = get_persistent_metadata_cache()
    hash_cache = get_persistent_hash_cache()
    
    for file_path in modified_files:
        meta_cache.remove(file_path)
        hash_cache.remove_hash(file_path)
    
    logger.info(f"Invalidated cache for {len(modified_files)} files")
```

---

## Cache Invalidation Strategies

### 1. File-Based Invalidation

Invalidate cache when files are modified, renamed, or deleted.

```python
def on_file_modified(file_path: str):
    """Invalidate all caches for modified file."""
    meta_cache.remove(file_path)
    hash_cache.remove_hash(file_path)
    cache.smart_invalidation([file_path])
```

### 2. Time-Based Invalidation

Disk cache automatically expires after 24 hours.

```python
# Disk cache expiry is automatic
# Check file modification time in cache
cache_path = disk_cache._get_cache_path(key)
if os.path.exists(cache_path):
    age = time.time() - os.path.getmtime(cache_path)
    if age > 86400:  # 24 hours
        # Cache expired, will be removed on next access
        pass
```

### 3. Manual Invalidation

Clear specific caches manually when needed.

```python
# Clear memory cache only
meta_cache.clear()
hash_cache.clear_memory_cache()
cache.memory_cache.clear()

# Full cache clear
cache.clear()  # Clears both memory and disk
```

### 4. Pattern-Based Invalidation

Invalidate caches by pattern (directory, extension, etc.).

```python
def invalidate_directory(dir_path: str):
    """Invalidate all caches for files in directory."""
    # Get all files in directory
    files = []
    for root, _, filenames in os.walk(dir_path):
        for filename in filenames:
            files.append(os.path.join(root, filename))
    
    # Invalidate
    cache.smart_invalidation(files)
    for file_path in files:
        meta_cache.remove(file_path)
        hash_cache.remove_hash(file_path)
```

### 5. Selective Invalidation

Invalidate only specific cache types.

```python
def invalidate_metadata_only(file_paths: list[str]):
    """Invalidate only metadata cache."""
    for file_path in file_paths:
        meta_cache.remove(file_path)
        # Keep hash cache intact

def invalidate_hashes_only(file_paths: list[str]):
    """Invalidate only hash cache."""
    for file_path in file_paths:
        hash_cache.remove_hash(file_path)
        # Keep metadata cache intact
```

---

## Performance Tuning

### Memory Cache Size

```python
# Default: 1000 items
cache = AdvancedCacheManager(memory_cache_size=1000)

# For large datasets: increase size
cache = AdvancedCacheManager(memory_cache_size=5000)

# For limited memory: decrease size
cache = AdvancedCacheManager(memory_cache_size=500)
```

### Disk Cache Threshold

```python
# Default: 1MB
cache.compression_threshold = 1024 * 1024

# Store more to disk: lower threshold
cache.compression_threshold = 512 * 1024  # 512KB

# Store less to disk: raise threshold
cache.compression_threshold = 5 * 1024 * 1024  # 5MB
```

### Batch Operations

Use batch operations for better performance:

```python
# BAD: Individual queries
for file_path in file_paths:
    if meta_cache.has(file_path):
        metadata = meta_cache.get(file_path)

# GOOD: Batch query
entries = meta_cache.get_entries_batch(file_paths)
for file_path, entry in entries.items():
    if entry:
        metadata = entry.data
```

### Cache Preloading

Preload cache for known file sets:

```python
def preload_cache(file_paths: list[str]):
    """Preload cache for multiple files."""
    # Batch query existing data
    entries = meta_cache.get_entries_batch(file_paths)
    hashes = hash_cache.get_files_with_hash_batch(file_paths)
    
    logger.info(f"Preloaded: {len(entries)} metadata, {len(hashes)} hashes")
```

---

## Troubleshooting Guide

### Problem 1: Low Cache Hit Rate

**Symptoms:**
- Performance slower than expected
- High cache miss rate in statistics

**Diagnosis:**
```python
stats = cache.get_stats()
if stats["memory_cache"]["hit_rate"] < 50:
    print("Low hit rate detected!")
```

**Solutions:**

1. **Increase memory cache size:**
```python
cache = AdvancedCacheManager(memory_cache_size=2000)
```

2. **Check cache invalidation frequency:**
```python
# Don't invalidate too often
cache.smart_invalidation(changed_files)  # Only changed files
```

3. **Use batch operations:**
```python
# Reduce cache misses with batch queries
entries = meta_cache.get_entries_batch(file_paths)
```

### Problem 2: High Memory Usage

**Symptoms:**
- Application using too much RAM
- System slowdowns

**Diagnosis:**
```python
stats = meta_cache.get_cache_stats()
print(f"Memory entries: {stats['memory_entries']}")

import sys
cache_size = sys.getsizeof(meta_cache._memory_cache)
print(f"Cache size: {cache_size / (1024*1024):.2f} MB")
```

**Solutions:**

1. **Clear memory cache:**
```python
meta_cache.clear()
hash_cache.clear_memory_cache()
```

2. **Reduce cache size:**
```python
cache = AdvancedCacheManager(memory_cache_size=500)
```

3. **Use auto-optimization:**
```python
cache.optimize_cache_size()  # Automatic reduction
```

### Problem 3: Stale Cache Data

**Symptoms:**
- Metadata not updating after file changes
- Hash mismatches

**Diagnosis:**
```python
# Check if cache has outdated data
cached_metadata = meta_cache.get(file_path)
current_metadata = load_metadata(file_path)

if cached_metadata != current_metadata:
    print("Stale cache detected!")
```

**Solutions:**

1. **Invalidate after file operations:**
```python
def rename_file(old_path: str, new_path: str):
    os.rename(old_path, new_path)
    
    # Invalidate old path
    meta_cache.remove(old_path)
    hash_cache.remove_hash(old_path)
    cache.smart_invalidation([old_path])
```

2. **Check file modification time:**
```python
def is_cache_valid(file_path: str) -> bool:
    """Check if cached metadata is still valid."""
    entry = meta_cache.get_entry(file_path)
    if not entry:
        return False
    
    file_mtime = os.path.getmtime(file_path)
    return entry.timestamp > file_mtime
```

### Problem 4: Database Errors

**Symptoms:**
- SQLite errors in logs
- Cache operations failing

**Diagnosis:**
```python
from core.database_manager import get_database_manager

db = get_database_manager()
# Check database health
```

**Solutions:**

1. **Reinitialize database:**
```python
# Close and reopen database connection
db._close_connection()
db = get_database_manager()
```

2. **Clear corrupted cache:**
```python
# Remove cache database file
import os
cache_db = os.path.expanduser("~/.local/share/oncutf/oncutf.db")
if os.path.exists(cache_db):
    os.remove(cache_db)
    # Restart application
```

### Problem 5: Disk Cache Growing Too Large

**Symptoms:**
- Disk space usage increasing
- Many .cache files in cache directory

**Diagnosis:**
```python
stats = cache.get_stats()
print(f"Disk cache size: {stats['disk_cache']['cache_size_mb']:.2f} MB")
print(f"Cache files: {stats['disk_cache']['cache_files']}")
```

**Solutions:**

1. **Clear disk cache:**
```python
cache.disk_cache.clear()
```

2. **Increase threshold to reduce disk usage:**
```python
cache.compression_threshold = 5 * 1024 * 1024  # 5MB
```

3. **Manual cleanup of old cache files:**
```python
import os
import time

cache_dir = os.path.expanduser("~/.oncutf/cache")
now = time.time()

for filename in os.listdir(cache_dir):
    if filename.endswith(".cache"):
        file_path = os.path.join(cache_dir, filename)
        # Remove files older than 7 days
        if now - os.path.getmtime(file_path) > 7 * 86400:
            os.remove(file_path)
```

---

## Best Practices

### 1. Always Check Cache First

```python
# GOOD
if meta_cache.has(file_path):
    metadata = meta_cache.get(file_path)
else:
    metadata = load_metadata(file_path)
    meta_cache.set(file_path, metadata)

# BAD - Always loading from disk
metadata = load_metadata(file_path)
```

### 2. Use Batch Operations

```python
# GOOD - Single batch query
entries = meta_cache.get_entries_batch(file_paths)

# BAD - Multiple individual queries
for file_path in file_paths:
    entry = meta_cache.get_entry(file_path)
```

### 3. Invalidate After Modifications

```python
# GOOD - Invalidate after change
os.rename(old_path, new_path)
meta_cache.remove(old_path)
hash_cache.remove_hash(old_path)

# BAD - No invalidation
os.rename(old_path, new_path)
# Cache now has stale data!
```

### 4. Monitor Cache Performance

```python
# GOOD - Regular monitoring
def log_cache_stats():
    meta_stats = meta_cache.get_cache_stats()
    hash_stats = hash_cache.get_cache_stats()
    cache_stats = cache.get_stats()
    
    logger.info(f"Metadata cache hit rate: {meta_stats['hit_rate_percent']:.2f}%")
    logger.info(f"Hash cache hit rate: {hash_stats['hit_rate_percent']:.2f}%")
    logger.info(f"Advanced cache hit rate: {cache_stats['overall_hit_rate']:.2f}%")

# Call periodically
```

### 5. Use Global Instances

```python
# GOOD - Single global instance
meta_cache = get_persistent_metadata_cache()

# BAD - Creating new instances
meta_cache = PersistentMetadataCache()  # Don't do this!
```

### 6. Handle Cache Errors Gracefully

```python
# GOOD - Graceful fallback
try:
    metadata = meta_cache.get(file_path)
except Exception as e:
    logger.warning(f"Cache error: {e}")
    metadata = load_metadata(file_path)  # Fallback

# BAD - No error handling
metadata = meta_cache.get(file_path)  # May crash
```

### 7. Clear Cache Periodically

```python
# GOOD - Periodic cleanup
def cleanup_old_cache():
    """Clear cache for files that no longer exist."""
    # Implementation depends on your needs
    pass

# Schedule cleanup
# e.g., on application shutdown or weekly
```

### 8. Use Appropriate Cache Types

```python
# GOOD - Right cache for the job
# Small, frequently accessed data
cache.memory_cache.set(key, small_data)

# Large datasets
cache.disk_cache.set(key, large_data)

# Persistent metadata
meta_cache.set(file_path, metadata)

# Persistent hashes
hash_cache.store_hash(file_path, hash_value)
```

---

## Cache Performance Metrics

### Expected Performance

| Operation | Without Cache | With Cache | Speedup |
|-----------|---------------|------------|---------|
| Metadata load | ~50ms | ~0.1ms | 500x |
| Hash calculation | ~30ms | ~0.1ms | 300x |
| Batch query (100 files) | ~5s | ~0.5s | 10x |
| Duplicate detection | ~30s | ~1s | 30x |

### Memory Usage

| Cache Type | Typical Size | Max Size |
|------------|--------------|----------|
| Memory Cache (LRU) | 10-50 MB | 100 MB |
| Metadata Cache | 20-100 MB | 500 MB |
| Hash Cache | 5-20 MB | 100 MB |
| Disk Cache | 50-200 MB | 1 GB |

### Hit Rate Targets

| Cache Type | Good | Excellent |
|------------|------|-----------|
| Memory Cache (LRU) | > 70% | > 90% |
| Metadata Cache | > 80% | > 95% |
| Hash Cache | > 75% | > 90% |
| Disk Cache | > 60% | > 80% |

---

## Summary

OnCutF's cache system provides:

✅ **Multi-layered caching** (memory + disk + database)  
✅ **Persistent storage** (survives application restarts)  
✅ **High performance** (500x speedup for cached operations)  
✅ **Automatic management** (LRU eviction, expiry, cleanup)  
✅ **Smart invalidation** (pattern-based, selective)  
✅ **Batch operations** (efficient for large file sets)  
✅ **Statistics tracking** (hit rates, performance metrics)  

**Key Takeaways:**

1. Always check cache before expensive operations
2. Use batch operations for multiple files
3. Invalidate cache after file modifications
4. Monitor cache hit rates regularly
5. Use appropriate cache types for different data
6. Handle cache errors gracefully

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-04  
**Status:** Complete ✅
