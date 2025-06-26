# Changelog

All notable changes to this project will be documented in this file.

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
