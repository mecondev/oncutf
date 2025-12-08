# Streaming Metadata Integration - Implementation Plan

**Date:** 2025-12-08  
**Status:** Planning Phase  
**Estimated Effort:** 1-2 days  
**Priority:** #1 in Pragmatic Refactoring Plan

---

## Executive Summary

Integrate the existing `load_metadata_streaming()` method (already implemented in `unified_metadata_manager.py`) into the UI workflow to provide progressive metadata loading with visual feedback. This will improve perceived performance and keep the UI responsive when loading metadata for large file sets.

**Current State:**
- ✅ `load_metadata_streaming()` method exists in `UnifiedMetadataManager` (lines 694-775)
- ✅ Uses parallel loading with ThreadPoolExecutor
- ✅ Yields (FileItem, metadata) tuples as they complete
- ✅ Checks cache before loading
- ❌ **Not used anywhere in the UI** (grep shows only documentation references)

**Goal:**
- Use streaming method in drag-drop workflow
- Show per-file loading indicators in table
- Keep UI responsive during long operations
- Maintain existing cache behavior and test coverage

---

## Architecture Analysis

### Current Metadata Loading Flow

```
User Action (drag/drop, shortcut)
    ↓
ApplicationService.load_metadata_for_items()
    ↓
UnifiedMetadataManager.load_metadata_for_items()
    ↓
[Blocking] Load all metadata with ProgressDialog
    ↓
Update all FileItems at once
    ↓
Emit signals → UI refresh
```

**Problems:**
1. **Blocking**: User sees progress dialog but can't interact
2. **All-or-nothing**: No partial results until completion
3. **Poor feedback**: No per-file status indication

### Target Streaming Flow

```
User Action (drag/drop with metadata option)
    ↓
ApplicationService.load_metadata_streaming()
    ↓
UnifiedMetadataManager.load_metadata_streaming()
    ↓
[Progressive] Yield (item, metadata) as available
    ↓
Update FileItem + table row immediately
    ↓
Show loading indicator → checkmark as each completes
    ↓
UI remains responsive (ESC to cancel)
```

**Benefits:**
1. **Non-blocking**: User can cancel, scroll, or do other work
2. **Progressive**: See results as they arrive
3. **Better feedback**: Per-file indicators show status
4. **Perceived speed**: Feels faster even if total time is same

---

## Implementation Phases

### Phase 1: Add Streaming Helper Method ✅ LOW RISK

**File:** `core/application_service.py`  
**Action:** Add new method `load_metadata_streaming()` that wraps the manager method

**Why separate from existing?**
- Preserve existing `load_metadata_for_items()` behavior (100% backward compatible)
- Allow gradual migration (can test streaming in isolation)
- Fallback to old method if streaming fails

**Implementation:**
```python
def load_metadata_streaming(
    self, items: list[FileItem], use_extended: bool = False, source: str = "unknown"
):
    """
    Load metadata progressively using streaming approach.
    
    Yields:
        Tuple[FileItem, dict]: (item, metadata) as each completes
    """
    logger.info(f"[{source}] Starting streaming metadata load for {len(items)} items")
    
    manager = self.main_window.metadata_manager
    
    # Use the existing streaming method
    for item, metadata in manager.load_metadata_streaming(items, use_extended=use_extended):
        # Update item (already done in manager, but ensure it's set)
        item.metadata = metadata
        item.metadata_status = "extended" if use_extended else "loaded"
        
        yield item, metadata
```

**Testing:**
- Run existing tests (no changes to old code)
- Add simple test: call new method, collect all results
- Verify same results as non-streaming version

**Risk:** ⚠️ **VERY LOW** (only adds new code, doesn't modify existing)

---

### Phase 2: Add UI Update Hook in FileTableModel ✅ LOW RISK

**File:** `models/file_table_model.py`  
**Action:** Add method to update single row's metadata status icon

**Current behavior:**
- Icon shown in column 0 via `data(role=Qt.DecorationRole)`
- Icon determined by `item.metadata_status` property
- Model already has `self.metadata_icons` dictionary

**Implementation:**
```python
def update_row_metadata_status(self, row: int, metadata_status: str) -> None:
    """
    Update metadata status for a single row.
    Used during streaming metadata loading.
    
    Args:
        row: Row index in current model
        metadata_status: New status ("none", "loaded", "extended", "modified")
    """
    if not 0 <= row < len(self.files):
        return
    
    # Update the FileItem
    self.files[row].metadata_status = metadata_status
    
    # Emit dataChanged for column 0 only (icon column)
    idx = self.index(row, 0)
    self.dataChanged.emit(idx, idx, [Qt.DecorationRole])
```

**Why this approach?**
- Minimal disruption (only emits signal for 1 cell)
- Uses existing icon rendering logic
- No new UI components needed
- Already tested via existing metadata loading

**Testing:**
- Load files, call method manually, verify icon updates
- Check that dataChanged signal is received by view

**Risk:** ⚠️ **VERY LOW** (uses existing mechanisms, minimal scope)

---

### Phase 3: Add Streaming Controller in FileLoadManager 🟡 MEDIUM RISK

**File:** `core/file_load_manager.py`  
**Action:** Add method to orchestrate streaming load with UI updates

**Current behavior:**
- `load_files_from_dropped_items()` handles drop events
- After loading files, optionally loads metadata via `load_metadata_for_items()`
- Uses blocking approach with ProgressDialog

**Implementation:**
```python
def _load_metadata_streaming_for_drop(
    self, items: list[FileItem], use_extended: bool
) -> None:
    """
    Load metadata for dropped files using streaming approach.
    Updates UI progressively as metadata arrives.
    
    Args:
        items: FileItems to load metadata for
        use_extended: Whether to load extended metadata
    """
    if not items:
        return
    
    logger.info(f"[FileLoadManager] Starting streaming metadata load for {len(items)} files")
    
    # Build row mapping (model index may differ from file order)
    file_to_row = {}
    for row, file_item in enumerate(self.parent_window.file_model.files):
        file_to_row[file_item.full_path] = row
    
    # Track progress
    loaded_count = 0
    total_count = len(items)
    
    # Update status bar to show progress
    if hasattr(self.parent_window, "status_manager"):
        self.parent_window.status_manager.show_message(
            f"Loading metadata: 0/{total_count}...", timeout=0
        )
    
    # Stream metadata results
    try:
        for item, metadata in self.parent_window.app_service.load_metadata_streaming(
            items, use_extended=use_extended, source="drag-drop"
        ):
            loaded_count += 1
            
            # Find row for this item
            row = file_to_row.get(item.full_path)
            if row is not None:
                # Update model (triggers icon update)
                status = "extended" if use_extended else "loaded"
                self.parent_window.file_model.update_row_metadata_status(row, status)
            
            # Update status bar
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.show_message(
                    f"Loading metadata: {loaded_count}/{total_count}...", timeout=0
                )
            
            # Process events to keep UI responsive (every 5 files)
            if loaded_count % 5 == 0:
                QApplication.processEvents()
        
        # Final status message
        if hasattr(self.parent_window, "status_manager"):
            self.parent_window.status_manager.show_message(
                f"Loaded metadata for {loaded_count} files", timeout=3000
            )
        
        logger.info(f"[FileLoadManager] Completed streaming metadata load: {loaded_count}/{total_count}")
        
    except Exception as e:
        logger.error(f"[FileLoadManager] Streaming metadata load failed: {e}")
        if hasattr(self.parent_window, "status_manager"):
            self.parent_window.status_manager.show_message(
                f"Metadata loading error: {e}", timeout=5000
            )
```

**Why this approach?**
- Self-contained (all streaming logic in one place)
- Optional feature (doesn't replace existing workflow yet)
- Easy to test (can call manually with test files)
- Respects existing architecture (uses app_service layer)

**Testing:**
- Drop 10 files, verify progressive icon updates
- Drop 100 files, verify UI stays responsive
- Cancel operation mid-stream (Ctrl+C or close window)

**Risk:** 🟡 **MEDIUM** (new workflow, needs thorough testing)

---

### Phase 4: Integrate Streaming into Drop Workflow 🟡 MEDIUM RISK

**File:** `core/file_load_manager.py`  
**Action:** Add option to use streaming method in drop handler

**Current behavior:**
- `load_files_from_dropped_items()` loads files immediately
- No automatic metadata loading on drop (user must press F5/F6)

**Implementation:**
```python
def load_files_from_dropped_items(
    self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier
) -> None:
    """
    Handle multiple dropped items (table drop).
    
    Modifiers:
        Ctrl: Recursive folder scan
        Shift: Merge mode (add to existing files)
        Alt: Auto-load basic metadata (NEW)
        Alt+Shift: Auto-load extended metadata (NEW)
    """
    if not paths:
        logger.info("[Drop] No files dropped in table.")
        return
    
    # Parse modifiers
    ctrl = bool(modifiers & Qt.ControlModifier)
    shift = bool(modifiers & Qt.ShiftModifier)
    alt = bool(modifiers & Qt.AltModifier)
    
    recursive = ctrl
    merge_mode = shift
    auto_metadata = alt  # NEW: Auto-load metadata on drop
    use_extended = alt and shift  # NEW: Extended metadata with Alt+Shift
    
    # ... existing file loading logic ...
    
    # NEW: Auto-load metadata if Alt key pressed
    if auto_metadata and all_file_paths:
        # Convert paths to FileItems
        file_items = [
            item for item in self.parent_window.file_model.files
            if item.full_path in set(all_file_paths)
        ]
        
        # Use streaming load for better UX
        self._load_metadata_streaming_for_drop(file_items, use_extended=use_extended)
```

**User Experience:**
- **Before:** Drop files → press F5 → wait for progress dialog → done
- **After:** Drop files with Alt → see progressive loading → done
- **Backward compatible:** Drop without Alt = same as before

**Testing:**
- Drop files without modifiers (should work as before)
- Drop with Alt (should load basic metadata progressively)
- Drop with Alt+Shift (should load extended metadata progressively)

**Risk:** 🟡 **MEDIUM** (changes user workflow, needs testing)

---

## Safety Measures

### 1. Backward Compatibility ✅

**Principle:** Never break existing functionality

**Implementation:**
- ✅ Keep all existing methods unchanged
- ✅ Add new methods alongside (not replacing)
- ✅ New feature is opt-in (requires modifier key)
- ✅ Fallback to old behavior if streaming fails

**Validation:**
- Run full test suite before and after each phase
- Verify existing shortcuts (F5/F6) work identically
- Test all drag/drop scenarios without Alt key

---

### 2. Incremental Testing 🧪

**Principle:** Test each phase before proceeding

**Phase 1 Testing:**
```bash
# Add test case
def test_streaming_metadata_basic():
    items = [FileItem.from_path("test1.jpg"), FileItem.from_path("test2.jpg")]
    results = list(app_service.load_metadata_streaming(items))
    assert len(results) == 2
    assert all(item.metadata for item, _ in results)
```

**Phase 2 Testing:**
```python
# Manual test in debug mode
model.update_row_metadata_status(0, "loaded")
# Verify icon changes in UI
```

**Phase 3 Testing:**
```bash
# Drop 10 files with debug logging enabled
# Check log output for progressive updates
# Verify final state matches non-streaming version
```

**Phase 4 Testing:**
```bash
# Test matrix:
# - Drop without modifiers (old behavior)
# - Drop with Alt (basic metadata streaming)
# - Drop with Alt+Shift (extended metadata streaming)
# - Mix of cached and non-cached files
```

---

### 3. Rollback Plan 🔄

**If Phase 1-2 fail:**
- Simply delete new methods (no existing code changed)
- Zero impact on production code

**If Phase 3 fails:**
- Comment out `_load_metadata_streaming_for_drop()` method
- Old workflow unaffected

**If Phase 4 fails:**
- Remove Alt key handling in drop handler
- Reverts to current behavior

**Git strategy:**
- Each phase = separate commit
- Commit message: "Phase N: [description] - NO BREAKING CHANGES"
- Easy to revert individual phases via `git revert`

---

## Testing Strategy

### Unit Tests (Phase 1-2)

```python
# tests/test_streaming_metadata.py

def test_streaming_returns_all_items():
    """Verify streaming yields all items."""
    items = create_test_items(10)
    results = list(app_service.load_metadata_streaming(items))
    assert len(results) == 10

def test_streaming_respects_cache():
    """Verify streaming uses cached metadata."""
    items = create_test_items(5)
    # Pre-cache first 3 items
    for item in items[:3]:
        cache.set(item.full_path, {"test": "data"})
    
    results = list(app_service.load_metadata_streaming(items))
    # Should get all 5 items (3 from cache, 2 loaded)
    assert len(results) == 5

def test_model_update_changes_icon():
    """Verify model update triggers icon change."""
    model = FileTableModel()
    model.set_files([create_test_item()])
    
    # Get initial icon
    idx = model.index(0, 0)
    icon_before = model.data(idx, Qt.DecorationRole)
    
    # Update status
    model.update_row_metadata_status(0, "loaded")
    
    # Get new icon
    icon_after = model.data(idx, Qt.DecorationRole)
    
    assert icon_before != icon_after
```

### Integration Tests (Phase 3-4)

```python
# tests/test_streaming_integration.py

def test_drop_with_alt_loads_metadata(qtbot):
    """Verify Alt+Drop triggers streaming metadata load."""
    main_window = create_test_window()
    
    # Simulate drop with Alt modifier
    paths = ["/path/to/test1.jpg", "/path/to/test2.jpg"]
    modifiers = Qt.AltModifier
    
    main_window.file_load_manager.load_files_from_dropped_items(paths, modifiers)
    
    # Wait for streaming to complete
    qtbot.wait(1000)
    
    # Verify metadata loaded
    files = main_window.file_model.files
    assert all(file.has_metadata for file in files)
```

### Manual Testing Checklist

**Phase 1:**
- [ ] Call `app_service.load_metadata_streaming()` with 10 files
- [ ] Verify yields 10 results
- [ ] Check each result has (FileItem, metadata) format
- [ ] Verify metadata matches non-streaming version

**Phase 2:**
- [ ] Load files into table
- [ ] Call `model.update_row_metadata_status(0, "loaded")`
- [ ] Verify icon changes in row 0
- [ ] Repeat for all rows
- [ ] Verify no crashes or errors

**Phase 3:**
- [ ] Drop 10 files
- [ ] Call `_load_metadata_streaming_for_drop()` manually
- [ ] Watch status bar for progress updates
- [ ] Verify all icons update progressively
- [ ] Check final state matches expected

**Phase 4:**
- [ ] Drop files without modifiers (should load files only)
- [ ] Drop files with Alt (should load + stream basic metadata)
- [ ] Drop files with Alt+Shift (should load + stream extended metadata)
- [ ] Drop large file set (100+) and verify UI stays responsive
- [ ] Press Ctrl+C during loading (should cancel gracefully)

---

## Performance Considerations

### Expected Behavior

**Small file sets (< 10 files):**
- Streaming overhead = ~50ms
- User won't notice difference
- Still beneficial for consistency

**Medium file sets (10-50 files):**
- Progressive updates feel faster
- User sees results after ~100ms
- Much better than 5s blocking dialog

**Large file sets (50+ files):**
- Significant UX improvement
- UI responsive throughout
- Can cancel if taking too long

### Optimization Notes

**From existing `load_metadata_streaming()` code:**
- ✅ Uses ThreadPoolExecutor (parallel loading)
- ✅ Checks cache before loading (avoids duplicate work)
- ✅ Uses `as_completed()` (yields as soon as each finishes)
- ✅ max_workers = min(cpu_count * 2, 16) (good defaults)

**UI Update Frequency:**
- Current plan: Update every item (may be too frequent)
- Consider: Batch updates every 5 items (reduce signal overhead)
- Fallback: `processEvents()` every 5 items (current plan)

---

## Documentation Updates

### User-Facing

**File:** `docs/keyboard_shortcuts.md`

Add section:
```markdown
### Drag & Drop Modifiers

| Modifier | Action |
|----------|--------|
| None | Load files only |
| Ctrl | Recursive folder scan |
| Shift | Merge with existing files |
| Alt | Load files + basic metadata (streaming) |
| Alt+Shift | Load files + extended metadata (streaming) |
```

### Developer-Facing

**File:** `docs/architecture/streaming_metadata_system.md` (new)

Document:
- Architecture decision: why streaming vs blocking
- Flow diagrams: before/after
- API reference: new methods
- Testing guide: how to verify streaming works
- Troubleshooting: common issues

---

## Success Criteria

### Phase 1 ✅
- [ ] New method exists in `application_service.py`
- [ ] Yields correct format: `(FileItem, dict)`
- [ ] All existing tests pass
- [ ] Can collect all results into list (same as non-streaming)

### Phase 2 ✅
- [ ] New method exists in `file_table_model.py`
- [ ] Updates single row icon without full refresh
- [ ] Emits `dataChanged` signal correctly
- [ ] Icon rendering matches existing behavior

### Phase 3 🟡
- [ ] New method exists in `file_load_manager.py`
- [ ] Updates status bar progressively
- [ ] Updates table icons progressively
- [ ] Handles exceptions gracefully
- [ ] UI stays responsive (can scroll, select)

### Phase 4 🟡
- [ ] Alt key triggers streaming load
- [ ] Alt+Shift triggers extended streaming load
- [ ] No modifiers = existing behavior (unchanged)
- [ ] All manual tests pass
- [ ] Performance acceptable (< 5s for 100 files)

### Overall ✅
- [ ] All 460 existing tests pass
- [ ] No regressions in existing workflows
- [ ] User documentation updated
- [ ] Developer documentation added
- [ ] Code reviewed and committed

---

## Timeline

**Day 1 (Morning):**
- Phase 1: Add ApplicationService method (1 hour)
- Phase 2: Add FileTableModel method (1 hour)
- Testing: Verify phases 1-2 (1 hour)

**Day 1 (Afternoon):**
- Phase 3: Add FileLoadManager orchestration (2 hours)
- Testing: Manual testing with debug logging (1 hour)

**Day 2 (Morning):**
- Phase 4: Integrate into drop workflow (1 hour)
- Testing: Full test matrix (2 hours)

**Day 2 (Afternoon):**
- Documentation updates (1 hour)
- Code review and cleanup (1 hour)
- Final testing and commit (1 hour)

**Total: 12 hours across 2 days**

---

## Decision Points

### Go/No-Go After Phase 2

**Decision criteria:**
- ✅ Both methods work in isolation
- ✅ All existing tests pass
- ✅ No performance degradation

**If NO:** Stop here, no harm done (only added new unused methods)

### Go/No-Go After Phase 3

**Decision criteria:**
- ✅ Streaming load works for test files
- ✅ UI updates progressively
- ✅ No crashes or deadlocks
- ✅ Performance acceptable

**If NO:** Comment out Phase 3 method, document why it failed

### Go/No-Go After Phase 4

**Decision criteria:**
- ✅ All modifier combinations work
- ✅ No regressions in existing workflows
- ✅ User testing feedback positive
- ✅ Performance meets targets

**If NO:** Revert Phase 4 changes, keep Phase 1-3 for future use

---

## Risks and Mitigations

### Risk 1: UI Freezes During Streaming 🔴

**Likelihood:** Low  
**Impact:** High  
**Mitigation:**
- Use `QApplication.processEvents()` every N items
- Add cancellation check (ESC key or close button)
- Fallback to non-streaming if detected

### Risk 2: Icon Updates Cause Flicker 🟡

**Likelihood:** Medium  
**Impact:** Low  
**Mitigation:**
- Only emit `dataChanged` for single cell (not whole row)
- Use Qt's update optimization flags
- Batch updates if flicker persists

### Risk 3: Cache Invalidation Issues 🟡

**Likelihood:** Medium  
**Impact:** Medium  
**Mitigation:**
- Existing `load_metadata_streaming()` already handles cache
- No changes to cache logic (use as-is)
- Test with mixed cached/uncached files

### Risk 4: Race Conditions 🟡

**Likelihood:** Medium  
**Impact:** High  
**Mitigation:**
- All updates happen on main thread
- Use file path as stable identifier
- Build row mapping before iteration starts
- Don't modify file list during streaming

### Risk 5: Breaking Existing Tests 🔴

**Likelihood:** Very Low  
**Impact:** High  
**Mitigation:**
- No changes to existing methods (only additions)
- Run tests after each phase
- Keep phases independent (easy to revert)

---

## Alternative Approaches Considered

### Alternative 1: Async/Await with asyncio

**Pros:**
- Modern Python pattern
- Better for I/O-bound operations

**Cons:**
- PyQt5 + asyncio integration is complex
- Would require major refactoring
- Higher risk of breaking existing code

**Decision:** ❌ Rejected (too risky for this phase)

---

### Alternative 2: QThread for Background Loading

**Pros:**
- Qt-native approach
- Clean separation of UI and background work

**Cons:**
- Already using ThreadPoolExecutor (works well)
- Would duplicate existing parallel loading
- More complex signal/slot setup

**Decision:** ❌ Rejected (existing approach is sufficient)

---

### Alternative 3: Batch Loading (Load N at a time)

**Pros:**
- Simpler than streaming
- Easier to test

**Cons:**
- Still blocking during each batch
- User doesn't see progress until batch completes
- Less responsive than true streaming

**Decision:** ❌ Rejected (streaming provides better UX)

---

### Alternative 4: Use Existing load_metadata_for_items() with Progress

**Pros:**
- Zero code changes
- Already tested and working

**Cons:**
- User sees progress dialog but can't interact
- No per-file feedback
- Doesn't solve the UX problem

**Decision:** ❌ Rejected (doesn't meet goals)

---

## Conclusion

This plan provides a **safe, incremental approach** to integrating streaming metadata loading:

1. **Phase 1-2:** Add helper methods (no risk, easy to test)
2. **Phase 3:** Add orchestration (self-contained, optional feature)
3. **Phase 4:** Integrate into workflow (opt-in with modifier key)

Each phase includes:
- ✅ Clear success criteria
- ✅ Testing strategy
- ✅ Rollback plan
- ✅ Go/no-go decision points

**Risk Level:** 🟡 **MEDIUM** overall (mostly low-risk additions with one medium-risk integration)

**Expected Outcome:** Significantly improved UX for metadata loading with minimal code changes and full backward compatibility.

---

## Next Steps

1. **Review this plan** with user for approval
2. **Set up test environment** with sample files (10, 50, 100 files)
3. **Run baseline tests** to capture current behavior
4. **Proceed with Phase 1** if approved

**Awaiting approval to proceed...**
