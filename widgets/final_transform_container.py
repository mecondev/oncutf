"""
final_transform_container.py

Author: Michael Economou
Date: 2025-06-28

Container widget for the final transformation controls.
Uses a clean 3-column layout: Labels | Controls | Buttons
"""

from typing import Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from modules.base_module import BaseRenameModule
from utils.icons_loader import get_menu_icon
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FinalTransformContainer(QWidget):
    """
    Container widget for final transformation controls.

    Layout structure:
    1. Top: "Final Transform:" label
    2. Bottom: 3 columns (Labels | Controls | Buttons)
    """

    updated = pyqtSignal()
    add_module_requested = pyqtSignal()
    remove_module_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("FinalTransformContainer")
        self._setup_ui()

        # Initialize last value for change detection
        self._last_value = str(self.get_data())

    def _setup_ui(self):
        """Setup the UI with 3-column layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        # 1. Top label
        self.title_label = QLabel("Final Transform:")
        main_layout.addWidget(self.title_label)

        # 2. Three columns container
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(12)

        # Column 1: Labels
        labels_layout = QVBoxLayout()
        labels_layout.setSpacing(6)

        self.greeklish_label = QLabel("Greeklish:")
        self.greeklish_label.setFixedWidth(70)
        self.case_label = QLabel("Case:")
        self.case_label.setFixedWidth(70)
        self.separator_label = QLabel("Separator:")
        self.separator_label.setFixedWidth(70)

        labels_layout.addWidget(self.greeklish_label)
        labels_layout.addWidget(self.case_label)
        labels_layout.addWidget(self.separator_label)

        # Column 2: Controls
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(6)

        self.greeklish_checkbox = QCheckBox("Convert Greek to Greeklish")
        self.greeklish_checkbox.toggled.connect(self._on_value_change)

        self.case_combo = QComboBox()
        self.case_combo.addItems(["original", "lower", "UPPER", "Capitalize"])
        self.case_combo.setFixedWidth(200)
        self.case_combo.currentIndexChanged.connect(self._on_value_change)

        self.separator_combo = QComboBox()
        self.separator_combo.addItems(["as-is", "snake_case", "kebab-case", "space"])
        self.separator_combo.setFixedWidth(200)
        self.separator_combo.currentIndexChanged.connect(self._on_value_change)

        controls_layout.addWidget(self.greeklish_checkbox)
        controls_layout.addWidget(self.case_combo)
        controls_layout.addWidget(self.separator_combo)

        # Column 3: Buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(6)

        # Spacer for greeklish row (no button needed)
        spacer_widget = QWidget()
        spacer_widget.setFixedHeight(22)  # Same height as checkbox

        self.add_button = QPushButton()
        self.add_button.setIcon(get_menu_icon("plus"))
        self.add_button.setFixedSize(28, 28)
        self.add_button.setToolTip("Add new module")
        self.add_button.clicked.connect(self.add_module_requested.emit)

        self.remove_button = QPushButton()
        self.remove_button.setIcon(get_menu_icon("minus"))
        self.remove_button.setFixedSize(28, 28)
        self.remove_button.setToolTip("Remove last module")
        self.remove_button.clicked.connect(self.remove_module_requested.emit)

        buttons_layout.addWidget(spacer_widget)
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.remove_button)

        # Add columns to main layout
        columns_layout.addLayout(labels_layout)
        columns_layout.addLayout(controls_layout)
        columns_layout.addLayout(buttons_layout)
        columns_layout.addStretch()  # Push everything to the left

        main_layout.addLayout(columns_layout)

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
