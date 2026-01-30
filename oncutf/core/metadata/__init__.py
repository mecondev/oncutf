"""Metadata management package.

Author: Michael Economou
Date: 2025-12-21
Updated: 2026-01-03

This package contains all metadata-related functionality:
- MetadataCacheService: Cache operations for metadata and hashes
- CompanionMetadataHandler: Companion file (XMP, sidecar) metadata handling
- MetadataWriter: Metadata writing via ExifTool
- MetadataShortcutHandler: Keyboard shortcut handling for metadata operations
- MetadataProgressHandler: Progress dialog management for metadata/hash operations
- MetadataLoader: Orchestration of metadata loading operations (single/batch/streaming)
- MetadataCommandManager: Undo/redo command management for metadata operations
- MetadataStagingManager: Staged changes management (pending modifications)
- FieldCompatibilityChecker: Field compatibility checking for file types
- Commands: Command pattern implementations (MetadataCommand, EditMetadataFieldCommand, etc.)

NOTE: HashLoadingService, MetadataOperationsManager, UnifiedMetadataManager moved to ui/managers/.
"""

from oncutf.core.metadata.command_manager import (
    MetadataCommandManager,
    get_metadata_command_manager,
)

# Command pattern classes
from oncutf.core.metadata.commands import (
    BatchMetadataCommand,
    EditMetadataFieldCommand,
    MetadataCommand,
    ResetMetadataFieldCommand,
    SaveMetadataCommand,
)
from oncutf.core.metadata.companion_metadata_handler import CompanionMetadataHandler
from oncutf.core.metadata.field_compatibility import (
    FieldCompatibilityChecker,
    get_field_compatibility_checker,
)
from oncutf.core.metadata.metadata_cache_service import MetadataCacheService
from oncutf.core.metadata.metadata_loader import MetadataLoader
from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler
from oncutf.core.metadata.metadata_shortcut_handler import MetadataShortcutHandler
from oncutf.core.metadata.metadata_writer import MetadataWriter
from oncutf.core.metadata.staging_manager import (
    MetadataStagingManager,
    get_metadata_staging_manager,
    set_metadata_staging_manager,
)
from oncutf.core.metadata.unified_metadata_protocol import (
    UnifiedMetadataManagerProtocol,
)

__all__ = [
    "BatchMetadataCommand",
    "CompanionMetadataHandler",
    "EditMetadataFieldCommand",
    "FieldCompatibilityChecker",
    "MetadataCacheService",
    "MetadataCommand",
    "MetadataCommandManager",
    "MetadataLoader",
    "MetadataProgressHandler",
    "MetadataShortcutHandler",
    "MetadataStagingManager",
    "MetadataWriter",
    "ResetMetadataFieldCommand",
    "SaveMetadataCommand",
    "UnifiedMetadataManagerProtocol",
    "get_field_compatibility_checker",
    "get_metadata_command_manager",
    "get_metadata_staging_manager",
    "set_metadata_staging_manager",
]
