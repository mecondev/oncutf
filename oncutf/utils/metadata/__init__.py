"""Metadata utilities package.

Helpers for metadata operations, validation, caching, and export.
Lightweight adapters - core logic moved to core.metadata.
"""

# Re-exports from core.metadata for backward compatibility
from oncutf.domain.validation import MetadataFieldValidator

__all__ = [
    "MetadataFieldValidator",
]
