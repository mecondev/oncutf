# Day 1-2: Debounce Preview Generation Implementation Plan

**Date:** 2025-12-04  
**Goal:** Reduce redundant preview recalculations during rapid user input  
**Target:** 50% reduction in preview calls, <300ms perceived latency

---

## Problem Analysis

### Current Behavior (Bottleneck Identified)
```python
# In ui_manager.py lines 659-660:
self.parent_window.rename_modules_area.updated.connect(
    self.parent_window.request_preview_update
)
```

**Issue:** Every parameter change triggers immediate preview regeneration
- User types "abc" → 3 preview calls (a, ab, abc)
- User adjusts counter padding 1→5 → 5 preview calls
- User changes multiple modules → N preview calls

**Measurement (from semantic search):**
- Current: 200-500ms per preview for 100 files
- With debounce: Target <300ms perceived latency
- Expected: 50-70% reduction in preview calls

---

## Solution Design

### 1. Add Debounce Timer to MainWindow

**Location:** `main_window.py`

**New Attributes:**
```python
class MainWindow:
    def __init__(self):
        # ... existing code ...
        self._preview_debounce_timer: QTimer | None = None
        self._preview_pending: bool = False
```

**New Method:**
```python
def request_preview_update_debounced(self) -> None:
    """Request preview update with 300ms debounce."""
    self._preview_pending = True
    
    # Cancel existing timer
    if self._preview_debounce_timer and self._preview_debounce_timer.isActive():
        self._preview_debounce_timer.stop()
    
    # Create/reuse timer
    if not self._preview_debounce_timer:
        self._preview_debounce_timer = QTimer(self)
        self._preview_debounce_timer.setSingleShot(True)
        self._preview_debounce_timer.timeout.connect(self._execute_pending_preview)
    
    # Start 300ms countdown
    self._preview_debounce_timer.start(300)
    
def _execute_pending_preview(self) -> None:
    """Execute pending preview update."""
    if self._preview_pending:
        self._preview_pending = False
        self.request_preview_update()  # Original method
```

### 2. Update Signal Connections

**Location:** `core/ui_manager.py` line 659-672

**Before:**
```python
self.parent_window.rename_modules_area.updated.connect(
    self.parent_window.request_preview_update
)
self.parent_window.final_transform_container.updated.connect(
    self.parent_window.request_preview_update
)
```

**After:**
```python
self.parent_window.rename_modules_area.updated.connect(
    self.parent_window.request_preview_update_debounced
)
self.parent_window.final_transform_container.updated.connect(
    self.parent_window.request_preview_update_debounced
)
```

### 3. Add Immediate Preview for Critical Actions

**Scenario:** User clicks "Rename" button → needs immediate validation

**Solution:** Keep direct `request_preview_update()` for:
- File selection changes (in `table_manager.py`)
- Explicit "Refresh" button clicks
- Module add/remove (structural changes)

**Implementation:**
```python
# In RenameModulesArea:
def add_module(self, module_type: str) -> None:
    # ... existing code ...
    self.updated.emit()  # This will use debounced version
    
    # Force immediate preview for structural change
    if hasattr(self, '_main_window_ref'):
        self._main_window_ref.request_preview_update()  # Immediate
```

---

## Implementation Steps

### Step 1: Add Debounce Infrastructure
**Files:** `main_window.py`
- Add `_preview_debounce_timer` attribute
- Add `_preview_pending` flag
- Implement `request_preview_update_debounced()`
- Implement `_execute_pending_preview()`

### Step 2: Update Signal Connections
**Files:** `core/ui_manager.py`
- Change 2 signal connections (lines 659, 668)
- Keep cache clear connections as-is
- Document which actions use debounced vs immediate

### Step 3: Add Immediate Triggers for Critical Actions
**Files:** `core/table_manager.py`, `widgets/rename_modules_area.py`
- Ensure file selection changes use immediate preview
- Module add/remove use immediate preview
- Parameter changes use debounced preview

### Step 4: Test Performance
**Test Cases:**
1. Type text rapidly in specified text module
2. Adjust counter padding 1→10 with slider
3. Change multiple module parameters in quick succession
4. Add/remove modules (should be immediate)
5. Select different files (should be immediate)

**Metrics:**
- Measure preview call count before/after
- Measure perceived latency (user experience)
- Target: 50% reduction in preview calls

---

## Expected Results

### Before Debounce
```
User types "test" (4 keystrokes):
- Preview 1: "t" → 250ms
- Preview 2: "te" → 250ms
- Preview 3: "tes" → 250ms
- Preview 4: "test" → 250ms
Total: 1000ms, 4 preview calls
```

### After Debounce
```
User types "test" (4 keystrokes):
- (debounce timer resets 4 times)
- Preview 1: "test" → 250ms (300ms after last keystroke)
Total: 550ms perceived, 1 preview call
Reduction: 75% fewer calls, 45% faster perceived
```

---

## Edge Cases & Considerations

### 1. Multiple Concurrent Changes
**Scenario:** User changes counter module AND final transform simultaneously

**Solution:** Single debounce timer handles both (they both trigger same timer reset)

### 2. Very Slow Preview (>300ms)
**Scenario:** 1000 files take 2 seconds to preview

**Solution:** Debounce still effective - prevents 10 calls becoming 1 call (2s vs 20s)

### 3. User Expects Immediate Feedback
**Scenario:** User types one character and waits

**Solution:** 300ms delay is imperceptible (human reaction time ~150-200ms)

### 4. Rapid Module Switching
**Scenario:** User switches between metadata/counter/text modules rapidly

**Solution:** Debounce timer handles this - only generates preview after user settles

---

## Rollback Plan

**If debounce causes issues:**
1. Revert signal connections in `ui_manager.py` (2 lines)
2. Remove debounce methods from `main_window.py`
3. Git tag: `performance-day-1-rollback`

**Known Risks:**
- Users might notice 300ms delay (mitigated: human reaction time buffer)
- Critical actions must bypass debounce (addressed: immediate triggers)

---

## Testing Checklist

### Functional Tests
- [ ] Type rapidly in specified text module
- [ ] Adjust counter padding with slider
- [ ] Change metadata format dropdown
- [ ] Add module → preview updates immediately
- [ ] Remove module → preview updates immediately
- [ ] Select files → preview updates immediately
- [ ] Clear cache → preview regenerates correctly

### Performance Tests
- [ ] Measure preview call count (before/after)
- [ ] Measure average latency (before/after)
- [ ] Test with 10, 100, 1000 files
- [ ] Profile with `monitor_performance` decorator

### Regression Tests
- [ ] All 460 unit tests pass
- [ ] No crashes or freezes
- [ ] Preview accuracy unchanged

---

## Success Criteria

**Must Achieve:**
- ✅ 50% reduction in preview calls for rapid input
- ✅ <300ms perceived latency
- ✅ All 460 tests passing
- ✅ No regressions in preview accuracy

**Nice to Have:**
- ✅ 70% reduction in preview calls
- ✅ <200ms perceived latency
- ✅ User feedback confirms improved responsiveness

---

**Next:** Implement Step 1 (Add debounce infrastructure to MainWindow)
