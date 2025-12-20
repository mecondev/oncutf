# OnCutF Refactoring Execution Roadmap

> **Status**: ACTIVE  
> **Created**: December 2025  
> **Governing Document**: [ARCH_REFACTOR_PLAN.md](ARCH_REFACTOR_PLAN.md)

---

## Execution Rules (Non-Negotiable)

1. **One responsibility per step** - never mix file moves with logic changes
2. **Test → Lint → Commit → Push** after every step
3. **App must be runnable** at every checkpoint
4. **No optimization** - correctness over elegance
5. **No "while we're here" changes** - strict scope discipline

---

## Phase 0: Package Structure (Move-Only)

**Overall Goal**: Move all application code under `oncutf/` package.  
**Constraint**: NO logic changes. NO renames. ONLY file moves and import fixes.

---

### Step 0.1: Create Package Directory Structure

**Goal**: Create empty `oncutf/` package with all subdirectories.

**Files/Folders Affected**:
```
CREATE:
  oncutf/
  oncutf/__init__.py
  oncutf/ui/
  oncutf/ui/__init__.py
  oncutf/ui/dialogs/
  oncutf/ui/dialogs/__init__.py
  oncutf/ui/widgets/
  oncutf/ui/widgets/__init__.py
  oncutf/ui/delegates/
  oncutf/ui/delegates/__init__.py
  oncutf/ui/mixins/
  oncutf/ui/mixins/__init__.py
  oncutf/core/
  oncutf/core/__init__.py
  oncutf/modules/
  oncutf/modules/__init__.py
  oncutf/models/
  oncutf/models/__init__.py
  oncutf/utils/
  oncutf/utils/__init__.py
```

**Allowed**:
- Creating directories
- Creating empty `__init__.py` files

**Forbidden**:
- Moving any existing files
- Modifying any existing code
- Adding any logic to `__init__.py`

**Tests to Run**:
```bash
pytest tests/ -x -q
```
(All existing tests must still pass - nothing changed yet)

**Commit Message**:
```
chore: create oncutf package directory structure
```

**Definition of Done**:
- [ ] All directories created
- [ ] All `__init__.py` files exist (empty)
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches app successfully
- [ ] Committed and pushed

**Safe to Continue When**: App launches, tests pass.

---

### Step 0.2: Move models/ to oncutf/models/

**Goal**: Move all model files to new location.

**Files/Folders Affected**:
```
MOVE:
  models/__init__.py      → oncutf/models/__init__.py
  models/file_entry.py    → oncutf/models/file_entry.py
  models/file_item.py     → oncutf/models/file_item.py
  models/metadata_entry.py → oncutf/models/metadata_entry.py
  models/metadata_models.py → oncutf/models/metadata_models.py
  models/rename_types.py  → oncutf/models/rename_types.py

DELETE (after move):
  models/
```

**Allowed**:
- Moving files with `git mv`
- Updating imports in moved files (from `models.X` to `oncutf.models.X`)
- Updating imports in ALL files that reference `models.*`

**Forbidden**:
- Changing any logic
- Renaming any classes/functions
- Modifying any docstrings
- Adding new functionality

**Tests to Run**:
```bash
pytest tests/ -x -q
```

**Commit Message**:
```
refactor: move models to oncutf/models
```

**Definition of Done**:
- [ ] All model files in `oncutf/models/`
- [ ] Old `models/` directory deleted
- [ ] All imports updated across codebase
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches app successfully
- [ ] Committed and pushed

**Safe to Continue When**: App launches, tests pass, no import errors.

---

### Step 0.3: Move modules/ to oncutf/modules/

**Goal**: Move all rename module files to new location.

**Files/Folders Affected**:
```
MOVE:
  modules/__init__.py           → oncutf/modules/__init__.py
  modules/base_module.py        → oncutf/modules/base_module.py
  modules/counter_module.py     → oncutf/modules/counter_module.py
  modules/metadata_module.py    → oncutf/modules/metadata_module.py
  modules/name_transform_module.py → oncutf/modules/name_transform_module.py
  modules/specified_text_module.py → oncutf/modules/specified_text_module.py
  modules/text_removal_module.py → oncutf/modules/text_removal_module.py

DELETE (after move):
  modules/
```

**Allowed**:
- Moving files with `git mv`
- Updating imports (from `modules.X` to `oncutf.modules.X`)

**Forbidden**:
- Changing any module logic
- Renaming any classes
- Modifying apply_from_data or any methods

**Tests to Run**:
```bash
pytest tests/ -x -q
pytest tests/unit/test_counter_module.py -v  # Specific module tests
```

**Commit Message**:
```
refactor: move modules to oncutf/modules
```

**Definition of Done**:
- [ ] All module files in `oncutf/modules/`
- [ ] Old `modules/` directory deleted
- [ ] All imports updated
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches, rename preview works
- [ ] Committed and pushed

**Safe to Continue When**: Rename preview generates correct names.

---

### Step 0.4: Move utils/ to oncutf/utils/

**Goal**: Move all utility files to new location.

**Files/Folders Affected**:
```
MOVE:
  utils/*.py → oncutf/utils/*.py
  (all 55+ files)

DELETE (after move):
  utils/
```

**Allowed**:
- Moving files with `git mv`
- Updating imports (from `utils.X` to `oncutf.utils.X`)

**Forbidden**:
- Changing any utility logic
- Splitting or merging files
- Renaming any functions

**Tests to Run**:
```bash
pytest tests/ -x -q
```

**Commit Message**:
```
refactor: move utils to oncutf/utils
```

**Definition of Done**:
- [ ] All utility files in `oncutf/utils/`
- [ ] Old `utils/` directory deleted
- [ ] All imports updated
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches successfully
- [ ] Committed and pushed

**Safe to Continue When**: App launches, all features work.

---

### Step 0.5: Move widgets/ to oncutf/ui/widgets/

**Goal**: Move all widget files to new location.

**Files/Folders Affected**:
```
MOVE:
  widgets/*.py → oncutf/ui/widgets/*.py
  widgets/mixins/*.py → oncutf/ui/mixins/*.py
  (all 35+ files)

DELETE (after move):
  widgets/
```

**Allowed**:
- Moving files with `git mv`
- Updating imports (from `widgets.X` to `oncutf.ui.widgets.X`)
- Updating imports (from `widgets.mixins.X` to `oncutf.ui.mixins.X`)

**Forbidden**:
- Changing any widget logic
- Modifying any Qt signals/slots
- Renaming any classes

**Tests to Run**:
```bash
pytest tests/ -x -q
pytest tests/unit/widgets/ -v  # Widget-specific tests
```

**Commit Message**:
```
refactor: move widgets to oncutf/ui/widgets
```

**Definition of Done**:
- [ ] All widget files in `oncutf/ui/widgets/`
- [ ] All mixin files in `oncutf/ui/mixins/`
- [ ] Old `widgets/` directory deleted
- [ ] All imports updated
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches, UI displays correctly
- [ ] Committed and pushed

**Safe to Continue When**: UI renders correctly, table/tree views work.

---

### Step 0.6: Move core/ to oncutf/core/

**Goal**: Move all core files to new location.

**Files/Folders Affected**:
```
MOVE:
  core/*.py → oncutf/core/*.py
  (all 60+ files)

DELETE (after move):
  core/
```

**Allowed**:
- Moving files with `git mv`
- Updating imports (from `core.X` to `oncutf.core.X`)

**Forbidden**:
- Changing any manager logic
- Splitting ApplicationContext
- Modifying any service code

**Tests to Run**:
```bash
pytest tests/ -x -q
```

**Commit Message**:
```
refactor: move core to oncutf/core
```

**Definition of Done**:
- [ ] All core files in `oncutf/core/`
- [ ] Old `core/` directory deleted
- [ ] All imports updated
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches successfully
- [ ] Committed and pushed

**Safe to Continue When**: All managers initialize correctly.

---

### Step 0.7: Move main_window.py and config.py

**Goal**: Move remaining root-level application files.

**Files/Folders Affected**:
```
MOVE:
  main_window.py → oncutf/ui/main_window.py
  config.py      → oncutf/config.py
```

**Allowed**:
- Moving files with `git mv`
- Updating imports in main.py and all referencing files

**Forbidden**:
- Changing MainWindow logic
- Modifying config values
- Splitting config into multiple files

**Tests to Run**:
```bash
pytest tests/ -x -q
```

**Commit Message**:
```
refactor: move main_window and config to oncutf package
```

**Definition of Done**:
- [ ] `main_window.py` in `oncutf/ui/`
- [ ] `config.py` in `oncutf/`
- [ ] All imports updated
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches successfully
- [ ] Committed and pushed

**Safe to Continue When**: App launches from root main.py.

---

### Step 0.8: Update main.py Entry Point

**Goal**: Update root main.py to import from oncutf package.

**Files/Folders Affected**:
```
MODIFY:
  main.py (entry point - update imports only)

CREATE:
  oncutf/__main__.py (for python -m oncutf support)
```

**Allowed**:
- Changing imports in main.py to reference `oncutf.*`
- Creating `__main__.py` that calls the same entry logic

**Forbidden**:
- Changing any application logic
- Adding new features
- Modifying command-line argument handling

**Tests to Run**:
```bash
pytest tests/ -x -q
python main.py  # Direct run
python -m oncutf  # Module run (if __main__.py added)
```

**Commit Message**:
```
refactor: update main.py to use oncutf package imports
```

**Definition of Done**:
- [ ] `main.py` imports from `oncutf.*`
- [ ] `oncutf/__main__.py` exists and works
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches successfully
- [ ] `python -m oncutf` launches successfully
- [ ] Committed and pushed

**Safe to Continue When**: Both entry methods work.

---

### Step 0.9: Update Test Imports

**Goal**: Fix all test imports to use new package structure.

**Files/Folders Affected**:
```
MODIFY:
  tests/conftest.py
  tests/unit/*.py
  tests/integration/*.py
  (all test files with old imports)
```

**Allowed**:
- Updating imports in test files
- Updating conftest.py paths

**Forbidden**:
- Changing test logic
- Adding new tests
- Removing any tests

**Tests to Run**:
```bash
pytest tests/ -x -q
pytest tests/ --collect-only  # Verify all tests discovered
```

**Commit Message**:
```
refactor: update test imports for oncutf package structure
```

**Definition of Done**:
- [ ] All test imports updated
- [ ] `pytest tests/ -x -q` passes (all 549 tests)
- [ ] `pytest tests/ --collect-only` shows same test count
- [ ] Committed and pushed

**Safe to Continue When**: All 549 tests pass.

---

### Step 0.10: Cleanup and Verification

**Goal**: Final verification that Phase 0 is complete.

**Files/Folders Affected**:
```
VERIFY (should NOT exist):
  models/
  modules/
  utils/
  widgets/
  core/
  main_window.py (at root)
  config.py (at root - wait, keep this or move?)

VERIFY (should exist):
  main.py (entry point stub)
  oncutf/
  oncutf/config.py
  oncutf/ui/main_window.py
  oncutf/ui/widgets/
  oncutf/ui/mixins/
  oncutf/core/
  oncutf/modules/
  oncutf/models/
  oncutf/utils/
```

**Allowed**:
- Removing empty directories
- Running final verification

**Forbidden**:
- Any code changes
- Any logic modifications

**Tests to Run**:
```bash
pytest tests/ -v  # Full verbose run
python main.py    # Manual verification
ruff check .      # Lint check
```

**Commit Message**:
```
chore: complete Phase 0 package restructure
```

**Definition of Done**:
- [ ] No old directories remain at root
- [ ] All code lives under `oncutf/`
- [ ] `pytest tests/` - all 549 tests pass
- [ ] `ruff check .` - no new errors
- [ ] `python main.py` - app launches and works
- [ ] Manual test: load files, preview rename, execute rename
- [ ] Committed and pushed

---

## Phase 0 Completion Checkpoint

Before proceeding to Phase 1, the following MUST be confirmed:

```
[ ] App launches: python main.py
[ ] All tests pass: pytest tests/ -x -q (549 tests)
[ ] Core workflow works:
    [ ] Drag & drop files into table
    [ ] Enable counter module
    [ ] Preview shows numbered filenames
    [ ] Metadata loads for images
[ ] No import errors in console
[ ] Git history clean: one commit per step
```

**Signal to Proceed**: User explicitly confirms all checkboxes above.

---

## Phase 1: State Management Fix (Preview)

> **Prerequisite**: Phase 0 COMPLETE and CONFIRMED

Phase 1 will be detailed AFTER Phase 0 confirmation. It will follow the same
step-by-step format with:

- Step 1.1: Add FileGroup dataclass (models only)
- Step 1.2: Update FileStore to use FileGroup (logic change)
- Step 1.3: Add CounterScope enum (models only)
- Step 1.4: Update CounterModule to support scope (logic change)
- Step 1.5: Add StateCoordinator (new file)
- Step 1.6: Wire StateCoordinator signals (integration)

Each step will be ONE responsibility only.

---

## Appendix: Import Update Reference

### Old → New Import Mapping

```python
# Models
from models.file_item import FileItem
→ from oncutf.models.file_item import FileItem

# Modules
from modules.counter_module import CounterModule
→ from oncutf.modules.counter_module import CounterModule

# Utils
from utils.path_utils import normalize_path
→ from oncutf.utils.path_utils import normalize_path

# Widgets
from widgets.file_table_view import FileTableView
→ from oncutf.ui.widgets.file_table_view import FileTableView

# Mixins
from widgets.mixins.drag_mixin import DragMixin
→ from oncutf.ui.mixins.drag_mixin import DragMixin

# Core
from core.application_context import ApplicationContext
→ from oncutf.core.application_context import ApplicationContext

# Main Window
from main_window import MainWindow
→ from oncutf.ui.main_window import MainWindow

# Config
from config import Config
→ from oncutf.config import Config
```

---

*Document version: 1.0*  
*Last updated: December 2025*
