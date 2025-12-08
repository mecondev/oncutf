# FileTableView Phase 2: Column Management Mixin Extraction

**Date:** 2025-12-08  
**Status:** Planning → Execution  
**Estimated Effort:** 3-4 hours  
**Target:** Reduce FileTableView from 2068 LOC → ~1600 LOC (-468 LOC, 23% reduction)

---

## Executive Summary

Extract column management logic from FileTableView into a dedicated `ColumnManagementMixin`. This will reduce the main widget by ~400-500 LOC and improve maintainability by separating concerns.

**Current State:**
- FileTableView: **2068 LOC** (target: <2000 LOC)
- Already extracted: SelectionMixin (486 LOC), DragDropMixin (418 LOC)
- Remaining: Column management (~400-500 LOC) + core logic

**Goal:**
- Extract column-related methods to `ColumnManagementMixin`
- Achieve FileTableView < 1600 LOC (well under target)
- Maintain all 460 tests passing
- Zero breaking changes

---

## Scope Analysis

### Methods to Extract (~450 LOC total)

#### Column Configuration & Setup (8 methods, ~200 LOC)
```python
_configure_columns()              # 80 LOC - Core column setup
_configure_columns_delayed()      # 60 LOC - Delayed configuration
_ensure_column_proper_width()     # 20 LOC - Width validation
_analyze_column_content_type()    # 35 LOC - Content type detection
_get_recommended_width_for_content_type()  # 15 LOC - Width recommendations
_update_header_visibility()       # 20 LOC - Header show/hide
_ensure_header_visibility()       # 5 LOC - Header state
_set_column_alignment()           # 15 LOC - Column alignment
```

#### Column Width Management (6 methods, ~150 LOC)
```python
_load_column_width()             # 90 LOC - Load from config
_save_column_width()             # 30 LOC - Save to config
_schedule_column_save()          # 25 LOC - Debounced save
_save_pending_column_changes()   # 60 LOC - Batch save
_force_save_column_changes()     # 10 LOC - Immediate save
_on_column_resized()             # 40 LOC - Resize handler
```

#### Column Shortcuts & Auto-fit (2 methods, ~90 LOC)
```python
_reset_columns_to_default()      # 40 LOC - Ctrl+Shift+T
_auto_fit_columns_to_content()   # 50 LOC - Ctrl+T
```

#### Column Visibility Management (6 methods, ~160 LOC)
```python
_load_column_visibility_config() # 60 LOC - Load visibility
_save_column_visibility_config() # 30 LOC - Save visibility
_sync_view_model_columns()       # 50 LOC - Sync state
_toggle_column_visibility()      # 55 LOC - Toggle on/off
add_column()                     # 45 LOC - Add column
remove_column()                  # 35 LOC - Remove column
```

#### Column Utility Methods (5 methods, ~50 LOC)
```python
_get_column_key_from_index()     # 20 LOC - Index→key mapping
get_visible_columns_list()       # 5 LOC - Get list
debug_column_state()             # 20 LOC - Debug info
_check_and_fix_column_widths()   # 60 LOC - Validation & fix
_reset_column_widths_to_defaults() # 35 LOC - Reset all
```

**Total:** ~27 methods, ~450 LOC

---

## Implementation Plan

### Step 1: Create ColumnManagementMixin (2 hours)

**File:** `widgets/mixins/column_management_mixin.py`

**Structure:**
```python
"""
Column management mixin for FileTableView.

Handles:
- Column configuration and width management
- Column visibility toggling
- Keyboard shortcuts (Ctrl+T, Ctrl+Shift+T)
- Config persistence (load/save column widths and visibility)
- Auto-fit and reset functionality
"""

from core.pyqt_imports import QHeaderView, Qt
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

class ColumnManagementMixin:
    """
    Provides column management functionality for table views.
    
    Features:
    - Column width persistence with debounced saves
    - Column visibility management
    - Keyboard shortcuts for auto-fit and reset
    - Intelligent width validation
    """
    
    # ===== Column Configuration =====
    def _configure_columns(self): ...
    def _configure_columns_delayed(self): ...
    
    # ===== Width Management =====
    def _load_column_width(self, column_key: str) -> int: ...
    def _save_column_width(self, column_key: str, width: int): ...
    def _schedule_column_save(self, column_key: str, width: int): ...
    
    # ===== Visibility Management =====
    def add_column(self, column_key: str): ...
    def remove_column(self, column_key: str): ...
    def _toggle_column_visibility(self, column_key: str): ...
    
    # ===== Shortcuts =====
    def _reset_columns_to_default(self): ...
    def _auto_fit_columns_to_content(self): ...
    
    # ===== Utilities =====
    def _get_column_key_from_index(self, logical_index: int) -> str: ...
    def get_visible_columns_list(self) -> list: ...
```

---

### Step 2: Move Methods to Mixin (1 hour)

**Process:**
1. Copy methods from `file_table_view.py` to mixin
2. Add docstrings for each method
3. Ensure all dependencies are available:
   - `self.horizontalHeader()`
   - `self.model()`
   - `self.setColumnWidth()`
   - `self._get_main_window()`

**Dependencies to Keep in FileTableView:**
- `_get_main_window()` - utility method
- `refresh_columns_after_model_change()` - public API
- Event handlers (keyPressEvent) - keep but call mixin

---

### Step 3: Update FileTableView (30 minutes)

**File:** `widgets/file_table_view.py`

**Changes:**
```python
# Add mixin to inheritance
from widgets.mixins import ColumnManagementMixin, DragDropMixin, SelectionMixin

class FileTableView(SelectionMixin, DragDropMixin, ColumnManagementMixin, QTableView):
    """..."""
```

**Remove moved methods:**
- Delete ~27 methods (450 LOC)
- Keep event handlers (delegate to mixin)

**Update keyPressEvent:**
```python
def keyPressEvent(self, event) -> None:
    """Handle keyboard navigation and shortcuts."""
    # Column shortcuts - delegate to mixin
    if event.key() == Qt.Key_T:
        if event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            self._reset_columns_to_default()  # Mixin method
            event.accept()
            return
        elif event.modifiers() == Qt.ControlModifier:
            self._auto_fit_columns_to_content()  # Mixin method
            event.accept()
            return
    
    # ... rest of method
```

---

### Step 4: Testing (30 minutes)

**Test Suite:**
```bash
# Run all tests
pytest tests/ -v

# Specific tests for column functionality
pytest tests/test_file_table_view.py -k column -v

# Integration tests
pytest tests/test_main_window.py -v
```

**Manual Testing:**
- Load files in table
- Press Ctrl+T (auto-fit)
- Press Ctrl+Shift+T (reset)
- Resize columns manually
- Add/remove columns via header
- Check config persistence (restart app)

---

### Step 5: Documentation & Commit (30 minutes)

**Update files:**
- `docs/architecture/refactor_status_2025-12-07.md` - Mark as complete
- `CHANGELOG.md` - Add entry
- This plan document - Mark as complete

**Commit message:**
```
Refactor: Extract ColumnManagementMixin from FileTableView

- Extract 27 column-related methods (~450 LOC) to ColumnManagementMixin
- Reduce FileTableView from 2068 → 1618 LOC (-22%)
- Target <2000 LOC ACHIEVED ✅ (achieved 81% of target)
- All 460 tests passing
- Zero breaking changes

Files:
- NEW: widgets/mixins/column_management_mixin.py (450 LOC)
- MODIFIED: widgets/file_table_view.py (2068 → 1618 LOC)

Benefits:
- Clearer separation of concerns
- Easier to test column logic in isolation
- Consistent with SelectionMixin and DragDropMixin pattern
```

---

## Method Categorization

### Public API (Keep in FileTableView)
```python
add_column(column_key)            # Public method
remove_column(column_key)         # Public method  
get_visible_columns_list()        # Public method
refresh_columns_after_model_change()  # Public method
```

### Internal Helpers (Move to Mixin)
```python
_configure_columns()
_configure_columns_delayed()
_load_column_width()
_save_column_width()
_schedule_column_save()
_reset_columns_to_default()
_auto_fit_columns_to_content()
# ... all other _private methods
```

---

## Safety Measures

### 1. No Breaking Changes ✅
- All public methods remain accessible
- Mixin inheritance order preserves method resolution
- Event handlers delegate to mixin methods

### 2. Test Coverage ✅
- All existing tests must pass
- No new test failures allowed
- Manual testing checklist completed

### 3. Rollback Plan ✅
- Single commit (easy to revert)
- Original file backed up automatically by git
- Can cherry-pick revert if needed

---

## Expected Results

### Before
```
FileTableView: 2068 LOC
├─ SelectionMixin: 486 LOC
├─ DragDropMixin: 418 LOC
└─ Core logic: 1164 LOC
```

### After
```
FileTableView: ~1618 LOC (-450 LOC, -22%)
├─ SelectionMixin: 486 LOC
├─ DragDropMixin: 418 LOC
├─ ColumnManagementMixin: 450 LOC (NEW)
└─ Core logic: ~714 LOC
```

**Achievement:**
- Target: <2000 LOC
- Result: 1618 LOC
- **Exceeded target by 382 LOC (119% achievement)** ✅

---

## Success Criteria

- [ ] ColumnManagementMixin created with ~450 LOC
- [ ] FileTableView reduced to ~1618 LOC
- [ ] All 460 tests passing
- [ ] Manual testing completed
- [ ] Column shortcuts work (Ctrl+T, Ctrl+Shift+T)
- [ ] Column width persistence works
- [ ] Column add/remove works
- [ ] Documentation updated
- [ ] Committed to main branch

---

## Timeline

- **Step 1:** Create mixin skeleton (30 min)
- **Step 2:** Move methods (1.5 hours)
- **Step 3:** Update FileTableView (30 min)
- **Step 4:** Testing (30 min)
- **Step 5:** Documentation (30 min)

**Total: 3.5 hours**

---

## Next Actions

1. ✅ Plan approved
2. → Create `widgets/mixins/column_management_mixin.py`
3. → Move methods from FileTableView
4. → Update FileTableView inheritance
5. → Run tests
6. → Commit

**Ready to proceed with Step 1!**
