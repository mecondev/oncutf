"""Metadata Widget V2 - Composition-based implementation.

This widget provides the UI for metadata-based renaming using composition
instead of inheritance to avoid QSS and event propagation conflicts.

Author: Michael Economou
Date: 2025-01-27
"""

from typing import Optional

from core.pyqt_imports import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QStandardItem,
    QStandardItemModel,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
    Qt,
)
from modules.metadata_module import MetadataModule
from utils.logger_factory import get_cached_logger
from widgets.hierarchical_combo_box import HierarchicalComboBox

logger = get_cached_logger(__name__)


class MetadataWidgetV2(QWidget):
    """Metadata widget using composition pattern.
    
    This widget creates its own clean UI without inheriting from RenameModuleWidget,
    avoiding styling and event conflicts.
    """
    
    # Signals
    updated = pyqtSignal(object)  # For compatibility with existing code
    
    def __init__(self, parent: Optional[QWidget] = None, parent_window=None) -> None:
        """Initialize the metadata widget."""
        super().__init__(parent)
        
        # Store parent window for compatibility (currently unused in V2)
        self.parent_window = parent_window
        
        # Create the metadata module (composition, not inheritance)
        self.metadata_module = MetadataModule()
        
        # UI components
        self.category_combo: Optional[QComboBox] = None
        self.options_combo: Optional[HierarchicalComboBox] = None
        self.options_label: Optional[QLabel] = None
        
        # Setup the UI
        self._setup_ui()
        self._setup_connections()
        
        # Initialize with first category selected
        if self.category_combo and self.category_combo.count() > 0:
            self.category_combo.setCurrentIndex(0)
            self._update_options()
        
        logger.debug("[MetadataWidgetV2] Widget initialized")
    
    def _setup_ui(self) -> None:
        """Setup the widget UI with correct spacing like other modules."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # Match other modules spacing
        
        # Row 1: Category
        category_row = QHBoxLayout()
        category_row.setContentsMargins(0, 0, 0, 0)
        category_row.setSpacing(8)
        
        category_label = QLabel("Category")
        category_label.setFixedWidth(70)
        category_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.category_combo = QComboBox()
        self.category_combo.setFixedWidth(150)
        self.category_combo.setFixedHeight(24)
        logger.debug("[MetadataWidgetV2] Category combo created")
        
        category_row.addWidget(category_label)
        category_row.addWidget(self.category_combo)
        category_row.addStretch()
        layout.addLayout(category_row)
        
        # Row 2: Field
        options_row = QHBoxLayout()
        options_row.setContentsMargins(0, 0, 0, 0)
        options_row.setSpacing(8)
        
        self.options_label = QLabel("Field")
        self.options_label.setFixedWidth(70)
        self.options_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.options_combo = HierarchicalComboBox()
        self.options_combo.setFixedWidth(200)
        self.options_combo.setFixedHeight(24)
        self.options_combo.setEnabled(False)  # Disabled until category is selected
        
        options_row.addWidget(self.options_label)
        options_row.addWidget(self.options_combo)
        options_row.addStretch()
        layout.addLayout(options_row)
        
        self.setLayout(layout)
        
        # Populate categories after UI is fully set up
        self._populate_categories()
    
    def _setup_connections(self) -> None:
        """Setup signal connections."""
        if self.category_combo:
            self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        
        if self.options_combo:
            self.options_combo.item_selected.connect(self._on_hierarchical_item_selected)
    
    def _populate_categories(self) -> None:
        """Populate the category combo box with dynamic categories."""
        logger.debug(f"[MetadataWidgetV2] _populate_categories called, combo is: {self.category_combo}")
        if not self.category_combo:
            logger.warning("[MetadataWidgetV2] Category combo is None!")
            return
        
        # Clear existing items first
        self.category_combo.clear()
        
        # Add categories directly to combo box (simpler approach)
        self.category_combo.addItem("File Date/Time", "file_dates")
        self.category_combo.addItem("Hash", "hash")
        self.category_combo.addItem("EXIF/Metadata", "metadata_keys")
        
        logger.debug(f"[MetadataWidgetV2] Populated {self.category_combo.count()} categories")
    
    def _on_category_changed(self) -> None:
        """Handle category selection change."""
        current_data = self.category_combo.currentData()
        logger.debug(f"[MetadataWidgetV2] Category changed to: {current_data}")
        
        if current_data is None:
            return
        
        # Clear and update options
        self.options_combo.clear()
        self._update_options()
        
        # Emit update signal for compatibility
        self.updated.emit(self)
    
    def _update_options(self) -> None:
        """Update options based on selected category."""
        category = self.category_combo.currentData()
        self.options_combo.clear()
        
        logger.debug(f"[MetadataWidgetV2] update_options called with category: {category}")
        
        if category == "file_dates":
            self.options_label.setText("Type")
            self._populate_file_dates()
            self.options_combo.setEnabled(True)
        elif category == "hash":
            self.options_label.setText("Type")
            self._populate_hash_options()
            # Hash combo is always disabled for now (like original)
            self.options_combo.setEnabled(False)
        elif category == "metadata_keys":
            self.options_label.setText("Field")
            self._populate_metadata_keys()
            self.options_combo.setEnabled(True)
    
    def _populate_file_dates(self) -> None:
        """Populate file date options."""
        hierarchical_data = {
            "File Date/Time": [
                ("Last Modified (YYMMDD)", "last_modified_yymmdd"),
                ("Last Modified (YYYY-MM-DD)", "last_modified_iso"),
                ("Last Modified (DD-MM-YYYY)", "last_modified_eu"),
                ("Last Modified (MM-DD-YYYY)", "last_modified_us"),
                ("Last Modified (YYYY)", "last_modified_year"),
                ("Last Modified (YYYY-MM)", "last_modified_month"),
                ("Last Modified (YYYY-MM-DD HH-MM)", "last_modified_iso_time"),
                ("Last Modified (DD-MM-YYYY HH-MM)", "last_modified_eu_time"),
                ("Last Modified (YYMMDD_HHMM)", "last_modified_compact"),
            ]
        }
        
        self.options_combo.populate_from_metadata_groups(hierarchical_data)
        logger.debug("[MetadataWidgetV2] Populated file dates")
    
    def _populate_hash_options(self) -> None:
        """Populate hash options (always disabled like original)."""
        hierarchical_data = {
            "Hash Types": [
                ("CRC32", "hash_crc32"),
            ]
        }
        
        self.options_combo.populate_from_metadata_groups(hierarchical_data)
        logger.debug("[MetadataWidgetV2] Populated hash options (disabled)")
    
    def _populate_metadata_keys(self) -> None:
        """Populate EXIF/metadata options."""
        # Use simplified EXIF categories for now
        hierarchical_data = {
            "Camera Settings": [
                ("ISO Speed", "ISOSpeedRatings"),
                ("Aperture", "FNumber"),
                ("Shutter Speed", "ExposureTime"),
                ("Focal Length", "FocalLength"),
                ("Flash", "Flash"),
                ("White Balance", "WhiteBalance"),
            ],
            "Image Info": [
                ("Image Width", "ImageWidth"),
                ("Image Height", "ImageHeight"),
                ("Orientation", "Orientation"),
                ("Color Space", "ColorSpace"),
            ],
            "Camera Info": [
                ("Camera Make", "Make"),
                ("Camera Model", "Model"),
                ("Lens Model", "LensModel"),
            ],
            "Date/Time": [
                ("DateTime Original", "DateTimeOriginal"),
                ("DateTime Digitized", "DateTimeDigitized"),
            ],
            "GPS & Location": [
                ("GPS Latitude", "GPSLatitude"),
                ("GPS Longitude", "GPSLongitude"),
                ("GPS Altitude", "GPSAltitude"),
            ]
        }
        
        self.options_combo.populate_from_metadata_groups(hierarchical_data)
        logger.debug("[MetadataWidgetV2] Populated metadata keys")
    
    def _on_hierarchical_item_selected(self, item_data) -> None:
        """Handle hierarchical combo box item selection."""
        logger.debug(f"[MetadataWidgetV2] Hierarchical item selected: {item_data}")
        
        # Update the module selection
        category = self.category_combo.currentData()
        if category and item_data:
            # Map the selection to our module
            self.metadata_module.selected_category = self._map_category_to_module(category)
            self.metadata_module.selected_field = self._map_field_to_module(item_data)
        
        # Emit update signal for compatibility
        self.updated.emit(self)
    
    def _map_category_to_module(self, category: str) -> str:
        """Map UI category to module category."""
        mapping = {
            "file_dates": "Modified Date",
            "hash": "Hash",
            "metadata_keys": "EXIF"
        }
        return mapping.get(category, "")
    
    def _map_field_to_module(self, field: str) -> str:
        """Map UI field to module field."""
        # For now, use the field as-is
        # This could be extended with more complex mapping
        return field
    
    def get_module_name(self) -> str:
        """Get the module name."""
        return self.metadata_module.module_name
    
    def get_configuration_summary(self) -> str:
        """Get a summary of the current configuration."""
        return self.metadata_module.get_configuration_summary()
    
    def is_configuration_valid(self) -> bool:
        """Check if the current configuration is valid."""
        return self.metadata_module.validate_configuration()
    
    def process_filename(self, filename: str, metadata: Optional[dict] = None) -> str:
        """Process a filename using the selected metadata."""
        return self.metadata_module.process_filename(filename, metadata)
    
    def reset_configuration(self) -> None:
        """Reset the widget configuration."""
        self.metadata_module.reset_configuration()
        
        # Reset UI
        if self.category_combo:
            self.category_combo.setCurrentIndex(0)
        
        if self.options_combo:
            self.options_combo.clear()
            self.options_combo.setEnabled(False)
        
        logger.debug("[MetadataWidgetV2] Configuration reset")
    
    def get_widget_height_rows(self) -> int:
        """Get the logical row count for this widget."""
        return 2  # Category + Field rows
