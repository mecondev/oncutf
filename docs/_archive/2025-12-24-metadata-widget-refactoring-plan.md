# MetadataWidget Refactoring Plan

**Date:** 2025-12-24  
**Author:** Michael Economou  
**Target file:** `oncutf/ui/widgets/metadata_widget.py` (1565 lines → target ~400 lines)  
**Status:** 🚀 **IN PROGRESS**

---

## Overview

The `MetadataWidget` is a PyQt5 widget for selecting metadata sources (file dates, hash, EXIF).
It has grown to 1565 lines and mixes several responsibilities:

1. **UI Setup & Layout** (~100 lines)
2. **Category Management** (~150 lines) - combo box population, availability
3. **Hash Operations** (~200 lines) - hash checking, calculation dialogs
4. **Metadata Operations** (~200 lines) - metadata keys collection, grouping
5. **Field Formatting** (~200 lines) - display formatting helpers
6. **Styling** (~150 lines) - theme application, combo box styling
7. **Signal/Event Handling** (~200 lines) - emit_if_changed, selection handlers
8. **Data Access** (~150 lines) - get_data, get_selected_files, cache access

---

## Target Architecture

```
oncutf/ui/widgets/metadata/
├── __init__.py                  # Public exports
├── metadata_widget.py           # Main widget (~400 lines, thin wrapper)
├── category_manager.py          # Category combo box management (~200 lines)
├── hash_handler.py              # Hash operations & dialogs (~250 lines)
├── metadata_keys_handler.py     # Metadata keys collection & grouping (~300 lines)
├── field_formatter.py           # Field name formatting utilities (~150 lines)
└── styling_handler.py           # Theme/styling application (~100 lines)
```

---

## Execution Plan

### Phase 1: Create Package Structure & Field Formatter
**Branch:** `refactor/2025-12-24/metadata-widget-phase1`  
**Estimated time:** 20 min

**Actions:**
1. Create `oncutf/ui/widgets/metadata/` package
2. Create `__init__.py` with exports
3. Extract `_format_field_name`, `_format_camel_case`, `format_metadata_key_name` to `field_formatter.py`
4. Update imports in `metadata_widget.py`

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: extract field formatter from MetadataWidget (phase 1)`

---

### Phase 2: Extract Metadata Keys Handler
**Branch:** `refactor/2025-12-24/metadata-widget-phase2`  
**Estimated time:** 30 min

**Actions:**
1. Create `metadata_keys_handler.py`
2. Move: `populate_metadata_keys`, `_group_metadata_keys`, `_classify_metadata_key`, `get_available_metadata_keys`
3. Handler takes widget reference for combo box access
4. Update imports in `metadata_widget.py`

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: extract metadata keys handler from MetadataWidget (phase 2)`

---

### Phase 3: Extract Hash Handler
**Branch:** `refactor/2025-12-24/metadata-widget-phase3`  
**Estimated time:** 30 min

**Actions:**
1. Create `hash_handler.py`
2. Move: `populate_hash_options`, `_calculate_hashes_for_files`, `_check_hash_calculation_requirements`, `_check_files_have_hash`, `_get_supported_hash_algorithms`
3. Handler takes widget reference for combo box and parent window access
4. Update imports in `metadata_widget.py`

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: extract hash handler from MetadataWidget (phase 3)`

---

### Phase 4: Extract Category Manager
**Branch:** `refactor/2025-12-24/metadata-widget-phase4`  
**Estimated time:** 30 min

**Actions:**
1. Create `category_manager.py`
2. Move: `update_category_availability`, `_on_category_changed`, `update_options`, `populate_file_dates`
3. Manager coordinates with hash_handler and metadata_keys_handler
4. Update imports in `metadata_widget.py`

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: extract category manager from MetadataWidget (phase 4)`

---

### Phase 5: Extract Styling Handler
**Branch:** `refactor/2025-12-24/metadata-widget-phase5`  
**Estimated time:** 20 min

**Actions:**
1. Create `styling_handler.py`
2. Move: `_apply_disabled_combo_styling`, `_apply_normal_combo_styling`, `_apply_combo_theme_styling`, `_apply_disabled_category_styling`, `_apply_category_styling`, `_ensure_theme_inheritance`
3. Handler provides styling methods for combo boxes
4. Update imports in `metadata_widget.py`

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: extract styling handler from MetadataWidget (phase 5)`

---

### Phase 6: Consolidate & Cleanup
**Branch:** `refactor/2025-12-24/metadata-widget-phase6`  
**Estimated time:** 25 min

**Actions:**
1. Clean up `metadata_widget.py`:
   - Keep only: `__init__`, `setup_ui`, `get_data`, `emit_if_changed`, signal handlers
   - Delegate all operations to handlers
2. Update all docstrings
3. Update `__init__.py` exports
4. Verify all public APIs work

**Validation:**
```bash
ruff check .
mypy .
pytest tests/ -q
```

**Commit:** `refactor: finalize MetadataWidget refactoring (phase 6)`

---

## Method Distribution

### metadata_widget.py (Main Widget - ~400 lines)
- `__init__` - Initialize handlers
- `setup_ui` - UI setup (unchanged)
- `get_data` - Return state dict
- `emit_if_changed`, `force_preview_update` - Signal emission
- `_emit_settings_changed` - Settings change handler
- `_on_hierarchical_item_selected`, `_on_hierarchical_selection_confirmed` - Combo handlers
- `_on_selection_changed`, `_on_metadata_loaded` - Event handlers
- `_get_selected_files`, `_get_app_context` - Data access helpers
- `is_effective` - Static validation
- `clear_cache`, `refresh_metadata_keys`, `trigger_update_options` - Public API

### field_formatter.py (~150 lines)
- `format_metadata_key_name` - Format key for display
- `_format_field_name` - Format underscore-separated names
- `_format_camel_case` - Format camelCase names
- `FIELD_REPLACEMENTS` - Constants dict for common replacements

### metadata_keys_handler.py (~300 lines)
- `populate_metadata_keys` - Populate combo with grouped keys
- `_group_metadata_keys` - Group keys by category
- `_classify_metadata_key` - Classify key into category
- `get_available_metadata_keys` - Get keys from cache
- `_get_metadata_cache_via_context` - Cache access helper
- `_check_files_have_metadata` - Check metadata availability
- `_check_metadata_calculation_requirements` - Check if dialog needed
- `_load_metadata_for_files` - Load metadata for files

### hash_handler.py (~250 lines)
- `populate_hash_options` - Populate hash combo
- `_calculate_hashes_for_files` - Trigger hash calculation
- `_check_hash_calculation_requirements` - Check if dialog needed
- `_check_files_have_hash` - Check hash availability
- `_get_supported_hash_algorithms` - Get supported algorithms
- `_show_calculation_dialog` - Show hash/metadata dialog

### category_manager.py (~200 lines)
- `update_category_availability` - Enable/disable categories
- `_on_category_changed` - Handle category change
- `update_options` - Update options combo
- `populate_file_dates` - Populate file dates options

### styling_handler.py (~100 lines)
- `_apply_disabled_combo_styling` - Disabled state
- `_apply_normal_combo_styling` - Normal state
- `_apply_combo_theme_styling` - Full theme CSS
- `_apply_disabled_category_styling` - Category disabled
- `_apply_category_styling` - Category normal
- `_ensure_theme_inheritance` - Ensure child styles

---

## Risk Mitigation

1. **Each phase is atomic** - can be reverted independently
2. **All gates must pass** - ruff, mypy, pytest before commit
3. **No behavior changes** - pure refactoring, same external API
4. **Incremental extraction** - one handler at a time
5. **Merge to main** - after each phase passes all gates

---

## Progress Tracking

| Phase | Status | Branch | Commit | Notes |
|-------|--------|--------|--------|-------|
| 1 | ⬜ Not Started | - | - | Field formatter |
| 2 | ⬜ Not Started | - | - | Metadata keys handler |
| 3 | ⬜ Not Started | - | - | Hash handler |
| 4 | ⬜ Not Started | - | - | Category manager |
| 5 | ⬜ Not Started | - | - | Styling handler |
| 6 | ⬜ Not Started | - | - | Final cleanup |

---

## Notes

- The `_show_calculation_dialog` method is shared between hash and metadata operations
  - Will keep in hash_handler.py with generic signature
  - Or extract to a shared dialog helper
- Existing signals (`updated`, `settings_changed`) must remain unchanged
- The `is_effective` static method stays in main widget for compatibility
