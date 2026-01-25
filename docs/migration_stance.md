# Migration Stance — Architecture Evolution Guide

**Author:** Michael Economou  
**Date:** 2026-01-01  
**Last Updated:** 2026-01-25  
**Status:** Active policy document — Phase E Complete (Typing Tightening)

---

## Executive Summary

The oncutf codebase is transitioning from a **classic manager-based architecture** to a
**modern layered architecture** (Controllers → Services → Domain → UI). This document
defines **which patterns to use when**, preventing "hybrid forever" syndrome.

---

## The Two Architectures

### [LEGACY] Legacy Pattern (Maintenance Mode)

```
┌──────────────────────────────────────────┐
│          MainWindow (UI God Object)      │
│  ├── ui_managers/*_manager.py            │
│  ├── core/*_manager.py (some)            │
│  └── Direct service calls from UI        │
└──────────────────────────────────────────┘
```

**Characteristics:**
- UI directly orchestrates business logic
- Managers tightly coupled to Qt widgets
- State scattered across managers and UI
- Hard to test without full Qt instantiation

**Status:** [STOP] **MAINTENANCE MODE**
- Bug fixes only
- No new features
- No new managers in `ui_managers/`
- Gradual migration to new architecture

### [ACTIVE] Modern Pattern (Active Development)

```
┌──────────────────────────────────────────┐
│            UI Layer (Views + Behaviors)  │
│  ├── Widgets are "dumb" — display only   │
│  ├── Behaviors handle UI interactions    │
│  └── Handlers route events               │
│                  ↓                        │
├──────────────────────────────────────────┤
│          Controllers (oncutf/controllers/)│
│  ├── UI-agnostic orchestration           │
│  ├── Testable without Qt                 │
│  └── Coordinate multiple services        │
│                  ↓                        │
├──────────────────────────────────────────┤
│          Core Services (oncutf/core/)    │
│  ├── Business logic encapsulation        │
│  ├── Protocol-based interfaces           │
│  └── Cacheable, composable               │
│                  ↓                        │
├──────────────────────────────────────────┤
│          Domain (oncutf/domain/)         │
│  ├── Pure data models (dataclasses)      │
│  ├── No Qt dependencies                  │
│  └── Business rules                      │
└──────────────────────────────────────────┘
```

**Status:** [OK] **ACTIVE DEVELOPMENT**
- All new features go here
- Existing features migrate here

---

## Decision Rules

### For NEW Features

| Question | Answer |
|----------|--------|
| Where does orchestration logic go? | `oncutf/controllers/` |
| Where does business logic go? | `oncutf/core/` (services) |
| Where do data models go? | `oncutf/domain/` |
| Where does UI behavior go? | `oncutf/ui/behaviors/` |
| Where do event handlers go? | `oncutf/ui/widgets/*/handlers/` |

### For Bug Fixes in Legacy Code

1. **Quick fix:** Patch in place, add `# TODO: Migrate to controllers` comment
2. **Medium fix:** If touching >20 lines, consider extracting to controller
3. **Major fix:** Always migrate to modern pattern

### DO NOT

[X] Add new methods to `ui_managers/*_manager.py`  
[X] Add new methods to `MainWindow` directly  
[X] Create new mixins in `ui/mixins/`  
[X] Put business logic in UI widgets  
[X] Create new `*_manager.py` files in `ui_managers/`  

### DO

[+] Create new controllers for new workflows  
[+] Use behaviors for reusable UI interactions  
[+] Use services/protocols for business logic  
[+] Keep widgets as thin display shells  
[+] Write tests for controllers (no Qt needed)  

---

## Module Migration Status

### Controllers (Modern) [DONE]

| Controller | Status | Migrated From |
|------------|--------|---------------|
| `FileLoadController` | [DONE] Complete | `FileLoadManager` + MainWindow |
| `MetadataController` | [DONE] Complete | `UnifiedMetadataManager` calls |
| `RenameController` | [DONE] Complete | `UnifiedRenameEngine` calls |
| `MainWindowController` | [DONE] Complete | MainWindow orchestration |

### Legacy Managers → Migration Target

| Legacy Manager | Target | Priority |
|----------------|--------|----------|
| `ui_managers/ui_manager.py` | Split to specialized controllers | [HIGH] High |
| `ui_managers/column_manager.py` | `UnifiedColumnService` (exists) | [HIGH] High |
| `core/events/context_menu_handlers.py` | Split by domain | [HIGH] High |
| `core/file/load_manager.py` | Already uses `FileLoadController` | [MED] Medium |
| `core/metadata/operations_manager.py` | Merge into `MetadataController` | [MED] Medium |

### Single Source of Truth (Canonical Services)

| Domain | Canonical Module | Adapters/Facades |
|--------|------------------|------------------|
| **Rename Pipeline** | `UnifiedRenameEngine` | — |
| **Column Management** | `UnifiedColumnService` | `ColumnManager`, `ColumnManagementBehavior` |
| **Metadata Loading** | `UnifiedMetadataManager` | `MetadataController` |
| **File Operations** | `FileLoadController` | `FileLoadManager` |

---

## Migration Workflow

When migrating a manager to the modern architecture:

### 1. Create Controller/Service

```python
# oncutf/controllers/new_feature_controller.py
class NewFeatureController:
    """UI-agnostic orchestration for new feature."""
    
    def __init__(self, service: SomeService):
        self._service = service
    
    def perform_action(self, data: SomeData) -> Result:
        """Orchestrate the action without Qt dependencies."""
        return self._service.do_something(data)
```

### 2. Update Legacy Manager to Delegate

```python
# oncutf/ui_managers/old_manager.py
class OldManager:
    """LEGACY: Delegates to NewFeatureController."""
    
    def __init__(self, main_window):
        self._controller = NewFeatureController(...)
    
    def old_method(self):
        """Backward compatibility - delegates to controller."""
        return self._controller.perform_action(...)
```

### 3. Update UI to Use Controller

```python
# oncutf/ui/main_window.py
def some_action(self):
    # OLD: self.old_manager.old_method()
    # NEW:
    result = self._new_feature_controller.perform_action(data)
    self._update_ui(result)
```

### 4. Add Tests for Controller

```python
# tests/controllers/test_new_feature_controller.py
def test_perform_action():
    mock_service = Mock()
    controller = NewFeatureController(mock_service)
    result = controller.perform_action(test_data)
    assert result.success
```

### 5. Remove Legacy Manager (Eventually)

Once all callers use the controller, mark manager for removal:

```python
class OldManager:
    """DEPRECATED: Will be removed in v2.0. Use NewFeatureController."""
```

---

## Quality Gates

Before merging migration PRs:

1. **Tests pass:** `pytest` (1154/1161 tests passing — 99.4%)
2. **No regressions:** Existing functionality works
3. **Lint clean:** `ruff check .` (0 violations)
4. **Type check:** `mypy .` (0 errors in 548 files)
5. **Type safety:** Strictness 8.8/10, type:ignore count ≤5
6. **Controller tested:** New controllers have >90% coverage
7. **Docstring coverage:** Maintain 99%+ coverage

---

## Delegator Files Policy

Delegator files (re-export modules that redirect to new locations) are useful for migration but risky if permanent.

### When Delegators are OK

- **Public API stability:** Keeping `from oncutf.utils import something` working
- **Migration period:** 1-2 releases maximum
- **Always include:** Deprecation warning + link to new location

### Delegator Template

```python
"""Delegator module for backward compatibility.

DEPRECATED: This module will be removed in v2.0.
Use `oncutf.core.new_location` instead.

Author: Michael Economou
Date: 2026-01-01
"""
import warnings

warnings.warn(
    "oncutf.old_location is deprecated. Use oncutf.core.new_location instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for compatibility
from oncutf.core.new_location import *  # noqa: F401, F403
```

### Delegator Cleanup Rules

1. **Mark with removal version** in docstring
2. **Log deprecation warning** on import
3. **Remove after 2 releases** or when no internal usage remains
4. **Track in this document** if widely used

### Current Delegators

| Delegator | Points To | Removal Target |
|-----------|-----------|----------------|
| (none currently) | — | — |

---

## Node Editor Architecture (Future)

The codebase is prepared for future Node Editor implementation. Key integration points:

### Current Foundation

```
oncutf/controllers/
    module_orchestrator.py      <- Brain for rename modules
    module_drag_drop_manager.py <- UI drag/drop handling
```

The `ModuleOrchestrator` explicitly states: "separates module business logic from UI concerns to enable future node editor implementation."

### Planned Structure

```
oncutf/
    core/
        rename_graph/           <- NEW: Graph model (pure data)
            __init__.py
            graph_model.py      <- Node/edge data structures
            graph_validator.py  <- Connection rules
            graph_executor.py   <- Execute rename pipeline
    
    ui/
        widgets/
            node_editor/        <- NEW: Node editor UI
                __init__.py
                canvas.py       <- Main canvas widget
                node_widget.py  <- Individual node rendering
                connection.py   <- Edge rendering
                handlers/
                    selection_handler.py
                    connection_handler.py
```

### Integration Rules

1. **Graph model is domain** - no Qt dependencies in `rename_graph/`
2. **Node editor is pure UI** - only rendering and user interaction
3. **Orchestrator is the bridge** - connects UI events to graph operations
4. **Do NOT put graph logic in widgets** - keep rename_module_widget.py as UI only

### Migration Path

1. [FUTURE] Create `rename_graph/` with pure Python graph model
2. [FUTURE] Update `ModuleOrchestrator` to work with graph model
3. [FUTURE] Create `node_editor/` widgets
4. [FUTURE] Keep existing linear UI as alternative view

---

## Phase E Completion — Type Safety Tightening (2026-01-25)

### Overview

Phase E achieved **pragmatic strict typing** across the codebase with 8.8/10 strictness while maintaining 0 mypy errors. The key insight: full strict mode is inappropriate for metadata-centric applications.

### Three-Tier Typing Strategy

```
Tier 1 (app/domain/infra):
  ├─ Pragmatic Strict Mode (10/12 strict flags)
  ├─ Excluded: disallow_any_explicit, disallow_any_expr
  └─ Rationale: Metadata domain uses dict[str, Any] for EXIF

Tier 2 (controllers/core/models):
  ├─ Strict typing (disallow_untyped_defs)
  └─ ~200 files, 0 errors

Tier 3 (UI/Qt):
  ├─ Selective suppressions (13 Qt-specific)
  └─ ~300 files, logic bugs still caught
```

### Key Decisions

**1. Pragmatic Exclusions (Tier 1)**
- **disallow_any_explicit:** Metadata uses `dict[str, Any]` for EXIF data (intrinsically untyped)
- **disallow_any_expr:** Validators need `Callable[[Any], ...]` for runtime validation
- **Why correct:** Camera-dependent fields make `dict[str, Any]` idiomatic, not lazy

**2. Type:ignore Reduction**
- Started: 115 type:ignore comments
- Finished: 5 type:ignore comments (95.7% reduction)
- Remaining 5: All justified (Qt stubs, metaclass patterns)

**3. Strictness Metrics**
- Phase start: 6.0/10 strictness
- Phase end: 8.8/10 strictness (+47%)
- Result: Production-ready type safety

### Lessons Learned

**✅ DO:**
- Choose typing strictness appropriate for domain
- Document why certain strict flags are excluded
- Use three-tier strategy for gradual migration
- Reduce type:ignore comments systematically
- Test with `mypy . 2>&1 | grep -oE '\[.*\]' | sort | uniq -c` to find error patterns

**❌ DON'T:**
- Force full strict mode on metadata-centric apps
- Add type:ignore without justification
- Mix typing strictness within same tier
- Skip documentation of pragmatic choices

### Phase E Commits

| Part | Description | Commit | Impact |
|------|-------------|--------|--------|
| 3 | Remove obsolete type:ignore | 76b5b9c7 | -104 type:ignore |
| 4 | Enable disallow_untyped_defs (Tier 2) | f9f61a48 | ~200 files strict |
| 5 | Reduce type:ignore to 5 | 4f2c8be3 | 11→5 type:ignore |
| 5b | Fix mypy unreachable warnings | 2af01cd4 | Cleaner control flow |
| 6 | Pragmatic strict mode (Tier 1) | 26f90d80 | 8.8/10 strictness |

---

## Dependency Management Best Practices (2026-01-25)

### PyProject.toml Configuration

**Runtime Dependencies:**
```toml
[project]
dependencies = [
    "PyQt5>=5.15.11",          # Core only, not sub-deps
    "Pillow>=10.1.0",          # Python 3.12 wheels
    "rawpy>=0.24.0",           # Python 3.12 wheels
]
```

**Dev Dependencies:**
```toml
[project.optional-dependencies]
dev = [
    "PyQt5-stubs>=5.15.6.0",  # Type stubs for dev only
    "ruff>=0.3.0",             # Single formatter (not black)
    "mypy>=1.8.0",
]
```

### Key Decisions

**1. Clean PyQt5 Dependencies**
- ❌ Old: `PyQt5`, `PyQt5-Qt5`, `PyQt5-sip` in runtime
- ✅ New: Only `PyQt5` in runtime (sub-deps auto-installed)
- Rationale: Prevents resolver constraint conflicts

**2. Python 3.12 Wheel Compatibility**
- ❌ Old: `Pillow>=9.0.0` (no 3.12 wheels)
- ✅ New: `Pillow>=10.1.0` (3.12 wheels available)
- ❌ Old: `rawpy>=0.21.0` (limited 3.12 support)
- ✅ New: `rawpy>=0.24.0` (3.12 wheels verified)

**3. Packaging for Distribution**
```toml
[tool.setuptools]
include-package-data = true

[tool.setuptools.package-data]
oncutf = [
    "../resources/fonts/**/*.ttf",
    "../resources/icons/**/*.svg",
    "../resources/icons/**/*.png",
    "../resources/images/**/*.png",
    "../resources/styles/**/*.qss",
]
```
- Runtime assets (fonts, icons, qss) included in wheel
- Located in `resources/` at project root (not in `oncutf/` package)

**4. Single Formatter Policy**
- ❌ Old: Both `black` and `ruff format`
- ✅ New: Only `ruff format`
- Rationale: Avoid dual formatter conflicts

**5. Mypy Tier Isolation**
```toml
[tool.mypy]
ignore_missing_imports = true  # Base: external packages

[[tool.mypy.overrides]]
module = ["oncutf.*"]
ignore_missing_imports = false  # Tiers: strict on our code
```
- Base config: Tolerant of external packages
- Overrides: Strict on internal code
- Result: Proper tier isolation

### Commit

- **e0533afe:** Clean pyproject.toml per resolver/packaging best practices

---

## References

- [ARCHITECTURE.md](ARCHITECTURE.md) — Overall system architecture
- [_archive/UI_ARCHITECTURE_PATTERNS_COMPLETED.md](_archive/UI_ARCHITECTURE_PATTERNS_COMPLETED.md) — Mixins vs Behaviors vs Handlers (archived)
- [_archive/mixin_to_behavior_extraction_COMPLETED.md](_archive/mixin_to_behavior_extraction_COMPLETED.md) — Behavior extraction guide (archived)
- [_archive/REFACTORING_ROADMAP_COMPLETED.md](_archive/REFACTORING_ROADMAP_COMPLETED.md) — Refactoring history (archived)
