# Refactoring Roadmap

> Generated: 2026-01-01  
> Status: Active planning document

This document tracks technical debt and planned refactoring for the oncutf codebase.

---

## 📊 Current Mega-Files (>700 lines)

| File | Lines | Priority | Split Strategy |
|------|-------|----------|----------------|
| `metadata_tree/view.py` | 1670 | HIGH | Extract handlers → view_handlers.py |
| `database_manager.py` | 1614 | HIGH | Split by table: hash_store, metadata_store, backup_store |
| `main_window.py` | 1362 | MEDIUM | Already using controllers - continue delegation |
| `context_menu_handlers.py` | 1288 | HIGH | Split by domain: metadata_menu, rename_menu, file_menu |
| `unified_rename_engine.py` | 1258 | MEDIUM | Extract validators, conflict resolution |
| `metadata_edit_behavior.py` | 1119 | LOW | Stable, well-tested |
| `file_table_model.py` | 1081 | LOW | Stable, core functionality |

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

### Phase 1: Context Menu Handlers (EASY, HIGH VALUE)

Current: `oncutf/core/events/context_menu_handlers.py` (1288 lines)

Split into:
```
oncutf/core/events/context_menu/
├── __init__.py          # Re-exports ContextMenuHandlers
├── base.py              # ContextMenuHandlers class (delegator)
├── metadata_menu.py     # Metadata-related actions
├── rename_menu.py       # Rename-related actions
├── hash_menu.py         # Hash/duplicate actions
└── file_menu.py         # File operations
```

### Phase 2: Database Manager

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

### Phase 3: Metadata Tree View

Current: `oncutf/ui/widgets/metadata_tree/view.py` (1670 lines)

Split into:
```
oncutf/ui/widgets/metadata_tree/
├── view.py              # Main MetadataTreeView (~600 lines)
├── view_handlers.py     # Event handlers
├── view_delegates.py    # Custom delegates
└── view_helpers.py      # Utility functions
```

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

---

## 📚 Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System overview
- [subsystems/rename_engine.md](subsystems/rename_engine.md) - Rename system details
- [subsystems/metadata_engine.md](subsystems/metadata_engine.md) - Metadata system details
- [TODO.md](../TODO.md) - Feature backlog
