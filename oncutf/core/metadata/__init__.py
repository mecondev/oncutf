"""
Metadata management package.

Extracted from unified_metadata_manager.py for better separation of concerns.
"""

from oncutf.core.metadata.companion_metadata_handler import CompanionMetadataHandler
from oncutf.core.metadata.metadata_cache_service import MetadataCacheService
from oncutf.core.metadata.metadata_reader import MetadataReader
from oncutf.core.metadata.metadata_writer import MetadataWriter

__all__ = [
    "MetadataCacheService",
    "CompanionMetadataHandler",
    "MetadataReader",
    "MetadataWriter",
]
