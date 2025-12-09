# Refactoring & Optimization Plan

**Date:** 2025-12-09  
**Author:** Claude Opus  
**Status:** DRAFT — Awaiting Review

---

## 1. Executive Summary

This document outlines a comprehensive refactoring plan for the `oncutf` codebase. The primary goals are:

1. **Improve Performance** — Reduce startup time, optimize metadata loading, enhance cache efficiency.
2. **Enhance Code Clarity** — Split oversized "god classes," reorganize flat directory structures.
3. **Reduce GUI Errors** — Implement defensive programming, global error boundaries, and improved thread safety.

### Key Findings

| File | Lines | Size | Issue |
|------|-------|------|-------|
| `core/unified_metadata_manager.py` | 2,184 | 88KB | Monolithic — handles reading, writing, caching, and loading |
| `widgets/metadata_tree_view.py` | 2,055 | 86KB | Widget + model + delegate all in one file |
| `core/event_handler_manager.py` | 1,556 | 65KB | Handles all UI events — no domain separation |
| `main_window.py` | 1,309 | 57KB | Thin facade — acceptable |
| `utils/theme_engine.py` | — | 62KB | Large styling logic — extract to theme tokens |

The `core/` directory contains **61 files** with no subdirectory organization.

---

## 2. Structural Refactoring

### 2.1 Reorganize `core/` Package

**Problem:** 61 files in a flat structure makes navigation and understanding difficult.

**Proposed Structure:**
```
core/
├── __init__.py
├── services/               # Background/async services
│   ├── backup_manager.py
│   ├── database_manager.py
│   ├── hash_manager.py
│   └── thread_pool_manager.py
├── data/                   # Data stores and caches
│   ├── file_store.py
│   ├── selection_store.py
│   ├── persistent_metadata_cache.py
│   └── persistent_hash_cache.py
├── metadata/               # Metadata operations (split from unified_metadata_manager)
│   ├── metadata_reader.py
│   ├── metadata_writer.py
│   ├── metadata_cache_service.py
│   └── companion_metadata_handler.py
├── events/                 # Event handling (split from event_handler_manager)
│   ├── file_events.py
│   ├── ui_events.py
│   └── drag_events.py
├── initialization/         # Startup logic
│   ├── initialization_orchestrator.py
│   ├── initialization_worker.py
│   └── initialization_manager.py
├── ui/                     # UI management
│   ├── ui_manager.py
│   ├── theme_manager.py
│   ├── splitter_manager.py
│   └── status_manager.py
└── rename/                 # Rename operations
    ├── rename_manager.py
    ├── rename_history_manager.py
    └── unified_rename_engine.py
```

### 2.2 Split God Classes

#### 2.2.1 `unified_metadata_manager.py` → 4 Modules

| New Module | Responsibility |
|------------|----------------|
| `MetadataReader` | Load metadata from files using ExifTool |
| `MetadataWriter` | Write/update metadata to files |
| `MetadataCacheService` | In-memory and persistent cache operations |
| `CompanionMetadataHandler` | Handle sidecar/companion file metadata |

#### 2.2.2 `event_handler_manager.py` → 3 Modules

| New Module | Responsibility |
|------------|----------------|
| `FileEventHandlers` | Browse, folder import, file operations |
| `UIEventHandlers` | Context menus, header toggles, splitter moves |
| `DragEventHandlers` | Drag & drop operations |

#### 2.2.3 `metadata_tree_view.py` → 3 Modules

| New Module | Responsibility |
|------------|----------------|
| `MetadataTreeView` (slimmed) | Core tree view widget only |
| `MetadataTreeModel` | Data model and filtering logic |
| `MetadataItemDelegate` | Custom item rendering |

---

## 3. Performance Optimization

### 3.1 Startup Time Reduction

**Current Flow:**
1. Splash screen shows
2. Background worker initializes (database, cache, etc.)
3. MainWindow created after both conditions met

**Optimizations:**
- [ ] Profile initialization to identify bottlenecks
- [ ] Lazy-load non-essential managers (e.g., `RenameHistoryManager`)
- [ ] Defer database connection until first use

### 3.2 ExifTool Batching

The codebase already uses `-stay_open` mode (good). Additional optimizations:

- [ ] Verify batch size is optimal (currently unknown)
- [ ] Add request coalescing for rapid successive calls
- [ ] Implement request prioritization (UI-blocking vs background)

### 3.3 Cache Strategy Review

**Files to audit:**
- `core/advanced_cache_manager.py`
- `core/persistent_metadata_cache.py`
- `utils/metadata_cache_helper.py`

**Actions:**
- [ ] Ensure L1 (memory) → L2 (disk) cache hierarchy
- [ ] Review cache invalidation logic for staleness bugs
- [ ] Add cache hit/miss metrics logging

### 3.4 GUI Responsiveness

- [ ] Audit for long-running operations on main thread
- [ ] Verify signal debouncing is applied to all high-frequency signals
- [ ] Review `processEvents()` calls — can cause reentrancy bugs

---

## 4. GUI Error Reduction

### 4.1 Global Error Boundary

**Problem:** Unhandled exceptions crash the application.

**Solution:** Implement `sys.excepthook` to:
1. Log the exception with full traceback
2. Show a non-intrusive toast notification
3. Attempt graceful recovery or offer restart

**Implementation Location:** `main.py` after logging setup.

### 4.2 Defensive Widget Programming

**Pattern to enforce in `widgets/`:**
```python
# Before
value = file_item.metadata.get("Date")

# After
value = getattr(file_item, 'metadata', {}).get("Date", "")
```

**Files requiring audit:**
- All files in `widgets/`
- `core/event_handler_manager.py`

### 4.3 Qt Object Lifecycle

**Problem:** `RuntimeError: wrapped C/C++ object has been deleted`

**Solution:**
- Use `QPointer` for potentially deleted objects
- Check `isValid()` / `is not None` before operations
- Use `deleteLater()` instead of `del` or `close()`

---

## 5. Code Quality

### 5.1 Type Annotations

**Current State:** Inconsistent — many files use `# type: ignore`.

**Actions:**
- [ ] Add strict type hints to refactored modules
- [ ] Configure `mypy` with `strict = true` for new code
- [ ] Gradually expand coverage

### 5.2 Test Coverage

**Existing Tests:** Located in `tests/` directory (54 files).

**Actions:**
- [ ] Run existing tests to establish baseline
- [ ] Add tests for refactored modules
- [ ] Target 80% coverage for `core/` and `utils/`

---

## 6. Implementation Roadmap

### Phase 1: Foundation (Days 1-3)
- [ ] Create new directory structure under `core/`
- [ ] Implement global error boundary
- [ ] Add `sys.excepthook` handler
- [ ] Run existing tests — ensure no regressions

### Phase 2: Core Refactoring (Days 4-8)
- [ ] Split `unified_metadata_manager.py`
- [ ] Split `event_handler_manager.py`
- [ ] Update all imports
- [ ] Run tests after each split

### Phase 3: Widget Refactoring (Days 9-12)
- [ ] Split `metadata_tree_view.py`
- [ ] Add defensive programming patterns
- [ ] Audit Qt object lifecycle issues

### Phase 4: Performance (Days 13-15)
- [ ] Profile startup time
- [ ] Optimize cache strategy
- [ ] Add metrics logging

---

## 7. Verification Plan

### Automated Tests
```bash
# Run all existing tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=core --cov=utils --cov=widgets --cov-report=term-missing
```

### Manual Verification
1. **Startup Test:** Application starts without errors in < 3 seconds
2. **File Loading:** Load 100+ files, check for UI freezes
3. **Metadata Operations:** Load, edit, and save metadata without crashes
4. **Drag & Drop:** Verify all drag operations work smoothly

---

## 8. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Startup Time | ~4s (estimated) | < 2s |
| Max File Size (single module) | 88KB | < 30KB |
| Unhandled Exceptions | Unknown | 0 |
| Test Coverage | Unknown | > 80% |

---

## 9. Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Run tests after each change |
| Import cycle issues after reorganization | Use lazy imports where needed |
| Performance regression | Profile before/after each phase |

---

**Next Steps:** Review this plan and approve before proceeding to Phase 1.
