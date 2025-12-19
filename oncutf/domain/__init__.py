"""
Domain layer for oncutf application.

Author: Michael Economou
Date: December 17, 2025

Pure Python business logic with no UI dependencies.

Exports:
    MetadataExtractor: Pure Python metadata extraction with DI support.
    ExtractionResult: Dataclass holding extraction results.
"""

from oncutf.domain.metadata.extractor import ExtractionResult, MetadataExtractor

__all__: list[str] = [
    "MetadataExtractor",
    "ExtractionResult",
]
