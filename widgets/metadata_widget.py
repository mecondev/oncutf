"""Metadata Widget V2 - Composition-based implementation.

This widget provides the UI for metadata-based renaming using composition
instead of inheritance to avoid QSS and event propagation conflicts.

Author: Michael Economou
Date: 2025-01-27
"""

from typing import Optional

from core.pyqt_imports import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
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
    remove_requested = pyqtSignal()
    configuration_changed = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the metadata widget."""
        super().__init__(parent)
        
        # Create the metadata module (composition, not inheritance)
        self.metadata_module = MetadataModule()
        
        # UI components
        self.category_combo: Optional[HierarchicalComboBox] = None
        self.field_combo: Optional[HierarchicalComboBox] = None
        
        # Setup the UI
        self._setup_ui()
        self._setup_connections()
        self._populate_category_combo()
        
        logger.debug("[MetadataWidgetV2] Widget initialized")
    
    def _setup_ui(self) -> None:
        """Setup the widget UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # Header with title and remove button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        # Title
        title_label = QLabel("Metadata")
        title_label.setObjectName("module_title")
        try:
            from utils.theme_engine import ThemeEngine
            theme = ThemeEngine()
            title_color = theme.get_color("text_primary")
            title_label.setStyleSheet(f"color: {title_color}; font-weight: 600;")
        except Exception:
            pass
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setObjectName("remove_button")
        remove_btn.setFixedSize(24, 24)
        remove_btn.clicked.connect(self.remove_requested.emit)
        try:
            from utils.theme_engine import ThemeEngine
            theme = ThemeEngine()
            btn_bg = theme.get_color("button_background")
            btn_hover = theme.get_color("button_hover_background")
            btn_text = theme.get_color("button_text")
            remove_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    color: {btn_text};
                    border: none;
                    border-radius: 12px;
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                }}
            """)
        except Exception:
            pass
        
        header_layout.addWidget(remove_btn)
        main_layout.addLayout(header_layout)
        
        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)
        
        # Category selection
        category_label = QLabel("Category:")
        try:
            from utils.theme_engine import ThemeEngine
            theme = ThemeEngine()
            label_color = theme.get_color("text_secondary")
            category_label.setStyleSheet(f"color: {label_color};")
        except Exception:
            pass
        
        self.category_combo = HierarchicalComboBox()
        self.category_combo.setObjectName("metadata_category_combo")
        
        content_layout.addWidget(category_label)
        content_layout.addWidget(self.category_combo)
        
        # Field selection
        field_label = QLabel("Field:")
        try:
            from utils.theme_engine import ThemeEngine
            theme = ThemeEngine()
            label_color = theme.get_color("text_secondary")
            field_label.setStyleSheet(f"color: {label_color};")
        except Exception:
            pass
        
        self.field_combo = HierarchicalComboBox()
        self.field_combo.setObjectName("metadata_field_combo")
        self.field_combo.setEnabled(False)  # Disabled until category is selected
        
        content_layout.addWidget(field_label)
        content_layout.addWidget(self.field_combo)
        
        main_layout.addWidget(content_widget)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    
    def _setup_connections(self) -> None:
        """Setup signal connections."""
        if self.category_combo:
            self.category_combo.currentTextChanged.connect(self._on_category_changed)
        
        if self.field_combo:
            self.field_combo.currentTextChanged.connect(self._on_field_changed)
    
    def _populate_category_combo(self) -> None:
        """Populate the category combo box."""
        if not self.category_combo:
            return
        
        self.category_combo.clear()
        
        # Add placeholder
        self.category_combo.add_item("Select category...", None)
        
        # Add categories
        for category in self.metadata_module.metadata_categories.keys():
            self.category_combo.add_item(category, category)
        
        logger.debug(f"[MetadataWidgetV2] Populated {len(self.metadata_module.metadata_categories)} categories")
    
    def _populate_field_combo(self, category: str) -> None:
        """Populate the field combo box for the selected category."""
        if not self.field_combo:
            return
        
        self.field_combo.clear()
        
        if not category:
            self.field_combo.setEnabled(False)
            return
        
        # Add placeholder
        self.field_combo.add_item("Select field...", None)
        
        # Add fields for the category
        fields = self.metadata_module.get_fields_for_category(category)
        for field in fields:
            self.field_combo.add_item(field, field)
        
        self.field_combo.setEnabled(True)
        logger.debug(f"[MetadataWidgetV2] Populated {len(fields)} fields for category: {category}")
    
    def _on_category_changed(self, category: str) -> None:
        """Handle category selection change."""
        # Update the module
        self.metadata_module.selected_category = category if category != "Select category..." else ""
        
        # Update field combo
        self._populate_field_combo(self.metadata_module.selected_category)
        
        # Reset field selection
        self.metadata_module.selected_field = ""
        
        # Emit configuration change
        self.configuration_changed.emit()
        
        logger.debug(f"[MetadataWidgetV2] Category changed to: {category}")
    
    def _on_field_changed(self, field: str) -> None:
        """Handle field selection change."""
        # Update the module
        self.metadata_module.selected_field = field if field != "Select field..." else ""
        
        # Emit configuration change
        self.configuration_changed.emit()
        
        logger.debug(f"[MetadataWidgetV2] Field changed to: {field}")
    
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
        
        if self.field_combo:
            self.field_combo.clear()
            self.field_combo.setEnabled(False)
        
        logger.debug("[MetadataWidgetV2] Configuration reset")
    
    def get_widget_height_rows(self) -> int:
        """Get the logical row count for this widget."""
        return 2  # Category + Field rows
