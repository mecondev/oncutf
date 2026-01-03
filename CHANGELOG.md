# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Deprecated
- **Legacy Methods** (marked for removal in v2.0):
  - `ApplicationContext.set_files()` - Use `FileStore.set_loaded_files()` instead
  - `TextRemovalModule.on_text_changed()` - Connect to `module_changed` signal instead
  - `TextRemovalModule.on_position_changed()` - Connect to `module_changed` signal instead  
  - `TextRemovalModule.on_case_changed()` - Connect to `module_changed` signal instead
  - `ProgressWidget._format_time()` - Use `_format_time_hms()` instead
  - `ColorColumnDelegate._set_file_color()` - Use `_set_files_color()` with single-element list
- **Delegator Modules** (will be removed in v2.0):
  - `oncutf.ui.widgets.file_table_view` - Import from `oncutf.ui.widgets.file_table` instead
  - `oncutf.ui.widgets.file_tree_view` - Import from `oncutf.ui.widgets.file_tree` instead
  - `oncutf.ui.behaviors.selection_behavior` - Import from `oncutf.ui.behaviors.selection` instead
  - `oncutf.ui.behaviors.column_management_behavior` - Import from `oncutf.ui.behaviors.column_management` instead
  - `oncutf.ui.behaviors.metadata_edit_behavior` - Import from `oncutf.ui.behaviors.metadata_edit` instead
  - `oncutf.ui.behaviors.metadata_context_menu_behavior` - Import from `oncutf.ui.behaviors.metadata_context_menu` instead

### Code Quality
- **Audit-driven improvements** (2026-01-03):
  - Standardized all logging to `get_cached_logger(__name__)` pattern
  - Added `@deprecated` decorator to legacy methods with migration guidance
  - Converted critical error handlers to `logger.exception()` for stack traces
  - Added `ExifMetadata` TypedDict for better IDE autocomplete
  - Added `OperationType` Literal type for type-safe operation handling
  - Extracted `WorkerProtocol` and `CancellableMixin` for worker consistency
  - Removed duplicate `OperationDialog` class (use `ProgressDialog` instead)
  - Added deprecation warnings to delegator files
  - Removed dead `_legacy_selection_mode` flag (SelectionStore is always enabled)

### Performance
- **Phase 7 - Final Polish**: Major performance optimizations and polish
  - **Startup Optimization**: 31% faster application startup (1426ms → 989ms)
    - Lazy-loaded ExifToolWrapper in UnifiedMetadataManager (12% improvement)
    - Lazy-loaded CompanionFilesHelper in UnifiedMetadataManager (21% improvement)
    - Exceeded target of <1000ms startup time
  - **Memory Optimization**: Bounded memory caches to prevent unbounded growth
    - Added LRU eviction to PersistentHashCache (1000 entry limit)
    - Added LRU eviction to PersistentMetadataCache (500 entry limit)
    - OrderedDict-based LRU implementation with move_to_end() pattern
  - **Performance Profiling**: Created comprehensive profiling infrastructure
    - Added scripts/profile_startup.py for startup time analysis
    - Added scripts/profile_memory.py for memory usage tracking
    - Created docs/PERFORMANCE_BASELINE.md for tracking improvements

### Added
- **Phase 1D - MainWindowController**: High-level orchestration controller
  - New MainWindowController coordinating FileLoad, Metadata, and Rename controllers
  - `restore_last_session_workflow()`: Orchestrates session restoration (folder validation, file loading, optional metadata, sort config)
  - `coordinate_shutdown_workflow()`: Orchestrates graceful shutdown with progress callbacks
  - 17 comprehensive tests for all orchestration workflows
  - Integration with WindowConfigManager for session restore
  - Testable orchestration layer separating UI from business logic

### Changed
- **Phase 1D - Architecture Improvements**:
  - Session restoration now uses MainWindowController instead of direct manager calls
  - Shutdown orchestration extracted from MainWindow to MainWindowController
  - Improved code organization following MVC-inspired controller pattern
  - Enhanced testability of complex multi-service workflows

### Refactoring
- **Mixin Extraction from FileTableView** (Day 8 - 2025-12-04):
  - Extracted SelectionMixin (486 lines, 12 methods) for Windows Explorer-style selection
  - Extracted DragDropMixin (365 lines, 9 methods) for drag-and-drop functionality
  - Reduced FileTableView from 2716 to 2066 lines (-24% complexity)
  - Improved code reusability and maintainability
  - All 460 tests passing (100% compatibility)
  - Created `widgets/mixins/` package for reusable widget behaviors
  - Comprehensive documentation with usage examples

### Documentation
- **Cache Strategy Documentation** (Day 7 - 2025-12-04):
  - Comprehensive cache system documentation (2500+ lines)
  - Complete guide for AdvancedCacheManager, PersistentHashCache, PersistentMetadataCache
  - 30+ working code examples with usage patterns
  - Performance benchmarks showing 500x speedup for metadata loading
  - Troubleshooting guide for 5 common problems
  - 8 best practices for optimal cache usage
  - Quick reference card for daily use
  - Complete documentation index with navigation
  - Visual diagrams and architecture charts

### Added
- **Companion Files System**: Comprehensive support for camera-generated companion/sidecar files
  - Automatic detection of Sony camera XML metadata files (e.g., C8227.MP4 + C8227M01.XML)
  - Support for XMP sidecar files for RAW images (e.g., IMG_1234.CR2 + IMG_1234.xmp)
  - Subtitle file support for videos (SRT, VTT, ASS formats)
  - Configurable display options (hide, show, or group companion files)
  - Automatic companion file renaming when main files are renamed
  - Enhanced metadata display with companion file data integration
  - CompanionFilesWidget for user-friendly settings management
  - Metadata extraction from Sony XML files (duration, codec, resolution, etc.)
  - File loading optimization to filter companion files based on preferences
  - Professional workflow support for video production and photography
  - **Metadata Integration**: Automatic companion metadata enhancement during metadata loading
    - Sony XML metadata automatically merged into MP4 file metadata
    - Device info, video specs, and audio info extracted from companion files
    - Enhanced metadata displayed in unified metadata view
    - Seamless integration with existing metadata loading workflows

### Fixed
- **CRITICAL (Windows)**: Fixed application crash on exit with "Debug/Close Program" dialog
  - Added timeout parameter to `thread.wait()` after `terminate()` to prevent infinite hang
  - Fixed double cleanup race condition with ExifTool processes
  - Added global `_cleanup_done` flag to prevent duplicate cleanup from `atexit`
  - Improved thread termination logging with proper error reporting
  - Windows-specific issue where Qt threads didn't terminate gracefully

## [1.3] - 2025-06-29

### Added
- **Backup System**: Automatic database backups for data protection
  - Automatic backups on application shutdown
  - Periodic backup system (every 15 minutes, configurable)
  - BackupManager with rotation and cleanup functionality
  - Configurable backup count and interval settings
  - Backup files with timestamp naming: `oncutf_YYYYMMDD_HHMMSS.db.bak`

### Fixed
- **CRITICAL**: Fixed tooltip system crash when renaming files (RuntimeError: deleted Qt objects)
- **CRITICAL**: Fixed post-rename workflow crash that prevented UI updates after successful file renaming
  - Implemented Safe Rename Workflow with TimerManager for delayed execution
  - Added comprehensive error handling and state validation
  - Restored proper UI state after rename operations (checked files, metadata, preview, icons)
  - Enhanced rename workflow with graceful degradation and fallback mechanisms
- Fixed memory leaks in persistent tooltip management
- Enhanced error recovery for Qt object deletion scenarios
- Improved application stability during file operations

### Changed
- **Tooltip System Overhaul**: Complete rewrite of tooltip management
  - Added comprehensive error handling for Qt object lifecycle
  - Enhanced tooltip persistence with proper cleanup mechanisms
  - Improved tooltip positioning and screen boundary detection
  - Added robust protection against deleted widget references
  - Optimized tooltip event handling and reduced memory footprint

### Technical
- Enhanced error logging and debugging capabilities
- Improved application shutdown sequence with backup integration
- Added comprehensive test suite for backup functionality (simplified architecture)
- All 185 tests passing successfully
- Better Qt object lifecycle management throughout the application

## [1.3.0] - 2025-07-27 (Database System Release)

### Added
- **Database System**: Comprehensive SQLite-based database system for persistent storage
  - Persistent metadata cache with automatic database storage
  - Persistent hash cache for CRC32 checksums
  - Rename history tracking for undo/redo functionality
  - Thread-safe operations with connection pooling
  - Automatic schema migrations and maintenance

- **Rename History & Undo Functionality**
  - Complete rename history tracking with batch operation support
  - Undo functionality for rename operations with validation
  - Rename History Dialog for viewing and managing operations
  - Operation integrity checking and rollback capabilities

- **Enhanced Performance**
  - Memory cache layer for frequently accessed data
  - Lazy loading with database fallback
  - Optimized database indexes and query performance
  - Connection pooling for better concurrency

- **Data Persistence**
  - Metadata and hashes survive application restarts
  - Automatic cleanup of orphaned records
  - Database statistics and maintenance tools
  - Cross-platform data directory management

- **Backward Compatibility**
  - Drop-in replacement for existing cache systems
  - Maintains all original API signatures
  - Graceful fallback to memory-only operation
  - Seamless migration from old cache system

### Changed
- Replaced memory-only MetadataCache with PersistentMetadataCache
- Enhanced HashManager with persistent caching capabilities
- Improved error handling and recovery mechanisms
- Better thread safety across all database operations

### Technical Details
- Database location: `~/.local/share/oncutf/` (Linux/macOS) or `%APPDATA%/oncutf/` (Windows)
- SQLite backend with WAL mode for better concurrency
- Foreign key constraints for referential integrity
- Comprehensive test suite for all database functionality
- Full documentation in `docs/database_system.md`

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.2] - 2025-05-27

### Added
- Smart default window geometry based on screen size and aspect ratio
- Metadata groups now display in logical order (File Info first, then alphabetical)
- Splash screen positioning relative to main window location
- Individual file export system (creates separate files per source)

### Changed
- **BREAKING**: Removed CSV export format from metadata export dialog
- **BREAKING**: Metadata export now creates individual files instead of combined files
- Markdown export format cleaned up (removed all bold formatting and colors)
- Export system now uses dynamic configuration values from config.py
- Version format changed from "1.1" to "v1.1" for consistency

### Fixed
- **CRITICAL**: Fixed save metadata bug where the third modified file wouldn't be saved
- Fixed Qt imports consolidation for better maintainability
- Fixed splash screen positioning when no config.json exists

### Technical
- Consolidated Qt imports through central qt_imports.py
- Improved error handling in window geometry calculations
- Enhanced metadata tree view modification tracking
- Better progress tracking for metadata operations

## [v1.1] - Previous Release

### Features
- Metadata export system (JSON, Markdown, CSV)
- Bulk file operations
- Advanced metadata editing
- Hash calculation and duplicate detection
- Cross-platform compatibility
