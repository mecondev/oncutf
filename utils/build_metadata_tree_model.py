"""
Module: build_metadata_tree_model.py

Author: Michael Economou
Date: 2025-05-31

utils/build_metadata_tree_model.py
Provides a utility function for converting nested metadata
(dicts/lists) into a QStandardItemModel suitable for display in a QTreeView.
Enhanced with better metadata grouping and extended metadata indicators.
"""
import re

from core.qt_imports import Qt, QColor, QFont, QStandardItem, QStandardItemModel

# Initialize Logger
from utils.logger_factory import get_cached_logger
from utils.tooltip_helper import setup_tooltip, TooltipType

logger = get_cached_logger(__name__)


def format_key(key: str) -> str:
    """Convert 'ImageSensorType' → 'Image Sensor Type'."""
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', key)


def classify_key(key: str) -> str:
    """
    Classify a metadata key into a detailed group label.
    Enhanced grouping for better organization of metadata.
    """
    key_lower = key.lower()

    # File-related metadata
    if (key_lower.startswith("file") or key_lower in {"rotation", "directory", "sourcefile"}):
        return "File Info"

    # Camera Settings - Critical for photography/videography
    if any(term in key_lower for term in [
        'iso', 'aperture', 'fnumber', 'shutter', 'exposure', 'focal', 'flash',
        'metering', 'whitebalance', 'gain', 'lightvalue'
    ]):
        return "Camera Settings"

    # GPS and Location
    if any(term in key_lower for term in ['gps', 'location', 'latitude', 'longitude', 'altitude']):
        return "GPS & Location"

    # Sensor Data (accelerometer, gyroscope, etc.)
    if any(term in key_lower for term in [
        'accelerometer', 'gyro', 'pitch', 'roll', 'yaw', 'rotation', 'orientation',
        'gravity', 'magnetometer', 'compass'
    ]):
        return "Sensor Data"

    # Audio-related metadata
    if (key_lower.startswith("audio") or
        key_lower in {"samplerate", "channelmode", "bitrate", "title", "album", "artist", "composer", "genre", "duration"}):
        return "Audio Info"

    # Image-specific metadata
    if (key_lower.startswith("image") or "sensor" in key_lower or
        any(term in key_lower for term in ['width', 'height', 'resolution', 'dpi', 'colorspace'])):
        return "Image Info"

    # Video-specific metadata
    if any(term in key_lower for term in [
        'video', 'frame', 'codec', 'bitrate', 'fps', 'duration', 'format',
        'avgbitrate', 'maxbitrate', 'videocodec'
    ]):
        return "Video Info"

    # Color and Processing
    if any(term in key_lower for term in [
        'color', 'saturation', 'contrast', 'brightness', 'hue', 'gamma',
        'curve', 'tone', 'highlight', 'shadow', 'vibrance'
    ]):
        return "Color & Processing"

    # Lens Information
    if any(term in key_lower for term in [
        'lens', 'zoom', 'focus', 'distortion', 'vignetting', 'chromatic'
    ]):
        return "Lens Info"

    # Copyright and Rights
    if any(term in key_lower for term in [
        'copyright', 'rights', 'creator', 'owner', 'license', 'usage'
    ]):
        return "Copyright & Rights"

    # Technical/System
    if any(term in key_lower for term in [
        'version', 'software', 'firmware', 'make', 'model',
        'serial', 'uuid', 'id'
    ]):
        return "Technical Info"

    # Everything else
    return "Other"


def create_item(text: str, alignment = None) -> QStandardItem:
    """Create a QStandardItem with given text and alignment."""
    item = QStandardItem(text)
    if alignment is None:
        alignment = Qt.AlignLeft
    item.setTextAlignment(Qt.Alignment(alignment))
    return item


def build_metadata_tree_model(metadata: dict, modified_keys: set = None, extended_keys: set = None) -> QStandardItemModel:
    """
    Build a tree model for metadata display with enhanced grouping and extended metadata indicators.

    Args:
        metadata: Dictionary containing metadata
        modified_keys: Set of keys that have been modified
        extended_keys: Set of keys that are only available in extended metadata mode
    """
    logger.debug(">>> build_metadata_tree_model called", extra={"dev_only": True})
    logger.debug(f"metadata type: {type(metadata)} | keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'N/A'}", extra={"dev_only": True})

    if modified_keys is None:
        modified_keys = set()
    if extended_keys is None:
        extended_keys = set()

    # ExifTool-specific fields that should be hidden from the metadata tree
    exiftool_hidden_fields = {
        'ExifToolVersion',
        'Directory',
        'SourceFile',
        'FileName',  # Hide ExifTool FileName - we use our own
        'FileSize',  # Hide ExifTool FileSize - we have our own
        'FileModifyDate',  # Hide ExifTool FileModifyDate - we have our own
        'FileAccessDate',
        'FileInodeChangeDate',
        'FilePermissions',
        'FileType',  # Can be hidden if we have our own Type
        'FileTypeExtension',
        'MIMEType'
    }

    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["Key", "Value"])
    root_item = model.invisibleRootItem()

    grouped = {}

    for key, value in metadata.items():
        # Skip internal markers
        if key.startswith("__"):
            continue

        # Skip ExifTool-specific fields
        if key in exiftool_hidden_fields:
            logger.debug(f"Skipping ExifTool field: {key}", extra={"dev_only": True})
            continue

        group = classify_key(key)
        grouped.setdefault(group, []).append((key, value))

    # Sort groups with File Info first, then alphabetically
    def group_sort_key(group_name):
        if group_name == "File Info":
            return (0, "File Info")  # Always first
        elif group_name == "Other":
            return (2, group_name)  # Always last
        else:
            return (1, group_name)  # Alphabetical order for everything else

    ordered_groups = sorted(grouped.keys(), key=group_sort_key)

    for group_name in ordered_groups:
        items = grouped[group_name]
        logger.debug(f"Creating group: {group_name} with {len(items)} items", extra={"dev_only": True})

        # Check if this group has extended metadata
        group_has_extended = any(key in extended_keys for key, _ in items)

        # Create group item with enhanced styling
        if group_has_extended:
            display_name = f"{group_name} [Extended] ({len(items)})"
        else:
            display_name = f"{group_name} ({len(items)})"

        group_item = QStandardItem(display_name)
        group_item.setEditable(False)
        group_item.setSelectable(False)

        # Set font with specific size and bold weight for cross-platform consistency
        group_font = QFont()
        group_font.setBold(True)
        group_font.setPointSize(10)
        group_item.setFont(group_font)

        # Add tooltip for extended groups using Qt's native tooltip system
        # Note: We use setToolTip() instead of our custom tooltip system
        # because QStandardItem is not a QWidget and doesn't support our tooltip system
        if group_has_extended:
            extended_count = sum(1 for key, _ in items if key in extended_keys)
            group_item.setToolTip(f"Contains {extended_count} keys from extended metadata")

        dummy_value_item = QStandardItem("")  # empty second column
        dummy_value_item.setSelectable(False)

        for key, value in items:
            key_item = create_item(format_key(key))
            value_item = create_item(str(value))

            # Apply styling based on key type
            is_modified = key_path in modified_keys or key in modified_keys if (key_path := f"{group_name}/{key}") else key in modified_keys
            is_extended = key in extended_keys

            if is_extended:
                # Extended metadata styling - subtle blue tint
                extended_font = QFont()
                extended_font.setItalic(True)
                key_item.setFont(extended_font)
                value_item.setFont(extended_font)

                # Add extended indicator to key name
                key_item.setText(f"[Ext] {format_key(key)}")
                key_item.setToolTip("Available only in extended metadata mode")
                value_item.setToolTip("Available only in extended metadata mode")

                # Set text color to indicate extended metadata
                extended_color = QColor(100, 150, 255)  # Light blue
                key_item.setForeground(extended_color)

            if is_modified:
                # Modified metadata styling - italic and bold
                modified_font = QFont()
                modified_font.setItalic(True)
                modified_font.setBold(True)
                key_item.setFont(modified_font)
                value_item.setFont(modified_font)

                # Add modified indicator if not already extended
                if not is_extended:
                    key_item.setText(f"[Mod] {format_key(key)}")
                else:
                    key_item.setText(f"[Ext][Mod] {format_key(key)}")

                key_item.setToolTip("Modified value" + (" (extended metadata)" if is_extended else ""))
                value_item.setToolTip("Modified value" + (" (extended metadata)" if is_extended else ""))

            group_item.appendRow([key_item, value_item])

        root_item.appendRow([group_item, dummy_value_item])

    return model
