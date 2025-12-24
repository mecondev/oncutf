# MetadataTreeView Refactoring Plan

**Date:** 2025-12-23  
**Author:** Michael Economou  
**Branch:** `refactor/2025-12-23/metadata-tree-phase2`  
**Target file:** `oncutf/ui/widgets/metadata_tree_view.py` (2043 lines → target ~600 lines)  
**Status:** ✅ **PHASES 1-6 COMPLETED**

---

## Progress Summary

| Phase | Status | Lines Extracted | Commit |
|-------|--------|-----------------|--------|
| Phase 1: Drag Handler | ✅ Complete | ~208 | fb488bf4 |
| Phase 2: View Config | ✅ Complete | ~340 | e347bfa0 |
| Phase 3: Search Handler | ✅ Complete | ~330 | b8c4d394 |
| Phase 4: Selection Handler | ✅ Complete | ~240 | cf0a0b2b |
| Phase 5: Modifications Handler | ✅ Complete | ~140 | 7a1ee4eb |
| Phase 6: Cache Handler | ✅ Complete | ~95 | 16b75c63 |
| **TOTAL EXTRACTED** | | **~1353 lines** | |
| **Current file size** | | **1359 lines** (from 2043) | |

---

## Current State Analysis

### File Statistics
- **Current size:** 2043 lines
- **Target size:** ~500-700 lines (thin view wrapper)
- **Existing package:** `oncutf/ui/widgets/metadata_tree/` with model.py, service.py, controller.py

### Code Sections Identified for Extraction

| Section | Lines (approx) | Target Module |
|---------|----------------|---------------|
| Drag & Drop handling | ~100 | `metadata_tree/drag_handler.py` |
| Model/Column management | ~200 | `metadata_tree/view_config.py` |
| Search field management | ~150 | `metadata_tree/search_handler.py` |
| Metadata display/render | ~300 | Consolidate in `controller.py` |
| Selection handling | ~150 | `metadata_tree/selection_handler.py` |
| Cache/Lazy loading | ~100 | `metadata_tree/cache_handler.py` |
| Modifications tracking | ~150 | `metadata_tree/modifications_handler.py` |
| Helper methods | ~200 | Distribute to appropriate handlers |

---

## Execution Plan

### Phase 1: Extract Drag & Drop Handler
**Estimated time:** 30 min

**Actions:**
1. Create `metadata_tree/drag_handler.py`
2. Move: `dragEnterEvent`, `dragMoveEvent`, `dropEvent`, `_perform_drag_cleanup`, `_complete_drag_cleanup`
3. Wire handler to view

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: extract drag handler from MetadataTreeView`

---

### Phase 2: Extract View Configuration
**Estimated time:** 30 min

**Actions:**
1. Create `metadata_tree/view_config.py`
2. Move: `_setup_tree_view_properties`, `_configure_placeholder_mode`, `_configure_normal_mode`, `_update_header_visibility`, `_connect_column_resize_signals`, `_on_column_resized`, `_update_scrollbar_policy_intelligently`, `_force_style_update`
3. Wire config to view

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: extract view configuration from MetadataTreeView`

---

### Phase 3: Extract Search Handler
**Estimated time:** 30 min

**Actions:**
1. Create `metadata_tree/search_handler.py`
2. Move: `_update_search_field_state`, `_clear_search_field`, `_update_search_suggestions`, `_collect_suggestions_from_tree_model`, `_collect_suggestions_from_metadata`
3. Wire handler to view

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: extract search handler from MetadataTreeView`

---

### Phase 4: Extract Selection Handler
**Estimated time:** 30 min

**Actions:**
1. Create `metadata_tree/selection_handler.py`
2. Move: `_get_current_selection`, `update_from_parent_selection`, `refresh_metadata_from_selection`, `handle_selection_change`, `handle_invert_selection`, `should_display_metadata_for_selection`, `smart_display_metadata_or_empty_state`
3. Wire handler to view

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: extract selection handler from MetadataTreeView`

---

### Phase 5: Extract Modifications Handler
**Estimated time:** 30 min

**Actions:**
1. Create `metadata_tree/modifications_handler.py`
2. Move: `get_modified_metadata`, `get_all_modified_metadata_for_files`, `clear_modifications`, `clear_modifications_for_file`, `has_modifications_for_selected_files`, `has_any_modifications`, `_update_metadata_in_cache`, `_set_metadata_in_cache`, `_remove_metadata_from_cache`
3. Wire handler to view

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: extract modifications handler from MetadataTreeView`

---

### Phase 6: Extract Cache Handler
**Estimated time:** 30 min

**Actions:**
1. Create `metadata_tree/cache_handler.py`
2. Move: `_initialize_cache_helper`, `_get_cache_helper`, `_initialize_direct_loader`, `_get_direct_loader`, `_try_lazy_metadata_loading` (from mixin)
3. Wire handler to view

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: extract cache handler from MetadataTreeView`

---

### Phase 7: Consolidate Display Logic in Controller
**Estimated time:** 45 min

**Actions:**
1. Move display logic to controller: `display_metadata`, `show_empty_state`, `clear_view`, `_render_metadata_view`, `_render_metadata_view_impl`, `display_file_metadata`, `handle_metadata_load_completion`
2. Update controller to handle all rendering orchestration
3. View only calls controller methods

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: consolidate display logic in MetadataTreeController`

---

### Phase 8: Final Cleanup & Documentation
**Estimated time:** 30 min

**Actions:**
1. Clean up MetadataTreeView - only thin wrapper with Qt event overrides
2. Update all docstrings
3. Update `__init__.py` exports
4. Verify all public APIs still work

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: finalize MetadataTreeView refactoring`

---

## Expected Final Structure

```
oncutf/ui/widgets/metadata_tree/
├── __init__.py              # Public exports
├── model.py                 # Pure data structures (292 lines) ✓
├── service.py               # Business logic (582 lines) ✓
├── controller.py            # Qt orchestration (~400 lines)
├── drag_handler.py          # Drag & drop (~100 lines)
├── view_config.py           # View configuration (~150 lines)
├── search_handler.py        # Search functionality (~120 lines)
├── selection_handler.py     # Selection handling (~120 lines)
├── modifications_handler.py # Modifications tracking (~120 lines)
└── cache_handler.py         # Cache/lazy loading (~80 lines)

oncutf/ui/widgets/metadata_tree_view.py  # Thin wrapper (~500 lines)
```

---

## Risk Mitigation

1. **Each phase is atomic** - can be reverted independently
2. **All gates must pass** - ruff, mypy, pytest before commit
3. **No behavior changes** - pure refactoring, same external API
4. **Incremental extraction** - one handler at a time

---

## Progress Tracking

| Phase | Status | Commit Hash | Notes |
|-------|--------|-------------|-------|
| 1     | ⬜ Not started | - | Drag handler |
| 2     | ⬜ Not started | - | View config |
| 3     | ⬜ Not started | - | Search handler |
| 4     | ⬜ Not started | - | Selection handler |
| 5     | ⬜ Not started | - | Modifications handler |
| 6     | ⬜ Not started | - | Cache handler |
| 7     | ⬜ Not started | - | Display consolidation |
| 8     | ⬜ Not started | - | Final cleanup |

---

## Notes

- Existing mixins (`MetadataScrollMixin`, `MetadataCacheMixin`, `MetadataEditMixin`, `MetadataContextMenuMixin`) will remain as-is for now
- Focus on extracting **internal implementation** to handlers
- Public API of `MetadataTreeView` must remain unchanged
