# Application Context Migration Plan

## Overview

This document outlines the plan to migrate state management from `MainWindow` to `ApplicationContext`, reducing coupling and improving testability.

**Current State:** ApplicationContext exists in "skeleton mode" with partial implementation.

**Goal:** Complete migration of application state to centralized context, reducing MainWindow from 1269 lines to ~500 lines.

---

## Current Architecture Analysis

### State Distribution (As of 2025-11-21)

```
┌─────────────────────────────────────────┐
│         MainWindow (1269 lines)         │
│  - files: list[FileItem]               │
│  - current_folder_path: str            │
│  - current_folder_is_recursive: bool   │
│  - preview_map: dict                   │
│  - metadata_cache                      │
│  - file_model: FileTableModel          │
│  - UI components (table_view, etc.)    │
│  - 15+ managers                        │
└─────────────────────────────────────────┘
         │
         │ references
         ▼
┌─────────────────────────────────────────┐
│   ApplicationContext (skeleton mode)    │
│  - _files: list (legacy)               │
│  - _current_folder: str (legacy)       │
│  - file_store: FileStore ✓             │
│  - selection_store: SelectionStore ✓   │
└─────────────────────────────────────────┘
```

### Problems with Current Architecture

1. **Tight Coupling:** Components reference `parent_window.files` directly
2. **Testing Difficulty:** Need full MainWindow instance to test managers
3. **State Duplication:** Same state in multiple places (MainWindow vs Context)
4. **No Single Source of Truth:** Unclear which component owns which state

---

## Migration Strategy

### Phase 1: Core State Migration ✓ (Partially Complete)

**Status:** FileStore and SelectionStore created but not fully adopted.

**Remaining Work:**
- Complete integration of FileStore in MainWindow
- Remove duplicate state from MainWindow
- Update all components to use stores via context

### Phase 2: Manager Registration (This Plan)

**Goal:** Move manager references to ApplicationContext

**Current:** MainWindow owns all managers directly
```python
class MainWindow:
    def __init__(self):
        self.metadata_manager = MetadataManager(self)
        self.table_manager = TableManager(self)
        # ... 13 more managers
```

**Target:** ApplicationContext manages and provides managers
```python
class ApplicationContext:
    def register_manager(self, name: str, manager: Any):
        self._managers[name] = manager
    
    def get_manager(self, name: str) -> Any:
        return self._managers.get(name)
```

**Benefits:**
- Managers accessible without MainWindow reference
- Easier to test managers in isolation
- Clear dependency graph

### Phase 3: UI Component Separation

**Goal:** Extract UI setup from MainWindow into specialized managers

**Current:** MainWindow.__init__() has mixed concerns:
- Manager creation
- UI layout
- Signal connections
- Config loading

**Target:** Separate concerns
```
MainWindow (500 lines)
  ├─► UIManager (already exists) - UI layout & widgets
  ├─► MenuManager (NEW) - menu & toolbar setup
  ├─► SignalCoordinator (NEW) - connect all signals
  └─► ApplicationContext - state & managers
```

### Phase 4: Complete Migration

**Goal:** MainWindow becomes thin coordinator

**Target Structure:**
```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. Create context
        self.context = ApplicationContext.create_instance(self)
        
        # 2. Register managers
        self._register_managers()
        
        # 3. Setup UI
        self.ui_manager.setup_all_ui()
        
        # 4. Connect signals
        self._connect_signals()
        
        # 5. Load config
        self._load_configuration()
```

---

## Detailed Migration Steps

### Step 1: Complete FileStore Integration

**Files to Modify:**
- `main_window.py` - Remove `self.files`, use `context.file_store`
- `file_load_manager.py` - Load files into FileStore
- `file_table_model.py` - Get files from FileStore

**Changes:**

#### MainWindow
```python
# BEFORE
self.files = []
self.files = load_files_from_folder(folder_path)

# AFTER
# Remove self.files attribute
self.context.file_store.load_files_from_paths([folder_path])
files = self.context.file_store.get_loaded_files()
```

#### FileTableModel
```python
# BEFORE
def __init__(self, parent_window):
    self.parent_window = parent_window
    self.files = parent_window.files

# AFTER
def __init__(self, context):
    self.context = context
    
@property
def files(self):
    return self.context.file_store.get_loaded_files()
```

**Expected Outcome:**
- Remove `self.files` from MainWindow (-1 attribute, ~50 references)
- Single source of truth for file list

---

### Step 2: Migrate Folder State

**Files to Modify:**
- `main_window.py` - Remove folder-related attributes
- `file_load_manager.py` - Use context for folder operations

**State to Migrate:**
```python
# BEFORE (MainWindow)
self.current_folder_path = None
self.current_folder_is_recursive = False

# AFTER (ApplicationContext)
# Already exists in skeleton:
self._current_folder: str | None = None
# Need to add:
self._recursive_mode: bool = False
```

**New Context Methods:**
```python
class ApplicationContext:
    def get_current_folder(self) -> str | None:
        return self._current_folder
    
    def set_current_folder(self, path: str, recursive: bool = False):
        self._current_folder = path
        self._recursive_mode = recursive
        self.file_store.set_current_folder(path)
        # Emit signal for UI updates
    
    def is_recursive_mode(self) -> bool:
        return self._recursive_mode
```

**Expected Outcome:**
- Remove 2 attributes from MainWindow
- Centralized folder state management

---

### Step 3: Manager Registry System

**New ApplicationContext Methods:**

```python
class ApplicationContext:
    def __init__(self):
        # ... existing init ...
        self._managers: dict[str, Any] = {}
    
    def register_manager(self, name: str, manager: Any) -> None:
        """Register a manager for global access."""
        if name in self._managers:
            logger.warning(f"Manager '{name}' already registered, replacing")
        self._managers[name] = manager
        logger.debug(f"Registered manager: {name}")
    
    def get_manager(self, name: str) -> Any:
        """Get a registered manager."""
        if name not in self._managers:
            raise KeyError(f"Manager '{name}' not registered")
        return self._managers[name]
    
    def has_manager(self, name: str) -> bool:
        """Check if manager is registered."""
        return name in self._managers
```

**MainWindow Integration:**

```python
class MainWindow:
    def _register_managers(self):
        """Register all managers with ApplicationContext."""
        ctx = self.context
        
        # Core managers
        ctx.register_manager('metadata', self.metadata_manager)
        ctx.register_manager('table', self.table_manager)
        ctx.register_manager('preview', self.preview_manager)
        ctx.register_manager('rename', self.rename_manager)
        ctx.register_manager('file_ops', self.file_operations_manager)
        ctx.register_manager('selection', self.selection_manager)
        ctx.register_manager('dialog', self.dialog_manager)
        ctx.register_manager('drag', self.drag_manager)
        
        # Utility managers
        ctx.register_manager('utility', self.utility_manager)
        ctx.register_manager('shortcuts', self.shortcut_manager)
        ctx.register_manager('window_config', self.window_config_manager)
        
        logger.info(f"Registered {len(self.context._managers)} managers")
```

**Usage Example:**

```python
# BEFORE: Deep parent traversal
metadata_mgr = self.parent_window.metadata_manager

# AFTER: Get from context
from core.application_context import get_app_context
metadata_mgr = get_app_context().get_manager('metadata')
```

**Expected Outcome:**
- Managers accessible without MainWindow reference
- ~15 managers registered in context
- Easier dependency injection for testing

---

### Step 4: Migrate Preview State

**State to Migrate:**
```python
# BEFORE (MainWindow)
self.preview_map = {}  # preview_filename -> FileItem

# AFTER (ApplicationContext or PreviewManager)
# Option A: In ApplicationContext
self._preview_cache: dict[str, FileItem] = {}

# Option B: In PreviewManager (Better)
# PreviewManager already handles preview generation
# Just needs to expose cache access methods
```

**Recommended:** Keep preview_map in PreviewManager, expose via context

```python
class ApplicationContext:
    @property
    def preview_manager(self):
        return self.get_manager('preview')
    
    def get_preview_for_file(self, file_item: FileItem) -> str:
        return self.preview_manager.get_preview(file_item)
```

**Expected Outcome:**
- Remove `self.preview_map` from MainWindow
- Preview state owned by PreviewManager

---

### Step 5: Extract Menu & Toolbar Setup

**Create:** `core/menu_manager.py`

**Purpose:** Move menu and toolbar creation out of MainWindow/UIManager

```python
class MenuManager:
    """Manages application menus and toolbars."""
    
    def __init__(self, main_window: QMainWindow, context: ApplicationContext):
        self.main_window = main_window
        self.context = context
    
    def setup_menus(self) -> None:
        """Create all application menus."""
        self._create_file_menu()
        self._create_edit_menu()
        self._create_view_menu()
        self._create_tools_menu()
        self._create_help_menu()
    
    def setup_toolbars(self) -> None:
        """Create application toolbars."""
        self._create_main_toolbar()
        self._create_preview_toolbar()
    
    def _create_file_menu(self) -> None:
        file_menu = self.main_window.menuBar().addMenu("&File")
        # ... menu actions ...
```

**Expected Outcome:**
- Extract ~200 lines from UIManager
- Cleaner separation of concerns

---

### Step 6: Extract Signal Coordination

**Create:** `core/signal_coordinator.py`

**Purpose:** Centralize all signal connections

```python
class SignalCoordinator:
    """Coordinates signal connections across the application."""
    
    def __init__(self, main_window: MainWindow, context: ApplicationContext):
        self.main_window = main_window
        self.context = context
    
    def connect_all_signals(self) -> None:
        """Connect all application signals."""
        self._connect_file_signals()
        self._connect_selection_signals()
        self._connect_metadata_signals()
        self._connect_preview_signals()
        self._connect_ui_signals()
    
    def _connect_file_signals(self) -> None:
        file_store = self.context.file_store
        file_store.files_loaded.connect(self.main_window.on_files_loaded)
        file_store.folder_changed.connect(self.main_window.on_folder_changed)
        # ... more connections ...
```

**Expected Outcome:**
- Clear overview of all signal connections
- Easier to debug signal-related issues
- ~100 lines extracted from MainWindow.__init__

---

## Migration Milestones

### Milestone 1: Core State Complete ✅ (Target: Week 1)

- [x] FileStore created and integrated
- [x] SelectionStore created and integrated
- [ ] Remove `self.files` from MainWindow
- [ ] Remove `self.current_folder_path` from MainWindow
- [ ] All file operations use FileStore

**Success Criteria:**
- No direct file list access in MainWindow
- All components use stores via context

### Milestone 2: Manager Registry Complete (Target: Week 2)

- [ ] Manager registration system in ApplicationContext
- [ ] All managers registered on startup
- [ ] At least 5 components refactored to use context.get_manager()
- [ ] Unit tests for manager registry

**Success Criteria:**
- Managers accessible without MainWindow
- Can test managers with mock context

### Milestone 3: UI Separation Complete (Target: Week 3)

- [ ] MenuManager created and integrated
- [ ] SignalCoordinator created and integrated
- [ ] MainWindow.__init__() reduced to <200 lines
- [ ] UIManager focused only on layout

**Success Criteria:**
- Clear separation of UI setup concerns
- MainWindow is thin coordinator

### Milestone 4: Full Migration Complete (Target: Week 4)

- [ ] MainWindow reduced to ~500 lines
- [ ] All state managed by ApplicationContext
- [ ] Documentation updated
- [ ] Integration tests passing

**Success Criteria:**
- MainWindow size reduced by 60%
- State ownership clearly defined
- Test coverage >80% for context

---

## Risk Assessment

### High Risk Areas

1. **Signal Connection Breakage**
   - Risk: Moving code may disconnect signals
   - Mitigation: Add signal connection tests, verify functionality after each change

2. **Circular Dependencies**
   - Risk: Context → Manager → Context loops
   - Mitigation: Use forward references, lazy initialization

3. **Performance Regression**
   - Risk: Extra indirection through context may slow down operations
   - Mitigation: Benchmark critical paths, optimize if needed

### Low Risk Areas

1. **Manager Registration** - Simple dict-based lookup
2. **State Migration** - Already have stores in place
3. **UI Extraction** - Isolated changes

---

## Testing Strategy

### Unit Tests

**New Test Files:**
- `tests/test_application_context_migration.py`
- `tests/test_manager_registry.py`
- `tests/test_menu_manager.py`
- `tests/test_signal_coordinator.py`

**Test Coverage Goals:**
- ApplicationContext: 90%
- Manager registry: 95%
- New managers: 80%

### Integration Tests

**Scenarios to Test:**
1. Load files → verify FileStore state
2. Select files → verify SelectionStore state
3. Get manager → verify registry works
4. UI actions → verify signals connected

### Manual Testing Checklist

After each milestone:
- [ ] Load folder with files
- [ ] Select and deselect files
- [ ] Generate preview
- [ ] Execute rename
- [ ] Load metadata
- [ ] Use all menu items
- [ ] Check keyboard shortcuts

---

## Rollback Plan

If migration causes major issues:

1. **Keep Old Code:** Comment out, don't delete during migration
2. **Feature Flags:** Use config to toggle new/old paths
3. **Git Branches:** Separate branch per milestone for easy revert

**Example:**
```python
# config.py
USE_NEW_CONTEXT_SYSTEM = True  # Toggle for A/B testing

# main_window.py
if USE_NEW_CONTEXT_SYSTEM:
    files = self.context.file_store.get_loaded_files()
else:
    files = self.files  # Legacy path
```

---

## Success Metrics

### Quantitative

- MainWindow lines: 1269 → ~500 (-60%)
- Number of MainWindow attributes: 30+ → ~10 (-66%)
- Test coverage: 60% → 80% (+20%)
- Circular dependencies: Reduced to 0

### Qualitative

- Clearer state ownership
- Easier to add new features
- Simpler testing setup
- Better documentation

---

## Next Steps

1. **Immediate:** Complete Step 1 (FileStore integration)
2. **This Week:** Implement Step 2 (Folder state) + Step 3 (Manager registry)
3. **Next Week:** Create Step 5 (MenuManager) + Step 6 (SignalCoordinator)
4. **Final Week:** Polish, test, document

**Start with:** Removing `self.files` from MainWindow (highest impact, lowest risk)

---

## Related Documents

- [Application Workflow](./application_workflow.md) - High-level architecture
- [Concurrency Decision](./concurrency_decision.md) - Threading model
- [Threading Patterns](./threading_patterns.md) - Threading implementation guide
- [Architecture Plan](./oncutf_architecture_plan.md) - Overall improvement plan

---

## Appendix: Code Size Analysis

### Current MainWindow Breakdown

```
Total lines: 1269

Breakdown:
- Initialization (__init__): 200 lines
- UI setup delegation: 50 lines
- File operations: 150 lines
- Metadata operations: 100 lines
- Preview operations: 120 lines
- Rename operations: 100 lines
- Selection handling: 80 lines
- Event handlers: 150 lines
- Utility methods: 100 lines
- Shutdown/cleanup: 80 lines
- Miscellaneous: 139 lines
```

### Target MainWindow (Post-Migration)

```
Target lines: ~500

Breakdown:
- Initialization (streamlined): 50 lines
- Manager registration: 30 lines
- Signal coordination: 50 lines
- Thin wrapper methods: 200 lines
- Event handlers (UI-specific): 100 lines
- Shutdown/cleanup: 50 lines
- Miscellaneous: 20 lines
```

**Extracted to:**
- MenuManager: 200 lines
- SignalCoordinator: 100 lines
- ApplicationContext: 200 lines (additions)
- Managers (various): 200+ lines

---

## Conclusion

This migration will significantly improve OnCutF's architecture by:
- **Reducing coupling** between components
- **Improving testability** through dependency injection
- **Clarifying ownership** of application state
- **Simplifying MainWindow** to a thin coordinator

The phased approach ensures stability while making steady progress toward the goal.
