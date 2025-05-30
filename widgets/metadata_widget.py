"""
Module: metadata_widget.py

Author: Michael Economou
Date: 2025-05-04

This module defines a QWidget-based UI for the metadata rename module that allows
selecting a metadata field (such as creation date, modification date, or EXIF tag)
to include in the renamed filename.

Features two-level selection:
1. Category selection (File Dates vs EXIF/Metadata)
2. Dynamic options based on category
"""

from typing import Optional, Set
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout
from PyQt5.QtCore import pyqtSignal, QTimer
from utils.logger_helper import get_logger
from utils.metadata_cache import MetadataEntry

logger = get_logger(__name__)


class MetadataWidget(QWidget):
    """
    A widget that allows the user to select a metadata field to include in the filename.
    Uses a two-level selection system for better organization.
    """

    updated = pyqtSignal(object)  # Emitted when selection changes

    def __init__(self, parent: Optional[QWidget] = None, parent_window: Optional[QWidget] = None) -> None:
        """
        Initializes the MetadataWidget.

        :param parent: Optional parent widget
        :param parent_window: Reference to main window for metadata cache access
        """
        super().__init__(parent)
        self.parent_window = parent_window
        self.setProperty("module", True)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Row 1: Category Selection
        category_row = QHBoxLayout()
        category_label = QLabel("Category:")
        category_label.setFixedWidth(80)

        self.category_combo = QComboBox()
        self.category_combo.addItem("File Dates", userData="file_dates")
        self.category_combo.addItem("EXIF/Metadata", userData="metadata_keys")
        self.category_combo.setFixedWidth(120)

        category_row.addWidget(category_label)
        category_row.addWidget(self.category_combo)
        category_row.addStretch()
        layout.addLayout(category_row)

        # Row 2: Options Selection (Dynamic)
        options_row = QHBoxLayout()
        options_label = QLabel("Field:")
        options_label.setFixedWidth(80)

        self.options_combo = QComboBox()
        self.options_combo.setFixedWidth(200)

        options_row.addWidget(options_label)
        options_row.addWidget(self.options_combo)
        options_row.addStretch()
        layout.addLayout(options_row)

        # Connect signals
        self.category_combo.currentIndexChanged.connect(self.update_options)
        self.options_combo.currentIndexChanged.connect(lambda _: self.updated.emit(self))

        # Initialize with default category
        QTimer.singleShot(0, self.update_options)
        QTimer.singleShot(10, lambda: self.updated.emit(self))

    def update_options(self) -> None:
        """Updates the options combo based on selected category."""
        category = self.category_combo.currentData()
        logger.debug(f"[MetadataWidget] Updating options for category: {category}")

        self.options_combo.clear()

        if category == "file_dates":
            self.populate_file_dates()
        elif category == "metadata_keys":
            self.populate_metadata_keys()

        # Emit update signal after populating
        self.updated.emit(self)

    def populate_file_dates(self) -> None:
        """Populates file date options."""
        file_date_options = [
            ("Last Modified (YYMMDD)", "last_modified_yymmdd"),
            ("Last Modified (YYYY-MM-DD)", "last_modified_iso"),
            ("Last Modified (DD/MM/YYYY)", "last_modified_eu"),
            ("Last Modified (MM-DD-YYYY)", "last_modified_us"),
            ("Last Modified (YYYY)", "last_modified_year"),
            ("Last Modified (YYYY-MM)", "last_modified_month"),
        ]

        for display_name, data_value in file_date_options:
            self.options_combo.addItem(display_name, userData=data_value)

        logger.debug(f"[MetadataWidget] Populated {len(file_date_options)} file date options")

    def populate_metadata_keys(self) -> None:
        """Populates metadata key options from available files."""
        available_keys = self.get_available_metadata_keys()

        if not available_keys:
            self.options_combo.addItem("(No metadata loaded)", userData=None)
            logger.info("[MetadataWidget] No metadata keys available")
            return

        # Add each available metadata key
        for key in sorted(available_keys):
            # Create user-friendly display name
            display_name = self.format_metadata_key_name(key)
            self.options_combo.addItem(display_name, userData=key)

        logger.debug(f"[MetadataWidget] Populated {len(available_keys)} metadata keys")

    def get_available_metadata_keys(self) -> Set[str]:
        """Collects all unique metadata keys from loaded files."""
        if not self.parent_window or not hasattr(self.parent_window, 'metadata_cache'):
            logger.warning("[MetadataWidget] No access to metadata cache")
            return set()

        all_keys = set()
        cache = self.parent_window.metadata_cache._cache

        for entry in cache.values():
            if isinstance(entry, MetadataEntry) and entry.data:
                # Filter out internal/system keys
                filtered_keys = {
                    k for k in entry.data.keys()
                    if not k.startswith('_') and k not in ['path', 'filename']
                }
                all_keys.update(filtered_keys)

        logger.debug(f"[MetadataWidget] Found {len(all_keys)} unique metadata keys")
        return all_keys

    def format_metadata_key_name(self, key: str) -> str:
        """Formats a metadata key for user-friendly display."""
        # Convert snake_case to Title Case
        formatted = key.replace('_', ' ').title()

        # Handle common EXIF abbreviations
        replacements = {
            'Exif': 'EXIF',
            'Gps': 'GPS',
            'Iso': 'ISO',
            'Rgb': 'RGB',
            'Dpi': 'DPI',
            'Cm': 'cm',
            'Mm': 'mm',
        }

        for old, new in replacements.items():
            formatted = formatted.replace(old, new)

        return formatted

    def get_data(self) -> dict:
        """
        Returns selected metadata info as dictionary for preview/generation.

        :return: Dict with metadata field type and category info
        """
        category = self.category_combo.currentData() or "file_dates"
        field = self.options_combo.currentData() or "last_modified_yymmdd"

        return {
            "type": "metadata",
            "category": category,
            "field": field
        }
