# Database System Documentation

## Overview

The oncutf application now includes a comprehensive database system for persistent storage of metadata, file hashes, and rename history. This system provides enhanced performance, data persistence, and undo/redo functionality.

## Architecture

### Core Components

1. **DatabaseManager** (`core/database_manager.py`)
   - SQLite backend for persistent storage
   - Thread-safe operations with connection pooling
   - Automatic schema migrations
   - Manages three main data types: files, metadata, hashes, and rename history

2. **PersistentMetadataCache** (`core/persistent_metadata_cache.py`)
   - Drop-in replacement for the original MetadataCache
   - Automatic database persistence of metadata
   - Memory cache for performance with database fallback
   - Maintains existing API for backward compatibility

3. **PersistentHashCache** (`core/persistent_hash_cache.py`)
   - Persistent storage of file hashes (CRC32)
   - Enhanced duplicate detection capabilities
   - Integration with existing hash operations
   - Support for multiple hash algorithms

4. **RenameHistoryManager** (`core/rename_history_manager.py`)
   - Tracks rename operations for undo/redo functionality
   - Batch operation recording and rollback
   - Operation validation and integrity checking
   - User-friendly undo interface

## Database Schema

### Files Table
```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    file_size INTEGER,
    modified_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Metadata Table
```sql
CREATE TABLE metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    metadata_type TEXT NOT NULL DEFAULT 'fast',  -- 'fast' or 'extended'
    metadata_json TEXT NOT NULL,  -- JSON blob of metadata
    is_modified BOOLEAN DEFAULT FALSE,  -- User modifications flag
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
);
```

### Hashes Table
```sql
CREATE TABLE hashes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    algorithm TEXT NOT NULL DEFAULT 'CRC32',
    hash_value TEXT NOT NULL,
    file_size_at_hash INTEGER,  -- File size when hash was calculated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
);
```

### Rename History Table
```sql
CREATE TABLE rename_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL,  -- UUID for grouping related renames
    file_id INTEGER NOT NULL,
    old_path TEXT NOT NULL,
    new_path TEXT NOT NULL,
    old_filename TEXT NOT NULL,
    new_filename TEXT NOT NULL,
    operation_type TEXT NOT NULL DEFAULT 'rename',  -- 'rename', 'undo', 'redo'
    modules_data TEXT,  -- JSON of modules used for this rename
    post_transform_data TEXT,  -- JSON of post-transform settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
);
```

## Usage

### Initialization

The database system is automatically initialized when the main window starts:

```python
from core.database_manager import initialize_database
from core.persistent_metadata_cache import get_persistent_metadata_cache
from core.persistent_hash_cache import get_persistent_hash_cache
from core.rename_history_manager import get_rename_history_manager

# Initialize database system
db_manager = initialize_database()

# Get persistent caches
metadata_cache = get_persistent_metadata_cache()
hash_cache = get_persistent_hash_cache()
rename_history = get_rename_history_manager()
```

### Metadata Operations

The persistent metadata cache maintains the same API as the original cache:

```python
# Store metadata
metadata_cache.set(file_path, metadata_dict, is_extended=True)

# Retrieve metadata
metadata = metadata_cache.get(file_path)

# Check if metadata exists
if metadata_cache.has(file_path):
    print("Metadata available")

# Get metadata entry with flags
entry = metadata_cache.get_entry(file_path)
if entry:
    print(f"Extended: {entry.is_extended}, Modified: {entry.modified}")
```

### Hash Operations

Enhanced hash caching with persistence:

```python
# Store hash
hash_cache.store_hash(file_path, hash_value, 'CRC32')

# Retrieve hash
hash_value = hash_cache.get_hash(file_path, 'CRC32')

# Find duplicates
duplicates = hash_cache.find_duplicates(file_paths_list)

# Verify file integrity
is_valid = hash_cache.verify_file_integrity(file_path)
```

### Rename History

Track and undo rename operations:

```python
# Record a rename batch
operation_id = rename_history.record_rename_batch(
    renames=[(old_path, new_path), ...],
    modules_data=modules_config,
    post_transform_data=transform_config
)

# Get recent operations
operations = rename_history.get_recent_operations(limit=20)

# Check if operation can be undone
can_undo, reason = rename_history.can_undo_operation(operation_id)

# View complete history: Press Ctrl+Y for command history dialog
# Undo last operation: Press Ctrl+Z (global shortcut)
# Redo last operation: Press Ctrl+Shift+Z (global shortcut)

# Undo operation
if can_undo:
    success, message, files_processed = rename_history.undo_operation(operation_id)
```

## Features

### Performance Optimizations

1. **Memory Cache Layer**: Hot cache in memory for frequently accessed data
2. **Connection Pooling**: Thread-safe database connections with automatic cleanup
3. **Lazy Loading**: Database queries only when memory cache misses
4. **Batch Operations**: Efficient bulk operations for large datasets

### Data Integrity

1. **Foreign Key Constraints**: Ensures referential integrity
2. **Transaction Support**: Atomic operations with rollback on errors
3. **Schema Migrations**: Automatic database schema updates
4. **Orphaned Record Cleanup**: Removes stale data for non-existent files

### Backward Compatibility

1. **Drop-in Replacement**: Existing code works without modification
2. **Legacy API Support**: Maintains all original method signatures
3. **Graceful Fallback**: Falls back to memory-only cache if database unavailable
4. **Migration Support**: Seamlessly migrates from old cache system

## Configuration

### Database Location

The database is stored in the user's data directory:

- **Windows**: `%APPDATA%/oncutf/oncutf_data.db`
- **Linux/macOS**: `~/.local/share/oncutf/oncutf_data.db`

### Custom Database Path

You can specify a custom database path during initialization:

```python
db_manager = initialize_database("/custom/path/to/database.db")
```

### Performance Tuning

The database uses several SQLite optimizations:

- **WAL Mode**: Better concurrency for read/write operations
- **Foreign Keys**: Enabled for referential integrity
- **Indexes**: Optimized indexes on frequently queried columns
- **Connection Timeout**: 30-second timeout for busy databases

## Maintenance

### Database Statistics

Get information about database usage:

```python
stats = db_manager.get_database_stats()
print(f"Files: {stats['files']}")
print(f"Metadata: {stats['metadata']}")
print(f"Hashes: {stats['hashes']}")
print(f"History: {stats['rename_history']}")
```

### Cache Statistics

Monitor cache performance:

```python
# Metadata cache stats
metadata_stats = metadata_cache.get_cache_stats()
print(f"Hit rate: {metadata_stats['hit_rate_percent']}%")

# Hash cache stats
hash_stats = hash_cache.get_cache_stats()
print(f"Memory cache size: {hash_stats['memory_cache_size']}")
```

### Cleanup Operations

Remove orphaned records:

```python
# Cleanup database
cleaned_count = db_manager.cleanup_orphaned_records()
print(f"Cleaned {cleaned_count} orphaned records")

# Cleanup old history
history_cleaned = rename_history.cleanup_old_history(days_to_keep=30)
print(f"Cleaned {history_cleaned} old history records")
```

## User Interface

### Rename History Dialog

A user-friendly dialog for viewing and managing rename history:

```python
from widgets.rename_history_dialog import show_rename_history_dialog

# Show the dialog
show_rename_history_dialog(parent_window)
```

The dialog provides:
- List of recent rename operations
- Detailed view of each operation
- Undo functionality with validation
- Operation status and file counts
- Cleanup tools for old history

### Menu Integration

Database management features can be accessed through:
- Tools menu (if available)
- Context menus
- Keyboard shortcuts (Ctrl+Z for undo, Ctrl+Shift+Z for redo, Ctrl+Y for history)
- Status indicators

## Migration from Old System

The new database system is designed to seamlessly replace the old memory-only caches:

1. **Automatic Migration**: Existing metadata and hashes are preserved
2. **No Code Changes**: Existing code continues to work
3. **Enhanced Features**: New features become available immediately
4. **Performance Improvement**: Better performance with persistence

## Error Handling

The system includes comprehensive error handling:

1. **Database Errors**: Graceful fallback to memory-only operation
2. **File System Errors**: Proper handling of missing files
3. **Corruption Recovery**: Automatic schema recreation if needed
4. **Thread Safety**: Safe concurrent access from multiple threads

## Testing

Comprehensive test suite covers:

- Database schema creation and migration
- Metadata storage and retrieval
- Hash caching and duplicate detection
- Rename history recording and undo
- Error conditions and edge cases
- Performance characteristics

Run tests with:
```bash
python -m pytest tests/test_database_system.py -v
```

## Future Enhancements

Planned improvements include:

1. **Compression**: Compress large metadata blobs
2. **Encryption**: Optional encryption for sensitive metadata
3. **Backup/Restore**: Database backup and restore functionality
4. **Analytics**: Usage analytics and performance metrics
5. **Cloud Sync**: Optional cloud synchronization of data
6. **Export/Import**: Export data to various formats

## Troubleshooting

### Common Issues

1. **Database Locked**: Usually resolves automatically with retry
2. **Permission Errors**: Check write permissions to data directory
3. **Corruption**: Database will be recreated automatically
4. **Performance**: Monitor cache hit rates and cleanup orphaned records

### Debug Information

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('core.database_manager').setLevel(logging.DEBUG)
```

### Manual Recovery

If database issues persist:

1. Close the application
2. Delete the database file
3. Restart the application (database will be recreated)
4. Note: This will lose all stored metadata and history

## Related Documentation

- **Quick Start Guide**: [Database Quick Start](database_quick_start.md)
- **Progress Tracking**: [Progress Manager System](progress_manager_system.md)
- **Safe Operations**: [Safe Rename Workflow](safe_rename_workflow.md)
- **Case-Sensitive Renaming**: [Case-Sensitive Rename Guide](case_sensitive_rename_guide.md)
- **Configuration**: [JSON Config System](json_config_system.md)
- **Module Reference**: [oncutf Module Docstrings](oncutf_module_docstrings.md)
