"""
final_transform_container.py

Author: Michael Economou
Date: 2025-06-28

Container widget for the final transformation controls.
Uses a clean 3-column layout: Labels | Controls | Buttons
"""

from typing import Optional

from core.qt_imports import pyqtSignal, QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSize, Qt, QGridLayout
from modules.base_module import BaseRenameModule
from utils.icons_loader import get_menu_icon
from utils.logger_factory import get_cached_logger
from utils.tooltip_helper import setup_tooltip, TooltipType

logger = get_cached_logger(__name__)


class FinalTransformContainer(QWidget):
    """
    Container widget for final transformation controls.

    Layout structure:
    3 columns (Labels | Controls | Buttons)
    """

    updated = pyqtSignal()
    add_module_requested = pyqtSignal()
    remove_module_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("FinalTransformContainer")

        # Set transparent background to avoid white borders around rounded corners
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # type: ignore

        self._setup_ui()

        # Initialize last value for change detection
        self._last_value = str(self.get_data())

    def _setup_ui(self):
        """Setup the UI with grid layout for better alignment."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)  # Remove spacing since we removed the title

        # Greeklish row (alone, touching left)
        greeklish_layout = QHBoxLayout()
        greeklish_layout.setContentsMargins(0, 0, 0, 0)
        greeklish_layout.setSpacing(4)  # Reduced spacing from 8 to 4

        # Label for the checkbox (first)
        greeklish_text_label = QLabel("Convert Greek to Greeklish")

        # Checkbox for Greek to Greeklish conversion
        self.greeklish_checkbox = QCheckBox()  # Removed "Greeklish" text
        self.greeklish_checkbox.setChecked(False)
        # Setup custom tooltip for greeklish checkbox
        setup_tooltip(self.greeklish_checkbox, "Toggle Greek to Greeklish conversion", TooltipType.INFO)
        self.greeklish_checkbox.toggled.connect(self._on_value_change)

        greeklish_layout.addWidget(greeklish_text_label)
        greeklish_layout.addWidget(self.greeklish_checkbox)
        greeklish_layout.addStretch()  # Push everything to the left

        # Create buttons separately for each row
        # Add button
        self.add_button = QPushButton()
        self.add_button.setIcon(get_menu_icon("plus"))
        self.add_button.setFixedSize(30, 30)
        self.add_button.setIconSize(QSize(24, 24))
        self.add_button.clicked.connect(self.add_module_requested.emit)
        self.add_button.setCursor(Qt.PointingHandCursor)  # type: ignore
        setup_tooltip(self.add_button, "Add new module", TooltipType.INFO)

        # Remove button
        self.remove_button = QPushButton()
        self.remove_button.setIcon(get_menu_icon("minus"))
        self.remove_button.setFixedSize(30, 30)
        self.remove_button.setIconSize(QSize(24, 24))
        self.remove_button.clicked.connect(self.remove_module_requested.emit)
        self.remove_button.setCursor(Qt.PointingHandCursor)  # type: ignore
        setup_tooltip(self.remove_button, "Remove last module", TooltipType.INFO)

        # Case row - HBoxLayout: [Label][Combo] --- STRETCH --- [Add Button]
        case_row_layout = QHBoxLayout()
        case_row_layout.setSpacing(0)
        case_row_layout.setContentsMargins(0, 0, 0, 0)

        self.case_label = QLabel("Case")
        self.case_label.setFixedWidth(65)  # Increased by 20px
        self.case_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore

        self.case_combo = QComboBox()
        self.case_combo.addItems(["original", "lower", "UPPER", "Capitalize"])
        self.case_combo.setFixedWidth(116)  # Reduced by 10px
        self.case_combo.setFixedHeight(18)
        self.case_combo.currentIndexChanged.connect(self._on_value_change)

        # Add to case row: Label + Combo (left), Stretch (middle), Add Button (right)
        case_row_layout.addWidget(self.case_label, 0, Qt.AlignVCenter)  # type: ignore
        case_row_layout.addSpacing(8)  # Space between label and combo
        case_row_layout.addWidget(self.case_combo, 0, Qt.AlignVCenter)  # type: ignore
        case_row_layout.addStretch()  # This pushes add button to the right
        case_row_layout.addWidget(self.add_button, 0, Qt.AlignVCenter)  # type: ignore

        # Separator row - HBoxLayout: [Label][Combo] --- STRETCH --- [Remove Button]
        separator_row_layout = QHBoxLayout()
        separator_row_layout.setSpacing(0)
        separator_row_layout.setContentsMargins(0, 0, 0, 0)

        self.separator_label = QLabel("Separator")
        self.separator_label.setFixedWidth(65)  # Increased by 20px
        self.separator_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore

        self.separator_combo = QComboBox()
        self.separator_combo.addItems(["as-is", "snake_case", "kebab-case", "space"])
        self.separator_combo.setFixedWidth(116)  # Reduced by 10px
        self.separator_combo.setFixedHeight(18)
        self.separator_combo.currentIndexChanged.connect(self._on_value_change)

        # Add to separator row: Label + Combo (left), Stretch (middle), Remove Button (right)
        separator_row_layout.addWidget(self.separator_label, 0, Qt.AlignVCenter)  # type: ignore
        separator_row_layout.addSpacing(8)  # Space between label and combo
        separator_row_layout.addWidget(self.separator_combo, 0, Qt.AlignVCenter)  # type: ignore
        separator_row_layout.addStretch()  # This pushes remove button to the right
        separator_row_layout.addWidget(self.remove_button, 0, Qt.AlignVCenter)  # type: ignore

        # Add all to main layout
        main_layout.addLayout(greeklish_layout)
        main_layout.addLayout(case_row_layout)
        main_layout.addLayout(separator_row_layout)

    def _on_value_change(self):
        """Handle value changes and emit update signal if data changed."""
        current_data = str(self.get_data())
        if current_data != self._last_value:
            self._last_value = current_data
            self.updated.emit()

    def get_data(self) -> dict:
        """Get the current transformation data."""
        return {
            "greeklish": self.greeklish_checkbox.isChecked(),
            "case": self.case_combo.currentText(),
            "separator": self.separator_combo.currentText(),
        }

    def set_data(self, data: dict):
        """Set the transformation data."""
        self.greeklish_checkbox.setChecked(data.get("greeklish", False))
        self.case_combo.setCurrentText(data.get("case", "original"))
        self.separator_combo.setCurrentText(data.get("separator", "as-is"))
        self._last_value = str(self.get_data())

    def set_remove_button_enabled(self, enabled: bool):
        """Enable/disable the remove button."""
        self.remove_button.setEnabled(enabled)
