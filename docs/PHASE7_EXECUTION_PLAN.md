# Phase 7: Final Polish — Execution Plan

> **Status**: PLANNED  
> **Created**: December 19, 2025  
> **Branch**: `phase7-polish`  
> **Author**: Michael Economou

---

## Overview

**Phase 7** is the final phase of the oncutf refactoring project. It focuses on
performance optimization, documentation completion, and final code cleanup to
ensure the application is production-ready.

### Current State Analysis

After completing Phases 0-6:

| Metric | Value | Status |
|--------|-------|--------|
| Tests | 866 | ✅ 100% passing |
| MyPy (Phase 1-6 code) | 0 errors | ✅ Clean |
| Ruff (Phase 1-6 code) | 0 errors | ✅ Clean |
| MyPy (upstream/legacy) | ~614 errors | ⚠️ Pre-existing |
| Architecture Layers | 5 | ✅ Complete |
| Service Protocols | 5 | ✅ Complete |
| Controllers | 4 | ✅ Complete |

### Goals

1. **Performance Optimization** - Profile and optimize startup time and memory usage
2. **Documentation Completion** - Ensure all user and developer docs are complete
3. **Code Cleanup** - Address remaining style issues and improve consistency
4. **Final Testing** - Stress testing and edge case validation

---

## Execution Rules

1. **Measure first** - Profile before optimizing
2. **Document changes** - Keep changelog updated
3. **Test after every change** - No regressions allowed
4. **App must be runnable** at every checkpoint

---

## Step 7.1: Performance Profiling Setup

**Goal**: Set up profiling infrastructure and establish baseline metrics.

### Sub-step 7.1.1: Create Profiling Script

**File**: `scripts/profile_startup.py`

**Implementation**:
```python
"""
Startup profiling script for oncutf.

Author: Michael Economou
Date: December 2025
"""
import cProfile
import pstats
import time
from pathlib import Path

def profile_startup():
    """Profile application startup time."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    start = time.perf_counter()
    # Import and initialize app
    from oncutf.ui.main_window import MainWindow
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = MainWindow()
    
    elapsed = time.perf_counter() - start
    profiler.disable()
    
    # Save stats
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.dump_stats('reports/startup_profile.prof')
    
    print(f"Startup time: {elapsed:.3f}s")
    stats.print_stats(30)
    
    return elapsed

if __name__ == "__main__":
    profile_startup()
```

**Commit Message**: `chore: add startup profiling script`

**Definition of Done**:
- [ ] Script created and executable
- [ ] Baseline startup time recorded
- [ ] Profile data saved to reports/
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

### Sub-step 7.1.2: Create Memory Profiling Script

**File**: `scripts/profile_memory.py`

**Implementation**:
```python
"""
Memory profiling script for oncutf.

Author: Michael Economou
Date: December 2025
"""
import tracemalloc
import sys
from pathlib import Path

def profile_memory():
    """Profile application memory usage."""
    tracemalloc.start()
    
    from oncutf.ui.main_window import MainWindow
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = MainWindow()
    
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print("Top 20 memory allocations:")
    for stat in top_stats[:20]:
        print(stat)
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"\nCurrent: {current / 1024 / 1024:.2f} MB")
    print(f"Peak: {peak / 1024 / 1024:.2f} MB")
    
    tracemalloc.stop()
    return peak

if __name__ == "__main__":
    profile_memory()
```

**Commit Message**: `chore: add memory profiling script`

**Definition of Done**:
- [ ] Script created and executable
- [ ] Baseline memory usage recorded
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

### Sub-step 7.1.3: Document Baseline Metrics

**File**: `docs/PERFORMANCE_BASELINE.md`

**Content**: Record baseline metrics including:
- Startup time (cold/warm)
- Peak memory usage
- Time to first paint
- Top 10 slowest imports/functions

**Commit Message**: `docs: add performance baseline documentation`

**Definition of Done**:
- [ ] Baseline document created
- [ ] All metrics recorded
- [ ] Comparison targets defined

---

## Step 7.2: Startup Optimization

**Goal**: Optimize application startup time based on profiling data.

### Sub-step 7.2.1: Analyze Import Dependencies

**Action**: Review import chain and identify heavy imports.

**Potential Optimizations**:
- Lazy import of ExifTool (only when needed)
- Defer metadata manager initialization
- Lazy load theme resources
- Defer database connection

**Commit Message**: `perf: optimize import chain for faster startup`

**Definition of Done**:
- [ ] Import analysis complete
- [ ] Heavy imports identified
- [ ] Lazy loading implemented where beneficial
- [ ] Startup time improved by measurable amount
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

### Sub-step 7.2.2: Optimize Service Initialization

**Action**: Ensure ServiceRegistry uses lazy initialization.

**Review Points**:
- `oncutf/services/registry.py` - verify lazy loading
- `oncutf/core/application_service.py` - check initialization order
- `oncutf/controllers/` - verify no eager loading

**Commit Message**: `perf: optimize service initialization order`

**Definition of Done**:
- [ ] Service initialization order optimized
- [ ] No unnecessary eager loading
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

## Step 7.3: Memory Optimization

**Goal**: Reduce peak memory usage and prevent memory leaks.

### Sub-step 7.3.1: Audit Large Data Structures

**Action**: Review caching strategies and data retention.

**Review Points**:
- `oncutf/core/persistent_hash_cache.py` - cache size limits
- `oncutf/core/advanced_cache_manager.py` - eviction policies
- `oncutf/core/unified_metadata_manager.py` - metadata retention
- Icon caches in `utils/icon_cache.py`

**Commit Message**: `perf: optimize cache memory usage`

**Definition of Done**:
- [ ] Cache sizes reviewed and bounded
- [ ] Eviction policies verified
- [ ] Memory usage reduced or documented as acceptable
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

### Sub-step 7.3.2: Review Signal Connections

**Action**: Ensure no memory leaks from signal connections.

**Review Points**:
- Check for disconnected signals on widget destruction
- Verify weak references where appropriate
- Review long-lived signal connections

**Commit Message**: `fix: ensure proper signal cleanup`

**Definition of Done**:
- [ ] Signal connections audited
- [ ] No memory leaks from signals
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

## Step 7.4: Documentation Completion

**Goal**: Ensure all documentation is complete and accurate.

### Sub-step 7.4.1: Update User Documentation

**Files to Review/Update**:
- `README.md` - Installation and quick start
- `docs/keyboard_shortcuts.md` - All shortcuts documented
- `CHANGELOG.md` - All changes documented

**Commit Message**: `docs: update user documentation`

**Definition of Done**:
- [ ] README reflects current state
- [ ] All keyboard shortcuts documented
- [ ] CHANGELOG complete through Phase 7
- [ ] No broken links

---

### Sub-step 7.4.2: Update Developer Documentation

**Files to Review/Update**:
- `DEVELOPMENT.md` - Development setup instructions
- `docs/ARCHITECTURE.md` - Architecture overview accurate
- `docs/database_system.md` - Database docs accurate
- `docs/structured_metadata_system.md` - Metadata docs accurate

**Commit Message**: `docs: update developer documentation`

**Definition of Done**:
- [ ] All architecture docs reflect current state
- [ ] Development setup instructions work
- [ ] API documentation complete
- [ ] No outdated information

---

### Sub-step 7.4.3: Create API Reference

**File**: `docs/API_REFERENCE.md`

**Content**:
- Service protocols and their methods
- Controller public interfaces
- Core manager APIs
- Module API contracts

**Commit Message**: `docs: add API reference documentation`

**Definition of Done**:
- [ ] All public APIs documented
- [ ] Examples provided
- [ ] Type hints documented

---

## Step 7.5: Code Cleanup

**Goal**: Final code quality improvements.

### Sub-step 7.5.1: Consistency Audit

**Action**: Ensure consistent code style across the codebase.

**Review Points**:
- Docstring format consistency
- Logging message format consistency
- Error handling patterns
- Import organization

**Commit Message**: `style: improve code consistency`

**Definition of Done**:
- [ ] Consistent docstring format
- [ ] Consistent logging format (%-style, ASCII only)
- [ ] Consistent error handling
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

### Sub-step 7.5.2: Dead Code Removal

**Action**: Remove any remaining dead code.

**Tools**:
- `vulture` for dead code detection
- Manual review of TODO/FIXME comments

**Commit Message**: `refactor: remove dead code`

**Definition of Done**:
- [ ] No dead code remaining
- [ ] TODO/FIXME comments addressed or documented
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

### Sub-step 7.5.3: Address Upstream Issues (Optional)

**Action**: Fix pre-existing mypy/ruff issues where safe.

**Approach**:
- Focus on high-impact, low-risk fixes
- Skip complex refactors that risk regressions
- Document issues that cannot be fixed

**Commit Message**: `fix: address upstream type/style issues`

**Definition of Done**:
- [ ] Safe fixes applied
- [ ] Unfixable issues documented
- [ ] No regressions
- [ ] `pytest tests/ -q` passes

---

## Step 7.6: Final Testing

**Goal**: Comprehensive final validation.

### Sub-step 7.6.1: Stress Testing

**Action**: Test with large file sets.

**Test Scenarios**:
- 1000+ files in a single directory
- Deep directory structures (10+ levels)
- Large metadata (RAW files with extensive EXIF)
- Rapid rename operations

**Commit Message**: `test: add stress tests`

**Definition of Done**:
- [ ] Stress tests pass
- [ ] Performance acceptable under load
- [ ] No crashes or hangs

---

### Sub-step 7.6.2: Edge Case Testing

**Action**: Test edge cases and error handling.

**Test Scenarios**:
- Files with special characters in names
- Read-only files
- Network paths (if supported)
- Unicode filenames
- Very long paths

**Commit Message**: `test: add edge case tests`

**Definition of Done**:
- [ ] Edge cases handled gracefully
- [ ] Error messages are clear
- [ ] No crashes on invalid input

---

### Sub-step 7.6.3: Cross-Platform Validation

**Action**: Validate on different platforms.

**Platforms**:
- Linux (primary)
- Windows (if applicable)
- macOS (if applicable)

**Commit Message**: `test: validate cross-platform compatibility`

**Definition of Done**:
- [ ] Works on all target platforms
- [ ] Platform-specific issues documented

---

## Step 7.7: Release Preparation

**Goal**: Prepare for release.

### Sub-step 7.7.1: Version Bump

**Action**: Update version number.

**Files to Update**:
- `pyproject.toml` - version field
- `oncutf/__init__.py` - __version__ (if present)

**Commit Message**: `chore: bump version to X.Y.Z`

**Definition of Done**:
- [ ] Version updated consistently
- [ ] CHANGELOG reflects version

---

### Sub-step 7.7.2: Final CHANGELOG Update

**File**: `CHANGELOG.md`

**Action**: Ensure all Phase 7 changes are documented.

**Commit Message**: `docs: finalize CHANGELOG for release`

**Definition of Done**:
- [ ] All changes documented
- [ ] Release date set
- [ ] Breaking changes highlighted (if any)

---

### Sub-step 7.7.3: Create Release Tag

**Action**: Create git tag for release.

```bash
git tag -a vX.Y.Z -m "Release X.Y.Z - Final Polish"
git push origin vX.Y.Z
```

**Commit Message**: N/A (tag only)

**Definition of Done**:
- [ ] Tag created
- [ ] Tag pushed to remote
- [ ] Release notes written

---

## Phase 7 Checklist Summary

### Performance
- [ ] Profiling scripts created
- [ ] Baseline metrics documented
- [ ] Startup time optimized
- [ ] Memory usage optimized
- [ ] Signal cleanup verified

### Documentation
- [ ] User documentation complete
- [ ] Developer documentation complete
- [ ] API reference created

### Code Quality
- [ ] Consistency audit complete
- [ ] Dead code removed
- [ ] Upstream issues addressed (where safe)

### Testing
- [ ] Stress tests pass
- [ ] Edge cases handled
- [ ] Cross-platform validated

### Release
- [ ] Version bumped
- [ ] CHANGELOG finalized
- [ ] Release tag created

---

## Timeline Estimate

| Step | Estimated Effort | Priority |
|------|------------------|----------|
| 7.1 Profiling Setup | 2-3 hours | High |
| 7.2 Startup Optimization | 4-6 hours | High |
| 7.3 Memory Optimization | 3-4 hours | Medium |
| 7.4 Documentation | 4-6 hours | High |
| 7.5 Code Cleanup | 2-4 hours | Medium |
| 7.6 Final Testing | 3-4 hours | High |
| 7.7 Release Prep | 1-2 hours | High |
| **Total** | **19-29 hours** | |

---

## Success Criteria

Phase 7 is complete when:

1. ✅ Startup time improved or documented as acceptable
2. ✅ Memory usage bounded and documented
3. ✅ All documentation complete and accurate
4. ✅ No dead code remaining
5. ✅ All tests passing (866+ tests)
6. ✅ Stress tests passing
7. ✅ Release tag created

---

*This plan is a living document and may be updated as work progresses.*
