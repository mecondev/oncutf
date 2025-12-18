"""
Module: extractor.py

Author: Michael Economou
Date: December 17, 2025

Pure Python metadata extraction logic with no UI dependencies.
Extracts metadata from files (filesystem dates, EXIF, hashes) for use in rename operations.

Supports dependency injection via service protocols for testability:
- MetadataServiceProtocol for EXIF/metadata loading
- HashServiceProtocol for hash computation
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Initialize logger
from oncutf.utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.services.interfaces import HashServiceProtocol, MetadataServiceProtocol

logger = get_cached_logger(__name__)


@dataclass
class ExtractionResult:
    """Result of metadata extraction operation."""

    value: str
    source: str  # 'filesystem', 'exif', 'hash', 'fallback'
    raw_value: Any = None
    field: str = ""
    category: str = ""


class MetadataExtractor:
    """
    Pure Python metadata extraction logic.
    No Qt/PyQt5 dependencies - fully testable in isolation.

    Supports dependency injection for services:
    - metadata_service: For loading EXIF/file metadata
    - hash_service: For computing file hashes

    If services are not provided, they are retrieved from ServiceRegistry.
    This ensures loose coupling while maintaining ease of use.
    """

    def __init__(
        self,
        metadata_service: MetadataServiceProtocol | None = None,
        hash_service: HashServiceProtocol | None = None,
    ) -> None:
        """Initialize the metadata extractor.

        Args:
            metadata_service: Optional service for metadata loading.
                              If None, retrieved from ServiceRegistry.
            hash_service: Optional service for hash computation.
                          If None, retrieved from ServiceRegistry.
        """
        self._cache: dict[str, ExtractionResult] = {}
        self._cache_timestamp = 0.0
        self._cache_validity_duration = 0.1  # 100ms cache validity

        # Use provided services or get from registry
        if metadata_service is not None:
            self._metadata_service = metadata_service
        else:
            self._metadata_service = self._get_service_from_registry("metadata")

        if hash_service is not None:
            self._hash_service = hash_service
        else:
            self._hash_service = self._get_service_from_registry("hash")

    def _get_service_from_registry(
        self, service_type: str
    ) -> MetadataServiceProtocol | HashServiceProtocol | None:
        """Get a service from the ServiceRegistry.

        Args:
            service_type: Either "metadata" or "hash"

        Returns:
            The service instance or None if not registered.
        """
        try:
            from oncutf.services.interfaces import (
                HashServiceProtocol as HashProto,
                MetadataServiceProtocol as MetaProto,
            )
            from oncutf.services.registry import get_service_registry

            registry = get_service_registry()
            if service_type == "metadata":
                return registry.get(MetaProto)
            elif service_type == "hash":
                return registry.get(HashProto)
        except ImportError:
            logger.debug("ServiceRegistry not available, using fallback")
        return None

    def extract(
        self,
        file_path: Path | str,
        field: str,
        category: str = "file_dates",
        metadata: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        """
        Extract metadata value from file.

        Args:
            file_path: Path to the file
            field: Field to extract (e.g., 'last_modified_iso', 'hash_crc32')
            category: Category of extraction ('file_dates', 'hash', 'metadata_keys')
            metadata: Pre-loaded metadata dict (optional)

        Returns:
            ExtractionResult with extracted value
        """
        # Normalize path
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Normalize path for Windows compatibility
        from oncutf.utils.path_normalizer import normalize_path

        normalized_path = normalize_path(str(file_path))
        file_path = Path(normalized_path)

        # Check cache first
        cache_key = f"{normalized_path}_{field}_{category}"
        current_time = time.time()

        if (
            cache_key in self._cache
            and current_time - self._cache_timestamp < self._cache_validity_duration
        ):
            logger.debug(
                "Returning cached result for %s",
                file_path.name,
                extra={"dev_only": True},
            )
            return self._cache[cache_key]

        # Validate inputs
        if not field:
            return ExtractionResult(
                value="invalid", source="error", field=field, category=category
            )

        # Skip file existence check if metadata is provided (for testing)
        if metadata is None and not file_path.exists():
            return ExtractionResult(
                value="invalid", source="error", field=field, category=category
            )

        # Extract based on category
        result: ExtractionResult

        if category == "file_dates":
            result = self._extract_filesystem_date(file_path, field)
        elif category == "hash":
            result = self._extract_hash(file_path, field)
        elif category == "metadata_keys":
            result = self._extract_metadata_field(file_path, field, metadata or {})
        else:
            result = ExtractionResult(
                value="invalid", source="error", field=field, category=category
            )

        # Cache and return
        self._cache[cache_key] = result
        self._cache_timestamp = current_time

        return result

    def _extract_filesystem_date(self, file_path: Path, field: str) -> ExtractionResult:
        """Extract filesystem date in various formats."""
        try:
            ts = os.path.getmtime(str(file_path))
            dt = datetime.fromtimestamp(ts)

            format_map = {
                "last_modified_yymmdd": "%y%m%d",
                "last_modified_iso": "%Y-%m-%d",
                "last_modified_eu": "%d-%m-%Y",
                "last_modified_us": "%m-%d-%Y",
                "last_modified_year": "%Y",
                "last_modified_month": "%Y-%m",
                "last_modified_iso_time": "%Y-%m-%d_%H-%M",
                "last_modified_eu_time": "%d-%m-%Y_%H-%M",
                "last_modified_compact": "%y%m%d_%H%M",
                "last_modified": "%Y-%m-%d",  # Legacy support
            }

            date_format = format_map.get(field, "%y%m%d")
            formatted_value = dt.strftime(date_format)

            return ExtractionResult(
                value=formatted_value,
                source="filesystem",
                raw_value=ts,
                field=field,
                category="file_dates",
            )

        except Exception as e:
            logger.debug(
                "Error getting filesystem date for %s: %s",
                file_path.name,
                e,
                extra={"dev_only": True},
            )
            return ExtractionResult(
                value="invalid", source="error", field=field, category="file_dates"
            )

    def _extract_hash(self, file_path: Path, field: str) -> ExtractionResult:
        """Extract file hash.

        Uses injected hash_service if available, otherwise falls back to
        internal implementation via get_hash_for_file helper.
        """
        if not field.startswith("hash_"):
            return ExtractionResult(
                value="invalid", source="error", field=field, category="hash"
            )

        try:
            hash_type = field.replace("hash_", "").lower()
            hash_value: str | None = None

            # Use injected service if available
            if self._hash_service is not None:
                hash_value = self._hash_service.compute_hash(file_path, hash_type)
            else:
                # Fallback to internal helper
                from oncutf.utils.file_status_helpers import get_hash_for_file

                hash_value = get_hash_for_file(str(file_path), hash_type.upper())

            if hash_value:
                return ExtractionResult(
                    value=hash_value,
                    source="hash",
                    raw_value=hash_value,
                    field=field,
                    category="hash",
                )

            # Fallback to filename if hash not available
            base_name = file_path.stem
            return ExtractionResult(
                value=base_name,
                source="fallback",
                raw_value=None,
                field=field,
                category="hash",
            )

        except Exception as e:
            logger.warning("Error getting hash for %s: %s", file_path.name, e)
            base_name = file_path.stem
            return ExtractionResult(
                value=base_name,
                source="fallback",
                raw_value=None,
                field=field,
                category="hash",
            )

    def _extract_metadata_field(
        self, file_path: Path, field: str, metadata: dict[str, Any]
    ) -> ExtractionResult:
        """Extract metadata field from EXIF/metadata dict."""
        # Legacy field mappings
        if field == "creation_date":
            value = metadata.get("creation_date") or metadata.get("date_created")
            if value:
                cleaned = self.clean_for_filename(str(value))
                return ExtractionResult(
                    value=cleaned,
                    source="exif",
                    raw_value=value,
                    field=field,
                    category="metadata_keys",
                )

        if field == "date":
            value = metadata.get("date")
            if value:
                cleaned = self.clean_for_filename(str(value))
                return ExtractionResult(
                    value=cleaned,
                    source="exif",
                    raw_value=value,
                    field=field,
                    category="metadata_keys",
                )

        # Try centralized field mapper
        try:
            from oncutf.utils.metadata_field_mapper import MetadataFieldMapper

            if MetadataFieldMapper.has_field_mapping(field):
                possible_keys = MetadataFieldMapper.get_metadata_keys_for_field(field)
                for key in possible_keys:
                    if key in metadata:
                        raw_value = metadata[key]
                        if raw_value is not None:
                            cleaned = self.clean_for_filename(str(raw_value))
                            return ExtractionResult(
                                value=cleaned,
                                source="exif",
                                raw_value=raw_value,
                                field=field,
                                category="metadata_keys",
                            )
        except ImportError:
            pass

        # Direct metadata access
        value = metadata.get(field)
        if value is not None:
            cleaned = self.clean_for_filename(str(value))
            return ExtractionResult(
                value=cleaned,
                source="exif",
                raw_value=value,
                field=field,
                category="metadata_keys",
            )

        # Fallback to filename
        base_name = file_path.stem
        return ExtractionResult(
            value=base_name,
            source="fallback",
            raw_value=None,
            field=field,
            category="metadata_keys",
        )

    def clean_for_filename(self, value: str) -> str:
        """
        Clean metadata value for filename safety.

        Windows-safe filename cleaning that handles all invalid characters.
        Time separators and timezone offsets use underscores for consistency.

        Args:
            value: The raw metadata value

        Returns:
            Cleaned value safe for use in filenames
        """
        if not value:
            return value

        # Windows invalid filename characters: < > : " / \ | ? *
        cleaned = value.replace(":", "_")

        invalid_chars = ["<", ">", '"', "/", "\\", "|", "?", "*"]
        for char in invalid_chars:
            cleaned = cleaned.replace(char, "_")

        # Replace multiple spaces with single space
        while "  " in cleaned:
            cleaned = cleaned.replace("  ", " ")

        # Replace spaces with underscore
        cleaned = cleaned.replace(" ", "_")

        # Regex fallback: allow alnum, dash, underscore and dot
        # This handles Unicode and other non-ASCII characters early
        cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "_", cleaned).strip("_")

        # Remove leading/trailing underscores
        cleaned = cleaned.strip("_")

        # Try validation if available
        try:
            from oncutf.utils.validate_filename_text import is_valid_filename_text

            if is_valid_filename_text(cleaned):
                return cleaned
        except ImportError:
            pass

        # Try more aggressive cleaning if validation failed
        try:
            from oncutf.utils.filename_validator import clean_filename_text
            from oncutf.utils.validate_filename_text import is_valid_filename_text

            alt_cleaned = clean_filename_text(cleaned)
            if is_valid_filename_text(alt_cleaned):
                return alt_cleaned
        except ImportError:
            pass

        # Return what we have
        return cleaned

    def get_available_fields(self, category: str) -> list[str]:
        """
        Get list of available fields for a category.

        Args:
            category: Category ('file_dates', 'hash', 'metadata_keys')

        Returns:
            List of field names
        """
        category_fields = {
            "file_dates": [
                "last_modified_yymmdd",
                "last_modified_iso",
                "last_modified_eu",
                "last_modified_us",
                "last_modified_year",
                "last_modified_month",
                "last_modified_iso_time",
                "last_modified_eu_time",
                "last_modified_compact",
            ],
            "hash": ["hash_crc32"],
            "metadata_keys": ["creation_date", "date", "DateTimeOriginal", "CreateDate"],
        }
        return category_fields.get(category, [])

    def clear_cache(self) -> None:
        """Clear the extraction cache."""
        self._cache.clear()
        self._cache_timestamp = 0.0
