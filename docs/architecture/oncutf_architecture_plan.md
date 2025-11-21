# oncutf - Comprehensive Architecture Analysis & Improvement Plan

## Executive Summary

This document provides a deep analysis of the oncutf codebase architecture, identifies critical patterns and data flows, and proposes concrete, prioritized improvements. The analysis is based on direct code inspection and aims to be actionable for incremental refactoring.

---

## 1. High-Level Architecture Map

### 1.1 Core Application Layer

**Entry Points & Orchestration**
- `main.py` - Application entry, logging setup, Qt initialization, splash screen, theme application
- `main_window.py` - Primary UI controller (1532 lines), orchestrates all managers and coordinates UI operations
- `core/application_context.py` - Centralized application state management (singleton pattern)
- `core/application_service.py` - Facade providing unified API to all managers (751 lines)

**Key Observations:**
- MainWindow is large and acts as central coordinator
- ApplicationContext is in "skeleton mode" - gradual migration to centralized state
- ApplicationService reduces coupling but requires all managers to exist before initialization

### 1.2 Core Manager Layer

**File & Data Management**
- `core/file_load_manager.py` - File loading from drag/drop, browse, folder traversal
- `core/file_store.py` - Centralized file state (part of ApplicationContext migration)
- `core/selection_manager.py` - Selection state coordination
- `core/selection_store.py` - Persistent selection state (part of ApplicationContext migration)
- `core/table_manager.py` - File table behavior and display coordination

**Metadata System**
- `core/metadata_manager.py` - Primary metadata operations coordinator (980 lines)
- `core/unified_metadata_manager.py` - Unified metadata API facade
- `core/structured_metadata_manager.py` - Categorized metadata with database schema (V3)
- `core/persistent_metadata_cache.py` - Persistent caching between sessions
- `core/direct_metadata_loader.py` - Direct metadata loading operations
- `utils/metadata_loader.py` - Threaded metadata worker with progress tracking
- `utils/exiftool_wrapper.py` - ExifTool process management with `-stay_open` mode (530 lines)

**Rename System**
- `core/unified_rename_engine.py` - Central rename orchestrator (preview → validation → execution)
- `core/preview_manager.py` - Preview generation with caching (324 lines)
- `core/rename_manager.py` - Rename execution and conflict handling
- `utils/preview_engine.py` - Module composition and application (165 lines)
- `utils/rename_logic.py` - Safe case-aware rename operations (248 lines)

**Database & Persistence**
- `core/database_manager.py` - SQLite database with V3 schema (structured metadata)
- `core/optimized_database_manager.py` - Performance-optimized database operations
- `core/persistent_hash_cache.py` - File hash caching (CRC32)
- `core/backup_manager.py` - Automatic database backups (periodic + shutdown)
- `core/rename_history_manager.py` - Rename operation history and undo

**UI Coordination**
- `core/ui_manager.py` - Overall UI layout and component setup
- `core/status_manager.py` - Status bar and progress reporting
- `core/dialog_manager.py` - Dialog coordination and management
- `core/shortcut_manager.py` - Keyboard shortcuts and actions
- `core/window_config_manager.py` - Window geometry persistence
- `core/splitter_manager.py` - Splitter state management

**Concurrency & Threading**
- `core/thread_pool_manager.py` - Qt-based worker thread management with priority queues (577 lines)
- `core/async_operations_manager.py` - asyncio-based operations in separate thread
- `utils/timer_manager.py` - Centralized timer management with consolidation
- `core/hash_worker.py` - Threaded hash calculation worker

**Drag & Drop System**
- `core/drag_manager.py` - Drag operation coordination (singleton)
- `core/drag_visual_manager.py` - Visual feedback for drag operations
- `core/drag_cleanup_manager.py` - Cleanup after drag operations
- `utils/drag_zone_validator.py` - Drop zone validation logic
- `utils/file_drop_helper.py` - File path extraction from drops

### 1.3 Rename Module System

**Base Infrastructure**
- `modules/base_module.py` - Base widget for all rename modules with signal protection
  - Contract: `is_effective()`, `get_data()`, `apply_from_data()`
  - Signal management: `emit_if_changed()` to prevent redundant updates
  - Theme inheritance support

**Module Implementations**
- `modules/specified_text_module.py` - Add custom text with context menu shortcuts
- `modules/counter_module.py` - Sequential numbering with padding/step
- `modules/metadata_module.py` - File date and metadata field insertion
- `modules/original_name_module.py` - Original name with transformations
- `modules/name_transform_module.py` - Case and separator transforms
- `modules/text_removal_module.py` - Remove text patterns from names

**Module Composition**
- Modules produce name fragments (not full filenames)
- `utils/preview_engine.py` applies modules in sequence
- Final transform applied after module composition
- Module caching with 50ms TTL to optimize rapid UI changes

### 1.4 UI Widget Layer

**File & Table Views**
- `widgets/file_table_view.py` - Custom QTableView with Windows Explorer behavior (2689 lines)
  - Full-row selection with anchor handling
  - Intelligent column width management with 7-second delayed save
  - Drag & drop support with custom MIME types
  - Hover highlighting and visual feedback

- `widgets/file_tree_view.py` - Folder navigation tree with drag support
- `widgets/interactive_header.py` - Custom table header with column management

**Metadata Display**
- `widgets/metadata_tree_view.py` - Hierarchical metadata display (3271 lines)
  - Drag & drop from file table to load metadata
  - Context menu for copy/edit/reset
  - Scroll position memory per file with smooth animation
  - Placeholder mode for empty content
  - Modified item tracking with visual indicators

**Rename Module UI**
- `widgets/rename_module_widget.py` - Individual module container
- `widgets/rename_modules_area.py` - Module management area with add/remove
- `widgets/final_transform_container.py` - Post-processing transform UI
- `widgets/name_transform_widget.py` - Case/separator transform widget
- `widgets/original_name_widget.py` - Original name module widget

**Dialogs & Helpers**
- `widgets/custom_message_dialog.py` - Themed message dialogs
- `widgets/rename_conflict_resolver.py` - Conflict resolution dialog
- `widgets/metadata_edit_dialog.py` - Metadata field editor
- `widgets/metadata_waiting_dialog.py` - Progress dialog for metadata loading
- `widgets/custom_splash_screen.py` - Application splash screen

**Delegates & Validation**
- `widgets/ui_delegates.py` - Custom item delegates (hover, combobox, tree)
- `widgets/validated_line_edit.py` - Real-time input validation
- `widgets/base_validated_input.py` - Base class for validated inputs

### 1.5 Utility Layer

**Path & File Utilities**
- `utils/path_utils.py` - Cross-platform path operations
- `utils/path_normalizer.py` - Path normalization for Windows
- `utils/filename_validator.py` - Filename validation rules
- `utils/validate_filename_text.py` - Text content validation
- `utils/file_size_formatter.py` - Human-readable file sizes
- `utils/file_drop_helper.py` - Extract file paths from drop events

**Visual & Theme**
- `utils/theme_engine.py` - Central theming system
- `utils/theme_font_generator.py` - DPI-aware font sizing
- `utils/dpi_helper.py` - Multi-monitor DPI detection
- `utils/icon_cache.py` - Icon caching for performance
- `utils/icon_utilities.py` - Icon generation and manipulation
- `utils/svg_icon_generator.py` - SVG icon generation
- `utils/smart_icon_cache.py` - Advanced icon caching

**Metadata Helpers**
- `utils/metadata_cache_helper.py` - Metadata cache access patterns
- `utils/metadata_field_mapper.py` - Field name mapping
- `utils/metadata_field_validators.py` - Metadata value validation
- `utils/metadata_exporter.py` - Export metadata to CSV/JSON
- `utils/build_metadata_tree_model.py` - Build tree model from metadata

**Logging & Config**
- `utils/logger_factory.py` - Cached logger instances
- `utils/logger_setup.py` - Logging configuration
- `utils/json_config_manager.py` - JSON-based settings persistence
- `config.py` - Global configuration constants (755 lines)

**UI Helpers**
- `utils/placeholder_helper.py` - Placeholder text for empty views
- `utils/tooltip_helper.py` - Tooltip management
- `utils/cursor_helper.py` - Cursor state management
- `utils/multiscreen_helper.py` - Multi-monitor support

---

## 2. Main Data Flows

### 2.1 File Loading Pipeline

```
User Action (Browse/Drag/Drop)
    ↓
FileLoadManager.load_folder() / load_files_from_paths()
    ↓
File Validation (FileValidationManager)
    ↓
FileItem Creation (models/file_item.py)
    ↓
FileTableModel Population (models/file_table_model.py)
    ↓
UI Update (FileTableView)
    ↓
Optional: Metadata Loading (based on modifiers)
```

**Key Decision Points:**
- Modifier keys determine metadata loading mode:
  - No modifier: Skip metadata (folder) / Fast metadata (file drop)
  - Ctrl: Load basic metadata
  - Ctrl+Shift: Load extended metadata
- Recursive folder loading remembered from previous operation
- File extensions filtered against `ALLOWED_EXTENSIONS` in `config.py`

### 2.2 Metadata Loading Pipeline

```
Metadata Request (from FileLoadManager or user action)
    ↓
MetadataManager.determine_metadata_mode()
    ↓
Check Persistent Cache (PersistentMetadataCache)
    ↓ (cache miss)
ExifToolWrapper.get_metadata_batch()
    ↓ (batch processing in subprocess)
Parse JSON Output
    ↓
Store in Database (DatabaseManager)
    ↓
Update Memory Cache
    ↓
Update FileItem.metadata
    ↓
Emit signals for UI update
```

**Performance Optimizations:**
- ExifTool runs in `-stay_open` mode for fast repeated calls
- Batch metadata loading (10x faster than individual calls)
- Two-tier caching: memory + persistent database
- Incremental loading with progress dialogs for large file sets

**Threading:**
- Metadata loading runs in QThread workers (MetadataWorker in widgets/metadata_worker.py)
- Progress signals: `progress(current, total)` and `size_progress(processed_bytes, total_bytes)`
- Cancellable operations via flag

### 2.3 Rename Preview Pipeline

```
Module Configuration Change / File Selection Change
    ↓
PreviewManager.generate_preview_names()
    ↓
Check Preview Cache (100ms TTL)
    ↓ (cache miss)
For each file:
    UnifiedRenameEngine.generate_preview()
        ↓
    Apply modules in sequence (preview_engine.apply_rename_modules)
        ↓
    Check module effectiveness (is_effective())
        ↓
    Get module output (apply_from_data())
        ↓
    Concatenate fragments
        ↓
    Apply final transform (NameTransformModule)
        ↓
    Validate filename (filename_validator)
    ↓
Generate (old_name, new_name) pairs
    ↓
ValidationManager.validate_preview()
    - Check for duplicates
    - Validate filenames
    - Detect unchanged names
    ↓
Update PreviewTablesView
    ↓
Update StatusManager with stats
```

**Caching Strategy:**
- Preview results cached with key: `hash(file_paths) + hash(modules_data) + hash(post_transform)`
- Cache validity: 100ms (prevents redundant computation during rapid UI changes)
- Module results cached separately with 50ms TTL

### 2.4 Rename Execution Pipeline

```
User clicks "Rename" button
    ↓
RenameManager.execute_rename()
    ↓
UnifiedRenameEngine.execute_rename()
    ↓
Build execution plan (old_path → new_path pairs)
    ↓
For each file:
    Validate filename
        ↓
    Check for conflicts (os.path.exists(new_path))
        ↓ (conflict detected)
    ConflictResolver dialog
        - Skip / Skip All / Overwrite / Cancel
        ↓
    Determine if case-only change
        ↓ (case-only)
    safe_case_rename() - two-step process for Windows
        ↓ (regular rename)
    os.rename()
        ↓
    Update rename history (RenameHistoryManager)
        ↓
    Store in database
    ↓
Update UI with results (ExecutionResult)
    ↓
Emit completion signals
```

**Safety Mechanisms:**
- Case-only rename detection and two-step process for Windows NTFS
- Conflict resolution with user choice
- Rename history for undo capability
- Database transaction for atomicity
- Error recovery and partial success handling

### 2.5 Database Interaction Flow

```
Application Operation (metadata load, hash calc, rename)
    ↓
DatabaseManager method call
    ↓
Connection Pool (thread-safe)
    ↓
SQLite with WAL mode
    ↓
Structured schema (V3):
    - file_paths (central registry)
    - file_metadata (raw ExifTool JSON)
    - file_metadata_structured (categorized fields)
    - file_hashes (CRC32, etc.)
    - file_rename_history (operations log)
    ↓
Automatic cleanup (orphaned records)
    ↓
Periodic backups (BackupManager)
    - Every 15 minutes
    - On shutdown
    - Rotation: keep 2 most recent
```

### 2.6 Signal Flow Architecture

**Key Signal Chains:**

1. **File Selection Change:**
   ```
   FileTableView.selection_changed
       → SelectionManager
       → ApplicationContext.selection_changed
       → PreviewManager (update preview)
       → MetadataTreeView (update display)
   ```

2. **Module Configuration Change:**
   ```
   RenameModuleWidget.updated
       → RenameModulesArea
       → PreviewManager (regenerate preview)
       → PreviewTablesView (update display)
   ```

3. **Metadata Loading Complete:**
   ```
   MetadataWorker.finished
       → MetadataManager
       → Update cache
       → Update FileItem
       → TableManager (update display)
       → PreviewManager (regenerate if metadata-dependent)
   ```

---

## 3. Critical Patterns & Conventions

### 3.1 Rename Module Contract

**Pure Function Pattern:**
- Modules produce name fragments, NOT full filenames
- No filesystem operations in modules
- No side effects (except UI updates)

**Required Methods:**
```python
class RenameModule(BaseRenameModule):
    @staticmethod
    def is_effective(data: dict) -> bool:
        """Return True if module should contribute to output"""

    @staticmethod
    def apply_from_data(data: dict, file_item: FileItem,
                        index: int, metadata_cache=None) -> str:
        """Generate name fragment from configuration"""

    def get_data(self) -> dict:
        """Return current module configuration"""
```

**Signal Management:**
- Use `emit_if_changed()` to prevent redundant signal emissions
- Block signals during programmatic updates: `block_signals_while(widget, func)`
- Last value tracking to detect actual changes

**Theme Integration:**
- Override `_ensure_theme_inheritance()` sparingly
- Prefer global ThemeEngine styling over per-widget QSS
- Avoid stylesheet pollution that affects child widgets (especially combo trees)

### 3.2 Manager Pattern Usage

**Separation of Concerns:**
- Business logic lives in `core/*_manager.py`
- UI code in `widgets/`
- Widgets delegate to managers via ApplicationService

**Manager Initialization:**
- Managers created in MainWindow.__init__()
- ApplicationService.initialize() verifies all managers exist
- Circular dependency prevention via late imports

**Manager Communication:**
- Via Qt signals (loose coupling)
- Via ApplicationContext (centralized state)
- Direct method calls through ApplicationService facade

**Example Manager Responsibilities:**
- FileLoadManager: File import logic, validation, model population
- MetadataManager: Metadata operations, threading, progress
- PreviewManager: Preview generation, caching
- RenameManager: Execution, conflict resolution, history

### 3.3 Threading & Concurrency Model

**Current Dual Model (Issue Identified):**

1. **Qt Thread Model (primary):**
   - `core/thread_pool_manager.py` - Priority-based work queue
   - Workers: QThread with QObject for signals
   - Used for: Hash calculation, file processing
   - Features: Priority queues, resource-aware allocation, work stealing

2. **asyncio Model (underutilized):**
   - `core/async_operations_manager.py` - Separate asyncio event loop in Python thread
   - Used for: Potentially I/O-bound operations
   - Complexity: Mixing Qt signals with asyncio requires careful synchronization

**Threading Patterns:**
- Long-running operations (metadata, hashing) use worker threads
- Progress reporting via Qt signals: `progress(current, total)`
- Cancellation via shared boolean flags
- Cleanup on shutdown: request_shutdown() → wait with timeout

**Timer Consolidation:**
- `utils/timer_manager.py` prevents UI flooding
- Groups similar timers (e.g., multiple column resize events)
- Priority levels: CRITICAL, HIGH, NORMAL, LOW, BACKGROUND
- Automatic cleanup on shutdown

### 3.4 Caching Strategy

**Multi-Level Cache Hierarchy:**

1. **Module Result Cache (50ms TTL)**
   - In `utils/preview_engine.py`
   - Caches individual module outputs
   - Very short-lived for rapid UI updates

2. **Preview Cache (100ms TTL)**
   - In `core/preview_manager.py` and `core/unified_rename_engine.py`
   - Caches complete preview results
   - Key: hash(files + modules + transforms)

3. **Memory Cache (session-scoped)**
   - In `core/persistent_metadata_cache.py`
   - Holds metadata for current session
   - LRU eviction when size limits exceeded

4. **Database Cache (persistent)**
   - SQLite database with WAL mode
   - Survives application restarts
   - Automatic cleanup of orphaned records

**Cache Invalidation:**
- Time-based expiration (TTL)
- Manual clearing on file changes
- Automatic on file timestamp changes
- Per-key timestamps (not global)

### 3.5 Signal/Slot Architecture

**Signal Naming Convention:**
- Past tense for completed events: `files_loaded`, `selection_changed`
- Progressive for ongoing: `progress`, `loading`
- Request prefix for commands: `request_preview_update`

**Connection Patterns:**
- Direct connections for same-thread communication
- Queued connections for cross-thread (automatic with Qt signals)
- Use lambdas sparingly (can cause memory leaks if not careful)
- Disconnect in cleanup methods to prevent dangling references

**Signal Debouncing:**
- Use TimerManager for consolidating rapid signals
- Example: Column resize events batched and saved after 7 seconds
- Prevents excessive I/O and processing

### 3.6 Database Patterns

**Connection Management:**
- Thread-local connections via get_connection()
- WAL mode for better concurrency
- Automatic connection pool cleanup

**Transaction Patterns:**
```python
with db_manager.get_connection() as conn:
    # Operations within transaction
    conn.commit()  # or conn.rollback()
```

**Schema Versioning:**
- V3 schema with structured metadata
- Automatic migration on version mismatch
- Default schema initialization with 7 categories, 37 fields

**Backup Strategy:**
- Periodic: Every 15 minutes (configurable)
- On shutdown: Always
- Rotation: Keep 2 most recent
- Format: `oncutf_YYYYMMDD_HHMMSS.db.bak`

### 3.7 Error Handling Patterns

**Logging Levels:**
- DEBUG: Detailed flow information (dev_only extra parameter)
- INFO: Normal operations, startup/shutdown
- WARNING: Recoverable issues (missing cache, slow operations)
- ERROR: Operation failures with context
- CRITICAL: Fatal errors preventing app startup

**Error Recovery:**
- Graceful degradation: Continue with reduced functionality
- User-friendly messages via DialogManager
- Detailed logging for debugging
- Cleanup in finally blocks and context managers

**ExifTool Error Handling:**
- Timeout handling (10 second default)
- Process restart on failure
- Fallback to empty metadata on error
- Force cleanup on shutdown

---

## 4. Identified Issues & Improvement Opportunities

### 4.1 Concurrency Model Complexity (HIGH PRIORITY)

**Issue:**
- Dual concurrency models (Qt threads + asyncio) increase complexity
- `async_operations_manager.py` runs asyncio loop in separate Python thread
- Potential for shutdown deadlocks and race conditions
- Unclear which model to use for new features

**Impact:**
- Maintenance burden
- Difficult to reason about thread safety
- Shutdown sequence is complex and error-prone

**Evidence:**
- `core/thread_pool_manager.py`: 577 lines with priority queues, work stealing
- `core/async_operations_manager.py`: Separate event loop management
- Multiple shutdown paths need coordination

### 4.2 MainWindow Size & Responsibility (MEDIUM PRIORITY)

**Issue:**
- MainWindow is 1532 lines and acts as central coordinator
- Many managers still initialized and stored in MainWindow
- ApplicationContext migration incomplete ("skeleton mode")
- ApplicationService requires all managers before initialization

**Impact:**
- Difficult to test in isolation
- Hard to understand complete flow
- Circular dependency risks

**Evidence:**
- `main_window.py`: 1532 lines
- `core/application_context.py`: Comments indicate "skeleton mode" and "gradual migration"

### 4.3 Metadata System Fragmentation (MEDIUM PRIORITY)

**Issue:**
- Multiple metadata managers: MetadataManager, UnifiedMetadataManager, StructuredMetadataManager
- Unclear responsibility boundaries
- DirectMetadataLoader vs MetadataLoader vs worker pattern

**Impact:**
- Confusion about which component to use
- Code duplication potential
- Testing complexity

**Evidence:**
- `core/metadata_manager.py`: 980 lines
- Multiple import paths for metadata operations
- Overlapping functionality

### 4.4 Preview Generation Performance (LOW-MEDIUM PRIORITY)

**Issue:**
- Preview caching is effective but could be smarter
- Module effectiveness checks happen after cache miss
- Batch metadata availability checks could be optimized
- Large file sets (1000+) can be slow

**Impact:**
- UI lag with many files
- User perception of slowness

**Evidence:**
- Caching with 100ms TTL helps but is time-based, not event-based
- Per-file module application with sequential checks

### 4.5 Testing Coverage Gaps (MEDIUM PRIORITY)

**Issue:**
- Test files exist but coverage is incomplete
- Limited integration tests for complete workflows
- GUI tests present but may skip on CI
- Mock fixtures for ExifTool and filesystem operations could be improved

**Impact:**
- Regression risks during refactoring
- Manual testing burden
- Difficult to validate complex scenarios

**Evidence:**
- 41 test files in `tests/` directory
- Markers configured (unit, integration, gui, exiftool, local_only)
- Some tests marked with `@pytest.mark.skip`

### 4.6 Drag & Drop System Complexity (LOW PRIORITY)

**Issue:**
- Drag and drop logic spread across multiple managers and helpers
- `drag_manager.py` (singleton), `drag_visual_manager.py`, `drag_cleanup_manager.py`
- Complex state tracking for active drags
- Visual feedback coordination across widgets

**Impact:**
- Hard to maintain and extend
- Subtle bugs in edge cases
- Testing difficulty

**Evidence:**
- Three separate manager files for drag operations
- Complex visual feedback state machine

### 4.7 Configuration Management (LOW PRIORITY)

**Issue:**
- `config.py` is 755 lines with many constants
- Mix of defaults and runtime state
- Debug flags at module level
- Some values should be user-configurable

**Impact:**
- Hard to find settings
- Debug flags accidentally left enabled
- Configuration sprawl

**Evidence:**
- `config.py`: 755 lines
- DEBUG_RESET_DATABASE, DEBUG_RESET_CONFIG flags
- Mix of UI defaults, paths, filters

---

## 5. Prioritized Improvement Plan

### Area A: Concurrency Model Consolidation 🔴 HIGH PRIORITY

**Current Situation:**
- Qt thread pool (primary) for CPU-bound tasks
- asyncio manager (underutilized) for I/O operations
- Both models present increases shutdown complexity
- Unclear patterns for new concurrent features

**Goals:**
1. Standardize on Qt threading model (better PyQt5 integration)
2. Migrate or remove async_operations_manager
3. Simplify shutdown sequence
4. Document threading patterns

**Proposed Changes:**

**✅ Task A1: Audit asyncio Usage [COMPLETED]**
- **Files:** `core/async_operations_manager.py`, grep for async/await usage
- **Action:** Document all current asyncio usage patterns
- **Identify:** Operations that could use Qt threads instead
- **Outcome:** Decision matrix (keep asyncio vs migrate)
- **Status:** Complete - See `docs/architecture/concurrency_inventory.md`

**✅ Task A2: Add Health Check APIs [COMPLETED]**
- **Files:** `core/thread_pool_manager.py`, `utils/timer_manager.py`, `utils/exiftool_wrapper.py`
- **Action:** Add `health_check()`, `is_healthy()`, `last_error()` methods
- **Status:** Complete - All concurrent components now have health monitoring

**✅ Task A3: Create Shutdown Coordinator [COMPLETED]**
- **Files:** New `core/shutdown_coordinator.py`
- **Responsibility:** Ordered cleanup sequence
- **Order:**
  1. Cancel async tasks (if keeping asyncio)
  2. Thread pool shutdown (request + wait with timeout)
  3. Timer manager cleanup
  4. ExifTool process termination
  5. Database connection close
- **Integrate:** `main.py` and `main_window.closeEvent()`
- **Status:** Complete - Centralized shutdown with progress callbacks and health checks

**✅ Task A3b: Emergency main_window.py Cleanup [COMPLETED]**
- **Files:** `main_window.py`
- **Issue:** File corruption with 676 lines of orphaned code and duplicate methods
- **Action:** Remove duplicates, restore missing methods, integrate shutdown coordinator
- **Status:** Complete - 1280 lines, 108 unique methods, 0 duplicates, all tests passing

**✅ Task A4: Concurrency Decision Document [COMPLETED]**
- **Files:** New `docs/architecture/concurrency_decision.md`
- **Action:** Document decision on asyncio usage based on A1 audit
- **Decision:** Qt-only model (remove asyncio infrastructure)
- **Rationale:** Zero production usage, Qt threads handle all requirements
- **Status:** Complete - Decision document created with full analysis

**✅ Task A5: AsyncOperationsManager Removal [COMPLETED]**
- **Files:** Removed `core/async_operations_manager.py` (618 lines)
- **Updated:** `main_window.py`, `core/shutdown_coordinator.py`
- **Action:** Remove unused asyncio infrastructure
- **Result:** 
  - Removed: async_operations_manager.py (618 lines)
  - Simplified: shutdown_coordinator.py (5 phases instead of 6)
  - Removed: ASYNC_OPERATIONS phase from shutdown sequence
  - Tests: 295/295 passing after removal
- **Status:** Complete - Clean removal with zero breakage
- **Files:** `core/async_operations_manager.py` (evaluate/simplify/remove)
- **Action:** Based on A4 decision, migrate or retire
- **Status:** Blocked by A4

**✅ Task A6: Standardize Progress Reporting [COMPLETED]**
- **Files:** New `core/progress_protocol.py`, `tests/test_progress_protocol.py`
- **Created:** Standard progress callback interface with type-safe protocols
- **Components:**
  - `ProgressCallback` protocol for item-based progress
  - `SizeProgressCallback` protocol for byte-level progress
  - `ProgressInfo` and `SizeProgress` dataclasses
  - `ProgressSignals` mixin for Qt workers
  - Helper functions for formatting and signal bridging
- **Benefits:**
  - Type-safe progress callbacks (Protocol-based)
  - Consistent progress reporting across all workers
  - Easy testing with mock callbacks
  - Clear documentation of progress contracts
- **Tests:** 24/24 passing
- **Status:** Complete - Standard progress interface implemented

**Task A7: Document Threading Patterns [PENDING]**
- **Create:** `docs/threading_patterns.md`
- **Content:**
  - When to use threads vs main thread
  - How to create workers
  - Progress reporting standard
  - Cancellation pattern
  - Cleanup requirements
- **Status:** Not started

**Expected Outcomes:**
- ✅ Simpler mental model for developers (health checks added)
- ✅ More reliable shutdown (coordinator implemented)
- ✅ Easier to add concurrent features (clear patterns documented)
- ✅ Better testability (295/295 tests passing)

**Completed Files:**
- ✅ `core/shutdown_coordinator.py` (NEW - centralized shutdown)
- ✅ `docs/architecture/concurrency_inventory.md` (NEW - complete audit)
- ✅ `core/thread_pool_manager.py` (health check APIs added)
- ✅ `utils/timer_manager.py` (health check APIs added)
- ✅ `utils/exiftool_wrapper.py` (health check APIs added)
- ✅ `main_window.py` (integrated shutdown coordinator, 1280 lines)
- ✅ `core/persistent_metadata_cache.py` (duplicates removed)

**Remaining Files:**
- ⏳ `docs/concurrency_decision.md` (Task A4 - pending)
- ⏳ `core/async_operations_manager.py` (Task A5 - evaluate after A4)
- ⏳ `docs/threading_patterns.md` (Task A7 - pending)

---

### Area B: Application Context Migration 🟡 MEDIUM PRIORITY

**Current Situation:**
- ApplicationContext exists but in "skeleton mode"
- Most state still in MainWindow (1532 lines)
- ApplicationService provides facade but requires MainWindow
- Incomplete migration to centralized state

**Goals:**
1. Complete ApplicationContext migration
2. Reduce MainWindow size and responsibilities
3. Enable easier testing of components
4. Clearer dependency graph

**Proposed Changes:**

**Step 1: Complete Store Initialization**
- **Files:** `core/application_context.py`, `core/file_store.py`, `core/selection_store.py`
- **Action:** Move remaining file/selection state from MainWindow
- **Ensure:** All state access goes through context
- **Migrate:** Current folder path, recursive flag, etc.

**Step 2: Manager Registration in Context**
- **Files:** `core/application_context.py`
- **Add:** Manager registry: `register_manager(name, instance)`
- **Benefit:** Managers accessible without MainWindow traversal
- **Pattern:**
  ```python
  context = get_app_context()
  metadata_mgr = context.get_manager('metadata')
  ```

**Step 3: Break MainWindow Monolith**
- **Extract:** Menu/toolbar setup → `core/menu_manager.py`
- **Extract:** Widget creation → `core/widget_factory.py`
- **Extract:** Layout setup → improved `ui_manager.py`
- **Result:** MainWindow becomes wiring only

**Step 4: Update ApplicationService**
- **Files:** `core/application_service.py`
- **Change:** Get managers from context instead of main_window reference
- **Remove:** Hard requirement for MainWindow
- **Enable:** Testing with mock context

**Expected Outcomes:**
- MainWindow reduced to ~500 lines
- Clear state ownership
- Easier unit testing
- Better separation of concerns

**Files to Modify:**
- `core/application_context.py` (complete migration)
- `core/file_store.py` (move remaining state)
- `core/selection_store.py` (move remaining state)
- `main_window.py` (reduce size)
- `core/application_service.py` (use context)
- New: `core/menu_manager.py`
- New: `core/widget_factory.py`

---

### Area C: Metadata System Unification 🟡 MEDIUM PRIORITY

**Current Situation:**
- Three metadata managers with overlapping responsibilities
- Multiple loader patterns (DirectMetadataLoader, MetadataLoader, worker)
- Unclear API for metadata operations
- ExifTool wrapper integration scattered

**Goals:**
1. Single clear API for metadata operations
2. Consolidate loader patterns
3. Improved caching strategy
4. Better ExifTool resilience

**Proposed Changes:**

**Step 1: Define Metadata API Contract**
- **Files:** New `core/metadata_service.py`
- **Responsibility:** Single entry point for all metadata operations
- **Methods:**
  - `load_metadata(files, mode='fast'|'extended')` → returns Future/callback
  - `get_metadata(file_path)` → from cache or load
  - `save_metadata(file_path, metadata)` → to database
  - `export_metadata(files, format)` → CSV/JSON
- **Hide:** Implementation details (workers, cache, database)

**Step 2: Consolidate Loaders**
- **Decision:** Keep worker pattern, remove DirectMetadataLoader
- **Files:** `utils/metadata_loader.py` (enhance), remove `core/direct_metadata_loader.py`
- **Standardize:** Progress reporting, cancellation, error handling
- **Worker:** Single MetadataWorker class with mode parameter

**Step 3: Improve Caching Strategy**
- **Files:** `core/persistent_metadata_cache.py`
- **Add:** Event-based invalidation (not just TTL)
- **Add:** File timestamp tracking for auto-invalidation
- **Add:** Cache size limits with LRU eviction
- **Monitor:** Cache hit rate, report in performance widget

**Step 4: ExifTool Resilience**
- **Files:** `utils/exiftool_wrapper.py`
- **Add:** Automatic process restart on failure
- **Add:** Health check before batch operations
- **Add:** Fallback strategies for corrupted files
- **Improve:** Error logging with file paths

**Step 5: Deprecate Old Managers**
- **Strategy:** Gradual migration to MetadataService
- **Phase 1:** Route all new code through MetadataService
- **Phase 2:** Migrate existing call sites
- **Phase 3:** Remove deprecated managers

**Expected Outcomes:**
- Clear single API for metadata
- Improved reliability
- Better performance monitoring
- Easier to add features (e.g., custom fields)

**Files to Modify:**
- New: `core/metadata_service.py` (unified API)
- `utils/metadata_loader.py` (enhance)
- `utils/exiftool_wrapper.py` (resilience)
- `core/persistent_metadata_cache.py` (smarter invalidation)
- Remove: `core/direct_metadata_loader.py` (after migration)
- Migrate: `core/metadata_manager.py` (to use service)
- Update: All metadata call sites

---

### Area D: Preview Engine Optimization 🟢 MEDIUM-LOW PRIORITY

**Current Situation:**
- Preview caching works but is time-based (100ms TTL)
- Module effectiveness checked after cache miss
- Sequential file processing
- Batch metadata availability check could be optimized

**Goals:**
1. Event-driven cache invalidation
2. Smarter module effectiveness pre-filtering
3. Parallel preview generation for large file sets
4. Better progress feedback

**Proposed Changes:**

**Step 1: Event-Driven Cache Invalidation**
- **Files:** `core/preview_manager.py`, `core/unified_rename_engine.py`
- **Replace:** TTL-based cache with event-based
- **Trigger:** Invalidate on:
  - Module configuration change
  - File selection change
  - File metadata update
- **Benefit:** No stale previews, more responsive

**Step 2: Module Pre-Filtering**
- **Files:** `utils/preview_engine.py`
- **Add:** Check `is_effective()` BEFORE applying modules
- **Skip:** Modules that won't contribute
- **Cache:** Module effectiveness per configuration
- **Benefit:** Fewer wasted module applications

**Step 3: Batch Preview Generation**
- **Files:** `core/unified_rename_engine.py`
- **Strategy:** Process files in batches of 100
- **Use:** ThreadPoolManager for parallel processing
- **Maintain:** Order for counter modules
- **Progress:** Update every batch completion

**Step 4: Optimize Availability Checks**
- **Files:** `core/unified_rename_engine.py` → `BatchQueryManager`
- **Current:** Single batch query for all files (good)
- **Improve:** Cache availability across preview regenerations
- **Invalidate:** Only on file changes, not preview changes
- **Benefit:** Avoid repeated database queries

**Expected Outcomes:**
- Faster preview for 1000+ files
- More responsive UI
- Better progress indication
- Lower CPU usage

**Files to Modify:**
- `core/preview_manager.py` (event-driven cache)
- `core/unified_rename_engine.py` (batch processing)
- `utils/preview_engine.py` (pre-filtering)
- `core/performance_monitor.py` (track improvements)

---

### Area E: Testing & Developer Experience 🟢 LOW-MEDIUM PRIORITY

**Current Situation:**
- Test files exist (41 files) but coverage incomplete
- Limited integration tests
- Some GUI tests skipped on CI
- Mock fixtures could be improved

**Goals:**
1. Increase test coverage to 70%+
2. Add integration tests for key workflows
3. Improve mock fixtures
4. Better developer documentation

**Proposed Changes:**

**Step 1: Test Infrastructure**
- **Files:** `tests/conftest.py`, new fixtures
- **Create:** Mock ExifTool with fake metadata responses
- **Create:** Temporary filesystem fixture with sample files
- **Create:** Mock ApplicationContext for unit tests
- **Benefit:** Faster, more reliable tests

**Step 2: Module Testing**
- **Focus:** Each rename module
- **Pattern:** Property-based testing with hypothesis
- **Test:** All module combinations
- **Verify:** Output consistency and effectiveness
- **Files:** `tests/test_modules/test_*.py` (expand)

**Step 3: Integration Tests**
- **Scenarios:**
  - Complete rename workflow (load → preview → execute)
  - Metadata loading with caching
  - Conflict resolution
  - Database persistence
- **Files:** `tests/integration/` (new directory)
- **Use:** Real file operations in temp directories

**Step 4: Performance Benchmarks**
- **Files:** `tests/benchmarks/` (new directory)
- **Measure:**
  - Preview generation speed (100, 1000, 5000 files)
  - Metadata loading speed
  - Database operations
- **Track:** Over time to detect regressions

**Step 5: Developer Documentation**
- **Create:** `docs/developer_guide.md`
- **Content:**
  - Architecture overview
  - How to add a rename module
  - How to add a manager
  - Testing patterns
  - Debugging tips
- **Update:** `docs/README.md` with better navigation

**Expected Outcomes:**
- Confidence in refactoring
- Faster debugging
- Easier onboarding
- Regression prevention

**Files to Create:**
- `tests/fixtures/mock_exiftool.py`
- `tests/fixtures/sample_files.py`
- `tests/fixtures/mock_context.py`
- `tests/integration/` (directory with workflow tests)
- `tests/benchmarks/` (directory with performance tests)
- `docs/developer_guide.md`
- `docs/testing_guide.md`
- `docs/performance_optimization.md`

**Files to Enhance:**
- `tests/conftest.py` (better fixtures)
- `tests/test_*_module.py` (property-based tests)
- Existing integration tests (expand scenarios)

---

### Area F: UI/UX Polish 🟢 LOW PRIORITY

**Current Situation:**
- FileTableView is 2689 lines
- MetadataTreeView is 3271 lines
- Drag & drop system spread across multiple files
- Some UI state management still in widgets

**Goals:**
1. Simplify large widget files
2. Consolidate drag & drop logic
3. Improve accessibility
4. Better keyboard navigation

**Proposed Changes:**

**Step 1: Extract View Helpers**
- **Files:** `widgets/file_table_view.py`
- **Extract:** Column management → `widgets/table_column_manager.py`
- **Extract:** Selection logic → use SelectionManager more
- **Extract:** Drag logic → consolidate with drag managers
- **Result:** FileTableView ~1000 lines

**Step 2: Consolidate Drag System**
- **Files:** `core/drag_manager.py`, `core/drag_visual_manager.py`, `core/drag_cleanup_manager.py`
- **Merge:** Into single `core/drag_drop_coordinator.py`
- **Simplify:** State machine for drag operations
- **Clear:** Responsibility boundaries
- **Benefit:** Easier to maintain and debug

**Step 3: Accessibility Improvements**
- **Add:** ARIA-like roles for screen readers
- **Improve:** Tab order consistency
- **Add:** Keyboard shortcuts help dialog
- **Ensure:** All operations keyboard-accessible

**Step 4: State Management Cleanup**
- **Move:** Widget state to ApplicationContext
- **Examples:**
  - Splitter positions
  - Column widths
  - Window geometry
- **Already:** WindowConfigManager, SplitterManager exist
- **Ensure:** Consistent persistence

**Expected Outcomes:**
- More maintainable widget code
- Better user experience
- Improved accessibility
- Clearer code organization

**Files to Modify:**
- `widgets/file_table_view.py` (reduce size)
- `widgets/metadata_tree_view.py` (reduce size)
- `core/drag_manager.py`, `core/drag_visual_manager.py`, `core/drag_cleanup_manager.py` → merge
- New: `widgets/table_column_manager.py`
- New: `core/drag_drop_coordinator.py`
- Enhance: Keyboard shortcut system

---

## 6. Implementation Strategy

### 6.1 Phased Approach

**Phase 1: Foundation (Weeks 1-2)**
- Area A: Concurrency audit and shutdown coordinator
- Area E: Test infrastructure setup
- Document current state

**Phase 2: Core Improvements (Weeks 3-5)**
- Area B: ApplicationContext migration
- Area C: Metadata system unification
- Expand test coverage

**Phase 3: Optimization (Weeks 6-7)**
- Area D: Preview engine optimization
- Performance benchmarking
- Measure improvements

**Phase 4: Polish (Weeks 8-9)**
- Area F: UI/UX improvements
- Documentation updates
- Final testing

### 6.2 Risk Mitigation

**For Each Change:**
1. Write tests BEFORE refactoring
2. Make incremental changes
3. Run full test suite after each step
4. Test on Windows and Linux
5. Performance benchmark comparison

**Rollback Strategy:**
- Git branch for each area
- Ability to merge areas independently
- Feature flags for new implementations
- Maintain backward compatibility during migration

### 6.3 Success Metrics

**Quantitative:**
- Test coverage: Current → 70%+
- MainWindow LOC: 1532 → ~500
- Preview speed for 1000 files: Baseline → 30% faster
- Shutdown time: Baseline → <2 seconds

**Qualitative:**
- Simpler mental model (developer survey)
- Easier to add features (measure PR complexity)
- More reliable (track crash reports)
- Better documentation (completeness checklist)

---

## 7. Quick Wins (Can Start Immediately)

These changes are low-risk and high-value:

1. **Add Shutdown Coordinator** (1-2 days)
   - Immediate: More reliable shutdown
   - File: New `core/shutdown_coordinator.py`

2. **Consolidate Drag Managers** (2-3 days)
   - Immediate: Clearer code
   - Files: Merge 3 managers into 1

3. **Event-Driven Preview Cache** (2 days)
   - Immediate: More responsive UI
   - Files: `core/preview_manager.py`

4. **ExifTool Health Check** (1 day)
   - Immediate: Fewer metadata errors
   - Files: `utils/exiftool_wrapper.py`

5. **Module Pre-Filtering** (1 day)
   - Immediate: Faster previews
   - Files: `utils/preview_engine.py`

6. **Developer Guide** (2 days)
   - Immediate: Better onboarding
   - Files: New `docs/developer_guide.md`

Total: ~2 weeks for significant improvements

---

## Conclusion

The oncutf codebase is well-structured with clear separation of concerns, but has grown organically and would benefit from consolidation in several areas:

**Strengths:**
- Clear manager pattern separating UI from logic
- Good caching strategies
- Comprehensive feature set
- Decent documentation

**Primary Opportunities:**
- Simplify concurrency model (dual system → single)
- Complete ApplicationContext migration
- Unify metadata system API
- Increase test coverage

**Recommended Starting Point:**
- **Area A** (Concurrency) - Highest impact on stability
- Or **Quick Wins** above for immediate improvements

This plan provides concrete, actionable steps with clear file references and expected outcomes. Each area can be tackled independently with measurable progress.
