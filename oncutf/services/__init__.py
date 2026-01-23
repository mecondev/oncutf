"""Services layer for oncutf application.

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
    from oncutf.services import ServiceRegistry, get_service_registry
    from oncutf.services import ExifToolService, FilesystemService

Modules:
    interfaces: Protocol definitions for all services
    registry: Service locator for dependency injection
    exiftool_service: ExifTool-based metadata extraction
    cached_hash_service: Cached-only hash service for rename operations
    filesystem_service: Filesystem operations abstraction
"""

from __future__ import annotations

# Import concrete implementations
from oncutf.services.exiftool_service import ExifToolService
from oncutf.services.filesystem_service import FilesystemService

# Import protocols for convenient access
from oncutf.services.interfaces import (
    FilesystemServiceProtocol,
    HashServiceProtocol,
    MetadataServiceProtocol,
)

# Import registry utilities
from oncutf.services.registry import (
    ServiceRegistry,
    configure_default_services,
    get_service_registry,
)

__all__ = [
    # Implementations
    "ExifToolService",
    "FilesystemService",
    "FilesystemServiceProtocol",
    "HashServiceProtocol",
    # Protocols
    "MetadataServiceProtocol",
    # Registry
    "ServiceRegistry",
    "configure_default_services",
    "get_service_registry",
]
