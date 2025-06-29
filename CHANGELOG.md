# Changelog

All notable changes to this project will be documented in this file.

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

## [1.3.0] - 2025-01-27 (Database System Release)

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

## [v1.2] - 2025-01-27

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
