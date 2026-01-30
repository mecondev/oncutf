"""Module: styled_combo_box.py.

Author: Michael Economou
Date: December 18, 2025

StyledComboBox - QComboBox with automatic theme integration.
Thin wrapper that sets up delegate and applies theme styling.
Popup sizing logic is delegated to combo_popup_helper for reusability.
"""

from PyQt5.QtWidgets import QComboBox, QWidget

from oncutf.ui.delegates.ui_delegates import ComboBoxItemDelegate
from oncutf.ui.helpers.combo_popup_helper import (
    apply_combo_popup_metrics,
    prepare_combo_popup,
)
from oncutf.ui.theme_manager import get_theme_manager
from oncutf.utils.logging.logger_factory import get_cached_logger

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
        self.setMaxVisibleItems(10)
        self.setProperty("variant", "styled")  # For potential QSS targeting

        self._setup_delegate()
        self._configure_view()
        self._apply_theme()

        logger.debug("StyledComboBox initialized")

    def _configure_view(self) -> None:
        """Configure the popup view (alternating rows, etc.)."""
        view = self.view()
        if view is not None:
            # Enable alternating rows (delegate will paint them)
            view.setAlternatingRowColors(True)

    def showPopup(self) -> None:
        """Show popup with proper sizing and frameless appearance.

        Uses combo_popup_helper to prevent Qt internal scroller artifacts
        and remove frame borders.
        """
        prepare_combo_popup(self)
        apply_combo_popup_metrics(self, pre_show=True)
        super().showPopup()
        apply_combo_popup_metrics(self, pre_show=False)

    def _setup_delegate(self) -> None:
        """Setup the item delegate for proper dropdown styling."""
        theme = get_theme_manager()
        delegate = ComboBoxItemDelegate(self, theme)
        self.setItemDelegate(delegate)

    def _apply_theme(self) -> None:
        """Apply theme-aware styling."""
        try:
            theme = get_theme_manager()
            combo_height = theme.get_constant("combo_height")
            item_height = theme.get_constant("combo_item_height")
            self.setFixedHeight(combo_height)

            # Apply inline stylesheet for proper styling
            bg = theme.get_color("input_bg")
            text = theme.get_color("text")
            border = theme.get_color("input_border")
            focus_border = theme.get_color("input_focus_border")
            hover_border = theme.get_color("outline")
            menu_bg = theme.get_color("menu_background")

            self.setStyleSheet(f"""
                QComboBox {{
                    background-color: {bg};
                    color: {text};
                    border: 1px solid {border};
                    border-radius: 4px;
                    padding: 3px 6px 3px 6px;
                }}
                QComboBox:hover {{
                    border-color: {hover_border};
                }}
                QComboBox:focus {{
                    border: 2px solid {focus_border};
                    padding: 2px 5px 2px 5px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {menu_bg};
                    color: {text};
                    border: 0px;
                    outline: 0px;
                }}
                QComboBox QFrame {{
                    border: 0px;
                }}
                QComboBox QAbstractItemView::item {{
                    min-height: {item_height}px;
                    padding: 0px 8px;
                    border: none;
                }}
            """)

            logger.debug("Theme applied: height=%d", combo_height)
        except Exception as e:
            logger.warning("Failed to apply theme: %s", e)
            # Fallback to default height
            self.setFixedHeight(32)
