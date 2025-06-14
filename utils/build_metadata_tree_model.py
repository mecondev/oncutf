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

    if key_lower.startswith("file"):
        return "File Info"
    elif key_lower.startswith("audio") or key_lower in {"samplerate", "channelmode", "bitrate"}:
        return "Audio Info"
    elif key_lower in {"title", "album", "artist", "composer", "genre"}:
        return "ID3 Tags"
    elif key_lower.startswith("image") or "sensor" in key_lower:
        return "Image Info"
    else:
        return "Other"


def create_item(text: str, alignment: Qt.AlignmentFlag = Qt.AlignLeft) -> QStandardItem:
    """Create a QStandardItem with given text and alignment."""
    item = QStandardItem(text)
    item.setTextAlignment(Qt.Alignment(alignment))
    return item


def build_metadata_tree_model(metadata: dict) -> QStandardItemModel:
    logger.debug(">>> build_metadata_tree_model called")
    logger.debug(f"metadata type: {type(metadata)} | keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'N/A'}", extra={"dev_only": True})

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
            group_item.appendRow([key_item, value_item])

        root_item.appendRow([group_item, dummy_value_item])

    return model
