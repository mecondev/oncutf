# Codebase Cleaning Plan — 2025-12-24

**Status:** In Progress (Phases A, B, B+, D, E Complete — Finalization Pending)  
**Author:** Michael Economou  
**Goal:** Clean dead code, stale comments, duplicate patterns, and improve type safety

**Completed:** 5 phases, 50 files changed, ~230 lines removed  
**Remaining:** Phase F (optional cleanup), finalization and merge

---

## Executive Summary

**Completed work:**
- ~~**~50 "Phase X" comments** referencing completed refactorings~~ ✅ **Phase A** (13 files)
- ~~**Duplicate `normalize_path()` functions**~~ ✅ **Phase B** (6 files)
- ~~**12 instances of duplicate row selection pattern**~~ ✅ **Phase B** (6 files)
- ~~**4 legacy main_window access patterns**~~ ✅ **Phase B+** (6 files)
- ~~**20+ ThemeEngine imports to migrate**~~ ✅ **Phase D** (22 files)
- ~~**8 imports from deprecated `theme.py`** module~~ ✅ **Phase E** (9 files)
- ~~**MetadataWaitingDialog alias**~~ ✅ **Phase E** (3 files)

**Optional cleanup:**
- **~35 dead functions/classes** that are never called (Phase F)
- **~50 modules** with `ignore_errors=true` in mypy (gradual strictness)

---

## ✅ Phase A: Safe Cleanup (COMPLETED)

**Branch:** `refactor/2025-12-24/cleanup-phase-a`  
**Commit:** `9debcdc4`  
**Status:** Merged to main

### Completed Actions:
1. ✅ Removed ~15 "Phase X" references from comments
2. ✅ Cleaned author headers (removed `(refactored)` suffix from 2 files)
3. ✅ Removed dead commented import in `file_table_view.py`
4. ✅ Simplified optimization comments (removed phase numbers)

**Files changed:** 13 files  
**Quality gates:** All passed (ruff ✓, mypy ✓, pytest 592+ ✓)

---

## ✅ Phase B: Duplicate Code Consolidation (COMPLETED)

**Branch:** `refactor/2025-12-24/consolidate-phase-b`  
**Commit:** `712ce382`  
**Status:** Merged to main

### Completed Actions:
1. ✅ **Removed duplicate `normalize_path()` from `path_utils.py`**
   - Kept canonical version in `path_normalizer.py` (20+ usages)
   - Removed unused duplicate with different behavior (OS-native vs forward slashes)

2. ✅ **Created `get_selected_row_set()` helper function**
   - Replaced 12 instances of `{index.row() for index in selection_model.selectedRows()}`
   - Added to `selection_provider.py`
   - Updated 6 files: `selection_mixin.py`, `file_table_view.py`, `selection_manager.py`, etc.

3. ✅ Fixed `test_path_utils.py` to use correct import
4. ✅ Removed unused `os` import from `path_utils.py`

**Files changed:** 6 files  
**Quality gates:** All passed (ruff 11 fixes ✓, mypy ✓, pytest 592+ ✓)

---

## ✅ Phase B+: Legacy Code Cleanup (COMPLETED)

**Branch:** `refactor/2025-12-24/consolidate-phase-b`  
**Commits:** `448ec69a`, `bd5dd269`  
**Status:** Ready to merge

### Completed Actions:
1. ✅ **Removed invalid `store_hash()` calls (Critical Bug Fix)**
   - HashManager has no store_hash() method — hash is auto-stored by calculate_hash()
   - Removed 3 invalid calls causing "object has no attribute" warnings
   - Files: hash_operations_manager.py, unified_metadata_manager.py, direct_metadata_loader.py

2. ✅ **Fixed controller method calls**
   - `get_all_files()` → `get_loaded_files()`
   - `get_recursive_mode()` → `is_recursive_mode()`
   - Fixed FileStore method calls in metadata_controller

3. ✅ **Replaced legacy main_window access with manager registry**
   - `main_window.table_manager` → `get_manager("table")`
   - `main_window.metadata_cache` → `get_manager("metadata").metadata_cache`
   - Proper dependency injection pattern (4 locations fixed)

4. ✅ **Fixed export_metadata API call**
   - `export_metadata_to_file()` (doesn't exist) → `MetadataExporter().export_files()`
   - Added TODO for StructuredMetadataManager.get_common_fields() (not implemented yet)

**Files changed:** 6 files  
**Quality gates:** All passed (ruff ✓, pytest 888 ✓)

---

## 1. Dead Code (Remaining - Low Priority)

### 1.1 Definitely Unused Functions

| File | Line | Function/Class | Issue |
|------|------|----------------|-------|
| `oncutf/utils/file_size_formatter.py` | 153 | `FileSizeCalculator` class | Never instantiated |
| `oncutf/utils/multiscreen_helper.py` | 68 | `ensure_on_screen()` | Never called |
| `oncutf/utils/multiscreen_helper.py` | 109 | `position_dialog_center()` | Never called |
| `oncutf/utils/multiscreen_helper.py` | 154 | `position_near_widget()` | Never called (different function exists in `dialog_position_helper.py`) |
| `oncutf/utils/progress_manager_factory.py` | 236 | `cleanup()` | Never called |
| `oncutf/utils/progress_manager_factory.py` | 273 | `create_simple_progress()` | Never called |
| `oncutf/utils/file_drop_helper.py` | 285 | `FileDropZone` class | Never instantiated |
| `oncutf/utils/selection_provider.py` | 172 | `get_selected_count()` | Never called |
| `oncutf/utils/selection_provider.py` | 182 | `has_selection()` | Never called |
| `oncutf/utils/metadata_loader.py` | 48 | `_is_cached()` | Never called |
| `oncutf/utils/metadata_exporter.py` | 223 | `_format_metadata_for_text()` | Never called |
| `oncutf/utils/fonts.py` | 30 | `get_icon_font()` | Never called (project uses `get_icon_font_family()`) |
| `oncutf/core/conflict_resolver.py` | 349 | `_get_unique_filename()` | Never called |
| `oncutf/core/batch_processor.py` | 219 | `_should_skip_file()` | Never called |
| `oncutf/core/batch_processor.py` | 239 | `_process_single_file()` | Never called |
| `oncutf/core/file_store.py` | 131 | `get_file_by_index()` | Never called |
| `oncutf/core/application_context.py` | 435 | `cleanup()` | Never called |
| `oncutf/core/application_context.py` | 445 | `get_manager()` | Never called (uses internal method) |
| `oncutf/core/application_context.py` | 450 | `has_manager()` | Never called |
| `oncutf/core/application_context.py` | 455 | `list_managers()` | Never called |
| `oncutf/core/metadata/metadata_cache_service.py` | 215 | `get_cache_stats()` | Never called externally |
| `oncutf/core/hash/hash_manager.py` | 57 | `clear_cache()` | Never called |
| `oncutf/ui/main_window.py` | 637 | `_on_file_selection_changed()` | Never called |
| `oncutf/ui/main_window.py` | 823 | `_calculate_preview_async()` | Never called |
| `oncutf/ui/widgets/file_table_view.py` | 375 | `get_visible_rows()` | Never called |
| `oncutf/ui/widgets/file_table_view.py` | 319 | `select_files_by_path()` | Never called |
| `oncutf/ui/widgets/metadata_tree_view.py` | 231 | `_on_search_text_changed()` | Never called |
| `oncutf/ui/widgets/metadata_tree_view.py` | 257 | `_clear_search()` | Never called |
| `oncutf/ui/widgets/interactive_header.py` | 213 | `get_column_width()` | Never called |
| `oncutf/ui/widgets/interactive_header.py` | 218 | `set_column_width()` | Never called |
| `oncutf/ui/widgets/interactive_header.py` | 223 | `get_visible_columns()` | Never called |
| `oncutf/ui/widgets/custom_message_dialog.py` | 774 | `exec_with_timeout()` | Never called |
| `oncutf/ui/mixins/selection_mixin.py` | 161 | `_update_selection_highlight()` | Never called (dead code) |
| `oncutf/ui/mixins/drag_drop_mixin.py` | 292 | `_start_internal_drag()` | Never called (dead code) |
| `oncutf/ui/mixins/drag_drop_mixin.py` | 262 | `_handle_drop_from_tree()` | Never called (dead code) |

### 1.2 Unused Exports

| File | Export | Issue |
|------|--------|-------|
| `oncutf/utils/__init__.py` | `ColumnConfig` | Exported but never imported anywhere |

### 1.3 Recommended Actions

**Safe to remove immediately:**
- `FileSizeCalculator` class (never used)
- `multiscreen_helper.py` functions: `ensure_on_screen()`, `position_dialog_center()`, `position_near_widget()`
- `progress_manager_factory.py` functions: `cleanup()`, `create_simple_progress()`

**Review before removal (may be for future use):**
- `cleanup_*` functions in `application_context.py` (may be needed for proper shutdown)
- `get_cache_stats()` functions (development utilities)

---

## 2. Stale Comments (Medium Priority)

### 2.1 Phase Reference Comments (Completed Refactorings)

These reference completed refactoring phases and should be simplified:

| File | Lines | Current Comment | Action |
|------|-------|-----------------|--------|
| `oncutf/ui/widgets/metadata_tree_view.py` | 167 | `# Controller for layered architecture (Phase 4 refactoring)` | Remove "(Phase 4 refactoring)" |
| `oncutf/ui/widgets/metadata_tree_view.py` | 173 | `# Drag handler for drag & drop operations (Phase 2 refactoring)` | Remove "(Phase 2 refactoring)" |
| `oncutf/ui/widgets/metadata_tree_view.py` | 176 | `# View configuration handler (Phase 2 refactoring)` | Remove "(Phase 2 refactoring)" |
| `oncutf/ui/widgets/metadata_tree_view.py` | 179 | `# Search handler (Phase 3 refactoring)` | Remove "(Phase 3 refactoring)" |
| `oncutf/ui/widgets/metadata_tree_view.py` | 182 | `# Selection handler (Phase 4 refactoring)` | Remove "(Phase 4 refactoring)" |
| `oncutf/ui/widgets/metadata_tree_view.py` | 185 | `# Modifications handler (Phase 5 refactoring)` | Remove "(Phase 5 refactoring)" |
| `oncutf/ui/widgets/metadata_tree_view.py` | 188 | `# Cache handler (Phase 6 refactoring)` | Remove "(Phase 6 refactoring)" |
| `oncutf/ui/widgets/metadata_tree_view.py` | 281 | `"""Lazy initialization of controller layer (Phase 4 refactoring)."""` | Simplify docstring |
| `oncutf/ui/widgets/metadata_tree_view.py` | 802 | `# Use controller for building tree model (Phase 4 refactoring)` | Remove phase reference |
| `oncutf/ui/widgets/metadata_tree/__init__.py` | 27-55 | `# Phase 1: Data model only`, `# Phase 2: Service layer`, `# Phase 3: Controller layer` | Simplify to descriptive comments |
| `main.py` | 212 | `# Configure default services for dependency injection (Phase 6)` | Remove "(Phase 6)" |
| `main.py` | 217 | `logger.info("Default services configured (Phase 6 DI)")` | Remove "(Phase 6 DI)" |
| `oncutf/ui/main_window.py` | 56 | `# Use InitializationOrchestrator for structured initialization (Phase 4)` | Remove "(Phase 4)" |
| `oncutf/ui/main_window.py` | 1331 | `Phase 2 of Application Context Migration.` | Remove phase reference |
| `oncutf/models/file_group.py` | 7 | `Part of Phase 2: State Management Fix.` | Remove phase reference |
| `oncutf/models/counter_scope.py` | 7 | `Part of Phase 2: State Management Fix.` | Remove phase reference |
| `oncutf/modules/metadata_module.py` | 9 | `Refactored in Phase 3 (Dec 2025) to delegate...` | Keep description, remove "Phase 3" |
| `oncutf/core/persistent_hash_cache.py` | 21 | `# Increased from 500 to 1000 for better hit rate (Phase 3 optimization)` | Remove phase reference |
| `oncutf/core/cache/persistent_metadata_cache.py` | 21 | `# Increased from 1000 to 2000 for better hit rate (Phase 3 optimization)` | Remove phase reference |
| `oncutf/core/application_context.py` | 60, 298 | `# Manager registry (Phase 2: centralized manager access)` | Remove phase reference |

### 2.2 Legacy Method Comments

| File | Lines | Comment | Action |
|------|-------|---------|--------|
| `oncutf/ui/main_window.py` | 664 | `# Legacy method - logic moved to Application Service` | Consider removing the method |
| `oncutf/ui/main_window.py` | 669 | `# Legacy method - logic moved to Application Service` | Consider removing the method |
| `oncutf/ui/main_window.py` | 769 | `# Legacy method - logic moved to WindowConfigManager` | Consider removing the method |

### 2.3 Dead Import Comments

| File | Line | Comment | Action |
|------|------|---------|--------|
| `oncutf/ui/widgets/file_table_view.py` | 15 | `# from oncutf.config import FILE_TABLE_COLUMN_CONFIG  # deprecated: using UnifiedColumnService` | Remove commented import |

### 2.4 Author Header Cleanup

| File | Issue | Action |
|------|-------|--------|
| `oncutf/core/metadata/metadata_cache_service.py` | `Author: Michael Economou (refactored)` | Remove "(refactored)" |
| `oncutf/core/metadata/metadata_loader.py` | `Author: Michael Economou (refactored)` | Remove "(refactored)" |
| `oncutf/core/metadata/metadata_writer.py` | `Author: Michael Economou (refactored)` | Remove "(refactored)" |

---

## 3. Deprecated Modules Still in Use (Remaining - Medium Priority)

### 3.1 theme_engine.py

**Location:** `oncutf/utils/theme_engine.py`

**Deprecation comment:**
```python
"""
DEPRECATED: This module is a facade for backwards compatibility.
Use ThemeManager directly for new code.
"""
```

**Current usages (20+ imports):**
- `main.py`
- `oncutf/ui/widgets/ui_delegates.py`
- `oncutf/ui/widgets/styled_combo_box.py`
- `oncutf/ui/widgets/rename_module_widget.py`
- `oncutf/ui/widgets/rename_modules_area.py`
- `oncutf/ui/widgets/progress_widget.py`
- `oncutf/ui/widgets/preview_tables_view.py`
- `oncutf/ui/widgets/original_name_widget.py`
- `oncutf/ui/widgets/name_transform_widget.py`
- `oncutf/ui/widgets/metadata_validated_input.py`
- `oncutf/ui/widgets/metadata_history_dialog.py`
- `oncutf/ui/widgets/interactive_header.py`
- `oncutf/ui/widgets/metadata/styling_handler.py`
- `oncutf/ui/widgets/final_transform_container.py`
- And more...

**Action:** Migration needed — cannot remove without updating all imports.

### 3.2 theme.py

**Location:** `oncutf/utils/theme.py`

**Deprecation comment:**
```python
"""
DEPRECATED: These helper functions delegate to ThemeManager.
"""
```

**Current usages (10+ imports):**
- `oncutf/utils/placeholder_helper.py`
- `oncutf/ui/widgets/ui_delegates.py`
- `oncutf/ui/widgets/preview_tables_view.py`
- `oncutf/ui/widgets/metadata_edit_dialog.py`

**Action:** Migration needed — update imports to use `ThemeManager` directly.

### 3.3 MetadataWaitingDialog

**Location:** `oncutf/ui/widgets/metadata_waiting_dialog.py`

**Marked deprecated** but still used in:
- `oncutf/core/drag/drag_manager.py` (lines 265, 270)
- `oncutf/ui/main_window.py` (lines 1251, 1266)
- `oncutf/ui/widgets/__init__.py` (lines 21, 55)

**Action:** Assess if still needed; if not, remove usages and delete.

---

## 4. Other Cleanup Opportunities (Remaining - Low Priority)

### 4.1 validate_rotation() Consolidation

**Files:**
- `oncutf/utils/metadata_validators.py` (lines 16-61)
- `oncutf/domain/metadata_field_validators.py` (lines 222-270)

**Issue:** Two different rotation validators with different signatures.

**Action:** Consolidate into single function; update callers.

### 4.2 format_file_size() Consolidation

**Files:**
- `oncutf/utils/file_size_formatter.py` — `FileSizeFormatter.format_size()`
- `oncutf/utils/text_helpers.py` — `format_file_size_stable()`
- `oncutf/utils/metadata_exporter.py` — `_format_file_size()`

**Issue:** Three implementations with slightly different features.

**Action:** Unify in `FileSizeFormatter`; other functions should delegate to it.

### 4.4 get_selected_files() — MEDIUM PRIORITY

**Files affected:**
- `oncutf/core/ui_managers/table_manager.py`
- `oncutf/ui/widgets/file_table_view.py`
- `oncutf/ui/widgets/metadata_edit_dialog.py`
- `oncutf/ui/widgets/rename_history_dialog.py`
- `oncutf/ui/widgets/metadata_history_dialog.py`
- `oncutf/ui/widgets/hash_generation_dialog.py`

**Issue:** Selection retrieval logic implemented in multiple places.

**Action:** Use `SelectionProvider` consistently across all widgets.

### 4.5 Selection Row Pattern — MEDIUM PRIORITY

**Pattern appearing 14+ times:**
```python
selected_rows = {index.row() for index in selection_model.selectedRows()}
```

**Action:** Extract to helper function:
```python
def get_selected_row_set(selection_model: QItemSelectionModel) -> set[int]:
    return {index.row() for index in selection_model.selectedRows()}
```3 History Dialog Base Class Extraction| Delegates to specialized handlers |
| 626-659 | Multiple styling methods | Use `StylingHandler` methods |

**Action:** Verify no external dependencies use these directly, then remove.

---

## 6. Mypy Strictness Improvements

### 6.1 Current State

- **~50 modules** with `ignore_errors=true`
- **2,815 typing issues** (ANN rules)
- **100+ `# type: ignore`** comments
Type Safety Improvements (Remaining - Medium Priority)
### 6.2 Typing Issues Breakdown (from ruff ANN)

| Rule | Count | Description |
|------|-------|-------------|
| ANN201 | 1,145 | Missing return type (public functions) |
| ANN001 | 1,025 | Missing type for function arguments |
| ANN202 | 308 | Missing return type (private functions) |
| ANN204 | 173 | Missing return type (`__init__`, `__new__`) |
| ANN401 | 146 | Use of `Any` type (too broad) |
| ANN003 | 10 | Missing `**kwargs` type |
| ANN205 | 4 | Missing return type (static methods) |

### 6.3 Recommended Strictness Progression

**Step 1: Enable mypy for Controllers (4 files, already clean)**
```toml
[[tool.mypy.overrides]]
module = ["oncutf.controllers.*"]
ignore_errors = false
disallow_untyped_defs = false  # Start lenient
```

**Step 2: Enable mypy for Models (8 files)**
```toml
[[tool.mypy.overrides]]
module = ["oncutf.models.*"]
ignore_errors = false
```

**Step 3: Enable F403 in Ruff (only 4 violations)**
```toml
# Remove F403, F405 from ignore list
# Then fix the 4 wildcard import occurrences
```

**Step 4: Migrate modules one-by-one from ignore_errors=true**
- Start with smaller modules: `conflict_resolver`, `performance_monitor`
- Use `mypy --show-error-stats` to track progress

### 6.4 Typing Inconsistencies to Fix

| Issue | Current | Standard |
|-------|---------|----------|
| Optional syntax | `Optional["SomeType"]` | `SomeType \| None` (Python 3.12+) |
| `__init__` return | Often omitted | `-> None` |
| Type aliases | Raw `dict[str, Any]` | Use from `type_aliases.py` |

---

## 8. Ruff Rules to Consider Enabling (Remaining - Low Priority)

| Rule | Current Violations | Impact |
|------|-------------------|--------|
| `F403` | 4 | Wildcard imports — easy to fix |
| `RET502/503` | 5 | Implicit returns |
| `PTH*` | ~20 | Prefer `pathlib` over `os.path` |
| `FURB*` | ~10 | Modern Python idioms |

---

## 9. Remaining Action Plan

### ~~Phase A: Safe Cleanup~~ ✅ COMPLETED

**Branch:** `refactor/2025-12-24/cleanup-phase-a` (merged to main)

### ~~Phase B: Duplicate Code Consolidation~~ ✅ COMPLETED

**Branch:** `refactor/2025-12-24/consolidate-phase-b` (merged to main)

---

## ✅ Phase D: Deprecated Module Migration — ThemeEngine (COMPLETED)

**Branch:** `refactor/2025-12-24/consolidate-phase-b` (same branch)  
**Commit:** `c48a6164`  
**Status:** Completed

### Completed Actions:

**1. Migrated from ThemeEngine facade to ThemeManager singleton (22 files)**

Replaced all `ThemeEngine()` instantiations with `get_theme_manager()` calls:

- **Main application:**
  - `main.py`: Removed duplicate theme manager, simplified theme application callback
  
- **Rename modules (3 files):**
  - `oncutf/modules/counter_module.py`
  - `oncutf/modules/specified_text_module.py`
  - `oncutf/modules/text_removal_module.py`

- **UI widgets (12 files):**
  - `oncutf/ui/widgets/file_table_view.py` — row height from theme
  - `oncutf/ui/widgets/styled_combo_box.py` — delegate + theme height
  - `oncutf/ui/widgets/rename_module_widget.py` — drag handle colors + combo height
  - `oncutf/ui/widgets/rename_modules_area.py` — drop indicator + placeholder colors
  - `oncutf/ui/widgets/ui_delegates.py` — type hints updated to ThemeManager
  - `oncutf/ui/widgets/progress_widget.py` — bar colors from theme
  - `oncutf/ui/widgets/preview_tables_view.py` — table row heights (2 occurrences)
  - `oncutf/ui/widgets/name_transform_widget.py` — combo height
  - `oncutf/ui/widgets/original_name_widget.py` — secondary text color
  - `oncutf/ui/widgets/metadata_validated_input.py` — combo height
  - `oncutf/ui/widgets/metadata_history_dialog.py` — table row height
  - `oncutf/ui/widgets/interactive_header.py` — context menu stylesheet
  - `oncutf/ui/widgets/final_transform_container.py` — combo height
  - `oncutf/ui/widgets/metadata/styling_handler.py` — combo box styling

- **UI mixins (1 file):**
  - `oncutf/ui/mixins/metadata_context_menu_mixin.py` — context menu styling

- **Test files (2 files):**
  - `tests/test_metadata_tree_view.py` — updated fixture to use get_theme_manager()
  - `tests/test_hierarchical_combo_box.py` — updated fixture to use get_theme_manager()

**2. Added backwards compatibility tokens to THEME_TOKENS**

Added to `oncutf/config.py`:
```python
# Component-Specific: ComboBoxes
"combo_dropdown_background": "#181818",
"combo_item_background_hover": "#3e5c76",
"combo_item_background_selected": "#748cab",
```

**3. Import organization improvements**

- Moved inline `from oncutf.utils.theme_engine import ThemeEngine` to top-level imports
- Changed to `from oncutf.core.theme_manager import get_theme_manager`
- Updated TYPE_CHECKING imports in `ui_delegates.py`

**Files changed:** 22 files  
**Lines changed:** +68 insertions, -87 deletions  
**Quality gates:** ruff ✓, pytest ✓ (888 passed, 11 skipped)

### Migration Summary

| Component | Before | After |
|-----------|--------|-------|
| Import | `from oncutf.utils.theme_engine import ThemeEngine` | `from oncutf.core.theme_manager import get_theme_manager` |
| Usage | `theme = ThemeEngine()` | `theme = get_theme_manager()` |
| Type hint | `theme: "ThemeEngine"` | `theme: "ThemeManager"` |
| Result | New instance per call (inefficient) | Singleton pattern (efficient) |

### Remaining ThemeEngine Usage

**test_theme_integration.py** — Intentionally NOT migrated  
This test file specifically tests the ThemeEngine facade for backwards compatibility.  
It verifies that the facade correctly delegates to ThemeManager.

---

### Phase C: Type Safety Improvements (DEFERRED)

**Estimated effort:** 4-6 hours  
**Complexity:** High (116 mypy errors, 54 Qt-related)

Analysis showed this phase needs module-by-module approach due to Qt typing complexity.  
Deferred in favor of higher-value quick wins (Phase D completed instead).

1. Enable mypy for `oncutf.controllers.*`
2. Enable mypy for `oncutf.models.*`
3. Enable `F403` in ruff, fix violations
4. Add `-> None` to `__init__` methods in strict modules

### ~~Phase D: ThemeEngine Migration~~ ✅ **DONE** (commit c48a6164)

**Target:** Deprecated `theme_engine.py` module  
**Time:** 90 minutes  
**Impact:** Critical (22 files, ~140 usages, 8 years of legacy)  
**Files:** 22 files modified

Successfully migrated all `ThemeEngine` usages to `ThemeManager`:
- 6 direct `ThemeEngine.get_color()` usages → `ThemeManager.get_color()`
- 16 indirect usages via imports or get_instance() → `get_theme_manager()`
- Added 3 backwards compatibility combo tokens to prevent breaking untouched code

**Quality gates:** ✅ All passed
- `ruff check .` → All checks passed  
- `pytest` → 888 passed, 11 skipped

---

### ~~Phase E: Migrate Deprecated Helpers~~ ✅ **DONE** (commit ff631b1a)

**Target:** `theme.py` module and `MetadataWaitingDialog` alias  
**Time:** 45 minutes  
**Impact:** High (final cleanup of deprecated imports)  
**Files:** 9 files modified

**E1. Migrate `theme.py` usages to ThemeManager (6 files)** ✅

Successfully migrated all deprecated helper functions:
- `oncutf/utils/placeholder_helper.py` (1 usage)
- `oncutf/ui/widgets/metadata_edit_dialog.py` (1 usage)
- `oncutf/ui/widgets/ui_delegates.py` (13 total: 2 imports, multiple usages)
- `oncutf/ui/widgets/preview_tables_view.py` (2 usages)
- `oncutf/ui/widgets/color_grid_menu.py` (10 total: inline imports + multiple usages)
- `oncutf/ui/delegates/color_column_delegate.py` (3 usages)

**Migration pattern:**
```python
# Before
from oncutf.utils.theme import get_theme_color, get_qcolor
color = get_theme_color("background")
qcolor = get_qcolor("text")

# After
from oncutf.core.theme_manager import get_theme_manager
theme = get_theme_manager()
color = theme.get_color("background")
qcolor = QColor(theme.get_color("text"))
```

**E2. Remove MetadataWaitingDialog alias (3 files)** ✅

Replaced all backward compatibility alias usages:
- `oncutf/ui/main_window.py` — replaced findChildren and isinstance references
- `oncutf/core/drag/drag_manager.py` — replaced import and isinstance check
- `oncutf/ui/widgets/__init__.py` — removed export statement

**Quality gates:** ✅ All passed
- `ruff check .` → All checks passed
- `pytest` → 888 passed, 11 skipped

---

### Phase F: Optional Deep Cleanup (LOW PRIORITY)
1. ~~Migrate `theme_engine.py` usages to `ThemeManager`~~ ✅ **DONE**
2. Migrate `theme.py` usages (if any remain)
3. Assess and remove `MetadataWaitingDialog` if no longer needed
4. Remove deprecated wrapper methods from `metadata_module_widget.py`

### Phase F: Additional Cleanup (Optional)

**Estimated effort:** Variable

1. Remove dead code from Section 1 (verify usages first)
2. Remove legacy methods from Section 2
3. Consolidate `validate_rotation()` and `format_file_size()`
4. Extract `BaseHistoryDialog` class

---

## 10. Quality Gates

After each phase:

```b1sh
ruff check .           # Must pass with 0 errors
mypy .                 # Check for regressions
pytest                 # All 592+ tests must pass
python main.py         # Smoke test — app must launch
```

---

## 10. Notes

- **Do not remove** deprecated modules (`theme_engine.py`, `theme.py`) without migration
- **Do not remove** `# type: ignore` comments for PyQt5-stubs limitations
- **Keep** comments that document active fallback behavior
- **Test** each change before committing
