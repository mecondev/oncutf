"""Module: metadata_keys_handler.py.

Author: Michael Economou
Date: 2025-12-24

Handler for metadata keys operations - collection, grouping, and categorization.
"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from oncutf.core.metadata.metadata_simplification_service import (
    get_metadata_simplification_service,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_widget import MetadataWidget

logger = get_cached_logger(__name__)


class MetadataKeysHandler:
    """Handler for metadata keys operations in MetadataWidget."""

    def __init__(self, widget: MetadataWidget) -> None:
        """Initialize the handler with a reference to the widget.

        Args:
            widget: The MetadataWidget instance

        """
        self._widget = widget
        self._simplification_service = get_metadata_simplification_service()

    def populate_metadata_keys(self) -> None:
        """Populate the hierarchical combo box with available metadata keys.
        Keys are grouped by category with Common Fields (semantic aliases) at top.
        """
        keys = self.get_available_metadata_keys()
        self._widget.options_combo.clear()

        # Log available keys for debugging
        logger.debug("Available metadata keys: %s", keys)

        if not keys:
            hierarchical_data = {
                "No Metadata": [
                    ("(No metadata fields available)", None),
                ]
            }
            self._widget.options_combo.populate_from_metadata_groups(hierarchical_data)
            logger.debug("No metadata keys available, showing placeholder")
            return

        # Build hierarchical data structure
        hierarchical_data = {}

        # Add Common Fields group first (semantic aliases)
        common_fields = self._build_common_fields_group(keys)
        if common_fields:
            hierarchical_data["Common Fields"] = common_fields
            logger.debug("Added %d common fields", len(common_fields))

        # Group remaining keys by category
        grouped_keys = self.group_metadata_keys(keys)
        logger.debug("Grouped keys: %s", grouped_keys)

        for category, category_keys in grouped_keys.items():
            if category_keys:  # Only add categories that have items
                hierarchical_data[category] = []
                for key in sorted(category_keys):
                    # Use simplification service for display text
                    display_text = self._simplification_service.simplify_single_key(key)
                    hierarchical_data[category].append((display_text, key))
                    logger.debug("Added %s -> %s to %s", display_text, key, category)

        # Populate combo box with grouped data
        # When populating metadata keys we prefer the first key selected automatically
        self._widget.options_combo.populate_from_metadata_groups(
            hierarchical_data, auto_select_first=True
        )

        # Prefer selecting 'FileName' by default if available
        with suppress(Exception):
            self._widget.options_combo.select_item_by_data("FileName")

        # Force update to ensure UI reflects changes
        self._widget.emit_if_changed()

        # Enable the combo box
        self._widget.options_combo.setEnabled(True)

        # Apply normal styling
        self._widget._styling_handler.apply_normal_combo_styling()

        logger.debug("Populated metadata keys with %d categories", len(hierarchical_data))

    def group_metadata_keys(self, keys: set[str]) -> dict[str, list[str]]:
        """Group metadata keys by category for better organization.

        Args:
            keys: Set of metadata key names

        Returns:
            Dictionary mapping category names to lists of keys

        """
        grouped = {}

        for key in keys:
            category = self.classify_metadata_key(key)
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(key)

        # Sort categories for consistent display order
        category_order = [
            "File Info",
            "Camera Settings",
            "Image Info",
            "Video Info",
            "Audio Info",
            "GPS & Location",
            "Technical Info",
            "Other",
        ]

        # Return ordered dictionary
        ordered_grouped = {}
        for category in category_order:
            if category in grouped:
                ordered_grouped[category] = grouped[category]

        return ordered_grouped

    def classify_metadata_key(self, key: str) -> str:
        """Classify a metadata key into a category.

        Args:
            key: The metadata key name

        Returns:
            Category name (File Info, Camera Settings, etc.)

        """
        key_lower = key.lower()

        # File-related metadata
        if key_lower.startswith("file") or key_lower in {"rotation", "directory", "sourcefile"}:
            return "File Info"

        # Camera Settings - Critical for photography/videography
        if any(
            term in key_lower
            for term in [
                "iso",
                "aperture",
                "fnumber",
                "shutter",
                "exposure",
                "focal",
                "flash",
                "metering",
                "whitebalance",
                "gain",
                "lightvalue",
            ]
        ):
            return "Camera Settings"

        # GPS and Location
        if any(
            term in key_lower for term in ["gps", "location", "latitude", "longitude", "altitude"]
        ):
            return "GPS & Location"

        # Audio-related metadata
        if key_lower.startswith("audio") or key_lower in {
            "samplerate",
            "channelmode",
            "bitrate",
            "title",
            "album",
            "artist",
            "composer",
            "genre",
            "duration",
        }:
            return "Audio Info"

        # Image-specific metadata
        if (
            key_lower.startswith("image")
            or "sensor" in key_lower
            or any(
                term in key_lower for term in ["width", "height", "resolution", "dpi", "colorspace"]
            )
        ):
            return "Image Info"

        # Video-specific metadata
        if any(
            term in key_lower
            for term in [
                "video",
                "frame",
                "codec",
                "bitrate",
                "fps",
                "duration",
                "format",
                "avgbitrate",
                "maxbitrate",
                "videocodec",
            ]
        ):
            return "Video Info"

        # Technical/System
        if any(
            term in key_lower
            for term in ["version", "software", "firmware", "make", "model", "serial", "uuid", "id"]
        ):
            return "Technical Info"

        return "Other"

    def _build_common_fields_group(self, available_keys: set[str]) -> list[tuple[str, str]]:
        """Build Common Fields group from semantic aliases present in available keys.

        Args:
            available_keys: Set of available metadata keys

        Returns:
            List of (display_text, original_key) tuples for common fields

        """
        common_fields = []

        # Access registry semantic index directly
        semantic_index = self._simplification_service._registry._semantic_index

        for semantic_name, original_keys_list in semantic_index.items():
            # Find first available key for this semantic alias
            for original_key in original_keys_list:
                if original_key in available_keys:
                    # Use semantic name as display text
                    common_fields.append((semantic_name, original_key))
                    break  # Use first match only

        # Sort by display name for consistent order
        common_fields.sort(key=lambda x: x[0])
        return common_fields

    def get_available_metadata_keys(self) -> set[str]:
        """Get all available metadata keys from selected files.

        Returns:
            Set of metadata key names found in selected files

        """
        selected_files = self._widget._get_selected_files()

        # Use the same persistent cache as batch_metadata_status
        from oncutf.core.cache.persistent_metadata_cache import get_persistent_metadata_cache

        metadata_cache = get_persistent_metadata_cache()

        if not metadata_cache:
            return set()

        keys = set()
        for file_item in selected_files:
            # Use the same path normalization as batch_metadata_status
            from oncutf.utils.filesystem.path_normalizer import normalize_path

            normalized_path = normalize_path(file_item.full_path)
            # Support multiple cache types: persistent cache (get_entry) or dict-like
            try:
                if hasattr(metadata_cache, "get_entry"):
                    entry = metadata_cache.get_entry(normalized_path)
                    meta = getattr(entry, "data", {}) or {}
                elif isinstance(metadata_cache, dict):
                    meta = metadata_cache.get(normalized_path, {})
                elif hasattr(metadata_cache, "get"):
                    try:
                        meta = metadata_cache.get(normalized_path)  # type: ignore
                        if meta is None:
                            meta = {}
                    except TypeError:
                        meta = {}
                else:
                    meta = {}
            except Exception as e:
                logger.debug(
                    "[MetadataKeysHandler] Error reading metadata cache for %s: %s",
                    normalized_path,
                    e,
                    extra={"dev_only": True},
                )
                meta = {}

            if meta and isinstance(meta, dict):
                keys.update(meta.keys())

        return keys
