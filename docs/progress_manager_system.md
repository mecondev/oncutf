# Progress Manager System

## Overview

The new ProgressManager system provides a unified API for progress tracking across all file operations in the ONCUTF application.

## Architecture

### ProgressManager Class

The `ProgressManager` is the main class that unifies all progress operations:

```python
from widgets.progress_manager import ProgressManager

# Create manager for hash operations
hash_manager = ProgressManager("hash", parent)

# Create manager for metadata operations
metadata_manager = ProgressManager("metadata", parent)

# Create manager for copy operations (future)
copy_manager = ProgressManager("copy", parent)
```

### Supported Operations

- **hash**: Size-based progress with real-time tracking for CRC32 calculations
- **metadata**: Count-based progress with optional size tracking for metadata loading
- **copy**: Size-based progress for file operations (future)

## API Reference

### Constructor

```python
ProgressManager(operation_type: str, parent: Optional[QWidget] = None)
```

**Parameters:**
- `operation_type`: Operation type ("hash", "metadata", "copy")
- `parent`: Parent widget (optional)

### Methods

#### start_tracking()

```python
start_tracking(total_size: int = 0, total_files: int = 0)
```

Starts progress tracking with the appropriate parameters.

**Parameters:**
- `total_size`: Total size in bytes (for size-based operations)
- `total_files`: Total number of files (for count-based operations)

#### update_progress()

```python
update_progress(file_count: int = 0, total_files: int = 0,
               processed_bytes: int = 0, total_bytes: int = 0,
               filename: str = "", status: str = "")
```

Updates progress with unified API.

**Parameters:**
- `file_count`: Current number of processed files
- `total_files`: Total number of files
- `processed_bytes`: Processed bytes (cumulative)
- `total_bytes`: Total size in bytes
- `filename`: Current filename
- `status`: Status message

#### reset()

```python
reset()
```

Resets progress tracking.

#### get_widget()

```python
get_widget() -> ProgressWidget
```

Returns the underlying progress widget.

#### is_tracking()

```python
is_tracking() -> bool
```

Checks if progress tracking is active.

## Factory Functions

For convenience, factory functions are provided:

```python
from widgets.progress_manager import (
    create_hash_progress_manager,
    create_metadata_progress_manager,
    create_copy_progress_manager
)

# Create managers
hash_manager = create_hash_progress_manager(parent)
metadata_manager = create_metadata_progress_manager(parent)
copy_manager = create_copy_progress_manager(parent)
```

## Usage Examples

### Hash Operations

```python
# Create manager
manager = ProgressManager("hash", parent)

# Start tracking
manager.start_tracking(total_size=1000000000)  # 1GB

# Update progress
manager.update_progress(
    processed_bytes=500000000,  # 500MB
    filename="large_file.mov",
    status="Calculating CRC32 hash..."
)
```

### Metadata Operations

```python
# Create manager
manager = ProgressManager("metadata", parent)

# Start tracking
manager.start_tracking(total_files=100, total_size=50000000)

# Update progress
manager.update_progress(
    file_count=50,
    total_files=100,
    processed_bytes=25000000,
    filename="photo.jpg",
    status="Loading metadata..."
)
```

### Copy Operations (Future)

```python
# Create manager
manager = ProgressManager("copy", parent)

# Start tracking
manager.start_tracking(total_size=500000000)  # 500MB

# Update progress
manager.update_progress(
    processed_bytes=250000000,  # 250MB
    filename="video.mp4",
    status="Copying file..."
)
```

## Migration Guide

### From the Old System

**Old:**
```python
from widgets.progress_widget import create_size_based_progress_widget

widget = create_size_based_progress_widget(parent)
widget.start_progress_tracking(total_size)
widget.update_progress(processed_bytes=bytes, total_bytes=total)
```

**New:**
```python
from widgets.progress_manager import create_hash_progress_manager

manager = create_hash_progress_manager(parent)
manager.start_tracking(total_size=total_size)
manager.update_progress(processed_bytes=bytes)
```

### Benefits

1. **Unified API**: One API for all operations
2. **Automatic Mode Selection**: Automatic mode selection based on operation type
3. **Better Error Handling**: Improved error handling and validation
4. **Future Ready**: Ready for new operations (copy, move, etc.)
5. **Cleaner Code**: Less duplicate code

## Related Documentation

- **Database System**: [Database Quick Start](database_quick_start.md) | [Database System](database_system.md)
- **Safe Rename Operations**: [Safe Rename Workflow](safe_rename_workflow.md)
- **Case-Sensitive Renaming**: [Case-Sensitive Rename Guide](case_sensitive_rename_guide.md)
- **Configuration**: [JSON Config System](json_config_system.md)
- **Module Documentation**: [oncutf Module Docstrings](oncutf_module_docstrings.md)

## Implementation Details

### Progress Widget Integration

The ProgressManager uses the existing ProgressWidget as backend:

- **Hash operations**: Uses size-based progress mode
- **Metadata operations**: Uses count-based progress mode with optional size tracking
- **Copy operations**: Uses size-based progress mode

### Throttling

Throttling is done at the ProgressWidget level for optimal performance:
- 50ms updates for small files
- 100ms updates for large files
- Real-time updates for files >100MB

### Thread Safety

The ProgressManager is thread-safe and can be used from worker threads.

## Testing

Tests are located in `tests/test_progress_manager.py`:

```bash
python -m pytest tests/test_progress_manager.py -v
```

## Future Enhancements

1. **Copy Operations**: Full support για file copy operations
2. **Move Operations**: Support για file move operations
3. **Batch Operations**: Support για batch file operations
4. **Custom Operations**: Support για custom operation types
5. **Progress Persistence**: Save/restore progress state
