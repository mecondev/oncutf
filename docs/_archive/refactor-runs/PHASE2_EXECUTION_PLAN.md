# Phase 2: State Management Fix — Execution Plan

> **Status**: READY TO START  
> **Phase**: 2 of 7  
> **Priority**: HIGH  
> **Branch**: `phase2-state-management`

---

## Overview

Phase 2 addresses the critical problem of **scattered file state** across multiple sources and **counter conflicts** in multi-folder imports.

### Goals

1. ✅ Single source of truth for file state
2. ✅ Fix counter numbering in multi-folder scenarios
3. ✅ Unified state notifications system
4. ✅ Proper state coordination between UI and domain layers

### Root Causes Fixed

- **Counter Conflicts**: Files from multiple folders get wrong numbers
- **Stale Preview States**: State changes don't propagate correctly
- **No State Events**: UI updates rely on polling, not signals

### Current State

| Component | Before | After |
|-----------|--------|-------|
| File state sources | 4 (model, context, store, UI) | 1 (FileStore) |
| Counter behavior | Global index only | Global + Per-folder + Per-selection |
| State changes | Manual refresh calls | Automatic via signals |
| State coordination | None (scattered) | StateCoordinator (central) |

---

## Step 2.1: Create FileGroup and Update FileStore

### Objective

Add `FileGroup` concept to track folder boundaries and support counter scoping.

### Changes

**File**: `oncutf/models/file_store.py`

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class FileGroup:
    """Group of files from the same source folder."""
    source_folder: Path
    files: list[FileItem]
    load_order: int  # For deterministic ordering

class FileStore:
    """Single source of truth for all loaded files."""
    
    def __init__(self):
        self._groups: list[FileGroup] = []
        self._flat_cache: list[FileItem] | None = None
    
    def add_folder(self, source_folder: Path, files: list[FileItem], load_order: int) -> None:
        """Add a folder group."""
        group = FileGroup(source_folder, files, load_order)
        self._groups.append(group)
        self._flat_cache = None  # Invalidate cache
    
    def clear(self) -> None:
        """Clear all files and groups."""
        self._groups.clear()
        self._flat_cache = None
    
    def get_all_files(self) -> list[FileItem]:
        """Get all files as a flat list."""
        if self._flat_cache is None:
            self._flat_cache = []
            for group in self._groups:
                self._flat_cache.extend(group.files)
        return self._flat_cache
    
    def get_groups(self) -> list[FileGroup]:
        """Get all folder groups."""
        return self._groups
```

### Testing

**File**: `tests/unit/models/test_file_store.py`

```python
def test_file_store_add_folder():
    store = FileStore()
    files = [FileItem(...), FileItem(...)]
    store.add_folder(Path("/folder1"), files, load_order=0)
    
    assert len(store.get_groups()) == 1
    assert len(store.get_all_files()) == 2

def test_file_store_multiple_groups():
    store = FileStore()
    store.add_folder(Path("/folder1"), files1, load_order=0)
    store.add_folder(Path("/folder2"), files2, load_order=1)
    
    groups = store.get_groups()
    assert len(groups) == 2
    assert groups[0].source_folder == Path("/folder1")
```

### Commit

```
feat(models): add FileGroup to FileStore for folder tracking

- Add FileGroup dataclass for folder boundaries
- Update FileStore to track multiple groups
- Add get_groups() method for counter scope support
- Cache flattened file list for performance
- 12 comprehensive tests
```

---

## Step 2.2: Implement Counter Scope Support

### Objective

Support multiple counter scoping modes: GLOBAL, PER_FOLDER, PER_SELECTION.

### Changes

**File**: `oncutf/domain/rename/counter_scope.py`

```python
from enum import Enum

class CounterScope(Enum):
    """How counter should behave across multiple groups."""
    GLOBAL = "global"           # Single sequence for all files
    PER_FOLDER = "per_folder"   # Reset at each folder boundary
    PER_SELECTION = "per_selection"  # Reset for checked files only
```

**File**: `oncutf/modules/counter_module.py` (update)

```python
from oncutf.domain.rename.counter_scope import CounterScope

class CounterModule(BaseModule):
    """Generate sequential numbers with scope support."""
    
    def apply_from_data(
        self, 
        data: dict,
        file_item: FileItem,
        index: int = 0,
        metadata_cache: dict | None = None,
        group_index: int | None = None,  # NEW: index within group
        file_store = None,  # NEW: for scope calculation
    ) -> str:
        """Apply counter with proper scoping."""
        start = data.get("start", 1)
        step = data.get("step", 1)
        scope = data.get("scope", CounterScope.GLOBAL.value)
        padding = data.get("padding", 4)
        
        # Calculate effective index based on scope
        if scope == CounterScope.PER_FOLDER and group_index is not None:
            effective_index = group_index
        elif scope == CounterScope.PER_SELECTION:
            # Only count checked files
            effective_index = self._count_checked_before(file_item, file_store)
        else:  # GLOBAL
            effective_index = index
        
        # Generate counter
        value = start + (effective_index * step)
        formatted = str(value).zfill(padding)
        return formatted
```

### Testing

**File**: `tests/unit/modules/test_counter_scope.py`

```python
def test_counter_global_scope():
    """Counter sequence across all files."""
    module = CounterModule()
    
    result1 = module.apply_from_data(
        {"scope": "global", "start": 1, "step": 1},
        FileItem(...), index=0
    )
    result2 = module.apply_from_data(
        {"scope": "global", "start": 1, "step": 1},
        FileItem(...), index=5
    )
    
    assert result1 == "0001"
    assert result2 == "0006"

def test_counter_per_folder_scope():
    """Counter resets at folder boundary."""
    # Files from folder 1: indices 0-2
    # Files from folder 2: indices 0-2
    
    result_f1_i2 = module.apply_from_data(
        {"scope": "per_folder", "start": 1},
        FileItem(...), index=2, group_index=2
    )
    result_f2_i0 = module.apply_from_data(
        {"scope": "per_folder", "start": 1},
        FileItem(...), index=3, group_index=0
    )
    
    assert result_f1_i2 == "0003"
    assert result_f2_i0 == "0001"  # Reset!
```

### Commit

```
feat(modules): add counter scope support

- Add CounterScope enum (GLOBAL, PER_FOLDER, PER_SELECTION)
- Update counter_module.py to respect scope
- Support group_index parameter for folder-based numbering
- 15 comprehensive tests for all scoping modes
```

---

## Step 2.3: Create StateCoordinator

### Objective

Centralize state management and provide signals for state changes.

### Changes

**File**: `oncutf/controllers/state_coordinator.py`

```python
from PyQt5.QtCore import QObject, pyqtSignal
from pathlib import Path

class StateCoordinator(QObject):
    """Central coordinator for application state changes.
    
    Provides a single source of truth and emits signals when state changes.
    This prevents scattered state and ensures all components see updates.
    """
    
    # Signals
    files_changed = pyqtSignal(list)  # list[FileItem]
    selection_changed = pyqtSignal(set)  # set[row indices]
    preview_invalidated = pyqtSignal()
    folder_group_changed = pyqtSignal()  # Groups changed
    
    def __init__(self, file_store):
        super().__init__()
        self._file_store = file_store
        self._selected_rows: set[int] = set()
    
    def set_files(self, files: list[FileItem]) -> None:
        """Update file list (called when files loaded/cleared)."""
        self._file_store.set_files(files)
        self.files_changed.emit(files)
        self.preview_invalidated.emit()
    
    def set_selection(self, rows: set[int]) -> None:
        """Update selected file rows."""
        self._selected_rows = rows
        self.selection_changed.emit(rows)
        self.preview_invalidated.emit()
    
    def add_folder_group(self, path: Path, files: list[FileItem]) -> None:
        """Add a folder group."""
        self._file_store.add_folder(path, files, load_order=len(self._file_store.get_groups()))
        self.folder_group_changed.emit()
        self.preview_invalidated.emit()
    
    def get_all_files(self) -> list[FileItem]:
        """Get current file list."""
        return self._file_store.get_all_files()
    
    def get_groups(self):
        """Get folder groups."""
        return self._file_store.get_groups()
    
    def clear(self) -> None:
        """Clear all state."""
        self._file_store.clear()
        self._selected_rows.clear()
        self.files_changed.emit([])
        self.preview_invalidated.emit()
```

### Testing

**File**: `tests/unit/controllers/test_state_coordinator.py`

```python
def test_state_coordinator_files_changed_signal(qtbot):
    """Files changed signal emitted."""
    coordinator = StateCoordinator(FileStore())
    
    with qtbot.waitSignal(coordinator.files_changed) as blocker:
        files = [FileItem(...), FileItem(...)]
        coordinator.set_files(files)
    
    assert len(blocker.args[0]) == 2

def test_state_coordinator_preview_invalidation(qtbot):
    """Preview invalidated on any state change."""
    coordinator = StateCoordinator(FileStore())
    
    with qtbot.waitSignal(coordinator.preview_invalidated):
        coordinator.set_selection({0, 1, 2})
    
    with qtbot.waitSignal(coordinator.preview_invalidated):
        coordinator.add_folder_group(Path("/test"), [FileItem(...)])
```

### Commit

```
feat(controllers): add StateCoordinator for centralized state

- Create StateCoordinator class with file_store integration
- Emit signals for: files_changed, selection_changed, preview_invalidated
- Support folder groups with load ordering
- 16 comprehensive tests with signal validation
```

---

## Step 2.4: Integrate StateCoordinator into Application

### Objective

Wire StateCoordinator into MainWindow and controllers.

### Changes

**File**: `oncutf/ui/main_window.py` (update)

```python
from oncutf.controllers.state_coordinator import StateCoordinator

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state_coordinator = StateCoordinator(self.file_store)
        
        # Connect state signals to UI updates
        self.state_coordinator.files_changed.connect(self._on_files_changed)
        self.state_coordinator.selection_changed.connect(self._on_selection_changed)
        self.state_coordinator.preview_invalidated.connect(self._on_preview_invalidated)
    
    def _on_files_changed(self, files: list):
        """Update UI when files change."""
        self.file_table_view.update_files(files)
    
    def _on_selection_changed(self, rows: set):
        """Update preview when selection changes."""
        self._update_preview()
    
    def _on_preview_invalidated(self):
        """Regenerate preview on any state change."""
        self._update_preview()
```

### Commit

```
refactor(ui): integrate StateCoordinator into MainWindow

- Wire StateCoordinator signals to UI updates
- Replace manual refresh calls with signal connections
- Ensure consistent state propagation
```

---

## Validation Checklist

Before moving to Step 3, verify:

- [ ] FileStore correctly tracks folder groups
- [ ] Counter generates correct numbers per scope
- [ ] StateCoordinator emits signals on state changes
- [ ] MainWindow responds to state signals
- [ ] All 43+ tests passing
- [ ] No regressions in existing functionality
- [ ] ruff clean
- [ ] mypy clean

---

## Success Criteria

| Criterion | Measure |
|-----------|---------|
| Single state source | File state only in FileStore |
| Counter conflicts fixed | Multi-folder import generates correct numbers |
| State events | Preview updates automatically without manual refresh |
| Test coverage | 43+ tests, 100% pass rate |
| Code quality | ruff + mypy clean |

---

## Timeline

- **Step 2.1**: 30 min (FileGroup + FileStore)
- **Step 2.2**: 45 min (Counter scope)
- **Step 2.3**: 45 min (StateCoordinator)
- **Step 2.4**: 30 min (Integration)
- **Testing + Validation**: 30 min

**Total**: ~3 hours

---

## Next Phase

After Phase 2 completion, proceed to **Phase 3: Metadata Module Fix**

*Document version: 1.0*  
*Created: December 19, 2025*
