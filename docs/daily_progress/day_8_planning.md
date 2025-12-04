# Day 8 Planning: Mixin Extraction Strategy

**Date:** 2025-12-04  
**Focus:** Extract SelectionMixin and DragDropMixin from FileTableView  
**Current State:** FileTableView is 2715 LOC  
**Target:** FileTableView < 2000 LOC (reduce by ~700+ lines)  

---

## Analysis

### Current FileTableView Size
- **Total lines:** 2715
- **Methods:** 95
- **Target reduction:** 700+ lines

### Methods to Extract

#### SelectionMixin (~400 lines, 12 methods)
1. `_get_selection_store()` - Get SelectionStore from context
2. `_update_selection_store()` - Update SelectionStore and Qt model  
3. `_sync_qt_selection_model()` - Batch sync Qt selection
4. `_get_current_selection()` - Get current selection
5. `_get_current_selection_safe()` - Safe selection getter
6. `_set_anchor_row()` - Set anchor row
7. `_get_anchor_row()` - Get anchor row
8. `ensure_anchor_or_select()` - Handle selection with modifiers
9. `selectionChanged()` - Qt selection change handler
10. `select_rows_range()` - Select range of rows
11. `select_dropped_files()` - Select specific dropped files
12. `_sync_selection_safely()` - Safe selection sync

#### DragDropMixin (~350 lines, 9 methods)
1. `_start_custom_drag()` - Initiate drag operation
2. `_start_drag_feedback_loop()` - Start drag feedback timer
3. `_update_drag_feedback()` - Update drag visual feedback
4. `_end_custom_drag()` - End drag operation
5. `_restore_hover_after_drag()` - Restore hover state
6. `_handle_drop_on_metadata_tree()` - Handle metadata tree drops
7. `dragEnterEvent()` - Qt drag enter handler
8. `dragMoveEvent()` - Qt drag move handler
9. `dropEvent()` - Qt drop handler

**Total extraction:** ~750 lines (exceeds 700-line target ✅)

---

## Implementation Strategy

### Phase 1: Create Mixin Skeletons
- Create `widgets/mixins/__init__.py`
- Create `widgets/mixins/selection_mixin.py` (skeleton)
- Create `widgets/mixins/drag_drop_mixin.py` (skeleton)

### Phase 2: Extract SelectionMixin
- Copy selection methods from FileTableView
- Add necessary imports
- Add type hints and docstrings
- Ensure proper attribute access (use self)

### Phase 3: Extract DragDropMixin
- Copy drag/drop methods from FileTableView
- Add necessary imports
- Add type hints and docstrings
- Ensure proper attribute access (use self)

### Phase 4: Update FileTableView
- Import mixins
- Add mixins to inheritance chain
- Remove extracted methods
- Verify no broken references

### Phase 5: Testing
- Run existing tests
- Verify FileTableView still works
- Check LOC reduction

---

## Challenges

### 1. Shared State
Both mixins and FileTableView share state like:
- `self.selected_rows`
- `self.anchor_row`
- `self._is_dragging`
- `self._drag_data`
- `self._manual_anchor_index`

**Solution:** Mixins access these via `self` (no changes needed)

### 2. Method Dependencies
Some methods call each other:
- `_update_selection_store()` → `_sync_qt_selection_model()`
- `_start_custom_drag()` → `_start_drag_feedback_loop()`

**Solution:** Keep related methods in same mixin

### 3. Qt Event Handlers
Methods like `selectionChanged()`, `dragEnterEvent()` override Qt methods.

**Solution:** Mixins provide these overrides, FileTableView inherits them via MRO

### 4. Imports
Mixins need imports from:
- `core.pyqt_imports`
- `core.application_context`
- `utils.logger_factory`

**Solution:** Import in each mixin file

---

## Multiple Inheritance Order

```python
class FileTableView(SelectionMixin, DragDropMixin, QTableView):
    """FileTableView with selection and drag/drop mixins."""
```

**MRO (Method Resolution Order):**
1. FileTableView
2. SelectionMixin
3. DragDropMixin
4. QTableView
5. QAbstractItemView
6. ...

This ensures:
- FileTableView can override mixin methods
- Mixins provide Qt event handler overrides
- QTableView provides base functionality

---

## Verification

### LOC Check
```bash
wc -l widgets/file_table_view.py widgets/mixins/*.py
```

**Expected:**
- `selection_mixin.py`: ~400 lines
- `drag_drop_mixin.py`: ~350 lines
- `file_table_view.py`: <2000 lines (from 2715)

### Functionality Check
1. Run application
2. Test selection (single, range, Ctrl, Shift)
3. Test drag/drop (table→tree, files→table)
4. Test all existing tests

---

## Risks & Mitigation

### Risk 1: Broken References
**Mitigation:** Thorough testing after extraction

### Risk 2: MRO Issues
**Mitigation:** Correct inheritance order, test carefully

### Risk 3: Shared State Bugs
**Mitigation:** Document shared attributes clearly

---

## Success Criteria

✅ `SelectionMixin` created with ~400 lines  
✅ `DragDropMixin` created with ~350 lines  
✅ `FileTableView` reduced to <2000 lines  
✅ All existing tests pass  
✅ Manual testing confirms functionality  
✅ No regressions in selection or drag/drop  

---

## Timeline

- **Phase 1-2:** 2 hours (SelectionMixin extraction)
- **Phase 3:** 1.5 hours (DragDropMixin extraction)
- **Phase 4:** 1 hour (Update FileTableView)
- **Phase 5:** 1 hour (Testing & verification)

**Total:** ~5.5 hours

---

**Status:** Planning complete, ready to implement ✅
