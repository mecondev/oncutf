"""Module: metadata_module.py

Author: Michael Economou
Date: 2025-05-06

This module provides logic for extracting metadata fields (such as creation date,
modification date, or EXIF tag) to include in renamed filenames.

Refactored in Dec 2025 to delegate extraction logic to MetadataExtractor domain layer.
"""

import os
from pathlib import Path
from typing import Any

from oncutf.models.file_item import FileItem

# initialize logger
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataModule:
    """Logic component (non-UI) for extracting and formatting metadata fields.
    Uses MetadataExtractor for actual extraction logic.
    """

    # Phase 3.1: Module metadata for auto-discovery
    DISPLAY_NAME = "Metadata"
    UI_ROWS = 2
    DESCRIPTION = "Extract file metadata (dates, hash, EXIF)"
    CATEGORY = "Metadata"

    @staticmethod
    def clean_metadata_value(value: str) -> str:
        """Clean metadata value for filename safety by replacing problematic characters.

        DEPRECATED: Use MetadataExtractor.clean_for_filename() instead.
        Kept for backwards compatibility.

        Args:
            value (str): The raw metadata value

        Returns:
            str: Cleaned value safe for use in filenames

        """
        from oncutf.domain.metadata.extractor import MetadataExtractor

        extractor = MetadataExtractor()
        return extractor.clean_for_filename(value)

    @staticmethod
    def apply_from_data(
        data: dict[str, Any],
        file_item: FileItem,
        _index: int = 0,
        metadata_cache: dict[str, Any] | None = None,
    ) -> str:
        """Apply metadata extraction using MetadataExtractor domain logic.

        This method delegates to MetadataExtractor for actual extraction,
        maintaining backwards compatibility with existing code.

        Args:
            data: Configuration dict with 'field' and 'category'
            file_item: File to extract metadata from
            _index: File index (unused in metadata extraction)
            metadata_cache: Optional metadata cache

        Returns:
            Extracted metadata value or fallback

        """
        logger.debug(
            "[DEBUG] [MetadataModule] apply_from_data CALLED for %s",
            file_item.filename,
            extra={"dev_only": True},
        )
        logger.debug("[DEBUG] [MetadataModule] data: %s", data, extra={"dev_only": True})
        logger.debug(
            "[DEBUG] [MetadataModule] metadata_cache provided: %s",
            metadata_cache is not None,
            extra={"dev_only": True},
        )

        # Extract field and category from data
        field = data.get("field")
        category = data.get("category", "file_dates")

        if not field:
            logger.debug(
                "[DEBUG] [MetadataModule] No field specified - returning 'invalid'",
                extra={"dev_only": True},
            )
            return "invalid"

        # Get file path
        from oncutf.utils.filesystem.path_normalizer import normalize_path

        path = file_item.full_path
        if not path:
            logger.debug(
                "[DEBUG] [MetadataModule] No path - returning 'invalid'",
                extra={"dev_only": True},
            )
            return "invalid"

        # Normalize path for Windows compatibility
        path = normalize_path(path)
        logger.debug("[DEBUG] [MetadataModule] Normalized path: %s", path, extra={"dev_only": True})

        # Get metadata dict
        metadata_dict = MetadataModule._get_metadata_dict(path, metadata_cache)

        # Use MetadataExtractor with cached-only hash service for rename preview
        # This ensures no expensive hash computation happens during preview
        from oncutf.domain.metadata.extractor import MetadataExtractor
        from oncutf.services.cached_hash_service import CachedHashService

        extractor = MetadataExtractor(hash_service=CachedHashService())
        result = extractor.extract(
            file_path=Path(path), field=field, category=category, metadata=metadata_dict
        )

        logger.debug(
            "[DEBUG] [MetadataModule] Extraction result: value=%s, source=%s",
            result.value,
            result.source,
            extra={"dev_only": True},
        )

        return result.value

    @staticmethod
    def _get_metadata_dict(
        path: str, metadata_cache: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Get metadata dict from cache or persistent cache.

        Args:
            path: Normalized file path
            metadata_cache: Optional metadata cache

        Returns:
            Metadata dict (empty if not found)

        """
        if not metadata_cache:
            # Use persistent metadata cache
            from oncutf.core.cache.persistent_metadata_cache import get_persistent_metadata_cache

            persistent_cache = get_persistent_metadata_cache()
            if persistent_cache:
                try:
                    if hasattr(persistent_cache, "get_entry"):
                        entry = persistent_cache.get_entry(path)
                        metadata = getattr(entry, "data", {}) or {}
                    else:
                        metadata = persistent_cache.get(path) or {}
                except Exception as e:
                    logger.debug(
                        "[DEBUG] [MetadataModule] persistent cache lookup failed: %s",
                        e,
                        extra={"dev_only": True},
                    )
                    metadata = {}
            else:
                metadata = {}
            logger.debug(
                "[DEBUG] [MetadataModule] Using persistent cache, has_metadata: %s",
                bool(metadata),
                extra={"dev_only": True},
            )
        else:
            # Use provided cache - single linear initialization
            metadata = {}  # Already defined above, no type annotation needed
            if metadata_cache is not None and isinstance(path, str) and path:
                try:
                    metadata = metadata_cache.get(path) or {}
                except Exception as e:
                    logger.debug(
                        "[DEBUG] [MetadataModule] Provided cache lookup failed: %s",
                        e,
                        extra={"dev_only": True},
                    )
            logger.debug(
                "[DEBUG] [MetadataModule] Using provided cache, has_metadata: %s",
                bool(metadata),
                extra={"dev_only": True},
            )

        if not isinstance(metadata, dict):
            metadata = {}
            logger.debug(
                "[DEBUG] [MetadataModule] Metadata is not dict, using empty dict",
                extra={"dev_only": True},
            )

        return metadata

    @staticmethod
    def clear_cache() -> None:
        """Clear the metadata cache.

        NOTE: Caching is now handled by MetadataExtractor internally.
        This method is kept for backwards compatibility.
        """
        from oncutf.domain.metadata.extractor import MetadataExtractor

        extractor = MetadataExtractor()
        extractor.clear_cache()
        logger.debug("[MetadataModule] Cache cleared")

    @staticmethod
    def _get_file_hash(file_path: str, hash_type: str) -> str:
        """Get file hash using the hash cache.

        DEPRECATED: Hash extraction is now handled by MetadataExtractor.
        Kept for backwards compatibility.

        Args:
            file_path: Path to the file
            hash_type: Type of hash (CRC32 only)

        Returns:
            str: Hash value or original name if not available

        """
        from oncutf.utils.filesystem.file_status_helpers import get_hash_for_file

        try:
            hash_value = get_hash_for_file(file_path, hash_type)
            if hash_value:
                return hash_value
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            return base_name
        except Exception as e:
            logger.warning("[MetadataModule] Error getting hash for %s: %s", file_path, e)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            return base_name

    @staticmethod
    def is_effective_data(data: dict[str, Any]) -> bool:
        """Returns True if any transformation is active."""
        field = data.get("field")
        category = data.get("category", "file_dates")

        # For hash category, check if field is a valid hash type
        if category == "hash":
            return bool(field and field.startswith("hash_"))

        # For other categories, any field is effective
        return bool(field)
