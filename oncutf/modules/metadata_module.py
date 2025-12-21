"""
Module: metadata_module.py

Author: Michael Economou
Date: 2025-05-06

This module provides logic for extracting metadata fields (such as creation date,
modification date, or EXIF tag) to include in renamed filenames.

Refactored in Phase 3 (Dec 2025) to delegate extraction logic to MetadataExtractor domain layer.
"""

import os
from pathlib import Path

from oncutf.models.file_item import FileItem

# initialize logger
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataModule:
    """
    Logic component (non-UI) for extracting and formatting metadata fields.
    Uses MetadataExtractor for actual extraction logic.
    """

    @staticmethod
    def clean_metadata_value(value: str) -> str:
        """
        Clean metadata value for filename safety by replacing problematic characters.

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
        data: dict, file_item: FileItem, _index: int = 0, metadata_cache: dict | None = None
    ) -> str:
        """
        Apply metadata extraction using MetadataExtractor domain logic.

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
        from oncutf.utils.path_normalizer import normalize_path

        path = file_item.full_path
        if not path:
            logger.debug(
                "[DEBUG] [MetadataModule] No path - returning 'invalid'",
                extra={"dev_only": True},
            )
            return "invalid"

        # Normalize path for Windows compatibility
        path = normalize_path(path)
        logger.debug(
            "[DEBUG] [MetadataModule] Normalized path: %s", path, extra={"dev_only": True}
        )

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
    def _get_metadata_dict(path: str, metadata_cache: dict | None = None) -> dict:
        """
        Get metadata dict from cache or persistent cache.

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
                        try:
                            metadata = persistent_cache.get(path)  # type: ignore
                            if metadata is None:
                                metadata = {}
                        except TypeError:
                            metadata = {}
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
            # Use provided cache
            try:
                if hasattr(metadata_cache, "get_entry"):
                    entry = metadata_cache.get_entry(path)
                    metadata = getattr(entry, "data", {}) or {}
                elif isinstance(metadata_cache, dict):
                    metadata = metadata_cache.get(path, {})
                elif hasattr(metadata_cache, "get"):
                    try:
                        metadata = metadata_cache.get(path)  # type: ignore
                        if metadata is None:
                            metadata = {}
                    except TypeError:
                        metadata = {}
                else:
                    metadata = {}
            except Exception as e:
                logger.debug(
                    "[DEBUG] [MetadataModule] Provided cache lookup failed: %s",
                    e,
                    extra={"dev_only": True},
                )
                metadata = {}
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
        """
        Clear the metadata cache.

        NOTE: Caching is now handled by MetadataExtractor internally.
        This method is kept for backwards compatibility.
        """
        from oncutf.domain.metadata.extractor import MetadataExtractor

        extractor = MetadataExtractor()
        extractor.clear_cache()
        logger.debug("[MetadataModule] Cache cleared")

    @staticmethod
    def _get_file_hash(file_path: str, hash_type: str) -> str:
        """
        Get file hash using the hash cache.

        DEPRECATED: Hash extraction is now handled by MetadataExtractor.
        Kept for backwards compatibility.

        Args:
            file_path: Path to the file
            hash_type: Type of hash (CRC32 only)

        Returns:
            str: Hash value or original name if not available
        """
        from oncutf.utils.file_status_helpers import get_hash_for_file

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
    def _ask_user_for_hash_calculation(_file_path: str, _hash_type: str) -> bool:
        """
        DEPRECATED: Hash calculation is handled manually by the user.
        Kept for backward compatibility.
        """
        return False

    @staticmethod
    def _start_hash_calculation(file_path: str, hash_type: str) -> None:
        """
        DEPRECATED: Hash calculation is handled manually by the user.
        Kept for backward compatibility.
        """

    @staticmethod
    def is_effective(data: dict) -> bool:
        """
        Check if module is effective (will produce output).

        Args:
            data: Configuration dict with 'field' and 'category'

        Returns:
            True if module will produce output
        """
        field = data.get("field")
        category = data.get("category", "file_dates")

        # For hash category, check if field is a valid hash type
        if category == "hash":
            return field and field.startswith("hash_")  # type: ignore

        # For other categories, any field is effective
        return bool(field)
