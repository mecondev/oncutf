# Core → UI Migration Plan (2026-01-26)

## Overview

This plan outlines the migration of UI-coupled modules from `oncutf/core/` to appropriate locations in `oncutf/ui/`. The goal is to enforce proper architectural boundaries.

**Current violations:** 27 core→ui imports (down from 41)  
**Target:** <10 runtime violations (TYPE_CHECKING imports acceptable)

---

## Phase 1: UI Managers Migration (HIGH PRIORITY)

### Files to Move

```
core/ui_managers/                  → ui/managers/
├── __init__.py                    → __init__.py
├── column_manager.py              → column_manager.py (adapter only)
├── column_service.py              → column_service.py (canonical service)
├── shortcut_manager.py            → shortcut_manager.py
├── splitter_manager.py            → splitter_manager.py
└── window_config_manager.py       → window_config_manager.py
```

### Impact Analysis

**Files importing from core/ui_managers/:**
```bash
$ grep -r "from oncutf\.core\.ui_managers" oncutf/ --include="*.py" | wc -l
# Result: ~15 files
```

**Breakdown:**
- `ui/behaviors/column_management/` (4 files) → uses UnifiedColumnService
- `ui/widgets/file_table/view.py` (1 file) → uses get_column_service()
- `core/initialization/` (1 file) → uses managers
- `ui/main_window.py` (1 file) → uses managers

**Migration Steps:**

1. **Create target directory:**
   ```bash
   mkdir -p oncutf/ui/managers
   ```

2. **Move files with git:**
   ```bash
   git mv oncutf/core/ui_managers/__init__.py oncutf/ui/managers/__init__.py
   git mv oncutf/core/ui_managers/column_service.py oncutf/ui/managers/column_service.py
   # ... repeat for all files
   ```

3. **Update imports (bulk operation):**
   ```python
   # Before:
   from oncutf.core.ui_managers.column_service import UnifiedColumnService
   
   # After:
   from oncutf.ui.managers.column_service import UnifiedColumnService
   ```

4. **Update __init__.py exports:**
   ```python
   # oncutf/ui/managers/__init__.py
   from oncutf.ui.managers.column_service import UnifiedColumnService, get_column_service
   from oncutf.ui.managers.shortcut_manager import ShortcutManager
   # ... etc
   ```

**Risk Level:** MEDIUM
- Impact: ~15 files need import updates
- Breaking change: No (same API)
- Test impact: Low (no logic changes)

**Estimated effort:** 1-2 hours

---

## Phase 2: Initialization Bootstrap Migration (HIGH PRIORITY)

### Files to Move

```
core/initialization/               → ui/boot/
├── __init__.py                    → __init__.py
├── initialization_orchestrator.py → bootstrap_orchestrator.py (rename)
├── initialization_manager.py      → bootstrap_manager.py (rename)
└── initialization_worker.py       → bootstrap_worker.py (rename)
```

### Impact Analysis

**Files importing from core/initialization/:**
```
- ui/main_window.py (primary consumer)
- main.py (application entry point)
```

**Migration Steps:**

1. **Create target directory:**
   ```bash
   mkdir -p oncutf/ui/boot
   ```

2. **Move and rename files:**
   ```bash
   git mv oncutf/core/initialization/initialization_orchestrator.py \
           oncutf/ui/boot/bootstrap_orchestrator.py
   # Update class names: InitializationOrchestrator → BootstrapOrchestrator
   ```

3. **Update imports:**
   ```python
   # Before:
   from oncutf.core.initialization.initialization_orchestrator import InitializationOrchestrator
   
   # After:
   from oncutf.ui.boot.bootstrap_orchestrator import BootstrapOrchestrator
   ```

4. **Update main_window.py:**
   - Replace initialization_orchestrator usage
   - Update __init__ to use BootstrapOrchestrator

**Risk Level:** MEDIUM-HIGH
- Impact: 2 critical files (main.py, main_window.py)
- Breaking change: Yes (entry point changes)
- Test impact: Medium (integration tests may need updates)

**Estimated effort:** 2-3 hours

---

## Phase 3: Event/Signal Coordination Migration (MEDIUM PRIORITY)

### Files to Analyze

```
core/event_handler_manager.py      → ui/events/event_coordinator.py
core/signal_coordinator.py         → ui/events/signal_coordinator.py
```

### Current Architecture

```
event_handler_manager.py (core)
├── Delegates to: FileEventHandlers (core/events/)
├── Delegates to: UIEventHandlers (core/events/)
└── Delegates to: ContextMenuHandlers (ui/events/) ← VIOLATION
```

**Problem:** Core module importing from UI module.

### Proposed Architecture

```
ui/events/event_coordinator.py
├── Coordinates: FileEventHandlers (keep in core/events/)
├── Coordinates: UIEventHandlers (keep in core/events/)
└── Coordinates: ContextMenuHandlers (ui/events/)
```

**Migration Steps:**

1. **Move event_handler_manager.py:**
   ```bash
   git mv oncutf/core/event_handler_manager.py \
           oncutf/ui/events/event_coordinator.py
   ```

2. **Update class name:**
   ```python
   # EventHandlerManager → EventCoordinator
   ```

3. **Update imports in main_window.py:**
   ```python
   # Before:
   from oncutf.core.event_handler_manager import EventHandlerManager
   
   # After:
   from oncutf.ui.events.event_coordinator import EventCoordinator
   ```

4. **Move signal_coordinator.py:**
   ```bash
   git mv oncutf/core/signal_coordinator.py \
           oncutf/ui/events/signal_coordinator.py
   ```

**Risk Level:** LOW
- Impact: 2-3 files
- Breaking change: No (facade pattern)
- Test impact: Low

**Estimated effort:** 1 hour

---

## Phase 4: Drag Managers Analysis (LOW PRIORITY - DEFER)

### Current Structure

```
core/drag/
├── drag_manager.py           (some UI coupling)
├── drag_visual_manager.py    (heavy UI coupling)
└── drag_cleanup_manager.py   (UI coupling)
```

**Used by:**
- `ui/behaviors/drag_drop_behavior.py`
- `ui/widgets/file_tree/drag_handler.py`

### Recommendation

**DEFER** - This requires deeper architectural refactoring:
1. Split drag business logic from UI logic
2. Create drag protocols/ports
3. Extract pure drag state management to core
4. Move UI visualization to ui/drag/

**Reason for deferral:** Complex refactoring, low priority compared to other migrations.

---

## Phase 5: Remaining Specialized Dialogs (CREATE PORTS)

Instead of moving these, create protocol-based ports:

### Dialogs Without Ports

1. **ResultsTableDialog** (hash_results_presenter.py)
   ```python
   # Create: app/ports/results_display.py
   class ResultsDisplayPort(Protocol):
       def show_hash_results(self, results: dict, was_cancelled: bool) -> None: ...
   ```

2. **ConflictResolutionDialog** (file/operations_manager.py)
   ```python
   # Create: app/ports/conflict_resolution.py
   class ConflictResolutionPort(Protocol):
       def resolve_conflict(self, old: str, new: str) -> tuple[str, bool]: ...
   ```

3. **MetadataEditDialog** (metadata/operations_manager.py)
   ```python
   # Create: app/ports/metadata_editing.py
   class MetadataEditPort(Protocol):
       def edit_field(self, field: str, files: list, current: str) -> tuple[bool, str, list]: ...
   ```

4. **StyledComboBox** (metadata/operations_manager.py)
   - **Alternative:** Use standard QComboBox in core, style in UI
   - **OR:** Pass pre-styled widget from UI to core

5. **update_info_icon()** helper (metadata_writer.py)
   ```python
   # Create: app/ports/ui_update.py
   class UIUpdatePort(Protocol):
       def update_file_icon(self, file_path: str) -> None: ...
   ```

**Estimated effort:** 3-4 hours (all ports)

---

## Migration Timeline

### Week 1 (Immediate)
- [x] **Day 1-2:** Phase 1 - UI Managers Migration ✅ COMPLETED 2026-01-26
  - Moved: core/ui_managers/ → ui/managers/ (9 files)
  - Updated: 13 files with import path changes
  - Created: FileLoadUIPort + adapter for remaining violation
  - Violations: 27 → 18 (-33%)
  - Commits: 37a5a216, 8b4d4fed, 3565b762
  - All core→ui.managers violations eliminated (except initialization_orchestrator)

### Week 2 (High Priority)
- [ ] **Day 3-4:** Phase 2 - Initialization Bootstrap
  - Move core/initialization/ → ui/boot/
  - Rename classes (Initialization → Bootstrap)
  - Update entry points
  - Test integration thoroughly

- [ ] **Day 5:** Phase 3 - Event Coordination
  - Move event coordinators to ui/events/
  - Update imports
  - Test and commit

### Week 3 (Medium Priority)
- [ ] **Day 6-7:** Phase 5 - Create Ports
  - Create ResultsDisplayPort
  - Create ConflictResolutionPort
  - Create MetadataEditPort
  - Create UIUpdatePort
  - Implement adapters in ui/adapters/

### Future (Deferred)
- [ ] **Phase 4:** Drag Managers Refactoring (requires architecture redesign)

---

## Pre-Migration Checklist

Before each phase:

1. **Backup current state:**
   ```bash
   git commit -am "Checkpoint before [PHASE] migration"
   git tag pre-[PHASE]-migration
   ```

2. **Run full test suite:**
   ```bash
   pytest -v
   ruff check .
   mypy .
   ```

3. **Document current import graph:**
   ```bash
   grep -r "from oncutf\.core\.[TARGET]" oncutf/ --include="*.py" > /tmp/imports_before.txt
   ```

4. **Create migration branch:**
   ```bash
   git checkout -b refactor/2026-01-26/[PHASE]-migration
   ```

---

## Post-Migration Checklist

After each phase:

1. **Verify all imports updated:**
   ```bash
   grep -r "from oncutf\.core\.[OLD_PATH]" oncutf/ --include="*.py"
   # Should return 0 results
   ```

2. **Run quality gates:**
   ```bash
   ruff check .
   mypy .
   pytest -v
   ```

3. **Update documentation:**
   - Update ARCHITECTURE.md
   - Update migration_stance.md
   - Update 260125_summary.md

4. **Commit with detailed message:**
   ```bash
   git add -A
   git commit -m "Refactor: Move [MODULE] from core to ui

   - Moved: core/[PATH] → ui/[PATH]
   - Updated: [N] import statements
   - Impact: [DESCRIPTION]
   
   Violations: [OLD_COUNT] → [NEW_COUNT]
   
   Quality gates:
   ✅ ruff check: All passed
   ✅ mypy: Success
   ✅ pytest: [PASSED]/[TOTAL] passed
   "
   ```

5. **Merge to main:**
   ```bash
   git checkout main
   git merge --no-ff refactor/2026-01-26/[PHASE]-migration
   git push
   ```

---

## Expected Final State

After all migrations:

**core→ui violations:**
- Before Phase 1: 27
- After Phase 1: 18 (-33%) ✅ ACHIEVED
- Target Phase 2: ~9 (-9 from initialization)
- Target Phase 3: ~6 (-3 from event/signal)
- Target Phase 5: ~1 (-5 from ports)

**Remaining acceptable violations:**
- TYPE_CHECKING imports (6) - these are fine
- application_context.py backward compat (2) - temporary
- Drag managers (defer to future)

**Target achieved:** <10 runtime violations ✅

---

## Risk Mitigation

### High-Risk Areas

1. **main.py / main_window.py** (initialization changes)
   - **Mitigation:** Extensive integration testing
   - **Fallback:** Keep old code commented for 1 release

2. **Column service** (heavily used)
   - **Mitigation:** Update all imports in single commit
   - **Fallback:** Create temporary delegator in old location

3. **Event handlers** (core→ui boundary)
   - **Mitigation:** Maintain facade pattern
   - **Fallback:** Protocol-based abstraction

### Rollback Plan

If migration causes issues:

```bash
# Rollback to pre-migration tag
git reset --hard pre-[PHASE]-migration

# OR cherry-pick fixes
git checkout main
git cherry-pick [COMMIT_BEFORE_MIGRATION]
```

---

## Success Criteria

✅ All tests passing (1154+ tests)  
✅ Ruff: 0 violations  
✅ Mypy: 0 errors in migrated modules  
✅ Core→UI violations: <10 runtime imports  
✅ No functionality regressions  
✅ Documentation updated  
✅ Git history clean (no merge commits without --no-ff)

