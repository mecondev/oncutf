# Database System Quick Start

## Overview

The oncutf application now includes a comprehensive database system that provides:

- **Persistent Metadata Storage**: Metadata storage that persists between sessions
- **Hash Caching**: Persistent caching of CRC32 hashes for improved performance
- **Rename History**: Undo/redo functionality for rename operations
- **Enhanced Performance**: Memory caching with database fallback

## Core Features

### 🗄️ Persistent Storage
- All metadata and hashes are stored permanently
- Fast access with memory caching
- Automatic maintenance and cleanup

### ↩️ Undo Functionality
- Complete tracking of rename operations
- Undo with validation and integrity checking
- Batch operations support

### ⚡ Performance
- Thread-safe operations
- Connection pooling
- Optimized database queries
- Lazy loading with smart caching

## Usage

### Automatic Activation
The database system is automatically activated when the application starts. No configuration required.

### Database Location
- **Linux**: `~/.local/share/oncutf/oncutf_data.db`
- **Windows**: `%APPDATA%/oncutf/oncutf_data.db`

### New Features

#### Command History & Undo/Redo
- Press `Ctrl+Y` to view command history dialog (shows all metadata operations)
- Press `Ctrl+Z` (global) to undo the last operation
- Press `Ctrl+Shift+Z` (global) to redo the last undone operation
- Shortcuts work throughout the application, not just in metadata tree
- Validation for safe undo operations

#### Database Statistics
- View database usage statistics
- Monitor cache performance
- Cleanup tools for old data

## Testing

To test the new system:

```bash
python scripts/test_database_system.py
```

This script:
- Creates test data
- Tests all functionality
- Verifies correct operation
- Cleans up temporary files

## Backward Compatibility

The new system is fully backward compatible:
- Existing code continues to work
- Old APIs are preserved
- Automatic migration from memory-only caches
- Graceful fallback in case of problems

## Troubleshooting

### Common Issues

1. **Database Locked**: Usually resolves automatically
2. **Permission Errors**: Check permissions on the data directory
3. **Performance Issues**: Use cleanup tools

### Debug Mode
```python
import logging
logging.getLogger('core.database_manager').setLevel(logging.DEBUG)
```

### Manual Reset
If there are problems:
1. Close the application
2. Delete the database file
3. Restart (a new database will be created)

## Related Documentation

- **Complete Technical Documentation**: [Database System](database_system.md)
- **Safe Rename Workflow**: [Safe Rename Workflow](safe_rename_workflow.md)
- **Case-Sensitive Renaming**: [Case-Sensitive Rename Guide](case_sensitive_rename_guide.md)
- **Configuration System**: [JSON Config System](json_config_system.md)
- **Test Suite**: [`tests/test_database_system.py`](../tests/test_database_system.py)
- **Demo Script**: [`scripts/test_database_system.py`](../scripts/test_database_system.py)

## Future Improvements

- Compression for large metadata
- Optional encryption
- Backup/restore functionality
- Cloud synchronization
- Export/import capabilities

---

The new database system provides a solid foundation for future extensions and improvements to the application!
