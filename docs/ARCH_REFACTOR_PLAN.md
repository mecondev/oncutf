# OnCutF Architecture Refactoring Plan

> **Status**: DRAFT v1.0  
> **Created**: December 2025  
> **Author**: Architecture Review Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Analysis](#2-current-architecture-analysis)
3. [Critical Problems Root Cause Analysis](#3-critical-problems-root-cause-analysis)
4. [Target Architecture](#4-target-architecture)
5. [Phase 0: Project Restructuring](#5-phase-0-project-restructuring)
6. [Phased Refactoring Plan](#6-phased-refactoring-plan)
7. [Naming & API Consistency Audit](#7-naming--api-consistency-audit)
8. [Node Editor Integration Strategy](#8-node-editor-integration-strategy)
9. [Risk Assessment & Mitigation](#9-risk-assessment--mitigation)

---

## 1. Executive Summary

### Current State

OnCutF is a PyQt5 desktop application (~100k LOC) for batch file renaming with
EXIF/metadata support. The codebase has grown organically and exhibits several
architectural issues:

- **Flat project structure** mixing application code with tooling
- **Inconsistent layering** with UI performing business logic
- **Counter/rename conflicts** after multi-folder imports
- **Stale preview states** due to poor state management
- **Metadata module issues** with ComboBox styling and EXIF fetching

### Refactoring Goals

1. **Clean project structure** with `oncutf/` package boundary
2. **Strict architectural layers** (UI → Controllers → Domain → Services)
3. **Fix all 6 critical problems** with correct root cause solutions
4. **Node editor foundation** for future rename pipeline UX
5. **Stable, testable codebase** with safety rail tests

### Approach

- **Phase 0**: File moves only (no logic changes)
- **Phases 1-5**: Incremental architectural fixes
- **One commit per step** with clear DoD

---

## 2. Current Architecture Analysis

### 2.1 Project Structure Issues

```
project_root/           # ❌ Flat - app code next to tooling
├─ .vscode/             # Tooling
├─ .pytest_cache/       # Tooling  
├─ .ruff_cache/         # Tooling
├─ main.py              # Entry point
├─ main_window.py       # Main UI (1309 lines!)
├─ config.py            # Config (mixed concerns)
├─ core/                # 60+ files - too many!
├─ modules/             # Rename modules
├─ widgets/             # UI widgets
├─ utils/               # Utilities (56 files!)
├─ models/              # Data models (good)
└─ tests/               # Tests (good location)
```

**Problems**:
- No package boundary - hard to reason about imports
- `core/` has 60+ files mixing managers, stores, engines
- `utils/` is a dumping ground (56 files)
- Entry point at root level

### 2.2 Module Responsibilities (Smell Map)

| Module | Lines | Issues |
|--------|-------|--------|
| `main_window.py` | 1309 | Too large, orchestration mixed with UI |
| `core/unified_rename_engine.py` | 1163 | Good structure but coupled to Qt |
| `core/event_handler_manager.py` | 1523 | God object - handles everything |
| `core/file_load_manager.py` | 661 | Multiple responsibilities |
| `utils/preview_engine.py` | 165 | Logic should be in domain layer |
| `modules/metadata_module.py` | 530 | Mixed UI and logic |

### 2.3 Dependency Graph Issues

```
main_window.py
    ├── imports 30+ modules directly
    ├── creates managers inline
    ├── holds global state
    └── performs business logic

core/application_context.py (singleton)
    ├── _file_store
    ├── _selection_store  
    ├── _metadata_cache (dict - not typed)
    └── _managers (dict - loose coupling)
```

**Key Issues**:
1. **Circular imports** prevented only by TYPE_CHECKING guards
2. **Singleton abuse** in ApplicationContext
3. **No dependency injection** - hard to test
4. **Widget → Manager → Widget cycles**

### 2.4 State Management Problems

```python
# Multiple sources of truth for "current files":
main_window.file_model.files        # Model state
application_context._files          # Context state
file_store._loaded_files            # Store state
file_table_view selected_rows       # UI state

# Preview state scattered:
preview_engine._module_cache        # Global dict
unified_rename_engine.SmartCacheManager  # Instance
metadata_module._metadata_cache     # Module-level global
```

---

## 3. Critical Problems Root Cause Analysis

### Problem 1: Counter Conflicts After Multi-Folder Import

**Symptoms**:
- Duplicate numbers when importing multiple folders
- Unstable ordering
- Incorrect counter ranges

**Root Cause Analysis**:

```python
# preview_engine.py line 82-87
if module_type == "counter":
    start = data.get("start", 1)
    step = data.get("step", 1)
    value = start + (index * step)  # ← index is GLOBAL across all files
```

The counter uses the global `index` position in the file list, but when
multiple folders are imported:
1. Files from folder A get indices 0-99
2. Files from folder B get indices 100-199
3. Counter starts at 1 for ALL files, not per-folder

**Proposed Fix**:
- Introduce `FolderGroup` concept in `RenamePlan`
- Counter resets per folder group OR uses explicit "continue from previous"
- Add `counter_scope` setting: `global | per_folder | per_selection`

**User-Visible Outcome**:
Counter numbering respects folder boundaries with explicit user control.

**Validation Method**:
- Unit test: Import 2 folders with 5 files each, counter should reset
- Integration test: Preview shows correct numbers per folder

---

### Problem 2: Metadata Rename Module Issues

**Symptoms**:
- ComboBox doesn't respect QSS styling
- EXIF metadata not fetched correctly
- Preview not updated immediately when settings change

**Root Cause Analysis**:

```python
# metadata_module.py - UI and logic mixed in same class
class MetadataModule:
    @staticmethod
    def apply_from_data(data, file_item, index, metadata_cache):
        # Complex logic here, not in domain layer
        # Uses global _metadata_cache - stale state
```

```python
# ComboBox styling issue:
# metadata_widget.py creates combo without proper delegate
self.category_combo = QComboBox()
# Missing: setItemDelegate(ComboBoxItemDelegate(...))
```

**Proposed Fix**:
1. Split into `MetadataModuleWidget` (UI) and `MetadataExtractor` (domain)
2. Add `ComboBoxItemDelegate` to all combo boxes
3. Emit signal on ANY setting change, connect to preview refresh
4. Replace global cache with injected `MetadataService`

**User-Visible Outcome**:
ComboBox styled consistently, metadata loads correctly, preview updates instantly.

**Validation Method**:
- Visual test: ComboBox matches theme
- Unit test: Setting change → signal emitted
- Integration test: Select metadata field → preview updates

---

### Problem 3: Text Removal Module Not Usable

**Symptoms**:
- UX unclear
- Edge cases not handled
- Preview doesn't reflect changes

**Root Cause Analysis**:

```python
# text_removal_module.py - insufficient feedback
def apply_to_name(self, original_name: str) -> str:
    # No preview of WHAT will be removed
    # No highlighting of match locations
    # Regex errors silently swallowed
```

**Proposed Fix**:
1. Add live preview showing match highlights (red strikethrough)
2. Show "No matches" message explicitly
3. Add regex validation with error display
4. Implement proper edge cases:
   - Empty result handling
   - Multiple matches display
   - Escape sequence support

**User-Visible Outcome**:
User sees exactly what will be removed with visual highlighting.

**Validation Method**:
- Unit test: Edge cases (empty input, no match, all removed)
- UI test: Match highlighting visible

---

### Problem 4: UI Consistency and UX

**Symptoms**:
- Visual inconsistency
- Unpredictable workflow

**Root Cause Analysis**:
- Multiple styling approaches (ThemeEngine + ThemeManager + inline)
- No design system / component library
- Inconsistent spacing/margins across widgets

**Proposed Fix**:
1. Consolidate to single `ThemeManager` (token-based)
2. Create `ui/components/` with base styled widgets
3. Define spacing constants in theme tokens
4. Document UX patterns in `docs/UX_GUIDELINES.md`

**User-Visible Outcome**:
Consistent look and feel across all UI elements.

**Validation Method**:
- Visual regression tests
- Theme token audit script

---

### Problem 5: Flat/Messy Project Structure

**Root Cause**: Organic growth without package boundaries.

**Proposed Fix**: See [Phase 0](#5-phase-0-project-restructuring).

---

### Problem 6: Rename Modules UI Not Usable

**Symptoms**:
- Module arrangement unclear
- Can't visualize rename pipeline
- No way to save/load rename presets

**Root Cause Analysis**:
- Linear list UI doesn't show data flow
- No pipeline concept in data model
- Modules tightly coupled to widget positions

**Proposed Fix**:
See [Section 8: Node Editor Integration](#8-node-editor-integration-strategy).

---

## 4. Target Architecture

### 4.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      UI Layer (PyQt5)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Windows  │  │ Dialogs  │  │ Widgets  │  │Delegates │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │             │             │             │            │
│       └─────────────┴──────┬──────┴─────────────┘            │
│                            ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Controllers / Presenters                │    │
│  │   (Orchestration, UI↔Domain translation)            │    │
│  └────────────────────────┬────────────────────────────┘    │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer (Pure Python)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │RenamePipeline│  │ConflictResolver│  │  Validators │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ RenameModule │  │MetadataExtract│  │ PreviewEngine│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Services Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │FilesystemSvc │  │ ExifToolSvc  │  │  HashService │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ConfigService│  │ CacheService │  │DatabaseService│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Key Principles

1. **UI Layer**: Qt widgets only, NO business logic
2. **Controllers**: Translate UI events → domain operations
3. **Domain Layer**: Pure Python, fully testable, Qt-free
4. **Services**: I/O operations (filesystem, exiftool, database)
5. **Models**: Typed dataclasses (`FileItem`, `RenamePlan`, etc.)

### 4.3 Data Flow

```
User Action → UI Event → Controller → Domain Logic → Service I/O
                                   ↓
                            PreviewResult
                                   ↓
                            Controller
                                   ↓
                            UI Update
```

### 4.4 Dependency Rules

- UI may import Controllers, Models (never Domain/Services directly)
- Controllers may import Domain, Services, Models
- Domain may import Models only (never Services)
- Services may import Models only
- Models are leaf nodes (no imports from app)

---

## 5. Phase 0: Project Restructuring

### 5.1 Target Layout

```
project_root/
├── oncutf/                      # Application package
│   ├── __init__.py              # Version, public API
│   ├── __main__.py              # python -m oncutf
│   ├── app.py                   # QApplication bootstrap
│   │
│   ├── ui/                      # UI Layer
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── dialogs/
│   │   │   ├── __init__.py
│   │   │   ├── metadata_edit_dialog.py
│   │   │   ├── rename_conflict_dialog.py
│   │   │   └── ...
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── file_table_view.py
│   │   │   ├── file_tree_view.py
│   │   │   ├── metadata_tree_view.py
│   │   │   ├── rename_modules_area.py
│   │   │   └── ...
│   │   ├── delegates/
│   │   │   ├── __init__.py
│   │   │   └── ui_delegates.py
│   │   └── mixins/
│   │       ├── __init__.py
│   │       └── ...
│   │
│   ├── controllers/             # Controller Layer
│   │   ├── __init__.py
│   │   ├── main_controller.py
│   │   ├── rename_controller.py
│   │   ├── metadata_controller.py
│   │   └── file_controller.py
│   │
│   ├── domain/                  # Domain Layer (Pure Python)
│   │   ├── __init__.py
│   │   ├── rename/
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py      # RenamePipeline
│   │   │   ├── modules/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── counter.py
│   │   │   │   ├── metadata.py
│   │   │   │   ├── text_removal.py
│   │   │   │   └── ...
│   │   │   ├── validators.py
│   │   │   └── conflict_resolver.py
│   │   ├── metadata/
│   │   │   ├── __init__.py
│   │   │   ├── extractor.py
│   │   │   └── field_mapper.py
│   │   └── preview/
│   │       ├── __init__.py
│   │       └── engine.py
│   │
│   ├── services/                # Services Layer
│   │   ├── __init__.py
│   │   ├── filesystem_service.py
│   │   ├── exiftool_service.py
│   │   ├── hash_service.py
│   │   ├── database_service.py
│   │   └── config_service.py
│   │
│   ├── models/                  # Data Models
│   │   ├── __init__.py
│   │   ├── file_item.py
│   │   ├── metadata_entry.py
│   │   ├── rename_plan.py
│   │   └── rename_module_config.py
│   │
│   ├── workers/                 # Background Workers
│   │   ├── __init__.py
│   │   ├── metadata_worker.py
│   │   └── hash_worker.py
│   │
│   └── utils/                   # Shared Utilities
│       ├── __init__.py
│       ├── path_utils.py
│       ├── timer_manager.py
│       └── logger.py
│
├── tests/                       # Tests (stays at root)
│   ├── __init__.py
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── docs/                        # Documentation
├── resources/                   # Assets (icons, fonts, QSS)
├── scripts/                     # Dev scripts
├── .vscode/                     # IDE config
├── pyproject.toml
├── requirements.txt
└── README.md
```

### 5.2 Phase 0 Steps

#### Step 0.1: Create Package Structure

```bash
# Create directories
mkdir -p oncutf/{ui/{dialogs,widgets,delegates,mixins},controllers,domain/{rename/modules,metadata,preview},services,models,workers,utils}

# Create __init__.py files
find oncutf -type d -exec touch {}/__init__.py \;
```

**Commit**: `chore: create oncutf package directory structure`

#### Step 0.2: Move Entry Points

| From | To |
|------|----|
| `main.py` | `oncutf/app.py` (rename to `run_app()`) |
| (new) | `oncutf/__main__.py` (calls `run_app()`) |
| (new) | `main.py` (stub: imports and runs) |

**Commit**: `refactor: move entry point to oncutf package`

#### Step 0.3: Move UI Components

| From | To |
|------|----|
| `main_window.py` | `oncutf/ui/main_window.py` |
| `widgets/*.py` | `oncutf/ui/widgets/` |
| `widgets/mixins/` | `oncutf/ui/mixins/` |

**Commit**: `refactor: move UI components to oncutf/ui`

#### Step 0.4: Move Models

| From | To |
|------|----|
| `models/*.py` | `oncutf/models/` |

**Commit**: `refactor: move models to oncutf/models`

#### Step 0.5: Move Core → Split

| From | To |
|------|----|
| `core/application_context.py` | `oncutf/controllers/app_context.py` |
| `core/application_service.py` | `oncutf/controllers/app_service.py` |
| `core/*_manager.py` | `oncutf/controllers/` (evaluate each) |
| `core/unified_rename_engine.py` | `oncutf/domain/rename/engine.py` |
| `core/conflict_resolver.py` | `oncutf/domain/rename/conflict_resolver.py` |

**Commit**: `refactor: split core into controllers and domain`

#### Step 0.6: Move Modules → Domain

| From | To |
|------|----|
| `modules/base_module.py` | `oncutf/domain/rename/modules/base.py` |
| `modules/counter_module.py` | `oncutf/domain/rename/modules/counter.py` |
| `modules/metadata_module.py` | `oncutf/domain/rename/modules/metadata.py` |
| `modules/*_module.py` | `oncutf/domain/rename/modules/` |

**Commit**: `refactor: move rename modules to domain layer`

#### Step 0.7: Move Utils → Services + Utils

| From | To |
|------|----|
| `utils/exiftool_wrapper.py` | `oncutf/services/exiftool_service.py` |
| `utils/path_utils.py` | `oncutf/utils/path_utils.py` |
| `utils/timer_manager.py` | `oncutf/utils/timer_manager.py` |
| (most utils) | `oncutf/utils/` |

**Commit**: `refactor: reorganize utils and create services`

#### Step 0.8: Fix All Imports

Run automated import fixer:

```python
# scripts/fix_imports.py
import ast
import os
from pathlib import Path

IMPORT_MAP = {
    "main_window": "oncutf.ui.main_window",
    "widgets.": "oncutf.ui.widgets.",
    "models.": "oncutf.models.",
    "core.": "oncutf.controllers.",  # or domain/services
    "modules.": "oncutf.domain.rename.modules.",
    "utils.": "oncutf.utils.",
}
```

**Commit**: `refactor: fix imports for new package structure`

#### Step 0.9: Verify & Clean

```bash
# Verify imports work
python -c "from oncutf.app import run_app"

# Run tests
pytest tests/ -x

# Remove old directories (after verification)
rm -rf widgets/ models/ core/ modules/ utils/
```

**Commit**: `chore: remove old directories after migration`

---

## 6. Phased Refactoring Plan

### Phase 1: State Management Fix (Priority: HIGH)

**Goal**: Single source of truth for file state

#### Step 1.1: Consolidate FileStore

```python
# oncutf/models/file_store.py
@dataclass
class FileGroup:
    """Group of files from same source folder."""
    source_folder: Path
    files: list[FileItem]
    load_order: int  # For counter scope

class FileStore:
    """Single source of truth for loaded files."""
    _groups: list[FileGroup]
    _flat_list: list[FileItem]  # Cached flattened view
    
    def add_folder(self, path: Path, files: list[FileItem]) -> None: ...
    def get_all_files(self) -> list[FileItem]: ...
    def get_files_by_group(self) -> list[FileGroup]: ...
```

**Test**: `test_file_store_groups.py`  
**Commit**: `feat: add FileGroup concept to FileStore`

#### Step 1.2: Fix Counter Scope

```python
# oncutf/domain/rename/modules/counter.py
class CounterScope(Enum):
    GLOBAL = "global"           # Single counter across all files
    PER_FOLDER = "per_folder"   # Reset at folder boundary
    PER_SELECTION = "per_selection"  # Reset for checked files

@dataclass
class CounterConfig:
    start: int = 1
    step: int = 1
    padding: int = 4
    scope: CounterScope = CounterScope.PER_FOLDER
```

**Test**: `test_counter_scope.py`  
**Commit**: `feat: add counter scope support (fixes multi-folder issue)`

#### Step 1.3: Unified State Signals

```python
# oncutf/controllers/state_coordinator.py
class StateCoordinator(QObject):
    """Central coordinator for state changes."""
    
    files_changed = pyqtSignal(list)  # FileItem list
    selection_changed = pyqtSignal(set)  # row indices
    preview_invalidated = pyqtSignal()
    
    def notify_files_changed(self, files: list[FileItem]) -> None:
        self._file_store.set_files(files)
        self.files_changed.emit(files)
        self.preview_invalidated.emit()
```

**Test**: `test_state_coordinator.py`  
**Commit**: `feat: add StateCoordinator for centralized state management`

---

### Phase 2: Metadata Module Fix (Priority: HIGH)

#### Step 2.1: Split MetadataModule

```python
# oncutf/domain/metadata/extractor.py (Pure Python)
class MetadataExtractor:
    """Extract metadata values from FileItem."""
    
    def extract(self, file: FileItem, field: str) -> str | None: ...
    def get_available_fields(self, file: FileItem) -> list[str]: ...

# oncutf/ui/widgets/metadata_module_widget.py (Qt)
class MetadataModuleWidget(QWidget):
    """UI for metadata extraction settings."""
    
    settings_changed = pyqtSignal(dict)  # Emitted on ANY change
```

**Test**: `test_metadata_extractor.py`  
**Commit**: `refactor: split MetadataModule into extractor and widget`

#### Step 2.2: Fix ComboBox Styling

```python
# oncutf/ui/widgets/styled_combo_box.py
class StyledComboBox(QComboBox):
    """ComboBox with proper theme integration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_delegate()
    
    def _setup_delegate(self) -> None:
        from oncutf.ui.delegates import ComboBoxItemDelegate
        theme = ThemeManager.instance()
        self.setItemDelegate(ComboBoxItemDelegate(self, theme))
        self.setFixedHeight(theme.get_constant("combo_height"))
```

**Commit**: `fix: add StyledComboBox with proper delegate`

#### Step 2.3: Instant Preview Updates

```python
# oncutf/ui/widgets/metadata_module_widget.py
def _on_any_setting_change(self) -> None:
    """Emit settings_changed on ANY user interaction."""
    self.settings_changed.emit(self.get_config())

# Connect all inputs:
self.field_combo.currentIndexChanged.connect(self._on_any_setting_change)
self.format_input.textChanged.connect(self._on_any_setting_change)
```

**Commit**: `fix: emit signal on any metadata setting change`

---

### Phase 3: Text Removal Module Fix (Priority: MEDIUM)

#### Step 3.1: Add Match Preview

```python
# oncutf/domain/rename/modules/text_removal.py
@dataclass
class TextRemovalMatch:
    start: int
    end: int
    matched_text: str

class TextRemovalModule:
    def find_matches(self, text: str, pattern: str) -> list[TextRemovalMatch]: ...
    def apply_removal(self, text: str, matches: list[TextRemovalMatch]) -> str: ...
```

**Test**: `test_text_removal_matches.py`  
**Commit**: `feat: add match preview to text removal module`

#### Step 3.2: UI with Highlighting

```python
# oncutf/ui/widgets/text_removal_widget.py
class TextRemovalWidget(QWidget):
    def _update_preview(self) -> None:
        matches = self._module.find_matches(self._sample_text, self._pattern)
        highlighted = self._create_highlighted_html(self._sample_text, matches)
        self.preview_label.setText(highlighted)
    
    def _create_highlighted_html(self, text: str, matches: list) -> str:
        # Red strikethrough for matched portions
        ...
```

**Commit**: `feat: add visual match highlighting to text removal`

---

### Phase 4: Theme Consolidation (Priority: MEDIUM)

#### Step 4.1: Merge Theme Systems

```python
# oncutf/ui/theme/manager.py
class ThemeManager:
    """Single source for all theming."""
    
    _instance: ClassVar["ThemeManager | None"] = None
    
    def __init__(self):
        self._tokens = self._load_tokens()
        self._qss_cache: str | None = None
    
    def get_color(self, token: str) -> str: ...
    def get_constant(self, name: str) -> int: ...
    def get_qss(self) -> str: ...
```

**Commit**: `refactor: consolidate ThemeEngine and ThemeManager`

#### Step 4.2: Component Base Classes

```python
# oncutf/ui/components/base.py
class ThemedWidget(QWidget):
    """Base for all themed widgets."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_theme()
    
    def _apply_theme(self) -> None:
        theme = ThemeManager.instance()
        # Apply common styling
```

**Commit**: `feat: add ThemedWidget base class`

---

### Phase 5: Domain Layer Purification (Priority: MEDIUM)

#### Step 5.1: Remove Qt from Domain

```python
# oncutf/domain/rename/pipeline.py
# NO Qt imports allowed!
from dataclasses import dataclass
from typing import Protocol

class RenameModule(Protocol):
    """Protocol for rename modules."""
    def apply(self, file: FileItem, index: int, context: RenameContext) -> str: ...

@dataclass
class RenamePipeline:
    modules: list[RenameModule]
    post_transform: PostTransformConfig | None
    
    def generate_preview(self, files: list[FileItem]) -> PreviewResult: ...
```

**Commit**: `refactor: make domain layer Qt-free`

#### Step 5.2: Service Interfaces

```python
# oncutf/services/interfaces.py
from typing import Protocol

class MetadataService(Protocol):
    def load_metadata(self, path: Path) -> dict[str, Any]: ...
    def load_metadata_batch(self, paths: list[Path]) -> dict[Path, dict]: ...

class HashService(Protocol):
    def compute_hash(self, path: Path, algorithm: str) -> str: ...
```

**Commit**: `feat: add service protocols for dependency injection`

---

## 7. Naming & API Consistency Audit

### 7.1 Staged Cleanup Strategy

**Stage A: Constants** (Low Risk)
```python
# Before
ALLOWED_EXTS = [...]
file_table_column_config = {...}

# After
ALLOWED_EXTENSIONS = [...]
FILE_TABLE_COLUMN_CONFIG = {...}
```

**Stage B: Private Methods** (Low Risk)
```python
# Before
def update_preview_internal(self): ...
def _do_load(self): ...

# After (consistent prefix)
def _update_preview(self): ...
def _load_files(self): ...
```

**Stage C: Class Names** (Medium Risk)
```python
# Before
class MetadataModule:       # Ambiguous: UI or logic?
class UnifiedRenameEngine:  # Too generic

# After
class MetadataExtractor:    # Clear: domain logic
class MetadataModuleWidget: # Clear: UI widget
class RenameEngine:         # Shorter, clear
```

**Stage D: Signal Names** (Medium Risk)
```python
# Before
updated = pyqtSignal(object)
files_dropped = pyqtSignal(list, object)

# After (consistent pattern)
settings_changed = pyqtSignal(dict)
files_dropped = pyqtSignal(list)  # modifiers in handler
```

### 7.2 Type Annotation Audit

**Priority fixes**:
```python
# Before
def get_metadata(file_item, cache=None):
    
# After
def get_metadata(
    file_item: FileItem,
    cache: MetadataCache | None = None
) -> dict[str, Any]:
```

---

## 8. Node Editor Integration Strategy

### 8.1 Feasibility Assessment

**Pros**:
- Visual pipeline clarity
- Natural drag-and-drop UX
- Easy preset save/load
- Future extensibility

**Cons**:
- Significant UI complexity
- Learning curve for users
- Development time

**Recommendation**: PROCEED with backend-first approach.

### 8.2 Backend-First Design

#### Node Graph Data Model

```python
# oncutf/domain/rename/node_graph.py
from dataclasses import dataclass, field
from uuid import UUID, uuid4

@dataclass
class NodePort:
    """Connection point on a node."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    port_type: str = "string"  # string, file_list, metadata

@dataclass
class Node:
    """Base node in rename pipeline graph."""
    id: UUID = field(default_factory=uuid4)
    type: str = ""  # counter, metadata, text_removal, etc.
    position: tuple[float, float] = (0, 0)
    config: dict = field(default_factory=dict)
    inputs: list[NodePort] = field(default_factory=list)
    outputs: list[NodePort] = field(default_factory=list)

@dataclass
class Connection:
    """Edge between two nodes."""
    id: UUID = field(default_factory=uuid4)
    source_node: UUID
    source_port: UUID
    target_node: UUID
    target_port: UUID

@dataclass
class NodeGraph:
    """Complete rename pipeline as a graph."""
    nodes: list[Node] = field(default_factory=list)
    connections: list[Connection] = field(default_factory=list)
    
    def to_json(self) -> str: ...
    
    @classmethod
    def from_json(cls, data: str) -> "NodeGraph": ...
```

#### Graph → Pipeline Mapping

```python
# oncutf/domain/rename/graph_executor.py
class GraphExecutor:
    """Execute node graph as rename pipeline."""
    
    def __init__(self, graph: NodeGraph):
        self._graph = graph
        self._execution_order = self._topological_sort()
    
    def execute(self, files: list[FileItem]) -> PreviewResult:
        """Run pipeline for preview."""
        context = ExecutionContext(files=files)
        
        for node_id in self._execution_order:
            node = self._get_node(node_id)
            inputs = self._gather_inputs(node, context)
            outputs = self._execute_node(node, inputs)
            context.set_outputs(node_id, outputs)
        
        return self._collect_final_names(context)
```

### 8.3 Migration Path

**Phase A**: Backend only (no UI changes)
- Implement `NodeGraph`, `Node`, `Connection` dataclasses
- Implement `GraphExecutor`
- Convert existing modules to nodes internally
- Full test coverage

**Phase B**: Preset System
- Add save/load for `NodeGraph` JSON
- "Presets" dropdown in existing UI
- No visual graph yet

**Phase C**: Visual Graph UI
- Evaluate libraries: `nodeeditor`, `pyqtgraph`
- Implement `NodeEditorWidget`
- Keep linear UI as fallback

**Phase D**: Full Integration
- Replace linear module list with node editor
- Deprecate old UI

---

## 9. Risk Assessment & Mitigation

### High Risk Items

| Risk | Impact | Mitigation |
|------|--------|------------|
| Import cycle during Phase 0 | App won't start | Use TYPE_CHECKING, fix incrementally |
| State desync after Phase 1 | Wrong previews | Add state validation assertions |
| Theme regression after Phase 4 | Visual bugs | Screenshot comparison tests |

### Medium Risk Items

| Risk | Impact | Mitigation |
|------|--------|------------|
| Test breakage during moves | CI fails | Run tests after each commit |
| Performance regression | Slow preview | Benchmark before/after |
| User confusion (UX change) | Complaints | Document changes, gradual rollout |

### Rollback Strategy

Each phase is designed to be:
1. **Atomic**: Complete or revert
2. **Testable**: Verify before merge
3. **Reversible**: Git revert safe

---

## Appendix A: File Move Manifest

See `docs/FILE_MOVE_MANIFEST.csv` for complete mapping.

## Appendix B: Commit Message Format

```
type(scope): description

[body - optional]

[footer - optional]
```

Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`

Scopes: `ui`, `domain`, `services`, `models`, `controllers`, `build`

---

*Document version: 1.0*  
*Last updated: December 2025*
