"""Module: service.py

Author: Michael Economou
Date: 2025-12-23

Business logic layer for the metadata tree widget.

This module contains the service layer that handles:
- Metadata grouping and classification
- Key formatting and normalization
- Modified/extended key detection
- Tree data structure building (pure data, no Qt)

This layer is Qt-free and works with pure data structures (TreeNodeData).
Qt model creation is delegated to the view/controller layer.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from oncutf.ui.widgets.metadata_tree.model import (
    EXTENDED_ONLY_PATTERNS,
    FieldStatus,
    MetadataDisplayState,
    NodeType,
    TreeNodeData,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.metadata import MetadataStagingManager

logger = get_cached_logger(__name__)


class MetadataTreeService:
    """Service layer for metadata tree operations.

    This class handles all business logic related to metadata processing:
    - Classifying keys into groups (File Info, Camera Settings, GPS, etc.)
    - Formatting keys for display (ImageSensorType -> Image Sensor Type)
    - Detecting modified and extended metadata keys
    - Building TreeNodeData hierarchies (pure data structures)
    - Applying staged changes from the staging manager

    This service is Qt-free - it works with pure Python data structures.
    Qt model creation is delegated to the view/controller layer.

    Usage:
        service = MetadataTreeService()
        tree_data = service.build_tree_data(metadata, display_state)
    """

    def __init__(self) -> None:
        """Initialize the service."""
        self._staging_manager: MetadataStagingManager | None = None

    def set_staging_manager(self, manager: MetadataStagingManager) -> None:
        """Set the staging manager for modification tracking."""
        self._staging_manager = manager

    def format_key(self, key: str) -> str:
        """Convert camelCase/PascalCase keys to readable format.

        Examples:
            'ImageSensorType' -> 'Image Sensor Type'
            'GPSLatitude' -> 'GPS Latitude'
            'ISOSpeed' -> 'ISO Speed'

        Args:
            key: The metadata key to format

        Returns:
            Human-readable formatted key

        """
        return re.sub(r"(?<!^)(?=[A-Z])", " ", key)

    def classify_key(self, key: str) -> str:
        """Classify a metadata key into a detailed group label.

        Groups metadata into logical categories for better organization:
        - File Info: File-related metadata (filename, directory, rotation)
        - Camera Settings: Photography settings (ISO, aperture, shutter, exposure)
        - GPS & Location: Geographic data
        - Sensor Data: Accelerometer, gyroscope, orientation
        - Audio Info: Audio metadata
        - Image Info: Image dimensions, resolution, color space
        - Video Info: Video codec, frame rate, duration
        - Color & Processing: Color adjustments, curves, saturation
        - Lens Info: Lens model, focal length, distortion
        - Copyright & Rights: Legal and ownership information
        - Technical Info: Device information, software versions
        - Other: Everything else

        Args:
            key: The metadata key to classify

        Returns:
            Group label for the key

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
        gps_terms = ["gps", "location", "latitude", "longitude", "altitude"]
        if any(term in key_lower for term in gps_terms):
            return "GPS & Location"

        # Sensor Data (accelerometer, gyroscope, etc.)
        if any(
            term in key_lower
            for term in [
                "accelerometer",
                "gyro",
                "pitch",
                "roll",
                "yaw",
                "rotation",
                "orientation",
                "gravity",
                "magnetometer",
                "compass",
            ]
        ):
            return "Sensor Data"

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
        image_terms = ["width", "height", "resolution", "dpi", "colorspace"]
        if (
            key_lower.startswith("image")
            or "sensor" in key_lower
            or any(term in key_lower for term in image_terms)
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

        # Color and Processing
        if any(
            term in key_lower
            for term in [
                "color",
                "saturation",
                "contrast",
                "brightness",
                "hue",
                "gamma",
                "curve",
                "tone",
                "highlight",
                "shadow",
                "vibrance",
            ]
        ):
            return "Color & Processing"

        # Lens Information
        if any(
            term in key_lower
            for term in ["lens", "zoom", "focus", "distortion", "vignetting", "chromatic"]
        ):
            return "Lens Info"

        # Copyright and Rights
        if any(
            term in key_lower
            for term in ["copyright", "rights", "creator", "owner", "license", "usage"]
        ):
            return "Copyright & Rights"

        # Technical/System
        if any(
            term in key_lower
            for term in ["version", "software", "firmware", "make", "model", "serial", "uuid", "id"]
        ):
            return "Technical Info"

        # Everything else
        return "Other"

    def build_tree_data(
        self,
        metadata: dict[str, Any],
        display_state: MetadataDisplayState,
    ) -> TreeNodeData:
        """Build a TreeNodeData hierarchy from metadata.

        This is the main entry point for converting raw metadata into
        a structured tree representation. Returns pure data structures
        with no Qt dependencies.

        Args:
            metadata: Raw metadata dictionary
            display_state: Current display state with modifications

        Returns:
            Root TreeNodeData node with full hierarchy

        """
        logger.debug(
            "[MetadataTreeService] Building tree data for file: %s",
            display_state.file_path,
            extra={"dev_only": True},
        )

        # Prepare metadata with staged changes applied
        display_data = self._prepare_display_data(metadata, display_state)

        # Detect extended-only keys
        extended_keys = self._detect_extended_keys(metadata, display_state)

        # Build the tree structure
        root = self._build_tree_hierarchy(display_data, display_state.modified_keys, extended_keys)

        logger.debug(
            "[MetadataTreeService] Tree data built: %d groups",
            len(root.children),
            extra={"dev_only": True},
        )

        return root

    def _build_tree_hierarchy(
        self,
        metadata: dict[str, Any],
        modified_keys: set[str],
        extended_keys: set[str],
    ) -> TreeNodeData:
        """Build the tree hierarchy from metadata.

        Args:
            metadata: Processed metadata dictionary
            modified_keys: Set of modified key paths
            extended_keys: Set of extended-only keys

        Returns:
            Root TreeNodeData with children

        """
        root = TreeNodeData(
            key="root",
            node_type=NodeType.ROOT,
        )

        # Group metadata by classification
        grouped: dict[str, list[tuple[str, Any]]] = {}
        for key, value in metadata.items():
            # Skip internal markers
            if key.startswith("__"):
                continue

            group = self.classify_key(key)
            grouped.setdefault(group, []).append((key, value))

        # Sort groups with File Info first, Other last
        def group_sort_key(group_name: str) -> tuple[int, str]:
            if group_name == "File Info":
                return (0, "File Info")
            elif group_name == "Other":
                return (2, group_name)
            else:
                return (1, group_name)

        ordered_groups = sorted(grouped.keys(), key=group_sort_key)

        # Build group nodes
        for group_name in ordered_groups:
            items = grouped[group_name]

            # Sort items alphabetically within each group
            items.sort(key=lambda item: item[0].lower())

            # Create group node
            group_node = TreeNodeData(
                key=group_name,
                value=f"({len(items)} fields)",
                node_type=NodeType.GROUP,
            )

            # Add field nodes to group
            for key, value in items:
                field_status = self._determine_field_status(
                    key, group_name, modified_keys, extended_keys
                )

                field_node = TreeNodeData(
                    key=key,
                    value=str(value),
                    node_type=NodeType.FIELD,
                    status=field_status,
                )

                group_node.add_child(field_node)

            root.add_child(group_node)

        return root

    def _determine_field_status(
        self,
        key: str,
        group_name: str,
        modified_keys: set[str],
        extended_keys: set[str],
    ) -> FieldStatus:
        """Determine the status of a field based on modifications and extensions.

        Args:
            key: The field key
            group_name: The group the field belongs to
            modified_keys: Set of modified key paths
            extended_keys: Set of extended-only keys

        Returns:
            FieldStatus enum value

        """
        # Check for modification
        # We check multiple patterns to handle different key path formats:
        # - "Group/Key" (e.g., "EXIF/Rotation")
        # - Just "Key" (e.g., "Rotation")
        # - Any path ending with "/Key"
        key_path = f"{group_name}/{key}"
        direct_match = key_path in modified_keys or key in modified_keys
        suffix_match = any(mk.endswith(f"/{key}") or mk == key for mk in modified_keys)
        is_modified = direct_match or suffix_match

        # Check for extended
        is_extended = key in extended_keys

        # Determine status
        if is_modified:
            return FieldStatus.MODIFIED
        elif is_extended:
            return FieldStatus.EXTENDED
        else:
            return FieldStatus.NORMAL

    def _prepare_display_data(
        self,
        metadata: dict[str, Any],
        display_state: MetadataDisplayState,
    ) -> dict[str, Any]:
        """Prepare metadata for display by applying staged changes.

        Args:
            metadata: Raw metadata from file
            display_state: Current state with modifications

        Returns:
            Display-ready metadata dictionary

        """
        display_data = dict(metadata)

        # Preserve filename if present
        filename = metadata.get("FileName")
        if filename:
            display_data["FileName"] = filename

        # Apply staged changes from staging manager
        if self._staging_manager and display_state.file_path:
            staged_changes = self._staging_manager.get_staged_changes(display_state.file_path)

            logger.info(
                "[MetadataTreeService] Applying staged changes for %s: %s",
                display_state.file_path,
                staged_changes,
            )

            for key_path, value in staged_changes.items():
                self._apply_staged_change(display_data, key_path, value)

            # Update modified keys in display state
            display_state.modified_keys = set(staged_changes.keys())
        else:
            logger.info(
                "[MetadataTreeService] No staging manager (%s) or file_path (%s)",
                self._staging_manager is not None,
                display_state.file_path,
            )

        # Cleanup empty groups
        self._cleanup_empty_groups(display_data, display_state)

        return display_data

    def _apply_staged_change(
        self,
        display_data: dict[str, Any],
        key_path: str,
        value: str,
    ) -> None:
        """Apply a staged change to display data.

        Args:
            display_data: The metadata dictionary to modify
            key_path: Path to the field (e.g., "EXIF/Title" or "Rotation")
            value: The new value

        """
        # Special handling for rotation - it's always top-level
        if key_path.lower() == "rotation":
            display_data["Rotation"] = value
            return

        # Handle other fields normally
        parts = key_path.split("/")

        if len(parts) == 1:
            # Top-level key
            display_data[parts[0]] = value
        elif len(parts) == 2:
            # Nested key (group/key)
            group, key = parts
            if group not in display_data or not isinstance(display_data[group], dict):
                display_data[group] = {}
            display_data[group][key] = value

    def _cleanup_empty_groups(
        self,
        display_data: dict[str, Any],
        display_state: MetadataDisplayState,
    ) -> None:
        """Remove empty groups from display data.

        Preserves groups that have modified items even if currently empty.

        Args:
            display_data: Metadata dictionary to clean
            display_state: Current state (for modification tracking)

        """
        groups_with_modifications = set()

        # Find groups with staged modifications
        for key_path in display_state.modified_keys:
            if "/" in key_path:
                group_name = key_path.split("/")[0]
                groups_with_modifications.add(group_name)

        # Remove empty groups (except those with modifications)
        empty_groups = []
        for group_name, group_data in display_data.items():
            if isinstance(group_data, dict) and len(group_data) == 0:
                if group_name not in groups_with_modifications:
                    empty_groups.append(group_name)

        for group_name in empty_groups:
            display_data.pop(group_name, None)

    def _detect_extended_keys(
        self,
        metadata: dict[str, Any],
        display_state: MetadataDisplayState,
    ) -> set[str]:
        """Detect which keys are extended-only metadata.

        Args:
            metadata: Raw metadata
            display_state: Current state with is_extended_metadata flag

        Returns:
            Set of keys that are extended-only

        """
        extended_keys = set(display_state.extended_keys)

        # If metadata was loaded in extended mode, detect extended-only keys
        if display_state.is_extended_metadata or metadata.get("__extended__"):
            # Use heuristic based on key patterns
            for key in metadata:
                key_lower = key.lower()
                if any(pattern in key_lower for pattern in EXTENDED_ONLY_PATTERNS):
                    extended_keys.add(key)

        return extended_keys

    def get_modification_count(self, display_state: MetadataDisplayState) -> int:
        """Get the number of modified fields.

        Args:
            display_state: Current display state

        Returns:
            Count of modified fields

        """
        return display_state.modification_count

    def get_field_count(self, metadata: dict[str, Any]) -> int:
        """Count total fields in metadata (including nested).

        Args:
            metadata: Metadata dictionary

        Returns:
            Total field count

        """
        total_fields = 0

        def count_fields(data: dict) -> None:
            nonlocal total_fields
            for _key, value in data.items():
                if isinstance(value, dict):
                    count_fields(value)
                else:
                    total_fields += 1

        count_fields(metadata)
        return total_fields


def create_metadata_tree_service() -> MetadataTreeService:
    """Factory function to create a configured MetadataTreeService.

    Returns:
        Configured service instance

    """
    service = MetadataTreeService()

    # Try to inject staging manager if available
    try:
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()
        if staging_manager:
            service.set_staging_manager(staging_manager)
    except ImportError:
        logger.debug(
            "[MetadataTreeService] Staging manager not available",
            extra={"dev_only": True},
        )

    return service
