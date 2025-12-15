# Phase 1A: FileLoadController Methods Mapping

**Date:** 2025-12-15  
**Status:** Method identification complete

---

## Current Architecture

### Layer 1: MainWindow (UI)
- **File:** `oncutf/ui/main_window.py` (1309 lines)
- **Role:** UI event handlers, delegates to ApplicationService

### Layer 2: ApplicationService (Facade)
- **File:** `oncutf/core/application_service.py` (863 lines)
- **Role:** Facade pattern, delegates to managers
- **Problem:** Thin delegation layer with no orchestration logic

### Layer 3: FileLoadManager (Domain Service)
- **File:** `oncutf/core/file_load_manager.py` (661 lines)
- **Role:** Actual file loading implementation

---

## Problem Statement

**Current flow:**
```
MainWindow -> ApplicationService -> FileLoadManager
   (UI)           (thin facade)      (domain logic)
```

**Target flow:**
```
MainWindow -> FileLoadController -> FileLoadManager + other services
   (UI)        (orchestration)        (domain services)
```

**Why?**
- ApplicationService is too thin (just delegates, no orchestration)
- FileLoadController will add orchestration logic (validation, coordination, error handling)
- Better separation: UI → Controller (orchestration) → Services (implementation)

---

## Methods to Extract/Replace

### From MainWindow (oncutf/ui/main_window.py)

**File Loading Delegates (lines 280-315):**
```python
✓ load_files_from_folder(folder_path, force=False)         # Line 280
✓ load_files_from_paths(file_paths, clear=True)            # Line 284
✓ load_files_from_dropped_items(paths, modifiers)          # Line 287
✓ prepare_folder_load(folder_path, clear=True)             # Line 297
✓ load_single_item_from_drop(path, modifiers)              # Line 303
✓ _handle_folder_drop(folder_path, merge_mode, recursive)  # Line 308
✓ _handle_file_drop(file_path, merge_mode)                 # Line 312
```

**File Table Management:**
```python
✓ clear_file_table(message="No folder selected")           # Line 343
✓ prepare_file_table(file_items)                           # Line 339
```

**Total:** ~35 lines in MainWindow (simple delegates)

---

### From ApplicationService (oncutf/core/application_service.py)

**File Operations Section (lines 66-115):**
```python
✓ load_files_from_folder(folder_path, force=False)         # Line 70
✓ load_files_from_paths(file_paths, clear=True)            # Line 84
✓ load_files_from_dropped_items(paths, modifiers)          # Line 87
✓ prepare_folder_load(folder_path, clear=True)             # Line 93
✓ load_single_item_from_drop(path, modifiers)              # Line 96
✓ handle_folder_drop(folder_path, merge_mode, recursive)   # Line 102
✓ handle_file_drop(file_path, merge_mode)                  # Line 106
```

**Total:** ~50 lines in ApplicationService (thin delegates)

---

## FileLoadController Responsibilities

### 1. Orchestration Logic (NEW)
- **Validate paths** before loading
- **Coordinate** between FileLoadManager, FileStore, TableManager
- **Error handling** and user feedback
- **Progress tracking** for long operations
- **State management** (recursive mode, merge mode)

### 2. API Surface
```python
class FileLoadController:
    # Primary operations
    async def load_files(paths: List[Path]) -> dict
    async def load_folder(folder_path: Path, recursive: bool) -> dict
    def clear_files() -> bool
    
    # Drop handling
    async def handle_drop(paths: List[Path], modifiers: KeyboardModifiers) -> dict
    
    # State queries
    def get_loaded_file_count() -> int
    def is_recursive_mode() -> bool
    def set_recursive_mode(recursive: bool) -> None
```

### 3. Dependencies (Injected)
- `FileLoadManager` — low-level file operations
- `FileStore` — state management
- `TableManager` — UI table updates
- `ApplicationContext` — global state

---

## Lines of Code Estimates

### To Remove:
- MainWindow: ~35 lines (delegates)
- ApplicationService: ~50 lines (delegates)
- **Total removal:** ~85 lines

### To Add:
- FileLoadController: ~200-250 lines (orchestration + error handling)
- Tests: ~150 lines
- **Total addition:** ~350-400 lines

### Net Change:
- **+265-315 lines** (better separation, testability)

---

## Implementation Strategy

### Step 1A.3: Implement FileLoadController (2 hours)

**Actions:**
1. Keep ApplicationService + FileLoadManager intact
2. Implement FileLoadController with orchestration logic
3. Add proper error handling and logging
4. Add type hints and docstrings

**Logic to add:**
```python
# Path validation
- Check paths exist
- Filter by allowed extensions
- Handle symlinks/permissions

# Coordination
- Clear file store if needed
- Load via FileLoadManager
- Update TableManager
- Track progress

# Error handling
- Collect errors per file
- Return structured results
- Log operations

# State management
- Remember recursive mode
- Handle merge mode
- Coordinate with ApplicationContext
```

### Step 1A.4: Wire to MainWindow (1 hour)

**Feature flag approach:**
```python
# In MainWindow.__init__()
self._use_file_load_controller = True  # Feature flag

if self._use_file_load_controller:
    from oncutf.controllers.file_load_controller import FileLoadController
    self._file_load_controller = FileLoadController(
        file_load_manager=self.file_load_manager,
        file_store=self.file_store,
        table_manager=self.table_manager,
        context=self.context
    )

# In load_files_from_folder()
if self._use_file_load_controller:
    result = await self._file_load_controller.load_folder(folder_path, recursive)
else:
    self.app_service.load_files_from_folder(folder_path)  # Fallback
```

### Step 1A.5: Remove Old Code (30 min)

**Actions:**
1. Remove feature flag
2. Remove delegates from MainWindow
3. Remove file operations from ApplicationService
4. Update all call sites

### Step 1A.6: Cleanup (30 min)

**Actions:**
1. Remove unused imports
2. Update docstrings
3. Run tests, ruff, mypy
4. Manual smoke test

---

## Testing Strategy

### Unit Tests (tests/test_file_load_controller.py)

```python
def test_load_files_with_valid_paths():
    """Test loading valid file paths."""
    
def test_load_files_with_invalid_paths():
    """Test error handling for invalid paths."""
    
def test_load_folder_recursive():
    """Test recursive folder loading."""
    
def test_handle_drop_with_modifiers():
    """Test drop handling with keyboard modifiers."""
    
def test_clear_files():
    """Test clearing loaded files."""
```

### Integration Tests
- Drag & drop files → verify loaded
- Load folder recursively → verify all files found
- Load with merge mode → verify existing files retained

---

## Success Criteria

✅ **FileLoadController exists and works**
- All methods implemented with orchestration logic
- Proper error handling and logging
- Type hints and docstrings complete

✅ **MainWindow uses controller**
- Calls FileLoadController instead of ApplicationService
- Feature flag tested (both on/off work identically)

✅ **Old code removed**
- No duplicate logic in ApplicationService
- No unused delegates in MainWindow

✅ **All tests pass**
- 549 existing tests + new controller tests
- No regressions

✅ **Manual verification**
- Drag & drop works
- Load folder works
- Recursive mode works
- Clear files works

---

## Next Steps

**Current:** Step 1A.2 complete ✅

**Next:** Step 1A.3 - Implement FileLoadController.load_files() (2 hours)

Ready to proceed!
