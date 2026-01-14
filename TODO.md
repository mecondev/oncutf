# oncutf - TODO List

Consolidated list of all TODO items extracted from codebase.

**Last Updated:** 2026-01-14

---

## High Priority Features

### 0. Metadata Key Simplification
**Status:** Planned  
**Priority:** High  
**Description:** Implement algorithmic simplification of long metadata keys with semantic aliasing for cross-format consistency.

**Implementation Roadmap:** See [docs/metadata_key_simplification_plan.md](docs/metadata_key_simplification_plan.md)

**Key Features:**
- SmartKeySimplifier: Algorithmic key simplification (removes common prefixes, repetitions)
- SimplifiedMetadata: Bidirectional wrapper (original <-> simplified)
- MetadataKeyRegistry: Undo/redo, conflict resolution, export/import
- Semantic Aliases: Fixed predefined aliases (Lightroom-style)
- User Config: Auto-created at ~/.oncutf/semantic_metadata_aliases.json

**Components:**
1. Phase 1 (Core): SmartKeySimplifier, SimplifiedMetadata, MetadataKeyRegistry
2. Phase 2 (Config): Semantic aliases file
3. Phase 3 (Integration): Update UnifiedMetadataManager, metadata module
4. Phase 4 (UI): Configuration dialog
5. Phase 5 (Testing): Integration and performance tests

**Estimated Duration:** 8-11 working days

**Current Status:** Planning complete, ready for implementation

---

### 1. Last State Restoration (Sort Column Persistence)
**Status:** Planned  
**Priority:** Medium  
**Description:** Implement persistent storage and restoration of sort column state across sessions.

**Implementation needed in:**
- [oncutf/core/ui_managers/shortcut_manager.py#L64](oncutf/core/ui_managers/shortcut_manager.py#L64) - Restore previous sort column when clearing (Escape key)
- [oncutf/core/ui_managers/window_config_manager.py#L276](oncutf/core/ui_managers/window_config_manager.py#L276) - Restore actual sort column from config
- [oncutf/core/ui_managers/window_config_manager.py#L381](oncutf/core/ui_managers/window_config_manager.py#L381) - Restore sort column preference in getter
- [oncutf/core/initialization/initialization_orchestrator.py#L156](oncutf/core/initialization/initialization_orchestrator.py#L156) - Restore saved sort column during initialization
- [oncutf/utils/shared/json_config_manager.py#L76](oncutf/utils/shared/json_config_manager.py#L76) - Remember actual sort column in config

**Current behavior:**
- Sort column always defaults to column 2 (filename) on startup
- Sort state is lost when clearing file table (Escape)
- Sort state is not persisted in config

**Desired behavior:**
- Save current sort column and order when changed
- Restore saved sort column on application startup
- Restore previous sort column after clearing file table
- Persist across sessions in window config JSON

**Technical notes:**
- Currently hardcoded to column 2 (filename) instead of column 1 (color)
- Needs integration with FileTableStateHelper
- Should be part of window_config in json_config_manager

---

### 2. Non-Blocking Conflict Resolution UI
**Status:** Planned  
**Priority:** Medium  
**Description:** Implement proper UI for handling file rename conflicts without blocking the rename workflow.

**Location:** [oncutf/core/file/operations_manager.py#L78](oncutf/core/file/operations_manager.py#L78)

**Current behavior:**
- Conflicts are automatically skipped
- No user interaction for conflict resolution
- Prevents blocking but gives no control to user

**Desired behavior:**
- Show dialog with conflict details (existing file, new name)
- Options: Skip, Overwrite, Rename with suffix, Cancel batch
- Non-blocking implementation (async or deferred)
- Remember choice for batch operations (apply to all)

**Technical notes:**
- Must not block unified_rename_engine workflow
- Consider using Qt signals for async UI updates
- May need custom dialog similar to CustomMessageDialog

---

### 3. Metadata Database Search Functionality
**Status:** Planned  
**Priority:** Low  
**Description:** Implement full-text search across metadata database for finding files by metadata values.

**Location:** [oncutf/core/metadata/structured_manager.py#L418](oncutf/core/metadata/structured_manager.py#L418)

**Current behavior:**
- Search method exists but returns empty list
- No database query implementation

**Desired behavior:**
- Search metadata fields (EXIF, XMP, IPTC) by value
- Support wildcards and regex patterns
- Return matching file paths
- Integrate with file table filtering

**Technical notes:**
- Requires SQL query building for metadata JSON column
- May need SQLite JSON functions (json_extract)
- Consider performance implications for large databases
- Might need separate search index table

---

## Architecture/Refactoring Tasks

### 5. Backup Store Extraction
**Status:** Not Started  
**Priority:** Low  
**Description:** Extract rename history methods from DatabaseManager to BackupStore for better separation of concerns.

**Location:** [oncutf/core/database/backup_store.py#L35](oncutf/core/database/backup_store.py#L35)

**Methods to extract:**
- `store_rename_operation`
- `get_rename_history`
- `get_rename_operations_by_id`
- `get_last_operation_id`
- `clear_rename_history`

**Technical notes:**
- Part of database split plan
- Improves modularity of database layer
- BackupStore already has basic structure
- Should maintain backward compatibility

---

### 6. Hash Duplicates Migration
**Status:** Not Started  
**Priority:** Medium  
**Description:** Migrate duplicate detection to use HashLoadingService callbacks instead of legacy HashWorkerCoordinator.

**Location:** [oncutf/core/hash/hash_operations_manager.py#L64](oncutf/core/hash/hash_operations_manager.py#L64)

**Current behavior:**
- Uses legacy `HashWorkerCoordinator` for backward compatibility
- Duplicates feature not using modern callback architecture

**Desired behavior:**
- Use `HashLoadingService` with callbacks
- Remove dependency on `HashWorkerCoordinator`
- Consistent architecture with other hash operations

**Technical notes:**
- Part of hash system modernization
- May require changes to duplicate detection UI
- Test thoroughly with large file sets

---

## Development/Testing Tasks

### 7. Rename Preview Profiling
**Status:** Not Started  
**Priority:** Low  
**Description:** Complete profiling implementation for rename preview performance testing.

**Location:** [scripts/profile_performance.py#L173](scripts/profile_performance.py#L173)

**Current behavior:**
- Profiling script exists but rename preview section is stubbed
- Prints warning message instead of running profile

**Desired behavior:**
- Load sample files (various sizes and types)
- Trigger rename preview with different module combinations
- Measure time for preview generation
- Profile metadata loading impact
- Generate performance report

**Technical notes:**
- Should use test fixtures or example files
- Need to simulate different file counts (10, 100, 1000+)
- Profile both with and without metadata caching
- Compare performance across different rename modules

---

## Node Editor Implementation (Future)

### 8. Module-to-Graph Conversion
**Status:** Not Started  
**Priority:** Low  
**Description:** Implement conversion from linear module list to node graph representation.

**Location:** [oncutf/controllers/rename_graph_controller.py#L196](oncutf/controllers/rename_graph_controller.py#L196)

**Implementation steps:**
1. Create appropriate nodes for each module
2. Connect nodes in sequence
3. Add OutputNode at end

**Technical notes:**
- Part of future Node Editor feature (see migration_stance.md)
- Foundation already exists in ModuleOrchestrator
- Should preserve existing linear UI

---

### 9. Graph-to-Module Conversion
**Status:** Not Started  
**Priority:** Low  
**Description:** Implement conversion from node graph back to linear module list.

**Location:** [oncutf/controllers/rename_graph_controller.py#L212](oncutf/controllers/rename_graph_controller.py#L212)

**Implementation steps:**
1. Traverse graph in execution order
2. Convert each node to module config
3. Return list compatible with existing system

**Technical notes:**
- Required for bidirectional editing (linear ↔ graph)
- Should use topological sort from graph_model
- Output must be compatible with get_all_data() format

---

### 10. Node Factory Implementation
**Status:** Not Started  
**Priority:** Low  
**Description:** Create node instances by type name using NodeRegistry.

**Location:** [oncutf/controllers/rename_graph_controller.py#L232](oncutf/controllers/rename_graph_controller.py#L232)

**Technical notes:**
- Use node_editor NodeRegistry to create nodes
- Should support all module types (counter, original_name, etc.)
- Part of node creation workflow

---

### 11. Edge Creation Implementation
**Status:** Not Started  
**Priority:** Low  
**Description:** Implement node connection logic for graph building.

**Location:** [oncutf/controllers/rename_graph_controller.py#L255](oncutf/controllers/rename_graph_controller.py#L255)

**Technical notes:**
- Validate socket compatibility before connecting
- Should use GraphValidator for connection rules
- Part of interactive graph editing

---

### 12. Graph Cycle Detection
**Status:** Not Started  
**Priority:** Medium  
**Description:** Implement proper cycle detection using Depth-First Search for graph validation.

**Location:** [oncutf/core/rename_graph/graph_validator.py#L138](oncutf/core/rename_graph/graph_validator.py#L138)

**Current behavior:**
- Placeholder returns empty list (assumes no cycles)

**Desired behavior:**
- DFS-based cycle detection
- Return list of error messages with cycle details
- Prevent invalid graph execution

**Technical notes:**
- Critical for graph validation
- Should detect all cycles, not just first one
- Consider performance with large graphs

---

### 13. Graph Topological Sort
**Status:** Not Started  
**Priority:** Medium  
**Description:** Implement topological sort for proper node execution order.

**Location:** [oncutf/core/rename_graph/graph_model.py#L152](oncutf/core/rename_graph/graph_model.py#L152)

**Current behavior:**
- Returns nodes as-is (insertion order)

**Desired behavior:**
- Kahn's algorithm or DFS-based topological sort
- Order nodes for execution (dependencies first)
- Handle multiple valid orderings

**Technical notes:**
- Required for correct graph execution
- Should work with cycle detection
- Consider caching for performance

---

### 14. Graph Deserialization
**Status:** Not Started  
**Priority:** Low  
**Description:** Implement loading of saved graph configurations from dict representation.

**Location:** [oncutf/core/rename_graph/graph_model.py#L177](oncutf/core/rename_graph/graph_model.py#L177)

**Current behavior:**
- Placeholder returns True without loading

**Desired behavior:**
- Reconstruct graph from serialized dict
- Restore nodes, edges, and metadata
- Validate deserialized graph

**Technical notes:**
- Counterpart to serialize() method
- Should handle version compatibility
- Part of graph persistence system

---

## Completed Items

None yet - this is the initial TODO consolidation.

---

## Notes

- TODOs initially extracted on 2026-01-01, updated 2026-01-15
- **Total:** 15 TODO items tracked (added metadata key simplification)
- **By Category:**
  - High Priority Features: 4 (was 3, now includes metadata simplification)
  - Architecture/Refactoring: 2
  - Development/Testing: 1
  - Node Editor Implementation: 7
  - Infrastructure: 1 (sort column - 5 locations)
- **Priority Breakdown:**
  - High: 1 (Metadata Key Simplification - estimated 8-11 days)
  - Medium: 5 (Sort Column, Conflict Resolution, Cycle Detection, Topological Sort, Hash Migration)
  - Low: 9
- No critical or blocking TODOs identified
- All items are future enhancements, not bugs
- Node Editor items are foundation for future visual rename editor (see migration_stance.md)

