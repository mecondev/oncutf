"""
Services layer for oncutf application.

Author: Michael Economou
Date: December 18, 2025

This package provides service abstractions and implementations for external
dependencies (filesystem, exiftool, hashing, database). Services follow the
Protocol pattern for dependency injection and testability.

The services layer sits between the domain layer and external systems:
- Domain layer depends on service protocols (interfaces)
- Concrete implementations handle actual I/O
- This enables testing domain logic without real filesystem/network access

Usage:
    from oncutf.services import MetadataServiceProtocol, HashServiceProtocol
    from oncutf.services import ServiceRegistry

Modules:
    interfaces: Protocol definitions for all services
    registry: Service locator for dependency injection
    exiftool_service: ExifTool-based metadata extraction
    hash_service: File hashing implementations
    filesystem_service: Filesystem operations abstraction
"""

from __future__ import annotations

__all__: list[str] = []
