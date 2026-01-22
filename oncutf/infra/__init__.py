"""Infrastructure layer - implementation of ports.

This layer contains:
- External tool clients (ExifTool, FFmpeg)
- Cache implementations
- Database repositories
- Filesystem adapters

Allowed imports:
- domain/ modules
- app/ports/ (to implement interfaces)
- External libraries (subprocess, sqlite3, etc.)

Forbidden imports:
- ui/ modules
- Direct Qt imports (unless needed for external tool integration)

Author: Michael Economou
Date: 2026-01-22
"""
