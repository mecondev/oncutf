# Node Editor Integration Plan

**Author:** Michael Economou  
**Date:** 2026-01-03  
**Status:** Phase 1 - Initial Setup

---

## Overview

Integrate the portable PyQt Node Editor framework into oncutf to provide a visual, 
node-based interface for building rename pipelines as an alternative to the linear 
module list.

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │           MainWindow                     │
                    │  ┌─────────────────────────────────────┐ │
                    │  │   QStackedWidget (View Switcher)    │ │
                    │  │  ┌────────────┐ ┌────────────────┐  │ │
                    │  │  │ Linear View│ │  Node Editor   │  │ │
                    │  │  │ (existing) │ │  View (NEW)    │  │ │
                    │  │  └────────────┘ └────────────────┘  │ │
                    │  └─────────────────────────────────────┘ │
                    └─────────────────────────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │        RenameGraphController          │
                    │     (Bridge between views & engine)   │
                    └───────────────────┬───────────────────┘
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            │                           │                           │
            ▼                           ▼                           ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│   node_editor/        │   │   rename_graph/       │   │   UnifiedRename       │
│   (UI Layer)          │   │   (Domain Layer)      │   │   Engine              │
│   - Graphics          │   │   - Graph Model       │   │   (Execution)         │
│   - Widgets           │   │   - Validators        │   │                       │
│   - Themes            │   │   - Executor          │   │                       │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
```

---

## File Structure

```
oncutf/
├── core/
│   └── rename_graph/                    <- NEW: Domain layer (Qt-free)
│       ├── __init__.py
│       ├── graph_model.py               <- Rename pipeline graph
│       ├── graph_validator.py           <- Connection rules
│       └── graph_executor.py            <- Execute graph -> filenames
│
├── controllers/
│   └── rename_graph_controller.py       <- NEW: Bridge controller
│
└── ui/
    └── widgets/
        └── node_editor/                 <- NEW: Portable package (copy)
            ├── __init__.py
            ├── core/                    <- Node, Edge, Socket, Scene
            ├── graphics/                <- QGraphicsItem subclasses
            ├── widgets/                 <- NodeEditorWidget, Window
            ├── nodes/
            │   ├── registry.py
            │   ├── math_nodes.py        <- Built-in (keep for reference)
            │   └── rename_nodes/        <- NEW: oncutf-specific nodes
            │       ├── __init__.py
            │       ├── original_name_node.py
            │       ├── counter_node.py
            │       ├── text_removal_node.py
            │       ├── metadata_node.py
            │       ├── text_input_node.py
            │       └── transform_node.py
            ├── themes/
            ├── tools/
            └── utils/
```

---

## Phases

### Phase 1: Initial Setup [COMPLETE]
- [x] Write integration plan
- [x] Copy node_editor package to `oncutf/ui/widgets/node_editor/`
- [x] Update imports from `node_editor.*` to `oncutf.ui.widgets.node_editor.*`
- [x] Create `oncutf/core/rename_graph/` with graph_model, validator, executor
- [x] Create `oncutf/controllers/rename_graph_controller.py`
- [x] Create `oncutf/ui/widgets/node_editor/nodes/rename_nodes/` placeholder
- [x] Add node_editor to mypy ignore (external code)
- [x] Verify all imports work
- [x] Run tests (974 passed)
- [x] Run mypy (clean)

### Phase 2: Create Rename Nodes (op_codes 200+) [NEXT]
- [ ] Create `rename_nodes/` package in node_editor
- [ ] Implement `OriginalNameNode` (op_code 200) - outputs original filename
- [ ] Implement `CounterNode` (op_code 201) - outputs sequential number
- [ ] Implement `TextRemovalNode` (op_code 202) - removes text patterns
- [ ] Implement `MetadataNode` (op_code 203) - outputs EXIF data
- [ ] Implement `TextInputNode` (op_code 204) - user-specified text
- [ ] Implement `TransformNode` (op_code 205) - case/trim operations
- [ ] Implement `ConcatNode` (op_code 206) - joins multiple inputs
- [ ] Implement `OutputNode` (op_code 207) - final filename output
- [ ] Add unit tests for each node

### Phase 3: Graph Model (Domain Layer)
- [ ] Implement `RenameGraph` extending Scene for rename-specific logic
- [ ] Implement `RenameGraphValidator` for connection rules:
  - Only OutputNode can be terminal
  - ConcatNode required for multiple inputs
  - Type checking (string nodes to string inputs)
- [ ] Implement `RenameGraphExecutor`:
  - Traverse graph in topological order
  - Execute each node with FileItem context
  - Collect final filename from OutputNode

### Phase 4: Controller & Integration
- [ ] Create `RenameGraphController`:
  - Load/save graph configurations
  - Convert graph to module pipeline (backward compatibility)
  - Execute graph for preview generation
- [ ] Update `ModuleOrchestrator` to support graph mode
- [ ] Add graph execution to `UnifiedRenameEngine`

### Phase 5: UI Integration
- [ ] Add NodeEditorWidget to MainWindow
- [ ] Create view switcher (Linear vs Node Editor)
- [ ] Add toolbar for node editor (add nodes, save/load graph)
- [ ] Implement drag & drop from node palette
- [ ] Connect to preview system (real-time updates)
- [ ] Theme synchronization with oncutf theme

### Phase 6: Advanced Features
- [ ] Save/load graph configurations (.json)
- [ ] Graph templates (common rename patterns)
- [ ] Node groups (collapse multiple nodes)
- [ ] Undo/redo integration with oncutf history
- [ ] Keyboard shortcuts

---

## Module to Node Mapping

| oncutf Module | Node Name | Op Code | Inputs | Outputs |
|---------------|-----------|---------|--------|---------|
| `OriginalNameModule` | `OriginalNameNode` | 200 | 0 | 1 (string) |
| `CounterModule` | `CounterNode` | 201 | 0 | 1 (string) |
| `TextRemovalModule` | `TextRemovalNode` | 202 | 1 (string) | 1 (string) |
| `MetadataModule` | `MetadataNode` | 203 | 0 | 1 (string) |
| `SpecifiedTextModule` | `TextInputNode` | 204 | 0 | 1 (string) |
| `NameTransformModule` | `TransformNode` | 205 | 1 (string) | 1 (string) |
| (new) | `ConcatNode` | 206 | N (strings) | 1 (string) |
| (new) | `OutputNode` | 207 | 1 (string) | 0 |

---

## Node Types Detail

### OriginalNameNode (200)
- **Purpose**: Provides original filename (without extension)
- **Inputs**: None
- **Outputs**: 1 (string - original name)
- **Content Widget**: Checkbox for include_extension

### CounterNode (201)
- **Purpose**: Sequential numbering
- **Inputs**: None  
- **Outputs**: 1 (string - formatted number)
- **Content Widget**: Start, Step, Padding spinboxes

### TextRemovalNode (202)
- **Purpose**: Remove patterns from input
- **Inputs**: 1 (string to process)
- **Outputs**: 1 (processed string)
- **Content Widget**: Pattern input, regex checkbox

### MetadataNode (203)
- **Purpose**: Extract EXIF/metadata values
- **Inputs**: None
- **Outputs**: 1 (string - metadata value)
- **Content Widget**: Field selector dropdown

### TextInputNode (204)
- **Purpose**: User-specified literal text
- **Inputs**: None
- **Outputs**: 1 (string)
- **Content Widget**: Text input field

### TransformNode (205)
- **Purpose**: Case/trim transformations
- **Inputs**: 1 (string)
- **Outputs**: 1 (transformed string)
- **Content Widget**: Transform type dropdown

### ConcatNode (206)
- **Purpose**: Join multiple strings
- **Inputs**: N (variable, strings)
- **Outputs**: 1 (concatenated string)
- **Content Widget**: Separator input

### OutputNode (207)
- **Purpose**: Final filename destination
- **Inputs**: 1 (final filename string)
- **Outputs**: None
- **Content Widget**: Extension handling dropdown

---

## Validation Rules

1. **Single Output**: Graph must have exactly one OutputNode
2. **Connected Output**: OutputNode must have connected input
3. **No Cycles**: Graph must be acyclic (DAG)
4. **Type Matching**: String outputs to string inputs only
5. **Source Nodes**: OriginalName, Counter, Metadata, TextInput need no inputs

---

## Backward Compatibility

The linear module view will remain as the default. Users can:
1. Switch to node editor view via menu/toolbar
2. Convert existing module configuration to graph
3. Export graph back to linear module list
4. Save/load both formats independently

---

## Testing Strategy

### Unit Tests
- Each node's eval() method
- Graph validation rules
- Graph execution order
- Serialization/deserialization

### Integration Tests
- Node editor widget creation
- Graph to module conversion
- Preview generation with graph
- Theme switching

### Manual Tests
- Drag & drop node creation
- Edge connections
- Real-time preview updates
- Save/load graph files

---

## References

- [MIGRATION_STANCE.md](MIGRATION_STANCE.md) - Architecture guidelines
- [REFACTORING_ROADMAP.md](REFACTORING_ROADMAP.md) - Refactoring status
- Node Editor: `/mnt/data_1/edu/Python/node_editor/`
- Node Editor Docs: `node_editor/docs/architecture.md`

---

## Progress Log

### 2026-01-03
- Created integration plan
- Phase 1 COMPLETE:
  - Copied node_editor package (52 built-in nodes, theme engine, serialization)
  - Updated all imports to full path (oncutf.ui.widgets.node_editor.*)
  - Created rename_graph domain layer (graph_model, validator, executor)
  - Created rename_graph_controller bridge
  - Created rename_nodes placeholder package
  - Added to mypy Tier 0 (external code)
  - All 974 tests passing, mypy clean
