"""
utils/build_metadata_tree_model.py

Author: Michael Economou
Date: 2025-05-09

Provides a utility function for converting nested metadata
(dicts/lists) into a QStandardItemModel suitable for display in a QTreeView.
"""

import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QStandardItem, QStandardItemModel

# Initialize Logger
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)



def format_key(key: str) -> str:
    """Convert 'ImageSensorType' → 'Image Sensor Type'."""
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', key)


def classify_key(key: str) -> str:
    """Classify a metadata key into a group label."""
    key_lower = key.lower()

    # File-related metadata
    if key_lower.startswith("file") or key_lower in {"rotation"}:
        return "File Info"

    # Media-specific metadata
    if (key_lower.startswith("audio") or
        key_lower in {"samplerate", "channelmode", "bitrate", "title", "album", "artist", "composer", "genre"}):
        return "Audio Info"

    # Image-specific metadata
    if key_lower.startswith("image") or "sensor" in key_lower:
        return "Image Info"

    # Everything else
    return "Other"


def create_item(text: str, alignment: Qt.AlignmentFlag = Qt.AlignLeft) -> QStandardItem:
    """Create a QStandardItem with given text and alignment."""
    item = QStandardItem(text)
    item.setTextAlignment(Qt.Alignment(alignment))
    return item


def build_metadata_tree_model(metadata: dict, modified_keys: set = None) -> QStandardItemModel:
    logger.debug(">>> build_metadata_tree_model called", extra={"dev_only": True})
    logger.debug(f"metadata type: {type(metadata)} | keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'N/A'}", extra={"dev_only": True})

    if modified_keys is None:
        modified_keys = set()

    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["Key", "Value"])
    root_item = model.invisibleRootItem()

    grouped = {}

    for key, value in metadata.items():
        group = classify_key(key)
        grouped.setdefault(group, []).append((key, value))

    ordered_groups = sorted(grouped.keys(), key=lambda x: (x == "Other", x.lower()))

    for group_name in ordered_groups:
        items = grouped[group_name]
        logger.debug(f"Creating group: {group_name} with {len(items)} items", extra={"dev_only": True})
        group_item = QStandardItem(group_name)
        group_item.setEditable(False)
        group_item.setSelectable(False)

        # Set font with specific size and bold weight for cross-platform consistency
        group_font = QFont()
        group_font.setBold(True)
        group_font.setPointSize(10)  # Explicit size for consistency across platforms
        group_item.setFont(group_font)

        dummy_value_item = QStandardItem("")  # empty second column
        dummy_value_item.setSelectable(False)

        for key, value in items:
            key_item = create_item(format_key(key))
            value_item = create_item(str(value))

            # Check if this key is modified and apply italic style
            key_path = f"{group_name}/{key}"
            if key_path in modified_keys or key in modified_keys:
                # Apply italic style to both key and value for modified items
                italic_font = QFont()
                italic_font.setItalic(True)
                key_item.setFont(italic_font)
                value_item.setFont(italic_font)
                # Optionally, add a tooltip to indicate it's modified
                key_item.setToolTip("Modified value")
                value_item.setToolTip("Modified value")

            group_item.appendRow([key_item, value_item])

        root_item.appendRow([group_item, dummy_value_item])

    return model
