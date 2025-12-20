# Phase 1B: MetadataController — Methods Identification

**Author:** Michael Economou  
**Date:** 2025-12-16  
**Status:** Step 1B.2 — Method identification

---

## Purpose

Document all metadata-related methods currently in MainWindow and ApplicationService that will be migrated to MetadataController.

---

## Current Architecture (3-Layer)

```
┌─────────────────────────────────────────────────────────────┐
│                        MainWindow                           │
│  - UI logic (widgets, signals, layout)                     │
│  - Calls ApplicationService for business operations        │
└────────────────────┬────────────────────────────────────────┘
                     │ delegates
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   ApplicationService                        │
│  - Business coordination                                    │
│  - Delegates to domain managers                            │
└────────────────────┬────────────────────────────────────────┘
                     │ uses
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain Managers                          │
│  - UnifiedMetadataManager                                   │
│  - StructuredMetadataManager                                │
│  - MetadataOperationsManager                                │
│  - TableManager (for cache restoration)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Target Architecture (with MetadataController)

```
┌─────────────────────────────────────────────────────────────┐
│                        MainWindow                           │
│  - Pure UI (widgets, signals, layout)                      │
│  - Delegates to MetadataController                          │
└────────────────────┬────────────────────────────────────────┘
                     │ orchestrates
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   MetadataController                        │
│  - Testable (no Qt dependencies)                            │
│  - Coordinates metadata operations                          │
│  - Aggregates results from multiple managers                │
└────────────────────┬────────────────────────────────────────┘
                     │ uses
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain Managers                          │
│  - UnifiedMetadataManager (loading)                         │
│  - StructuredMetadataManager (structured access)            │
│  - MetadataOperationsManager (editing)                      │
│  - TableManager (cache restoration, display)                │
└─────────────────────────────────────────────────────────────┘
```

---

## Methods to Extract

### 1. From MainWindow (oncutf/ui/main_window.py)

#### Primary Methods (to migrate):

1. **`load_metadata_for_items(items, use_extended, source)`** (Line ~326)
   - Current: Delegates to ApplicationService
   - New: Will call MetadataController.load_metadata()
   - LOC: ~3
   - Complexity: Simple delegate

2. **`restore_fileitem_metadata_from_cache()`** (Line ~349)
   - Current: Delegates to ApplicationService → TableManager
   - New: Will call MetadataController.restore_metadata_from_cache()
   - LOC: ~3
   - Complexity: Simple delegate

3. **`determine_metadata_mode()`** (Line ~446)
   - Current: Delegates to ApplicationService → MetadataManager
   - New: Will call MetadataController.determine_metadata_mode()
   - LOC: ~3
   - Complexity: Simple delegate (returns tuple)

4. **`should_use_extended_metadata()`** (Line ~450)
   - Current: Delegates to ApplicationService → MetadataManager
   - New: Will call MetadataController.should_use_extended_metadata()
   - LOC: ~3
   - Complexity: Simple delegate (returns bool)

#### Shortcut Methods (to keep in MainWindow, will use controller):

5. **`shortcut_load_metadata()`** (Line ~82)
   - Keep in MainWindow (UI shortcut handler)
   - Will call MetadataController instead of ApplicationService
   - LOC: ~2-3

6. **`shortcut_load_extended_metadata()`** (Line ~86)
   - Keep in MainWindow (UI shortcut handler)
   - Will call MetadataController
   - LOC: ~2-3

7. **`shortcut_save_selected_metadata()`** (Line ~90)
   - Keep in MainWindow (UI shortcut handler)
   - Will call MetadataController.export_metadata()
   - LOC: ~2-3

8. **`shortcut_save_all_metadata()`** (Line ~94)
   - Keep in MainWindow (UI shortcut handler)
   - Will call MetadataController.export_metadata()
   - LOC: ~2-3

#### Widget/UI Methods (keep in MainWindow, no migration):

9. **`refresh_metadata_widgets()`** (Line ~1176)
   - Pure UI: Updates metadata widget display
   - Keep in MainWindow
   - No controller involvement

10. **`update_active_metadata_widget_options()`** (Line ~1207)
    - Pure UI: Updates metadata widget options
    - Keep in MainWindow
    - No controller involvement

11. **`show_metadata_status()`** (Line ~531)
    - Pure UI: Shows metadata status in status bar
    - Keep in MainWindow
    - No controller involvement

12. **`on_metadata_value_edited(key_path, old_value, new_value)`** (Line ~550)
    - Metadata editing operation
    - Will use MetadataController for actual edit operation
    - Keep UI logic in MainWindow

13. **`on_metadata_value_reset(key_path)`** (Line ~573)
    - Metadata reset operation
    - Will use MetadataController for actual reset
    - Keep UI logic in MainWindow

14. **`on_metadata_value_copied(value)`** (Line ~591)
    - Pure UI: Clipboard operation
    - Keep in MainWindow
    - No controller involvement

15. **`get_common_metadata_fields()`** (Line ~362)
    - Query operation (returns list of common fields)
    - Will delegate to MetadataController.get_common_metadata_fields()
    - LOC: ~2-3

---

### 2. From ApplicationService (oncutf/core/application_service.py)

#### Methods to Remove (migrate to controller):

1. **`load_metadata_for_items(items, use_extended, source)`** (Line ~93)
   - Current: Delegates to UnifiedMetadataManager
   - Migration: Logic moves to MetadataController.load_metadata()
   - LOC: ~8
   - Complexity: Simple logging + delegation

2. **`load_metadata_fast()`** (Line ~138)
   - Current: Delegates to MetadataManager.shortcut_load_metadata()
   - Migration: Remove (MainWindow will call controller directly)
   - LOC: ~2

3. **`load_metadata_extended()`** (Line ~142)
   - Current: Delegates to MetadataManager.shortcut_load_extended_metadata()
   - Migration: Remove (MainWindow will call controller directly)
   - LOC: ~2

4. **`load_metadata_all_fast()`** (Line ~146)
   - Current: Delegates to MetadataManager.shortcut_load_metadata_all()
   - Migration: Remove (MainWindow will call controller directly)
   - LOC: ~2

5. **`load_metadata_all_extended()`** (Line ~150)
   - Current: Delegates to MetadataManager.shortcut_load_extended_metadata_all()
   - Migration: Remove (MainWindow will call controller directly)
   - LOC: ~2

6. **`determine_metadata_mode()`** (Line ~218)
   - Current: Delegates to MetadataManager.determine_metadata_mode()
   - Migration: Logic moves to MetadataController
   - LOC: ~4

7. **`should_use_extended_metadata()`** (Line ~224)
   - Current: Delegates to MetadataManager.should_use_extended_metadata()
   - Migration: Logic moves to MetadataController
   - LOC: ~4

8. **`restore_fileitem_metadata_from_cache()`** (Line ~244)
   - Current: Delegates to TableManager.restore_fileitem_metadata_from_cache()
   - Migration: Logic moves to MetadataController
   - LOC: ~2

---

## Lines of Code Estimate

### To Remove:
- **MainWindow:** ~12 lines (4 delegate methods)
- **ApplicationService:** ~26 lines (8 methods)
- **Total Removal:** ~38 lines

### To Add:
- **MetadataController:** ~450-500 lines
  - load_metadata() — ~80 lines
  - reload_metadata() — ~40 lines
  - restore_from_cache() — ~30 lines
  - determine_metadata_mode() — ~20 lines
  - should_use_extended_metadata() — ~20 lines
  - export_metadata() — ~60 lines
  - get_common_metadata_fields() — ~30 lines
  - State queries (is_loading, get_loaded_count, has_metadata) — ~40 lines
  - Helper methods — ~100 lines
  - Docstrings, imports, logging — ~120 lines

### Net Change:
- **Total:** +450-500 lines (controller), -38 lines (old code)
- **Net Impact:** ~+412-462 lines

---

## Key Dependencies

MetadataController will need access to:

1. **UnifiedMetadataManager**
   - load_metadata_for_items()
   - is_loading_metadata()
   - get_metadata_cache()

2. **StructuredMetadataManager**
   - get_structured_metadata()
   - get_common_fields()
   - get_metadata_for_item()

3. **MetadataOperationsManager**
   - edit_metadata_value()
   - reset_metadata_value()
   - export_metadata_to_file()

4. **TableManager**
   - restore_fileitem_metadata_from_cache()
   - get_all_file_items()

5. **ApplicationContext**
   - Access to file store
   - Access to settings
   - Access to modifier state

---

## Testing Strategy

### Unit Tests (No Qt):
- Test metadata loading with mock managers
- Test error handling for missing files
- Test cache restoration logic
- Test export format handling
- Test state queries

### Integration Tests (With Qt):
- Test full metadata loading workflow
- Test reload behavior
- Test keyboard shortcut integration
- Test UI updates after metadata load

### Existing Tests:
- **549 tests** currently passing
- All must remain green after Phase 1B

---

## Risk Assessment

### Low Risk:
- Simple delegate methods
- Well-defined interfaces
- No complex state management

### Medium Risk:
- Metadata loading has async behavior (progress dialogs)
- Cache restoration involves TableManager coordination
- Export functionality has multiple format options

### Mitigation:
- Feature flag for gradual rollout
- Parallel testing (old + new paths)
- Step-by-step commits with validation

---

## Phase 1B Steps

1. ✅ **Step 1B.1:** Create MetadataController skeleton
2. 🔄 **Step 1B.2:** Document methods (this file)
3. **Step 1B.3:** Implement orchestration logic
4. **Step 1B.4:** Wire to MainWindow with feature flag
5. **Step 1B.5:** Remove old code
6. **Step 1B.6:** Final cleanup

---

## Next Actions

- Review this document for completeness
- Proceed to Step 1B.3: Implement MetadataController methods
- Focus on: load_metadata(), reload_metadata(), restore_from_cache()
- Use %-formatting for all logger calls (PEP 282 compliant)

---

**End of Phase 1B Methods Map**
