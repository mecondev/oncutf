"""
Module: metadata_module.py

Author: Michael Economou
Date: 2025-05-31

This module provides logic for extracting metadata fields (such as creation date,
modification date, or EXIF tag) to include in renamed filenames.
It is used in the oncutf tool to dynamically extract and apply file
metadata during batch renaming.
"""

import os
import time
from datetime import datetime

from models.file_item import FileItem
from utils.file_status_helpers import get_hash_for_file

# initialize logger
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Performance optimization: Cache for metadata lookups
_metadata_cache: dict = {}
_cache_timestamp = 0
_cache_validity_duration = 0.1  # 100ms cache validity

# Global cache variables to avoid UnboundLocalError
_global_cache_timestamp = 0


class MetadataModule:
    """
    Logic component (non-UI) for extracting and formatting metadata fields.
    Used during rename preview and execution.
    """

    @staticmethod
    def clean_metadata_value(value: str) -> str:
        """
        Clean metadata value for filename safety by replacing problematic characters.

        Args:
            value (str): The raw metadata value

        Returns:
            str: Cleaned value safe for use in filenames
        """
        if not value:
            return value

        # Replace colons and spaces with underscores for filename safety
        cleaned = value.replace(":", "_").replace(" ", "_")
        return cleaned

    @staticmethod
    def apply_from_data(
        data: dict, file_item: FileItem, index: int = 0, metadata_cache: dict | None = None
    ) -> str:
        logger.debug(
            f"[DEBUG] [MetadataModule] apply_from_data CALLED for {file_item.filename}",
            extra={"dev_only": True},
        )
        logger.debug(f"[DEBUG] [MetadataModule] data: {data}", extra={"dev_only": True})
        logger.debug(
            f"[DEBUG] [MetadataModule] metadata_cache provided: {metadata_cache is not None}",
            extra={"dev_only": True},
        )

        global _metadata_cache, _global_cache_timestamp

        # Performance optimization: Check cache first
        cache_key = f"{file_item.full_path}_{hash(str(data))}"
        current_time = time.time()

        if (
            cache_key in _metadata_cache
            and current_time - _global_cache_timestamp < _cache_validity_duration
        ):
            logger.debug(
                f"[DEBUG] [MetadataModule] Returning cached result for {file_item.filename}",
                extra={"dev_only": True},
            )
            return _metadata_cache[cache_key]

        field = data.get("field")
        logger.debug(f"[DEBUG] [MetadataModule] Field: {field}", extra={"dev_only": True})
        if not field:
            logger.debug(
                "[DEBUG] [MetadataModule] No field specified - returning 'invalid'",
                extra={"dev_only": True},
            )
            return "invalid"

        path = file_item.full_path
        if not path:
            logger.debug(
                "[DEBUG] [MetadataModule] No path - returning 'invalid'", extra={"dev_only": True}
            )
            return "invalid"

        # Use the same persistent cache as the UI if no cache provided
        if not metadata_cache:
            from core.persistent_metadata_cache import get_persistent_metadata_cache
            from utils.path_normalizer import normalize_path

            persistent_cache = get_persistent_metadata_cache()
            normalized_path = normalize_path(path)
            metadata = persistent_cache.get(normalized_path) if persistent_cache else {}
            logger.debug(
                f"[DEBUG] [MetadataModule] Using persistent cache for {file_item.filename}, normalized_path: {normalized_path}, metadata: {metadata}",
                extra={"dev_only": True},
            )
        else:
            metadata = metadata_cache.get(path) if metadata_cache else {}
            logger.debug(
                f"[DEBUG] [MetadataModule] Using provided cache for {file_item.filename}, path: {path}, metadata: {metadata}",
                extra={"dev_only": True},
            )

        if not isinstance(metadata, dict):
            metadata = {}  # fallback to empty
            logger.debug(
                "[DEBUG] [MetadataModule] Metadata is not dict, using empty dict",
                extra={"dev_only": True},
            )

        # Handle filesystem-based date formats
        if field and field.startswith("last_modified_"):
            logger.debug(
                f"[DEBUG] [MetadataModule] Handling filesystem date format: {field}",
                extra={"dev_only": True},
            )
            try:
                ts = os.path.getmtime(path)
                dt = datetime.fromtimestamp(ts)

                if field == "last_modified_yymmdd":
                    result = dt.strftime("%y%m%d")
                elif field == "last_modified_iso":
                    result = dt.strftime("%Y-%m-%d")
                elif field == "last_modified_eu":
                    result = dt.strftime("%d/%m/%Y")
                elif field == "last_modified_us":
                    result = dt.strftime("%m-%d-%Y")
                elif field == "last_modified_year":
                    result = dt.strftime("%Y")
                elif field == "last_modified_month":
                    result = dt.strftime("%Y-%m")
                else:
                    # Fallback to YYMMDD format for unknown last_modified variants
                    result = dt.strftime("%y%m%d")

                # Cache the result
                _metadata_cache[cache_key] = result
                _global_cache_timestamp = current_time
                logger.debug(
                    f"[DEBUG] [MetadataModule] Filesystem date result: {result}",
                    extra={"dev_only": True},
                )
                return result

            except Exception as e:
                logger.debug(
                    f"[DEBUG] [MetadataModule] Error getting filesystem date: {e}",
                    extra={"dev_only": True},
                )
                return "invalid"

        # Legacy support for old "last_modified" field name
        if field == "last_modified":
            logger.debug(
                "[DEBUG] [MetadataModule] Handling legacy last_modified field",
                extra={"dev_only": True},
            )
            try:
                ts = os.path.getmtime(path)
                result = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                _metadata_cache[cache_key] = result
                _global_cache_timestamp = current_time
                logger.debug(
                    f"[DEBUG] [MetadataModule] Legacy last_modified result: {result}",
                    extra={"dev_only": True},
                )
                return result
            except Exception as e:
                logger.debug(
                    f"[DEBUG] [MetadataModule] Error getting legacy last_modified: {e}",
                    extra={"dev_only": True},
                )
                return "invalid"

        # Handle category-based metadata access
        category = data.get("category", "file_dates")
        logger.debug(f"[DEBUG] [MetadataModule] Category: {category}", extra={"dev_only": True})

        if category == "hash" and field:
            logger.debug(
                "[DEBUG] [MetadataModule] Handling hash category", extra={"dev_only": True}
            )
            # Handle hash fields for the hash category
            if field.startswith("hash_"):
                try:
                    hash_type = field.replace("hash_", "").upper()
                    result = MetadataModule._get_file_hash(path, hash_type)
                    _metadata_cache[cache_key] = result
                    _global_cache_timestamp = current_time
                    logger.debug(
                        f"[DEBUG] [MetadataModule] Hash result: {result}", extra={"dev_only": True}
                    )
                    return result
                except Exception as e:
                    logger.debug(
                        f"[DEBUG] [MetadataModule] Error getting hash: {e}",
                        extra={"dev_only": True},
                    )
                    return "invalid"
            else:
                logger.debug(
                    f"[DEBUG] [MetadataModule] Invalid hash field: {field}",
                    extra={"dev_only": True},
                )
                return "invalid"

        if category == "metadata_keys" and field:
            logger.debug(
                f"[DEBUG] [MetadataModule] Handling metadata_keys category for field: {field}",
                extra={"dev_only": True},
            )
            # Access custom metadata key from file metadata
            value = metadata.get(field)
            logger.debug(
                f"[DEBUG] [MetadataModule] Metadata value for field '{field}': {value}",
                extra={"dev_only": True},
            )
            if value is None:
                logger.debug(
                    f"[DEBUG] [MetadataModule] Field '{field}' not found in metadata, falling back to original name",
                    extra={"dev_only": True},
                )
                # Fallback: return original name
                from modules.original_name_module import OriginalNameModule

                return OriginalNameModule.apply_from_data({}, file_item, index, metadata_cache)

            # Format the value appropriately and clean it for filename safety
            try:
                cleaned_value = MetadataModule.clean_metadata_value(str(value).strip())
                _metadata_cache[cache_key] = cleaned_value
                _global_cache_timestamp = current_time
                logger.debug(
                    f"[DEBUG] [MetadataModule] Metadata result: {cleaned_value}",
                    extra={"dev_only": True},
                )
                return cleaned_value
            except Exception as e:
                logger.debug(
                    f"[DEBUG] [MetadataModule] Error cleaning metadata value: {e}",
                    extra={"dev_only": True},
                )
                return "invalid"

        # Handle legacy metadata-based fields for backwards compatibility
        if field == "creation_date":
            value = metadata.get("creation_date") or metadata.get("date_created")
            if not value:
                from modules.original_name_module import OriginalNameModule

                return OriginalNameModule.apply_from_data({}, file_item, index, metadata_cache)
            result = MetadataModule.clean_metadata_value(str(value))
            _metadata_cache[cache_key] = result
            _global_cache_timestamp = current_time
            return result

        if field == "date":
            value = metadata.get("date")
            if not value:
                from modules.original_name_module import OriginalNameModule

                return OriginalNameModule.apply_from_data({}, file_item, index, metadata_cache)
            result = MetadataModule.clean_metadata_value(str(value))
            _metadata_cache[cache_key] = result
            _global_cache_timestamp = current_time
            return result

        # === Generic metadata field fallback using centralized mapper ===
        if field:
            # Try using the centralized field mapper for better key mapping
            try:
                from utils.metadata_field_mapper import MetadataFieldMapper

                # Check if this field has a mapping in our centralized mapper
                if MetadataFieldMapper.has_field_mapping(field):
                    value = MetadataFieldMapper.get_metadata_value(metadata, field)
                    if value:
                        # For rename module, we want raw values not formatted ones
                        # So get the raw value using the mapper's key lookup
                        possible_keys = MetadataFieldMapper.get_metadata_keys_for_field(field)
                        for key in possible_keys:
                            if key in metadata:
                                raw_value = metadata[key]
                                if raw_value is not None:
                                    cleaned_value = MetadataModule.clean_metadata_value(
                                        str(raw_value).strip()
                                    )
                                    _metadata_cache[cache_key] = cleaned_value
                                    _global_cache_timestamp = current_time
                                    return cleaned_value
                        from modules.original_name_module import OriginalNameModule

                        return OriginalNameModule.apply_from_data(
                            {}, file_item, index, metadata_cache
                        )
            except ImportError:
                # Fallback if mapper not available
                pass

        # Final fallback: try direct metadata access
        value = metadata.get(field)
        if value is not None:
            cleaned_value = MetadataModule.clean_metadata_value(str(value).strip())
            _metadata_cache[cache_key] = cleaned_value
            _global_cache_timestamp = current_time
            return cleaned_value

        # If we get here, the field was not found
        from modules.original_name_module import OriginalNameModule

        return OriginalNameModule.apply_from_data({}, file_item, index, metadata_cache)

    @staticmethod
    def clear_cache():
        """Clear the metadata cache."""
        global _metadata_cache, _global_cache_timestamp
        _metadata_cache.clear()
        _global_cache_timestamp = 0

    @staticmethod
    def _get_file_hash(file_path: str, hash_type: str) -> str:
        """
        Get file hash using the hash cache. If hash is missing, return original name without showing dialog.

        Args:
            file_path: Path to the file
            hash_type: Type of hash (CRC32 only)

        Returns:
            str: Hash value or original name if not available
        """
        try:
            hash_value = get_hash_for_file(file_path, hash_type)
            if hash_value:
                return hash_value
            import os

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            return base_name
        except Exception as e:
            logger.warning(f"[MetadataModule] Error getting hash for {file_path}: {e}")
            import os

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            return base_name

    @staticmethod
    def _ask_user_for_hash_calculation(_file_path: str, _hash_type: str) -> bool:
        """
        This method is no longer used - hash calculation is handled manually by the user.
        Kept for backward compatibility.
        """
        return False

    @staticmethod
    def _start_hash_calculation(file_path: str, hash_type: str) -> None:
        """
        This method is no longer used - hash calculation is handled manually by the user.
        """

    @staticmethod
    def is_effective(data: dict) -> bool:
        # All metadata fields are effective, including last_modified and hash
        field = data.get("field")
        category = data.get("category", "file_dates")

        # For hash category, check if field is a valid hash type
        if category == "hash":
            return field and field.startswith("hash_")

        # For other categories, any field is effective
        return bool(field)
