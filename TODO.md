# oncutf - TODO List

Consolidated list of all TODO items extracted from codebase.

**Last Updated:** 2026-01-31

---

## High Priority Features

### 1. Thumbnails Layout System

**Status:** In Progress (Phase 3 - UI Layer)  
**Priority:** High  
**Description:** Implement thumbnail view mode for visual file browsing alongside the current table view.

**Current Progress:**

- ✅ Phase 1: Core Infrastructure (ThumbnailCache, Providers, DB migrations)
- ✅ Phase 2: ThumbnailManager & Workers (background generation)
- ⏳ Phase 3: UI Layer (ThumbnailDelegate, ThumbnailViewportWidget, Lasso Selection)
- ⏳ Phase 4: Integration & Sync (model synchronization, sorting)
- 📋 Phase 6: Testing & Polish

**See:** [thumbnail_viewport_implementation_plan.md](docs/thumbnail_viewport_implementation_plan.md)

**Deferred Features (Post-MVP):**

- **Video Preview Dialog:** Frame-by-frame video preview with custom frame picker
  - Playback controls (play, pause, seek)
  - Frame stepping (arrow keys)
  - "Set This Frame as Thumbnail" action
  - Estimated effort: 3-5 days

**Benefits:**

- Easier visual file identification
- Better UX for photographers/video editors
- Industry-standard feature (like Lightroom, Bridge)

---

### 2. Node Editor Implementation

**Status:** Foundation Ready  
**Priority:** High  
**Description:** Visual node-based rename pipeline editor as alternative to linear module list.

**Current Foundation:**

- `ModuleOrchestrator` designed for node editor integration
- Architecture documented in [migration_stance.md](docs/migration_stance.md#node-editor-architecture-future)
- Controllers ready for graph-based workflow

**Implementation Plan:**

1. **Phase 1: Core Graph Model** (oncutf/core/rename_graph/)
   - Graph data structures (nodes, edges, sockets)
   - Graph validation and cycle detection
   - Topological sort for execution order
   - Serialization/deserialization

2. **Phase 2: UI Components** (oncutf/ui/widgets/node_editor/)
   - Canvas widget for node placement
   - Node rendering with input/output sockets
   - Connection/edge rendering with Bezier curves
   - Drag & drop node creation
   - Selection and connection handlers

3. **Phase 3: Integration**
   - Bidirectional conversion (linear ↔ graph)
   - Node editor controller orchestration
   - Save/load graph configurations
   - Preview integration

**Benefits:**

- Visual pipeline construction
- Better understanding of complex rename workflows
- Conditional branching support (future)
- Reusable pipeline templates

**Related TODOs:** Items 9-14 (graph implementation details)

---

### 3. Dockable Widgets System

**Status:** Not Started  
**Priority:** High  
**Description:** Implement docking/undocking system for main application panels (file table, metadata panel, preview, etc.).

**Current State:**

- Fixed layout with splitters
- No ability to detach panels into separate windows
- Limited customization for multi-monitor setups

**Proposed Features:**

- **Dockable Panels:** All main widgets can be docked/undocked
  - File Table
  - Metadata Panel (tree view)
  - Preview Panel
  - Rename Modules Panel
  - Properties/Info Panel
- **Floating Windows:** Detached panels as independent windows
- **Multi-Monitor Support:** Position panels across multiple screens
- **Drag & Drop Docking:** Visual feedback during dock operations
- **Dock Areas:** Top, bottom, left, right, center tabbed areas
- **State Persistence:** Save/restore dock layout across sessions
- **Reset to Default:** One-click layout restoration

**Technical Considerations:**

- Use QDockWidget for dock-able panels
- Store dock state in session database (hybrid config system)
- Handle window close events for floating panels
- Maintain controller orchestration (no business logic in dock widgets)
- Support both docked and floating modes simultaneously

**Benefits:**

- Flexible workspace customization
- Better multi-monitor workflow
- Industry-standard UI pattern (like Photoshop, Blender, VS Code)
- Power user feature for complex workflows

**Integration Points:**

- oncutf/ui/main_window.py - Convert splitter layout to dock system
- oncutf/core/session_state_manager.py - Persist dock geometry and state
- oncutf/ui/widgets/* - Wrap panels in QDockWidget containers
- oncutf/controllers/main_window_controller.py - Handle dock events

---

### 4. Metadata Database Search Functionality

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

## Development/Testing Tasks

### 6. Rename Preview Profiling

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

## Node Editor Implementation (Foundation)

### 7. Module-to-Graph Conversion

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

### 8. Graph-to-Module Conversion

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

### 9. Node Factory Implementation

**Status:** Not Started  
**Priority:** Low  
**Description:** Create node instances by type name using NodeRegistry.

**Location:** [oncutf/controllers/rename_graph_controller.py#L232](oncutf/controllers/rename_graph_controller.py#L232)

**Technical notes:**

- Use node_editor NodeRegistry to create nodes
- Should support all module types (counter, original_name, etc.)
- Part of node creation workflow

---

### 10. Edge Creation Implementation

**Status:** Not Started  
**Priority:** Low  
**Description:** Implement node connection logic for graph building.

**Location:** [oncutf/controllers/rename_graph_controller.py#L255](oncutf/controllers/rename_graph_controller.py#L255)

**Technical notes:**

- Validate socket compatibility before connecting
- Should use GraphValidator for connection rules
- Part of interactive graph editing

---

### 11. Graph Cycle Detection

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

### 12. Graph Topological Sort

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

### 13. Graph Deserialization

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

### Phase 7 (Final Polish) - Completed 2025-12-04 to 2026-01-11

#### Sort Column Persistence - Completed 2026-01-15

- **Full session persistence:** Sort column and order now save/restore across app restarts
- **Clear table preserves state:** Escape key clears files but remembers sort preference
- **5 integration tests:** Comprehensive test coverage for save/load/clear workflows
- **Files modified:** window_config_manager.py, shortcut_manager.py, initialization_orchestrator.py
- **Test file:** tests/integration/test_sort_column_persistence.py

#### Performance Optimizations

- **Startup Optimization:** 31% faster application startup (1426ms → 989ms)
  - Lazy-loaded ExifToolWrapper in UnifiedMetadataManager (12% improvement)
  - Lazy-loaded CompanionFilesHelper in UnifiedMetadataManager (21% improvement)
  - Exceeded target of <1000ms startup time
- **Memory Optimization:** Bounded memory caches to prevent unbounded growth
  - Added LRU eviction to PersistentHashCache (1000 entry limit)
  - Added LRU eviction to PersistentMetadataCache (500 entry limit)
- **Performance Profiling:** Created comprehensive profiling infrastructure
  - Added scripts/profile_startup.py for startup time analysis
  - Added scripts/profile_memory.py for memory usage tracking
  - Created docs/PERFORMANCE_BASELINE.md

#### Architecture Improvements

- **MainWindowController:** High-level multi-service orchestration completed
  - Coordinates FileLoad, Metadata, and Rename controllers
  - Session restoration and graceful shutdown workflows
  - Full integration tests
- **Mixin Extraction:** FileTableView complexity reduced by 24%
  - Extracted SelectionMixin (486 lines, 12 methods)
  - Extracted DragDropMixin (365 lines, 9 methods)
  - Created widgets/mixins/ package

#### Features

- **Companion Files System:** Complete implementation
  - Sony XML metadata files support
  - XMP sidecar files for RAW images
  - Subtitle file support (SRT, VTT, ASS)
  - Automatic companion file renaming
  - Metadata integration and enhancement

#### Code Quality

- **Test Coverage:** 1006 comprehensive tests across all modules
- **Logging Standardization:** All modules use get_cached_logger(**name**)
- **Deprecation System:** @deprecated decorator with migration guidance
- **Type Safety:** Added TypedDicts and Literal types
- **Windows Crash Fix:** Fixed application exit hang

#### Documentation

- **Cache Strategy Documentation:** 2500+ lines comprehensive guide
  - Complete guide for all cache managers
  - 30+ working code examples
  - Performance benchmarks
  - Troubleshooting guide and best practices

#### Repository Quality Improvements - Completed 2026-01-30 to 2026-01-31

- **Formatting Verification:** All 598 files verified as properly formatted (P0-1)
- **Vulture Integration:** Added vulture≥2.3 to dev dependencies for dead code analysis (P0-2)
- **Dead Code Cleanup:** Fixed 2 unused variables flagged by vulture at 100% confidence (P0-3)
- **Import Refinement:** Verified all "unused imports" are correctly used in TYPE_CHECKING blocks (P0-4)
- **Path Normalization:** Consolidated duplicate `normalize_path()` implementations (P1-2)
  - `database_manager.py` now delegates to `path_store.normalize_path()`
  - `path_store.py` uses canonical implementation from `path_normalizer.py`
- **ApplicationContext Migration:** Migrated 13 files from deprecated `application_context.py` to `QtAppContext` (P1-3)
  - Deleted deprecated `oncutf/ui/adapters/application_context.py`
  - All UI components now use `get_qt_app_context()` for Qt-aware context access
- **Code Simplification:**
  - **format_bytes Consolidation (P2-1):** Removed duplicate `format_bytes()` implementations, now using `FileSizeFormatter` consistently
  - **UI State Service Refactor (P2-3):** Removed redundant `ui_state_service.py` facade (-114 lines)
    - 3 consumers updated to use `FileTableStateHelper` directly
    - Simplified architecture by eliminating temporary facade layer
- **TODO Documentation (P1-4):** Created comprehensive `todo_tracking.md` with 6 documented TODOs
  - Categorized by priority (High/Medium/Low)
  - Proposed GitHub issue titles and descriptions
  - Ready for manual GitHub issue creation
- **Wildcard Import Elimination:** Removed final wildcard import from `main_window.py`
  - All `from module import *` replaced with explicit imports
  - `RUF012` (mutable class defaults) verified active and enforcing
- **Quality Gates:** All checks pass (ruff, mypy, pytest)

---

## Notes

- TODOs initially extracted on 2026-01-01, reorganized 2026-01-16
- **Total:** 13 active TODO items (5 completed items archived)
- **Remaining:** 13 active tasks
- **By Category:**
  - High Priority Features: 4 (Thumbnails Layout, Node Editor, Dockable Widgets, Metadata Search)
  - Architecture/Refactoring: 1 (Backup Store Extraction)
  - Development/Testing: 1 (Rename Preview Profiling)
  - Node Editor Foundation: 7 (technical implementation details)
- **Priority Breakdown:**
  - High: 4 (Thumbnails Layout, Node Editor Implementation, Dockable Widgets, Metadata Search)
  - Medium: 2 (Cycle Detection, Topological Sort)
  - Low: 7 (remaining implementation details)
- **Completed (Archived):**
  - Metadata Key Simplification (128 tests, 2026-01-15)
  - Sort Column Persistence (5 integration tests, 2026-01-15)
  - Non-Blocking Conflict Resolution UI (6 tests, 2026-01-15)
  - Hybrid Config System (JSON + Database, 2026-01-15)
  - Hash Duplicates Migration (1173 tests, 2026-01-15)
- No critical or blocking TODOs identified
- All items are feature enhancements, not bugs
- Node Editor has solid architectural foundation ready (see migration_stance.md)
