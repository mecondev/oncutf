# Phase 1D Execution Plan: MainWindowController

**Status:** READY TO START  
**Date:** 2025-12-16  
**Prerequisites:** Phase 1A (FileLoadController), 1B (MetadataController), 1C (RenameController) ✅ COMPLETE

---

## Overview

**Goal:** Create MainWindowController as orchestration layer that coordinates all sub-controllers  
**Current:** MainWindow has mixed UI + orchestration logic  
**Target:** MainWindow focuses on UI, MainWindowController orchestrates business workflows

---

## Sub-phase 1D: MainWindowController (Orchestration Layer)

**Estimated Time:** 4-5 hours  
**Complexity:** Medium (mostly coordination, less new logic)

---

## Step-by-Step Execution with Git Workflow

### Step 1D.1: Create temp branch & MainWindowController skeleton (30 min)

#### Actions:
1. Create temporary git branch
2. Create `oncutf/controllers/main_window_controller.py` (skeleton only)
3. Add basic structure with logging
4. Document responsibilities in docstring
5. **No logic yet, just structure**

#### Git Commands:
```bash
# Create and switch to temp branch
git checkout -b phase1d-main-window-controller

# After creating files
git add oncutf/controllers/main_window_controller.py
git status
```

#### Files to Create:
```python
# oncutf/controllers/main_window_controller.py
"""
Module: main_window_controller.py

Author: Michael Economou
Date: 2025-12-16

MainWindowController: High-level orchestration controller.

This controller coordinates all sub-controllers (FileLoad, Metadata, Rename)
and manages complex workflows that involve multiple domains. It handles:
- Multi-controller workflows (e.g., load files → load metadata)
- Application-level state coordination
- Complex user actions that span multiple domains
- Event propagation between controllers

The controller is UI-agnostic and focuses on orchestration logic.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from oncutf.controllers.file_load_controller import FileLoadController
    from oncutf.controllers.metadata_controller import MetadataController
    from oncutf.controllers.rename_controller import RenameController
    from oncutf.core.application_context import ApplicationContext

logger = logging.getLogger(__name__)


class MainWindowController:
    """
    High-level orchestration controller.
    
    Coordinates FileLoadController, MetadataController, and RenameController
    to handle complex workflows that span multiple domains.
    
    Responsibilities:
    - Orchestrate multi-step workflows
    - Coordinate between sub-controllers
    - Manage application-level state
    - Handle complex user actions
    
    This controller does NOT:
    - Interact directly with UI widgets
    - Contain domain-specific logic (that's in sub-controllers)
    - Duplicate logic from sub-controllers
    """
    
    def __init__(
        self,
        app_context: "ApplicationContext",
        file_load_controller: "FileLoadController",
        metadata_controller: "MetadataController",
        rename_controller: "RenameController",
    ) -> None:
        """
        Initialize MainWindowController.
        
        Args:
            app_context: Application context with shared services
            file_load_controller: Controller for file loading operations
            metadata_controller: Controller for metadata operations
            rename_controller: Controller for rename operations
        """
        self._app_context = app_context
        self._file_load_controller = file_load_controller
        self._metadata_controller = metadata_controller
        self._rename_controller = rename_controller
        
        logger.info("[MainWindowController] Initialized")
    
    # TODO: Add orchestration methods in next steps
```

#### Validation:
```bash
# Check syntax
python -c "from oncutf.controllers.main_window_controller import MainWindowController; print('OK')"

# Run pytest (should still pass - no logic changed)
pytest -q

# Run ruff
ruff check oncutf/controllers/main_window_controller.py

# Check mypy
mypy oncutf/controllers/main_window_controller.py
```

#### Expected Results:
- ✅ Import successful
- ✅ All 549+ tests pass
- ✅ Ruff clean
- ✅ Mypy clean (or acceptable warnings)

#### Commit:
```bash
git add oncutf/controllers/main_window_controller.py
git commit -m "feat(controllers): add MainWindowController skeleton

- Create main orchestration controller
- Define responsibilities in docstring
- Add TYPE_CHECKING imports for sub-controllers
- No logic yet, just structure

Part of Phase 1D: MainWindowController"
```

---

### Step 1D.2: Identify orchestration methods in MainWindow (45 min)

#### Actions:
1. Read MainWindow and find methods that coordinate multiple managers
2. Look for methods that:
   - Call multiple managers in sequence
   - Handle complex workflows
   - Coordinate state across domains
3. Document them in `PHASE1D_METHODS_MAP.md`
4. Estimate complexity

#### Examples of Orchestration Methods:
```python
# Methods that coordinate multiple operations:
- load_files_and_metadata()     # Loads files, then metadata
- reload_files_after_rename()   # Complex post-rename workflow
- handle_drop_event()           # Coordinates drag, validation, load
- batch_operation_complete()    # Coordinates multiple services
- apply_filters_and_update()    # Filter + UI update coordination
```

#### Output File:
```markdown
# docs/PHASE1D_METHODS_MAP.md

## Orchestration Methods to Extract from MainWindow

### High Priority (must move):
1. `load_files_and_metadata()` - Coordinates FileLoad + Metadata
2. `reload_files_after_rename()` - Complex post-rename workflow
3. `handle_complex_drop()` - Multi-step drop handling

### Medium Priority (consider moving):
4. `apply_filters_with_state()` - Filter coordination
5. `batch_complete_workflow()` - Batch operation coordination

### Low Priority (may keep in MainWindow):
6. Simple UI update methods (pure UI, no orchestration)

### Analysis:
- Total methods to move: ~5-8
- Estimated lines: ~200-300
- Complexity: Medium (mostly coordination, less new logic)
```

#### Validation:
- Manual review of method list
- Confirm with existing controllers
- Check for duplicated responsibilities

#### Commit:
```bash
git add docs/PHASE1D_METHODS_MAP.md
git commit -m "docs(phase1d): document orchestration methods to extract

- Identify methods coordinating multiple controllers
- Classify by priority (high/medium/low)
- Estimate complexity and lines

Part of Phase 1D: MainWindowController"
```

---

### Step 1D.3: Implement first orchestration method (1 hour)

#### Actions:
1. Choose simplest orchestration method first (e.g., `load_files_and_metadata`)
2. Implement in MainWindowController
3. Keep MainWindow method intact (don't remove yet!)
4. Add proper error handling, logging, type hints
5. Write unit tests

#### Implementation Example:
```python
# In MainWindowController
async def load_files_and_metadata(
    self,
    file_paths: List[Path],
    load_metadata: bool = True,
) -> Dict[str, Any]:
    """
    Orchestrate file loading followed by metadata loading.
    
    This is a common workflow: user drops files, we load them,
    then immediately load their metadata.
    
    Args:
        file_paths: Paths to files to load
        load_metadata: Whether to load metadata after files
    
    Returns:
        dict: {
            'files_loaded': int,
            'metadata_loaded': int,
            'success': bool,
            'errors': List[str]
        }
    """
    logger.info(
        "[MainWindowController] Load files and metadata: %d paths",
        len(file_paths)
    )
    
    errors = []
    
    # Step 1: Load files
    try:
        file_result = await self._file_load_controller.load_files(file_paths)
        if not file_result['success']:
            errors.extend(file_result.get('errors', []))
            return {
                'files_loaded': 0,
                'metadata_loaded': 0,
                'success': False,
                'errors': errors
            }
    except Exception as e:
        logger.error("[MainWindowController] File load failed: %s", e)
        errors.append(f"File load error: {e}")
        return {
            'files_loaded': 0,
            'metadata_loaded': 0,
            'success': False,
            'errors': errors
        }
    
    # Step 2: Load metadata (if requested)
    metadata_count = 0
    if load_metadata and file_result['loaded_count'] > 0:
        try:
            meta_result = await self._metadata_controller.load_metadata_for_all()
            metadata_count = meta_result.get('loaded_count', 0)
            if not meta_result.get('success'):
                errors.extend(meta_result.get('errors', []))
        except Exception as e:
            logger.error("[MainWindowController] Metadata load failed: %s", e)
            errors.append(f"Metadata load error: {e}")
    
    return {
        'files_loaded': file_result['loaded_count'],
        'metadata_loaded': metadata_count,
        'success': True,
        'errors': errors
    }
```

#### Test File:
```python
# tests/test_main_window_controller.py
"""Tests for MainWindowController."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from oncutf.controllers.main_window_controller import MainWindowController


@pytest.fixture
def mock_controllers():
    """Create mock sub-controllers."""
    file_load = MagicMock()
    file_load.load_files = AsyncMock(return_value={
        'success': True,
        'loaded_count': 5,
        'errors': []
    })
    
    metadata = MagicMock()
    metadata.load_metadata_for_all = AsyncMock(return_value={
        'success': True,
        'loaded_count': 5,
        'errors': []
    })
    
    rename = MagicMock()
    
    return file_load, metadata, rename


@pytest.fixture
def controller(mock_controllers):
    """Create MainWindowController with mocks."""
    file_load, metadata, rename = mock_controllers
    app_context = MagicMock()
    
    return MainWindowController(
        app_context=app_context,
        file_load_controller=file_load,
        metadata_controller=metadata,
        rename_controller=rename
    )


@pytest.mark.asyncio
async def test_load_files_and_metadata_success(controller, mock_controllers):
    """Test successful file and metadata loading."""
    file_load, metadata, _ = mock_controllers
    
    paths = [Path("/test/file1.jpg"), Path("/test/file2.jpg")]
    result = await controller.load_files_and_metadata(paths)
    
    # Verify file loading was called
    file_load.load_files.assert_called_once_with(paths)
    
    # Verify metadata loading was called
    metadata.load_metadata_for_all.assert_called_once()
    
    # Verify result
    assert result['success'] is True
    assert result['files_loaded'] == 5
    assert result['metadata_loaded'] == 5
    assert len(result['errors']) == 0


@pytest.mark.asyncio
async def test_load_files_and_metadata_skip_metadata(controller, mock_controllers):
    """Test file loading without metadata."""
    file_load, metadata, _ = mock_controllers
    
    paths = [Path("/test/file1.jpg")]
    result = await controller.load_files_and_metadata(paths, load_metadata=False)
    
    # Verify file loading was called
    file_load.load_files.assert_called_once()
    
    # Verify metadata loading was NOT called
    metadata.load_metadata_for_all.assert_not_called()
    
    # Verify result
    assert result['success'] is True
    assert result['files_loaded'] == 5
    assert result['metadata_loaded'] == 0
```

#### Validation:
```bash
# Run new tests
pytest tests/test_main_window_controller.py -v

# Run all tests
pytest -q

# Check coverage (optional)
pytest --cov=oncutf.controllers.main_window_controller tests/test_main_window_controller.py

# Run ruff
ruff check oncutf/controllers/main_window_controller.py tests/test_main_window_controller.py

# Run mypy
mypy oncutf/controllers/main_window_controller.py
```

#### Expected Results:
- ✅ New tests pass
- ✅ All existing tests pass
- ✅ Coverage > 80%
- ✅ Ruff clean
- ✅ Mypy clean

#### Commit:
```bash
git add oncutf/controllers/main_window_controller.py tests/test_main_window_controller.py
git commit -m "feat(controllers): implement load_files_and_metadata in MainWindowController

- Add orchestration method for file + metadata loading workflow
- Coordinate FileLoadController and MetadataController
- Add comprehensive error handling and logging
- Write unit tests with mocks

Part of Phase 1D: MainWindowController"
```

---

### Step 1D.4: Wire MainWindowController to MainWindow (1 hour)

#### Actions:
1. Create MainWindowController instance in MainWindow.__init__()
2. Keep old methods intact
3. Add feature flag to switch between old/new code path
4. Test both code paths

#### Implementation:
```python
# In MainWindow.__init__() (near other controller initialization)

# Feature flag for Phase 1D
self._use_main_window_controller = True

# Create MainWindowController
from oncutf.controllers.main_window_controller import MainWindowController
self._main_window_controller = MainWindowController(
    app_context=self.app_context,
    file_load_controller=self._file_load_controller,
    metadata_controller=self._metadata_controller,
    rename_controller=self._rename_controller,
)

# In method that loads files and metadata (e.g., _on_files_dropped_complete)
if self._use_main_window_controller:
    # Use new orchestration controller
    result = await self._main_window_controller.load_files_and_metadata(
        file_paths=paths,
        load_metadata=True
    )
else:
    # Use old code (fallback)
    result = await self._old_load_files_and_metadata(paths)
```

#### Validation:
```bash
# Test with flag = True (new controller)
# 1. Launch app
python main.py

# 2. Drag & drop files
# 3. Verify files load and metadata loads
# 4. Check logs for [MainWindowController] messages

# Test with flag = False (old code)
# 1. Edit main_window.py: self._use_main_window_controller = False
# 2. Launch app
python main.py

# 3. Drag & drop files
# 4. Verify behavior identical

# Run all tests
pytest -q

# Run ruff
ruff check .

# Check app launches
python main.py --version  # Quick launch test
```

#### Expected Results:
- ✅ App launches with both flag states
- ✅ File + metadata loading works with both paths
- ✅ Logs show controller usage when flag = True
- ✅ All tests pass
- ✅ Ruff clean

#### Commit:
```bash
git add oncutf/ui/main_window.py
git commit -m "feat(ui): wire MainWindowController to MainWindow (behind flag)

- Create MainWindowController instance in MainWindow.__init__
- Add feature flag _use_main_window_controller
- Integrate load_files_and_metadata orchestration
- Keep old code path as fallback for testing

Part of Phase 1D: MainWindowController"
```

---

### Step 1D.5: Remove old orchestration code from MainWindow (30 min)

#### Actions:
1. Remove feature flag
2. Remove old orchestration methods (e.g., `_old_load_files_and_metadata`)
3. Update all call sites to use MainWindowController
4. Clean up unused imports

#### Implementation:
```python
# Remove flag
# DELETE: self._use_main_window_controller = True

# Remove old methods
# DELETE: def _old_load_files_and_metadata(self, paths): ...

# Update call sites (remove if statement)
# BEFORE:
if self._use_main_window_controller:
    result = await self._main_window_controller.load_files_and_metadata(paths)
else:
    result = await self._old_load_files_and_metadata(paths)

# AFTER:
result = await self._main_window_controller.load_files_and_metadata(paths)
```

#### Validation:
```bash
# Run all tests
pytest -q

# Check app launches
python main.py

# Manual test: drag & drop files
# Verify file + metadata loading works

# Check git diff for expected deletions
git diff oncutf/ui/main_window.py

# Run ruff
ruff check .

# Run mypy (optional)
mypy oncutf/ui/main_window.py
```

#### Expected Results:
- ✅ All tests pass
- ✅ App launches and works
- ✅ Git diff shows old code removed
- ✅ Ruff clean
- ✅ No regressions

#### Commit:
```bash
git add oncutf/ui/main_window.py
git commit -m "refactor(ui): remove old orchestration code from MainWindow

- Remove feature flag _use_main_window_controller
- Remove old _old_load_files_and_metadata method
- All orchestration now through MainWindowController
- Clean up unused imports

Part of Phase 1D: MainWindowController"
```

---

### Step 1D.6: Add remaining orchestration methods (1.5 hours)

#### Actions:
1. Implement remaining orchestration methods from PHASE1D_METHODS_MAP.md
2. Focus on high and medium priority methods
3. Write tests for each new method
4. Update MainWindow to use new methods

#### Methods to Implement:
```python
# In MainWindowController

async def reload_files_after_rename(
    self,
    renamed_paths: List[Path],
    preserve_selection: bool = True
) -> Dict[str, Any]:
    """
    Orchestrate post-rename workflow.
    
    After rename execution, reload affected files, restore UI state,
    and update metadata.
    """
    # Implementation...

async def handle_batch_operation_complete(
    self,
    operation_type: str,
    results: Dict[str, Any]
) -> None:
    """
    Orchestrate post-batch-operation workflows.
    
    Coordinates UI updates, notifications, and state restoration
    after batch operations complete.
    """
    # Implementation...

# Add 2-3 more methods as needed from PHASE1D_METHODS_MAP.md
```

#### Validation (for each method):
```bash
# Run tests for new method
pytest tests/test_main_window_controller.py::test_new_method -v

# Run all tests
pytest -q

# Manual test (if applicable)
python main.py
# Test the specific workflow

# Run ruff
ruff check oncutf/controllers/main_window_controller.py
```

#### Expected Results:
- ✅ Each new method has tests
- ✅ All tests pass
- ✅ Manual testing confirms functionality
- ✅ Ruff clean

#### Commit (one per method or grouped):
```bash
git add oncutf/controllers/main_window_controller.py tests/test_main_window_controller.py
git commit -m "feat(controllers): add reload_files_after_rename orchestration

- Implement post-rename workflow coordination
- Handle file reload, state restoration, metadata update
- Add comprehensive tests
- Update MainWindow to use new method

Part of Phase 1D: MainWindowController"

# Repeat for other methods...
```

---

### Step 1D.7: Final cleanup & documentation (45 min)

#### Actions:
1. Review MainWindowController for any missing docstrings
2. Add module-level documentation
3. Remove any unused code or imports
4. Update MainWindow docstring to reflect new architecture
5. Run full test suite
6. Run linters

#### Tasks:
```python
# 1. Verify all methods have docstrings
# 2. Add type hints where missing
# 3. Remove any TODO comments that are done
# 4. Check for unused imports

# In MainWindowController module docstring, add:
"""
...

Architecture:
    MainWindow (UI) → MainWindowController (orchestration)
                    ├→ FileLoadController (file operations)
                    ├→ MetadataController (metadata operations)
                    └→ RenameController (rename operations)

Each controller is UI-agnostic and testable independently.
MainWindowController coordinates complex workflows that span multiple domains.
"""
```

#### Validation:
```bash
# Run full test suite
pytest tests/ -v

# Check test coverage for MainWindowController
pytest --cov=oncutf.controllers.main_window_controller \
       --cov-report=term-missing \
       tests/test_main_window_controller.py

# Run ruff on entire project
ruff check .

# Run mypy on controllers
mypy oncutf/controllers/

# Launch app and smoke test
python main.py
# Test: drag files, load metadata, preview rename, execute rename

# Check MainWindow line count reduction
wc -l oncutf/ui/main_window.py
# Should be reduced from original count
```

#### Expected Results:
- ✅ All 549+ tests pass
- ✅ MainWindowController coverage > 85%
- ✅ Ruff clean
- ✅ Mypy clean (or acceptable warnings)
- ✅ App works correctly
- ✅ MainWindow line count reduced

#### Commit:
```bash
git add oncutf/controllers/main_window_controller.py \
        oncutf/ui/main_window.py \
        tests/test_main_window_controller.py

git commit -m "chore(phase1d): final cleanup for MainWindowController

- Complete docstrings and type hints
- Remove unused code and imports
- Update architecture documentation
- Verify test coverage > 85%
- All linters clean

Phase 1D: MainWindowController ✅ COMPLETE"
```

---

### Step 1D.8: Merge to main and cleanup (15 min)

#### Actions:
1. Final validation on temp branch
2. Merge to main
3. Delete temp branch
4. Update PHASE1_EXECUTION_PLAN.md status

#### Git Commands:
```bash
# Final checks on temp branch
git status
git log --oneline -10

# Switch to main
git checkout main

# Merge temp branch (fast-forward if possible)
git merge phase1d-main-window-controller

# Verify merge
git log --oneline -10

# Delete temp branch
git branch -d phase1d-main-window-controller

# Verify branch deleted
git branch
```

#### Final Validation:
```bash
# On main branch, run all tests
pytest -q

# Run ruff
ruff check .

# Launch app
python main.py

# Quick smoke test
# - Drag & drop files
# - Load metadata
# - Preview rename
# - Execute rename
```

#### Update Status:
```bash
# Edit docs/PHASE1_EXECUTION_PLAN.md
# Change status from "READY TO START" to "✅ COMPLETE"
# Update Phase 1D section with completion date

git add docs/PHASE1_EXECUTION_PLAN.md
git commit -m "docs: mark Phase 1D as complete

Phase 1D (MainWindowController) completed successfully:
- MainWindowController created with orchestration logic
- All sub-controllers integrated
- MainWindow simplified
- All tests passing
- No regressions

Date: 2025-12-16"
```

---

## Summary of Commits

| Step | Commit Message | Type |
|------|---------------|------|
| 1D.1 | `feat(controllers): add MainWindowController skeleton` | feat |
| 1D.2 | `docs(phase1d): document orchestration methods to extract` | docs |
| 1D.3 | `feat(controllers): implement load_files_and_metadata in MainWindowController` | feat |
| 1D.4 | `feat(ui): wire MainWindowController to MainWindow (behind flag)` | feat |
| 1D.5 | `refactor(ui): remove old orchestration code from MainWindow` | refactor |
| 1D.6a | `feat(controllers): add reload_files_after_rename orchestration` | feat |
| 1D.6b | `feat(controllers): add batch_operation_complete orchestration` | feat |
| 1D.7 | `chore(phase1d): final cleanup for MainWindowController` | chore |
| 1D.8 | `docs: mark Phase 1D as complete` | docs |

**Total:** 8-9 atomic commits

---

## Time Estimates

| Step | Description | Time |
|------|-------------|------|
| 1D.1 | Create skeleton | 30 min |
| 1D.2 | Document methods | 45 min |
| 1D.3 | First method + tests | 1 hour |
| 1D.4 | Wire to MainWindow | 1 hour |
| 1D.5 | Remove old code | 30 min |
| 1D.6 | Remaining methods | 1.5 hours |
| 1D.7 | Final cleanup | 45 min |
| 1D.8 | Merge & update docs | 15 min |
| **Total** | | **6 hours** |

**Buffer:** 1 hour for unexpected issues  
**Total with buffer:** 7 hours (~1 day)

---

## Safety Checklist (After Each Step)

- [ ] All tests pass (`pytest -q`)
- [ ] Ruff clean (`ruff check .`)
- [ ] App launches (`python main.py`)
- [ ] Manual smoke test (drag files, load metadata, rename)
- [ ] Git commit with clear message
- [ ] No commented-out code remains
- [ ] All docstrings present

---

## Rollback Plan

If any step breaks:

1. **Check git log:** `git log --oneline -5`
2. **Undo last commit:** `git reset --hard HEAD~1`
3. **Review what broke:** Check test output, error messages
4. **Fix or skip:** Make targeted fix OR skip this step
5. **Retry:** Try again with safer approach

**Nuclear option:** Return to main branch
```bash
git checkout main
git branch -D phase1d-main-window-controller
# Start over from 1D.1
```

---

## Success Criteria

**Phase 1D Complete when:**
- ✅ MainWindowController exists and orchestrates sub-controllers
- ✅ Complex workflows moved from MainWindow to MainWindowController
- ✅ MainWindow uses MainWindowController for orchestration
- ✅ Old orchestration code removed from MainWindow
- ✅ All tests pass (549+)
- ✅ No regressions in functionality
- ✅ Test coverage > 85% for MainWindowController
- ✅ Ruff clean
- ✅ Code is more maintainable and testable

---

## Next Steps After Phase 1D

**Phase 1 will be complete!** 🎉

Then:
1. Review entire Phase 1 changes
2. Update CHANGELOG.md
3. Consider Phase 2 (if planned)
4. Celebrate successful refactoring!

---

## Ready to Start?

**Command to begin:**
```bash
git checkout -b phase1d-main-window-controller
```

Let's go! 🚀
