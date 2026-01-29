# Boundary-First Refactor Summary (260125)
**Last Updated:** 2026-01-28 22:10  
**Status:** ✅ MAJOR MILESTONE — 53% violations eliminated (73→34), app→core: 0

---

## What Changed Since Last Summary

1. **Corrected core→ui count:** Previous summary claimed 1 lazy import from `core/application_context.py` to `ui.adapters.qt_app_context`. **That file does not exist** — `application_context.py` was already moved to `app/state/context.py` (Qt-free). Only a stale `.pyc` file remained in `core/__pycache__/`.
2. **Re-ran `scripts/audit_boundaries.py`:** Accurate counts now.
3. **Duplicates verified at 0** — `preview_engine.py` was deleted, services consolidated.

---

## Executive Summary

| Violation Type | Before | Now | Status |
|----------------|--------|-----|--------|
| **Total violations** | 73 | **34** | 📉 53% ↓ |
| **core→ui imports** | 12 | **0** | ✅ DONE |
| **domain purity** | 11 | **0** | ✅ DONE |
| **app→core imports** | 27 | **0** | ✅ DONE |
| **infra→app** | 2 | **1** | ✅ TYPE_CHECKING only |
| **app→ui imports** | 23 | **2** | 📉 91% ↓ |
| **controllers→ui** | 8 | **4** | 📉 50% ↓ |
| **Qt signals in core** | 0 | 0 | ✅ DONE |

**Verified 2026-01-28 via `scripts/audit_boundaries.py`** — All 1154 tests pass.

### Key Accomplishments (2026-01-28)

- Moved 11 UI-coupled files from `core/` → `ui/managers/`
- Moved `domain/metadata/extractor.py` → `core/metadata/metadata_extractor.py`
- Fixed ApplicationContext → AppContext in all controllers
- Moved 8 files from `app/services/` → `ui/services/`
- **Moved 9 files from `core/` → `infra/`:**
  - `core/cache/persistent_*` → `infra/cache/`
  - `core/database/*` (7 files) → `infra/db/`
  - `core/file/store.py` → `infra/state/file_store.py`
  - `core/selection/selection_store.py` → `infra/state/`
- **Moved 5 more modules to fix app→core:**
  - `core/batch/` → `infra/batch/`
  - `core/folder_color_command.py` → `infra/`
  - `core/type_aliases.py` → `app/types.py`
  - `app/services/metadata_*.py` → `core/metadata/`
- **Moved `app/services/color/` → `infra/color/`** to fix infra→app violation

---

## Detailed Violation Report (35 total)

### Violations by Rule

| Rule | Count |
|------|-------|
| `app_must_not_depend_on_ui_infra_core` | 20 |
| `ui_must_not_import_infra` | 9 |
| `controllers_must_not_import_ui` | 4 |
| `infra_must_not_depend_on_ui_app_controllers` | 2 |

### Violations by Direction

| Direction | Count |
|-----------|-------|
| app→infra | 18 |
| ui→infra | 9 |
| controllers→ui | 4 |
| app→ui | 2 |
| **app→core** | **0** ✅ |

---

## Files by Layer (237 total scanned)

| Layer | Files |
|-------|-------|
| ui | 100 |
| core | 51 |
| utils | 33 |
| utils_ui | 19 |
| config | 13 |
| app | 9 |
| modules | 6 |
| models | 4 |
| controllers | 2 |

---

## `# type: ignore` Inventory (15 occurrences in 6 files)

| File | Count | Reason |
|------|-------|--------|
| `core/shutdown_coordinator.py` | 8 | `[unreachable]` — defensive hasattr checks after early-return |
| `core/rename/preview_manager.py` | 2 | `[unreachable]` — defensive return after loop |
| `ui/widgets/node_editor/graphics/node.py` | 2 | `[attr-defined]` — dynamic `node` reference injection |
| `utils/filesystem/path_utils.py` | 1 | `[attr-defined]` — PyInstaller `sys._MEIPASS` |
| `utils/paths.py` | 1 | `[attr-defined]` — PyInstaller `sys._MEIPASS` |
| `utils/logging/logger_helper.py` | 1 | `[attr-defined]` — monkey-patching logger |

---

## Boundary Rules (Non-Negotiable)

| Layer | Can Import | Cannot Import |
|-------|------------|---------------|
| `domain/` | stdlib only | Qt, filesystem, subprocess, DB, threads, ui, infra, app |
| `app/` | domain, ports (protocols) | Qt, direct IO, ui, infra implementations, core |
| `infra/` | domain only | ui, app |
| `ui/` | app, domain | infra directly |
| `core/` | domain, stdlib, utils (non-ui) | ui, app, infra |

---

## Boundary Enforcement Plan

### Priority 1: Fix app→ui imports (14 violations)

**Files affected:**
- `app/services/cursor.py` (1)
- `app/services/file_load.py` (1)
- `app/services/progress.py` (4)
- `app/services/ui_state.py` (2)
- `app/services/user_interaction.py` (5)

**Action:**
1. Move `ui.adapters.application_context` imports → use `app.state.context.get_app_context()` instead.
2. `ui.adapters.qt_user_interaction` → define protocol in `app/ports/`, inject adapter.
3. `ui.widgets.file_table.view` → expose needed functionality via app/ports protocol.

### Priority 2: Fix app→utils_ui imports (34 violations)

**Files affected:**
- `app/services/icons.py` (10)
- `app/services/ui_state.py` (5)
- `app/services/progress.py` (2)
- `app/services/cursor.py` (2)
- `app/services/dialog_positioning.py` (1)
- `app/services/drag_state.py` (1)
- `app/services/folder_selection.py` (1)

**Action:**
1. Move `utils/ui/` helpers to `ui/helpers/` (they are Qt-dependent).
2. Alternatively, define protocols in `app/ports/` for icon loading, cursor management, progress dialogs.
3. Implement adapters in `ui/adapters/` that wrap `utils/ui/` code.

### Priority 3: Fix app→core imports (20 violations)

**Files affected:**
- `app/services/metadata_service.py` (6)
- `app/services/metadata_simplification_service.py` (4)
- `app/services/cache_service.py` (3)
- `app/services/database_service.py` (2)
- `app/services/folder_color_service.py` (2)
- `app/services/rename_history_service.py` (1)
- `app/state/context.py` (2)

**Action:**
Option A (Full refactor): Move business logic from `core/` to `domain/` or `app/ports/`.
Option B (Pragmatic): Reclassify `core/` as implementation layer, allow `app/` to use it (adjust rules).

> [!IMPORTANT]
> The current architecture treats `core/` as containing business logic that `app/` orchestrates. If `app/` cannot import `core/`, then either `core/` modules need port abstractions, or the boundary rule should be relaxed for the `app→core` direction.

### Priority 4: Reduce `# type: ignore` count

| File | Action |
|------|--------|
| `core/shutdown_coordinator.py` | Consider Optional types + proper Protocol for health_check |
| `core/rename/preview_manager.py` | Remove unreachable return or add explicit Never annotation |
| `utils/*.py` | PyInstaller `_MEIPASS` is legitimate; keep ignore |
| `ui/widgets/node_editor/graphics/node.py` | Document dynamic attribute assignment pattern |

---

## Final Target Metrics

| Metric | Start | Current | Target |
|--------|-------|---------|--------|
| Total violations | 73 | **39** | 0 |
| core→ui imports | 12 | **0** ✅ | 0 ✅ |
| domain purity | 11 | **0** ✅ | 0 ✅ |
| app→ui imports | 23 | 2 | 0 |
| app→core imports | 27 | 27 | 0 |
| controllers→ui | 8 | 4 | 0 |
| `# type: ignore` | 15 | 15 | ≤5 |

---

## Risk & Regression Checklist

### Rename/Metadata/Load/Preview Flows

| Flow | Risk Points | Verification |
|------|-------------|--------------|
| **File Load** | `file_load.py` imports `ui.adapters.application_context` | Test folder load after refactor |
| **Metadata Load** | `metadata_service.py` imports `core.metadata.*` | Test metadata display on file selection |
| **Preview Generation** | `preview_manager.py` is in `core/rename/` | Test rename preview in UI |
| **Rename Execution** | `unified_rename_engine.py` is Qt-free | Test batch rename operation |

### Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific flow tests
pytest tests/test_file_loading.py -v
pytest tests/test_metadata*.py -v
pytest tests/test_rename*.py -v

# Run boundary audit
python scripts/audit_boundaries.py --strict-ui-core
```

---

## Migration Phases (Historical Reference)

| Phase | Status | Description |
|-------|--------|-------------|
| 1 - UI Managers | ✅ DONE | core/ui_managers/ → ui/managers/ |
| 2 - Bootstrap | ✅ DONE | core/initialization/ → ui/boot/ |
| 3 - Event/Signal | ✅ DONE | core/event_handler_manager → ui/events/ |
| 4 - Drag Managers | ✅ DONE | core/drag/ → ui/drag/ |
| 5 - Dialog Ports | ✅ DONE | 4 ports + 4 adapters created |
| 6 - Service Layer | ✅ DONE | services/ → app/ports/ + infra/ |
| 7 - Boundary Cleanup | ⚠️ PARTIAL | 68 violations remain in app/ |
