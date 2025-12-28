"""Styling Handler for MetadataWidget.

This module handles styling operations for the MetadataWidget,
including theme inheritance and combo box styling.

Author: Michael Economou
Date: December 24, 2025
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.core.theme_manager import get_theme_manager
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_widget import MetadataWidget

logger = get_cached_logger(__name__)


class StylingHandler:
    """Handles styling operations for MetadataWidget."""

    def __init__(self, widget: MetadataWidget) -> None:
        """Initialize the StylingHandler.

        Args:
            widget: The parent MetadataWidget instance.
        """
        self.widget = widget
        logger.debug("StylingHandler initialized")

    def ensure_theme_inheritance(self) -> None:
        """Ensure that child widgets inherit theme styles properly.

        Note: This method is currently a no-op as detailed styling is handled
        by ComboBoxItemDelegate and the global ThemeManager.
        """

    def apply_disabled_combo_styling(self) -> None:
        """Apply disabled styling to hierarchical combo box.

        Note: This method is currently a no-op. Disabled state is handled
        by setEnabled(False) + global theme, avoiding interference with
        TreeViewItemDelegate dropdown states.
        """

    def apply_normal_combo_styling(self) -> None:
        """Apply normal styling to hierarchical combo box.

        Note: This method is currently a no-op. Global ThemeManager + delegates
        handle combo styling consistently, avoiding per-widget QSS interference.
        """

    def apply_combo_theme_styling(self) -> None:
        """Apply theme styling to combo boxes and ensure inheritance."""
        try:
            theme = get_theme_manager()
            logger.debug(
                "[MetadataWidget] Theme inheritance ensured for combo boxes",
                extra={"dev_only": True},
            )

            css = f"""
                QComboBox {{
                    background-color: {theme.get_color("input_background")};
                    border: 1px solid {theme.get_color("input_border")};
                    border-radius: 4px;
                    padding: 6px 8px;
                    color: {theme.get_color("input_text")};
                    font-size: 12px;
                    min-height: 20px;
                    selection-background-color: {theme.get_color("input_selection_background")};
                    selection-color: {theme.get_color("input_selection_text")};
                }}

                QComboBox:hover {{
                    border-color: {theme.get_color("input_border_hover")};
                }}

                QComboBox:focus {{
                    border-color: {theme.get_color("input_border_focus")};
                }}

                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}

                /* Custom styling for disabled items in custom model */
                QComboBox QAbstractItemView::item {{
                    background-color: transparent;
                    color: {theme.get_color("text")};
                    padding: 6px 8px;
                    border: none;
                    min-height: 18px;
                    border-radius: 3px;
                    margin: 1px;
                }}

                QComboBox QAbstractItemView::item:hover {{
                    background-color: {theme.get_color("combo_item_background_hover")};
                    color: {theme.get_color("text")};
                }}

                QComboBox QAbstractItemView::item:selected {{
                    background-color: {theme.get_color("combo_item_background_selected")};
                    color: {theme.get_color("input_selection_text")};
                }}

                /* Force grayout for items without ItemIsEnabled flag */
                QComboBox QAbstractItemView::item:!enabled {{
                    background-color: transparent !important;
                    color: {theme.get_color("text_disabled")} !important;
                    opacity: 0.6 !important;
                }}

                QComboBox QAbstractItemView::item:!enabled:hover {{
                    background-color: transparent !important;
                    color: {theme.get_color("text_disabled")} !important;
                }}
            """

            self.widget.category_combo.setStyleSheet(css)

        except Exception as e:
            logger.error("[MetadataWidget] Error applying combo theme styling: %s", e)

    def apply_disabled_category_styling(self) -> None:
        """Apply disabled styling to the category combo box.

        Note: This method is currently a no-op. Disabled state is handled
        by setEnabled(False) + global theme, avoiding interference with
        ComboBoxItemDelegate dropdown states.
        """

    def apply_category_styling(self) -> None:
        """Apply normal styling to the category combo box.

        Note: This method is currently a no-op. Global ThemeManager + delegates
        handle combo styling consistently, avoiding per-widget QSS interference.
        """
