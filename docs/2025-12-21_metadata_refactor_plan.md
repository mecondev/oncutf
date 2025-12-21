# Metadata Refactoring Plan

**Document Version:** 1.0  
**Created:** 2025-12-21  
**Author:** Michael Economou  
**Status:** Active  

---

## Executive Summary

This document is the **single source of truth** for the metadata subsystem refactoring effort.

### Context

- The independent Antigravity audit identified `unified_metadata_manager.py` (~2050 LOC, 69 methods) as the highest-priority technical debt.
- This module is a "god class" that handles:
  - Metadata loading (single/batch, streaming, parallel)
  - Caching (memory and disk via cache helper)
  - Companion file handling (XMP, sidecar metadata)
  - Keyboard shortcut handlers for metadata operations
  - Progress dialog orchestration
  - Hash loading coordination
  - Metadata saving workflow
  - Structured metadata access API
- A partial decomposition already exists in `oncutf/core/metadata/`:
  - `metadata_cache_service.py` (120 LOC)
  - `companion_metadata_handler.py` (236 LOC)
  - `metadata_reader.py` (289 LOC)
  - `metadata_writer.py` (266 LOC)
- Tooling is stable: `mypy .` passes, `ruff check .` reports only whitespace issues.

### Goals

1. Reduce `unified_metadata_manager.py` from ~2050 LOC to <500 LOC (facade only)
2. Extract focused, testable modules with single responsibilities
3. Maintain backward compatibility (external API unchanged)
4. Improve test coverage for metadata subsystem
5. Enable future strict typing incrementally

---

## Phase Overview

| Phase | Name | Goal | Est. Effort | Status |
|-------|------|------|-------------|--------|
| 0 | Pre-clean & noise reduction | Clean codebase, handle generated files | 1-2 hours | ✅ DONE |
| 1 | Decompose unified_metadata_manager | Extract responsibilities, keep facade | 4-8 hours | ✅ DONE |
| 2 | Internal cleanup & alignment | Reduce coupling, improve APIs | 2-4 hours | Pending |
| 3 | Typing & mypy expansion | Incremental strict typing | 2-4 hours | Pending |
| 4 | Deferred design discussion | Analysis & documentation only | 1-2 hours | Pending |

---

## PHASE 0 — Pre-clean & Noise Reduction

### Goals
- Establish clean baseline before architectural changes
- Handle generated artifacts
- Fix trivial linting issues

### Scope

#### IN SCOPE
- Fix whitespace issues reported by ruff (W293 in ui_manager.py, file_tree_view.py, etc.)
- Handle `fonts_rc.py` and `fonts_rc_temp_backup.py`:
  - These are PyQt5 Resource Compiler generated files (100K+ lines)
  - Decision: **Exclude from linting** via ruff configuration
  - Rationale: Generated code should not be manually edited or linted
- Verify mypy passes cleanly
- Verify pytest passes

#### OUT OF SCOPE
- Any architectural changes
- Refactoring logic
- Adding new features

### Tasks

- [x] Add `fonts_rc*.py` to ruff exclude patterns in `pyproject.toml`
- [x] Fix W293 whitespace issues in:
  - [x] `oncutf/core/ui_managers/ui_manager.py`
  - [x] `oncutf/ui/widgets/file_tree_view.py`
  - [x] `oncutf/ui/widgets/metadata_tree_view.py`
  - [x] `oncutf/ui/widgets/preview_tables_view.py`
- [x] Run quality gates and confirm all pass

### Validation Checklist

- [x] `ruff check .` — 0 errors, 0 warnings
- [x] `mypy .` — passes (300 source files)
- [x] `pytest` — all tests pass (6 skipped - stress tests)
- [x] No functional changes to application behavior

### Branch

```
refactor/2025-12-21/metadata-phase-0
```

### Completion Criteria

All quality gates pass. Clean baseline established.

---

## PHASE 1 — Decompose unified_metadata_manager (HIGHEST PRIORITY)

### Goals
- Extract focused responsibilities from the god class
- Keep `unified_metadata_manager.py` as a **thin facade** temporarily
- Use delegation pattern (not big-bang rewrite)
- External behavior must remain unchanged

### Current State Analysis

The `unified_metadata_manager.py` (2053 LOC, 69 methods) handles multiple concerns:

| Responsibility | Methods | Target Module |
|----------------|---------|---------------|
| Keyboard shortcuts | `shortcut_load_metadata`, `shortcut_load_extended_metadata`, `shortcut_load_metadata_all`, `shortcut_load_extended_metadata_all` | `metadata_shortcut_handler.py` |
| Loading orchestration | `load_metadata_for_items`, `load_metadata_streaming`, `_load_single_file_metadata`, `_load_multiple_files_metadata` | `metadata_loader.py` |
| Progress dialogs | `_show_metadata_progress_dialog`, `_show_hash_progress_dialog`, `_on_metadata_progress`, etc. | `metadata_progress_handler.py` |
| Hash operations | `load_hashes_for_files`, `check_cached_hash`, `has_cached_hash`, `_start_hash_loading*`, `_on_hash_*` | Existing `hash/` package |
| Metadata saving | `save_metadata_for_selected`, `save_all_modified_metadata`, `_save_metadata_files`, `_show_save_results` | `metadata_writer.py` (extend) |
| Structured access | `get_structured_metadata`, `process_and_store_metadata`, `get_field_value`, etc. | `structured_metadata_manager.py` (existing) |
| Companion handling | `_enhance_metadata_with_companions` | `companion_metadata_handler.py` (existing) |
| Cache access | `check_cached_metadata`, `has_cached_metadata`, `initialize_cache_helper` | `metadata_cache_service.py` (existing) |

### Scope

#### IN SCOPE
- Create new module: `oncutf/core/metadata/metadata_shortcut_handler.py`
  - Extract all `shortcut_*` methods
  - Handle keyboard modifier state detection
- Create new module: `oncutf/core/metadata/metadata_loader.py`
  - Extract loading orchestration logic
  - Handle single/batch/streaming modes
- Create new module: `oncutf/core/metadata/metadata_progress_handler.py`
  - Extract progress dialog creation and callbacks
  - Handle progress signal routing
- Extend existing modules as needed:
  - `metadata_writer.py` — add save workflow methods
  - `metadata_cache_service.py` — add any missing cache methods
- Update `unified_metadata_manager.py` to delegate to extracted modules
- Maintain all existing public APIs (backward compatibility)

#### OUT OF SCOPE
- Removing `unified_metadata_manager.py` entirely (it becomes facade)
- Changing external behavior or API signatures
- Refactoring hash operations (separate concern)
- UI changes
- Adding new features

### Extraction Strategy

**Step 1: Shortcut Handler** (lowest coupling)
```python
# oncutf/core/metadata/metadata_shortcut_handler.py
class MetadataShortcutHandler:
    """Handles keyboard shortcuts for metadata operations."""
    
    def __init__(self, metadata_manager, parent_window):
        self._manager = metadata_manager
        self._window = parent_window
    
    def shortcut_load_metadata(self) -> None: ...
    def shortcut_load_extended_metadata(self) -> None: ...
    def shortcut_load_metadata_all(self) -> None: ...
    def shortcut_load_extended_metadata_all(self) -> None: ...
    def determine_metadata_mode(self, modifier_state) -> tuple[bool, bool]: ...
    def should_use_extended_metadata(self, modifier_state) -> bool: ...
```

**Step 2: Progress Handler** (UI coordination)
```python
# oncutf/core/metadata/metadata_progress_handler.py
class MetadataProgressHandler:
    """Handles progress dialogs and callbacks for metadata operations."""
    
    def show_metadata_progress_dialog(self, ...) -> None: ...
    def show_hash_progress_dialog(self, ...) -> None: ...
    def on_metadata_progress(self, current, total) -> None: ...
    def on_hash_progress(self, current, total) -> None: ...
```

**Step 3: Loader** (core business logic)
```python
# oncutf/core/metadata/metadata_loader.py
class MetadataLoader:
    """Orchestrates metadata loading operations."""
    
    def load_metadata_for_items(self, items, use_extended, batch_mode) -> None: ...
    def load_metadata_streaming(self, items, use_extended) -> None: ...
    def _load_single_file_metadata(self, ...) -> dict: ...
    def _load_multiple_files_metadata(self, ...) -> None: ...
```

**Step 4: Update facade**
```python
# unified_metadata_manager.py (reduced to ~400-500 LOC)
class UnifiedMetadataManager(QObject):
    """Facade for metadata operations. Delegates to specialized handlers."""
    
    def __init__(self, parent_window=None):
        self._shortcut_handler = MetadataShortcutHandler(self, parent_window)
        self._progress_handler = MetadataProgressHandler(self, parent_window)
        self._loader = MetadataLoader(self, parent_window)
        # ... other handlers
    
    # Public API - delegates to handlers
    def shortcut_load_metadata(self) -> None:
        self._shortcut_handler.shortcut_load_metadata()
    
    # ... etc
```

### Tasks

- [x] Create `metadata_shortcut_handler.py` with extracted shortcut methods (~330 LOC)
- [x] Create `metadata_progress_handler.py` with progress dialog logic (~300 LOC)
- [x] Create `metadata_loader.py` with loading orchestration (~530 LOC)
- [x] Update `metadata/__init__.py` exports
- [x] Refactor `unified_metadata_manager.py` to delegate (facade pattern)
- [x] Update imports throughout codebase if needed
- [x] Fix test patch target in `test_save_cancellation.py` (ProgressDialog import changed)
- [ ] Add unit tests for new modules (deferred to Phase 2)
- [x] Run quality gates

### Validation Checklist

- [x] `ruff check .` — passes
- [x] `mypy .` — passes (303 source files)
- [x] `pytest` — all tests pass (6 skipped stress tests)
- [x] `unified_metadata_manager.py` reduced from 2053 → 821 LOC (60% reduction)
- [ ] All existing functionality works (manual smoke test)
- [x] No external API changes

### Phase 1 Results Summary

| Metric | Before | After |
|--------|--------|-------|
| `unified_metadata_manager.py` LOC | 2053 | 821 |
| Number of methods in facade | 69 | ~30 (delegating) |
| New modules created | 0 | 3 |
| Total new code LOC | 0 | ~1160 |
| Test failures | 0 | 0 |

**New modules created:**
- `oncutf/core/metadata/metadata_shortcut_handler.py` — Keyboard shortcuts (M, Ctrl+M, Shift+M)
- `oncutf/core/metadata/metadata_progress_handler.py` — Progress dialog management
- `oncutf/core/metadata/metadata_loader.py` — Loading orchestration (single/batch/streaming)

### Branch

```
refactor/2025-12-21/metadata-phase-1
```

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Use TYPE_CHECKING imports, forward references |
| Signal/slot breakage | Test Qt signals after extraction |
| Thread safety | Maintain existing thread patterns |
| Missing edge cases | Run full test suite, manual smoke test |

---

## PHASE 2 — Internal Cleanup & Responsibility Alignment

### Goals
- Reduce cross-coupling between metadata services
- Clarify ownership of caching, IO, and transformation logic
- Improve internal naming and APIs
- Prepare for stricter typing

### Scope

#### IN SCOPE
- Review and consolidate existing `metadata/` modules
- Clarify responsibilities:
  - `MetadataCacheService` — memory/disk caching only
  - `MetadataLoader` — orchestration (single/batch/streaming)
  - `MetadataWriter` — metadata writing (ExifTool interaction)
  - `CompanionMetadataHandler` — XMP/sidecar handling
- Remove any remaining duplication
- Improve docstrings and internal documentation

#### OUT OF SCOPE
- External API changes
- Performance optimization
- New features
- UI changes

### Tasks

- [x] Review existing modules for duplication
- [x] Remove redundant `MetadataReader` (functionality in `MetadataLoader`)
- [x] Update `__init__.py` exports
- [x] Improve docstrings in all metadata modules
- [x] Run quality gates

### Phase 2 Results Summary

| Action | Details |
|--------|---------|
| Removed `MetadataReader` | Redundant with `MetadataLoader`, was not used anywhere |
| Updated exports | Removed from `__init__.py` and `unified_metadata_manager.py` |
| Updated docstrings | Added Updated date and expanded responsibilities |
| Source files | 302 (down from 303 - removed metadata_reader.py) |

### Validation Checklist

- [x] `ruff check .` — passes
- [x] `mypy .` — passes (302 source files)
- [x] `pytest` — all tests pass (6 skipped stress tests)
- [x] Code review: clear responsibilities

### Branch

```
refactor/2025-12-21/metadata-phase-2
```

---

## PHASE 3 — Typing & mypy Expansion (Incremental)

### Goals
- Gradually enable stricter mypy coverage
- Start with service-layer metadata modules
- Do NOT enable strict typing for Qt/UI-heavy modules yet

### Scope

#### IN SCOPE
- Remove `ignore_errors` for well-typed metadata modules:
  - `oncutf/core/metadata/metadata_cache_service.py`
  - `oncutf/core/metadata/metadata_reader.py`
  - `oncutf/core/metadata/metadata_writer.py`
  - `oncutf/core/metadata/metadata_loader.py` (new)
  - `oncutf/core/metadata/metadata_shortcut_handler.py` (new)
- Add type annotations where missing
- Fix any mypy errors that surface

#### OUT OF SCOPE
- `unified_metadata_manager.py` (still has Qt noise)
- UI modules
- Adding `disallow_untyped_defs = true` globally

### Approach

Add to `pyproject.toml`:
```toml
[[tool.mypy.overrides]]
module = [
    "oncutf.core.metadata.metadata_cache_service",
    "oncutf.core.metadata.metadata_reader",
    "oncutf.core.metadata.metadata_writer",
    "oncutf.core.metadata.metadata_loader",
    "oncutf.core.metadata.metadata_shortcut_handler",
    "oncutf.core.metadata.metadata_progress_handler",
]
ignore_errors = false
warn_return_any = true
check_untyped_defs = true
```

### Tasks

- [ ] Add type annotations to new Phase 1 modules
- [ ] Update mypy configuration
- [ ] Fix any mypy errors
- [ ] Run quality gates

### Validation Checklist

- [ ] `ruff check .` — passes
- [ ] `mypy .` — passes with new strict modules
- [ ] `pytest` — all tests pass

### Branch

```
refactor/2025-12-21/metadata-phase-3
```

---

## PHASE 4 — Deferred Design Discussion (NO IMPLEMENTATION)

### Goals
- Analyze and document architectural considerations
- Inform future refactoring decisions
- This phase is **analysis and documentation only**

### Topics to Analyze

#### 1. FileEntry vs FileItem Responsibilities

Current state:
- `FileItem` appears to be the primary file representation
- `FileEntry` may be redundant or overlap
- Need to document:
  - Where each is used
  - What data each holds
  - Whether consolidation is desirable

#### 2. Domain Model Direction

Questions to answer:
- Should metadata be part of FileItem or separate?
- How should caching relate to the domain model?
- What is the ideal flow: load → cache → transform → display?

#### 3. Future Considerations

- Event-driven architecture for metadata changes?
- Async/await patterns for metadata loading?
- Plugin architecture for metadata sources?

### Tasks

- [ ] Document FileEntry vs FileItem usage
- [ ] Create architecture decision record (ADR) for domain model
- [ ] List future improvement opportunities
- [ ] No code changes in this phase

### Validation Checklist

- [ ] Documentation created
- [ ] No code changes
- [ ] Quality gates still pass

### Branch

```
refactor/2025-12-21/metadata-phase-4
```

---

## Workflow Rules Summary (Non-Negotiable)

For **each phase**:

1. **Create dedicated branch**
   - Format: `refactor/YYYY-MM-DD/<short-description>`

2. **Implement only current phase scope**

3. **Quality gates must pass**:
   ```bash
   ruff check .
   mypy .
   pytest
   ```

4. **If gate fails**: Fix issues, do NOT weaken configuration

5. **Update this document**:
   - Mark phase completed
   - Note key changes
   - Note follow-ups

6. **Commit with clear message**:
   ```
   refactor: complete metadata phase N - <summary>
   ```

7. **Merge into main**:
   ```bash
   git merge --no-ff <branch>
   ```

8. **Push main**

---

## Parking Lot (Future Discussion)

Items identified but explicitly out of scope:

1. **Hash operations refactoring** — separate effort, has its own package
2. **Performance optimization** — measure first, then optimize
3. **Async metadata loading** — requires careful thread safety analysis
4. **Plugin architecture** — future feature, not current debt
5. **UI-side caching** — belongs to UI refactoring, not metadata

---

## Progress Tracking

### Phase Status

| Phase | Status | Started | Completed | Notes |
|-------|--------|---------|-----------|-------|
| 0 | ✅ Completed | 2025-12-21 | 2025-12-21 | Clean baseline established |
| 1 | ✅ Completed | 2025-12-21 | 2025-12-21 | 60% LOC reduction, 3 modules extracted |
| 2 | ✅ Completed | 2025-12-21 | 2025-12-21 | Removed redundant MetadataReader |
| 3 | Not Started | - | - | - |
| 4 | Not Started | - | - | - |

### Quality Gate History

| Date | Phase | ruff | mypy | pytest | Notes |
|------|-------|------|------|--------|-------|
| 2025-12-21 | Pre | ⚠️ W293 | ✅ | ✅ | Baseline before Phase 0 |
| 2025-12-21 | 0 | ✅ | ✅ | ✅ | All gates pass, clean baseline |
| 2025-12-21 | 1 | ✅ | ✅ | ✅ | 303 source files, 6 tests skipped (stress) |
| 2025-12-21 | 2 | ✅ | ✅ | ✅ | 302 source files (removed metadata_reader.py) |

---

## Appendix A: Module Sizes

### Before Phase 1

| Module | LOC | Methods |
|--------|-----|---------|
| `unified_metadata_manager.py` | 2053 | 69 |
| `structured_metadata_manager.py` | ~600 | ~20 |
| `metadata_cache_service.py` | 120 | ~8 |
| `companion_metadata_handler.py` | 236 | ~10 |
| `metadata_reader.py` | 289 | ~12 |
| `metadata_writer.py` | 266 | ~10 |

### After Phase 1 (Actual)

| Module | LOC | Notes |
|--------|-----|-------|
| `unified_metadata_manager.py` (facade) | 821 | 60% reduction from 2053 |
| `metadata_shortcut_handler.py` (new) | ~330 | Keyboard shortcuts |
| `metadata_loader.py` (new) | ~530 | Loading orchestration |
| `metadata_progress_handler.py` (new) | ~300 | Progress dialogs |

---

## Appendix B: Key Files Reference

```
oncutf/core/
├── unified_metadata_manager.py      # Target for decomposition
├── structured_metadata_manager.py   # Structured access layer
├── metadata/                        # Extracted modules
│   ├── __init__.py
│   ├── companion_metadata_handler.py
│   ├── metadata_cache_service.py
│   ├── metadata_reader.py
│   └── metadata_writer.py
├── metadata_command_manager.py      # Command/undo for metadata
├── metadata_operations_manager.py   # Operations coordinator
└── metadata_staging_manager.py      # Staging for save
```

---

*End of document*
