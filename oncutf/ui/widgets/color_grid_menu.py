"""
Module: color_grid_menu.py

Author: Michael Economou
Date: 2025-12-21

Custom color grid menu widget for file color tagging.

Layout:
┌─────────────────────────┬───────┐
│ Color Grid (4 rows x 8) │ Color │
│                         │ Picker│
│                         ├───────┤
│                         │ None  │
└─────────────────────────┴───────┘
"""

from oncutf.core.pyqt_imports import (
    QColorDialog,
    QGridLayout,
    QHBoxLayout,
    QIcon,
    QPixmap,
    QPushButton,
    QSize,
    Qt,
    QToolButton,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
)
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.tooltip_helper import TooltipHelper

logger = get_cached_logger(__name__)


class ColorButton(QToolButton):
    """
    Single color button in the color grid.

    Displays a solid color swatch that can be clicked to select.
    """

    clicked_with_color = pyqtSignal(str)  # Emits hex color on click

    def __init__(self, color: str, parent=None):
        """
        Initialize color button.

        Args:
            color: Hex color string (e.g., "#ff0000")
            parent: Parent widget
        """
        super().__init__(parent)
        self.color = color

        from oncutf.config import COLOR_SWATCH_SIZE
        from oncutf.utils.theme import get_theme_color

        self.setFixedSize(COLOR_SWATCH_SIZE+2, COLOR_SWATCH_SIZE)
        TooltipHelper.setup_tooltip(self, color.upper())

        # Get theme colors for borders
        border_normal = get_theme_color("border")
        border_hover = get_theme_color("text")
        border_pressed = get_theme_color("border_hover")

        # Style with solid color background and theme-aware borders
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {color};
                border: 1px solid {border_normal};
                border-radius: 0px;
            }}
            QToolButton:hover {{
                border: 2px solid {border_hover};
            }}
            QToolButton:pressed {{
                border: 2px solid {border_pressed};
            }}
        """)

        self.clicked.connect(lambda: self.clicked_with_color.emit(self.color))


class ColorGridMenu(QWidget):
    """
    Color grid menu widget with 32 color swatches, custom color picker, and reset option.

    This widget appears as a popup when right-clicking on the color column.
    """

    color_selected = pyqtSignal(str)  # Emits selected color hex or "none"

    def __init__(self, parent=None):
        """
        Initialize color grid menu.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        logger.info("[ColorGridMenu] __init__ called with parent: %s", parent)

        # Popup window flags
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        logger.info("[ColorGridMenu] Window flags set")

        self._setup_ui()

        logger.info("[ColorGridMenu] UI setup complete, widget initialized")

    def _setup_ui(self):
        """Setup the menu UI layout."""
        from oncutf.utils.theme import get_theme_color

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Left: Color grid (4 rows x 8 columns)
        grid_widget = self._create_color_grid()
        main_layout.addWidget(grid_widget)

        # Right column: Picker + None button (equal height split)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(2)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Color picker button with image (50% of height)
        picker_btn = self._create_picker_button()
        right_layout.addWidget(picker_btn)

        # None/Reset button below picker (50% of height)
        none_btn = QPushButton("None")
        none_btn.setObjectName("noneButton")
        TooltipHelper.setup_tooltip(none_btn, "Remove color tag from file")
        none_btn.clicked.connect(lambda: self._on_color_selected("none"))
        right_layout.addWidget(none_btn)

        main_layout.addLayout(right_layout)

        # Apply theme-consistent styling
        bg_color = get_theme_color("background")
        border_color = get_theme_color("border")
        border_hover = get_theme_color("accent")  # Brighter blue like browse button
        button_bg = get_theme_color("button_bg")
        button_hover_bg = get_theme_color("button_hover_bg")
        button_pressed = get_theme_color("button_pressed_bg")
        text_color = get_theme_color("text")

        self.setStyleSheet(f"""
            ColorGridMenu {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 2px;
            }}
            QPushButton, #pickerButton {{
                background-color: {button_bg};
                color: {text_color};
                border: 2px solid {border_color};
                border-radius: 3px;
                padding: 0px;
                font-size: 12px;
                min-height: 24px;
            }}
            #pickerButton {{
                padding: 0px;
            }}
            QPushButton:hover, #pickerButton:hover {{
                background-color: {button_hover_bg};
                border: 2px solid {border_hover};
            }}
            QPushButton:pressed, #pickerButton:pressed {{
                background-color: {button_pressed};
            }}
        """)

    def _create_color_grid(self) -> QWidget:
        """
        Create the color grid widget with all color swatches.

        Returns:
            Widget containing the color grid
        """
        from oncutf.config import COLOR_GRID_COLS, COLOR_GRID_ROWS, COLOR_PALETTE

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(0)

        # Populate grid with COLOR_GRID_ROWS x COLOR_GRID_COLS layout
        for i, color in enumerate(COLOR_PALETTE[:COLOR_GRID_ROWS * COLOR_GRID_COLS]):
            row = i // COLOR_GRID_COLS
            col = i % COLOR_GRID_COLS

            btn = ColorButton(color)
            btn.clicked_with_color.connect(self._on_color_selected)
            grid_layout.addWidget(btn, row, col)

        return grid_widget

    def _create_picker_button(self) -> QToolButton:
        """
        Create the custom color picker button with image.

        Returns:
            Color picker button widget
        """
        from oncutf.config import COLOR_PICKER_IMAGE
        from oncutf.utils.path_utils import get_resource_path

        picker_btn = QToolButton()
        picker_btn.setObjectName("pickerButton")
        TooltipHelper.setup_tooltip(picker_btn, "Custom color picker\n(OS color dialog)")

        # Load color range image
        try:
            image_path = get_resource_path(COLOR_PICKER_IMAGE)
            pixmap = QPixmap(str(image_path))

            if not pixmap.isNull():
                # Scale to button size with smooth transformation
                scaled_pixmap = pixmap.scaled(
                    64, 24,
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation
                )
                picker_btn.setIcon(QIcon(scaled_pixmap))
                picker_btn.setIconSize(QSize(64, 24))
            else:
                logger.warning("[ColorGridMenu] Failed to load color picker image")
                picker_btn.setText("Picker")

        except Exception as e:
            logger.error("[ColorGridMenu] Error loading picker image: %s", e)
            picker_btn.setText("Picker")

        picker_btn.clicked.connect(self._open_color_picker)

        return picker_btn

    def _on_color_selected(self, color: str):
        """
        Handle color selection.

        Args:
            color: Selected hex color or "none"
        """
        logger.info("[ColorGridMenu] Color selected: %s", color)
        self.color_selected.emit(color)
        logger.info("[ColorGridMenu] Signal emitted, closing menu")
        self.close()
        logger.info("[ColorGridMenu] Menu closed")

    def _open_color_picker(self):
        """Open the Qt custom color picker dialog."""
        logger.debug("[ColorGridMenu] Opening custom color picker")

        dialog = QColorDialog(self)
        dialog.setWindowTitle("Select Custom Color")
        dialog.setOptions(QColorDialog.DontUseNativeDialog)

        # Customize buttons: remove icons and set fixed width
        for button in dialog.findChildren(QPushButton):
            button.setIcon(QIcon())
            button.setMinimumWidth(80)

        if dialog.exec_():
            color = dialog.currentColor()
            if color.isValid():
                hex_color = color.name()  # Returns #RRGGBB format
                logger.debug("[ColorGridMenu] Custom color selected: %s", hex_color)
                self._on_color_selected(hex_color)
        else:
            logger.debug("[ColorGridMenu] Color picker cancelled")
