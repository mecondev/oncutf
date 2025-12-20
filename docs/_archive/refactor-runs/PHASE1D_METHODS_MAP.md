# Phase 1D: Orchestration Methods Map

**Date:** 2025-12-16  
**Status:** Analysis Complete  
**Purpose:** Identify orchestration methods to move from MainWindow to MainWindowController

---

## Analysis Summary

After analyzing MainWindow (1334 lines), most business logic has already been delegated to:
- **ApplicationService** (high-level application operations)
- **FileLoadController** (Phase 1A - file loading)
- **MetadataController** (Phase 1B - metadata operations)
- **RenameController** (Phase 1C - rename operations)

**Current MainWindow state:** Mostly thin wrappers that delegate to services/controllers.

---

## Orchestration Methods Remaining

### Category 1: Already Delegated (No Action Needed)

Most methods in MainWindow are already thin wrappers:

```python
# Examples of already-delegated methods:
def handle_browse(self) -> None:
    self.app_service.handle_browse()

def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
    result = self.file_load_controller.load_files(file_paths, clear=clear)

def load_metadata_for_items(self, items: list[FileItem], use_extended: bool = False) -> None:
    result = self.metadata_controller.load_metadata(items, use_extended, source)
```

**Status:** ✅ Already using controllers - no orchestration logic to move.

---

### Category 2: Complex Workflows (Candidates for MainWindowController)

These methods coordinate multiple services/controllers and contain orchestration logic:

#### 🔴 High Priority (Should Move to MainWindowController)

1. **`restore_last_folder_if_available()` + file/metadata loading workflow**
   - **Location:** Line 695
   - **Current:** Delegates to WindowConfigManager
   - **Orchestration:** Restores folder → loads files → optionally loads metadata
   - **Complexity:** Medium (multi-step workflow across services)
   - **Estimated Lines:** ~30-50 (including full workflow)
   - **Recommendation:** Create `restore_last_session_workflow()` in MainWindowController

2. **Window state change + file table refresh workflow**
   - **Methods:** `_handle_window_state_change()`, `_refresh_file_table_for_window_change()`
   - **Location:** Lines 768-810
   - **Current:** Handles window maximize/restore + table refresh
   - **Orchestration:** State change → geometry update → table refresh → splitter adjust
   - **Complexity:** Medium (coordinates UI state + table updates)
   - **Estimated Lines:** ~40-60
   - **Recommendation:** Could stay in MainWindow (mostly UI state management)

3. **Metadata edit/reset workflows**
   - **Methods:** `on_metadata_value_edited()`, `on_metadata_value_reset()`
   - **Location:** Lines 560-600
   - **Current:** Handles metadata changes + command execution
   - **Orchestration:** Validate → execute command → refresh UI
   - **Complexity:** Medium (coordinates metadata manager + command system + UI)
   - **Estimated Lines:** ~50-70
   - **Recommendation:** **Move to MainWindowController** as `handle_metadata_edit_workflow()`

#### 🟡 Medium Priority (Consider Moving)

4. **File drop handling with modifiers**
   - **Method:** `load_files_from_dropped_items()`
   - **Location:** Lines 295-304
   - **Current:** Delegates to FileLoadController
   - **Orchestration:** Parse modifiers → determine mode → load files
   - **Complexity:** Low-Medium (mostly delegation)
   - **Estimated Lines:** ~10-15
   - **Recommendation:** Keep in MainWindow (thin wrapper)

5. **Shutdown coordination**
   - **Methods:** `closeEvent()`, `_start_coordinated_shutdown()`, `_pre_coordinator_cleanup()`, `_post_coordinator_cleanup()`
   - **Location:** Lines 814-1044
   - **Current:** Complex shutdown workflow with multiple phases
   - **Orchestration:** Check unsaved → cleanup workers → save config → close
   - **Complexity:** High (critical shutdown logic)
   - **Estimated Lines:** ~200+
   - **Recommendation:** **Partially move** orchestration to MainWindowController, keep UI-specific parts in MainWindow

#### 🟢 Low Priority (Keep in MainWindow)

6. **UI event handlers**
   - **Methods:** `resizeEvent()`, `changeEvent()`, `eventFilter()`
   - **Location:** Various
   - **Orchestration:** Minimal (mostly UI state updates)
   - **Recommendation:** Keep in MainWindow (pure UI)

7. **Window configuration management**
   - **Methods:** `_load_window_config()`, `_save_window_config()`, `_apply_loaded_config()`
   - **Location:** Lines 625-670
   - **Current:** Delegates to WindowConfigManager
   - **Orchestration:** Minimal (thin wrappers)
   - **Recommendation:** Keep in MainWindow (already delegated)

---

## Methods to Move to MainWindowController

### Summary Table

| Priority | Method | Lines | Complexity | New Controller Method |
|----------|--------|-------|------------|----------------------|
| 🔴 High | `restore_last_folder_if_available` + workflow | ~50 | Medium | `restore_last_session_workflow()` |
| 🔴 High | `on_metadata_value_edited/reset` | ~70 | Medium | `handle_metadata_edit_workflow()` |
| 🟡 Medium | Shutdown coordination (partial) | ~100 | High | `coordinate_shutdown_workflow()` |

**Total estimated lines to move:** ~220

**Total estimated methods:** 3-4 major orchestration workflows

---

## Detailed Method Analysis

### 1. `restore_last_session_workflow()` (NEW)

**Current State:**
```python
# MainWindow (line 695)
def restore_last_folder_if_available(self) -> None:
    self.window_config_manager.restore_last_folder_if_available()
```

**Proposed MainWindowController Method:**
```python
async def restore_last_session_workflow(
    self,
    load_metadata: bool = True,
    prompt_user: bool = True
) -> dict:
    """
    Orchestrate session restoration workflow.
    
    Workflow:
    1. Check if last folder exists in config
    2. Optionally prompt user
    3. Load files from last folder
    4. Optionally load metadata
    5. Restore selection/scroll state
    
    Returns:
        dict: {
            'success': bool,
            'folder_restored': bool,
            'files_loaded': int,
            'metadata_loaded': int,
            'errors': List[str]
        }
    """
```

**Orchestrates:**
- WindowConfigManager (get last folder)
- FileLoadController (load files)
- MetadataController (load metadata)
- UI state restoration

**Complexity:** Medium  
**Estimated Lines:** ~60-80

---

### 2. `handle_metadata_edit_workflow()` (NEW)

**Current State:**
```python
# MainWindow (lines 560-600)
def on_metadata_value_edited(self, key_path: str, old_value: str, new_value: str) -> None:
    # Complex logic with command execution, validation, refresh
    ...

def on_metadata_value_reset(self, key_path: str) -> None:
    # Complex logic with command execution, refresh
    ...
```

**Proposed MainWindowController Method:**
```python
def handle_metadata_edit_workflow(
    self,
    operation: str,  # 'edit' or 'reset'
    key_path: str,
    new_value: Optional[str] = None,
    file_items: Optional[List[FileItem]] = None
) -> dict:
    """
    Orchestrate metadata edit/reset workflow.
    
    Workflow:
    1. Validate operation
    2. Create and execute command
    3. Update cache
    4. Refresh UI widgets
    5. Emit signals
    
    Returns:
        dict: {
            'success': bool,
            'command_id': str,
            'affected_files': int,
            'errors': List[str]
        }
    """
```

**Orchestrates:**
- MetadataController (execute edit/reset)
- MetadataCommandManager (command execution)
- CacheManager (update cache)
- SignalCoordinator (refresh signals)

**Complexity:** Medium  
**Estimated Lines:** ~70-90

---

### 3. `coordinate_shutdown_workflow()` (NEW)

**Current State:**
```python
# MainWindow (lines 814-1044)
def closeEvent(self, event) -> None:
    # Check unsaved changes
    # Start coordinated shutdown
    ...

def _start_coordinated_shutdown(self):
    # Cleanup workers, save config, etc.
    ...
```

**Proposed MainWindowController Method:**
```python
async def coordinate_shutdown_workflow(
    self,
    force: bool = False
) -> dict:
    """
    Orchestrate application shutdown workflow.
    
    Workflow:
    1. Check for unsaved changes (unless force=True)
    2. Save configuration
    3. Cleanup background workers
    4. Stop metadata threads
    5. Cleanup ExifTool
    6. Emit shutdown complete signal
    
    Returns:
        dict: {
            'success': bool,
            'can_close': bool,
            'cleanup_errors': List[str]
        }
    """
```

**Orchestrates:**
- ConfigManager (save config)
- ThreadPoolManager (cleanup workers)
- MetadataManager (stop threads)
- ExifToolWrapper (cleanup)
- All controllers (cleanup)

**Complexity:** High  
**Estimated Lines:** ~100-150

**Note:** Some UI-specific parts (QCloseEvent handling, window geometry) should stay in MainWindow.

---

## Implementation Priority

### Phase 1D.3-1D.6: Implementation Order

1. **Step 1D.3:** `restore_last_session_workflow()` (simplest, good starting point)
   - Estimated time: 1 hour
   - Low risk

2. **Step 1D.6a:** `handle_metadata_edit_workflow()` (medium complexity)
   - Estimated time: 1.5 hours
   - Medium risk

3. **Step 1D.6b:** `coordinate_shutdown_workflow()` (optional, most complex)
   - Estimated time: 2+ hours
   - Higher risk (critical path)
   - **Recommendation:** Consider postponing to Phase 2 if time-constrained

---

## Alternative: Minimal MainWindowController

Given that most logic is already in controllers/services, MainWindowController could be **minimal** and focus on:

### Option A: Full Orchestration (Original Plan)
- Move all 3 workflows above
- ~220 lines of new orchestration code
- 3-4 new methods
- Time: ~4-5 hours

### Option B: Minimal Orchestration (Lightweight)
- Only move `restore_last_session_workflow()`
- Keep metadata edit/shutdown in MainWindow (already working)
- ~80 lines of new code
- 1 new method
- Time: ~1-2 hours

### Option C: Hybrid (Recommended)
- Move `restore_last_session_workflow()` ✅
- Move `handle_metadata_edit_workflow()` ✅
- Keep shutdown in MainWindow (complex, working)
- ~150 lines of new code
- 2 new methods
- Time: ~2.5-3 hours

---

## Recommendation

**Proceed with Option C (Hybrid Approach):**

1. **Step 1D.3:** Implement `restore_last_session_workflow()`
   - Simplest, clear orchestration value
   - Good demonstration of MainWindowController purpose

2. **Step 1D.6:** Implement `handle_metadata_edit_workflow()`
   - Medium complexity, real orchestration need
   - Improves testability of metadata editing

3. **Skip:** `coordinate_shutdown_workflow()` (for now)
   - Already working well
   - High complexity, critical path
   - Can be Phase 2 if needed

**Estimated Total:**
- 2 orchestration methods
- ~150 lines of code
- ~3 hours work (with tests)
- Low-medium risk

---

## Success Criteria

**MainWindowController will be considered complete when:**

1. ✅ It exists and is wired to MainWindow
2. ✅ It orchestrates at least 2 multi-controller workflows
3. ✅ It has >85% test coverage
4. ✅ MainWindow complexity is reduced
5. ✅ All existing tests pass
6. ✅ No regressions in functionality

---

## Next Steps

**Proceed to Step 1D.3:**
- Implement `restore_last_session_workflow()` in MainWindowController
- Write comprehensive tests
- Wire to MainWindow with feature flag

**Time Estimate:** 1 hour for implementation + 30 min for tests = 1.5 hours total
