"""Module: styled_combo_box.py

Author: Michael Economou
Date: December 18, 2025

StyledComboBox - QComboBox with automatic theme integration.
Provides consistent styling and proper delegate setup.
"""

from PyQt5.QtWidgets import QComboBox, QWidget

from oncutf.core.theme_manager import get_theme_manager
from oncutf.ui.delegates.ui_delegates import ComboBoxItemDelegate
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class StyledComboBox(QComboBox):
    """ComboBox with automatic theme integration.

    Features:
    - Automatic ComboBoxItemDelegate setup
    - Theme-aware height configuration
    - Consistent appearance across the application
    """

    def __init__(self, parent: QWidget | None = None):
        """Initialize the styled combo box.

        Args:
            parent: Parent widget

        """
        super().__init__(parent)
        self._setup_delegate()
        self._apply_theme()
        logger.debug("StyledComboBox initialized")

    def _setup_delegate(self) -> None:
        """Setup the item delegate for proper dropdown styling."""
        try:
            theme = get_theme_manager()
            delegate = ComboBoxItemDelegate(self, theme)
            self.setItemDelegate(delegate)
            logger.debug("ComboBoxItemDelegate set successfully")
        except Exception as e:
            logger.warning("Failed to set ComboBoxItemDelegate: %s", e)

    def _apply_theme(self) -> None:
        """Apply theme-aware styling."""
        try:
            theme = get_theme_manager()
            combo_height = theme.get_constant("combo_height")
            self.setFixedHeight(combo_height)

            # Apply inline stylesheet for proper styling
            bg = theme.get_color("input_bg")
            text = theme.get_color("text")
            border = theme.get_color("input_border")
            focus_border = theme.get_color("input_focus_border")
            hover_border = theme.get_color("outline")
            menu_bg = theme.get_color("menu_background")
            selected_bg = theme.get_color("selected")
            selected_text = theme.get_color("selected_text")

            self.setStyleSheet(f"""
                QComboBox {{
                    background-color: {bg};
                    color: {text};
                    border: 1px solid {border};
                    border-radius: 4px;
                    padding: 2px 6px;
                }}
                QComboBox:hover {{
                    border-color: {hover_border};
                }}
                QComboBox:focus {{
                    border: 2px solid {focus_border};
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {menu_bg};
                    color: {text};
                    selection-background-color: {selected_bg};
                    selection-color: {selected_text};
                    border: 1px solid {border};
                }}
            """)

            logger.debug("Theme applied: height=%d", combo_height)
        except Exception as e:
            logger.warning("Failed to apply theme: %s", e)
            # Fallback to default height
            self.setFixedHeight(32)
