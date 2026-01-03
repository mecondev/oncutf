# Column System Consolidation Plan

**Author:** Michael Economou  
**Date:** 2026-01-02  
**Status:** In Progress

---

## Executive Summary

The column management system currently has **3 sources of truth** that need consolidation:

1. **UnifiedColumnService** (391 lines) — Canonical service [KEEP AS-IS]
2. **ColumnManager** (853 lines) — Legacy facade [REFACTOR → <200 lines]
3. **ColumnManagementBehavior** (964 lines) — UI behavior [SIMPLIFY → <500 lines]
4. **models/file_table/column_manager.py** (350 lines) — Model-level [KEEP - Different purpose]

**Target Architecture:**
```
UnifiedColumnService (canonical business logic)
       ↑
       ├── ColumnManager (thin legacy adapter ~150 lines)
       └── ColumnManagementBehavior (UI-only logic ~400 lines)
```

---

## Current State Analysis

### 1. UnifiedColumnService (391 lines)

**Purpose:** Single source of truth for column configuration and user settings

**Key Responsibilities:**
- Load column configuration from config.py
- Manage user overrides (widths, visibility)
- Cache configuration for performance
- Provide type-safe column operations

**Methods:**
- `get_column_config(column_key)` — Get config for specific column
- `get_all_columns()` — Get all column configurations
- `get_visible_columns()` — Get visible columns in order
- `get_column_mapping()` — Index to key mapping
- `get_column_width(column_key)` — Effective width (user override or default)
- `set_column_width(column_key, width)` — Save user override
- `is_column_visible(column_key)` — Check visibility
- `set_column_visibility(column_key, visible)` — Set visibility
- `invalidate_cache()` — Force reload

**Status:** ✅ Complete - This is the canonical service

---

### 2. ColumnManager (853 lines)

**Purpose:** Originally designed for intelligent width calculation and Qt integration

**Current Responsibilities (23 methods):**
- `configure_table_columns(table_view, table_type)` — Main configuration entry
- `_initialize_default_configs()` — Default configs for file_table, metadata_tree
- `_calculate_column_width()` — Calculate optimal width
- `_load_saved_column_width()` — Load from config
- `_calculate_stretch_column_width()` — Dynamic stretch calculation
- `_needs_vertical_scrollbar()` — Scrollbar detection
- `_get_scrollbar_width()` — Scrollbar width calculation
- `ensure_horizontal_scrollbar_state()` — Scrollbar management
- `_connect_resize_signals()` — Connect to Qt signals
- `_on_column_resized()` — Handle resize events
- `adjust_columns_for_splitter_change()` — Respond to splitter
- `reset_user_preferences()` — Reset to defaults
- `save_column_state()` — Serialize state
- `load_column_state()` — Restore state
- `get_column_config()` — Get config for column
- `update_column_config()` — Update config
- Font metrics management
- State tracking (ColumnState class)

**Analysis:**
- **Overlap with UnifiedColumnService:** `get_column_width`, width loading, config management
- **Unique Qt Logic:** Scrollbar detection, signal connection, resize handling, splitter integration
- **Legacy Burden:** Hardcoded configs for file_table/metadata_tree (should come from service)

**Target:** Thin adapter (~150 lines)
- Delegate business logic to UnifiedColumnService
- Keep only Qt-specific integration code
- Remove duplicate width/config management

---

### 3. ColumnManagementBehavior (964 lines)

**Purpose:** UI behavior for column visibility and width management

**Current Responsibilities (38 methods):**
- `configure_columns()` — Initial setup
- `ensure_all_columns_proper_width()` — Width validation
- `reset_column_widths_to_defaults()` — Reset widths
- `check_and_fix_column_widths()` — Width sanity checks
- `auto_fit_columns_to_content()` — Content-based sizing
- `add_column(column_key)` — Show hidden column
- `remove_column(column_key)` — Hide column
- `get_visible_columns_list()` — List visible columns
- `refresh_columns_after_model_change()` — Model sync
- `force_save_column_changes()` — Immediate persist
- `handle_column_resized()` — User resize event
- `handle_column_moved()` — Column reorder (disabled)
- `_schedule_column_save()` — Delayed save (7 seconds)
- `_save_pending_column_changes()` — Write to config
- `_load_column_width()` — Load from config
- `_analyze_column_content_type()` — Detect data type
- `_get_recommended_width_for_content_type()` — Content-aware width
- `_update_header_visibility()` — Show/hide header
- `load_column_visibility_config()` — Load visibility from config
- `sync_view_model_columns()` — Sync view with model
- `toggle_column_visibility()` — Show/hide column
- Column alignment management
- Shutdown hooks for save
- Selection clearing for updates

**Analysis:**
- **Overlap with UnifiedColumnService:** Width loading, visibility management, config persistence
- **Unique UI Logic:** User interaction handling, delayed saves, shutdown hooks, selection clearing
- **Content Analysis:** Type detection and recommended widths (could be in service)

**Target:** UI-only (~400 lines)
- Delegate config/width/visibility to UnifiedColumnService
- Keep only UI interaction code (events, timers, selection)
- Extract content analysis to UnifiedColumnService

---

### 4. models/file_table/column_manager.py (350 lines)

**Purpose:** Model-level column operations (different from UI management)

**Status:** ✅ Keep as-is - Different responsibility (model data, not UI config)

---

## Migration Strategy

### Phase 1: Enhance UnifiedColumnService

Add missing business logic from ColumnManager and ColumnManagementBehavior:

**New Methods to Add:**
```python
# Content analysis (from ColumnManagementBehavior)
def analyze_column_content_type(column_key: str) -> str
def get_recommended_width_for_content_type(content_type: str) -> int

# Validation (from ColumnManagementBehavior)
def validate_column_width(column_key: str, width: int) -> int

# Bulk operations (from ColumnManager)
def get_visible_column_configs() -> list[ColumnConfig]
def reset_column_width(column_key: str) -> None
def reset_all_widths() -> None
```

**Estimated:** +100 lines → UnifiedColumnService becomes ~490 lines

---

### Phase 2: Refactor ColumnManager to Thin Adapter

**Keep Only:**
- Qt-specific integration (scrollbar detection, signal connection)
- Splitter integration
- Resize mode management

**Delegate to UnifiedColumnService:**
- All configuration lookups
- Width loading/saving
- Visibility management

**Target Structure:**
```python
class ColumnManager:
    def __init__(self, main_window: QWidget):
        self._service = get_column_service()
        self._main_window = main_window
        self.state = ColumnState()  # Qt-specific state only
    
    def configure_table_columns(self, table_view, table_type):
        # Get configs from service
        configs = self._service.get_visible_column_configs()
        # Apply Qt-specific setup
        self._apply_qt_configuration(table_view, configs)
        self._connect_resize_signals(table_view)
    
    def _apply_qt_configuration(self, table_view, configs):
        # Pure Qt code - no business logic
        ...
```

**Estimated:** 853 → ~150 lines (82% reduction)

---

### Phase 3: Simplify ColumnManagementBehavior

**Keep Only:**
- User interaction handlers (resize, add/remove)
- Delayed save timer
- Shutdown hooks
- Selection clearing for UI updates

**Delegate to UnifiedColumnService:**
- Config loading
- Width loading/saving
- Visibility loading/saving
- Content type analysis

**Target Structure:**
```python
class ColumnManagementBehavior:
    def __init__(self, widget: ColumnManageableWidget):
        self._widget = widget
        self._service = get_column_service()
        self._save_timer = QTimer()
        self._pending_changes = {}
    
    def handle_column_resized(self, logical_index, old_size, new_size):
        column_key = self._get_column_key(logical_index)
        # Schedule save via timer
        self._schedule_column_save(column_key, new_size)
    
    def add_column(self, column_key):
        # Delegate visibility to service
        self._service.set_column_visibility(column_key, True)
        # UI-only: Update view
        self._update_view_columns()
    
    def _schedule_column_save(self, column_key, width):
        # UI-only: Delayed save logic
        self._pending_changes[column_key] = width
        self._save_timer.start(7000)
```

**Estimated:** 964 → ~400 lines (58% reduction)

---

## Dependency Analysis

### Who Uses ColumnManager?

1. `initialization_orchestrator.py` (line 249):
   ```python
   self.window.column_manager = ColumnManager(self.window)
   ```

2. `ui_managers/__init__.py` — Re-exports for backward compatibility

**Impact:** Low - Only created once, rarely called directly

### Who Uses ColumnManagementBehavior?

Used by widgets that manage columns:
- `FileTableView` (file_table_view.py)
- Potentially other table views

**Impact:** Medium - Direct usage in UI code

### Who Uses UnifiedColumnService?

Currently minimal direct usage — designed to be the future canonical API

**Impact:** Low - Can expand usage without breaking changes

---

## Implementation Plan

### Step 1: Enhance UnifiedColumnService (30 minutes)

1. Add content analysis methods
2. Add validation methods
3. Add bulk operation methods
4. Add tests for new methods

**Files Changed:**
- `oncutf/core/ui_managers/column_service.py` (+100 lines)
- `tests/test_column_service.py` (new file, +200 lines)

---

### Step 2: Refactor ColumnManager (45 minutes)

1. Replace hardcoded configs with service calls
2. Delegate width/visibility management to service
3. Keep only Qt integration code
4. Update docstrings
5. Run tests

**Files Changed:**
- `oncutf/core/ui_managers/column_manager.py` (853 → ~150 lines)

**Backward Compatibility:** ✅ Public API unchanged

---

### Step 3: Simplify ColumnManagementBehavior (60 minutes)

1. Replace config/width loading with service calls
2. Move content analysis to service
3. Keep only UI event handling
4. Update docstrings
5. Run tests

**Files Changed:**
- `oncutf/ui/behaviors/column_management_behavior.py` (964 → ~400 lines)

**Backward Compatibility:** ✅ Public API unchanged

---

### Step 4: Update Documentation (15 minutes)

1. Update REFACTORING_ROADMAP.md
2. Update MIGRATION_STANCE.md
3. Update ARCHITECTURE.md if needed

---

### Step 5: Quality Gates (30 minutes)

1. Run `pytest` — All tests must pass
2. Run `ruff check .` — No new warnings
3. Run `mypy .` — No new errors
4. Manual testing — Verify column operations work

---

## Success Metrics

| Metric | Before | Target | Savings |
|--------|--------|--------|---------|
| **ColumnManager** | 853 lines | ~150 lines | 703 lines (82%) |
| **ColumnManagementBehavior** | 964 lines | ~400 lines | 564 lines (58%) |
| **UnifiedColumnService** | 391 lines | ~490 lines | +99 lines |
| **Total System** | 2208 lines | ~1040 lines | 1168 lines (53%) |
| **Tests Passing** | 949/949 | 949+/949+ | — |

---

## Risks & Mitigations

### Risk 1: Breaking Existing Column Behavior

**Mitigation:**
- Maintain backward compatibility of public APIs
- Extensive testing before merge
- Manual verification of all column operations

### Risk 2: Performance Regression

**Mitigation:**
- UnifiedColumnService already has caching
- Benchmark before/after if needed
- No n² operations introduced

### Risk 3: Incomplete Coverage

**Mitigation:**
- Read all methods before migration
- Check all call sites
- Test all user flows (add/remove/resize columns)

---

## Timeline

**Total Estimated Time:** 3 hours

1. Enhance UnifiedColumnService: 30 min
2. Refactor ColumnManager: 45 min
3. Simplify ColumnManagementBehavior: 60 min
4. Update Documentation: 15 min
5. Quality Gates: 30 min

**Target Completion:** Same session (2026-01-02)

---

## Next Steps

1. ✅ Create migration plan (this document)
2. ⏭️ Enhance UnifiedColumnService with missing methods
3. ⏭️ Refactor ColumnManager to thin adapter
4. ⏭️ Simplify ColumnManagementBehavior
5. ⏭️ Run quality gates
6. ⏭️ Merge to main

