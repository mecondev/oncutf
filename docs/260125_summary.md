# Boundary-First Refactor Summary (260125)
**Last Updated:** 2026-01-26  
**Status:** PARTIAL — Phase 6 mostly done; boundary cleanup still incomplete

---

## Executive Summary

**Migration Progress (Phases 1-5):** ✅ (file moves done)
- Most UI-coupled modules moved from core/ to ui/
- Port-adapter pattern added for dialogs/progress/cursor
- ApplicationContext split: Qt-free base + Qt wrapper
- File relocation executed; boundary enforcement still pending

**Boundary Enforcement:** ❌ INCOMPLETE
- core → ui: **1 lazy import** remains (no top-level imports)
- ui → core: **63 imports** remain (0 problematic top-level business logic; mostly lazy/config)
- Qt signals in core: **removed** (UnifiedRenameEngine is Qt-free)
- Duplicates not fully removed: `utils/naming/preview_engine.py` still exists

**Critical Gap:** The migration focused on file relocation, not true boundary enforcement.

---

## ACTUAL Violation Counts (2026-01-26)

| Violation Type | Current Count | Files | Status |
|----------------|---------------|-------|--------|
| **core → ui imports** | **1 (lazy)** | 1 file | ⚠️ OPEN |
| **ui → core imports** | **63** | many | ⚠️ OPEN (mostly lazy/config) |
| Qt signals in core | 0 | — | ✅ DONE |
| Duplicate rename paths | 1 file | preview_engine.py | ⚠️ OPEN |
| `# type: ignore` | 13 | Various | ⚠️ OPEN |

### Core → UI Imports (AST: 1 lazy import)

**OPEN:**
1. `core/application_context.py` (lazy): imports Qt wrapper at runtime
   - `from oncutf.ui.adapters.qt_app_context import QtAppContext`

**DONE:**
- `core/file/load_manager.py`: ui.drag imports removed
- `core/metadata/operations_manager.py`: StyledComboBox removed
- `core/rename/unified_rename_engine.py`: Qt signals removed

### UI → Core Imports (AST: 63 occurrences, 0 top-level business logic)

**Complete File List:**

**Behaviors (3 files):**
- `oncutf/ui/behaviors/column_management/column_behavior.py`
- `oncutf/ui/behaviors/metadata_edit/edit_operations.py`
- `oncutf/ui/behaviors/selection/selection_behavior.py`

**Boot/Bootstrap (2 files):**
- `oncutf/ui/boot/bootstrap_manager.py`
- `oncutf/ui/boot/bootstrap_orchestrator.py`

**Events (3 files):**
- `oncutf/ui/events/context_menu/base.py`
- `oncutf/ui/events/event_coordinator.py`
- `oncutf/ui/events/signal_coordinator.py`

**Handlers (1 file):**
- `oncutf/ui/handlers/shutdown_lifecycle_handler.py`

**Main Window (1 file):**
- `oncutf/ui/main_window.py`

**Managers (5 files):**
- `oncutf/ui/managers/column_service.py`
- `oncutf/ui/managers/file_load_ui_service.py`
- `oncutf/ui/managers/shortcut_manager.py`
- `oncutf/ui/managers/splitter_manager.py`
- `oncutf/ui/managers/window_config_manager.py`

**Widgets (14 files):**
- `oncutf/ui/widgets/file_table/viewport_handler.py`
- `oncutf/ui/widgets/file_tree/drag_handler.py`
- `oncutf/ui/widgets/file_tree/filesystem_handler.py`
- `oncutf/ui/widgets/final_transform_container.py`
- `oncutf/ui/widgets/interactive_header.py`
- `oncutf/ui/widgets/metadata_tree/controller.py`
- `oncutf/ui/widgets/metadata_tree/selection_handler.py`
- `oncutf/ui/widgets/metadata_tree/service.py`
- `oncutf/ui/widgets/metadata_tree/view.py`
- `oncutf/ui/widgets/metadata_widget.py`
- `oncutf/ui/widgets/realtime_validation_widget.py`
- `oncutf/ui/widgets/rename_module_widget.py`
- `oncutf/ui/widgets/rename_modules_area.py`
- `oncutf/ui/widgets/thumbnail_viewport.py`

**Most common import patterns:**
- `core.application_context` → multiple files (dependency injection needed)
- Core managers → multiple files (use controllers instead)
- Core drag helpers → some files (use adapters)

---

## Migration Phases: Completed ✅

**Phase 1: UI Managers (DONE)**
- Moved: core/ui_managers/ → ui/managers/
- Impact: 13 files updated
- Commits: 37a5a216, 8b4d4fed, 3565b762, bb948b33, 1da83558

**Phase 2: Bootstrap (DONE)**
- Moved: core/initialization/ → ui/boot/
- Impact: 2 entry points updated
- Commit: eb2bff24, 3f08c83a, b3b34830

**Phase 3: Event/Signal Coordination (DONE)**
- Moved: core/event_handler_manager, signal_coordinator → ui/events/
- Impact: 8 files updated
- Commit: c3bd2c2b, d73fafd4

**Phase 4: Drag Managers (DONE)**
- Moved: core/drag/ → ui/drag/
- Impact: 9 files updated
- Commit: efc8994c, 6340b254

**Phase 5: Specialized Dialog Ports (DONE)**
- Created 4 ports + 4 adapters
- Updated 4 core files with dependency injection
- Commit: 00c19f10

**Result:** File relocation successful, but boundary violations persist.

---

## Boundary Rules (Non-Negotiable)

| Layer | Can Import | Cannot Import |
|-------|------------|---------------|
| `domain/` | stdlib only | Qt, filesystem, subprocess, DB, threads, ui, infra, app |
| `app/` | domain, ports (protocols) | Qt, direct IO, ui, infra implementations |
| `infra/` | domain only | ui, app |
| `ui/` | app, domain | infra |

---


## What Remains to Complete Boundary Enforcement

### Phase 6: Final Boundary Cleanup (PARTIAL)

**6.1. Eliminate Core → UI Imports ⚠️ OPEN**

**Status:** 1 lazy import remains (must be reduced to zero).

1. **application_context.py Qt wrapper** (1 lazy import)
   - Remove runtime UI adapter import from core; keep Qt wrapper in `ui/adapters/` only.

**DONE:**
- `core/file/load_manager.py`: ui.drag imports removed
- `core/metadata/operations_manager.py`: StyledComboBox removed

---

**6.2. Remove Qt from Core ✅ COMPLETE**

**Status:** Qt dependencies eliminated from `core/rename/`.
- `unified_rename_engine.py` no longer imports QObject/pyqtSignal.
- Qt signals live in `ui/adapters/qt_rename_engine.py`.

---

**6.3. Reduce UI → Core Imports ⚠️ PARTIAL**

**Status:** AST shows **63 ui→core imports**, **0 top-level business logic**. Most are lazy/config/types/adapters.

Open work:
- Reduce remaining lazy imports by routing through app services or UI-only helpers.
- Replace remaining `core.application_context` references with `app/state/context` + UI adapters.

---

**Final Phase 6 Summary (Updated):**

| Phase | Status | Notes |
|-------|--------|-------|
| 6.1 - Eliminate core→ui | ⚠️ OPEN | 1 lazy import remains (application_context) |
| 6.2 - Remove Qt from core | ✅ DONE | UnifiedRenameEngine Qt-free |
| 6.3 - Reduce ui→core | ⚠️ PARTIAL | 63 imports remain, 0 top-level business logic |

**Current Metrics (Verified):**
- core → ui: **1 lazy import** (application_context)
- ui → core: **63 imports**, 0 top-level business logic
- Qt signals in core/rename: **0**
- Duplicates: **1** (`utils/naming/preview_engine.py`)
- `# type: ignore`: **13**

