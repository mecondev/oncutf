# Module Orchestration Refactoring

**Author:** Michael Economou  
**Date:** 2025-12-27  
**Status:** Phase 1 Complete

## Motivation

Prepare architecture for **node editor** implementation by separating:
- **Business logic** (module orchestration, data flow)
- **UI concerns** (widgets, drag-drop visuals)

## Current Problems

1. `RenameModuleWidget` mixes UI + logic + drag-drop (473 lines, multiple responsibilities)
2. Module registry hardcoded in UI widget
3. Drag-drop state management coupled with widget lifecycle
4. Height calculations in UI layer
5. Difficult to replace UI without touching business logic

## New Architecture

```
┌─────────────────────────────────────────────┐
│  UI Layer                                   │
│  • RenameModuleWidget (pure container)     │
│  • Future: Node Editor                     │
└──────────────┬──────────────────────────────┘
               │ uses
┌──────────────▼──────────────────────────────┐
│  Controllers                                │
│  • ModuleOrchestrator                      │
│    - Module registry                       │
│    - Pipeline management (add/remove)      │
│    - Data collection                       │
│    - Validation                            │
│  • ModuleDragDropManager                   │
│    - Drag state tracking                   │
│    - Cursor management                     │
└──────────────┬──────────────────────────────┘
               │ delegates to
┌──────────────▼──────────────────────────────┐
│  Pure Modules (oncutf/modules/*.py)        │
│  • CounterModule.apply_from_data()         │
│  • MetadataModule.apply_from_data()        │
│  • No PyQt dependencies                    │
└─────────────────────────────────────────────┘
```

## Phase 1: Controller Extraction (COMPLETE)

### Created Files

**1. `oncutf/controllers/module_orchestrator.py`** (300+ lines)
- **ModuleDescriptor**: Metadata about each module type
  - `name`: Internal ID (e.g., "counter")
  - `display_name`: UI label (e.g., "Counter")
  - `module_class`: Pure logic class
  - `ui_widget_class`: Optional UI widget
  - `ui_rows`: Height hint for rendering
  
- **ModuleOrchestrator**: Pipeline management
  - `register_module()`: Add module types to registry
  - `add_module()`: Add instance to pipeline
  - `remove_module()`: Remove by index
  - `reorder_module()`: Change position
  - `collect_all_data()`: Get config for rename engine
  - `validate_module()`: Check if effective

**2. `oncutf/controllers/module_drag_drop_manager.py`** (120+ lines)
- **ModuleDragDropManager**: Drag state management
  - `start_drag()`: Track drag initiation
  - `update_drag()`: Check threshold crossing
  - `end_drag()`: Complete operation
  - `cancel_drag()`: Abort
  - Static cursor helpers

### Benefits

✅ **Testable**: Controllers have no PyQt dependencies  
✅ **Reusable**: Same orchestrator works with node editor  
✅ **Maintainable**: Single responsibility per class  
✅ **Extensible**: Easy to add new module types  

## Phase 2: UI Integration (NEXT)

### Tasks

1. **Refactor `RenameModuleWidget`**
   - Remove hardcoded module registry → Use `ModuleOrchestrator`
   - Remove drag state → Use `ModuleDragDropManager`
   - Reduce to ~200 lines (pure UI container)

2. **Refactor `RenameModulesArea`**
   - Use orchestrator for `get_all_data()`
   - Delegate reordering to orchestrator
   - Remove duplicate logic

3. **Update tests**
   - Test orchestrator independently
   - Test drag manager independently
   - UI tests become simpler

### Migration Strategy

- **Backward compatible**: Keep existing APIs
- **Incremental**: One responsibility at a time
- **Test coverage**: Maintain 592+ tests passing

## Phase 3: Node Editor (FUTURE)

### Preparation Complete

With orchestrator extracted:
1. Implement node-based UI (separate package)
2. Connect to same `ModuleOrchestrator`
3. Reuse all module logic (`oncutf/modules/*.py`)
4. Zero changes to rename engine

### Node Editor Requirements

- Visual node graph (e.g., Qt Node Editor library)
- Nodes = Module instances
- Connections = Data flow
- Same data collection interface (`collect_all_data()`)

## File Organization

```
oncutf/
├── controllers/
│   ├── module_orchestrator.py         # NEW: Pipeline management
│   ├── module_drag_drop_manager.py    # NEW: Drag state
│   ├── file_load_controller.py        # Existing
│   ├── metadata_controller.py         # Existing
│   └── rename_controller.py           # Existing
├── modules/                            # Pure logic (unchanged)
│   ├── counter_module.py
│   ├── metadata_module.py
│   └── ...
└── ui/widgets/
    ├── rename_module_widget.py        # TO REFACTOR: Pure UI
    └── rename_modules_area.py         # TO REFACTOR: Use orchestrator
```

## Design Decisions

### Why ModuleDescriptor?

- **Metadata separation**: UI hints (rows, display name) separate from logic
- **Flexibility**: Can add metadata without changing module classes
- **Future-proof**: Node editor can use same descriptors

### Why separate DragDropManager?

- **Reusability**: Node editor needs different drag behavior
- **Testability**: Can test drag logic without widgets
- **Simplicity**: Single purpose class

### Why not full Model-View architecture yet?

- **Incremental**: Phase 1 focuses on extraction
- **Compatibility**: Maintain current behavior
- **Pragmatic**: Node editor will drive full MV implementation

## Testing Strategy

### Unit Tests (orchestrator)
```python
def test_add_module():
    orch = ModuleOrchestrator()
    idx = orch.add_module("counter", {"start": 1})
    assert orch.get_module_count() == 1
    
def test_reorder():
    orch = ModuleOrchestrator()
    orch.add_module("counter")
    orch.add_module("metadata")
    orch.reorder_module(0, 1)
    assert orch.get_module_at(1)["type"] == "counter"
```

### Integration Tests
- Existing tests continue to pass
- Add controller-level tests
- UI tests simplified

## Backward Compatibility

- `RenameModuleWidget.get_data()` → Delegate to orchestrator
- `RenameModulesArea.get_all_data()` → Delegate to orchestrator
- All signals preserved
- No API changes for main window

## Performance

- **No overhead**: Direct method calls, no extra layers
- **Memory**: Minimal (descriptors are singletons)
- **Speed**: Same as before (just better organized)

## Next Steps

1. ✅ Create `ModuleOrchestrator` (DONE)
2. ✅ Create `ModuleDragDropManager` (DONE)
3. ⏳ Integrate into `RenameModuleWidget`
4. ⏳ Integrate into `RenameModulesArea`
5. ⏳ Add tests
6. ⏳ Update documentation

## References

- **Architecture doc**: `docs/ARCHITECTURE.md`
- **Rename workflow**: `docs/safe_rename_workflow.md`
- **Controllers**: `oncutf/controllers/`
