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
        self.add_button.clicked.connect(self.add_module_requested.emit)
        # Remove any padding/margins that might affect centering
        self.add_button.setContentsMargins(0, 0, 0, 0)
        # Add right padding to center the icon properly
        self.add_button.setStyleSheet("QPushButton { padding-right: 5px; }")

        # Setup custom tooltip for add button
        setup_tooltip(self.add_button, "Add new module", TooltipType.INFO)

        # Centered remove button
        self.remove_button = QPushButton()
        self.remove_button.setIcon(get_menu_icon("minus"))
        self.remove_button.setFixedSize(30, 30)
        self.remove_button.setIconSize(QSize(16, 16))  # Increased icon size from default to 16x16
        self.remove_button.clicked.connect(self.remove_module_requested.emit)
        # Remove any padding/margins that might affect centering
        self.remove_button.setContentsMargins(0, 0, 0, 0)
        # Add right padding to center the icon properly
        self.remove_button.setStyleSheet("QPushButton { padding-right: 5px; }")

        # Setup custom tooltip for remove button
        setup_tooltip(self.remove_button, "Remove last module", TooltipType.INFO)

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

        # 🚧 TEMPORARY DEV LOGGING - Log widget dimensions and positions
        self._log_widget_dimensions()

    def _on_value_change(self):
        """Handle value changes and emit update signal if data changed."""
        current_data = str(self.get_data())
        if current_data != self._last_value:
            # 🚧 TEMPORARY DEV LOGGING - Log value changes
            print(f"🔄 Final Transform value changed: {current_data}")
            self._log_widget_dimensions()  # Log dimensions on each change

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

    def _log_widget_dimensions(self):
        """🚧 TEMPORARY DEV LOGGING - Log widget dimensions and positions for fixing layout."""
        print("\n" + "="*60)
        print("🚧 FINAL TRANSFORM CONTAINER - WIDGET DIMENSIONS")
        print("="*60)

        # Container dimensions
        container_size = self.size()
        print(f"📦 Container: {container_size.width()}x{container_size.height()}")

        # Checkbox dimensions
        checkbox_size = self.greeklish_checkbox.size()
        checkbox_pos = self.greeklish_checkbox.pos()
        print(f"☑️  Greeklish Checkbox: {checkbox_size.width()}x{checkbox_size.height()} at ({checkbox_pos.x()}, {checkbox_pos.y()})")

        # Case combo dimensions
        case_combo_size = self.case_combo.size()
        case_combo_pos = self.case_combo.pos()
        print(f"📋 Case Combo: {case_combo_size.width()}x{case_combo_size.height()} at ({case_combo_pos.x()}, {case_combo_pos.y()})")
        print(f"   Fixed size set to: {self.case_combo.minimumWidth()}x{self.case_combo.minimumHeight()}")

        # Separator combo dimensions
        sep_combo_size = self.separator_combo.size()
        sep_combo_pos = self.separator_combo.pos()
        print(f"📋 Separator Combo: {sep_combo_size.width()}x{sep_combo_size.height()} at ({sep_combo_pos.x()}, {sep_combo_pos.y()})")
        print(f"   Fixed size set to: {self.separator_combo.minimumWidth()}x{self.separator_combo.minimumHeight()}")

        # Button dimensions
        add_btn_size = self.add_button.size()
        add_btn_pos = self.add_button.pos()
        print(f"➕ Add Button: {add_btn_size.width()}x{add_btn_size.height()} at ({add_btn_pos.x()}, {add_btn_pos.y()})")

        remove_btn_size = self.remove_button.size()
        remove_btn_pos = self.remove_button.pos()
        print(f"➖ Remove Button: {remove_btn_size.width()}x{remove_btn_size.height()} at ({remove_btn_pos.x()}, {remove_btn_pos.y()})")

        # Label dimensions
        case_label_size = self.case_label.size()
        case_label_pos = self.case_label.pos()
        print(f"🏷️  Case Label: {case_label_size.width()}x{case_label_size.height()} at ({case_label_pos.x()}, {case_label_pos.y()})")

        sep_label_size = self.separator_label.size()
        sep_label_pos = self.separator_label.pos()
        print(f"🏷️  Separator Label: {sep_label_size.width()}x{sep_label_size.height()} at ({sep_label_pos.x()}, {sep_label_pos.y()})")

        print("="*60)
        print("💡 Use these values to set fixed dimensions in config!")
        print("="*60 + "\n")
