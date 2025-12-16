# Roadmap — OnCutF Development

**Last Updated:** 2025-12-16  
**Current Phase:** Phase 1 COMPLETE ✅

---

## Overview

OnCutF is undergoing a structured refactoring process to improve code organization, maintainability, and extensibility. This roadmap tracks progress across multiple phases.

---

## Phase Status

### ✅ Phase 0: Package Structure Migration (COMPLETE)
**Goal:** Move all application code under `oncutf/` package for better organization  
**Status:** **COMPLETE** (Dec 15, 2025)  
**Duration:** 10 steps, 11 commits

**Completed Steps:**
- [x] Created `oncutf/` package structure
- [x] Moved `models/` → `oncutf/models/` (5 files)
- [x] Moved `modules/` → `oncutf/modules/` (8 files)
- [x] Moved `utils/` → `oncutf/utils/` (55 files)
- [x] Moved `widgets/` → `oncutf/ui/widgets/` (40 files)
- [x] Moved `widgets/mixins/` → `oncutf/ui/mixins/` (7 files)
- [x] Moved `core/` → `oncutf/core/` (60 files)
- [x] Moved `main_window.py` → `oncutf/ui/main_window.py`
- [x] Moved `config.py` → `oncutf/config.py`
- [x] Created `oncutf/__main__.py` for module execution
- [x] Verified all 549 tests passing
- [x] Updated all imports to `oncutf.*` pattern

**Results:**
- Total files migrated: ~175 files (~100k LOC)
- All 549 tests passing
- Zero logic changes (move-only refactoring)
- Clean git history (11 atomic commits)
- Both entry points working: `python main.py` and `python -m oncutf`

**See:** [ARCH_REFACTOR_PLAN.md](ARCH_REFACTOR_PLAN.md), [EXECUTION_ROADMAP.md](EXECUTION_ROADMAP.md)

---

### ✅ Phase 1: Controllers Architecture (COMPLETE)
**Goal:** Separate UI from business logic with MVC-inspired controller layer  
**Status:** **COMPLETE** (Dec 16, 2025)  
**Duration:** 4 sub-phases (1A-1D), 8 commits total

**Completed Sub-phases:**

#### Phase 1A: FileLoadController ✅
- Created FileLoadController for file loading orchestration
- Methods: `load_files_from_drop()`, `load_folder()`, `clear_files()`
- Separated drag & drop logic from MainWindow
- 11 comprehensive tests (100% coverage)

#### Phase 1B: MetadataController ✅
- Created MetadataController for metadata operations
- Methods: `load_metadata()`, `reload_metadata()`, `clear_metadata_cache()`
- Orchestrates metadata loading with progress tracking
- 13 comprehensive tests covering all workflows

#### Phase 1C: RenameController ✅
- Created RenameController for rename workflows
- Methods: `preview_rename()`, `execute_rename()`, `update_preview()`
- Handles rename preview, validation, and execution
- 16 comprehensive tests with conflict scenarios

#### Phase 1D: MainWindowController ✅
- Created MainWindowController for high-level orchestration
- Methods: `restore_last_session_workflow()`, `coordinate_shutdown_workflow()`
- Coordinates FileLoad, Metadata, and Rename controllers
- 17 comprehensive tests for multi-service workflows

**Results:**
- 4 new controllers in `oncutf/controllers/`
- 57 new tests (549 → 592 tests, 100% pass rate)
- Testable architecture (controllers independent of Qt UI)
- Clean separation of concerns (UI → Controllers → Services)
- Comprehensive documentation (4 execution plans, 3 methods maps, guides)
- Zero regressions (all existing functionality preserved)

**See:** [PHASE1_EXECUTION_PLAN.md](PHASE1_EXECUTION_PLAN.md), [PHASE1D_COMPLETE.md](PHASE1D_COMPLETE.md), [PHASE1_SUMMARY.md](PHASE1_SUMMARY.md)

---

### 🔄 Phase 2: State Management Fix (READY)
**Goal:** Single source of truth for file state, fix counter conflicts  
**Status:** Ready to begin (pending approval)

**Planned Improvements:**
- [ ] Consolidate FileStore with FileGroup support
- [ ] Create StateCoordinator for synchronization
- [ ] Implement event system for state changes
- [ ] Fix counter conflicts after multi-folder imports
- [ ] Fix stale preview states
- [ ] Integrate preview engine with unified state

**Original Source:** ARCH_REFACTOR_PLAN.md "Phase 1: State Management Fix"

---

### 📋 Phase 3: UI/UX Improvements (PLANNED)
**Goal:** Enhance user interface and experience  
**Status:** Planned

**Planned Tasks:**
- [ ] Improve splash screen feedback
- [ ] Enhance progress indicators
- [ ] Refine metadata display
- [ ] Optimize column management UI
- [ ] Improve error messaging

---

### 🔧 Phase 4: Core Logic Improvements (PLANNED)
**Goal:** Refactor and optimize core business logic  
**Status:** Planned

**Planned Tasks:**
- [ ] Optimize metadata loading
- [ ] Enhance rename engine
- [ ] Improve caching strategies
- [ ] Refactor file operations

---

### 🎯 Phase 5: Final Polish (PLANNED)
**Goal:** Performance optimization and final cleanup  
**Status:** Planned

**Planned Tasks:**
- [ ] Performance profiling
- [ ] Memory optimization
- [ ] Documentation updates
- [ ] User guide improvements

---

## Historical Achievements

### Phase 1: Controllers Architecture (2025-12-16)
- **FileLoadController:** File loading orchestration (11 tests)
- **MetadataController:** Metadata operations coordination (13 tests)
- **RenameController:** Rename workflows management (16 tests)
- **MainWindowController:** High-level multi-service orchestration (17 tests)
- **Test Coverage:** Added 57 new tests (549 → 592, 100% pass rate)
- **Architecture:** Clean MVC-inspired separation (UI → Controllers → Services)

### Phase 0: Package Structure Migration (2025-12-15)
- **Package Migration:** Moved ~175 files to `oncutf/` package
- **Test Coverage:** Maintained 549 tests passing throughout
- **Zero Regressions:** Move-only refactoring with no logic changes

### FileTableView Decomposition (2025-12-08)
- **Mixin Extraction:** Reduced FileTableView from ~2069 LOC to 976 LOC
- **SelectionMixin:** Windows Explorer-style selection (486 lines, 12 methods)
- **DragDropMixin:** Drag-and-drop functionality (365 lines, 9 methods)
- **ColumnManagementMixin:** Column management (~1179 LOC)
- **Test Coverage:** Maintained 460 tests passing (100% compatibility)

---

## Documentation

### Core Documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
- [ARCH_REFACTOR_PLAN.md](ARCH_REFACTOR_PLAN.md) - Detailed refactoring plan
- [EXECUTION_ROADMAP.md](EXECUTION_ROADMAP.md) - Step-by-step execution tracking (Phase 0)
- [README.md](README.md) - Main project documentation

### Phase 1 Documentation
- [PHASE1_EXECUTION_PLAN.md](PHASE1_EXECUTION_PLAN.md) - Phase 1 overall execution plan
- [PHASE1_SUMMARY.md](PHASE1_SUMMARY.md) - Phase 1 complete summary (1A-1D)
- [PHASE1A_METHODS_MAP.md](PHASE1A_METHODS_MAP.md) - FileLoadController methods
- [PHASE1B_METHODS_MAP.md](PHASE1B_METHODS_MAP.md) - MetadataController methods
- [PHASE1D_METHODS_MAP.md](PHASE1D_METHODS_MAP.md) - MainWindowController methods
- [PHASE1D_COMPLETE.md](PHASE1D_COMPLETE.md) - Phase 1D completion summary

### System Documentation
- [database_system.md](database_system.md) - Database architecture
- [structured_metadata_system.md](structured_metadata_system.md) - Metadata handling
- [progress_manager_system.md](progress_manager_system.md) - Progress tracking
- [safe_rename_workflow.md](safe_rename_workflow.md) - Rename workflow
- [application_workflow.md](application_workflow.md) - Application flow

### User Guides
- [keyboard_shortcuts.md](keyboard_shortcuts.md) - Keyboard shortcuts reference
- [database_quick_start.md](database_quick_start.md) - Database quick reference
- [json_config_system.md](json_config_system.md) - Configuration system

---

## Next Steps

**Current Status:** Consolidation phase after Phase 1 completion  
**Immediate Tasks:**
- Documentation cleanup and consolidation
- Code review for old code path remnants
- Performance profiling of new controllers

**Next Phase:** Phase 2 - State Management Fix (ARCH_REFACTOR_PLAN.md)  
**Timeline:** To be determined  
**Focus:** Single source of truth, fix counter conflicts, state synchronization

---

*For detailed technical specifications and architecture decisions, see [ARCHITECTURE.md](ARCHITECTURE.md)*