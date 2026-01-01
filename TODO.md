# oncutf - TODO List

Consolidated list of all TODO items extracted from codebase (2026-01-01).

---

## High Priority Features

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

## Development/Testing Tasks

### 4. Rename Preview Profiling
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

## Completed Items

None yet - this is the initial TODO consolidation.

---

## Notes

- All TODOs extracted from codebase on 2026-01-01
- Sort column restoration (5 instances) is the most recurring item
- No critical or blocking TODOs identified
- All items are future enhancements, not bugs

