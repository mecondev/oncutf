# Codebase Analysis & Refactoring Plan

**Date:** 2025-12-22  
**Author:** Michael Economou  

---

## Current State Overview

### File Size Analysis (Top 25)

| Lines | File |
|------:|------|
| 1770 | `oncutf/ui/widgets/metadata_tree_view.py` |
| 1500 | `oncutf/utils/theme_engine.py` |
| 1403 | `oncutf/core/database/database_manager.py` |
| 1333 | `oncutf/ui/widgets/metadata_widget.py` |
| 1058 | `oncutf/config.py` |
| 1041 | `oncutf/ui/widgets/file_tree_view.py` |
| 1039 | `oncutf/ui/mixins/column_management_mixin.py` |
| 1036 | `oncutf/ui/main_window.py` |
| 995 | `oncutf/core/rename/unified_rename_engine.py` |
| 979 | `oncutf/core/events/context_menu_handlers.py` |
| 883 | `oncutf/models/file_table_model.py` |
| 878 | `oncutf/ui/widgets/file_table_view.py` |
| 758 | `oncutf/ui/mixins/metadata_edit_mixin.py` |
| 753 | `oncutf/core/ui_managers/ui_manager.py` |
| 729 | `oncutf/core/ui_managers/column_manager.py` |
| 658 | `oncutf/core/unified_metadata_manager.py` |
| 654 | `oncutf/ui/widgets/progress_widget.py` |
| 642 | `oncutf/core/hash/hash_operations_manager.py` |
| 625 | `oncutf/core/metadata_operations_manager.py` |
| 617 | `oncutf/core/metadata/metadata_loader.py` |
| 602 | `oncutf/core/ui_managers/status_manager.py` |
| 576 | `oncutf/core/file_load_manager.py` |
| 568 | `oncutf/utils/exiftool_wrapper.py` |
| 553 | `oncutf/core/database/optimized_database_manager.py` |
| 544 | `oncutf/core/application_service.py` |

### Statistics

- **Total Python files:** 226 (in `oncutf/`)
- **Ruff check:** All checks passed!
- **Main Window:** Reduced from ~2500 to **1036** lines

---

## File Status Assessment

### High Priority - Candidates for Split

| File | Lines | Status | Recommendation |
|------|------:|--------|----------------|
| `metadata_tree_view.py` | 1770 | 🔴 Large | Split into: TreeModel, TreeDelegate, TreeViewUI, TreeEditHandler |
| `metadata_widget.py` | 1333 | 🔴 Large | Split into: WidgetLayout, WidgetActions, EditPanel |

### Medium Priority - Borderline

| File | Lines | Status | Notes |
|------|------:|--------|-------|
| `theme_engine.py` | 1500 | 🟡 Config-heavy | Many data/colors, hard to split meaningfully |
| `database_manager.py` | 1403 | 🟡 OK | Database layer, cohesive |
| `file_tree_view.py` | 1041 | 🟡 Borderline | Could extract drag/drop handling |
| `column_management_mixin.py` | 1039 | 🟡 Borderline | Mixin by design |
| `unified_rename_engine.py` | 995 | 🟡 OK | Core engine, cohesive |
| `context_menu_handlers.py` | 979 | 🟡 OK | Event handlers grouped |

### Low Priority - Acceptable

| File | Lines | Status | Notes |
|------|------:|--------|-------|
| `config.py` | 1058 | 🟢 OK | Configuration file, should stay unified |
| `main_window.py` | 1036 | ✅ Good | Was ~2500, now well-structured |

---

## Completed Refactoring Work

### Phase 1-6 Achievements

1. **Main Window refactoring** - From ~2500 to 1036 lines ✅
2. **Controllers extracted:**
   - `FileLoadController` - File loading orchestration
   - `MetadataController` - Metadata operations
   - `RenameController` - Rename workflow
   - `MainWindowController` - High-level orchestration
3. **Metadata system split:**
   - `UnifiedMetadataManager` (facade)
   - `MetadataWriter` - Save operations
   - `MetadataLoader` - Load orchestration
   - `MetadataCacheService` - Cache operations
   - `MetadataProgressHandler` - Progress dialogs
   - `MetadataShortcutHandler` - Keyboard shortcuts
   - `CompanionMetadataHandler` - Companion files
4. **Code quality:** Ruff clean (0 errors)
5. **Test coverage:** 200+ tests

---

## Known Stubs (Intentional Placeholders)

| File | Method | Status | Priority |
|------|--------|--------|----------|
| `main_window.py` | `global_undo()` | Stub - logs only | 🟡 Medium |
| `main_window.py` | `global_redo()` | Stub - logs only | 🟡 Medium |
| `metadata_commands.py` | `SaveMetadataCommand.undo()` | Partial - doesn't restore files | 🟡 Medium |
| `rename_conflict_resolver.py` | `_ask_user_for_resolution()` | Stub - skips without dialog | 🟢 Low |
| `config.py` | Light theme | Placeholder values | 🟢 Low |

These are **intentional placeholders** for future features, not bugs.

---

## Recommended Next Steps

### Option A: Continue Refactoring (High Impact)

**Target:** `metadata_tree_view.py` (1770 lines)

Split into:
1. `MetadataTreeModel` - Data handling and structure
2. `MetadataTreeDelegate` - Custom rendering
3. `MetadataTreeEditHandler` - Edit operations and validation
4. `MetadataTreeView` - Main view (thin wrapper)

**Estimated effort:** 2-3 hours  
**Risk:** Medium (complex widget with many interactions)

### Option B: Feature Development

Focus on implementing stub features:
- Unified undo/redo system
- Interactive conflict resolution dialog
- Light theme support

### Option C: Stabilization

- Add more integration tests
- Document public APIs
- Performance profiling

---

## Bug Fixed Today

**Issue:** Metadata save appeared successful in logs but didn't actually write to disk.

**Root cause:** `MetadataWriter._save_metadata_files()` was a stub implementation left over from refactoring. The full implementation existed in `UnifiedMetadataManager` but wasn't being called due to delegation chain.

**Fix:** Moved full implementation to `MetadataWriter` with all helper methods:
- `_update_file_after_save()`
- `_update_caches_after_save()`
- `_update_nested_metadata()`
- `_refresh_display_if_current()`
- `_show_save_results()`
- `_record_save_command()`

**Commit:** `d3a562bf` - fix: implement metadata save stub in MetadataWriter

---

## Architecture Notes

The codebase follows a **layered architecture**:

```
┌─────────────────────────────────────────────┐
│                  UI Layer                    │
│  main_window.py, widgets/, delegates/        │
├─────────────────────────────────────────────┤
│              Controller Layer                │
│  controllers/ (FileLoad, Metadata, Rename)   │
├─────────────────────────────────────────────┤
│               Service Layer                  │
│  application_service.py, *_manager.py        │
├─────────────────────────────────────────────┤
│                Core Layer                    │
│  unified_rename_engine, database/, cache/    │
├─────────────────────────────────────────────┤
│               Utility Layer                  │
│  utils/, models/, config.py                  │
└─────────────────────────────────────────────┘
```

Key patterns:
- **Facade pattern:** UnifiedMetadataManager delegates to specialized handlers
- **MVC-ish:** Controllers separate UI from business logic
- **Dependency injection:** Services registered in ApplicationContext
