# oncutf Codebase Status — 2025-12-24 Dawn Hour

**Author:** Michael Economou  
**Date:** 2025-12-24  
**Purpose:** Consolidated status of all completed refactorings and remaining cleanup tasks

---

## Current State Summary

| Metric | Value |
|--------|-------|
| **Tests** | 893 passed, 6 skipped |
| **Ruff** | All checks passed |
| **Main files reduced** | metadata_widget.py: 1565→814 lines, metadata_tree_view.py: 2043→1338 lines |

---

## Completed Work (Ready for Archive)

### 1. MetadataTreeView Refactoring ✅
**Source:** `2025-12-23-metadata-tree-refactoring-plan.md`

- **6 phases completed**, 1353 lines extracted to handlers
- **Package:** `oncutf/ui/widgets/metadata_tree/`
  - `drag_handler.py`, `view_config.py`, `search_handler.py`
  - `selection_handler.py`, `modifications_handler.py`, `cache_handler.py`
- **Result:** 33.5% reduction (2043→1338 lines)

### 2. MetadataWidget Refactoring ✅
**Source:** `2025-12-24-metadata-widget-refactoring-plan.md`

- **All 6 phases completed**
- **Package:** `oncutf/ui/widgets/metadata/`
  - `field_formatter.py`, `metadata_keys_handler.py`, `hash_handler.py`
  - `category_manager.py`, `styling_handler.py`
- **Result:** 48% reduction (1565→814 lines)
- **Note:** Original methods marked "Deprecated: Use X instead" — ready for final removal

### 3. Win Cleaning Plan ✅
**Source:** `2025-12-24-win-cleaning-plan.md`

**Completed phases:**
- ✅ Phase A: ~50 "Phase X" comments cleaned (13 files)
- ✅ Phase B: Duplicate `normalize_path()` removed, `get_selected_row_set()` helper created
- ✅ Phase B+: Invalid `store_hash()` calls fixed, legacy main_window access replaced
- ✅ Phase D: ThemeEngine→ThemeManager migration (22 files)
- ✅ Phase E: Deprecated theme.py imports removed (9 files)
- ✅ Phase F: Stale phase reference comments cleaned (7 files)

---

## Remaining Work (Low-Medium Priority)

### 1. Dead Code Removal — LOW PRIORITY

The following unused functions were identified but not yet removed:

| File | Function | Notes |
|------|----------|-------|
| `utils/file_size_formatter.py` | `FileSizeCalculator` class | Never instantiated |
| `utils/multiscreen_helper.py` | `ensure_on_screen()`, `position_dialog_center()`, `position_near_widget()` | Never called |
| `utils/progress_manager_factory.py` | `cleanup()`, `create_simple_progress()` | Never called |
| `utils/file_drop_helper.py` | `FileDropZone` class | Never instantiated |
| `utils/selection_provider.py` | `get_selected_count()`, `has_selection()` | Never called |
| `core/conflict_resolver.py` | `_get_unique_filename()` | Never called |
| `core/batch_processor.py` | `_should_skip_file()`, `_process_single_file()` | Never called |
| `core/file_store.py` | `get_file_by_index()` | Never called |
| `core/application_context.py` | `cleanup()`, `get_manager()`, `has_manager()`, `list_managers()` | Never called |
| `ui/main_window.py` | `_on_file_selection_changed()`, `_calculate_preview_async()` | Never called |
| `ui/mixins/selection_mixin.py` | `_update_selection_highlight()` | Dead code |
| `ui/mixins/drag_drop_mixin.py` | `_start_internal_drag()`, `_handle_drop_from_tree()` | Dead code |

**Recommendation:** Safe to remove in a future cleanup phase.

### 2. MetadataWidget Deprecated Methods — MEDIUM PRIORITY

The widget still contains ~20 deprecated wrapper methods with docstrings like:
```
Deprecated: Use CategoryManager.on_category_changed() instead.
```

These delegate to handlers but add unnecessary indirection. Can be removed after verifying no external callers.

### 3. Duplicate Code Consolidation — LOW PRIORITY

| Pattern | Files | Action |
|---------|-------|--------|
| `validate_rotation()` | `metadata_validators.py`, `metadata_field_validators.py` | Consolidate |
| `format_file_size()` | 3 implementations | Unify in `FileSizeFormatter` |
| `get_selected_files()` | 6+ implementations | Use `SelectionProvider` |

### 4. Type Safety Improvements — DEFERRED

- ~50 modules with `ignore_errors=true` in mypy config
- 2,815 typing issues (ANN rules)
- **Strategy:** Enable mypy module-by-module, starting with controllers and models

### 5. Deprecated Modules — KEEP FOR NOW

| Module | Status | Notes |
|--------|--------|-------|
| `utils/theme_engine.py` | Facade only | All usages migrated to ThemeManager |
| `utils/theme.py` | Facade only | All usages migrated |
| `MetadataWaitingDialog` alias | Compatibility | Still referenced in 3 files |

These are thin facades that delegate to proper implementations. Keep for backward compatibility.

---

## Quality Gates Status

```bash
✓ ruff check .     → All checks passed
✓ pytest           → 893 passed, 6 skipped  
✓ mypy .           → No regressions (existing ignore_errors)
✓ python main.py   → Application launches successfully
```

---

## Recommended Next Steps

1. **Commit current docstring cleanups** (already done this session)
2. **Archive completed plan documents** (this document replaces them)
3. **Optional:** Remove deprecated wrapper methods from MetadataWidget
4. **Optional:** Remove clearly unused functions (dead code list above)
5. **Future:** Gradual mypy strictness improvement

---

## Archived Documents

The following documents are now superseded by this summary:
- `2025-12-23-metadata-tree-refactoring-plan.md` → `_archive/`
- `2025-12-24-metadata-widget-refactoring-plan.md` → `_archive/`
- `2025-12-24-win-cleaning-plan.md` → `_archive/`
