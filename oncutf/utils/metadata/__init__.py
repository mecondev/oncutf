"""Metadata utilities package.

Helpers for metadata operations, validation, caching, and export.
Lightweight adapters - core logic moved to core.metadata.
"""

# Re-exports from core.metadata for backward compatibility
from oncutf.core.metadata.field_validators import MetadataFieldValidator
from oncutf.utils.metadata.cache_helper import MetadataCacheHelper

__all__ = [
    "MetadataCacheHelper",
    "MetadataFieldValidator",
]
