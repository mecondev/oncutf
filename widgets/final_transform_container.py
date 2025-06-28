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
        """Setup the UI with grid layout for better alignment."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)  # Remove spacing since we removed the title

        # Apply checkbox styling to match metadata edit dialog
        self.setStyleSheet("""
            QCheckBox {
                color: #f0ebd8;
                font-size: 9pt;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #3a3b40;
                border-radius: 3px;
                background-color: #181818;
            }
            QCheckBox::indicator:unchecked {
                image: url(resources/icons/feather_icons/square.svg);
                background-color: #181818;
                border-color: #3a3b40;
            }
            QCheckBox::indicator:checked {
                image: url(resources/icons/feather_icons/check-square.svg);
                background-color: #181818;
                border-color: #3a3b40;
            }
            QCheckBox::indicator:hover {
                border-color: #555555;
                background-color: #232323;
            }
            QCheckBox::indicator:focus {
                border-color: #666666;
                background-color: #2a2a2a;
            }
        """)

        # Greeklish row (alone, touching left)
        greeklish_layout = QHBoxLayout()
        greeklish_layout.setContentsMargins(0, 0, 0, 0)
        greeklish_layout.setSpacing(4)  # Reduced spacing from 8 to 4

        # Label for the checkbox (first)
        greeklish_text_label = QLabel("Convert Greek to Greeklish")

        # Checkbox for Greek to Greeklish conversion
        self.greeklish_checkbox = QCheckBox()
        self.greeklish_checkbox.setToolTip("Toggle Greek to Greeklish conversion")
        self.greeklish_checkbox.toggled.connect(self._on_value_change)

        greeklish_layout.addWidget(greeklish_text_label)
        greeklish_layout.addWidget(self.greeklish_checkbox)
        greeklish_layout.addStretch()  # Push everything to the left

        # Grid layout for Case and Separator rows
        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)

        # Case row
        self.case_label = QLabel("Case")
        self.case_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.case_combo = QComboBox()
        self.case_combo.addItems(["original", "lower", "UPPER", "Capitalize"])
        self.case_combo.setFixedWidth(112)
        self.case_combo.setFixedHeight(22)
        self.case_combo.currentIndexChanged.connect(self._on_value_change)

        # Separator row
        self.separator_label = QLabel("Separator")
        self.separator_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.separator_combo = QComboBox()
        self.separator_combo.addItems(["as-is", "snake_case", "kebab-case", "space"])
        self.separator_combo.setFixedWidth(112)
        self.separator_combo.setFixedHeight(22)
        self.separator_combo.currentIndexChanged.connect(self._on_value_change)

        # Add buttons column
        buttons_layout = QVBoxLayout()
        buttons_layout.setAlignment(Qt.AlignRight | Qt.AlignTop)
        buttons_layout.setSpacing(4)

        # Centered add button
        self.add_button = QPushButton()
        self.add_button.setIcon(get_menu_icon("plus"))
        self.add_button.setFixedSize(30, 30)
        self.add_button.setIconSize(QSize(16, 16))  # Increased icon size from default to 16x16
        self.add_button.setToolTip("Add new module")
        self.add_button.clicked.connect(self.add_module_requested.emit)
        # Remove any padding/margins that might affect centering
        self.add_button.setContentsMargins(0, 0, 0, 0)
        # Add right padding to center the icon properly
        self.add_button.setStyleSheet("QPushButton { padding-right: 5px; }")

        # Centered remove button
        self.remove_button = QPushButton()
        self.remove_button.setIcon(get_menu_icon("minus"))
        self.remove_button.setFixedSize(30, 30)
        self.remove_button.setIconSize(QSize(16, 16))  # Increased icon size from default to 16x16
        self.remove_button.setToolTip("Remove last module")
        self.remove_button.clicked.connect(self.remove_module_requested.emit)
        # Remove any padding/margins that might affect centering
        self.remove_button.setContentsMargins(0, 0, 0, 0)
        # Add right padding to center the icon properly
        self.remove_button.setStyleSheet("QPushButton { padding-right: 5px; }")

        buttons_layout.addWidget(self.add_button, alignment=Qt.AlignCenter)
        buttons_layout.addWidget(self.remove_button, alignment=Qt.AlignCenter)

        # Add small spacer to push buttons slightly to the right
        buttons_layout.addSpacing(3)

        # Add to grid: [Label] [Combo] [Button]
        grid_layout.addWidget(self.case_label, 0, 0)
        grid_layout.addWidget(self.case_combo, 0, 1)
        grid_layout.addLayout(buttons_layout, 0, 2, 2, 1)  # Span 2 rows

        grid_layout.addWidget(self.separator_label, 1, 0)
        grid_layout.addWidget(self.separator_combo, 1, 1)

        # Set column stretch and minimum widths for better spacing
        grid_layout.setColumnStretch(0, 0)  # Labels column - no stretch
        grid_layout.setColumnStretch(1, 0)  # Combos column - no stretch (fixed width)
        grid_layout.setColumnStretch(2, 0)  # Buttons column - no stretch, stay at minimum width

        # Set minimum widths for better control
        grid_layout.setColumnMinimumWidth(0, 45)  # Labels column - reduced from 50 to 45
        grid_layout.setColumnMinimumWidth(1, 160)  # Combos column - fixed width
        grid_layout.setColumnMinimumWidth(2, 40)   # Buttons column - minimum width for buttons

        # Add all to main layout
        main_layout.addLayout(greeklish_layout)
        main_layout.addLayout(grid_layout)

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
