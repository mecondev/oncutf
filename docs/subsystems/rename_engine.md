# Rename Engine Subsystem

> **Status**: Architecture Documentation (Phase 7)  
> **Last Updated**: 2026-01-01  
> **Author**: Michael Economou

## Overview

The Rename Engine is the core subsystem responsible for batch file renaming operations. It implements a **pipeline architecture** where files flow through:

```
Input Files → [Modules] → Preview → Validate → Execute → Undo
```

This is not just a "rename feature" — it's a **data transformation pipeline** with:
- Composable modules for name generation
- Real-time preview with caching
- Validation with conflict detection
- Transactional execution with rollback
- Persistent undo/redo history

---

## Scope

The Rename Engine **owns**:
- Preview generation (name transformation)
- Validation (filename validity, duplicates, conflicts)
- Execution (filesystem operations)
- Undo/redo (history management)
- Module orchestration (pipeline composition)

The Rename Engine **does NOT own**:
- File discovery (→ File Engine)
- Metadata extraction (→ Metadata Engine)
- UI widgets (→ UI Layer)
- User selection state (→ Selection Manager)

---

## Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           UI LAYER                                   │
│  RenameModulesArea → MainWindow → ApplicationService                 │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CONTROLLER LAYER                                │
│  RenameController (UI-agnostic orchestration)                        │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ENGINE LAYER                                  │
│  UnifiedRenameEngine (central facade)                                │
│    ├── UnifiedPreviewManager                                         │
│    ├── UnifiedValidationManager                                      │
│    ├── UnifiedExecutionManager                                       │
│    └── RenameStateManager                                            │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       MODULE LAYER                                   │
│  counter, metadata, original_name, specified_text, remove_text       │
│  + NameTransformModule (post-processing)                             │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                              │
│  Renamer (filesystem ops), RenameHistoryManager (undo/redo)          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## File Ownership

### Core Engine (`oncutf/core/rename/`)

| File | Responsibility |
|------|----------------|
| `unified_rename_engine.py` | Central facade: preview, validate, execute |
| `rename_manager.py` | UI-aware workflow with post-rename state restoration |
| `rename_history_manager.py` | Persistent undo/redo with SQLite storage |

### Modules (`oncutf/modules/`)

| File | Responsibility |
|------|----------------|
| `base_module.py` | Abstract base class with signal throttling |
| `counter_module.py` | Sequential numbering (global/per-folder/per-extension) |
| `metadata_module.py` | EXIF dates, file dates, hash values |
| `original_name_module.py` | Original filename with Greeklish conversion |
| `specified_text_module.py` | User-defined static text |
| `text_removal_module.py` | Pattern removal from filenames |
| `name_transform_module.py` | Post-processing: case/separator transforms |

### Controller (`oncutf/controllers/`)

| File | Responsibility |
|------|----------------|
| `rename_controller.py` | UI-agnostic orchestration of rename workflow |
| `module_orchestrator.py` | Module registry and dynamic discovery |
| `module_drag_drop_manager.py` | Drag & drop reordering of modules |

### Utilities (`oncutf/utils/`)

| File | Responsibility |
|------|----------------|
| `preview_engine.py` | Core logic: apply modules to generate names |
| `renamer.py` | Low-level rename operations (plan/resolve/execute) |
| `batch_renamer.py` | Batch rename executor with validation |
| `filename_validator.py` | Filename validity checks |

### Validation (`oncutf/core/`)

| File | Responsibility |
|------|----------------|
| `file_validation_manager.py` | Pre-execution validation (existence, permissions) |
| `conflict_resolver.py` | Filesystem conflict resolution strategies |

---

## Data Flow

### Complete Rename Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. USER ACTION                                                       │
│    RenameModulesArea.updated signal                                  │
│    → MainWindow.request_preview_update() [debounced 300ms]           │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. PREVIEW GENERATION                                                │
│    UnifiedRenameEngine.generate_preview()                            │
│    → preview_engine.apply_rename_modules()                           │
│    → For each file: concatenate module outputs                       │
│    → Result: PreviewResult(name_pairs, has_changes)                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. VALIDATION                                                        │
│    UnifiedRenameEngine.validate_preview()                            │
│    → Check filename validity (characters, length)                    │
│    → Detect duplicates (case-insensitive on Windows)                 │
│    → Detect unchanged names                                          │
│    → Result: ValidationResult(items, duplicates, has_errors)         │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. USER CLICKS "RENAME"                                              │
│    Pre-execution validation:                                         │
│    → Check file existence                                            │
│    → Check write permissions                                         │
│    → Check file locks (Windows)                                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. EXECUTION                                                         │
│    Renamer.rename() for each file:                                   │
│    → Apply NameTransformModule (post-transform)                      │
│    → Handle case-only changes (safe_case_rename)                     │
│    → Execute os.rename()                                             │
│    → Handle conflicts                                                │
│    → Result: ExecutionResult(success_count, error_count)             │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. POST-RENAME WORKFLOW                                              │
│    RenameManager._execute_post_rename_workflow_safe()                │
│    → Record history (RenameHistoryManager)                           │
│    → Reload folder                                                   │
│    → Restore selection/checked state                                 │
│    → Regenerate preview                                              │
│    → Show completion dialog                                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Module Application

Each module is a **pure function** that generates a name fragment:

```python
# preview_engine.apply_rename_modules()
for module_data in modules_data:
    module_type = module_data["type"]
    
    if module_type == "counter":
        fragment = CounterModule.apply_from_data(module_data, index, all_files)
    elif module_type == "metadata":
        fragment = MetadataModule.apply_from_data(module_data, file_item, metadata_cache)
    elif module_type == "original_name":
        fragment = file_item.filename  # with optional Greeklish
    elif module_type == "specified_text":
        fragment = SpecifiedTextModule.apply_from_data(module_data)
    elif module_type == "remove_text":
        fragment = TextRemovalModule.apply_from_data(module_data, current_name)
    
    result += fragment

# Post-transform applied at end
result = NameTransformModule.apply(result, post_transform_data)
```

---

## Dependencies

### From Metadata Engine

```
MetadataModule.apply_from_data()
    ↓
UnifiedMetadataManager / MetadataExtractor
    ↓
• EXIF data (DateTimeOriginal, CreateDate, etc.)
• File system dates (created, modified)
• Hash values (CRC32, SHA256)
```

The `metadata_cache` dict is passed through the entire pipeline.

### From File Engine

```
FileStore
    └── get_file_items_from_folder() → List[FileItem]
    └── files_loaded signal → triggers post-rename reload

FileItem
    └── full_path, filename, extension, checked
```

### From UI Layer

```
RenameModulesArea
    └── get_all_data() → {"modules": [...], "post_transform": {...}}
    └── updated signal → triggers preview refresh

PreviewTablesView
    └── Displays old_name → new_name pairs
    └── Shows validation status icons
```

---

## Public API

### RenameController (recommended entry point)

```python
# Preview
controller.generate_preview(file_items, modules_data, post_transform, metadata_cache)
    → PreviewResult

# Validation
controller.validate_preview(preview_pairs)
    → ValidationResult

# Execution
controller.execute_rename(file_items, modules_data, post_transform, 
                          metadata_cache, current_folder)
    → ExecutionResult

# State
controller.has_pending_changes() → bool
controller.get_current_state() → RenameState
controller.clear_state()
```

### UnifiedRenameEngine (lower-level access)

```python
engine.generate_preview(files, modules_data, post_transform, metadata_cache)
engine.validate_preview(preview_pairs)
engine.execute_rename(files, new_names, conflict_callback, validator)
engine.get_current_state()
engine.clear_cache()

# Signals
engine.preview_updated.connect(handler)
engine.validation_updated.connect(handler)
engine.execution_completed.connect(handler)
```

### RenameHistoryManager (undo/redo)

```python
history.record_rename_batch(renames, modules_data, post_transform_data)
    → operation_id

history.get_recent_operations(limit=10)
    → List[dict]

history.can_undo_operation(operation_id)
    → (bool, reason)

history.undo_operation(operation_id)
    → (success, message, files_processed)
```

---

## Data Classes

### PreviewResult

```python
@dataclass
class PreviewResult:
    name_pairs: List[Tuple[str, str]]  # (old_name, new_name)
    has_changes: bool
    errors: List[str]
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    items: List[ValidationItem]
    duplicates: Set[str]
    has_errors: bool
```

### ValidationItem

```python
@dataclass
class ValidationItem:
    old_name: str
    new_name: str
    is_valid: bool
    is_duplicate: bool
    is_unchanged: bool
    error_message: Optional[str]
```

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    items: List[RenameItem]
    success_count: int
    error_count: int
```

---

## Known Issues & Technical Debt

### 1. Dual Preview Paths

There are two preview generation paths:
- `PreviewManager.generate_preview_names()` - Used by MainWindow
- `UnifiedRenameEngine.generate_preview()` - The "unified" system

Both eventually call `preview_engine.apply_rename_modules()`, creating maintenance overhead.

**Recommendation**: Consolidate to single path through UnifiedRenameEngine.

### 2. Multiple Manager Layers

The subsystem has overlapping "manager" classes:
- `RenameManager` (UI-aware, in `core/ui_managers/`)
- `FileOperationsManager` (file ops, in `core/ui_managers/`)
- `PreviewManager` (preview generation, in `core/`)
- `UnifiedPreviewManager` (inside UnifiedRenameEngine)

**Recommendation**: Clarify boundaries or consolidate.

### 3. Post-Transform Applied Multiple Times

`NameTransformModule.apply()` is called in:
1. `preview_engine.py` (preview generation)
2. `renamer.py` (before actual rename)
3. Various other places

**Recommendation**: Apply post-transform exactly once in pipeline.

### 4. Case-Sensitive Rename Handling

`safe_case_rename()` is implemented in `renamer.py` but called from multiple places. Should be single point of call.

---

## Future Direction: Node Editor

The current module pipeline is well-suited for visual representation:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Counter  │───▶│ Metadata │───▶│ Original │───▶│ Transform│
│  001     │    │   Date   │    │   Name   │    │ UPPERCASE│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │
     └───────────────┴───────────────┴───────────────┘
                              │
                              ▼
                     [ New Filename ]
```

The Node Editor would:
- Visualize the existing pipeline (not create new architecture)
- Allow drag-drop reordering (already supported)
- Show data flow between modules
- Enable conditional branches (future)

---

## Summary

| Aspect | Status |
|--------|--------|
| Core functionality | ✅ Complete |
| Module system | ✅ Extensible |
| Preview/Validation | ✅ Working |
| Undo/Redo | ✅ Persistent |
| Architecture clarity | ⚠️ Some overlap |
| Documentation | 📝 This document |

The Rename Engine is **production-ready** but would benefit from:
1. Consolidating dual preview paths
2. Clarifying manager responsibilities
3. Single point for post-transform application

These are **cleanup tasks**, not blockers.
