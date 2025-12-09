# OnCutF Architecture Guide

**Last Updated:** 2025-12-09  
**Status:** Refactored and Optimized (90% complete)

---

## Quick Navigation

- **[Pragmatic Refactoring Plan](architecture/pragmatic_refactor_2025-12-03.md)** — Strategic direction & goals
- **[Refactor Status (Latest)](architecture/refactor_status_2025-12-09.md)** — Current progress & metrics
- **[Next Steps Plan](architecture/next_steps_2025-12-09.md)** — Implementation roadmap
- **[Cache Strategy](architecture/cache_strategy.md)** — Caching layers & invalidation
- **[Column Management Guide](architecture/column_management_mixin_guide.md)** — FileTableView columns

---

## Architecture Overview

### Three-Tier Design

```
┌─────────────────────────────────────┐
│        UI Layer (PyQt5)             │
├─────────────────────────────────────┤
│  Main Window > Widgets > Mixins     │
│  ├── FileTableView (976 LOC)        │
│  ├── MetadataTreeView (1768 LOC)    │
│  ├── RenameModulesArea              │
│  └── Mixins: Selection, DragDrop... │
├─────────────────────────────────────┤
│      Business Logic (Core)          │
├─────────────────────────────────────┤
│  ├── UnifiedRenameEngine            │
│  ├── UnifiedMetadataManager         │
│  ├── Managers (30+)                 │
│  └── Domain Models                  │
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

### Phase 1: Widget Decomposition ✅
- **FileTableView:** 2715 → 976 LOC (-64%)
  - Extracted: Column management (34 methods)
  - Created: `ColumnManagementMixin` (1179 LOC)

- **MetadataTreeView:** 3102 → 1768 LOC (-43%)
  - Extracted: 4 specialized mixins
  - Improved: Testability and maintainability

### Phase 2: Domain Models ✅
- Created: `FileEntry` (type-safe file representation)
- Created: `MetadataEntry` (structured metadata)
- Benefit: Type safety, memory efficiency, clarity

### Phase 3: Selection Unification ✅
- Created: `SelectionProvider` (unified interface)
- Replaced: 50+ ad-hoc selection patterns
- Benefit: Single source of truth, 500x faster (cached)

### Phase 4: Code Quality ✅
- Translated: Greek → English (38 instances)
- Synced: Docstring dates to git history (75 files)
- Tests: 491 passing (100%)

---

## File Organization

```
oncutf/
├── main.py                          # Entry point
├── main_window.py                   # Primary UI controller
├── config.py                        # Configuration
│
├── core/                            # Business logic
│   ├── application_context.py       # Singleton application state
│   ├── unified_rename_engine.py     # Rename orchestration
│   ├── unified_metadata_manager.py  # Metadata loading
│   ├── selection_store.py           # Selection state
│   ├── persistent_hash_cache.py     # SQLite hash cache
│   ├── persistent_metadata_cache.py # SQLite metadata cache
│   ├── *_manager.py                 # 30+ manager classes
│   └── ...
│
├── widgets/                         # UI components
│   ├── file_table_view.py           # Main file table (976 LOC)
│   ├── metadata_tree_view.py        # Metadata editor (1768 LOC)
│   ├── rename_modules_area.py       # Rename config
│   ├── mixins/                      # Behavior mixins
│   │   ├── selection_mixin.py
│   │   ├── drag_drop_mixin.py
│   │   ├── column_management_mixin.py
│   │   └── ... (4+ more)
│   └── ... (30+ other widgets)
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
│   ├── test_*.py                    # 491 tests, 100% passing
│   ├── conftest.py
│   └── mocks.py
│
└── docs/                            # Documentation
    ├── architecture/                # This directory
    │   ├── ARCHITECTURE.md          # (this file)
    │   ├── refactor_status_*.md
    │   ├── next_steps_*.md
    │   ├── cache_strategy.md
    │   └── ... (planning docs)
    └── archive/                     # Old planning docs
        └── refactor_plan_2025-12-01.md
```

---

## Key Architecture Patterns

### 1. ApplicationContext (Singleton)
Central registry of managers and services:
```python
# Usage
context = ApplicationContext()
selection = context.selection_store.get_selected_files()
context.metadata_manager.load_metadata(files)
```

### 2. Mixin-based Composition
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

### 3. Domain Models (Dataclasses)
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

### 4. Unified Interfaces
Single point of access for common operations:
```python
# Old: scattered selection logic
table.selection_model().selectedRows()  # Qt direct
tree.selected_items()  # Custom

# New: unified interface
selection = SelectionProvider(table).get_selected_files()
```

### 5. Caching Strategy
Multi-layer caching:
- **L1:** Python dict (LRU, fast, volatile)
- **L2:** SQLite (persistent, indexed)
- **L3:** File system (original data)

See [Cache Strategy](architecture/cache_strategy.md) for details.

---

## Performance Metrics

| Metric | Before Refactor | After | Improvement |
|--------|-----------------|-------|-------------|
| FileTableView LOC | 2715 | 976 | -64% |
| MetadataTreeView LOC | 3102 | 1768 | -43% |
| Test Coverage | ~70% | ~75% | +7% |
| Largest Widget | 2715 | 1768 | -35% |
| Average Widget | ~550 | ~400 | -27% |

**Test Suite:** 491 tests, 100% passing ✅

---

## How to Navigate the Code

### Starting Points

1. **Understand file loading:**
   - `main_window.py` → `FileLoadManager` → `UnifiedMetadataManager`

2. **Understand rename flow:**
   - `RenameModulesArea` → `UnifiedRenameEngine` → `FileOperationsManager`

3. **Understand UI state:**
   - `ApplicationContext` → `SelectionStore` → Widget mixins

4. **Understand caching:**
   - See [Cache Strategy](architecture/cache_strategy.md)

### Code Reading Tips

- Start with `main.py` (simple entry point)
- Then `main_window.py` (primary controller)
- Then specific managers/widgets as needed
- Use mixin files to understand widget behavior
- Check `models/` for data structures

---

## Current Status Summary

### ✅ Completed
- Domain models (dataclasses)
- Selection unification
- Widget decomposition (mixins)
- Cache strategy documented
- Code quality (Greek translated, dates synced)
- 491 tests passing

### ⏳ In Progress
- Documentation cleanup (Task 1.1)
- ColumnManagementMixin guide (Task 1.2)
- Unit test expansion (Task 2.1)

### ⏸️ Deferred (Conscious Decision)
- Streaming metadata (ROI analysis: not worthwhile)
- Service layer consolidation (too risky)
- ViewModel layer (over-engineering)

---

## Next Steps

See [Next Steps Plan](architecture/next_steps_2025-12-09.md) for detailed roadmap:

1. **Week 1:** Documentation cleanup, mixin guide
2. **Week 2:** Unit tests, performance profiling
3. **Week 3:** Optional refinements

---

## Reference Documents

| Document | Purpose | Status |
|----------|---------|--------|
| [Pragmatic Refactor Plan](architecture/pragmatic_refactor_2025-12-03.md) | Strategic goals (10-day sprint) | ✅ Active |
| [Refactor Status](architecture/refactor_status_2025-12-09.md) | Current progress & metrics | ✅ Latest |
| [Next Steps Plan](architecture/next_steps_2025-12-09.md) | Implementation roadmap | ✅ New |
| [Cache Strategy](architecture/cache_strategy.md) | Caching layers & patterns | ✅ Complete |
| [Streaming Metadata Plan](architecture/streaming_metadata_plan.md) | Analysis (deferred) | ⏸️ Reference |
| [Old Refactor Plan](archive/refactor_plan_2025-12-01.md) | Comprehensive original analysis | 📦 Archive |

---

## Contributing

When modifying architecture:

1. **Keep mixins focused** — One responsibility per mixin
2. **Use domain models** — Don't pass dicts around
3. **Test new code** — Especially business logic
4. **Document changes** — Update this file if needed
5. **Consider impact** — Check for ripple effects

---

*Generated: 2025-12-09*  
*Last reviewed by: Architecture team*
