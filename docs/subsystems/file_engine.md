# File Engine Subsystem

> **Status**: Architecture Documentation (Phase 7)  
> **Last Updated**: 2026-01-01  
> **Author**: Michael Economou

## Overview

The File Engine is responsible for **file discovery, loading, storage, and UI display**. It implements a **centralized state pattern** where:

```
Filesystem → FileLoadManager → FileStore → FileTableModel → UI
```

Key capabilities:
- Folder scanning with extension filtering
- Drag & drop loading with modifier keys (Ctrl=recursive, Shift=merge)
- Streaming loading for large file sets (>200 files)
- Filesystem monitoring for auto-refresh
- Color tagging with database persistence

---

## Scope

The File Engine **owns**:
- File discovery (folder scanning, drag & drop)
- FileItem data model
- FileStore centralized state
- File table/tree UI components
- Extension filtering (ALLOWED_EXTENSIONS)
- Filesystem monitoring
- Color tagging

The File Engine **does NOT own**:
- Metadata extraction (→ Metadata Engine)
- Rename operations (→ Rename Engine)
- Hash computation (→ Metadata Engine)

---

## Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           UI LAYER                                   │
│  FileTableView → FileTableModel                                      │
│  FileTreeView → CustomFileSystemModel                                │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CONTROLLER LAYER                                │
│  FileLoadController (UI-agnostic orchestration)                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       MANAGER LAYER                                  │
│  FileLoadManager (folder scanning, streaming)                        │
│  FileOperationsManager (rename execution)                            │
│  FileValidationManager (content-based identification)                │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        STORE LAYER                                   │
│  FileStore (centralized state, caching, signals)                     │
│  FileItem (data model)                                               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    MONITORING LAYER                                  │
│  FilesystemMonitor (directory watching, drive events)                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## File Ownership

### Core (`oncutf/core/`)

| File | Responsibility |
|------|----------------|
| `file_store.py` | Centralized file state, caching, signals |
| `file_item.py` | Data model for single file |
| `file_load_manager.py` | Folder scanning, drag/drop, streaming |
| `file_operations_manager.py` | Rename execution workflow |
| `file_validation_manager.py` | Content-based identification, TTL caching |
| `filesystem_monitor.py` | Directory watching, drive mount events |

### Controller (`oncutf/controllers/`)

| File | Responsibility |
|------|----------------|
| `file_load_controller.py` | UI-agnostic loading orchestration |

### UI - Table (`oncutf/ui/file_table/`)

| File | Responsibility |
|------|----------------|
| `view.py` | FileTableView - QTableView with Explorer behavior |
| `model.py` | FileTableModel - Qt model for file display |
| `delegate.py` | Custom cell rendering (icons, colors) |
| `behaviors/` | Composition: selection, drag-drop, columns |

### UI - Tree (`oncutf/ui/file_tree/`)

| File | Responsibility |
|------|----------------|
| `view.py` | FileTreeView - filesystem navigation |
| `model.py` | CustomFileSystemModel with icons |

---

## Data Flow

### File Loading Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. ENTRY POINTS                                                      │
│    • FileTreeView drag → item_dropped signal                         │
│    • FileTableView drop → files_dropped signal                       │
│    • Import button → direct path selection                           │
│    • MainWindow folder change → reload trigger                       │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. FileLoadController                                                │
│    → Validates paths exist                                           │
│    → Filters by ALLOWED_EXTENSIONS                                   │
│    → Checks file readability                                         │
│    → Parses keyboard modifiers (Ctrl=recursive, Shift=merge)         │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. FileLoadManager                                                   │
│    → os.walk() for folder scanning                                   │
│    → Companion file filtering (RAW+JPG grouping)                     │
│    → Creates FileItem instances via FileItem.from_path()             │
│    → Streaming loading for >200 files (batch_size=100)               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. FileStore                                                         │
│    → Stores in _loaded_files: list[FileItem]                         │
│    → Maintains folder cache (_file_cache)                            │
│    → Emits files_loaded signal                                       │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. FileTableModel                                                    │
│    → set_files() receives FileItem list                              │
│    → Manages Qt model/view data binding                              │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. FileTableView                                                     │
│    → Displays files with selection, sorting, hover                   │
│    → Emits selection_changed for downstream consumers                │
└─────────────────────────────────────────────────────────────────────┘
```

### Loading Triggers

| Trigger | Entry Point | Modifiers |
|---------|-------------|-----------|
| FileTreeView drag | `item_dropped` signal | Ctrl=recursive, Shift=merge |
| FileTableView drop | `files_dropped` signal | Ctrl=recursive, Shift=merge |
| Import button | Direct path selection | Always recursive for folders |
| Folder selection | MainWindow callback | Configurable |
| FilesystemMonitor | `directory_changed` signal | Preserves original mode |

---

## FileItem Data Model

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `full_path` | `str` | Absolute file path |
| `path` | `str` | Alias for `full_path` |
| `filename` | `str` | Base name only (`photo.jpg`) |
| `name` | `str` | Alias for `filename` |
| `extension` | `str` | Extension without dot, lowercase |
| `modified` | `datetime` | Last modification timestamp |
| `size` | `int` | File size in bytes |
| `metadata` | `dict` | EXIF/QuickTime metadata |
| `metadata_status` | `str` | `"none"`, `"loaded"`, `"extended"`, `"error"` |
| `checked` | `bool` | Selection state for rename |
| `hash_value` | `str\|None` | SHA256 hash (lazy-loaded) |
| `color` | `str` | Hex color or `"none"` |

### Creation

```python
# Factory method (preferred)
file_item = FileItem.from_path("/path/to/file.jpg")
# Auto-detects: extension, modified time, size
# Loads color tag from database
```

### Properties

```python
file_item.has_metadata      # bool - metadata dict populated
file_item.has_extended_metadata  # bool - extended mode loaded
file_item.formatted_size    # str - "1.2 GB"
```

---

## FileStore Architecture

### Internal Structure

```python
class FileStore(QObject):
    _current_folder: str | None      # Active folder path
    _loaded_files: list[FileItem]    # Working file set
    _file_cache: dict[str, list[FileItem]]  # Folder → cached items
```

### Signals

| Signal | Payload | Description |
|--------|---------|-------------|
| `files_loaded` | `list[FileItem]` | Files loaded/changed |
| `folder_changed` | `str` | Current folder changed |
| `files_filtered` | `list[FileItem]` | After filtering |

### Query Methods

| Method | Description |
|--------|-------------|
| `get_loaded_files()` | Get all files (returns copy) |
| `filter_files_by_extension(exts)` | Filter by extension set |
| `get_current_folder()` | Get active folder path |
| `is_extension_allowed(ext)` | Check allowlist |

### Caching

```python
# Cache hit
if use_cache and folder_path in self._file_cache:
    return self._file_cache[folder_path].copy()

# Cache miss: scan + store
file_items = [...]
self._file_cache[folder_path] = file_items.copy()
```

Cache invalidation:
- `clear_cache()` - Full clear
- `invalidate_folder_cache(path)` - Specific folder
- Drive unmount - Automatic via FilesystemMonitor

### Thread Safety

- FileStore is **NOT thread-safe** - main thread only
- Uses Qt signals for async communication
- Streaming loading uses `QTimer.singleShot()` for batches

---

## Key Classes

### FileStore

- **File**: `oncutf/core/file_store.py`
- **Role**: Centralized file state management
- **Key Methods**: `get_file_items_from_folder()`, `load_mixed_paths()`, `get_loaded_files()`
- **Signals**: `files_loaded`, `folder_changed`, `files_filtered`

### FileLoadManager

- **File**: `oncutf/core/file_load_manager.py`
- **Role**: Folder scanning, drag/drop, streaming loading
- **Key Methods**: `load_folder()`, `load_from_paths()`, `handle_single_item_drop()`
- **Features**: Streaming for >200 files, companion filtering

### FileLoadController

- **File**: `oncutf/controllers/file_load_controller.py`
- **Role**: UI-agnostic loading orchestration
- **Key Methods**: `load_files()`, `load_folder()`, `process_drop()`

### FileTableView

- **File**: `oncutf/ui/file_table/view.py`
- **Role**: QTableView with Explorer-like behavior
- **Signals**: `selection_changed`, `files_dropped`, `refresh_requested`
- **Composition**: Uses behavior classes for selection, drag-drop, columns

### FileTreeView

- **File**: `oncutf/ui/file_tree/view.py`
- **Role**: Filesystem navigation tree
- **Signals**: `item_dropped`, `enter_pressed`, `selection_changed`

### FilesystemMonitor

- **File**: `oncutf/core/filesystem_monitor.py`
- **Role**: Directory watching, drive mount events
- **Signals**: `drive_mounted`, `drive_unmounted`, `directory_changed`

---

## Dependencies

### To Rename Engine

```
FileStore provides:
  • get_loaded_files() → List[FileItem] for rename preview
  • FileItem.checked → Selection state for batch rename
  • FileItem.full_path → Source path for rename operation
  • FileItem.metadata → EXIF data for name generation
```

### To Metadata Engine

```
FileStore provides:
  • FileItem.full_path → Path for metadata loading
  • files_loaded signal → Trigger for metadata loading
  • FileItem.metadata_status → Status icon rendering
  • FileItem.modified, FileItem.size → Change detection
```

### External Dependencies

| Dependency | Purpose |
|------------|---------|
| `os`, `os.path`, `pathlib` | Filesystem operations |
| `watchdog` | Directory change detection |
| `QElapsedTimer` | Performance timing |
| `ALLOWED_EXTENSIONS` | Extension filtering |
| `DatabaseManager` | Color tags, path tracking |

---

## Public API

### Get Loaded Files

```python
# Via ApplicationContext (preferred)
from oncutf.core.application_context import get_app_context

context = get_app_context()
files = context.file_store.get_loaded_files()
```

### Load Folder

```python
# Via Controller (preferred)
from oncutf.controllers.file_load_controller import FileLoadController

controller = FileLoadController(file_load_manager, file_store, context)
result = controller.load_folder("/path/to/folder", recursive=True)

# Via Manager (internal)
manager = FileLoadManager(parent_window)
manager.load_folder("/path/to/folder", merge_mode=False, recursive=True)
```

### Filter Files

```python
# By extension
filtered = file_store.filter_files_by_extension({"jpg", "png"})

# Custom filter
files = file_store.get_loaded_files()
large_files = [f for f in files if f.size > 10_000_000]
```

### Access File Properties

```python
file_item = files[0]
file_item.filename       # "photo.jpg"
file_item.extension      # "jpg"
file_item.size           # 1234567
file_item.modified       # datetime
file_item.has_metadata   # True/False
file_item.hash_value     # "abc123..." or None
file_item.color          # "#ff0000" or "none"
```

---

## Known Issues & Technical Debt

### 1. Dual State Management

FileLoadManager updates both `FileStore` AND `FileTableModel.files` directly, creating potential for state drift.

**Recommendation**: FileTableModel should observe FileStore signals instead of direct updates.

### 2. Parent Window Coupling

FileLoadManager has direct references to `parent_window.file_table`, `parent_window.preview_tables`, making unit testing difficult.

**Recommendation**: Inject dependencies via constructor, use signals for UI updates.

### 3. Mixed Responsibilities

FileLoadManager handles both loading logic AND UI updates (`wait_cursor`, widget manipulation). 700+ lines.

**Recommendation**: Extract UI refresh to separate manager or use event-driven updates.

### 4. Streaming Loading Complexity

Uses `QTimer.singleShot()` and recursive scheduling. Difficult to track state and cancel mid-stream.

**Recommendation**: Consider QThreadPool with progress signals.

### 5. Extension Filtering Duplication

`ALLOWED_EXTENSIONS` checked in multiple places:
- FileStore
- FileLoadManager
- FileValidationManager
- FileTableModel

**Recommendation**: Centralize to single validation utility.

### 6. BackupManager Naming

Named `backup_manager.py` but handles DATABASE backups, not file backups.

**Recommendation**: Rename to `database_backup_manager.py`.

---

## Summary

| Aspect | Status |
|--------|--------|
| File loading | ✅ Complete |
| Streaming loading | ✅ For >200 files |
| Folder caching | ✅ Per-folder cache |
| Filesystem monitoring | ✅ watchdog integration |
| Color tagging | ✅ Database persistence |
| Architecture clarity | ⚠️ Manager/Store overlap |
| Documentation | 📝 This document |

The File Engine is **production-ready** and provides:
- Fast file loading with streaming for large sets
- Persistent folder caching
- Real-time filesystem monitoring
- Flexible drag & drop with modifiers
