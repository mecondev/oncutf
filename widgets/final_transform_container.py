"""
final_transform_container.py

Author: Michael Economou
Date: 2025-06-28

Container widget for the final transformation controls.
Uses a clean 3-column layout: Labels | Controls | Buttons
"""

from typing import Optional

from core.qt_imports import pyqtSignal, QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSize, Qt
from modules.base_module import BaseRenameModule
from utils.icons_loader import get_menu_icon
from utils.logger_factory import get_cached_logger

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
        self._setup_ui()

        # Initialize last value for change detection
        self._last_value = str(self.get_data())

    def _setup_ui(self):
        """Setup the UI with separate layouts for greeklish and comboboxes."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)  # Space between the two sections

        # Top section: Convert Greek to Greeklish (horizontal)
        greeklish_layout = QHBoxLayout()
        greeklish_layout.setSpacing(8)

        # Convert Greek label and button
        greeklish_label = QLabel("Convert Greek to Greeklish")

        self.greeklish_button = QPushButton()
        self.greeklish_button.setCheckable(True)
        self.greeklish_button.setFixedSize(20, 20)
        self.greeklish_button.setToolTip("Toggle Greek to Greeklish conversion")
        # Make button square with no rounded corners
        self.greeklish_button.setStyleSheet("QPushButton { border-radius: 2px; }")

        # Set icons for checked/unchecked states
        try:
            check_icon = get_menu_icon("check")
            self.greeklish_button.setIcon(check_icon)
            # Make icon larger to fill button better
            self.greeklish_button.setIconSize(QSize(16, 16))
        except Exception as e:
            logger.debug(f"Could not load check icon: {e}", extra={"dev_only": True})

        self.greeklish_button.toggled.connect(self._on_value_change)

        greeklish_layout.addWidget(greeklish_label)
        greeklish_layout.addWidget(self.greeklish_button)
        greeklish_layout.addStretch()  # Push everything to the left

        main_layout.addLayout(greeklish_layout)

        # Bottom section: Case/Separator with buttons (3-column)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)
        bottom_layout.setAlignment(Qt.AlignVCenter)

        # Column 1: Labels for case and separator
        labels_layout = QVBoxLayout()
        labels_layout.setSpacing(6)

        self.case_label = QLabel("Case:")
        self.case_label.setFixedWidth(70)
        self.separator_label = QLabel("Separator:")
        self.separator_label.setFixedWidth(70)

        labels_layout.addWidget(self.case_label)
        labels_layout.addWidget(self.separator_label)

        # Column 2: Comboboxes
        combos_layout = QVBoxLayout()
        combos_layout.setSpacing(6)

        self.case_combo = QComboBox()
        self.case_combo.addItems(["original", "lower", "UPPER", "Capitalize"])
        self.case_combo.setFixedWidth(160)
        self.case_combo.currentIndexChanged.connect(self._on_value_change)

        self.separator_combo = QComboBox()
        self.separator_combo.addItems(["as-is", "snake_case", "kebab-case", "space"])
        self.separator_combo.setFixedWidth(160)
        self.separator_combo.currentIndexChanged.connect(self._on_value_change)

        combos_layout.addWidget(self.case_combo)
        combos_layout.addWidget(self.separator_combo)

        # Column 3: Buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(6)

        # Centered add button
        self.add_button = QPushButton()
        self.add_button.setIcon(get_menu_icon("plus"))
        self.add_button.setFixedSize(30, 30)
        self.add_button.setIconSize(QSize(20, 20))
        self.add_button.setToolTip("Add new module")
        self.add_button.clicked.connect(self.add_module_requested.emit)

        # Centered remove button
        self.remove_button = QPushButton()
        self.remove_button.setIcon(get_menu_icon("minus"))
        self.remove_button.setFixedSize(30, 30)
        self.remove_button.setIconSize(QSize(20, 20))
        self.remove_button.setToolTip("Remove last module")
        self.remove_button.clicked.connect(self.remove_module_requested.emit)

        buttons_layout.addWidget(self.add_button, 0, Qt.AlignCenter)
        buttons_layout.addWidget(self.remove_button, 0, Qt.AlignCenter)

        # Add columns to bottom layout
        bottom_layout.addLayout(labels_layout)
        bottom_layout.addLayout(combos_layout)
        bottom_layout.addLayout(buttons_layout)
        bottom_layout.addStretch()  # Push everything to the left

        main_layout.addLayout(bottom_layout)

    def _on_value_change(self):
        """Handle value changes and emit update signal if data changed."""
        current_data = str(self.get_data())
        if current_data != self._last_value:
            self._last_value = current_data
            self.updated.emit()

    def get_data(self) -> dict:
        """Get the current transformation data."""
        return {
            "greeklish": self.greeklish_button.isChecked(),
            "case": self.case_combo.currentText(),
            "separator": self.separator_combo.currentText(),
        }

    def set_data(self, data: dict):
        """Set the transformation data."""
        self.greeklish_button.setChecked(data.get("greeklish", False))
        self.case_combo.setCurrentText(data.get("case", "original"))
        self.separator_combo.setCurrentText(data.get("separator", "as-is"))
        self._last_value = str(self.get_data())

    def set_remove_button_enabled(self, enabled: bool):
        """Enable/disable the remove button."""
        self.remove_button.setEnabled(enabled)
