# Core Layer Qt Migration Plan

## Executive Summary

**UPDATED 2026-02-03:** Enhanced audit tool now detects **transitive Qt dependencies**.

**Actual Qt contamination:**

- **Core layer:** 34 direct + 13 transitive = **47 total violations**
- **App layer:** 3 direct + 6 transitive = **9 total violations**
- **Grand total:** 56 violations (was 37 with only direct checking)

The core layer should be pure business logic, testable without Qt dependencies.
The app layer (use cases) should also be Qt-free for testability.

## Current State (2026-02-03)

audit_boundaries.py results with `--transitive` enabled:

Violations by rule:

- core_must_not_import_qt                       34
- core_must_not_import_qt_transitive            13
- app_must_not_import_qt_transitive             6
- app_must_not_import_qt                        3

### Key Transitive Leaks

**Core layer:**

- `counter_module.py` → Qt (affects rename engine)
- `timer_manager.py` → Qt (affects streaming loader)
- `base_worker.py` → Qt (contaminates core/**init**)
- `operations_manager.py` → Qt (contaminates core/file/)

**App layer:**

- `selection_store.py` → Qt (contaminates entire app.state)
- `file_store.py` → Qt (contaminates app.services)
- `user_interaction.py` → Qt (contaminates app.services)

To generate current report: `python tools/audit_boundaries.py --package oncutf`

## Violation Categories

### Category A: Qt Signals/Threading (Highest Impact)

These modules use Qt for threading/signals and need complete redesign.

| File | Qt Usage | Migration Strategy |
| ------ | ---------- | ------------------- |
| `core/base_worker.py` | QObject, pyqtSignal | Move to `infra/workers/` |
| `core/thread_pool_manager.py` | QThreadPool | Move to `infra/threading/` |
| `core/shutdown_coordinator.py` | QTimer | Move to `infra/lifecycle/` |
| `core/memory_manager.py` | QTimer | Move to `infra/memory/` |
| `core/progress_protocol.py` | pyqtSignal | Abstract to Protocol |

### Category B: Thumbnail System (High Coupling)

Heavy Qt coupling for image processing.

| File | Qt Usage | Migration Strategy |
| ------ | ---------- | ------------------- |
| `core/thumbnail/providers.py` | QSize, QImage, QPixmap | Move to `infra/thumbnail/` |
| `core/thumbnail/thumbnail_cache.py` | QPixmap | Move to `infra/thumbnail/` |
| `core/thumbnail/thumbnail_manager.py` | QObject, QSize, QImage | Split: logic stays, Qt moves |
| `core/thumbnail/thumbnail_worker.py` | QRunnable, QImage | Move to `infra/workers/` |

### Category C: Metadata System (Medium Coupling)

Mixed business logic and Qt widgets.

| File | Qt Usage | Migration Strategy |
| ------ | ---------- | ------------------- |
| `core/metadata/metadata_loader.py` | QObject, QApplication | Extract Qt to adapter |
| `core/metadata/metadata_writer.py` | QObject, QMessageBox | Extract Qt to adapter |
| `core/metadata/parallel_loader.py` | QMessageBox, QObject | Extract Qt to adapter |
| `core/metadata/command_manager.py` | QObject | Abstract to Protocol |
| `core/metadata/staging_manager.py` | QObject | Abstract to Protocol |
| `core/metadata/metadata_progress_handler.py` | QMessageBox | Inject dialog dependency |
| `core/metadata/metadata_shortcut_handler.py` | QShortcut, QWidget | Move to `ui/handlers/` |

### Category D: Hash System (Medium Coupling)

Workers with Qt signals.

| File | Qt Usage | Migration Strategy |
| ------ | ---------- | ------------------- |
| `core/hash/base_hash_worker.py` | QObject, pyqtSignal | Move to `infra/workers/` |
| `core/hash/hash_worker.py` | QObject | Move to `infra/workers/` |
| `core/hash/parallel_hash_worker.py` | QObject | Move to `infra/workers/` |
| `core/hash/hash_results_presenter.py` | QDialog | Move to `ui/dialogs/` |

### Category E: File System (Low Coupling)

Minimal Qt usage, easiest to fix.

| File | Qt Usage | Migration Strategy |
| ------ | ---------- | ------------------- |
| `core/file/load_manager.py` | QObject | Abstract to Protocol |
| `core/file/monitor.py` | QObject, QTimer | Move to `infra/file/` |
| `core/file/operations_manager.py` | QObject, QUndoStack | Split: undo → ui, ops stay |

### Category F: Other Core Files

| File | Qt Usage | Migration Strategy |
| ------ | ---------- | ------------------- |
| `core/application_service.py` | QObject | Abstract to Protocol |
| `core/backup_manager.py` | QObject | Abstract to Protocol |
| `core/modifier_handler.py` | Qt.KeyboardModifier | Pass as enum/int |

### Category G: App Layer (3 violations)

| File | Qt Usage | Migration Strategy |
| ------ | ---------- | ------------------- |
| `app/services/user_interaction.py` | QWidget | Inject via Protocol |
| `app/state/file_store.py` | QObject | Abstract to Protocol |
| `app/state/selection_store.py` | QObject | Abstract to Protocol |

---

## Migration Phases

### Phase 1: Infrastructure Setup (Low Risk)

Create proper infrastructure layer for Qt-dependent code.

**Actions:**

1. Create `oncutf/infra/workers/` package
2. Create `oncutf/infra/threading/` package
3. Create `oncutf/infra/thumbnail/` package
4. Define abstract protocols in `oncutf/domain/protocols/`

**Files to create:**

oncutf/infra/workers/**init**.py
oncutf/infra/workers/base_worker.py      # from core/base_worker.py
oncutf/infra/threading/**init**.py
oncutf/infra/threading/pool_manager.py   # from core/thread_pool_manager.py
oncutf/domain/protocols/progress.py      # Abstract progress protocol
oncutf/domain/protocols/worker.py        # Abstract worker protocol

### Phase 2: Move Pure Qt Components (Medium Risk)

Move components that are purely Qt wrappers.

**Actions:**

1. Move `core/hash/hash_results_presenter.py` → `ui/dialogs/hash_results_dialog.py`
2. Move `core/metadata/metadata_shortcut_handler.py` → `ui/handlers/metadata_shortcuts.py`
3. Move thumbnail workers to `infra/thumbnail/`

### Phase 3: Abstract Qt Dependencies (Higher Risk)

Replace direct Qt usage with injected protocols.

**Pattern:**

```python
# Before (in core)
from PyQt5.QtCore import QObject, pyqtSignal

class MetadataLoader(QObject):
    progress_updated = pyqtSignal(int)

# After (in core)
from oncutf.domain.protocols.progress import ProgressReporter

class MetadataLoader:
    def __init__(self, progress_reporter: ProgressReporter):
        self._progress = progress_reporter
```

### Phase 4: Signal Abstraction (Complex)

Replace pyqtSignal with callback-based or observer pattern.

**Options:**

1. Callback injection: `on_progress: Callable[[int], None]`
2. Observer protocol: `ProgressObserver.update(value: int)`
3. Event bus: Decouple via message bus (overkill for this project)

---

## Recommended Order

| Priority | Files | Reason |
| ---------- | ------- | -------- |
| 1 | `hash_results_presenter.py` | Pure UI, easy move |
| 2 | `metadata_shortcut_handler.py` | Pure UI, easy move |
| 3 | `modifier_handler.py` | Simple Qt enum usage |
| 4 | Category F files | Low coupling |
| 5 | Category E files | File operations |
| 6 | Category D files | Hash workers |
| 7 | Category C files | Metadata system |
| 8 | Category B files | Thumbnail system |
| 9 | Category A files | Threading core |

---

## Success Criteria

1. `python tools/audit_boundaries.py` returns 0 violations
2. All tests pass
3. Application runs without regressions
4. Core layer can be unit tested without Qt imports

---

## Risk Mitigation

- **Incremental migration**: One file at a time
- **Feature branch**: `refactor/core-qt-migration-phase-N`
- **Test coverage**: Add tests before moving code
- **Rollback points**: Git tags at each phase completion

---

## Estimated Effort

| Phase | Files | Effort |
| ------- | ------- | -------- |
| Phase 1 | 6 | 2 hours |
| Phase 2 | 4 | 3 hours |
| Phase 3 | 15 | 8 hours |
| Phase 4 | 18 | 12 hours |
| **Total** | **43** | **~25 hours** |

---

## Quick Wins (Start Here)

1. **`core/hash/hash_results_presenter.py`** (17 lines Qt)
   - Move to `ui/dialogs/hash_results_dialog.py`
   - Update imports in callers

2. **`core/metadata/metadata_shortcut_handler.py`** (4 lines Qt)
   - Move to `ui/handlers/metadata_shortcuts.py`
   - Update imports in callers

3. **`core/modifier_handler.py`** (1 line Qt)
   - Replace `Qt.KeyboardModifier` with `int` or custom enum
