# UnifiedMetadataManager Refactoring Plan

**Author:** Michael Economou  
**Date:** 2026-01-02  
**Status:** In Progress

---

## Executive Summary

Extract remaining business logic from UnifiedMetadataManager (838 lines) by moving hash loading operations to a dedicated service.

**Current:** Facade with embedded hash loading logic (~140 lines)  
**Target:** Pure facade with all logic delegated (~500 lines, 40% reduction)

---

## Current State Analysis

### UnifiedMetadataManager (838 lines, 53 methods)

**Already Delegated ([x]):**
- `MetadataCacheService` — Cache operations
- `CompanionMetadataHandler` — Companion files
- `MetadataWriter` — Save operations  
- `MetadataShortcutHandler` — Keyboard shortcuts
- `MetadataProgressHandler` — Progress dialogs
- `MetadataLoader` — Metadata loading

**NOT Delegated ([FAIL] Extract these):**
- **Hash Loading** (~140 lines, lines 260-400):
  * `load_hashes_for_files()` — Orchestration
  * `_show_hash_progress_dialog()` — Progress UI
  * `_start_hash_loading()` — Worker creation
  * `_on_hash_progress()` — Progress handler
  * `_on_file_hash_calculated()` — Individual hash callback
  * `_on_hash_finished()` — Completion handler

- **Workers & Cleanup** (~100 lines):
  * `_cleanup_hash_worker_and_thread()` — Worker cleanup
  * `_cleanup_metadata_worker_and_thread()` — Worker cleanup
  * `cleanup()` — Master cleanup

---

## Migration Strategy

### Phase 1: Extract HashLoadingService

**Create:** `oncutf/core/metadata/hash_loading_service.py`

**Responsibilities:**
- Hash loading orchestration
- Progress dialog management
- Worker lifecycle management
- UI updates on hash completion

**Methods to extract:**
```python
class HashLoadingService:
    def load_hashes_for_files(files, source, cache_service, parent_window)
    def _show_hash_progress_dialog(files, source)
    def _start_hash_loading(files, source)
    def _on_hash_progress(current, total)
    def _on_file_hash_calculated(file_path, hash_value)
    def _on_hash_finished()
    def _cleanup_hash_worker()
    def cancel_loading()
```

**Target:** ~200 lines (includes error handling)

---

### Phase 2: Update UnifiedMetadataManager

**Remove hash loading methods** and delegate:

```python
# Before (838 lines):
class UnifiedMetadataManager(QObject):
    def load_hashes_for_files(self, files, source):
        # 30 lines of orchestration
        ...
    
    def _show_hash_progress_dialog(self, files, source):
        # 35 lines of dialog setup
        ...
    
    def _start_hash_loading(self, files, source):
        # 27 lines of worker setup
        ...
    
    def _on_file_hash_calculated(self, file_path, hash_value):
        # 28 lines of UI update
        ...
    
    def _on_hash_finished(self):
        # 20 lines of cleanup
        ...

# After (~500 lines):
class UnifiedMetadataManager(QObject):
    def __init__(self, parent_window):
        ...
        self._hash_service = HashLoadingService(parent_window, self._cache_service)
    
    def load_hashes_for_files(self, files, source):
        """Delegate to hash_service."""
        return self._hash_service.load_hashes_for_files(files, source)
    
    def _on_hash_finished(self):
        """Delegate to hash_service and handle UI updates."""
        self._hash_service.cleanup()
        self.loading_finished.emit()
        # UI refresh logic (can't be fully extracted)
```

---

## Implementation Plan

### Step 1: Create HashLoadingService (45 min)

1. Create `oncutf/core/metadata/hash_loading_service.py`
2. Extract hash loading methods
3. Add progress dialog management
4. Add worker lifecycle management
5. Add proper error handling

### Step 2: Update UnifiedMetadataManager (30 min)

1. Import HashLoadingService
2. Initialize in `__init__`
3. Replace hash loading methods with delegation
4. Keep minimal UI update logic
5. Update cleanup method

### Step 3: Testing & Validation (30 min)

1. Run all tests
2. Manual testing of hash loading
3. Verify progress dialogs work
4. Check cancellation works
5. Verify UI updates correctly

---

## Expected Results

| Component | Before | After | Change |
|-----------|--------|-------|--------|
| **UnifiedMetadataManager** | 838 lines | ~500 lines | **-338 lines (40%)** |
| **HashLoadingService** | 0 lines | ~200 lines | +200 lines (new) |
| **Net Change** | 838 lines | ~700 lines | **-138 lines (16%)** |

**Benefits:**
- [x] Clearer separation of concerns
- [x] HashLoadingService independently testable
- [x] UnifiedMetadataManager becomes purer facade
- [x] Better code organization

---

## Success Metrics

- [x] 949 tests passing (no regressions)
- [x] ruff clean
- [x] mypy clean
- [x] Hash loading functionality unchanged
- [x] Progress dialogs work correctly
- [x] Cancellation works correctly

---

## Timeline

**Total:** ~2 hours

1. Create HashLoadingService (45 min)
2. Update UnifiedMetadataManager (30 min)
3. Testing & validation (30 min)
4. Documentation updates (15 min)

---

## Next Steps

1. [x] Create migration plan
2. ⏭️ Create HashLoadingService
3. ⏭️ Extract hash loading methods
4. ⏭️ Update UnifiedMetadataManager to delegate
5. ⏭️ Run quality gates
6. ⏭️ Update REFACTORING_ROADMAP.md

