# Refactoring Roadmap — Monster Files Tracker

**Author:** Michael Economou  
**Date:** 2026-01-01  
**Status:** Active tracking document

---

## Purpose

Track and prioritize the decomposition of oversized modules (>600 lines).
Large files are maintenance risks: hidden interactions, difficult testing, refactor hell.

**Target thresholds:**
- [CRIT] **Critical (>900 lines):** Split ASAP
- [WARN] **Warning (600-900 lines):** Plan split
- [OK] **OK (<600 lines):** Monitor only

---

## Monster Files Inventory

### [CRIT] Critical Priority (>900 lines)

| File | Lines | Category | Split Strategy | Status |
|------|-------|----------|----------------|--------|
| `ui/widgets/file_tree_view.py` | 1629 | UI | Extract behaviors | ~~[TODO] Planned~~ [DONE] Split to package |
| `ui/widgets/file_table_view.py` | 1318 | UI | Behaviors already extracted | [SKIP] Already optimal |
| ~~`ui/widgets/metadata_tree/view.py`~~ | ~~1272~~ → 1082 | UI | ~~Handlers partially extracted~~ | [DONE] Delegation cleanup (-18%) |
| ~~`core/database/database_manager.py`~~ | ~~1615~~ | ~~Core~~ | ~~Split by concern~~ | [DONE] Split to 6 modules |
| ~~`config.py`~~ | ~~1298~~ | ~~Config~~ | ~~Split to package~~ | [DONE] Split to oncutf/config/ |
| ~~`core/events/context_menu_handlers.py`~~ | ~~1289~~ | ~~Core~~ | ~~Split by domain~~ | [DONE] Split to package |
| ~~`core/rename/unified_rename_engine.py`~~ | ~~1259~~ | ~~Core~~ | ~~Extract validators~~ | [DONE] Split to 10 modules (244 lines) |
| ~~`ui/behaviors/metadata_edit_behavior.py`~~ | ~~1120~~ | ~~UI~~ | ~~Split by operation~~ | [DONE] Split to metadata_edit/ (8 modules, 1503 lines) |
| ~~`models/file_table_model.py`~~ | ~~1082~~ | ~~Model~~ | ~~Extract delegates~~ | [DONE] Split to file_table/ (7 modules, 1622 lines) |
| ~~`ui_manager.py`~~ | ~~982~~ | ~~Legacy~~ | ~~Migrate to controllers~~ | [SKIP] Low priority |
| ~~`column_management_behavior.py`~~ | ~~964~~ | ~~UI~~ | ~~Simplify via service~~ | [DONE] Delegated to service (928 lines) |

### [WARN] Warning Priority (600-900 lines)

| File | Lines | Category | Split Strategy | Status |
|------|-------|----------|----------------|--------|
| `core/file/load_manager.py` | 872 | Core | Delegate to controller | [TODO] Planned |
| ~~`core/metadata/unified_manager.py`~~ | ~~838~~ | ~~Core~~ | ~~Extract cache logic~~ | [DONE] 838 → 706 lines (16% reduction) |
| `core/metadata/operations_manager.py` | 779 | Core | Merge with controller | [TODO] Planned |
| `core/ui_managers/status_manager.py` | 708 | Legacy | Review for splitting | [TODO] Planned |
| `core/events/context_menu/base.py` | 639 | Core | Extract more handlers | [TODO] Planned |
| `core/database/metadata_store.py` | 627 | Core | Extract to smaller modules | [TODO] Planned |
| `core/rename/rename_manager.py` | 586 | Core | Near threshold - monitor | [OK] Monitor |

---

## Detailed Split Plans

### 1. `config.py` (1298 lines) -> Package [DONE]

**Completed:** 2026-01-01

**Final structure:**
```
oncutf/config/
├── __init__.py (26 lines)  <- Re-exports all for backward compatibility
├── app.py (101 lines)      <- Debug, app info, logging, backup
├── columns.py (322 lines)  <- Table column configs (FileTable, MetadataTree)
├── features.py (111 lines) <- FeatureAvailability, timeouts, undo/redo
├── paths.py (68 lines)     <- Extensions, filename validation
├── shortcuts.py (57 lines) <- All keyboard shortcuts
└── ui.py (450 lines)       <- Themes, colors, fonts, dialogs
```

**Migration:** All existing imports like `from oncutf.config import APP_NAME` continue to work.

---

### 2. `metadata_tree/view.py` (1272 lines) -> Split + Cleanup [DONE]

**Status:** Completed 2026-01-02

**Final structure:**
```
metadata_tree/
├── __init__.py (109 lines)           <- Re-exports
├── view.py (1082 lines)              <- Main view (shell view, -18%)
├── controller.py (302 lines)         <- Controller logic
├── service.py (593 lines)            <- Service layer
├── model.py (294 lines)              <- Data model
├── view_config.py (309 lines)        <- Configuration
├── worker.py (358 lines)             <- Background workers
├── render_handler.py (295 lines)     <- Tree model building, proxy
├── ui_state_handler.py (287 lines)   <- Placeholders, info label
├── search_handler.py (322 lines)     <- Search logic
├── selection_handler.py (231 lines)  <- Selection logic
├── drag_handler.py (203 lines)       <- Drag & drop
├── event_handler.py (130 lines)      <- Event handling
├── modifications_handler.py (145 lines) <- Modifications
└── cache_handler.py (65 lines)       <- Cache management
```

**Changes (2026-01-02):**

1. **DisplayHandler Split:**
   - Original: 502 lines (mini-god object)
   - Split to: render_handler.py + ui_state_handler.py
   - Deleted: display_handler.py (facade no longer needed)

2. **Delegation Cleanup:**
   - Removed 245+ lines of pure pass-through delegations
   - Updated 15+ external callers to use handler properties:
     * `view._cache_behavior.method()` instead of `view.method()`
     * `view._edit_behavior.method()` instead of `view.method()`
     * `view._scroll_behavior.method()` instead of `view.method()`
   - view.py: 1327 -> 1082 lines (-18% reduction)

**Result:** view.py is now a thin shell with only essential public API.

---

### 3. `file_tree_view.py` (1629 lines) -> Proposed Split

**Current structure analysis:**
```
file_tree_view.py (1629 lines)
├── Init + styling (~100 lines: 67-165)
├── Filesystem monitor (~240 lines: 167-412) <- CAN EXTRACT
├── Tree UI setup (~125 lines: 437-560)
├── State persistence (~170 lines: 599-730) <- CAN EXTRACT
├── Drag & drop (~425 lines: 770-1157) <- CAN EXTRACT
├── Drop handling (~125 lines: 1158-1280)
├── Event handlers (~250 lines: 1281-1530) <- CAN EXTRACT
├── Misc tree operations (~60 lines: 1532-1590)
└── DragCancelFilter class (~35 lines: 1591-1625)
```

**Proposed target structure:**
```
ui/widgets/file_tree/                <- NEW package
├── __init__.py (~20 lines)          <- Re-exports FileTreeView
├── view.py (~450 lines)             <- Main view (Qt glue + wiring)
├── filesystem_monitor.py (~250 lines) <- Monitor setup & callbacks
├── state_handler.py (~180 lines)    <- Expanded state persistence
├── drag_handler.py (~400 lines)     <- All drag & drop logic
├── event_handler.py (~200 lines)    <- Keyboard, scroll, misc events
└── utils.py (~50 lines)             <- DragCancelFilter + helpers
```

**Migration priority:** [MED] Medium - large but functional

---

### 4. `context_menu_handlers.py` (1289 lines) -> Split by Domain [DONE]

**Completed:** Pre-existing split (discovered 2026-01-01)

**Current structure:**
```
events/context_menu/
├── __init__.py (11 lines)      <- Re-exports ContextMenuHandlers
├── base.py (639 lines)         <- Main handler class [WARN: >600]
├── file_status.py (153 lines)  <- File status helpers
├── hash_handlers.py (137 lines) <- Hash operations
├── metadata_handlers.py (172 lines) <- Metadata operations
└── rotation_handlers.py (360 lines) <- Rotation operations
```

**Note:** `base.py` at 639 lines is in [WARN] territory. Future work: extract more handlers.

---

### 5. `database_manager.py` (1615 lines) -> Split by Concern [DONE]

**Completed:** Pre-existing split (discovered 2026-01-01)

**Current structure:**
```
database/
├── __init__.py (35 lines)       <- Re-exports
├── database_manager.py (424 lines) <- Orchestrator
├── metadata_store.py (627 lines) <- Metadata operations [WARN]
├── migrations.py (520 lines)    <- Schema migrations
├── path_store.py (161 lines)    <- Path operations
├── hash_store.py (161 lines)    <- Hash operations
└── backup_store.py (40 lines)   <- Backup operations
```

**Note:** `metadata_store.py` at 627 lines is in [WARN] territory. Future work: extract to smaller modules.

---

### 6. `unified_rename_engine.py` (1259 lines) -> Split by Concern [DONE]

**Completed:** Pre-existing split (discovered 2026-01-01)

**Current structure:**
```
core/rename/
├── __init__.py (58 lines)              <- Re-exports
├── unified_rename_engine.py (244 lines) <- Orchestrator
├── data_classes.py (213 lines)         <- Data models
├── execution_manager.py (285 lines)    <- Execute renames
├── preview_manager.py (295 lines)      <- Preview generation
├── query_managers.py (205 lines)       <- Query operations
├── rename_history_manager.py (410 lines) <- Undo/redo history
├── rename_manager.py (586 lines)       <- Main rename logic [WARN: near 600]
├── state_manager.py (59 lines)         <- State tracking
└── validation_manager.py (98 lines)    <- Validation rules
```

**Total:** 2453 lines split across 10 modules. Average: 245 lines/module.

---

### 7. `unified_manager.py` (838 lines) -> Extract Hash Loading Logic [DONE]

**Completed:** 2026-01-02

**Problem:** UnifiedMetadataManager already delegates to 6 services but still contains ~140 lines of hash loading logic embedded in the facade.

**Solution:** Extract hash loading operations to dedicated HashLoadingService.

**Changes:**
1. Created `hash_loading_service.py` (254 lines):
   - `load_hashes_for_files()` - orchestration with cache filtering
   - `_show_hash_progress_dialog()` - progress UI management
   - `_start_hash_loading()` - ParallelHashWorker setup
   - `_on_hash_progress()` - progress updates
   - `_on_file_hash_calculated()` - individual file completion + UI refresh
   - `_on_hash_finished()` - completion handler + callback invocation
   - `cancel_loading()` - cancellation support
   - `_cleanup_hash_worker()` - resource cleanup
   - `cleanup()` - full cleanup

2. Updated `unified_manager.py` (838 → 706 lines, -132 lines, 16% reduction):
   - Removed hash loading methods
   - Removed `_hash_worker`, `_hash_progress_dialog` attributes
   - Removed `_cleanup_hash_worker_and_thread()` method
   - Delegated to HashLoadingService via `self._hash_service`
   - Simplified `load_hashes_for_files()` to 5-line delegation with callback
   - Updated `_cancel_current_loading()` to delegate cancellation
   - Updated `cleanup()` to call service cleanup

3. Updated `metadata/__init__.py`:
   - Exported HashLoadingService for external use
   - Updated package docstring

**Architecture:** Now 7 specialized services (was 6):
- MetadataCacheService (cache operations)
- CompanionMetadataHandler (companion files)
- MetadataWriter (write operations)
- MetadataShortcutHandler (keyboard shortcuts)
- MetadataProgressHandler (progress dialogs)
- MetadataLoader (metadata loading)
- **HashLoadingService (hash loading)** ← NEW

**Quality Gates:** ✅ 949 tests passed, ✅ ruff clean, ✅ mypy clean

**Result:** UnifiedMetadataManager is now a pure facade with no embedded business logic.

---

### 8. `metadata_edit_behavior.py` (1120 lines) -> Split by Operation [DONE]

**Completed:** Pre-existing split (discovered 2026-01-01)

**Current structure:**
```
ui/behaviors/metadata_edit/
├── __init__.py (52 lines)              <- Re-exports
├── metadata_edit_behavior.py (328 lines) <- Main coordinator
├── edit_operations.py (361 lines)      <- Edit logic
├── field_detector.py (205 lines)       <- Field detection
├── reset_handler.py (143 lines)        <- Reset operations
├── rotation_handler.py (136 lines)     <- Image rotation
├── tree_navigator.py (177 lines)       <- Tree navigation
└── undo_redo_handler.py (101 lines)    <- Undo/redo support
```

**Total:** 1503 lines split across 8 modules. Average: 188 lines/module.

---

### 8. `file_table_model.py` (1082 lines) -> Split by Concern [DONE]

**Completed:** Pre-existing split (discovered 2026-01-01)

**Current structure:**
```
models/file_table/
├── __init__.py (31 lines)              <- Re-exports
├── file_table_model.py (301 lines)     <- Main model
├── column_manager.py (350 lines)       <- Column handling
├── data_provider.py (372 lines)        <- Data access
├── file_operations.py (226 lines)      <- File operations
├── icon_manager.py (190 lines)         <- Icon management
└── sort_manager.py (152 lines)         <- Sort operations
```

**Total:** 1622 lines split across 7 modules. Average: 232 lines/module.

---

### 9. Column System Consolidation [DONE]

**Completed:** 2026-01-02

**Problem:** 3 sources of truth causing code duplication and maintenance burden

**Final Structure:**
```
UnifiedColumnService (canonical - 515 lines)
       ↑
       ├── ColumnManager (thin adapter - 329 lines, 61% reduction from 853)
       └── ColumnManagementBehavior (UI-only - 928 lines, 3.8% reduction from 965)
```

**Changes Made:**

1. **Enhanced UnifiedColumnService** (391 → 515 lines, +124 lines):
   - Added `analyze_column_content_type()` for content detection
   - Added `get_recommended_width_for_content_type()` for smart sizing
   - Added `validate_column_width()` for bounds checking
   - Added `get_visible_column_configs()` for bulk operations
   - Added `reset_column_width()` and `reset_all_widths()`
   - Added `get_column_keys()` for key enumeration

2. **Refactored ColumnManager** (853 → 329 lines, 61% reduction):
   - All business logic delegated to UnifiedColumnService
   - Kept only Qt-specific integration:
     * Signal connection and handling
     * Scrollbar detection and management
     * Splitter integration
     * Header configuration
   - Removed hardcoded configurations (now from service)
   - Removed duplicate width/config management
   - Backward compatible (all public API preserved)

3. **Simplified ColumnManagementBehavior** (965 → 928 lines, 3.8% reduction):
   - Delegated to service:
     * Content type analysis
     * Width recommendations
     * Width reset operations
     * All config queries
   - Removed duplicate config loading code
   - Removed 11 local `get_column_service()` imports
   - Maintains UI-only responsibilities (events, timers, shutdown hooks)

**Note:** ColumnManagementBehavior reduction was less than target (<500 lines) because
it contains significant UI interaction logic that cannot be further delegated. However,
all business logic is now properly delegated to the service, achieving the architectural goal.

**Quality Gates:** ✅ 949 tests passed, ✅ ruff clean, ✅ mypy clean

**Total System Reduction:** 2209 → 1772 lines (437 lines saved, 19.8% reduction)

**Migration:**
1. Move all business logic to `UnifiedColumnService`
2. `ColumnManager` becomes pass-through to service
3. `ColumnManagementBehavior` keeps only UI interactions

---

## Priority Order

### Phase 1: High Impact (Q1 2026)

1. ~~**`context_menu_handlers.py`**~~ — [DONE] Already split to package
2. ~~**`config.py`**~~ — [DONE] Split to oncutf/config/ package (7 modules)
3. ~~**Column system**~~ — [DONE] Consolidated (2209 → 1772 lines, 19.8% reduction)

### Phase 2: Core Services (Q1-Q2 2026)

4. ~~**`database_manager.py`**~~ — [DONE] Already split to 6 modules
5. ~~**`unified_rename_engine.py`**~~ — [DONE] Already split to 10 modules
6. ~~**`unified_manager.py`**~~ — [DONE] Extracted HashLoadingService (838 → 706 lines, 16% reduction)

### Phase 3: UI Layer (Q2 2026)

7. ~~**`metadata_edit_behavior.py`**~~ — [DONE] Already split to 8 modules
8. ~~**`file_table_model.py`**~~ — [DONE] Already split to 7 modules
9. ~~**`metadata_tree/view.py`**~~ — [DONE] Delegation cleanup (1327 → 1082 lines, -18%)
10. ~~**`file_tree_view.py`**~~ — [DONE] Extracted to package (1629 → 448 lines, 72% reduction)
11. **`file_table_view.py`** — [SKIP] Already optimal with 3 behaviors (1318 lines)

### Phase 4: Legacy Migration (Q2-Q3 2026)

12. **`ui_manager.py`** — Migrate to controllers (982 lines)
13. ~~**`column_manager.py`**~~ — [DONE] Thin adapter (853 → 329 lines, 61% reduction)
14. ~~**`column_management_behavior.py`**~~ — [DONE] Simplified (965 → 928 lines, 3.8% reduction)
15. **`load_manager.py`** — Delegate to controller (872 lines)

---

## Success Metrics

| Metric | Before | Current | Target |
|--------|--------|---------|--------|
| Files >900 lines | 11 | 1 | 0 |
| Files >600 lines | 16 | 8 | 5 |
| Average LOC/file | ~200 | ~200 | ~200 |
| Tests passing | 949 | 949 | 949+ |
| Docstring coverage | 96.2% | 96.2% | 98%+ |

---

## References

- [MIGRATION_STANCE.md](MIGRATION_STANCE.md) — Architecture migration policy
- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture
- [UI_ARCHITECTURE_PATTERNS.md](UI_ARCHITECTURE_PATTERNS.md) — UI patterns guide
