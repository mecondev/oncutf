# OnCutF Application Workflow Documentation

## Description

This document describes the complete flow of the OnCutF application from initialization to rename operation execution, including metadata processing, database operations, and rename modules functionality.

## 1. Application Startup

### 1.1 main.py - Entry Point
```python
def main():
    # Enable High DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    # Create QApplication
    app = QApplication(sys.argv)

    # Initialize theme, fonts, and splash screen
    theme_manager = ThemeEngine()
    splash = CustomSplashScreen()

    # Create main window
    window = MainWindow()

    # Apply theme and show window
    theme_manager.apply_complete_theme(app, window)
    window.show()
```

### 1.2 MainWindow.__init__() - Core Initialization

#### A. Core Context & Services
```python
# --- Core Application Context ---
self.context = ApplicationContext.create_instance(parent=self)

# --- Database System Initialization (V3 Architecture) ---
self.db_manager = initialize_database()
```

#### B. Cache Systems
```python
# Persistent caches that save data between sessions
self.metadata_cache = get_persistent_metadata_cache()
self.hash_cache = get_persistent_hash_cache()
```

#### C. Managers Initialization
```python
# Core managers for various functionalities
self.file_load_manager = FileLoadManager(self)
self.metadata_manager = MetadataManager(self)
self.rename_manager = RenameManager(self)
self.table_manager = TableManager(self)
# ... other managers
```

### 1.3 Debug Reset Features

If debug options are enabled in `config.py`:

```python
# config.py
DEBUG_RESET_DATABASE = True  # Deletes database on startup
DEBUG_RESET_CONFIG = True    # Deletes config.json on startup
```

- **Database Reset**: `DatabaseManager.__init__()` checks the flag and deletes the database
- **Config Reset**: `JSONConfigManager.load()` checks the flag and deletes config.json

## 2. Database Architecture (V3 Schema)

### 2.1 Database Tables

#### Core Tables:
1. **`file_paths`** - Central file registry
2. **`file_metadata`** - Raw metadata from ExifTool
3. **`file_hashes`** - File checksums (CRC32, etc.)
4. **`file_rename_history`** - Rename operations history

#### Structured Metadata Tables (V3):
5. **`metadata_categories`** - Metadata categories (Image, Camera, Video, etc.)
6. **`metadata_fields`** - Metadata field definitions with data types
7. **`file_metadata_structured`** - Structured metadata values

### 2.2 Default Metadata Schema

The application automatically creates 7 categories with 37 fields:

1. **File Information** (6 fields): Filename, Size, Modified Date, etc.
2. **Image Properties** (6 fields): Width, Height, Orientation, etc.
3. **Camera & Device** (9 fields): Make, Model, ISO, F-Number, etc.
4. **Video Properties** (5 fields): Duration, Frame Rate, Codec, etc.
5. **Audio Properties** (4 fields): Channels, Sample Rate, etc.
6. **Location & GPS** (4 fields): Latitude, Longitude, etc.
7. **Technical Details** (3 fields): ExifTool Version, Permissions, etc.

## 3. File Import System

### 3.1 Import Methods

#### A. Browse Button
```python
MainWindow.handle_browse() →
ApplicationService.handle_browse() →
FileLoadManager.load_files_from_paths()
```

#### B. Folder Import Button
```python
MainWindow.handle_folder_import() →
ApplicationService.handle_folder_import() →
FileLoadManager.load_folder()
```

#### C. Drag & Drop
```python
# Drag to File Tree or File Table
FileLoadManager.load_files_from_dropped_items() →
FileLoadManager.load_single_item_from_drop()
```

### 3.2 File Loading Process

#### A. FileLoadManager.load_folder()
```python
def load_folder(folder_path, merge_mode=False, recursive=False):
    # 1. Cleanup any active drag state
    if is_dragging():
        force_cleanup_drag()

    # 2. Fast file scanning with os.walk()
    file_paths = self._get_files_from_folder(folder_path, recursive)

    # 3. Update UI with files
    self._update_ui_with_files(file_paths, clear=not merge_mode)
```

#### B. File Item Creation
```python
# Create FileItem objects
items = [FileItem(path) for path in file_paths]

# Update FileTableModel
self.file_model.populate_from_items(items)
```

### 3.3 Modifier Keys Support

- **No Modifiers**: Normal load
- **Ctrl**: Recursive folder loading
- **Shift**: Merge mode (doesn't clear existing files)
- **Ctrl+Shift**: Recursive + Merge

## 4. Metadata Loading System

### 4.1 Metadata Loading Triggers

#### A. Automatic Loading
- Double-click on file
- File selection changes
- Drag & drop with metadata enabled

#### B. Manual Loading
- **F2**: Load basic metadata for selected files
- **F3**: Load extended metadata for selected files
- **Ctrl+F2**: Load basic metadata for all files
- **Ctrl+F3**: Load extended metadata for all files

### 4.2 Metadata Loading Process

#### A. MetadataManager.load_metadata_for_items()
```python
def load_metadata_for_items(items, use_extended=False, source="unknown"):
    # 1. Filter files that need metadata
    files_to_load = [item for item in items if not self._has_cached_metadata(item)]

    # 2. Choose loading mode
    loading_mode = self.determine_loading_mode(len(files_to_load), use_extended)

    # 3. Single file: Wait cursor
    if loading_mode == "single_file_wait_cursor":
        self._load_single_file_with_wait_cursor(items[0])

    # 4. Multiple files: Progress dialog with worker thread
    else:
        self._load_files_with_worker(files_to_load, use_extended)
```

#### B. Metadata Worker (Background Thread)
```python
# widgets/metadata_worker.py
class MetadataWorker(QObject):
    def run(self):
        for file_path in self.file_paths:
            # Load metadata with ExifTool
            metadata = self.exiftool_wrapper.get_metadata(file_path)

            # Store in database
            self.db_manager.store_metadata(file_path, metadata)

            # Process structured metadata
            self.structured_metadata_manager.process_and_store_metadata(file_path, metadata)

            # Emit progress signal
            self.progress.emit(current_index, total_files)
```

### 4.3 Metadata Processing Pipeline

#### A. Raw Metadata Storage
```python
# Store original ExifTool output
db_manager.store_metadata(file_path, raw_metadata, is_extended=True)
```

#### B. Structured Metadata Processing
```python
# Process and categorize metadata
structured_manager.process_and_store_metadata(file_path, raw_metadata)

# Example structured data:
{
    "file_basic": {
        "Filename": "IMG_1234.jpg",
        "File Size": "2.5 MB",
        "Modified Date": "2024-01-15 14:30:00"
    },
    "image": {
        "Width": "1920 pixels",
        "Height": "1080 pixels",
        "Orientation": "Horizontal"
    },
    "camera": {
        "Make": "Canon",
        "Model": "EOS 5D Mark IV",
        "ISO": "400",
        "F-Number": "f/2.8"
    }
}
```

### 4.4 Metadata Display

#### A. Metadata Tree View
```python
# widgets/metadata_tree_view.py
def display_metadata_for_file(file_item):
    # 1. Try structured metadata first
    if self._try_structured_metadata_loading(file_path):
        return

    # 2. Fallback to raw metadata
    self._load_raw_metadata(file_path)

def display_structured_metadata(structured_data):
    # Organize metadata in categories
    for category_name, fields in structured_data.items():
        category_item = QTreeWidgetItem([category_name, ""])

        for field_name, field_value in fields.items():
            field_item = QTreeWidgetItem([field_name, field_value])
            category_item.addChild(field_item)
```

#### B. Dynamic File Table Columns
```python
# Metadata fields can be added as table columns
# Context menu: "Add/Remove from File View"
metadata_tree_view.show_context_menu() →
self.column_manager.toggle_metadata_column(field_key)
```

## 5. Rename System Architecture

### 5.1 Rename Modules

The application uses a modular rename system:

#### A. Available Modules
- **CounterModule**: Add counters (001, 002, etc.)
- **MetadataModule**: Use metadata values in filenames
- **NameTransformModule**: Text transformations (uppercase, lowercase, etc.)
- **OriginalNameModule**: Use original filename
- **SpecifiedTextModule**: Add custom text
- **TextRemovalModule**: Remove text patterns

#### B. Module Configuration
```python
# Each module has configuration data
module_data = {
    "type": "metadata",
    "field": "DateTimeOriginal",
    "category": "metadata_keys",
    "max_length": 50
}

# Modules are applied in sequence
result = module.apply_from_data(module_data, file_item, metadata_cache)
```

### 5.2 Rename Process Flow

#### A. Preview Generation
```python
MainWindow.generate_preview_names():
    # 1. Get identity name pairs from modules
    name_pairs = self.get_identity_name_pairs()

    # 2. Update preview tables
    self.update_preview_tables_from_pairs(name_pairs)

    # 3. Validate new names
    for old_name, new_name in name_pairs:
        validation_result = validate_filename(new_name)
        # Set preview status (valid/invalid/duplicate/unchanged)
```

#### B. Rename Execution
```python
MainWindow.rename_files():
    # 1. Validate all names
    validation_results = self.validate_all_names()

    # 2. Check for conflicts
    conflicts = self.check_rename_conflicts()

    # 3. Execute rename with FileOperationsManager
    renamed_count = self.file_operations_manager.rename_files(rename_plan)

    # 4. Update database
    self.db_manager.store_rename_history(operation_data)

    # 5. Reload current folder
    self.reload_current_folder()
```

### 5.3 Safe Rename Workflow

#### A. Conflict Resolution
```python
# widgets/rename_conflict_resolver.py
class RenameConflictResolver:
    def resolve_conflicts(self, conflicts):
        # 1. Show dialog with options
        # 2. User chooses: Skip, Overwrite, Rename with suffix
        # 3. Return updated rename plan
```

#### B. Rename History
```python
# Store in database for undo functionality
rename_history_data = {
    "operation_id": unique_id,
    "old_path": original_path,
    "new_path": new_path,
    "modules_data": module_configurations,
    "timestamp": current_time
}
```

## 6. Caching & Performance

### 6.1 Persistent Caches

#### A. Metadata Cache
```python
# core/persistent_metadata_cache.py
class PersistentMetadataCache:
    # Caches metadata results between sessions
    # Key: file_path → Value: metadata_dict
    # Stored in database table: file_metadata
```

#### B. Hash Cache
```python
# core/persistent_hash_cache.py
class PersistentHashCache:
    # Caches file checksums between sessions
    # Key: file_path → Value: hash_value
    # Stored in database table: file_hashes
```

### 6.2 Memory Management

#### A. Lazy Loading
- Metadata is loaded only when needed
- Structured metadata is created on-demand

#### B. Cache Invalidation
- File modification time checking
- Automatic cleanup for old entries

## 7. UI Components & Interaction

### 7.1 Main Window Layout

```
┌─────────────────────────────────────────────────────────────┐
│ MenuBar & Toolbar                                           │
├─────────────┬─────────────────────────┬─────────────────────┤
│ File Tree   │ File Table              │ Metadata Tree       │
│             │ ┌─────────────────────┐   │                     │
│             │ │ Rename Modules      │   │                     │
│             │ └─────────────────────┘   │                     │
│             │ ┌─────────────────────┐   │                     │
│             │ │ Preview Tables      │   │                     │
│             │ └─────────────────────┘   │                     │
└─────────────┴─────────────────────────┴─────────────────────┘
```

### 7.2 Key UI Managers

#### A. SplitterManager
- Manage splitter positions
- Adaptive sizing for different screen sizes

#### B. ColumnManager
- Dynamic column management for File Table
- Add/Remove metadata columns

#### C. SelectionManager
- File selection coordination
- Preview updates

## 8. Configuration System

### 8.1 JSON Configuration
```python
# utils/json_config_manager.py
config_categories = {
    "window": WindowConfig(),      # Window geometry, splitters
    "app": AppConfig(),           # Theme, recent folders
    "file_hashes": FileHashConfig()  # Hash settings
}
```

### 8.2 Application Settings
```python
# config.py - Centralized configuration
DEBUG_RESET_DATABASE = False    # Reset database on startup
DEBUG_RESET_CONFIG = False      # Reset config.json on startup
ALLOWED_EXTENSIONS = {...}      # Supported file types
LARGE_FOLDER_WARNING_THRESHOLD = 150  # File count warning
```

## 9. Error Handling & Logging

### 9.1 Logging System
```python
# utils/logger_factory.py
logger = get_cached_logger(__name__)

# Log levels:
logger.debug("Debug info", extra={"dev_only": True})
logger.info("General info")
logger.warning("Warning message")
logger.error("Error occurred")
```

### 9.2 Exception Handling
- Database operations: Automatic rollback
- File operations: User-friendly error messages
- Metadata loading: Graceful fallbacks

## 10. Testing & Debug Features

### 10.1 Debug Configuration
```python
# config.py debug settings
DEBUG_RESET_DATABASE = True   # Fresh database on startup
DEBUG_RESET_CONFIG = True     # Fresh config on startup
SHOW_DEV_ONLY_IN_CONSOLE = True  # Show debug logs
```

### 10.2 Testing Framework
- Unit tests for each module
- Integration tests for workflows
- Mock objects for database/file operations

## Conclusion

The OnCutF application uses a sophisticated architecture with:

1. **Modular Design**: Separate managers for each functionality
2. **Database-Driven**: Persistent storage for metadata, hashes, history
3. **Caching**: Performance optimization with intelligent caching
4. **Error Resilience**: Robust error handling and recovery
5. **Extensibility**: Plugin-like module system for rename operations
6. **Debug Support**: Comprehensive debugging and testing features

This architecture allows for easy maintenance, extension, and debugging of the application.
