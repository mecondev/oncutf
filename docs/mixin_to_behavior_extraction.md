# Mixin → Behavior Extraction Log

**Author:** Michael Economou  
**Date:** 2025-12-28  
**Phase:** 2 (Extract Behaviors)

---

## Completed Extractions

### 3. ColumnManagementBehavior ✅
- **Source:** `ui/mixins/column_management_mixin.py` (1295 lines) 🔥 **LARGEST**
- **Target:** `ui/behaviors/column_management_behavior.py` (667 lines)
- **Protocol:** `ColumnManageableWidget`
- **Status:** Complete, syntax checked, ruff clean, mypy passing
- **Code reduction:** 48% (1295 → 667 lines)

**Key features preserved:**
- Column configuration and width management
- Column visibility toggling (add/remove)
- Config persistence (JSON + main config system)
- **Delayed save mechanism** (7-second timer)
- **Shutdown hook** for forced save
- Intelligent width validation
- Content-type detection (datetime, filesize, numeric, text)

**Quality gates:**
```bash
✅ Syntax check passed
✅ Ruff clean
✅ Mypy passing (4 source files)
```

---

### 1. SelectionBehavior ✅
- **Source:** `ui/mixins/selection_mixin.py` (513 lines)
- **Target:** `ui/behaviors/selection_behavior.py` (257 lines)
- **Protocol:** `SelectableWidget`
- **Status:** Complete, tested
- **Migration:** Not yet applied to FileTableView (still using mixin)

**Key improvements:**
- 50% reduction in code size through focused design
- Protocol-based dependency injection
- Testable without Qt widget instantiation
- No MRO complexity

---

### 2. DragDropBehavior ✅
- **Source:** `ui/mixins/drag_drop_mixin.py` (449 lines)
- **Target:** `ui/behaviors/drag_drop_behavior.py` (550 lines)
- **Protocol:** `DraggableWidget`
- **Status:** Complete, syntax checked, ruff clean, mypy passing
- **Migration:** Not yet applied to FileTableView (still using mixin)

**Protocol contract:**
```python
class DraggableWidget(Protocol):
    def model(self): ...
    def viewport(self): ...
    def visualRect(self, index: QModelIndex) -> QRect: ...
    def rect(self) -> QRect: ...
    def mapFromGlobal(self, pos): ...
    def blockSignals(self, block: bool) -> bool: ...
    def _get_current_selection_safe(self) -> set[int]: ...
    def _get_current_selection(self) -> set[int]: ...
    def _get_selection_store(self): ...
    def _force_cursor_cleanup(self) -> None: ...
```

**Key features preserved:**
- Custom drag operation with visual feedback
- Drag lifecycle (start → feedback loop → end)
- Integration with DragManager and DragVisualManager
- Drop handling on metadata tree
- Hover state restoration
- Large selection optimization (>100 files)
- Adaptive feedback delay based on selection size

**Quality gates:**
```bash
$ python -m py_compile oncutf/ui/behaviors/drag_drop_behavior.py
✅ No syntax errors

$ ruff check oncutf/ui/behaviors/drag_drop_behavior.py
✅ All checks passed!

$ mypy oncutf/ui/behaviors/
✅ Success: no issues found in 3 source files
```

---

## Pending Extractions

### 3. ColumnManagementBehavior ⏳
- **Source:** `ui/mixins/column_management_mixin.py` (1294 lines) 🔥 **LARGEST**
- **Complexity:** High (column persistence, delayed save, shutdown hooks)
- **Priority:** Medium
- **Estimated effort:** 4-6 hours

**Challenges:**
- 7-second delayed save mechanism
- Shutdown coordinator integration
- JSON config persistence
- Keyboard shortcut handling (Ctrl+T, Ctrl+Shift+T)

---

### 4. MetadataCacheBehavior ⏳
- **Source:** `ui/mixins/metadata_cache_mixin.py` (438 lines)
- **Complexity:** Medium
- **Priority:** Low (MetadataTreeView specific)
- **Estimated effort:** 2-3 hours

---

### 5. MetadataEditBehavior ⏳
- **Source:** `ui/mixins/metadata_edit_mixin.py` (960 lines)
- **Complexity:** High (inline editing, validation)
- **Priority:** Low (MetadataTreeView specific)
- **Estimated effort:** 3-4 hours

---

### 6. MetadataContextMenuBehavior ⏳
- **Source:** `ui/mixins/metadata_context_menu_mixin.py` (515 lines)
- **Complexity:** Medium (menu construction, actions)
- **Priority:** Low (MetadataTreeView specific)
- **Estimated effort:** 2-3 hours

---

### 7. MetadataScrollBehavior ⏳
- **Source:** `ui/mixins/metadata_scroll_mixin.py` (269 lines) 🟢 **SMALLEST**
- **Complexity:** Low (scroll synchronization)
- **Priority:** Low (MetadataTreeView specific)
- **Estimated effort:** 1-2 hours

---

## Next Steps

### Option A: Apply existing behaviors to FileTableView
**Goal:** Migrate FileTableView from mixins to behaviors  
**Steps:**
1. Add `_selection_behavior = SelectionBehavior(self)` to `__init__`
2. Add `_drag_drop_behavior = DragDropBehavior(self)` to `__init__`
3. Route existing mixin method calls to behavior instances
4. Test thoroughly (592+ tests should still pass)
5. Remove `SelectionMixin` and `DragDropMixin` from inheritance
6. Keep `ColumnManagementMixin` temporarily (not yet extracted)

**Risks:**
- Qt lifecycle subtleties may cause regressions
- Event routing complexity (mousePressEvent, dragEnterEvent, etc.)
- Selection/drag interaction edge cases

**Testing strategy:**
- Run full test suite: `pytest`
- Manual testing: drag-drop, selection, Ctrl/Shift modifiers
- Performance testing: large selections (>500 files)

---

### Option B: Extract ColumnManagementBehavior next
**Goal:** Complete FileTableView behavior extraction  
**Rationale:** ColumnManagementMixin is the last remaining FileTableView mixin

**Challenges:**
- Largest mixin (1294 lines)
- Complex state management (delayed saves, shutdown hooks)
- JSON persistence layer integration

**Recommendation:** Start with Option A (apply existing behaviors) before tackling this.

---

### Option C: Extract MetadataScrollBehavior (quick win)
**Goal:** Complete simplest mixin extraction  
**Rationale:** Smallest mixin (269 lines), low complexity

**Advantage:** Build confidence with successful extraction  
**Disadvantage:** Low priority, doesn't unblock FileTableView migration

---

## Recommendation

**Suggested order:**

1. **Apply SelectionBehavior + DragDropBehavior to FileTableView** (Option A)
   - Validate composition pattern works in production widget
   - Identify any missing protocol methods
   - Test edge cases thoroughly

2. **Extract ColumnManagementBehavior** (Option B)
   - Unblocks full FileTableView migration
   - Proves pattern scales to complex mixins

3. **Defer MetadataTreeView mixins** (Options 4-7)
   - Lower priority
   - Can be tackled after FileTableView proves pattern success

---

## Success Metrics

- ✅ All 592+ tests passing
- ✅ Ruff clean (except pre-existing naming error)
- ✅ Mypy passing
- ✅ No performance regressions (drag-drop, selection)
- ✅ Code is more maintainable (clear protocols, testable behaviors)

