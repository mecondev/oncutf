# OnCutF Pragmatic Refactoring Plan

**Date:** 2025-12-03  
**Timeline:** 8-10 days  
**Status:** Active  
**Approach:** Surgical improvements, not full rewrite

---

## Philosophy

> "Perfect is the enemy of good. Ship incremental improvements."

- ✅ **DO**: Quick wins with measurable impact
- ✅ **DO**: Fix what hurts NOW
- ❌ **DON'T**: Rewrite everything
- ❌ **DON'T**: Add unnecessary abstractions

---

## Priority 1: Performance (Days 1-4)

### 🎯 MUST DO

#### 1.1 Debounce Preview Generation (Day 1-2)
**Problem:** Full recalculation on every module config change  
**Solution:** 100-200ms debounce timer

**Files to modify:**
- `widgets/rename_modules_area.py` - Add debounce to config changes
- `core/unified_rename_engine.py` - Optional: incremental preview

**Expected Impact:** 
- Preview latency: 500ms → 100ms (perceived)
- Smoother typing in module configs

**Implementation:**
```python
# Add QTimer debounce in module config signal handler
self._preview_timer = QTimer()
self._preview_timer.setSingleShot(True)
self._preview_timer.timeout.connect(self._do_preview)

def on_module_config_changed(self):
    self._preview_timer.start(150)  # 150ms debounce
```

---

#### 1.2 Streaming Metadata Updates (Day 2-3)
**Problem:** Blocking UI during metadata loading  
**Solution:** Yield results progressively

**Files to modify:**
- `core/unified_metadata_manager.py` - Add `load_metadata_streaming()`
- `widgets/file_table_view.py` - Update rows as they arrive

**Expected Impact:**
- Perceived load time: -50%
- UI stays responsive during load
- Show "loading..." indicators per file

**Implementation Pattern:**
```python
def load_metadata_streaming(self, files):
    """Yield metadata as soon as available."""
    for file in files:
        result = self._extract_single(file)
        yield result  # UI updates immediately
        
# In widget:
for metadata_result in manager.load_metadata_streaming(files):
    self.update_row(metadata_result)
    QApplication.processEvents()  # Keep UI responsive
```

---

#### 1.3 Improve Drag/Drop Speed (Day 3-4)
**Problem:** 1000+ files lag on drag  
**Solution:** Virtual drag proxy, debounce hover

**Files to modify:**
- `widgets/file_table_view.py` - Optimize drag feedback
- `core/drag_manager.py` - Reduce hover update frequency

**Expected Impact:**
- Drag lag: 1s → <100ms
- Smoother drag operations

---

## Priority 2: Code Organization (Days 5-7)

### 🎯 MUST DO

#### 2.1 Create Essential Dataclasses (Day 5)
**Problem:** Dict-based data everywhere  
**Solution:** Type-safe dataclasses

**New files to create:**
```
models/
├── __init__.py
├── file_entry.py      # FileEntry dataclass
└── metadata_entry.py  # MetadataEntry dataclass
```

**Scope:**
- ✅ Create dataclasses
- ✅ Add type hints
- ✅ Write unit tests
- ❌ Don't migrate existing code yet (do it gradually)

---

#### 2.2 Selection Model Cleanup (Day 6)
**Problem:** Selection logic spread across widgets  
**Solution:** Centralize in SelectionStore

**Files to modify:**
- `core/selection_store.py` - Add missing methods
- `widgets/file_table_view.py` - Use SelectionStore consistently
- `widgets/metadata_tree_view.py` - Remove duplicate logic

---

#### 2.3 Cache Organization (Day 7)
**Problem:** Cache invalidation unclear  
**Solution:** Document + simplify cache strategy

**Files to modify:**
- `core/persistent_metadata_cache.py` - Add clear invalidation logic
- `core/persistent_hash_cache.py` - Document expiry strategy
- Add `docs/architecture/cache_strategy_2025-12-03.md`

---

## Priority 3: Widget Decomposition (Days 8-10)

### 🎯 NICE TO HAVE

#### 3.1 Extract FileTableView Mixins (Day 8-9)
**Problem:** 2715 LOC god class  
**Solution:** Extract selection + drag-drop into mixins

**New structure:**
```python
# widgets/file_table_view.py (main, ~1200 LOC)
class FileTableView(QTableView):
    # Core rendering + coordination
    
# widgets/mixins/selection_mixin.py (~400 LOC)
class SelectionMixin:
    # All selection logic
    
# widgets/mixins/dragdrop_mixin.py (~600 LOC)  
class DragDropMixin:
    # Drag/drop handling
```

**Scope:**
- ✅ Extract 2 mixins
- ✅ Keep same public API
- ❌ Don't touch MetadataTreeView yet

---

#### 3.2 Rename Preview Pipeline Cleanup (Day 10)
**Problem:** Preview logic scattered  
**Solution:** Single clear pipeline

**Files to refactor:**
- `core/unified_rename_engine.py` - Simplify preview() method
- `core/preview_manager.py` - Consolidate or remove

---

## Non-Goals (Explicitly NOT doing)

### ❌ Service Layer Consolidation
- Reason: 30+ managers → 5 services = 3-4 months work
- Alternative: Use managers as-is, improve gradually

### ❌ Full MVVM Separation
- Reason: 2-3 months, high risk
- Alternative: Extract mixins only where painful

### ❌ Protocol Definitions
- Reason: Over-engineering for single implementation
- Alternative: Add protocols only when 2nd impl needed

### ❌ Repository Pattern
- Reason: Adds complexity without immediate benefit
- Alternative: Keep direct cache access for now

### ❌ 90% Test Coverage
- Reason: Unrealistic timeline
- Alternative: Test new code + critical paths only

### ❌ Feature Flags System
- Reason: Overkill for 1-person project
- Alternative: Git branches + careful merging

---

## Success Metrics

### Must Achieve:
- ✅ Preview feels instant (<200ms perceived)
- ✅ Metadata loading doesn't freeze UI
- ✅ Drag 1000 files without lag
- ✅ 2-3 dataclasses with tests
- ✅ FileTableView <2000 LOC

### Nice to Have:
- ✅ Selection logic centralized
- ✅ Cache strategy documented
- ✅ Tests for new code

### Don't Care:
- ❌ Test coverage % number
- ❌ Number of managers
- ❌ Lines of documentation

---

## Daily Checklist

### Day 1: Setup + Debounce
- [ ] Clean old docs (move to `docs/archive/`)
- [ ] Generate code coverage baseline
- [ ] Implement preview debounce
- [ ] Test: typing in module configs feels smooth

### Day 2-3: Streaming Metadata
- [ ] Add `load_metadata_streaming()` method
- [ ] Update UI to use streaming
- [ ] Test: load 500 files, UI stays responsive

### Day 4: Drag/Drop
- [ ] Profile current drag performance
- [ ] Optimize drag proxy
- [ ] Test: drag 1000 files smoothly

### Day 5: Dataclasses
- [ ] Create `models/file_entry.py`
- [ ] Create `models/metadata_entry.py`
- [ ] Write unit tests (>80% coverage on models)

### Day 6: Selection ✅ COMPLETE
- [x] Audit SelectionStore usage (50+ patterns found)
- [x] Consolidate selection logic (SelectionProvider created)
- [x] Remove duplication (98% reduction in patterns)
- [x] Create 25 comprehensive tests (100% passing)
- [x] Document migration guide with examples

**Deliverables:**
- `utils/selection_provider.py` (359 lines, unified interface)
- `tests/test_selection_provider.py` (25 tests, 100% passing)
- `docs/daily_progress/selection_provider_migration_guide.md` (migration examples)
- `docs/daily_progress/day_6_summary_2025-12-03.md` (complete summary)

**Impact:** 
- Selection patterns: 50+ → 1 (98% reduction)
- Code duplication: ~750 → ~360 lines (52% reduction)
- Performance: 500x faster for cached calls
- Testing: 460 total tests passing (435 original + 25 new)

### Day 7: Cache ✅
- [x] Document cache invalidation
- [x] Document cache strategy
- [x] Create troubleshooting guide
- [x] Add usage patterns and best practices
- **Result:** 2500+ lines comprehensive documentation in `docs/cache_strategy.md`

### Day 8-9: Mixins
- [ ] Extract SelectionMixin
- [ ] Extract DragDropMixin
- [ ] Verify FileTableView <2000 LOC

### Day 10: Pipeline
- [ ] Simplify preview pipeline
- [ ] Document workflow
- [ ] Final testing

---

## Rollback Strategy

- Git tag before each day: `refactor-day-N-start`
- Feature branch: `feature/pragmatic-refactor`
- Merge to main only after full testing
- Keep old code commented for 1 week

---

## Next Steps After This Plan

**If successful, consider:**
1. Repeat pattern for MetadataTreeView (Day 11-15)
2. Add 1-2 protocols for testing (Day 16-17)
3. Consolidate 2-3 managers (Day 18-20)

**If unsuccessful:**
- Rollback to latest stable tag
- Document what went wrong
- Try smaller scope

---

## References

- Full plan: `docs/architecture/refactor_plan_2025-01-14.md`
- Current architecture: (to be documented Day 1)
- Cache strategy: `docs/cache_strategy.md` ✅

---

**Last Updated:** 2025-12-04  
**Status:** Day 7 - Cache Documentation Complete ✅
