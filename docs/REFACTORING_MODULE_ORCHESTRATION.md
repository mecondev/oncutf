# Module Orchestration Refactoring

**Author:** Michael Economou  
**Date:** 2025-12-27  
**Status:** Phase 2 Complete ✅ (911 tests passing)

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

## Phase 2: UI Integration ✅ COMPLETE

**Status:** All 911 tests passing  
**Commits:** 
- `f5a8c2e0` - Phase 2.1: RenameModulesArea integration
- `35c7be3d` - Phase 2.2: RenameModuleWidget integration
- `9c77e868` - Documentation (PHASE2_SUMMARY.md)

### Completed Tasks

1. ✅ **RenameModulesArea Integration (Phase 2.1)**
   - Added `self.orchestrator = ModuleOrchestrator()` in `__init__`
   - Refactored `get_all_data()` to delegate to `orchestrator.collect_all_data()`
   - Added `_sync_orchestrator_from_widgets()` bridge for gradual migration
   - Updated `get_module_count()` and `get_modules()` to use orchestrator
   - **Backward compatible:** Same return types, same API

2. ✅ **RenameModuleWidget Integration (Phase 2.2)**
   - Removed local drag state (`drag_start_position`, `is_dragging`)
   - Added `_drag_manager = ModuleDragDropManager()` as class variable
   - Updated all drag handlers to use manager:
     - `drag_handle_mouse_press` → `manager.start_drag()`
     - `drag_handle_mouse_move` → `manager.update_drag()`
     - `drag_handle_mouse_release` → `manager.end_drag()`
   - Simplified `start_drag()`/`end_drag()` to visual feedback only
   - **Backward compatible:** Same drag behavior, same threshold (5px)

3. ✅ **Documentation**
   - Created `docs/PHASE2_SUMMARY.md` with detailed changes
   - Documented architecture improvements
   - Recorded metrics: ~70 lines refactored, 2 hours effort

### Architecture Impact

**Before Phase 2:**
- 473-line `RenameModulesArea` mixing UI + data collection
- 479-line `RenameModuleWidget` mixing UI + drag state

**After Phase 2:**
- Clean delegation to `ModuleOrchestrator` for data collection
- Shared `ModuleDragDropManager` for drag state
- UI widgets focus on presentation only

### Migration Strategy

- ✅ **Backward compatible**: All existing APIs unchanged
- ✅ **Incremental**: Phase 2.1 → 2.2 with separate commits
- ✅ **Test coverage**: 911 tests passing throughout

## Phase 3: Dynamic Module Discovery (NEXT)

**Goal:** Remove hardcoded module registry, enable plugin architecture

### Current State

Module types hardcoded in `RenameModulesArea.__init__`:
```python
self.module_instances = {
    "Specified Text": SpecifiedTextModule(),
    "Counter": CounterModule(),
    "Metadata": MetadataModule(),
    # ... 8 more modules
}
```

**Problems:**
- Adding modules requires editing UI code
- No separation between module discovery and UI
- Cannot dynamically load modules from plugins

### Proposed Changes

1. **Move module registration to ModuleOrchestrator:**
   ```python
   # oncutf/controllers/module_orchestrator.py
   @classmethod
   def discover_modules(cls):
       """Auto-discover modules in oncutf/modules/."""
       # Scan for *_module.py files
       # Import and register each module class
   ```

2. **Update RenameModulesArea to use orchestrator:**
   ```python
   def __init__(self):
       self.orchestrator = ModuleOrchestrator()
       self.orchestrator.discover_modules()  # Auto-register all
       self._populate_module_menu()  # Build from orchestrator
   ```

3. **Benefits:**
   - Drop new module file → automatically appears in UI
   - Plugin architecture ready
   - Cleaner UI layer (no module knowledge)

### Tasks

- [ ] Implement `ModuleOrchestrator.discover_modules()`
- [ ] Remove `module_instances` dict from `RenameModulesArea`
- [ ] Update `_populate_module_menu()` to use orchestrator
- [ ] Add tests for module discovery
- [ ] Document plugin API

### Estimated Effort

- 2-3 hours implementation
- Low risk (orchestrator already exists)
- All tests must pass

---

## Phase 4: Node Editor (FUTURE)

### Preparation Complete

With orchestrator extracted and UI integrated:
1. Implement node-based UI (separate package)
2. Connect to same `ModuleOrchestrator`
3. Reuse all module logic (`oncutf/modules/*.py`)
4. Zero changes to rename engine

### Node Editor Requirements

- Visual node graph (e.g., Qt Node Editor library)
- Nodes = Module instances
- Connections = Data flow
- Same data collection interface (`collect_all_data()`)

---

## File Organization

```
oncutf/
├── controllers/
│   ├── module_orchestrator.py         # ✅ NEW: Pipeline management
│   ├── module_drag_drop_manager.py    # ✅ NEW: Drag state
│   ├── file_load_controller.py        # Existing
│   ├── metadata_controller.py         # Existing
│   └── rename_controller.py           # Existing
├── modules/                            # Pure logic (unchanged)
│   ├── counter_module.py
│   ├── metadata_module.py
│   └── ...
└── ui/widgets/
    ├── rename_module_widget.py        # ✅ REFACTORED: Using ModuleDragDropManager
    └── rename_modules_area.py         # ✅ REFACTORED: Using ModuleOrchestrator
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
