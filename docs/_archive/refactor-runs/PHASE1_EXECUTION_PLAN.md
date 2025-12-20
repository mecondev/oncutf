# Phase 1 Execution Plan: UI/Controllers Separation

**Status:** READY TO START  
**Date:** 2025-12-15  
**Approach:** Write new code first, test, then remove old code incrementally

---

## Overview

**Goal:** Separate UI (MainWindow) from business logic by introducing Controllers  
**Current:** MainWindow has 1309 lines with mixed responsibilities  
**Target:** MainWindow ~600 lines + 4 new Controllers

---

## Strategy: Safe Incremental Refactoring

### Principle: "New Code First, Old Code Last"

1. ✅ **Write** new controller code alongside old code
2. ✅ **Test** new controller works correctly
3. ✅ **Switch** MainWindow to use new controller
4. ✅ **Verify** all tests pass
5. ✅ **Remove** old code from MainWindow
6. ✅ **Commit** atomic change

**Never break the main branch. Every step must be testable.**

---

## Phase 1 Breakdown: 4 Sub-phases

### 1A: FileLoadController (Days 1-2)
### 1B: MetadataController (Days 2-3)  
### 1C: RenameController (Days 3-4)
### 1D: MainWindowController (Days 4-5)

---

## Step-by-Step Execution

## Sub-phase 1A: FileLoadController

**Objective:** Extract file loading logic from MainWindow

### Step 1A.1: Create FileLoadController skeleton (30 min)

**Actions:**
- Create `oncutf/controllers/__init__.py`
- Create `oncutf/controllers/file_load_controller.py` (empty skeleton)
- Add basic structure with logging
- **No logic yet, just structure**

**Files:**
```python
# oncutf/controllers/__init__.py
"""
Module: oncutf.controllers

Author: Michael Economou
Date: 2025-12-15

Controllers for separating UI from business logic.
"""

# oncutf/controllers/file_load_controller.py
"""
Module: file_load_controller.py

Author: Michael Economou
Date: 2025-12-15

FileLoadController: Handles file loading operations.

Responsibilities:
- File drag & drop coordination
- Directory scanning
- Companion file grouping
- File list management
"""

import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FileLoadController:
    """Controller for file loading operations."""
    
    def __init__(self):
        """Initialize FileLoadController."""
        logger.info("[FileLoadController] Initialized")
        self._file_load_manager = None  # Will be injected
    
    def load_files(self, paths: List[Path]) -> bool:
        """Load files from paths."""
        logger.info(f"[FileLoadController] Loading {len(paths)} paths")
        # TODO: Implement
        return False
```

**Validation:**
- Import the new module: `from oncutf.controllers.file_load_controller import FileLoadController`
- Instantiate: `controller = FileLoadController()`
- All tests still pass (no logic changed yet)
- **IMPORTANT:** All new files must include author/date headers (Michael Economou, current date)

**Commit:** `feat(controllers): add FileLoadController skeleton`

---

### Step 1A.2: Identify FileLoad methods in MainWindow (30 min)

**Actions:**
- Read MainWindow and find all file-loading related methods
- Document them in a checklist
- Estimate lines of code to move

**Methods to move (estimated):**
```python
# File loading methods in MainWindow (main_window.py)
- _on_files_dropped() 
- _handle_file_load()
- _load_files_from_paths()
- _scan_directory()
- _group_companion_files()
- _update_file_table()
- Interaction with FileLoadManager
```

**Output:** Create `PHASE1A_METHODS_MAP.md` in docs/

**Validation:** Manual review of method list

**Commit:** `docs(phase1a): document file loading methods to extract`

---

### Step 1A.3: Implement FileLoadController.load_files() (2 hours)

**Actions:**
- Copy logic from MainWindow's `_handle_file_load()` to controller
- Keep MainWindow method intact (don't remove yet!)
- Add proper error handling
- Add logging
- Add type hints

**Implementation:**
```python
class FileLoadController:
    def __init__(self, file_load_manager, file_store):
        self._file_load_manager = file_load_manager
        self._file_store = file_store
    
    async def load_files(self, paths: List[Path]) -> dict:
        """
        Load files from paths.
        
        Returns:
            dict: {
                'success': bool,
                'loaded_count': int,
                'errors': List[str]
            }
        """
        logger.info(f"[FileLoadController] Loading {len(paths)} paths")
        
        try:
            # Use existing FileLoadManager
            result = await self._file_load_manager.load_files_async(paths)
            
            logger.info(f"[FileLoadController] Loaded {result['loaded_count']} files")
            return result
            
        except Exception as e:
            logger.error(f"[FileLoadController] Error loading files: {e}")
            return {'success': False, 'loaded_count': 0, 'errors': [str(e)]}
```

**Validation:**
- Write unit test: `tests/test_file_load_controller.py`
- Test with mock FileLoadManager
- All existing tests still pass

**Commit:** `feat(controllers): implement FileLoadController.load_files()`

---

### Step 1A.4: Wire FileLoadController to MainWindow (1 hour)

**Actions:**
- Create FileLoadController instance in MainWindow.__init__()
- Keep old methods intact
- Add a feature flag to switch between old/new code path

```python
# In MainWindow.__init__()
self._use_new_controllers = True  # Feature flag

# Create controller
from oncutf.controllers.file_load_controller import FileLoadController
self._file_load_controller = FileLoadController(
    file_load_manager=self.file_load_manager,
    file_store=self.file_store
)

# In _on_files_dropped()
if self._use_new_controllers:
    # Use new controller
    result = await self._file_load_controller.load_files(paths)
else:
    # Use old code (fallback)
    result = await self._handle_file_load(paths)
```

**Validation:**
- Set flag to True, test drag & drop
- Set flag to False, test drag & drop
- Both should work identically
- All tests pass

**Commit:** `feat(controllers): wire FileLoadController to MainWindow (behind flag)`

---

### Step 1A.5: Remove old code from MainWindow (30 min)

**Actions:**
- Remove feature flag
- Remove old `_handle_file_load()` method
- Update all call sites to use controller

**Validation:**
- All tests pass
- Manual test: drag & drop files
- Check git diff: verify expected lines removed

**Commit:** `refactor(ui): remove old file loading code from MainWindow`

---

### Step 1A.6: Final cleanup & verification (30 min)

**Actions:**
- Remove any unused imports
- Update docstrings
- Run full test suite
- Run ruff & mypy

**Validation:**
- All 549 tests pass
- Ruff check clean
- Mypy clean (if possible)
- App launches and works

**Commit:** `chore(phase1a): final cleanup for FileLoadController`

---

## Sub-phase 1B: MetadataController

(Similar structure to 1A, ~6 steps)

### Step 1B.1: Create MetadataController skeleton
### Step 1B.2: Identify metadata methods in MainWindow
### Step 1B.3: Implement MetadataController.load_metadata()
### Step 1B.4: Wire MetadataController to MainWindow
### Step 1B.5: Remove old metadata code from MainWindow
### Step 1B.6: Final cleanup

---

## Sub-phase 1C: RenameController

(Similar structure, ~6 steps)

### Step 1C.1: Create RenameController skeleton
### Step 1C.2: Identify rename methods in MainWindow
### Step 1C.3: Implement RenameController.preview_rename()
### Step 1C.4: Implement RenameController.execute_rename()
### Step 1C.5: Wire RenameController to MainWindow
### Step 1C.6: Remove old rename code from MainWindow
### Step 1C.7: Final cleanup

---

## Sub-phase 1D: MainWindowController

(Orchestration layer, ~5 steps)

### Step 1D.1: Create MainWindowController skeleton
### Step 1D.2: Move high-level orchestration logic
### Step 1D.3: Wire all controllers together
### Step 1D.4: Simplify MainWindow to pure UI
### Step 1D.5: Final cleanup & documentation

---

## Commit Strategy

**Format:** `<type>(scope): <description>`

**Types:**
- `feat`: New controller/feature
- `refactor`: Code restructuring
- `test`: New tests
- `docs`: Documentation
- `chore`: Cleanup

**Example commits:**
```
feat(controllers): add FileLoadController skeleton
feat(controllers): implement FileLoadController.load_files()
feat(controllers): wire FileLoadController to MainWindow (behind flag)
refactor(ui): remove old file loading code from MainWindow
test(controllers): add FileLoadController tests
chore(phase1a): final cleanup for FileLoadController
```

---

## Safety Checklist (After Each Step)

- [ ] All 549 tests pass
- [ ] Ruff check clean
- [ ] App launches successfully
- [ ] Manual smoke test (drag files, load metadata, preview rename)
- [ ] Git commit with clear message
- [ ] No commented-out code remains

---

## Rollback Plan

If any step breaks:

1. **Immediate:** `git reset --hard HEAD~1` (undo last commit)
2. **Review:** Check what broke
3. **Fix:** Small targeted fix OR skip this step
4. **Retry:** Try again with safer approach

---

## Time Estimates

| Sub-phase | Steps | Time | Cumulative |
|-----------|-------|------|------------|
| 1A: FileLoadController | 6 | 5-6 hours | Day 1 |
| 1B: MetadataController | 6 | 5-6 hours | Day 2 |
| 1C: RenameController | 7 | 6-8 hours | Day 3 |
| 1D: MainWindowController | 5 | 4-5 hours | Day 4 |
| **Buffer & Testing** | - | 4-6 hours | Day 5 |

**Total:** 4-5 days (as planned)

---

## Success Criteria

**Phase 1A Complete when:**
- ✅ FileLoadController exists and works
- ✅ MainWindow uses controller for file loading
- ✅ Old file loading code removed from MainWindow
- ✅ All tests pass
- ✅ No regressions in file loading functionality

**Phase 1 Complete when:**
- ✅ 4 controllers exist (FileLoad, Metadata, Rename, MainWindow)
- ✅ MainWindow reduced from 1309 → ~600 lines
- ✅ All business logic moved to controllers
- ✅ All tests pass
- ✅ App works identically to before refactoring
- ✅ Code is more maintainable and testable

---

## Next Steps

**Ready to start?**

1. Review this plan
2. Approve or suggest modifications
3. Start with Step 1A.1 (30 minutes)

**Command to begin:**
```bash
git checkout -b phase1a-file-load-controller
```

Let's go! 🚀
