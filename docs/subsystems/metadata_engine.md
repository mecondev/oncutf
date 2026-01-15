# Metadata Engine Subsystem

> **Status**: Architecture Documentation (Phase 7)  
> **Last Updated**: 2026-01-01  
> **Author**: Michael Economou

## Overview

The Metadata Engine is responsible for **EXIF/XMP metadata extraction, caching, and display**. It implements a **two-tier caching architecture** with:

```
File → ExifTool → Cache (Memory + SQLite) → UI Display
```

Key capabilities:
- Parallel metadata extraction via ThreadPoolExecutor
- Two-tier cache (memory LRU + SQLite persistence)
- CRC32 hash computation with caching
- XMP/sidecar companion file merging
- Metadata editing with staging and undo/redo

---

## Entry Point Guidelines

### Recommended Entry Points

| Use Case | Entry Point | Notes |
|----------|-------------|-------|
| **Simple cache checks** | `file_status_helpers` | `has_metadata()`, `get_metadata_for_file()`, `get_metadata_value()`, `set_metadata_value()` |
| **Full loading operations** | `MetadataController` | UI-agnostic, for external callers |
| **Qt-integrated operations** | `UnifiedMetadataManager` | Signals, progress dialogs |

### Removed Entry Points

| Entry Point | Status | Migration Path |
|-------------|--------|----------------|
| `MetadataCacheHelper` | [FAIL] Removed 2026-01-01 | Use `file_status_helpers` functions |
| `DirectMetadataLoader` | [FAIL] Removed 2026-01-01 | Was dead code, use `UnifiedMetadataManager` |

---

## Scope

The Metadata Engine **owns**:
- EXIF/XMP metadata extraction (via exiftool)
- Metadata caching (memory + SQLite)
- Hash computation and caching
- Metadata tree UI components
- Metadata editing workflow (stage → save)
- Companion/sidecar file handling

The Metadata Engine **does NOT own**:
- File discovery (→ File Engine)
- Filename generation from metadata (→ Rename Engine modules)
- File table display (→ UI Layer)

---

## Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           UI LAYER                                   │
│  MetadataTreeView → MetadataTreeModel → Delegates                    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CONTROLLER LAYER                                │
│  MetadataController (UI-agnostic orchestration)                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       MANAGER LAYER                                  │
│  UnifiedMetadataManager (facade)                                     │
│    ├── MetadataLoader (orchestration)                                │
│    ├── MetadataStagingManager (pending changes)                      │
│    └── CompanionMetadataHandler (XMP/sidecar)                        │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CACHE LAYER                                   │
│  PersistentMetadataCache (memory + SQLite)                           │
│  PersistentHashCache (memory + SQLite)                               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTRACTION LAYER                                  │
│  ExifToolWrapper → exiftool subprocess                               │
│  ParallelMetadataLoader → ThreadPoolExecutor                         │
│  HashManager → CRC32 calculation                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## File Ownership

### Core Services (`oncutf/core/`)

| File | Responsibility |
|------|----------------|
| `unified_metadata_manager.py` | Facade for all metadata operations |
| `metadata_loader.py` | Orchestrates single/batch loading with progress |
| `parallel_metadata_loader.py` | ThreadPoolExecutor for parallel extraction |
| `metadata_staging_manager.py` | Tracks pending changes before save |
| `companion_metadata_handler.py` | XMP/sidecar file merging |
| `metadata_save_handler.py` | ExifTool write operations |
| `structured_metadata_manager.py` | Database-backed field categorization |

### Cache Layer (`oncutf/core/cache/`)

| File | Responsibility |
|------|----------------|
| `persistent_metadata_cache.py` | Two-tier metadata cache (1000 entries memory) |
| `persistent_hash_cache.py` | Two-tier hash cache (2000 entries memory) |
| `cache_operations_handler.py` | Cache abstraction layer |

### Hash Computation (`oncutf/core/hash/`)

| File | Responsibility |
|------|----------------|
| `hash_manager.py` | CRC32 calculation with cache integration |
| `parallel_hash_worker.py` | Multi-threaded hash calculation |

### UI Layer (`oncutf/ui/metadata_tree/`)

| File | Responsibility |
|------|----------------|
| `view.py` | QTreeView with drag-drop, context menu |
| `model.py` | MetadataTreeModel, MetadataItem data structures |
| `controller.py` | UI-agnostic tree operations |
| `worker.py` | Background MetadataWorker (QThread) |
| `service.py` | Service layer for tree operations |

### Controller (`oncutf/controllers/`)

| File | Responsibility |
|------|----------------|
| `metadata_controller.py` | UI-agnostic loading, reload, export, config |

### Utilities (`oncutf/utils/`)

| File | Responsibility |
|------|----------------|
| `exiftool_wrapper.py` | Low-level exiftool subprocess wrapper |
| `file_status_helpers.py` | **Recommended** — Central helpers for metadata/hash checks |

---

## Data Flow

### Metadata Loading Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. TRIGGER                                                           │
│    • User selects file in table                                      │
│    • Keyboard shortcut (Shift+F5 / Ctrl+Shift+F5)                    │
│    • Drag & drop onto metadata tree                                  │
│    • Programmatic: MetadataController.load_metadata()                │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. CACHE PRE-CHECK                                                   │
│    MetadataLoader._filter_cached_items()                             │
│    → Check PersistentMetadataCache                                   │
│    → Extended metadata never downgrades to fast                      │
│    → Returns: (needs_loading[], skipped_count)                       │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. MODE SELECTION                                                    │
│    ┌────────────────┬─────────────────────────────────┐              │
│    │ 1 file         │ Synchronous with wait_cursor    │              │
│    ├────────────────┼─────────────────────────────────┤              │
│    │ 2+ files       │ ProgressDialog + parallel load  │              │
│    └────────────────┴─────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. EXTRACTION                                                        │
│    ExifToolWrapper.get_metadata(file_path, use_extended)             │
│    ├─→ Fast mode: exiftool -json file.jpg                            │
│    └─→ Extended mode: exiftool -json -ee -b file.mp4                 │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. COMPANION ENHANCEMENT (optional)                                  │
│    CompanionMetadataHandler.enhance_metadata_with_companions()       │
│    → Finds XMP/sidecar files and merges metadata                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. CACHE STORAGE                                                     │
│    PersistentMetadataCache.set(path, metadata, is_extended)          │
│    ├─→ Memory cache (OrderedDict LRU, max 1000)                      │
│    └─→ SQLite (file_metadata table)                                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. UI UPDATE                                                         │
│    ├─→ FileModel.refresh_icons() — status icons in table            │
│    ├─→ MetadataTreeView.display_metadata() — tree rendering         │
│    └─→ loading_finished signal — notify subscribers                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Hash Computation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ UnifiedMetadataManager.load_hashes_for_files(files)                  │
│    └─→ ParallelHashWorker (QThread + ThreadPoolExecutor)             │
│        └─→ HashManager.calculate_hash(file_path)                     │
│            ├─→ Check PersistentHashCache first                       │
│            └─→ If miss: CRC32 with adaptive buffer (8KB/64KB/256KB)  │
│                └─→ Store in PersistentHashCache                      │
│                                                                      │
│ Signals:                                                             │
│   file_hash_calculated → UI icon refresh                             │
│   finished_processing → completion notification                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Caching Strategy

### Two-Tier Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     TWO-TIER CACHE                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────┐    ┌─────────────────────────────────┐ │
│  │    Memory Layer         │    │     SQLite Layer                │ │
│  │   (OrderedDict LRU)     │    │   (DatabaseManager)             │ │
│  │                         │    │                                 │ │
│  │  • Fast O(1) access     │    │  • Persistent across sessions   │ │
│  │  • Limited size (LRU)   │    │  • Unlimited size               │ │
│  │  • First lookup target  │    │  • Second lookup target         │ │
│  │                         │    │                                 │ │
│  │  Metadata: 1000 entries │    │  Tables:                        │ │
│  │  Hashes: 2000 entries   │    │   - file_paths (normalized)     │ │
│  │                         │    │   - file_metadata               │ │
│  └──────────┬──────────────┘    │   - file_hashes                 │ │
│             │                    │   - file_metadata_structured    │ │
│             ▼                    └─────────────────────────────────┘ │
│        Cache Miss?                                                   │
│             │                                                        │
│             └──────────► Load from SQLite → Store in Memory         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### What is Cached

| Data Type | Cache | Memory Limit | SQLite Table |
|-----------|-------|--------------|--------------|
| EXIF/Metadata | PersistentMetadataCache | 1000 entries (~2MB) | `file_metadata` |
| CRC32 Hashes | PersistentHashCache | 2000 entries (~200KB) | `file_hashes` |
| Structured Metadata | StructuredMetadataManager | In-memory | `file_metadata_structured` |

### Cache Invalidation

1. **LRU Eviction**: Memory cache uses `OrderedDict.popitem(last=False)` when full
2. **Extended Upgrade**: Fast metadata can upgrade to extended; never downgrade
3. **Manual Clear**: `cache.clear_memory_cache()` clears memory (SQLite untouched)
4. **Path Normalization**: All paths normalized via `normalize_path()` for consistency

---

## Dependencies

### From File Engine

```
FileItem objects with:
  • full_path: str
  • filename: str
  • size: int (for progress tracking)
  • metadata: dict (fallback storage)

FileStore.get_loaded_files() — for "reload all" operations
```

### To Rename Engine

```
Rename modules access metadata via:
  • file_status_helpers.get_metadata_for_file(file_path) — recommended
  • UnifiedMetadataManager.check_cached_metadata(file_item) — for FileItem objects

Key metadata fields used:
  • EXIF:DateTimeOriginal, CreateDate, ModifyDate
  • EXIF:Make, Model (camera info)
  • File:ImageWidth, ImageHeight (dimensions)
  • GPS:GPSLatitude, GPSLongitude (location)
```

### External Dependencies

| Dependency | Purpose | Required |
|------------|---------|----------|
| **exiftool** | Metadata extraction/writing | Yes (PATH) |
| **PyQt5** | Signals, QThread, QTreeView | Yes |
| **sqlite3** | Persistent cache | Yes (stdlib) |
| **zlib** | CRC32 calculation | Yes (stdlib) |

---

## Public API

### UnifiedMetadataManager (recommended entry point)

```python
from oncutf.core.metadata import get_unified_metadata_manager

manager = get_unified_metadata_manager(parent_window)

# Load metadata for files
manager.load_metadata_for_items(
    items=file_items,        # List[FileItem]
    use_extended=False,      # True for embedded GPS telemetry
    source="my_operation"    # For logging
)

# Load hashes
manager.load_hashes_for_files(file_items, source="user_request")

# Check cache (synchronous)
metadata = manager.check_cached_metadata(file_item)  # dict or None

# Signals
manager.metadata_loaded.connect(handler)      # (file_path, metadata)
manager.loading_started.connect(handler)      # (file_path,)
manager.loading_finished.connect(handler)     # ()
```

### MetadataController (UI-agnostic)

```python
from oncutf.controllers.metadata_controller import MetadataController

controller = MetadataController(app_context)

# Load with result
result = controller.load_metadata(file_items, use_extended=False)
# Returns: (success: bool, count: int, errors: List[str])

# Reload all
result = controller.reload_all_metadata()

# Export
result = controller.export_metadata(file_items, format="json", output_path=path)
```

### Direct Cache Access

```python
from oncutf.core.cache.persistent_metadata_cache import get_persistent_metadata_cache
from oncutf.core.cache.persistent_hash_cache import get_persistent_hash_cache

# Metadata cache
meta_cache = get_persistent_metadata_cache()
entry = meta_cache.get_entry(normalized_path)
if entry and entry.data:
    metadata = entry.data

# Hash cache
hash_cache = get_persistent_hash_cache()
hash_value = hash_cache.get(normalized_path)  # str or None
```

### File Status Helpers (utilities)

```python
from oncutf.utils.filesystem.file_status_helpers import (
    get_metadata_for_file,
    has_metadata,
    has_hash,
    get_hash_for_file
)

# Quick checks
if has_metadata(file_path):
    metadata = get_metadata_for_file(file_path)

if has_hash(file_path):
    hash_value = get_hash_for_file(file_path)
```

---

## Key Classes

### UnifiedMetadataManager

- **File**: `oncutf/core/unified_metadata_manager.py`
- **Role**: Facade pattern — single entry point for all metadata operations
- **Signals**: `metadata_loaded`, `loading_started`, `loading_finished`

### PersistentMetadataCache

- **File**: `oncutf/core/cache/persistent_metadata_cache.py`
- **Role**: Two-tier caching with LRU memory + SQLite persistence
- **Config**: MAX_MEMORY_CACHE_SIZE = 1000

### PersistentHashCache

- **File**: `oncutf/core/cache/persistent_hash_cache.py`
- **Role**: Two-tier hash caching with LRU memory + SQLite persistence
- **Config**: MAX_MEMORY_CACHE_SIZE = 2000

### HashManager

- **File**: `oncutf/core/hash/hash_manager.py`
- **Role**: CRC32 calculation with adaptive buffering and cache integration

### MetadataStagingManager

- **File**: `oncutf/core/metadata_staging_manager.py`
- **Role**: Tracks pending metadata changes before save
- **Signals**: `change_staged`, `change_unstaged`, `changes_cleared`

### ExifToolWrapper

- **File**: `oncutf/utils/exiftool_wrapper.py`
- **Role**: Low-level exiftool subprocess management
- **Modes**: Fast (`-json`) vs Extended (`-json -ee -b`)

---

## Known Issues & Technical Debt

### 1. No Cache Invalidation API

`PersistentMetadataCache` and `PersistentHashCache` lack methods to remove specific entries from SQLite. Only memory cache can be cleared.

**Recommendation**: Add `remove(path)` method for explicit invalidation.

### 2. ~~Multiple Entry Points~~ [x] RESOLVED (2026-01-01)

~~Metadata can be accessed via multiple entry points.~~

**Resolution**:
- `DirectMetadataLoader` removed (was dead code)
- `MetadataCacheHelper` removed (consolidated into `file_status_helpers`)
- Recommended entry points now clearly documented:
  - `file_status_helpers` for simple sync checks (`get_metadata_value()`, `set_metadata_value()`, etc.)
  - `UnifiedMetadataManager` for complex Qt-integrated operations
  - `MetadataController` for UI-agnostic external access

### 3. ~~DirectMetadataLoader vs MetadataLoader~~ [x] RESOLVED (2026-01-01)

~~Both loaders existed with unclear distinction.~~

**Resolution**: `DirectMetadataLoader` removed — was never imported externally (dead code).

### 4. Manager vs Controller Distinction

Both `UnifiedMetadataManager` and `MetadataController` orchestrate metadata loading.

**Clarification**:
- `MetadataController`: UI-agnostic entry point for external callers (tests, scripts)
- `UnifiedMetadataManager`: Qt-integrated facade with signals and progress dialogs

---

## Summary

| Aspect | Status |
|--------|--------|
| Metadata extraction | [x] Complete (exiftool) |
| Two-tier caching | [x] Memory + SQLite |
| Parallel loading | [x] ThreadPoolExecutor |
| Hash computation | [x] CRC32 with caching |
| Metadata editing | [x] Stage → Save workflow |
| Architecture clarity | [x] Entry points consolidated |
| Documentation |  This document |

The Metadata Engine is **production-ready** and provides:
- Fast cached access for previously-loaded files
- Parallel extraction for batch operations
- Persistent storage across application sessions
- Full EXIF/XMP support via exiftool
- Clear entry point guidelines (as of 2026-01-01)
