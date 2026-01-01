# Refactoring Roadmap

> Generated: 2026-01-01  
> Status: Active planning document

This document tracks technical debt and planned refactoring for the oncutf codebase.

---

## 📊 Current Mega-Files (>700 lines)

| File | Lines | Priority | Status |
|------|-------|----------|--------|
| ~~`metadata_tree/view.py`~~ | ~~1670~~ | ~~HIGH~~ | ✅ **DONE** |
| ~~`database_manager.py`~~ | ~~1614~~ | ~~HIGH~~ | ✅ **DONE** |
| `main_window.py` | 1362 | MEDIUM | ⏳ Delegating |
| ~~`context_menu_handlers.py`~~ | ~~1288~~ | ~~HIGH~~ | ✅ **DONE** |
| `unified_rename_engine.py` | 1258 | MEDIUM | ⏳ Planned |
| `metadata_edit_behavior.py` | 1119 | LOW | ⏳ Stable |
| `file_table_model.py` | 1081 | LOW | ⏳ Stable |

---

## 🎯 Canonical Patterns (Single Source of Truth)

### 1. Rename Pipeline

**Canonical**: `UnifiedRenameEngine` (`oncutf/core/rename/unified_rename_engine.py`)

```
User Action → RenameController → UnifiedRenameEngine → Preview/Execute
```

**Supporting (NOT entry points)**:
- `utils/naming/preview_engine.py` - Low-level preview helpers (used BY engine)
- `utils/naming/rename_logic.py` - Pure filename logic (used BY engine)
- `utils/naming/renamer.py` - Legacy, to be deprecated

**Rule**: All rename operations MUST go through `UnifiedRenameEngine`.

### 2. Column Management

**Canonical**: `UnifiedColumnService` (`oncutf/ui_managers/column_service.py`)

**Legacy**: `ColumnManager` - Thin adapter, delegates to UnifiedColumnService

**Rule**: New code uses `UnifiedColumnService`. Do not add logic to `ColumnManager`.

### 3. UI Component Patterns

**Canonical**: Behaviors (`oncutf/ui/behaviors/`)

```python
# NEW CODE pattern
class MyWidget(QWidget):
    def __init__(self):
        self.scroll_behavior = ScrollBehavior(self)
        self.edit_behavior = EditBehavior(self)
```

**Legacy**: Mixins (`oncutf/ui/mixins/`) - Do NOT create new mixins.

**Rule**: "New code uses behaviors. Mixins only in legacy widgets."

---

## 🔧 Planned Splits

### ✅ Phase 1: Context Menu Handlers (COMPLETED)

**Original**: `oncutf/core/events/context_menu_handlers.py` (1289 lines)

**Split into**:
```
oncutf/core/events/context_menu/
├── __init__.py              # Re-exports ContextMenuHandlers (11 lines)
├── base.py                  # Main menu builder (639 lines)
├── metadata_handlers.py     # Metadata analysis (172 lines)
├── hash_handlers.py         # Hash analysis (137 lines)
├── rotation_handlers.py     # Rotation operations (360 lines)
└── file_status.py           # File status utilities (153 lines)
```

**Benefits:**
- Each file focused on single domain
- Easier to test individual components
- Clear separation of concerns
- Backward compatible (old imports still work)

---

### ✅ Phase 2: Database Manager (COMPLETED)

**Original**: `oncutf/core/database/database_manager.py` (1614 lines)

**Split into**:
```
oncutf/core/database/
├── __init__.py              # Module exports
├── database_manager.py      # Main orchestrator (407 lines - 75% reduction!)
├── migrations.py            # Schema creation & migrations (520 lines)
├── metadata_store.py        # Metadata operations (627 lines)
├── path_store.py            # Path management (161 lines)
├── hash_store.py            # Hash operations (161 lines)
└── backup_store.py          # Rename history scaffold (40 lines)
```

**Benefits:**
- Single responsibility per store
- Orchestrator reduced by 75% (1614 → 407 lines)
- Clear table ownership (path_store owns file_paths table, etc.)
- Composition pattern (stores as dependencies)
- All 949 tests passing

---

### Phase 3: Metadata Tree View

Current: `oncutf/core/database/database_manager.py` (1614 lines)

Split into:
```
oncutf/core/database/
├── __init__.py
├── database_manager.py  # Main orchestrator (~400 lines)
├── hash_store.py        # Hash-related tables
├── metadata_store.py    # Metadata caching tables
├── backup_store.py      # Backup/restore tables
└── migrations.py        # Schema migrations
```

### ✅ Phase 3: Metadata Tree View (COMPLETED)

**Original**: `oncutf/ui/widgets/metadata_tree/view.py` (1670 lines)

**Split into**:
```
oncutf/ui/widgets/metadata_tree/
├── view.py                # Main orchestrator (~1036 lines, 38% reduction)
├── display_handler.py     # Display logic (502 lines)
├── event_handler.py       # Qt event handlers (132 lines)
└── [existing handlers]
    ├── cache_handler.py
    ├── drag_handler.py
    ├── modifications_handler.py
    ├── search_handler.py
    └── selection_handler.py
```

**Benefits:**
- Extracted 634 lines into specialized handlers
- `_rebuild_tree_from_metadata` (266 lines) moved to display_handler
- Consistent handler pattern across metadata tree
- All 949 tests passing

---

## 🚀 Node Editor Readiness

### Current Seams (already in place)
- `controllers/module_orchestrator.py` - Manages module chain
- `services/interfaces.py` - Service protocols
- `services/registry.py` - Dependency injection

### Next Steps for Node Editor
1. Create `RenameGraph` (pure Python, no Qt)
   - Nodes: ModuleNode, FilterNode, ConditionalNode
   - Edges: Data flow connections
   
2. Create `GraphExecutor`
   - Converts graph → module chain
   - Feeds into existing `UnifiedRenameEngine`

3. Create `NodeEditorWidget`
   - Visual graph editor
   - Uses `RenameGraph` as model

---

## 📋 Quick Wins Completed

- [x] Add docstring to `models/__init__.py`
- [x] Add docstring to `modules/__init__.py`
- [x] Document canonical patterns (this file)
- [x] **Phase 1: Split context_menu_handlers.py** (1289 → 6 files, all tests passing)
- [x] **Phase 2: Split database_manager.py** (1614 → 6 files, all tests passing)
- [x] **Phase 3: Split metadata_tree/view.py** (1670 → view.py + 2 handlers, all tests passing)
- [x] **Phase 2: Split database_manager.py** (1614 → 6 files, all tests passing)

---

## 📚 Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System overview
- [subsystems/rename_engine.md](subsystems/rename_engine.md) - Rename system details
- [subsystems/metadata_engine.md](subsystems/metadata_engine.md) - Metadata system details
- [TODO.md](../TODO.md) - Feature backlog
