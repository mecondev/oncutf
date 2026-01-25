"""Module: final_transform_container.py.

Author: Michael Economou
Date: 2025-06-25

final_transform_container.py
Container widget for the final transformation controls.
Uses a clean 3-column layout: Labels | Controls | Buttons
"""

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from oncutf.config import ICON_SIZES
from oncutf.ui.widgets.styled_combo_box import StyledComboBox
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import cancel_timer, schedule_ui_update
from oncutf.utils.ui.icons_loader import get_menu_icon
from oncutf.utils.ui.tooltip_helper import TooltipHelper, TooltipType

logger = get_cached_logger(__name__)


class FinalTransformContainer(QWidget):
    """Container widget for final transformation controls.

    Layout structure:
    3 columns (Labels | Controls | Buttons)
    """

    updated = pyqtSignal()
    add_module_requested = pyqtSignal()
    remove_module_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        """Initialize final transform container with controls and rename engine."""
        super().__init__(parent)
        self.setObjectName("FinalTransformContainer")

        # Set transparent background to avoid white borders around rounded corners
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Initialize UnifiedRenameEngine
        self.rename_engine = None
        self._setup_rename_engine()

        self._setup_ui()

        # Initialize last value for change detection
        self._last_value = str(self.get_data())

        # Central preview update timer ID (managed by TimerManager)
        self._preview_timer_id: str | None = None

    def _setup_ui(self):
        """Setup the UI with grid layout for better alignment."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(0)  # Remove spacing since we removed the title

        # Greeklish row (alone, touching left)
        greeklish_layout = QHBoxLayout()
        greeklish_layout.setContentsMargins(0, 0, 0, 0)
        greeklish_layout.setSpacing(0)  # Minimum spacing

        # Label for the checkbox (first)
        greeklish_text_label = QLabel("Convert Greek to Greeklish")
        greeklish_text_label.setAlignment(Qt.AlignVCenter)

        # Checkbox for Greek to Greeklish conversion
        self.greeklish_checkbox = GreeklishToggle()
        self.greeklish_checkbox.setChecked(False)
        TooltipHelper.setup_tooltip(
            self.greeklish_checkbox, "Toggle Greek to Greeklish conversion", TooltipType.INFO
        )
        self.greeklish_checkbox.toggled.connect(self._on_value_change)

        greeklish_layout.addWidget(greeklish_text_label, 0, Qt.AlignVCenter)
        greeklish_layout.addWidget(self.greeklish_checkbox, 0, Qt.AlignVCenter)
        greeklish_layout.addStretch()  # Push everything to the left

        # Create buttons separately for each row
        # Add button
        self.add_button = QPushButton()
        self.add_button.setIcon(get_menu_icon("plus"))
        self.add_button.setFixedSize(30, 30)
        self.add_button.setIconSize(QSize(ICON_SIZES["MEDIUM"], ICON_SIZES["MEDIUM"]))
        self.add_button.clicked.connect(self.add_module_requested.emit)
        self.add_button.setCursor(Qt.PointingHandCursor)
        TooltipHelper.setup_tooltip(self.add_button, "Add new module", TooltipType.INFO)

        # Remove button
        self.remove_button = QPushButton()
        self.remove_button.setIcon(get_menu_icon("minus"))
        self.remove_button.setFixedSize(30, 30)
        self.remove_button.setIconSize(QSize(ICON_SIZES["MEDIUM"], ICON_SIZES["MEDIUM"]))
        self.remove_button.clicked.connect(self.remove_module_requested.emit)
        self.remove_button.setCursor(Qt.PointingHandCursor)
        TooltipHelper.setup_tooltip(self.remove_button, "Remove last module", TooltipType.INFO)

        # Case row - HBoxLayout: [Label][Combo] --- STRETCH --- [Add Button]
        case_row_layout = QHBoxLayout()
        case_row_layout.setSpacing(0)
        case_row_layout.setContentsMargins(0, 0, 0, 0)

        self.case_label = QLabel("Case")
        self.case_label.setFixedWidth(65)  # Increased by 20px
        self.case_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.case_combo = StyledComboBox()
        self.case_combo.addItems(["original", "lower", "UPPER", "Capitalize"])
        self.case_combo.setFixedWidth(116)  # Reduced by 10px
        # Theme styling is handled by StyledComboBox
        # Ensure combo box drops down instead of popping up
        self.case_combo.view().window().setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.case_combo.currentIndexChanged.connect(self._on_value_change)

        # Add to case row: Label + Combo (left), Stretch (middle), Add Button (right)
        case_row_layout.addWidget(self.case_label, 0, Qt.AlignVCenter)
        case_row_layout.addSpacing(8)  # Space between label and combo
        case_row_layout.addWidget(self.case_combo, 0, Qt.AlignVCenter)
        case_row_layout.addStretch()  # This pushes add button to the right
        case_row_layout.addWidget(self.add_button, 0, Qt.AlignVCenter)

        # Separator row - HBoxLayout: [Label][Combo] --- STRETCH --- [Remove Button]
        separator_row_layout = QHBoxLayout()
        separator_row_layout.setSpacing(0)
        separator_row_layout.setContentsMargins(0, 0, 0, 0)

        self.separator_label = QLabel("Separator")
        self.separator_label.setFixedWidth(65)
        self.separator_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.separator_combo = StyledComboBox()
        self.separator_combo.addItems(["as-is", "snake_case", "kebab-case", "space"])
        self.separator_combo.setFixedWidth(116)  # Reduced by 10px
        # Theme styling is handled by StyledComboBox
        # Ensure combo box drops down instead of popping up
        self.separator_combo.view().window().setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.separator_combo.currentIndexChanged.connect(self._on_value_change)

        # Add to separator row: Label + Combo (left), Stretch (middle), Remove Button (right)
        separator_row_layout.addWidget(self.separator_label, 0, Qt.AlignVCenter)
        separator_row_layout.addSpacing(8)  # Space between label and combo
        separator_row_layout.addWidget(self.separator_combo, 0, Qt.AlignVCenter)
        separator_row_layout.addStretch()  # This pushes remove button to the right
        separator_row_layout.addWidget(self.remove_button, 0, Qt.AlignVCenter)

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
            # Trigger central preview update
            self._schedule_central_preview_update()

    def _setup_rename_engine(self):
        """Setup UnifiedRenameEngine."""
        try:
            from oncutf.core.rename.unified_rename_engine import UnifiedRenameEngine

            self.rename_engine = UnifiedRenameEngine()
            logger.debug("[FinalTransformContainer] UnifiedRenameEngine initialized")
        except Exception as e:
            logger.error("[FinalTransformContainer] Error initializing UnifiedRenameEngine: %s", e)

    def _schedule_central_preview_update(self):
        """Schedule central preview update with delay."""
        if self._preview_timer_id:
            cancel_timer(self._preview_timer_id)
        # Schedule with 50ms debounce via TimerManager
        self._preview_timer_id = schedule_ui_update(
            self._trigger_central_preview_update, delay=50
        )

    def _trigger_central_preview_update(self):
        """Trigger central preview update."""
        try:
            if self.rename_engine:
                # Clear cache to force fresh preview
                self.rename_engine.clear_cache()
                logger.debug("[FinalTransformContainer] Central preview update triggered")
        except Exception as e:
            logger.error("[FinalTransformContainer] Error in central preview update: %s", e)

    def trigger_preview_update(self):
        """Public method to trigger preview update."""
        self._trigger_central_preview_update()

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

        # Handle tooltip based on enabled state
        if enabled:
            # Re-enable tooltip when button is enabled
            TooltipHelper.setup_tooltip(self.remove_button, "Remove last module", TooltipType.INFO)
            # Set normal icon
            self.remove_button.setIcon(get_menu_icon("minus"))
        else:
            # Clear tooltip when button is disabled
            TooltipHelper.clear_tooltips_for_widget(self.remove_button)

            # Create disabled icon with reduced opacity
            from PyQt5.QtCore import Qt
            from PyQt5.QtGui import QPainter, QPixmap

            # Get the original icon
            original_icon = get_menu_icon("minus")
            original_pixmap = original_icon.pixmap(ICON_SIZES["MEDIUM"], ICON_SIZES["MEDIUM"])

            # Create a new pixmap with reduced opacity
            disabled_pixmap = QPixmap(original_pixmap.size())
            disabled_pixmap.fill(Qt.transparent)

            painter = QPainter(disabled_pixmap)
            painter.setOpacity(0.3)  # 30% opacity for disabled state
            painter.drawPixmap(0, 0, original_pixmap)
            painter.end()

            # Set the disabled icon
            from PyQt5.QtGui import QIcon

            disabled_icon = QIcon(disabled_pixmap)
            self.remove_button.setIcon(disabled_icon)



class GreeklishToggle(QLabel):
    """Custom toggle switch widget for Greeklish transformation."""

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        """Initialize toggle with icons and default unchecked state."""
        super().__init__(parent)
        self._checked = False
        self._icon_left = get_menu_icon("toggle-left")
        self._icon_right = get_menu_icon("toggle-right")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(28, 28)  # Slightly larger for padding
        self.setAlignment(Qt.AlignCenter)
        self._update_icon()

    def mousePressEvent(self, event):
        """Toggle state on mouse click."""
        self.setChecked(not self._checked)
        self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def setChecked(self, checked: bool):
        """Set toggle state and update icon."""
        self._checked = bool(checked)
        self._update_icon()

    def isChecked(self) -> bool:
        """Return current toggle state."""
        return self._checked

    def _update_icon(self):
        """Update icon based on current toggle state."""
        # Get QPixmap ~19x19 from QIcon, 20% larger than 16x16
        icon = self._icon_right if self._checked else self._icon_left
        pixmap = icon.pixmap(19, 19)
        # Create a new pixmap with padding (28x28)
        padded = QPixmap(28, 28)
        padded.fill(Qt.transparent)
        painter = QPainter(padded)
        # Center the 19x19 icon
        x = (28 - 19) // 2
        y = (28 - 19) // 2
        painter.drawPixmap(x, y, pixmap)
        painter.end()
        self.setPixmap(padded)
