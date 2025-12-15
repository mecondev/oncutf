"""
Module: metadata_module.py

Author: Michael Economou
Date: 2025-05-06

This module provides logic for extracting metadata fields (such as creation date,
modification date, or EXIF tag) to include in renamed filenames.
It is used in the oncutf tool to dynamically extract and apply file
metadata during batch renaming.
"""

import os
import time
from datetime import datetime

from oncutf.models.file_item import FileItem
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

        Windows-safe filename cleaning that handles all invalid characters.
        Time separators and timezone offsets use underscores for consistency.

        Args:
            value (str): The raw metadata value

        Returns:
            str: Cleaned value safe for use in filenames
        """
        if not value:
            return value

        # Windows invalid filename characters: < > : " / \ | ? *
        # Replace colons (common in date/time) with underscore for filename safety
        cleaned = value.replace(":", "_")

        # Replace other invalid characters with underscore
        invalid_chars = ["<", ">", '"', "/", "\\", "|", "?", "*"]
        for char in invalid_chars:
            cleaned = cleaned.replace(char, "_")

        # Replace multiple spaces with single underscore
        while "  " in cleaned:
            cleaned = cleaned.replace("  ", " ")

        # Replace spaces with underscore for filename safety
        cleaned = cleaned.replace(" ", "_")

        # Remove leading/trailing underscores
        cleaned = cleaned.strip("_")

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

        def _finalize_result(raw_value: str) -> str:
            """Normalize, validate and cache a metadata-derived filename-safe value.
            Returns a safe string or falls back to OriginalNameModule when not possible.
            """
            nonlocal cache_key, current_time
            try:
                candidate = MetadataModule.clean_metadata_value(str(raw_value).strip())

                # Quick validity check
                try:
                    from utils.validate_filename_text import is_valid_filename_text

                    if is_valid_filename_text(candidate):
                        _metadata_cache[cache_key] = candidate
                        _global_cache_timestamp = current_time
                        return candidate
                except Exception:
                    # If validator not available, proceed to cleaning attempts
                    pass

                # Try more aggressive cleaning using filename_validator
                try:
                    from utils.filename_validator import clean_filename_text
                    from utils.validate_filename_text import is_valid_filename_text

                    cleaned = clean_filename_text(candidate)
                    if is_valid_filename_text(cleaned):
                        _metadata_cache[cache_key] = cleaned
                        _global_cache_timestamp = current_time
                        return cleaned
                except Exception:
                    pass

                # Regex fallback: allow alnum, dash, underscore and dot
                import re

                alt = re.sub(r"[^A-Za-z0-9_.+-]+", "_", candidate).strip("_")
                try:
                    from utils.validate_filename_text import is_valid_filename_text

                    if is_valid_filename_text(alt):
                        _metadata_cache[cache_key] = alt
                        _global_cache_timestamp = current_time
                        return alt
                except Exception:
                    # If validator missing accept alt conservatively
                    _metadata_cache[cache_key] = alt
                    _global_cache_timestamp = current_time
                    return alt

            except Exception as e:
                logger.debug(f"[MetadataModule] _finalize_result error: {e}", extra={"dev_only": True})

            # Fallback to original name base
            try:
                from modules.original_name_module import OriginalNameModule

                return OriginalNameModule.apply_from_data({}, file_item, index, metadata_cache)  # type: ignore
            except Exception:
                # Last-resort fallback: basename without extension
                base = os.path.splitext(os.path.basename(file_item.filename))[0]
                return base

        # end _finalize_result

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

        # Normalize path for Windows compatibility at the very start
        from utils.path_normalizer import normalize_path

        path = file_item.full_path
        if not path:
            logger.debug(
                "[DEBUG] [MetadataModule] No path - returning 'invalid'", extra={"dev_only": True}
            )
            return "invalid"

        # CRITICAL: Normalize path for Windows
        path = normalize_path(path)
        logger.debug(f"[DEBUG] [MetadataModule] Normalized path: {path}", extra={"dev_only": True})

        # Use the same persistent cache as the UI if no cache provided
        if not metadata_cache:
            from core.persistent_metadata_cache import get_persistent_metadata_cache

            persistent_cache = get_persistent_metadata_cache()
            # Use normalized path for cache lookup.
            # Persistent cache exposes get_entry(...) (or batch methods); handle both persistent cache objects and dict-like fallbacks.
            if persistent_cache:
                try:
                    if hasattr(persistent_cache, "get_entry"):
                        entry = persistent_cache.get_entry(path)
                        metadata = getattr(entry, "data", {}) or {}
                    else:
                        # Some implementations may offer .get(path) (but may not accept a default arg)
                        try:
                            metadata = persistent_cache.get(path)  # type: ignore
                            if metadata is None:
                                metadata = {}
                        except TypeError:
                            metadata = {}
                except Exception as e:
                    logger.debug(
                        f"[DEBUG] [MetadataModule] persistent cache lookup failed: {e}",
                        extra={"dev_only": True},
                    )
                    metadata = {}
            else:
                metadata = {}
            logger.debug(
                f"[DEBUG] [MetadataModule] Using persistent cache for {file_item.filename}, path: {path}, has_metadata: {bool(metadata)}",
                extra={"dev_only": True},
            )
        else:
            # metadata_cache might be:
            # - a PersistentMetadataCache-like object (get_entry / get_entries_batch)
            # - a plain dict (used in tests)
            try:
                if hasattr(metadata_cache, "get_entry"):
                    entry = metadata_cache.get_entry(path)
                    metadata = getattr(entry, "data", {}) or {}
                elif isinstance(metadata_cache, dict):
                    metadata = metadata_cache.get(path, {})
                elif hasattr(metadata_cache, "get"):
                    # fallback; some cache-like objects implement get(path)
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
                    f"[DEBUG] [MetadataModule] Provided cache lookup failed: {e}",
                    extra={"dev_only": True},
                )
                metadata = {}
            logger.debug(
                f"[DEBUG] [MetadataModule] Using provided cache for {file_item.filename}, path: {path}, has_metadata: {bool(metadata)}",
                extra={"dev_only": True},
            )

        if not isinstance(metadata, dict):
            metadata = {}  # fallback to empty
            logger.debug(
                "[DEBUG] [MetadataModule] Metadata is not dict, using empty dict",
                extra={"dev_only": True},
            )

        # After getting metadata, log what we found
        if metadata:
            logger.debug(
                f"[DEBUG] [MetadataModule] Metadata keys available: {list(metadata.keys())[:20]}",
                extra={"dev_only": True},
            )

            # Log date-related fields specifically
            date_fields = {
                k: v for k, v in metadata.items() if "date" in k.lower() or "time" in k.lower()
            }
            if date_fields:
                logger.debug(
                    f"[DEBUG] [MetadataModule] Date/Time fields: {date_fields}",
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
                    # Use dash separator for EU format to be consistent with other displays
                    result = dt.strftime("%d-%m-%Y")
                elif field == "last_modified_us":
                    result = dt.strftime("%m-%d-%Y")
                elif field == "last_modified_year":
                    result = dt.strftime("%Y")
                elif field == "last_modified_month":
                    result = dt.strftime("%Y-%m")
                # New formats with time included
                elif field == "last_modified_iso_time":
                    # ISO-like with time (HH:MM) and safe for filenames (no colon)
                    result = dt.strftime("%Y-%m-%d_%H-%M")
                elif field == "last_modified_eu_time":
                    # EU style with time
                    result = dt.strftime("%d-%m-%Y_%H-%M")
                elif field == "last_modified_compact":
                    # Compact sortable with time YYMMDD_HHMM
                    result = dt.strftime("%y%m%d_%H%M")
                else:
                    # Fallback to YYMMDD format for unknown last_modified variants
                    result = dt.strftime("%y%m%d")

                logger.debug(
                    f"[DEBUG] [MetadataModule] Filesystem date result: {result}",
                    extra={"dev_only": True},
                )
                return _finalize_result(result)

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
                logger.debug(
                    f"[DEBUG] [MetadataModule] Legacy last_modified result: {result}",
                    extra={"dev_only": True},
                )
                return _finalize_result(result)
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
                    logger.debug(
                        f"[DEBUG] [MetadataModule] Hash result: {result}", extra={"dev_only": True}
                    )
                    return _finalize_result(result)
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

                return OriginalNameModule.apply_from_data({}, file_item, index, metadata_cache)  # type: ignore

            # Format the value appropriately and clean it for filename safety
            try:
                return _finalize_result(value)
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

                return OriginalNameModule.apply_from_data({}, file_item, index, metadata_cache)  # type: ignore
            return _finalize_result(value)

        if field == "date":
            value = metadata.get("date")
            if not value:
                from modules.original_name_module import OriginalNameModule

                return OriginalNameModule.apply_from_data({}, file_item, index, metadata_cache)  # type: ignore
            return _finalize_result(value)

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
                                    return _finalize_result(raw_value)
                        from modules.original_name_module import OriginalNameModule

                        return OriginalNameModule.apply_from_data(
                            {},
                            file_item,
                            index,
                            metadata_cache,  # type: ignore
                        )
            except ImportError:
                # Fallback if mapper not available
                pass

        # Final fallback: try direct metadata access
        value = metadata.get(field)
        if value is not None:
            return _finalize_result(value)

        # If we get here, the field was not found
        from modules.original_name_module import OriginalNameModule

        return OriginalNameModule.apply_from_data({}, file_item, index, metadata_cache)  # type: ignore

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
            # Fallback to original filename if hash is missing
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            return base_name
        except Exception as e:
            logger.warning(f"[MetadataModule] Error getting hash for {file_path}: {e}")
            # Fallback to original filename on error
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
            return field and field.startswith("hash_")  # type: ignore

        # For other categories, any field is effective
        return bool(field)
