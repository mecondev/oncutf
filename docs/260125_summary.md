στη διάσπαση του ApplicationContext# Boundary-First Refactor Summary (260125)
**Last Updated:** 2026-01-25  
**Status:** PARTIAL — boundaries not yet enforced; core<->ui violations remain.

---

## Executive Summary

- Goal: boundary-first cleanup with strict import rules, not "split-first," so cycles are removed without behavior changes.
- Single sources of truth for rename preview/execute, exiftool invocation, and caching, with an explicit deprecation plan.
- Domain/app become Qt-free and typed-first; UI keeps Qt signals only in UI/adapter layers.
- Next steps focus on breaking remaining cycles and removing legacy duplicates before deeper typing work.

---

## Remaining Violations (Actual Counts)

| Violation Type | Before QW-1 | After QW-1 | After QW-2 | Status |
|----------------|-------------|------------|------------|--------|
| core -> ui imports | 39 | 39 | 39 | OPEN |
| ui -> core imports | 159 | 79 (-50%) | **43** (-73% total) | **IMPROVED** |
| `# type: ignore` | 13 | 13 | 13 | OPEN |
| Duplicate rename paths | 4+ files | 4+ files | 4+ files | OPEN |
| Duplicate ExifTool paths | 3+ files | 3+ files | 3+ files | OPEN |

**Phase Status:**
- Phase A (Domain isolation): IN PROGRESS
- Phase B (App layer cleanup): IN PROGRESS
- Phase C (UI adapter creation): NOT STARTED
- Phase D (Duplicate removal): NOT STARTED

**Recent Progress (2026-01-25):**
- ✅ QW-1 completed: Removed all `oncutf.core.pyqt_imports` from UI layer (80+ files)
- ✅ QW-2 completed: Moved `theme_manager.py` from core to ui (58 imports updated)
- ✅ ApplicationContext split: Created Qt-free AppContext + Qt wrapper QtAppContext
- ✅ QW-3 completed: Removed UI re-exports from `core/events/__init__.py`
- ✅ QW-4 completed: Removed UI fallbacks from `app/services/user_interaction.py`
- 📉 ui → core imports reduced by 73% total (159 → 79 → 43)
- 📉 app → ui violations reduced by 8 (from user_interaction.py)
- 🔄 Backward compatibility maintained via deprecated wrapper

---

## Boundary Rules (Non-Negotiable)

| Layer | Can Import | Cannot Import |
|-------|------------|---------------|
| `domain/` | stdlib only | Qt, filesystem, subprocess, DB, threads, ui, infra, app |
| `app/` | domain, ports (protocols) | Qt, direct IO, ui, infra implementations |
| `infra/` | domain only | ui, app |
| `ui/` | app, domain | infra |

---

## Detailed Fix Plan (Boundary-First)

### 1. Break core -> ui Imports (39 occurrences)

**Problem:** Core modules import UI components (dialogs, progress, cursor helpers).

**Affected files:**
- `oncutf/core/metadata/*` - imports UI dialogs
- `oncutf/core/operations_manager.py` - imports CustomMessageDialog
- `oncutf/core/hash/*` - imports UI progress indicators

**Solution:**
```
Before: core/operations_manager.py -> ui/widgets/custom_message_dialog.py
After:  core/operations_manager.py -> app/ports/user_interaction.py
        ui/adapters/qt_user_interaction.py implements the port
```

**Steps:**
1. Create `oncutf/app/ports/user_interaction.py` (protocol)
2. Create `oncutf/ui/adapters/qt_user_interaction.py` (implementation)
3. Replace direct UI imports in core with port usage
4. Register adapter at bootstrap (ui/boot/)

### 2. Break ui -> core Imports (159 occurrences)

**Problem:** UI modules import core helpers that belong in UI layer.

**Most common violations:**
- `oncutf/core/pyqt_imports.py` - used 50+ times in UI
- `oncutf/core/theme_manager.py` - used 30+ times in UI
- `oncutf/core/rename/unified_rename_engine.py` - Qt signals in core

**Solution:**

| Current Location | Target Location |
|-----------------|-----------------|
| `core/pyqt_imports.py` | DELETE - use direct PyQt5 imports or `ui/qt_imports.py` |
| `core/theme_manager.py` | `ui/theme_manager.py` |
| `core/application_context.py` | Split: `app/state/context.py` + `ui/adapters/qt_context.py` |

**Steps:**
1. Replace all `from oncutf.core.pyqt_imports import ...` with direct PyQt5 imports
2. Move `theme_manager.py` to `oncutf/ui/theme_manager.py`
3. Update all import paths
4. Delete `oncutf/core/pyqt_imports.py`

### 3. App Services: Remove UI Fallbacks

**Problem:** `app/services/user_interaction.py` has fallback imports to UI.

**Current (broken):**
```python
# app/services/user_interaction.py
try:
    from oncutf.ui.widgets import CustomMessageDialog  # VIOLATION
except ImportError:
    pass
```

**Solution:**
```python
# app/ports/user_interaction.py
class UserInteractionPort(Protocol):
    def show_error(self, title: str, message: str) -> None: ...
    def show_confirmation(self, title: str, message: str) -> bool: ...

# ui/adapters/qt_user_interaction.py
class QtUserInteraction(UserInteractionPort):
    def show_error(self, title: str, message: str) -> None:
        CustomMessageDialog.error(title, message)
```

### 4. UnifiedRenameEngine: Extract Qt Signals

**Problem:** `unified_rename_engine.py` uses QObject/pyqtSignal in core layer.

**Solution:**
```
oncutf/core/rename/unified_rename_engine.py  (keep logic, remove Qt)
    |
    v
oncutf/app/use_cases/rename_engine.py  (Qt-free orchestration)
    |
    v
oncutf/ui/adapters/qt_rename_engine.py  (Qt wrapper with signals)
```

**Steps:**
1. Create `oncutf/app/use_cases/rename_engine.py` - pure Python, no Qt
2. Create `oncutf/ui/adapters/qt_rename_engine.py` - wraps engine, emits signals
3. Update UI to use Qt wrapper
4. Deprecate `oncutf/core/rename/unified_rename_engine.py`

### 5. ApplicationContext: Split Qt from State

**Problem:** `application_context.py` is QObject used by app services.

**Solution:**
```
oncutf/core/application_context.py (current - mixed)
    |
    v  SPLIT INTO:
    |
    +-> oncutf/app/state/context.py (Qt-free state container)
    |
    +-> oncutf/ui/adapters/qt_context.py (Qt signals/slots wrapper)
```

### 6. Initialization: Move Bootstrap to UI

**Problem:** `oncutf/core/initialization/*` imports UI components.

**Solution:**
- Move to `oncutf/ui/boot/` or `oncutf/ui/composition/`
- Keep only protocol registration in app layer

---

## De-duplication Plan (Single Source of Truth)

### Rename Pipeline

| Role | Canonical Path | Remove/Deprecate |
|------|----------------|------------------|
| Preview | `oncutf/domain/rename/preview.py` | `core/preview_manager.py`, `utils/naming/preview_engine.py`, `utils/naming/preview_generator.py` |
| Execute | `oncutf/app/use_cases/rename_execute.py` | `utils/naming/renamer.py`, legacy paths in `core/rename/*` |
| Validation | `oncutf/domain/rename/validation.py` | Scattered validation logic |

### ExifTool Pipeline

| Role | Canonical Path | Remove/Deprecate |
|------|----------------|------------------|
| Client | `oncutf/infra/external/exiftool_client.py` | - |
| Cache | `oncutf/infra/cache/metadata_cache.py` | - |
| Remove | - | `utils/metadata/exiftool_adapter.py`, `services/exiftool_service.py`, `utils/shared/exiftool_wrapper.py` |

---

## Quick Wins (Immediate Actions)

### ✅ QW-1: Replace pyqt_imports in UI (COMPLETED - 2026-01-25)

**Status:** DONE — All 80+ usages replaced with direct PyQt5 imports

**Changes made:**
- Replaced all `from oncutf.core.pyqt_imports import ...` with direct PyQt5 imports
- Split imports by module (QtCore, QtGui, QtWidgets) for clarity
- Updated both top-level and inline imports
- Fixed import sorting issues with `ruff check --fix`

**Files affected:** 80+ files in `oncutf/ui/` directory
- widgets/: 30+ files
- dialogs/: 10+ files
- behaviors/: 15+ files
- delegates/: 5+ files
- main_window.py and others

**Quality gates passed:**
- ✅ ruff check: 56 auto-fixes applied, 3 minor warnings (type-checking imports)
- ✅ mypy: Success (0 errors in 549 files)
- ✅ No import from oncutf.core.pyqt_imports in oncutf/ui/

**Impact:**
- Reduces ui -> core imports by ~80 occurrences
- Makes UI layer more independent
- Prepares for core/pyqt_imports.py deletion

**Next:** QW-2 (Move theme_manager to UI)

---

### ✅ QW-2: Move theme_manager to UI (COMPLETED - 2026-01-25)

**Status:** DONE — theme_manager.py migrated from core to ui

**Changes made:**
- Moved `oncutf/core/theme_manager.py` → `oncutf/ui/theme_manager.py`
- Updated internal import: `oncutf.core.pyqt_imports` → direct PyQt5
- Replaced all 58 import references across codebase
- Files updated: oncutf/ (31 files), tests/ (many), examples/ (1), main.py

**Quality gates passed:**
- ✅ ruff check: 8 auto-fixes applied, 3 minor warnings
- ✅ mypy: Success (0 errors in 549 files)
- ✅ All 58 imports migrated from `core.theme_manager` to `ui.theme_manager`

**Impact:**
- Reduces ui -> core imports by ~36 occurrences (79 → 43)
- ThemeManager is now properly in UI layer (Qt-dependent)
- Prepares for core layer to be Qt-free

**Next:** QW-3 (Clean __init__.py UI event imports)

---

### ✅ ApplicationContext Split (COMPLETED - 2026-01-25)

**Status:** DONE — ApplicationContext split into Qt-free and Qt wrapper versions

**Architecture:**
```
oncutf/app/state/context.py          (NEW - Qt-free AppContext)
    ↑
oncutf/ui/adapters/qt_app_context.py (NEW - Qt wrapper with signals)
    ↑
oncutf/core/application_context.py   (MODIFIED - backward compatibility wrapper)
```

**Changes made:**

1. **Created `oncutf/app/state/context.py`** (270 lines)
   - Pure Python `AppContext` class (no Qt dependencies)
   - Singleton pattern for application state
   - Manages files, selection, metadata, manager registry
   - Performance tracking capabilities

2. **Created `oncutf/ui/adapters/qt_app_context.py`** (280 lines)
   - QObject wrapper `QtAppContext` with pyqtSignals
   - Delegates all operations to `AppContext`
   - Emits Qt signals for UI components:
     - `files_changed`, `selection_changed`, `metadata_changed`
   - Connects AppContext state changes to Qt signals

3. **Modified `oncutf/core/application_context.py`** (210 lines)
   - Now a deprecated backward compatibility wrapper
   - Delegates all operations to `QtAppContext`
   - Preserves existing API for gradual migration
   - Added deprecation warnings pointing to new modules

**Migration path:**
- UI code: Use `QtAppContext` from `oncutf.ui.adapters`
- Non-UI code: Use `AppContext` from `oncutf.app.state`
- Legacy code: Continue using `ApplicationContext` (will be removed in v2.0)

**Quality gates passed:**
- ✅ ruff check: All context files clean (3 auto-fixes applied)
- ✅ mypy: ApplicationContext split files have 0 errors
- ✅ Backward compatibility: All 50+ existing imports still work

**Impact:**
- Enables non-UI code to use Qt-free state management
- Reduces coupling between app services and Qt
- Prepares for complete core/app layer Qt removal
- Temporary ui→core import created (ApplicationContext → QtAppContext) for compatibility

**Next:** Gradually migrate files from ApplicationContext to AppContext/QtAppContext

---

### ✅ QW-3: Clean __init__.py UI Event Imports (COMPLETED - 2026-01-25)

**Status:** DONE — Removed UI re-exports from core/events/__init__.py

**Problem:** `oncutf/core/events/__init__.py` was re-exporting `ContextMenuHandlers` from `oncutf.ui.events.context_menu`, creating a core→ui import violation.

**Changes made:**
- Removed `from oncutf.ui.events.context_menu import ContextMenuHandlers` from `core/events/__init__.py`
- Removed `ContextMenuHandlers` from `__all__` export list
- Added documentation note to import directly from `oncutf.ui.events.context_menu` instead
- `event_handler_manager.py` already imports directly, no changes needed

**Quality gates passed:**
- ✅ ruff check: All checks passed
- ✅ mypy: File clean (other unrelated errors in different files)
- ✅ No UI imports in core/__init__.py files

**Impact:**
- Removes 1 core→ui violation from __init__.py re-exports
- Makes boundary between core and ui clearer
- Forces explicit imports instead of convenience re-exports

**Next:** QW-4 (Remove UI fallbacks from app services)

---

### ✅ QW-4: Remove UI Fallbacks from App Services (COMPLETED - 2026-01-25)

**Status:** DONE — Removed UI fallback imports from app/services/user_interaction.py

**Problem:** `app/services/user_interaction.py` had fallback code that directly imported from `oncutf.ui.dialogs` and `oncutf.core.pyqt_imports` when the adapter wasn't registered, creating app→ui and app→core violations.

**Changes made:**
- Removed all fallback imports from `show_info_message()`, `show_error_message()`, `show_warning_message()`, `show_question_message()`
- Changed behavior: Now raises `RuntimeError` if `user_dialog` adapter is not registered
- Added `# noqa: ARG001` to unused `parent` parameter (kept for API compatibility)
- Updated docstrings to clarify that adapter must be registered during initialization

**Before:**
```python
if ctx.has_manager("user_dialog"):
    adapter.show_info(title, message)
else:
    # Fallback: direct Qt import (VIOLATION)
    from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog
    CustomMessageDialog.information(parent, title, message)
```

**After:**
```python
if not ctx.has_manager("user_dialog"):
    raise RuntimeError(
        "UserDialogPort adapter not registered. "
        "Call register_user_dialog_adapter() during initialization."
    )
adapter = ctx.get_manager("user_dialog")
adapter.show_info(title, message)
```

**Quality gates passed:**
- ✅ ruff check: All checks passed
- ✅ Removed 4 app→ui import violations
- ✅ Removed 4 app→core import violations (pyqt_imports)

**Impact:**
- Enforces proper dependency injection pattern
- Makes missing adapter registration fail fast with clear error message
- Removes 8 boundary violations from app layer
- app/services now strictly follows port-adapter pattern

**Remaining app→ui violations:**
- `app/services/progress.py` - 3 direct imports to `QtProgressDialogAdapter` (TODO: use adapter registry)
- `app/services/ui_state.py` - 1 import to `FileTableView` (TODO: use protocol)

**Next:** Continue with remaining boundary violations

---

### Remaining Work

```bash
# Find all usages
grep -r "from oncutf.core.pyqt_imports" oncutf/ui/
```

Replace with direct imports:
```python
# Before
from oncutf.core.pyqt_imports import QWidget, QVBoxLayout

# After
from PyQt5.QtWidgets import QWidget, QVBoxLayout
```

### QW-2: Move theme_manager to UI

```bash
git mv oncutf/core/theme_manager.py oncutf/ui/theme_manager.py
# Update all imports
```

### QW-3: Clean __init__.py UI Event Imports

Remove event handler re-exports from core `__init__.py` files.

### QW-4: Remove UI Fallbacks from App Services

Search and remove:
```bash
grep -r "from oncutf.ui" oncutf/app/
grep -r "from oncutf.ui" oncutf/core/
```

---

## File Move Targets (Complete Map)

| Current | Target | Priority |
|---------|--------|----------|
| `core/theme_manager.py` | `ui/theme_manager.py` | HIGH |
| `core/pyqt_imports.py` | DELETE (use PyQt5 directly) | HIGH |
| `core/application_context.py` | Split: `app/state/` + `ui/adapters/` | HIGH |
| `core/initialization/*` | `ui/boot/` | MEDIUM |
| `core/rename/unified_rename_engine.py` | `app/use_cases/` + `ui/adapters/` | MEDIUM |
| `utils/naming/preview_engine.py` | DELETE (use domain/rename/) | LOW |
| `utils/naming/renamer.py` | DELETE (use app/use_cases/) | LOW |
| `utils/metadata/exiftool_adapter.py` | DELETE (use infra/external/) | LOW |

---

## Typing Plan (Practical Strictness)

| Layer | Strictness | `Any` Allowed | `# type: ignore` |
|-------|------------|---------------|------------------|
| `domain/` | Strict | No | No |
| `app/` | Strict | No | No |
| `infra/` | Moderate | External libs only | Justified only |
| `ui/` | Gradual | Qt callbacks | Tracked for removal |

**Current type: ignore count:** 13 (target: 5 or less)

---

## Exit Criteria (Next Gate)

| Criterion | Current | Target | Status |
|-----------|---------|--------|--------|
| core -> ui imports | 39 | 0 | BLOCKED |
| ui -> core imports | 159 | 0 | BLOCKED |
| type: ignore | 13 | <=5 | OPEN |
| Duplicate rename paths | 4+ | 0 | OPEN |
| Duplicate ExifTool paths | 3+ | 0 | OPEN |

**Gate blocked until:** All HIGH priority moves completed.

---

## Verification Commands

```bash
# Count core -> ui violations
grep -r "from oncutf\.ui" oncutf/core/ | wc -l

# Count ui -> core violations  
grep -r "from oncutf\.core" oncutf/ui/ | wc -l

# Count type: ignore
grep -r "# type: ignore" oncutf/ | wc -l

# List pyqt_imports usages
grep -r "from oncutf.core.pyqt_imports" oncutf/

# Run quality gates
ruff check . && mypy . && pytest
```

---

## Archive Note

- Previous summary moved to `docs/_archive/260121_summary.md`.
