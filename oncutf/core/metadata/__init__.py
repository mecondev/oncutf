"""Metadata management package.

Extracted from unified_metadata_manager.py for better separation of concerns.

This package contains:
- MetadataCacheService: Cache operations for metadata and hashes
- CompanionMetadataHandler: Companion file (XMP, sidecar) metadata handling
- MetadataWriter: Metadata writing via ExifTool
- MetadataShortcutHandler: Keyboard shortcut handling for metadata operations
- MetadataProgressHandler: Progress dialog management for metadata/hash operations
- MetadataLoader: Orchestration of metadata loading operations (single/batch/streaming)
"""

from oncutf.core.metadata.companion_metadata_handler import CompanionMetadataHandler
from oncutf.core.metadata.metadata_cache_service import MetadataCacheService
from oncutf.core.metadata.metadata_loader import MetadataLoader
from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler
from oncutf.core.metadata.metadata_shortcut_handler import MetadataShortcutHandler
from oncutf.core.metadata.metadata_writer import MetadataWriter

__all__ = [
    "MetadataCacheService",
    "CompanionMetadataHandler",
    "MetadataWriter",
    "MetadataShortcutHandler",
    "MetadataProgressHandler",
    "MetadataLoader",
]
