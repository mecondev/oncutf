"""
Structured Metadata Manager

This module handles the conversion of raw metadata from ExifTool to structured metadata
that can be stored in the database with proper categorization and field definitions.
"""

from pathlib import Path
from typing import Any

from oncutf.core.database_manager import get_database_manager
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class StructuredMetadataManager:
    """
    Manages the conversion and storage of structured metadata.

    This class handles:
    - Converting raw ExifTool metadata to structured format
    - Storing structured metadata in the database
    - Retrieving structured metadata with proper categorization
    - Managing metadata field definitions and categories
    """

    def __init__(self):
        self.db_manager = get_database_manager()
        self._field_cache = {}
        self._category_cache = {}
        self._load_caches()

    def _load_caches(self):
        """Load metadata fields and categories into cache for performance."""
        try:
            # Load categories
            categories = self.db_manager.get_metadata_categories()
            self._category_cache = {cat["category_name"]: cat for cat in categories}

            # Load fields
            fields = self.db_manager.get_metadata_fields()
            self._field_cache = {field["field_key"]: field for field in fields}

            logger.debug(
                f"[StructuredMetadataManager] Loaded {len(self._category_cache)} categories and {len(self._field_cache)} fields"
            )

        except Exception as e:
            logger.error(f"[StructuredMetadataManager] Error loading caches: {e}")

    def refresh_caches(self):
        """Refresh the internal caches."""
        self._load_caches()

    def process_and_store_metadata(self, file_path: str, raw_metadata: dict[str, Any]) -> bool:
        """
        Process raw metadata and store it in structured format.

        Args:
            file_path: Path to the file
            raw_metadata: Raw metadata dictionary from ExifTool

        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare batch data: list of (field_key, field_value_str) tuples
            batch_data = []

            for field_key, field_value in raw_metadata.items():
                # Skip None values and empty strings
                if field_value is None or field_value == "":
                    continue

                # Check if this field is defined in our schema
                if field_key not in self._field_cache:
                    # For unknown fields, we could either skip them or create dynamic fields
                    # For now, we'll skip them but log for debugging
                    logger.debug(
                        f"[StructuredMetadataManager] Unknown field '{field_key}' - skipping"
                    )
                    continue

                # Convert value to string for storage
                field_value_str = self._format_field_value(field_key, field_value)
                batch_data.append((field_key, field_value_str))

            # Use batch insert for all fields at once
            if batch_data:
                stored_count = self.db_manager.batch_store_structured_metadata(
                    file_path, batch_data
                )
                logger.debug(
                    f"[StructuredMetadataManager] Stored {stored_count} structured metadata fields for {Path(file_path).name}"
                )
                return stored_count > 0
            else:
                logger.debug(
                    f"[StructuredMetadataManager] No valid fields to store for {Path(file_path).name}"
                )
                return True

        except Exception as e:
            logger.error(
                f"[StructuredMetadataManager] Error processing metadata for {file_path}: {e}"
            )
            return False

    def _format_field_value(self, field_key: str, field_value: Any) -> str:
        """
        Format field value according to its data type and display format.

        Args:
            field_key: The metadata field key
            field_value: The raw field value

        Returns:
            Formatted string value
        """
        try:
            field_info = self._field_cache.get(field_key)
            if not field_info:
                return str(field_value)

            data_type = field_info.get("data_type", "text")
            # display_format = field_info.get('display_format')

            # Handle different data types
            if data_type == "number":
                if isinstance(field_value, int | float):
                    return str(field_value)
                else:
                    # Try to extract number from string
                    import re

                    match = re.search(r"[\d.]+", str(field_value))
                    if match:
                        return match.group()
                    return str(field_value)

            elif data_type == "size":
                # Handle file size formatting
                if isinstance(field_value, int | float):
                    return str(int(field_value))
                return str(field_value)

            elif data_type == "datetime":
                # Handle datetime formatting
                return str(field_value)

            elif data_type == "duration":
                # Handle duration formatting
                return str(field_value)

            elif data_type == "coordinate":
                # Handle GPS coordinate formatting
                if isinstance(field_value, int | float):
                    return f"{field_value:.6f}"
                return str(field_value)

            else:
                # Default to string
                return str(field_value)

        except Exception as e:
            logger.error(f"[StructuredMetadataManager] Error formatting field '{field_key}': {e}")
            return str(field_value)

    def get_structured_metadata(self, file_path: str) -> dict[str, dict[str, Any]]:
        """
        Get structured metadata for a file, organized by categories.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary organized by category names containing field data
        """
        try:
            raw_structured = self.db_manager.get_structured_metadata(file_path)

            # Organize by categories
            categorized = {}

            for field_key, field_data in raw_structured.items():
                category_name = field_data["category_name"]
                category_display_name = field_data["category_display_name"]

                if category_name not in categorized:
                    categorized[category_name] = {
                        "display_name": category_display_name,
                        "fields": {},
                    }

                categorized[category_name]["fields"][field_key] = {
                    "value": field_data["value"],
                    "field_name": field_data["field_name"],
                    "data_type": field_data["data_type"],
                    "display_format": field_data["display_format"],
                }

            return categorized

        except Exception as e:
            logger.error(
                f"[StructuredMetadataManager] Error getting structured metadata for {file_path}: {e}"
            )
            return {}

    def get_field_value(self, file_path: str, field_key: str) -> str | None:
        """
        Get a specific field value for a file.

        Args:
            file_path: Path to the file
            field_key: The metadata field key

        Returns:
            Field value or None if not found
        """
        try:
            structured_data = self.db_manager.get_structured_metadata(file_path)
            field_data = structured_data.get(field_key)
            return field_data["value"] if field_data else None

        except Exception as e:
            logger.error(
                f"[StructuredMetadataManager] Error getting field '{field_key}' for {file_path}: {e}"
            )
            return None

    def get_available_fields(self, category_name: str = None) -> list[dict[str, Any]]:
        """
        Get available metadata fields, optionally filtered by category.

        Args:
            category_name: Optional category name to filter by

        Returns:
            List of field definitions
        """
        try:
            if category_name:
                # Get category ID first
                category_info = self._category_cache.get(category_name)
                if not category_info:
                    return []

                return self.db_manager.get_metadata_fields(category_info["id"])
            else:
                return self.db_manager.get_metadata_fields()

        except Exception as e:
            logger.error(f"[StructuredMetadataManager] Error getting available fields: {e}")
            return []

    def get_available_categories(self) -> list[dict[str, Any]]:
        """
        Get all available metadata categories.

        Returns:
            List of category definitions
        """
        try:
            return self.db_manager.get_metadata_categories()
        except Exception as e:
            logger.error(f"[StructuredMetadataManager] Error getting available categories: {e}")
            return []

    def add_custom_field(
        self,
        field_key: str,
        field_name: str,
        category_name: str,
        data_type: str = "text",
        is_editable: bool = True,
        is_searchable: bool = True,
        display_format: str = None,
    ) -> bool:
        """
        Add a custom metadata field.

        Args:
            field_key: Unique field key
            field_name: Display name for the field
            category_name: Category to add the field to
            data_type: Data type of the field
            is_editable: Whether the field can be edited
            is_searchable: Whether the field can be searched
            display_format: Optional display format

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get category ID
            category_info = self._category_cache.get(category_name)
            if not category_info:
                logger.error(f"[StructuredMetadataManager] Category '{category_name}' not found")
                return False

            # Create the field
            field_id = self.db_manager.create_metadata_field(
                field_key,
                field_name,
                category_info["id"],
                data_type,
                is_editable,
                is_searchable,
                display_format,
            )

            if field_id:
                # Refresh cache
                self.refresh_caches()
                logger.info(f"[StructuredMetadataManager] Added custom field '{field_key}'")
                return True

            return False

        except Exception as e:
            logger.error(
                f"[StructuredMetadataManager] Error adding custom field '{field_key}': {e}"
            )
            return False

    def update_field_value(self, file_path: str, field_key: str, new_value: str) -> bool:
        """
        Update a specific field value for a file.

        Args:
            file_path: Path to the file
            field_key: The metadata field key
            new_value: New value to set

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if field is editable
            field_info = self._field_cache.get(field_key)
            if not field_info:
                logger.error(f"[StructuredMetadataManager] Field '{field_key}' not found")
                return False

            if not field_info.get("is_editable", False):
                logger.error(f"[StructuredMetadataManager] Field '{field_key}' is not editable")
                return False

            # Format the new value
            formatted_value = self._format_field_value(field_key, new_value)

            # Store the updated value
            success = self.db_manager.store_structured_metadata(
                file_path, field_key, formatted_value
            )

            if success:
                logger.info(
                    f"[StructuredMetadataManager] Updated field '{field_key}' for {Path(file_path).name}"
                )

            return success

        except Exception as e:
            logger.error(f"[StructuredMetadataManager] Error updating field '{field_key}': {e}")
            return False

    def search_files_by_metadata(
        self, field_key: str, _search_value: str, _search_type: str = "contains"
    ) -> list[str]:
        """
        Search files by metadata field value.

        Args:
            field_key: The metadata field key to search
            search_value: Value to search for
            search_type: Type of search ("contains", "equals", "starts_with", "ends_with")

        Returns:
            List of file paths matching the search criteria
        """
        try:
            # Check if field is searchable
            field_info = self._field_cache.get(field_key)
            if not field_info or not field_info.get("is_searchable", True):
                logger.warning(f"[StructuredMetadataManager] Field '{field_key}' is not searchable")
                return []

            # This would require a more complex query - for now, return empty list
            # TODO: Implement database search functionality
            logger.info("[StructuredMetadataManager] Search functionality not yet implemented")
            return []

        except Exception as e:
            logger.error(f"[StructuredMetadataManager] Error searching by metadata: {e}")
            return []


# =====================================
# Global Instance Management
# =====================================

_structured_metadata_manager_instance = None


def get_structured_metadata_manager() -> StructuredMetadataManager:
    """Get global structured metadata manager instance."""
    global _structured_metadata_manager_instance
    if _structured_metadata_manager_instance is None:
        _structured_metadata_manager_instance = StructuredMetadataManager()
    return _structured_metadata_manager_instance


def initialize_structured_metadata_manager() -> StructuredMetadataManager:
    """Initialize structured metadata manager."""
    global _structured_metadata_manager_instance
    _structured_metadata_manager_instance = StructuredMetadataManager()
    return _structured_metadata_manager_instance
