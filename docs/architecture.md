# oncutf Architecture Guide

**Last Updated:** 2026-01-25  
**Status:** Production-Ready — Clean Architecture with Pragmatic Strict Typing ✅

---

## Quick Navigation

- **[Documentation Index](README.md)** — All available documentation
- **[Refactoring Summary](260121_summary.md)** — Phases A-E completion status
- **[Migration Stance](migration_stance.md)** — Architecture migration policy
- **Archived docs** — See `_archive/` for historical phase details

---

## Executive Summary (2026-01-25)

### Production Readiness Status

- ✅ **Clean Architecture:** Zero boundary violations (54 → 0)
- ✅ **Type Safety:** Pragmatic strict mode (strictness 8.8/10)
- ✅ **Code Quality:** Zero ruff violations (2062 → 0)
- ✅ **Test Coverage:** 99.4% pass rate (1154/1161)
- ✅ **Technical Debt:** 647 lines of duplicates removed

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      UI Layer (PyQt5)                       │
├─────────────────────────────────────────────────────────────┤
│  Main Window > Widgets > Behaviors > Handlers               │
│  ├── FileTableView (976 LOC)                                │
│  ├── MetadataTreeView (1768 LOC)                            │
│  ├── RenameModulesArea                                      │
│  ├── Behaviors: Selection, DragDrop, Metadata...            │
│  └── Adapters: Qt implementations of ports                  │
│                                                             │
│            ↓ delegates to (via facades)                     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│           Controllers Layer (UI-agnostic)                   │
├─────────────────────────────────────────────────────────────┤
│  ├── FileLoadController         (orchestrate file loading)  │
│  ├── MetadataController          (orchestrate metadata ops) │
│  ├── RenameController            (orchestrate rename flow)  │
│  └── MainWindowController        (high-level coordination)  │
│                                                             │
│         ↓ orchestrates (via services)                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│              App Services (Facades)                         │
├─────────────────────────────────────────────────────────────┤
│  TIER 1 — PRAGMATIC STRICT TYPING (10 strict flags)         │
│  ├── user_interaction   (dialogs, questions)                │
│  ├── cursor             (wait cursor)                       │
│  ├── progress           (progress dialogs)                  │
│  ├── validation_service (field validators)                  │
│  ├── metadata_service   (metadata staging/commands)         │
│  ├── cache_service      (metadata/hash caching)             │
│  ├── database_service   (database operations)               │
│  ├── batch_service      (batch processing)                  │
│  └── folder_color_service (auto-color commands)             │
│                                                             │
│         ↓ uses (business logic)                             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│          Business Logic (Core + Domain)                     │
├─────────────────────────────────────────────────────────────┤
│  TIER 2 — STRICT TYPING (disallow_untyped_defs)             │
│  ├── UnifiedRenameEngine        (rename orchestration)      │
│  ├── UnifiedMetadataManager     (metadata loading)          │
│  ├── Domain Models              (FileRecord, MetadataRecord)│
│  ├── Validators                 (field validation rules)    │
│  └── Managers (30+)             (application coordination)  │
│                                                             │
│          ↓ persists to                                      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│           Infrastructure (Persistence)                      │
├─────────────────────────────────────────────────────────────┤
│  TIER 1 — PRAGMATIC STRICT TYPING                           │
│  ├── external/                  (ExifTool, FFmpeg clients)  │
│  ├── cache/                     (metadata, hash, thumbnail) │
│  ├── db/                        (file repository, database) │
│  └── Persistent Caches          (SQLite with LRU eviction)  │
│                                                             │
│          ↓ persists to                                      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                  Data Layer (Storage)                       │
├─────────────────────────────────────────────────────────────┤
│  ├── SQLite Databases           (metadata, hash, files)     │
│  ├── JSON Config Files          (user preferences)          │
│  └── File System                (renames, backups)          │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Patterns

| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| **Facade** | app/services/*.py | Isolate UI from business logic |
| **Dependency Inversion** | app/ports/*.py (Protocols) | Decouple layers via interfaces |
| **Adapter** | ui/adapters/qt_*.py | Qt implementations of protocols |
| **Repository** | infra/db/file_repository.py | Abstract data access |
| **Controller** | controllers/*.py | UI-agnostic orchestration |
| **Behavior** | ui/behaviors/*.py | Reusable UI interactions |

---

## Type Safety Configuration (Phase E — Complete)

### Pragmatic Strict Typing Strategy

oncutf uses a **three-tier typing strategy** optimized for a metadata-centric application:

```
Tier 1 (app/domain/infra): PRAGMATIC STRICT
├─ 10 strict mypy flags enabled
├─ 2 pragmatically excluded (metadata domain)
├─ Type:ignore: 5 total (all justified)
└─ Rationale: Metadata is intrinsically untyped (EXIF)

Tier 2 (controllers/core/models): STRICT
├─ disallow_untyped_defs = true
├─ All functions require type annotations
└─ Generic types properly specified

Tier 3 (UI/Qt): SELECTIVE
├─ 13 Qt-specific error suppressions
└─ Rationale: PyQt5 stubs have limitations
```

### Enabled Strict Flags (Tier 1)

| Flag | Purpose | Impact |
|------|---------|--------|
| `disallow_untyped_defs` | All functions must have types | Core safety |
| `disallow_any_generics` | Generic types must be specified | Type precision |
| `warn_return_any` | Flag functions returning Any | Explicit Any |
| `no_implicit_reexport` | Prevent accidental exports | Clean API |
| `strict_optional` | Distinguish None from T | Null safety |
| `disallow_any_unimported` | No Any from untyped modules | Import safety |
| `disallow_any_decorated` | No Any from decorators | Decorator safety |
| `disallow_incomplete_defs` | No partial annotations | Completeness |
| `disallow_untyped_calls` | No calls to untyped functions | Call safety |
| `disallow_untyped_decorators` | Decorators must be typed | Decorator safety |

### Pragmatic Exclusions (Tier 1)

| Excluded Flag | Rationale |
|---------------|-----------|
| `disallow_any_explicit` | Metadata uses `dict[str, Any]` for EXIF data (intrinsically untyped) |
| `disallow_any_expr` | Validators use `Callable[[Any], ...]` for runtime validation |

**Why these exclusions are correct:**
- EXIF metadata has **no compile-time type information** (camera-dependent fields)
- Using `dict[str, Any]` is the **idiomatic Python approach** for dynamic data
- Alternatives (TypedDict per field, wrapper types) add complexity without improving safety
- This is **domain-appropriate** for metadata-centric applications

### Type:ignore Justification

Only **5 type:ignore** comments remain (down from 115):

1. `logger._patched_for_safe_log` — Runtime marker to prevent double-patching
2-3. `sys._MEIPASS` (2×) — PyInstaller-only runtime attribute
4-5. Qt node editor refs (2×) — Qt backward reference limitations

All are **runtime-only attributes** where type:ignore is the correct solution.

### Type Safety Metrics

| Metric | Before (Phase A) | After (Phase E) | Change |
|--------|------------------|-----------------|--------|
| Strictness | 6.0/10 | 8.8/10 | +47% |
| Type:ignore | 115 | 5 | -95.7% |
| Mypy errors | 21 | 0 | -100% |
| Untyped functions (Tier 1+2) | ~200 | 0 | -100% |

---

## Architecture Overview (Legacy Section)

**Note:** The section below describes the pre-Phase-A architecture. For current architecture, see the Executive Summary above.

### MVC-Inspired Four-Tier Design (Legacy)

```
┌─────────────────────────────────────┐
│        UI Layer (PyQt5)             │
├─────────────────────────────────────┤
│  Main Window > Widgets > Behaviors  │
│  ├── FileTableView (976 LOC)        │
│  ├── MetadataTreeView (1768 LOC)    │
│  ├── RenameModulesArea              │
│  └── Behaviors: Selection, DragDrop...│
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
| **FileTableView** | 1 + 3 behaviors | 976 | Display files with columns |
| **MetadataTreeView** | 1 + 4 behaviors | 1768 | Edit file metadata |
| **UnifiedRenameEngine** | 1 | ~400 | Orchestrate rename preview/validation/execution |
| **UnifiedMetadataManager** | 1 | ~300 | Metadata loading & caching |
| **Domain Models** | 4 dataclasses | ~500 | Type-safe data structures |
| **Behaviors** | 7+ files | ~2500 | UI behavior decomposition |
| **Managers** | 30+ | ~8000 | Application-level coordination |
| **Utilities** | 53 | ~5000 | Helpers & common functions |

---

## Recent Improvements (2025-12)

### Phase 7: Final Polish ⚡ (NEW - Dec 2025)
**Goal:** Performance optimization, documentation, and final polish

#### Performance Optimizations [x]
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

### Phase 1: Controllers Architecture [x] (Dec 2025)
**Goal:** Separate UI from business logic with testable controller layer

#### Phase 1A: FileLoadController [x]
- **Orchestrates:** File loading, drag & drop, directory scanning
- **Methods:** `load_files_from_drop()`, `load_folder()`, `clear_files()`
- **Tests:** 11 comprehensive tests (100% coverage)
- **Benefit:** File loading logic testable without Qt/GUI

#### Phase 1B: MetadataController [x]
- **Orchestrates:** Metadata loading, cache management
- **Methods:** `load_metadata()`, `reload_metadata()`, `clear_metadata_cache()`
- **Tests:** 13 comprehensive tests (100% coverage)
- **Benefit:** Metadata workflows testable independently

#### Phase 1C: RenameController [x]
- **Orchestrates:** Rename preview, validation, execution
- **Methods:** `preview_rename()`, `execute_rename()`, `update_preview()`
- **Tests:** 16 comprehensive tests (100% coverage)
- **Benefit:** Rename logic testable with mock dependencies

#### Phase 1D: MainWindowController [x]
- **Orchestrates:** High-level multi-service workflows
- **Methods:** `restore_last_session_workflow()`, `coordinate_shutdown_workflow()`
- **Tests:** 17 comprehensive tests (100% coverage)
- **Benefit:** Complex workflows testable without MainWindow

**Results:**
- 57 new tests (549 → 592, 100% pass rate)
- Clean separation: UI → Controllers → Services
- Zero regressions (all existing functionality preserved)
- Foundation for future CLI/API interfaces

---

### Phase 0: Widget Decomposition [x]
- **FileTableView:** 2715 → 976 LOC (-64%)
  - Extracted: Column management (34 methods)
  - Created: `ColumnManagementBehavior` (composition-based)

- **MetadataTreeView:** 3102 → 1768 LOC (-43%)
  - Extracted: 4 specialized behaviors
  - Improved: Testability and maintainability

### Domain Models [x]
- Created: `FileEntry` (type-safe file representation)
- Created: `MetadataEntry` (structured metadata)
- Benefit: Type safety, memory efficiency, clarity

### Selection Unification [x]
- Created: `SelectionProvider` (unified interface)
- Replaced: 50+ ad-hoc selection patterns
- Benefit: Single source of truth, 500x faster (cached)

### Code Quality [x]
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
│   │   ├── metadata_tree/           # Metadata tree package
│   │   │   ├── view.py              # Tree view (1768 LOC)
│   │   │   ├── worker.py            # Background worker
│   │   │   └── ... (handlers)       # 
│   │   ├── rename_modules_area.py   # Rename config
│   │   └── ... (30+ other widgets)
│   ├── behaviors/                   # Behavior composition
│   │   ├── selection_behavior.py
│   │   ├── drag_drop_behavior.py
│   │   ├── column_management_behavior.py
│   │   └── ... (4+ more)
│   ├── services/                    # UI-layer services
│   │   ├── dialog_manager.py
│   │   └── utility_manager.py
│   └── dialogs/                     # Dialog widgets
│       └── ... (various dialogs)
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
│   ├── filesystem/
│   │   └── file_status_helpers.py   # Canonical metadata/hash cache access
│   ├── metadata/
│   │   └── exiftool_adapter.py      # Low-level ExifTool wrapper
│   ├── icon_cache.py
│   └── ... (50+ helpers)
│
├── scripts/                         # Automation scripts
│   ├── translate_greek_to_english.py
│   ├── fix_module_dates.py
│   └── ... (utilities)
│
├── tests/                           # Test suite
│   ├── test_*.py                    # 866 tests, 100% passing
│   ├── conftest.py
│   └── mocks.py
│
└── docs/                            # Documentation
    ├── ARCHITECTURE.md              # (this file)
    ├── ROADMAP.md                   # Development roadmap
    ├── 2025_12_19.md                # Master plan and status
    └── _archive/                    # Historical phase docs
        └── refactor-runs/           # Phase execution records
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

### 3. Behavior-based Composition
Widget behavior decomposed into composable behaviors:
```python
class FileTableView(QTableView):
    def __init__(self):
        super().__init__()
        # Composition pattern with behaviors
        self._selection_behavior = SelectionBehavior(self)
        self._drag_drop_behavior = DragDropBehavior(self)
        self._column_mgmt_behavior = ColumnManagementBehavior(self)
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

**Test Suite:** 592 tests, 100% passing [x]

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
   - See persistence layer in `core/database/` and `core/cache/`

### Code Reading Tips

- Start with `main.py` (simple entry point)
- Then `ui/main_window.py` (primary UI, delegates to controllers)
- **NEW:** Check `controllers/` for business logic orchestration
- Then specific managers/widgets as needed
- Use behavior files to understand widget behavior
- Check `models/` for data structures
- See `tests/test_*_controller.py` for usage examples

---

## Current Status Summary

### [x] Completed
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

For detailed development plans, see documentation in `docs/` folder:

- State Management improvements
- UI/UX enhancements  
- Core logic optimizations
- Final polish and performance tuning

---

## Reference Documents

| Document | Purpose | Status |
|----------|---------|--------|
| [README.md](README.md) | Documentation index | [x] Active |
| [PHASE5_SUMMARY.md](PHASE5_SUMMARY.md) | Phase 5 summary | [x] Reference |

Historical phase execution plans are archived in `_archive/`.

---

## Naming Guidelines: Controllers, Services, Managers

**Problem:** The codebase has grown to include `*_controller.py`, `*_service.py`, and `*_manager.py` scattered across different layers (`controllers/`, `services/`, `core/`, `core/ui_managers/`). Without clear rules, this becomes confusing and inconsistent.

**Solution:** Use these strict naming and placement rules going forward:

### 1. **Controllers** (`controllers/`)
**Purpose:** UI/application flow orchestration  
**Responsibilities:**
- Handle user actions (button clicks, menu selections)
- Connect UI signals to business logic
- Coordinate between multiple core services/managers
- No direct UI manipulation (delegate to UI layer)
- No direct external I/O (delegate to services)

**Examples:**
- `controllers/file_load_controller.py` — Handles file loading workflow triggered by user
- `controllers/rename_controller.py` — Orchestrates rename preview → validation → execution
- `controllers/metadata_controller.py` — Manages metadata loading requests from UI

**Naming rule:** `<feature>_controller.py` in `controllers/`

---

### 2. **Services** (`services/`)
**Purpose:** Adapters to external world (I/O boundaries)  
**Responsibilities:**
- Filesystem operations (read/write files, directories)
- External tool integration (ExifTool, hash calculators)
- Database operations (SQLite reads/writes)
- Network I/O (if any)
- Pure I/O adapters with minimal business logic

**Examples:**
- `services/filesystem_service.py` — File system operations (list files, check existence)
- `services/exiftool_service.py` — ExifTool wrapper for metadata extraction
- `services/hash_service.py` — File hash computation

**Naming rule:** `<domain>_service.py` in `services/`

**Anti-pattern:** Don't put orchestration or stateful coordination in services. Services should be thin I/O adapters.

---

### 3. **Managers** (`core/`)
**Purpose:** Stateful orchestration + feature-specific coordination  
**Responsibilities:**
- Manage application state for a specific feature
- Coordinate multiple operations within a domain
- Cache management and invalidation
- Event/signal coordination
- Workflow orchestration (multi-step operations)

**Examples:**
- `core/metadata/unified_manager.py` — Orchestrates metadata loading, caching, companion files
- `core/metadata/staging_manager.py` — Manages staged metadata changes before write
- `core/backup_manager.py` — Coordinates backup creation/restoration
- `core/ui_managers/status_manager.py` — Manages status bar state and messages
- `core/batch/operations_manager.py` — Batches operations for performance

**Naming rule:** `<feature>_manager.py` in `core/<domain>/` or `core/ui_managers/`

**Special case - UI Managers:** Put UI-specific managers in `core/ui_managers/` (e.g., `status_manager.py`, `window_config_manager.py`, `column_manager.py`). These manage UI state but are NOT controllers (they don't handle user actions).

---

### 4. **Utils** (`utils/`)
**Purpose:** Stateless, reusable helper functions  
**Responsibilities:**
- Pure functions (no side effects)
- Data transformation and formatting
- Path normalization, validation
- Small composable utilities
- No I/O, no state, no signals

**Examples:**
- `utils/path_normalizer.py` — Path string manipulation
- `utils/logger_factory.py` — Logger creation
- `utils/cursor_helper.py` — Wait cursor context manager
- `utils/filesystem/file_status_helpers.py` — Cache access helpers (uses ApplicationContext)

**Naming rule:** `<domain>_<purpose>.py` in `utils/<domain>/`

**Anti-pattern:** Don't put I/O or orchestration in utils. If it touches files/DB/network → `services/`. If it coordinates → `core/`.

---

### Quick Decision Tree

```
Does it handle user actions or UI flow?
  ├─ YES → Controller (controllers/)
  └─ NO  ↓

Does it perform I/O (files, DB, external tools)?
  ├─ YES → Service (services/)
  └─ NO  ↓

Does it manage state or coordinate multiple operations?
  ├─ YES → Manager (core/)
  └─ NO  ↓

Is it a pure helper function?
  └─ YES → Util (utils/)
```

---

### Examples in Current Codebase

[x] **Good (follows rules):**
- `controllers/file_load_controller.py` — UI flow orchestration
- `services/exiftool_service.py` — External tool adapter
- `core/metadata/unified_manager.py` — Stateful metadata orchestration
- `utils/path_normalizer.py` — Pure path helper

⚠️ **Legacy (grandfathered, don't replicate):**
- `core/ui_managers/*` — UI managers (should ideally be in controllers or separate layer, but kept for historical reasons)
- Some `*_manager.py` scattered in `core/` root — Should be in feature folders like `core/<domain>/`

---

### Migration Strategy

**For new code:** Follow the rules above strictly.

**For existing code:** 
- Don't rename unless it causes real confusion
- Document exceptions in this file
- Refactor opportunistically (when touching the file anyway)

---

## Layering Rules

### Core vs Utils Separation

To avoid architectural confusion, follow these rules when placing code:

**`oncutf/core/*`** — Business logic, orchestration, workflows:
- Metadata loading orchestration (workflows, cache coordination)
- File operations (rename validation, execution, rollback)
- Services that bind to application state or managers
- Domain-specific logic with side effects (I/O, signals, threading)
- **Example:** `core/metadata/metadata_loader.py` (orchestrates parallel loading)

**`oncutf/utils/*`** — Pure helpers, formatters, small composable functions:
- Path normalization, filename validation
- Metadata formatting/parsing (no I/O)
- Logging factories, cursor helpers
- Reusable functions without side effects or state dependencies
- **Example:** `utils/filesystem/file_status_helpers.py` (cache access helpers)

**When in doubt:** If it coordinates multiple services or performs I/O → `core/`. If it's a stateless helper → `utils/`.

### UI Organization

**`oncutf/ui/dialogs/*`** — All dialog widgets:
- Progress dialogs, confirmation dialogs, input dialogs
- Self-contained UI units with their own lifecycle
- **No exceptions:** All dialog widgets belong here (not in `ui/widgets/` or elsewhere)

**`oncutf/ui/services/*`** — UI-layer helpers and managers:
- `dialog_manager.py` (dialog creation/coordination)
- `utility_manager.py` (UI utilities)
- Column managers, splitter managers, shortcut managers
- **Rule:** UI "managers" live under `ui/services/`, NOT `core/`

**`oncutf/core/*`** — Business logic only (no UI-specific code)

### Known Technical Debt

- **Metadata loader separation:** `utils/metadata/exiftool_adapter.py` is the low-level ExifTool wrapper, while `core/metadata/metadata_loader.py` is the orchestration layer. The separation is now clear with proper naming (adapter vs loader).

---

## Contributing

When modifying architecture:

1. **Use controllers for orchestration** — Don't put business logic in UI
2. **Keep behaviors focused** — One responsibility per behavior
3. **Use domain models** — Don't pass dicts around
4. **Test new code** — Especially business logic in controllers
5. **Document changes** — Update this file if needed
6. **Consider impact** — Check for ripple effects
7. **Follow layering rules** — See section above for core/utils/ui boundaries

---

*Last Updated: 2025-12-29 — Added "Naming Guidelines: Controllers, Services, Managers" section*
