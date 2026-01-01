"""Rename modules for oncutf application.

This package contains pure, composable name fragment generators:
- Each module produces a string fragment for the new filename
- Modules are stateless and have no filesystem dependencies
- Used by UnifiedRenameEngine for preview and execution

Module Types:
- counter_module: Sequential numbering
- datetime_module: Date/time from EXIF or filesystem
- metadata_module: Camera, lens, dimensions from EXIF
- text_module: Custom text, original name manipulation
- filesize_module: Human-readable file sizes
"""
