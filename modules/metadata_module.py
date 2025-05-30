"""
Module: metadata_module.py

Author: Michael Economou
Date: 2025-05-04

This module provides logic for extracting metadata fields (such as creation date,
modification date, or EXIF tag) to include in renamed filenames.

It is used in the oncutf tool to dynamically extract and apply file
metadata during batch renaming.
"""

from typing import Optional
from datetime import datetime
from models.file_item import FileItem
import os

# initialize logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class MetadataModule:
    """
    Logic component (non-UI) for extracting and formatting metadata fields.
    Used during rename preview and execution.
    """

    @staticmethod
    def apply_from_data(data: dict, file_item: FileItem, index: int = 0, metadata_cache: Optional[dict] = None) -> str:
        """
        Extracts a metadata value from the cache for use in filename.

        Args:
            data (dict): Must contain the 'field' key
            file_item (FileItem): The file to rename
            index (int): Unused
            metadata_cache (dict): full_path → metadata dict

        Returns:
            str: The stringified metadata value or a fallback ("unknown", "invalid")
        """
        logger.debug(f"[MetadataModule] apply_from_data called with data: {data}")

        field = data.get("field")
        if not field:
            logger.warning("[MetadataModule] Missing 'field' in data config.")
            return "invalid"

        path = file_item.full_path
        if not path:
            logger.warning(f"[MetadataModule] No full_path available for {file_item.filename}")
            return "invalid"

        metadata = metadata_cache.get(path) if metadata_cache else {}

        if not isinstance(metadata, dict):
            logger.warning(f"[MetadataModule] No metadata dict found for {path}")
            metadata = {}  # fallback to empty

        logger.debug(f"[MetadataModule] apply_from_data for {file_item.filename} with field='{field}', path='{path}'")

        # Handle filesystem-based date formats
        if field and field.startswith("last_modified_"):
            try:
                ts = os.path.getmtime(path)
                dt = datetime.fromtimestamp(ts)

                if field == "last_modified_yymmdd":
                    return dt.strftime("%y%m%d")
                elif field == "last_modified_iso":
                    return dt.strftime("%Y-%m-%d")
                elif field == "last_modified_eu":
                    return dt.strftime("%d/%m/%Y")
                elif field == "last_modified_us":
                    return dt.strftime("%m-%d-%Y")
                elif field == "last_modified_year":
                    return dt.strftime("%Y")
                elif field == "last_modified_month":
                    return dt.strftime("%Y-%m")
                else:
                    # Fallback to YYMMDD format for unknown last_modified variants
                    return dt.strftime("%y%m%d")

            except Exception as e:
                logger.warning(f"[MetadataModule] Failed to read last modified time: {e}")
                return "invalid"

        # Legacy support for old "last_modified" field name
        if field == "last_modified":
            try:
                ts = os.path.getmtime(path)
                return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            except Exception as e:
                logger.warning(f"[MetadataModule] Failed to read last modified time: {e}")
                return "invalid"

        # Handle category-based metadata access
        category = data.get("category", "file_dates")

        if category == "metadata_keys" and field:
            # Access custom metadata key from file metadata
            value = metadata.get(field)
            if value is None:
                logger.info(f"[MetadataModule] No '{field}' field in metadata for {file_item.filename}")
                return "unknown"

            # Format the value appropriately
            try:
                return str(value).strip()
            except Exception as e:
                logger.warning(f"[MetadataModule] Failed to stringify metadata value for '{field}': {e}")
                return "invalid"

        # Handle legacy metadata-based fields for backwards compatibility
        if field == "creation_date":
            value = metadata.get("creation_date") or metadata.get("date_created")
            if not value:
                logger.info(f"[MetadataModule] No 'creation_date' field in metadata for {file_item.filename}")
                return "unknown"
            return str(value)

        if field == "date":
            value = metadata.get("date")
            if not value:
                logger.info(f"[MetadataModule] No 'date' field in metadata for {file_item.filename}")
                return "unknown"
            return str(value)

        # === Generic metadata field fallback ===
        if field:
            value = metadata.get(field)
            if value is None:
                logger.warning(f"[MetadataModule] Field '{field}' not found in metadata for {path}")
                return "unknown"

            try:
                return str(value).strip()
            except Exception as e:
                logger.warning(f"[MetadataModule] Failed to stringify metadata value: {e}")
                return "invalid"

        # No valid field specified
        logger.warning("[MetadataModule] No valid field specified in data config")
        return "invalid"

    @staticmethod
    def is_effective(data: dict) -> bool:
        # All metadata fields are effective, including last_modified
        field = data.get('field')
        return bool(field)  # True if we have a valid field

