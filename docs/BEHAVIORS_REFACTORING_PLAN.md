# Behaviors Refactoring Plan

**Author:** Michael Economou  
**Date:** 2026-01-04  
**Status:** Planning

---

## Current State Analysis

### Behaviors Inventory (by size)

| Behavior | Lines | Status | Priority |
|----------|-------|--------|----------|
| `column_management_behavior.py` | 928 | [WARN] Complex | HIGH |
| `metadata_context_menu_behavior.py` | 717 | [WARN] Large | MEDIUM |
| `selection_behavior.py` | 630 | [WARN] Edge case | MEDIUM |
| `drag_drop_behavior.py` | 501 | [OK] Acceptable | LOW |
| `metadata_cache_behavior.py` | 466 | [OK] Acceptable | LOW |
| `metadata_edit/` (package) | 1520 | [OK] Already split | DONE |
| `metadata_scroll_behavior.py` | 325 | [OK] Good | - |

**Total:** 5087 lines across 7 behavior modules + 1 package

---

## Architecture Question: What IS a Behavior?

### Current Pattern
Behaviors are **composition-based alternatives to mixins** that:
- Encapsulate UI interaction logic
- Use Protocol-based typing (no inheritance)
- Attach to widgets without polluting their interface

### The Problem
Some behaviors have grown to include:
- Business logic (should be in services)
- Data transformation (should be in utilities)
- Complex orchestration (should be in controllers)

### The Rule Going Forward
```
Behavior = UI interaction only
         = Event handling
         = Visual state management
         = Widget coordination
         
Behavior != Business decisions
Behavior != Data processing
Behavior != Application state
```

---

## Refactoring Plan

### Phase 1: column_management_behavior.py (928 lines) -> Target: <500

**Analysis:**
- 30+ methods, many are config/validation
- Already delegates to `UnifiedColumnService`
- Has: width management, visibility, persistence, timers

**Split Strategy:**
```
ui/behaviors/column_management/
    __init__.py (20 lines)      <- Re-exports
    column_behavior.py (250)    <- Core behavior (events, signals)
    width_manager.py (200)      <- Width calculations & validation
    visibility_manager.py (150) <- Add/remove column logic
    persistence_handler.py (150)<- Save/load config
    header_configurator.py (100)<- Header setup
```

**What Moves Where:**
- `configure_columns()`, `_setup_header()` -> `header_configurator.py`
- `check_and_fix_column_widths()`, `auto_fit_columns_to_content()` -> `width_manager.py`
- `add_column()`, `remove_column()` -> `visibility_manager.py`
- `_load_column_config()`, `_save_column_config()`, timers -> `persistence_handler.py`

**Main behavior keeps:**
- Event connections
- Delegation to sub-handlers
- Widget reference management

---

### Phase 2: metadata_context_menu_behavior.py (717 lines) -> Target: <400

**Analysis:**
- One giant `show_context_menu()` method (200+ lines)
- Menu building, action handling, column integration all mixed
- Protocol is clean but implementation is monolithic

**Split Strategy:**
```
ui/behaviors/metadata_context_menu/
    __init__.py (20 lines)
    context_menu_behavior.py (200) <- Main behavior, menu display
    menu_builder.py (150)          <- Build menu structure
    action_handlers.py (150)       <- Handle menu actions
    column_integration.py (150)    <- Add/remove column logic
```

**What Moves Where:**
- Menu item creation logic -> `menu_builder.py`
- `_add_column_to_file_view()`, `_remove_column_from_file_view()` -> `column_integration.py`
- Edit/copy/reset handlers -> `action_handlers.py`

---

### Phase 3: selection_behavior.py (630 lines) -> Target: <400

**Analysis:**
- Core selection logic is sound
- Many edge case handlers
- Complex Qt selection model sync

**Split Strategy:**
```
ui/behaviors/selection/
    __init__.py (20 lines)
    selection_behavior.py (250)  <- Main behavior
    range_selector.py (150)      <- Range/shift selection
    sync_handler.py (150)        <- Qt model synchronization
```

**What Moves Where:**
- `_sync_qt_selection_model()`, `sync_selection_safely()` -> `sync_handler.py`
- `select_rows_range()`, shift-click logic -> `range_selector.py`

---

## Implementation Order

### Week 1: column_management_behavior.py
1. Create `ui/behaviors/column_management/` package
2. Extract `persistence_handler.py` first (low risk, clear boundary)
3. Extract `width_manager.py` 
4. Extract `visibility_manager.py`
5. Update imports, run tests
6. Target: 928 -> ~250 lines main behavior

### Week 2: metadata_context_menu_behavior.py
1. Create `ui/behaviors/metadata_context_menu/` package
2. Extract `menu_builder.py` (mechanical extraction)
3. Extract `column_integration.py`
4. Target: 717 -> ~200 lines main behavior

### Week 3: selection_behavior.py
1. Create `ui/behaviors/selection/` package
2. Extract `sync_handler.py`
3. Extract `range_selector.py`
4. Target: 630 -> ~250 lines main behavior

---

## Quality Gates

After each phase:
- [ ] All tests pass (974+)
- [ ] ruff clean
- [ ] mypy clean
- [ ] Main behavior < 300 lines
- [ ] No business logic in behaviors

---

## Expected Results

| Metric | Before | After |
|--------|--------|-------|
| Largest behavior | 928 lines | ~250 lines |
| Behaviors >600 lines | 3 | 0 |
| Average behavior size | 512 lines | ~200 lines |
| Total behavior packages | 1 | 4 |

---

## Notes

### Why Not Just Leave Them?
1. **Cognitive load:** 928 lines is too much to reason about
2. **Testing difficulty:** Hard to test pieces in isolation
3. **Change risk:** Every change touches too much code

### Why Split Instead of Delete?
Behaviors are the **right pattern** for UI interaction - they just grew too large.
The goal is to keep the pattern but with smaller, focused modules.

### Alternative Considered: Move to Services
Some logic could move to `core/ui_managers/` but:
- It's UI-specific (needs widget refs)
- It's already delegating to services where appropriate
- The issue is size, not location

---

## References

- [UI_ARCHITECTURE_PATTERNS.md](UI_ARCHITECTURE_PATTERNS.md) - Behavior pattern docs
- [MIGRATION_STANCE.md](MIGRATION_STANCE.md) - Architecture policy
- [REFACTORING_ROADMAP.md](REFACTORING_ROADMAP.md) - Overall roadmap
