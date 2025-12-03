# Cache System Quick Reference

**OnCutF Cache Strategy - Quick Reference Card**  
**Version:** 1.0 | **Date:** 2025-12-04

---

## Initialization

```python
# Advanced cache
from core.advanced_cache_manager import AdvancedCacheManager
cache = AdvancedCacheManager(memory_cache_size=1000)

# Hash cache
from core.persistent_hash_cache import get_persistent_hash_cache
hash_cache = get_persistent_hash_cache()

# Metadata cache
from core.persistent_metadata_cache import get_persistent_metadata_cache
meta_cache = get_persistent_metadata_cache()
```

---

## Basic Operations

### Store Data

```python
cache.set(key, value)
hash_cache.store_hash(file_path, hash_value)
meta_cache.set(file_path, metadata, is_extended=True)
```

### Retrieve Data

```python
value = cache.get(key)
hash_value = hash_cache.get_hash(file_path)
metadata = meta_cache.get(file_path)
```

### Check Existence

```python
if key in cache: ...
if hash_cache.has_hash(file_path): ...
if meta_cache.has(file_path): ...
```

---

## Batch Operations

```python
# Get multiple entries at once
entries = meta_cache.get_entries_batch(file_paths)
hashes = hash_cache.get_files_with_hash_batch(file_paths)

# Process results
for file_path, entry in entries.items():
    if entry:
        metadata = entry.data
```

---

## Cache Statistics

```python
# Get performance stats
stats = cache.get_stats()
print(f"Hit rate: {stats['overall_hit_rate']:.2f}%")

stats = meta_cache.get_cache_stats()
print(f"Metadata hit rate: {stats['hit_rate_percent']:.2f}%")

stats = hash_cache.get_cache_stats()
print(f"Hash hit rate: {stats['hit_rate_percent']:.2f}%")
```

---

## Cache Invalidation

```python
# Clear memory cache
cache.memory_cache.clear()
meta_cache.clear()
hash_cache.clear_memory_cache()

# Clear all caches
cache.clear()  # Memory + disk

# Remove specific file
meta_cache.remove(file_path)
hash_cache.remove_hash(file_path)

# Smart invalidation (pattern-based)
changed_files = ["/path/file1.jpg", "/path/file2.mp4"]
cache.smart_invalidation(changed_files)
```

---

## Performance Tuning

```python
# Adjust memory cache size
cache = AdvancedCacheManager(memory_cache_size=2000)  # Larger
cache = AdvancedCacheManager(memory_cache_size=500)   # Smaller

# Adjust disk cache threshold
cache.compression_threshold = 512 * 1024      # 512KB (more to disk)
cache.compression_threshold = 5 * 1024 * 1024 # 5MB (less to disk)

# Auto-optimize
cache.optimize_cache_size()
```

---

## Common Patterns

### Pattern 1: Check Cache Before Load

```python
if meta_cache.has(file_path):
    metadata = meta_cache.get(file_path)  # Cache hit
else:
    metadata = load_metadata(file_path)    # Load from disk
    meta_cache.set(file_path, metadata)    # Store in cache
```

### Pattern 2: Batch Processing

```python
# Query cache in batch
entries = meta_cache.get_entries_batch(file_paths)

# Process cached and uncached separately
cached = [path for path, entry in entries.items() if entry]
uncached = [path for path, entry in entries.items() if not entry]

# Load only uncached files
for file_path in uncached:
    metadata = load_metadata(file_path)
    meta_cache.set(file_path, metadata)
```

### Pattern 3: Invalidate After Modification

```python
def rename_file(old_path: str, new_path: str):
    os.rename(old_path, new_path)
    
    # Invalidate caches
    meta_cache.remove(old_path)
    hash_cache.remove_hash(old_path)
    cache.smart_invalidation([old_path])
```

---

## Troubleshooting

### Low Hit Rate

```python
# Check stats
stats = meta_cache.get_cache_stats()
if stats['hit_rate_percent'] < 50:
    # Increase cache size
    cache = AdvancedCacheManager(memory_cache_size=2000)
```

### High Memory Usage

```python
# Clear memory cache
meta_cache.clear()
hash_cache.clear_memory_cache()

# Reduce cache size
cache.optimize_cache_size()
```

### Stale Data

```python
# Invalidate specific files
for file_path in modified_files:
    meta_cache.remove(file_path)
    hash_cache.remove_hash(file_path)
```

---

## Performance Targets

| Cache Type | Good Hit Rate | Excellent Hit Rate |
|------------|---------------|--------------------|
| Memory (LRU) | > 70% | > 90% |
| Metadata | > 80% | > 95% |
| Hash | > 75% | > 90% |
| Disk | > 60% | > 80% |

---

## Expected Performance

| Operation | Without Cache | With Cache | Speedup |
|-----------|---------------|------------|---------|
| Metadata load | ~50ms | ~0.1ms | 500x |
| Hash calculation | ~30ms | ~0.1ms | 300x |
| Batch query (100) | ~5s | ~0.5s | 10x |

---

## Best Practices

✅ Always check cache before expensive operations  
✅ Use batch operations for multiple files  
✅ Invalidate cache after file modifications  
✅ Monitor cache hit rates regularly  
✅ Use global instances (get_* functions)  
✅ Handle cache errors gracefully (try/except)  
✅ Clear cache periodically  
✅ Use appropriate cache types for different data  

---

## Documentation

📖 **Full documentation:** `docs/cache_strategy.md`  
📊 **Day 7 summary:** `docs/daily_progress/day_7_summary_2025-12-04.md`  
🎨 **Visualization:** `docs/daily_progress/day_7_visualization.md`  

---

**Quick Reference Version:** 1.0  
**Last Updated:** 2025-12-04
