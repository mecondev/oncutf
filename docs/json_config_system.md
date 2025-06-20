# JSON Configuration System Documentation

## Overview

The oncutf JSON configuration system is a comprehensive configuration management solution that uses JSON files for storing and loading user settings and application state.

## Features

- **Multiple configuration categories**: Window, File Hashes, App configuration
- **Automatic backup creation**: Creates backup files before saving
- **Thread-safe operations**: Safe for use in multi-threaded environments
- **Default values**: Predefined default values for all settings
- **Cross-platform**: Works on Windows and Linux
- **Generic design**: Can be extended for any application needs

## File Structure

The configuration file is stored at:
- **Linux**: `~/.config/oncutf/config.json`
- **Windows**: `%APPDATA%/oncutf/config.json`

## Configuration Categories

### 1. Window Configuration
```json
{
  "window": {
    "geometry": {"x": 100, "y": 100, "width": 1200, "height": 900},
    "window_state": "normal",
    "splitter_states": {
      "horizontal": [250, 674, 250],
      "vertical": [500, 300]
    },
    "column_widths": {
      "file_table": [23, 345, 80, 60, 130],
      "metadata_tree": [180, 500]
    },
    "last_folder": "",
    "recursive_mode": false,
    "sort_column": 1,
    "sort_order": 0
  }
}
```

### 2. File Hash Configuration
```json
{
  "file_hashes": {
    "enabled": true,
    "algorithm": "sha256",
    "cache_size_limit": 10000,
    "auto_cleanup_days": 30,
    "hashes": {
      "/path/to/file.jpg": {
        "hash": "abc123def456",
        "timestamp": "2025-06-20T21:26:56.733254",
        "size": 1024000
      }
    }
  }
}
```

### 3. App Configuration
```json
{
  "app": {
    "theme": "dark",
    "language": "en",
    "auto_save_config": true,
    "recent_folders": ["/path/to/recent/folder"]
  }
}
```

## Usage

### Basic Usage
```python
from utils.json_config_manager import get_app_config_manager

# Get the config manager
config = get_app_config_manager()

# Read configuration value
window_config = config.get_category('window')
window_width = window_config.get('geometry')['width']

# Save configuration value
window_config.set('window_state', 'maximized')

# Save to file
config.save()
```

### File Hash Management
```python
# Add file hash
file_hash_config = config.get_category('file_hashes')
file_hash_config.add_file_hash('/path/to/file.jpg', 'sha256_hash', 1024000)

# Get file hash
hash_info = file_hash_config.get_file_hash('/path/to/file.jpg')
if hash_info:
    print(f"Hash: {hash_info['hash']}")
    print(f"Size: {hash_info['size']}")
```

### Recent Folders Management
```python
# Add recent folder
app_config = config.get_category('app')
app_config.add_recent_folder('/path/to/folder')

# Get recent folders
recent = app_config.get('recent_folders', [])
```

## MainWindow Integration

The JSON configuration system is fully integrated into the MainWindow:

### On Startup
1. Loads configuration from JSON file
2. Applies window geometry
3. Restores splitter states
4. Restores column widths

### On Shutdown
1. Saves current window geometry
2. Saves splitter states
3. Saves column widths
4. Saves last folder and settings

## MainWindow Methods

### `_load_window_config()`
Loads and applies window configuration on startup.

### `_save_window_config()`
Saves current window state on shutdown.

### `_apply_loaded_config()`
Applies UI configuration after interface initialization.

### `restore_last_folder_if_available()`
Restores the last folder if available and accessible.

## Backup Files

The system automatically creates backup files:
- `config.backup.json` - Backup copy
- Automatic restoration in case of errors

## Thread Safety

The JSON configuration system is thread-safe using `threading.RLock()` for data protection.

## Extension

To add new configuration categories:

1. Create a new class inheriting from `ConfigCategory`
2. Register it with the `JSONConfigManager` using `register_category()`
3. The `load()` and `save()` methods handle it automatically

## Usage Examples

### Creating Custom Categories
```python
class MyCustomConfig(ConfigCategory):
    def __init__(self):
        defaults = {
            'setting1': 'default_value',
            'setting2': 42
        }
        super().__init__('my_custom', defaults)

# Register the category
config_manager = JSONConfigManager('my_app')
config_manager.register_category(MyCustomConfig())
```

### Debugging
```python
# Show configuration info
info = config.get_config_info()
print(info)

# Display file content
import json
with open(config.config_file, 'r') as f:
    content = json.load(f)
print(json.dumps(content, indent=2))
```

## Troubleshooting

### Loading Errors
- Validates JSON file format
- Automatic restoration from backup
- Uses default values on error

### Saving Errors
- Creates backup before saving
- Uses temporary file for atomic operations
- Detailed logging for debugging
