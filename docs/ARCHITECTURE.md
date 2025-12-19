# OnCutF Architecture Guide

**Last Updated:** 2025-12-19  
**Status:** Phase 7 (Final Polish) - Performance Optimizations ⚡

---

## Quick Navigation

- **[Phase 1 Summary](PHASE1_SUMMARY.md)** — Controllers architecture complete overview
- **[Phase 7 Plan](PHASE7_EXECUTION_PLAN.md)** — Performance optimizations & polish
- **[Performance Baseline](PERFORMANCE_BASELINE.md)** — Startup time & memory tracking
- **[Roadmap](ROADMAP.md)** — Current progress & next phases
- **[Arch Refactor Plan](ARCH_REFACTOR_PLAN.md)** — Strategic refactoring plan
- **[Cache Strategy](architecture/cache_strategy.md)** — Caching layers & invalidation
- **[Column Management Guide](architecture/column_management_mixin_guide.md)** — FileTableView columns

---

## Architecture Overview

### MVC-Inspired Four-Tier Design

```
┌─────────────────────────────────────┐
│        UI Layer (PyQt5)             │
├─────────────────────────────────────┤
│  Main Window > Widgets > Mixins     │
│  ├── FileTableView (976 LOC)        │
│  ├── MetadataTreeView (1768 LOC)    │
│  ├── RenameModulesArea              │
│  └── Mixins: Selection, DragDrop... │
│                                     │
│            ↓ delegates to           │
│                                     │
├─────────────────────────────────────┤
│   Controllers Layer (NEW Phase 1)   │
├─────────────────────────────────────┤
│  ├── FileLoadController             │
│  ├── MetadataController             │
│  ├── RenameController               │
│  └── MainWindowController           │
│                                     │
│         ↓ orchestrates              │
│                                     │
├─────────────────────────────────────┤
│      Business Logic (Core)          │
├─────────────────────────────────────┤
│  ├── UnifiedRenameEngine            │
│  ├── UnifiedMetadataManager         │
│  ├── Managers (30+)                 │
│  └── Domain Models                  │
│                                     │
│          ↓ persists to              │
│                                     │
├─────────────────────────────────────┤
│      Data Layer                     │
├─────────────────────────────────────┤
│  ├── Persistent Caches (SQLite)     │
│  ├── Config Persistence (JSON)      │
│  └── File System Operations         │
└─────────────────────────────────────┘
```

### Key Components

| Component | Files | LOC | Purpose |
|-----------|-------|-----|---------|
| **Controllers (Phase 1)** | 4 | 1217 | UI ↔ Business logic separation |
| **FileTableView** | 1 + 3 mixins | 976 | Display files with columns |
| **MetadataTreeView** | 1 + 4 mixins | 1768 | Edit file metadata |
| **UnifiedRenameEngine** | 1 | ~400 | Orchestrate rename preview/validation/execution |
| **UnifiedMetadataManager** | 1 | ~300 | Metadata loading & caching |
| **Domain Models** | 4 dataclasses | ~500 | Type-safe data structures |
| **Mixins** | 7+ files | ~2500 | UI behavior decomposition |
| **Managers** | 30+ | ~8000 | Application-level coordination |
| **Utilities** | 53 | ~5000 | Helpers & common functions |

---

## Recent Improvements (2025-12)

### Phase 7: Final Polish ⚡ (NEW - Dec 2025)
**Goal:** Performance optimization, documentation, and final polish

#### Performance Optimizations ✅
- **Startup Time:** 31% faster (1426ms → 989ms)
  - Lazy-loaded ExifToolWrapper: -12% (1426ms → 1261ms)
  - Lazy-loaded CompanionFilesHelper: -21% (1261ms → 989ms)
  - **Result:** Exceeded <1000ms target 🎯

- **Memory Management:** Bounded caches with LRU eviction
  - PersistentHashCache: 1000 entry limit with OrderedDict LRU
  - PersistentMetadataCache: 500 entry limit with OrderedDict LRU
  - **Result:** Prevents unbounded growth with large file sets

- **Profiling Infrastructure:** Comprehensive performance tracking
  - `scripts/profile_startup.py`: Startup time analysis
  - `scripts/profile_memory.py`: Memory usage profiling
  - `docs/PERFORMANCE_BASELINE.md`: Performance history tracking

**Impact:**
- Faster application launch (sub-second startup)
- Memory-safe for large workloads (1000+ files)
- Foundation for future performance work

---

### Phase 1: Controllers Architecture ✅ (Dec 2025)
**Goal:** Separate UI from business logic with testable controller layer

#### Phase 1A: FileLoadController ✅
- **Orchestrates:** File loading, drag & drop, directory scanning
- **Methods:** `load_files_from_drop()`, `load_folder()`, `clear_files()`
- **Tests:** 11 comprehensive tests (100% coverage)
- **Benefit:** File loading logic testable without Qt/GUI

#### Phase 1B: MetadataController ✅
- **Orchestrates:** Metadata loading, cache management
- **Methods:** `load_metadata()`, `reload_metadata()`, `clear_metadata_cache()`
- **Tests:** 13 comprehensive tests (100% coverage)
- **Benefit:** Metadata workflows testable independently

#### Phase 1C: RenameController ✅
- **Orchestrates:** Rename preview, validation, execution
- **Methods:** `preview_rename()`, `execute_rename()`, `update_preview()`
- **Tests:** 16 comprehensive tests (100% coverage)
- **Benefit:** Rename logic testable with mock dependencies

#### Phase 1D: MainWindowController ✅
- **Orchestrates:** High-level multi-service workflows
- **Methods:** `restore_last_session_workflow()`, `coordinate_shutdown_workflow()`
- **Tests:** 17 comprehensive tests (100% coverage)
- **Benefit:** Complex workflows testable without MainWindow

**Results:**
- 57 new tests (549 → 592, 100% pass rate)
- Clean separation: UI → Controllers → Services
- Zero regressions (all existing functionality preserved)
- Foundation for future CLI/API interfaces

**See:** [PHASE1_SUMMARY.md](PHASE1_SUMMARY.md)

---

### Phase 0: Widget Decomposition ✅
- **FileTableView:** 2715 → 976 LOC (-64%)
  - Extracted: Column management (34 methods)
  - Created: `ColumnManagementMixin` (1179 LOC)

- **MetadataTreeView:** 3102 → 1768 LOC (-43%)
  - Extracted: 4 specialized mixins
  - Improved: Testability and maintainability

### Domain Models ✅
- Created: `FileEntry` (type-safe file representation)
- Created: `MetadataEntry` (structured metadata)
- Benefit: Type safety, memory efficiency, clarity

### Selection Unification ✅
- Created: `SelectionProvider` (unified interface)
- Replaced: 50+ ad-hoc selection patterns
- Benefit: Single source of truth, 500x faster (cached)

### Code Quality ✅
- Translated: Greek → English (38 instances)
- Synced: Docstring dates to git history (75 files)
- Tests: 592 passing (100%)

---

## File Organization

```
oncutf/
├── main.py                          # Entry point
├── config.py                        # Configuration
│
├── ui/                              # UI Layer
│   ├── main_window.py               # Primary UI (delegates to controllers)
│   ├── widgets/                     # UI components
│   │   ├── file_table_view.py       # Main file table (976 LOC)
│   │   ├── metadata_tree_view.py    # Metadata editor (1768 LOC)
│   │   ├── rename_modules_area.py   # Rename config
│   │   └── ... (30+ other widgets)
│   └── mixins/                      # Behavior mixins
│       ├── selection_mixin.py
│       ├── drag_drop_mixin.py
│       ├── column_management_mixin.py
│       └── ... (4+ more)
│
├── controllers/                     # Controllers Layer (NEW Phase 1)
│   ├── __init__.py                  # Exports all controllers
│   ├── file_load_controller.py      # File loading orchestration (274 LOC)
│   ├── metadata_controller.py       # Metadata operations (230 LOC)
│   ├── rename_controller.py         # Rename workflows (312 LOC)
│   └── main_window_controller.py    # High-level orchestration (401 LOC)
│
├── core/                            # Business Logic Layer
│   ├── application_context.py       # Singleton application state
│   ├── unified_rename_engine.py     # Rename orchestration
│   ├── unified_metadata_manager.py  # Metadata loading
│   ├── selection_store.py           # Selection state
│   ├── persistent_hash_cache.py     # SQLite hash cache
│   ├── persistent_metadata_cache.py # SQLite metadata cache
│   ├── *_manager.py                 # 30+ manager classes
│   └── ...
│
├── models/                          # Domain models
│   ├── file_entry.py                # File representation
│   ├── metadata_entry.py            # Metadata structure
│   ├── file_item.py
│   └── file_table_model.py
│
├── modules/                         # Rename modules (plugins)
│   ├── base_module.py
│   ├── specified_text_module.py
│   ├── metadata_module.py
│   ├── counter_module.py
│   └── ... (7+ total)
│
├── utils/                           # Utilities
│   ├── selection_provider.py        # Unified selection interface
│   ├── filename_validator.py
│   ├── metadata_loader.py
│   ├── icon_cache.py
│   └── ... (50+ helpers)
│
├── scripts/                         # Automation scripts
│   ├── translate_greek_to_english.py
│   ├── fix_module_dates.py
│   └── ... (utilities)
│
├── tests/                           # Test suite
│   ├── test_*.py                    # 592 tests, 100% passing
│   ├── conftest.py
│   └── mocks.py
│
└── docs/                            # Documentation
    ├── ARCHITECTURE.md              # (this file)
    ├── ROADMAP.md                   # Current progress
    ├── PHASE1_SUMMARY.md            # Phase 1 complete overview
    ├── ARCH_REFACTOR_PLAN.md        # Detailed refactoring plan
    └── architecture/                # Detailed docs
        ├── cache_strategy.md
        ├── column_management_mixin_guide.md
        └── ... (planning docs)
```

---

## Key Architecture Patterns

### 1. Controllers Layer (NEW - Phase 1)
Separation of UI from business logic:
```python
# FileLoadController - orchestrates file loading
controller = FileLoadController(app_context)
result = controller.load_folder("/path/to/folder", recursive=True)

# MetadataController - orchestrates metadata operations
metadata_ctrl = MetadataController(app_context)
result = metadata_ctrl.load_metadata(file_paths, on_progress=callback)

# RenameController - orchestrates rename workflows
rename_ctrl = RenameController(app_context)
preview = rename_ctrl.preview_rename(files, rename_config)
execute_result = rename_ctrl.execute_rename(preview.items)

# MainWindowController - high-level orchestration
main_ctrl = MainWindowController(app_context, file_load_ctrl, metadata_ctrl, rename_ctrl)
session = main_ctrl.restore_last_session_workflow(on_progress=callback)
shutdown = main_ctrl.coordinate_shutdown_workflow(on_progress=callback)
```

**Benefits:**
- Testable without Qt (controllers use pure Python interfaces)
- Clear responsibility boundaries
- Easy to mock dependencies in tests
- Reusable orchestration logic
- Foundation for future CLI/API interfaces

### 2. ApplicationContext (Singleton)
Central registry of managers and services:
```python
# Usage
context = ApplicationContext()
selection = context.selection_store.get_selected_files()
context.metadata_manager.load_metadata(files)
```

### 3. Mixin-based Composition
Widget behavior decomposed into mixins:
```python
class FileTableView(
    QTableView,
    SelectionMixin,          # Selection handling
    DragDropMixin,           # Drag/drop support
    ColumnManagementMixin    # Column config
):
    pass
```

### 4. Domain Models (Dataclasses)
Type-safe data structures:
```python
@dataclass
class FileEntry:
    path: Path
    size: int
    modified: datetime
    
@dataclass
class MetadataEntry:
    file_id: str
    exif_data: dict
    extracted_text: dict
```

### 5. Unified Interfaces
Single point of access for common operations:
```python
# Old: scattered selection logic
table.selection_model().selectedRows()  # Qt direct
tree.selected_items()  # Custom

# New: unified interface
selection = SelectionProvider(table).get_selected_files()
```

### 6. Caching Strategy
Multi-layer caching:
- **L1:** Python dict (LRU, fast, volatile)
- **L2:** SQLite (persistent, indexed)
- **L3:** File system (original data)

See [Cache Strategy](architecture/cache_strategy.md) for details.

---

## Performance Metrics

| Metric | Before Phase 1 | After Phase 1 | Improvement |
|--------|-----------------|---------------|-------------|
| Test Count | 549 | 592 | +43 tests (+7.8%) |
| Controller LOC | 0 | 1217 | New layer |
| MainWindow LOC | ~1309 | ~900 | -31% (UI-focused) |
| Test Coverage | ~75% | ~78% | +4% |
| Test Speed (controllers) | N/A | ~1s | Fast (no Qt) |

**Historical Widget Refactoring:**
- FileTableView: 2715 → 976 LOC (-64%)
- MetadataTreeView: 3102 → 1768 LOC (-43%)

**Test Suite:** 592 tests, 100% passing ✅

---

## How to Navigate the Code

### Starting Points

1. **Understand file loading:**
   - `main_window.py` → **`FileLoadController`** → `FileLoadManager` → `UnifiedMetadataManager`

2. **Understand rename flow:**
   - `RenameModulesArea` → **`RenameController`** → `UnifiedRenameEngine` → `FileOperationsManager`

3. **Understand metadata operations:**
   - `main_window.py` → **`MetadataController`** → `UnifiedMetadataManager` → Cache layers

4. **Understand application workflows:**
   - `main_window.py` → **`MainWindowController`** → Sub-controllers → Services

5. **Understand UI state:**
   - `ApplicationContext` → `SelectionStore` → Widget mixins

6. **Understand caching:**
   - See [Cache Strategy](architecture/cache_strategy.md)

### Code Reading Tips

- Start with `main.py` (simple entry point)
- Then `ui/main_window.py` (primary UI, delegates to controllers)
- **NEW:** Check `controllers/` for business logic orchestration
- Then specific managers/widgets as needed
- Use mixin files to understand widget behavior
- Check `models/` for data structures
- See `tests/test_*_controller.py` for usage examples

---

## Current Status Summary

### ✅ Completed
- **Phase 1: Controllers Architecture** (Dec 2025)
  - FileLoadController, MetadataController, RenameController, MainWindowController
  - 57 new tests (592 total, 100% passing)
  - Clean UI/business logic separation
- **Phase 0: Package Structure** (Dec 2025)
  - All code under `oncutf/` package
  - Clean import structure
- Domain models (dataclasses)
- Selection unification
- Widget decomposition (mixins)
- Cache strategy documented
- Code quality (Greek translated, dates synced)

### 🎯 Next Phase
- **Phase 2: State Management Fix**
  - Consolidate FileStore with FileGroup support
  - Fix counter conflicts after multi-folder imports
  - Implement StateCoordinator for synchronization

### ⏸️ Deferred (Conscious Decision)
- Streaming metadata (ROI analysis: not worthwhile)
- Service layer consolidation (too risky)
- ViewModel layer (over-engineering)

---

## Next Steps

See [ROADMAP.md](ROADMAP.md) for detailed roadmap:

- **Phase 2:** State Management Fix (consolidate FileStore, fix counter conflicts)
- **Phase 3:** UI/UX Improvements (splash screen, progress indicators)
- **Phase 4:** Core Logic Improvements (optimize metadata, caching)
- **Phase 5:** Final Polish (performance profiling, documentation)

---

## Reference Documents

| Document | Purpose | Status |
|----------|---------|--------|
| [ROADMAP.md](ROADMAP.md) | Current progress & next phases | ✅ Active |
| [PHASE1_SUMMARY.md](PHASE1_SUMMARY.md) | Phase 1 complete overview | ✅ Latest |
| [ARCH_REFACTOR_PLAN.md](ARCH_REFACTOR_PLAN.md) | Strategic refactoring plan (Phases 2-6) | ✅ Active |
| [Cache Strategy](architecture/cache_strategy.md) | Caching layers & patterns | ✅ Complete |
| [Column Management Guide](architecture/column_management_mixin_guide.md) | FileTableView columns | ✅ Complete |

---

## Contributing

When modifying architecture:

1. **Use controllers for orchestration** — Don't put business logic in UI
2. **Keep mixins focused** — One responsibility per mixin
3. **Use domain models** — Don't pass dicts around
4. **Test new code** — Especially business logic in controllers
5. **Document changes** — Update this file if needed
6. **Consider impact** — Check for ripple effects

---

*Generated: 2025-12-16*  
*Last reviewed by: Architecture team after Phase 1 completion*
