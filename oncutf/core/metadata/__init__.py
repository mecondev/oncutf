"""Metadata management package.

Author: Michael Economou
Date: 2025-12-21
Updated: 2025-12-28

This package contains all metadata-related functionality:
- MetadataCacheService: Cache operations for metadata and hashes
- CompanionMetadataHandler: Companion file (XMP, sidecar) metadata handling
- MetadataWriter: Metadata writing via ExifTool
- MetadataShortcutHandler: Keyboard shortcut handling for metadata operations
- MetadataProgressHandler: Progress dialog management for metadata/hash operations
- MetadataLoader: Orchestration of metadata loading operations (single/batch/streaming)
- MetadataCommandManager: Undo/redo command management for metadata operations
- MetadataOperationsManager: Export, field editing, compatibility checks
- MetadataStagingManager: Staged changes management (pending modifications)
- UnifiedMetadataManager: Facade for all metadata operations
"""

from oncutf.core.metadata.command_manager import (
    MetadataCommandManager,
    get_metadata_command_manager,
)
from oncutf.core.metadata.companion_metadata_handler import CompanionMetadataHandler
from oncutf.core.metadata.metadata_cache_service import MetadataCacheService
from oncutf.core.metadata.metadata_loader import MetadataLoader
from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler
from oncutf.core.metadata.metadata_shortcut_handler import MetadataShortcutHandler
from oncutf.core.metadata.metadata_writer import MetadataWriter
from oncutf.core.metadata.operations_manager import MetadataOperationsManager
from oncutf.core.metadata.staging_manager import (
    MetadataStagingManager,
    get_metadata_staging_manager,
)
from oncutf.core.metadata.unified_manager import (
    UnifiedMetadataManager,
    get_unified_metadata_manager,
)

__all__ = [
    # Cache and handlers
    "MetadataCacheService",
    "CompanionMetadataHandler",
    "MetadataWriter",
    "MetadataShortcutHandler",
    "MetadataProgressHandler",
    "MetadataLoader",
    # Managers (moved from core/ root)
    "MetadataCommandManager",
    "get_metadata_command_manager",
    "MetadataOperationsManager",
    "MetadataStagingManager",
    "get_metadata_staging_manager",
    "UnifiedMetadataManager",
    "get_unified_metadata_manager",
]
