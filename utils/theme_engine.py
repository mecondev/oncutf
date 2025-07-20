"""
Module: theme_engine.py

Author: Michael Economou
Date: 2025-06-20

Simplified theme engine for OnCutF application.
Applies all styling globally to handle dynamically created widgets.
"""

import logging
import platform

import config
from core.pyqt_imports import QApplication, QMainWindow

logger = logging.getLogger(__name__)


class ThemeEngine:
    """Simplified theme engine that applies all styling globally."""

    def __init__(self, theme_name: str = "dark"):
        self.theme_name = theme_name or config.THEME_NAME
        self.is_windows = platform.system() == "Windows"

        # Color definitions
        self.colors = {
            # Base application colors
            "app_background": "#212121",
            "app_text": "#f0ebd8",
            # Input field colors
            "input_background": "#181818",
            "input_text": "#f0ebd8",
            "input_border": "#3a3b40",
            "input_border_hover": "#555555",
            "input_border_focus": "#748cab",
            "input_background_hover": "#1f1f1f",
            "input_background_focus": "#181818",
            "input_selection_bg": "#748cab",
            "input_selection_text": "#0d1321",
            # Button colors
            "button_background": "#2a2a2a",
            "button_text": "#f0ebd8",
            "button_background_hover": "#3e5c76",
            "button_background_pressed": "#748cab",
            "button_text_pressed": "#0d1321",
            "button_background_disabled": "#232323",
            "button_text_disabled": "#888888",
            "button_border": "#3a3b40",
            # ComboBox colors
            "combo_background": "#2a2a2a",
            "combo_text": "#f0ebd8",
            "combo_background_hover": "#3e5c76",
            "combo_background_pressed": "#748cab",
            "combo_text_pressed": "#0d1321",
            "combo_dropdown_background": "#181818",
            "combo_item_background_hover": "#3e5c76",
            "combo_item_background_selected": "#748cab",
            "combo_border": "#3a3b40",
            # Table/Tree view colors
            "table_background": "#181818",
            "table_text": "#f0ebd8",
            "table_alternate_background": "#232323",
            "table_selection_background": "#748cab",
            "table_selection_text": "#0d1321",
            "table_header_background": "#181818",
            "table_hover_background": "#3e5c76",
            # Scroll area colors
            "scroll_area_background": "#181818",
            "scroll_track_background": "#2c2c2c",
            "scroll_handle_background": "#555555",
            "scroll_handle_hover": "#3e5c76",
            "scroll_handle_pressed": "#748cab",
            # Module/Card colors
            "module_background": "#181818",
            "module_border": "#3a3b40",
            "module_drag_handle": "#2a2a2a",
            # Dialog colors
            "dialog_background": "#2a2a2a",
            "dialog_text": "#f0ebd8",
            # Tooltip colors
            "tooltip_background": "#2b2b2b",
            "tooltip_text": "#f0ebd8",
            "tooltip_border": "#555555",
            "tooltip_error_background": "#3d1e1e",
            "tooltip_error_text": "#ffaaaa",
            "tooltip_error_border": "#cc4444",
            "tooltip_warning_background": "#3d3d1e",
            "tooltip_warning_text": "#ffffaa",
            "tooltip_warning_border": "#cccc44",
            "tooltip_info_background": "#1e2d3d",
            "tooltip_info_text": "#aaccff",
            "tooltip_info_border": "#4488cc",
            "tooltip_success_background": "#1e3d1e",
            "tooltip_success_text": "#aaffaa",
            "tooltip_success_border": "#44cc44",
            # Special colors
            "highlight_blue": "#4a6fa5",
            "highlight_light_blue": "#8a9bb4",
            "accent_color": "#748cab",
            "separator_background": "#444444",
            "separator_light": "#555555",
            "border_color": "#3a3b40",
            "disabled_background": "#181818",
            "disabled_text": "#666666",
        }

        # Font definitions (using Inter fonts for all platforms)
        self.fonts = {
            "base_family": "Inter",
            "base_size": "9pt",
            "base_weight": "400",
            "interface_size": "9pt",
            "tree_size": "10pt",
            "medium_weight": "500",
            "semibold_weight": "600",
        }

    def apply_complete_theme(self, app: QApplication, main_window: QMainWindow):
        """Apply complete theming to the entire application."""
        # Clear any existing stylesheets
        app.setStyleSheet("")
        main_window.setStyleSheet("")

        # Load Inter fonts first
        self._load_inter_fonts()

        # Set application font programmatically for better consistency
        from utils.fonts import get_inter_font

        app_font = get_inter_font("base", int(self.fonts["base_size"].replace("pt", "")))
        app.setFont(app_font)

        # Create complete global stylesheet with DPI awareness
        global_style = self._get_complete_stylesheet()

        # Add DPI-aware font styling
        try:
            from utils.theme_font_generator import generate_dpi_aware_css

            dpi_css = generate_dpi_aware_css()
            global_style += "\n" + dpi_css
        except ImportError:
            pass

        # Apply the complete stylesheet globally
        app.setStyleSheet(global_style)

        # Apply Windows-specific ComboBox fixes if on Windows
        if self.is_windows:
            self._apply_windows_combobox_fixes(app)

    def _load_inter_fonts(self):
        """Load Inter fonts from resources"""
        try:
            from utils.fonts import _get_inter_fonts

            inter_fonts = _get_inter_fonts()
            logger.debug(f"[Theme] Inter fonts loaded: {len(inter_fonts.loaded_fonts)} fonts")
        except Exception as e:
            logger.error(f"[Theme] Failed to load Inter fonts: {e}")

    def _get_complete_stylesheet(self) -> str:
        """Get the complete stylesheet for the application."""
        return f"""
            /* BASE APPLICATION STYLING */
            QMainWindow, QWidget {{
                background-color: {self.colors['app_background']};
                color: {self.colors['app_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['base_size']};
                font-weight: {self.fonts['base_weight']};
            }}

            QLabel {{
                background-color: transparent;
                color: {self.colors['app_text']};
                border: none;
                padding: 2px;
                margin: 0px;
            }}

            QFrame {{
                border: none;
                background-color: {self.colors['app_background']};
            }}

            /* INPUT FIELDS */
            QLineEdit {{
                background-color: {self.colors['input_background']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                color: {self.colors['input_text']};
                padding: 2px 6px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
                min-height: 18px;
                font-size: {self.fonts['interface_size']};
            }}

            QLineEdit:hover {{
                background-color: {self.colors['input_background_hover']};
                border-color: {self.colors['input_border_hover']};
            }}

            QLineEdit:focus {{
                border-color: {self.colors['input_border_focus']};
                background-color: {self.colors['input_background_focus']};
            }}

            QLineEdit:disabled {{
                background-color: {self.colors['disabled_background']};
                color: {self.colors['disabled_text']};
                border-color: {self.colors['input_border']};
            }}

            /* ValidatedLineEdit with consistent border width to prevent shifting */
            ValidatedLineEdit {{
                background-color: {self.colors['input_background']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                color: {self.colors['input_text']};
                padding: 2px 6px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
                min-height: 18px;
                font-size: {self.fonts['interface_size']};
            }}

            ValidatedLineEdit:hover {{
                background-color: {self.colors['input_background_hover']};
                border-color: {self.colors['input_border_hover']};
            }}

            ValidatedLineEdit:focus {{
                border-color: {self.colors['input_border_focus']};
                background-color: {self.colors['input_background_focus']};
            }}

            ValidatedLineEdit[error="true"] {{
                border: 1px solid #ff4444 !important;
                background-color: #332222 !important;
                color: #ff8888 !important;
            }}

            ValidatedLineEdit[warning="true"] {{
                border: 1px solid #cc6600 !important;
                background-color: #332200 !important;
                color: #ffaa44 !important;
            }}

            ValidatedLineEdit[info="true"] {{
                border: 1px solid #4a9eff !important;
                background-color: #223344 !important;
                color: #88ccff !important;
            }}

            /* LAYOUT SPACING */
            QHBoxLayout {{
                spacing: 1px;
                margin: 2px;
            }}

            QVBoxLayout {{
                spacing: 2px;
                margin: 2px;
            }}

            QWidget {{
                margin: 0px;
            }}

            /* BUTTONS */
            QPushButton {{
                background-color: {self.colors['button_background']};
                border: none;
                border-radius: 8px;
                color: {self.colors['button_text']};
                padding: 4px 12px 4px 8px;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['medium_weight']};
            }}

            QPushButton:hover {{
                background-color: {self.colors['button_background_hover']};
            }}

            QPushButton:pressed {{
                background-color: {self.colors['button_background_pressed']};
                color: {self.colors['button_text_pressed']};
            }}

            QPushButton:disabled {{
                background-color: {self.colors['button_background_disabled']} !important;
                color: {self.colors['button_text_disabled']} !important;
                opacity: 0.6 !important;
            }}

            QPushButton:disabled:hover {{
                background-color: {self.colors['button_background_disabled']} !important;
                color: {self.colors['button_text_disabled']} !important;
            }}

            /* FINAL TRANSFORM CONTAINER BUTTONS */
            FinalTransformContainer QPushButton {{
                background-color: {self.colors['button_background']};
                border: none;
                border-radius: 6px;
                color: {self.colors['button_text']};
                padding: 2px;
                margin: 0px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }}

            FinalTransformContainer QPushButton:hover {{
                background-color: {self.colors['button_background_hover']};
            }}

            FinalTransformContainer QPushButton:pressed {{
                background-color: {self.colors['button_background_pressed']};
                color: {self.colors['button_text_pressed']};
            }}

            FinalTransformContainer QPushButton:disabled {{
                background-color: {self.colors['button_background_disabled']} !important;
                color: {self.colors['button_text_disabled']} !important;
                border: none !important;
                opacity: 0.4 !important;
            }}

            FinalTransformContainer QPushButton:disabled QIcon {{
                opacity: 0.4 !important;
            }}

            FinalTransformContainer QPushButton:disabled:hover {{
                background-color: {self.colors['button_background_disabled']} !important;
                color: {self.colors['button_text_disabled']} !important;
            }}

            /* COUNTER MODULE SPECIFIC */
            CounterModule QLineEdit {{
                text-align: right;
                qproperty-alignment: AlignRight;
            }}

            /* COUNTER MODULE BUTTONS - Improved icon positioning */
            CounterModule QPushButton {{
                background-color: {self.colors['button_background']};
                border: none;
                border-radius: 4px;
                color: {self.colors['button_text']};
                padding: 0px;
                margin: 0px;
                text-align: center;
                icon-size: 16px 16px;
                qproperty-iconSize: 16px 16px;
            }}

            CounterModule QPushButton:hover {{
                background-color: {self.colors['button_background_hover']};
            }}

            CounterModule QPushButton:pressed {{
                background-color: {self.colors['button_background_pressed']};
                color: {self.colors['button_text_pressed']};
            }}

            CounterModule QPushButton:disabled {{
                background-color: {self.colors['button_background_disabled']};
                color: {self.colors['button_text_disabled']};
            }}

            /* COMBOBOX */
            QComboBox {{
                background-color: {self.colors['combo_background']};
                border: 1px solid {self.colors['combo_border']};
                border-radius: 4px;
                color: {self.colors['combo_text']};
                padding: 2px 6px;
                min-height: 18px;
                margin: 0px;
                font-size: {self.fonts['interface_size']};
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
            }}

            QComboBox:hover {{
                background-color: {self.colors['combo_background_hover']};
                border-color: {self.colors['input_border_hover']};
                color: {self.colors['combo_text']};
            }}

            QComboBox:focus {{
                border-color: {self.colors['input_border_focus']};
                background-color: {self.colors['combo_background_hover']};
                color: {self.colors['combo_text']};
                outline: none;
            }}

            QComboBox:focus:hover {{
                background-color: {self.colors['combo_background_pressed']};
                color: {self.colors['combo_text_pressed']};
            }}

            QComboBox:on {{
                background-color: {self.colors['combo_background_pressed']};
                color: {self.colors['combo_text_pressed']};
                border-color: {self.colors['input_border_focus']};
            }}

            QComboBox:pressed {{
                background-color: {self.colors['highlight_light_blue']};
                color: {self.colors['combo_text_pressed']};
            }}

            QComboBox:disabled {{
                background-color: {self.colors['disabled_background']};
                color: {self.colors['disabled_text']};
                border-color: {self.colors['input_border']};
            }}

            QComboBox:!focus:!hover {{
                background-color: {self.colors['combo_background']};
                color: {self.colors['combo_text']};
            }}

            QComboBox::drop-down {{
                border: none;
                background-color: transparent;
                width: 18px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }}

            QComboBox::drop-down:hover {{
                background-color: transparent;
            }}

            QComboBox::down-arrow {{
                image: url(resources/icons/feather_icons/chevrons-down.svg);
                width: 12px;
                height: 12px;
            }}

            QComboBox::down-arrow:on {{
                image: url(resources/icons/feather_icons/chevrons-up.svg);
            }}

            QComboBox::down-arrow:disabled {{
                opacity: 0.5;
            }}

            QComboBox::down-arrow:hover {{
                opacity: 1.0;
            }}

            /* COMBOBOX DROPDOWN */
            QComboBox QAbstractItemView {{
                background-color: {self.colors['combo_dropdown_background']};
                color: {self.colors['combo_text']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 6px;
                outline: none;
                selection-background-color: {self.colors['combo_item_background_selected']};
                selection-color: {self.colors['input_selection_text']};
                font-size: {self.fonts['interface_size']};
                margin: 0px;
                padding: 0px;
            }}

            QComboBox QAbstractItemView::item {{
                background-color: transparent;
                color: {self.colors['combo_text']};
                padding: 6px 8px;
                border: none;
                min-height: 18px;
                border-radius: 3px;
                margin: 1px;
            }}

            QComboBox QAbstractItemView::item:hover {{
                background-color: {self.colors['combo_item_background_hover']};
                color: {self.colors['combo_text']};
            }}

            QComboBox QAbstractItemView::item:selected {{
                background-color: {self.colors['combo_item_background_selected']};
                color: {self.colors['input_selection_text']};
            }}

            QComboBox QAbstractItemView::item:selected:hover {{
                background-color: {self.colors['highlight_light_blue']};
                color: {self.colors['input_selection_text']};
            }}

            QComboBox QAbstractItemView::item:disabled {{
                background-color: transparent;
                color: {self.colors['disabled_text']};
                opacity: 0.6;
            }}

            QComboBox QAbstractItemView::item:disabled:hover {{
                background-color: transparent;
                color: {self.colors['disabled_text']};
            }}

            /* SCROLLBARS */
            QScrollBar:vertical {{
                background: {self.colors['scroll_track_background']};
                width: 12px;
                border-radius: 6px;
                margin: 0px;
            }}

            QScrollBar::handle:vertical {{
                background: {self.colors['scroll_handle_background']};
                min-height: 20px;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {self.colors['scroll_handle_hover']};
            }}

            QScrollBar::handle:vertical:pressed {{
                background: {self.colors['scroll_handle_pressed']};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}

            QScrollBar:horizontal {{
                background: {self.colors['scroll_track_background']};
                height: 12px;
                border-radius: 6px;
                margin: 0px;
            }}

            QScrollBar::handle:horizontal {{
                background: {self.colors['scroll_handle_background']};
                min-width: 20px;
                border-radius: 6px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background: {self.colors['scroll_handle_hover']};
            }}

            QScrollBar::handle:horizontal:pressed {{
                background: {self.colors['scroll_handle_pressed']};
            }}

            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
            }}

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}

            /* SCROLL AREAS */
            QScrollArea {{
                border: 1px solid {self.colors['border_color']};
                border-radius: 4px;
                background-color: {self.colors['scroll_area_background']};
            }}

            QScrollArea > QWidget {{
                background-color: {self.colors['scroll_area_background']};
            }}

            /* TABLE VIEWS */
            QTableView, QTableWidget {{
                background-color: {self.colors['table_background']};
                color: {self.colors['table_text']};
                alternate-background-color: {self.colors['table_alternate_background']};
                gridline-color: transparent;
                border: none;
                border-radius: 8px;
                selection-background-color: {self.colors['table_selection_background']};
                selection-color: {self.colors['table_selection_text']};
                outline: none;
            }}

            QTableView::item, QTableWidget::item {{
                border: none;
                background-color: transparent;
                color: {self.colors['table_text']};
                padding: 2px 4px;
                min-height: 16px;
            }}

            QTableWidget::item:hover {{
                background-color: {self.colors['table_hover_background']};
            }}

            QTableWidget::item:selected {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
            }}

            /* TREE VIEWS */
            QTreeView {{
                background-color: {self.colors['table_background']};
                color: {self.colors['table_text']};
                alternate-background-color: {self.colors['table_alternate_background']};
                font-size: {self.fonts['tree_size']};
                border: none;
                outline: none;
                selection-background-color: {self.colors['table_selection_background']};
                selection-color: {self.colors['table_selection_text']};
                show-decoration-selected: 1;
            }}

            QTreeView::item {{
                border: none;
                background-color: transparent;
                color: {self.colors['table_text']};
                padding: 2px 4px;
                min-height: 18px;
            }}

            QTreeView::item:alternate {{
                background-color: {self.colors['table_alternate_background']};
            }}

            QTreeView::item:hover {{
                background-color: {self.colors['table_hover_background']};
                color: {self.colors['table_text']};
                border: none;
            }}

            QTreeView::item:selected {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
                border: none;
            }}

            QTreeView::item:selected:hover {{
                background-color: {self.colors['highlight_light_blue']};
                color: {self.colors['table_selection_text']};
                border: none;
            }}

            QTreeView::item:selected:focus {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
                border: none;
                outline: none;
            }}

            /* Tree view branch styling - ensure selection spans entire row */
            QTreeView::branch {{
                background-color: {self.colors['table_background']};
                color: transparent;
                border: none;
                outline: 0;
            }}

            QTreeView::branch:selected {{
                background-color: {self.colors['table_selection_background']};
                color: transparent;
                border: none;
            }}

            QTreeView::branch:hover {{
                background-color: {self.colors['table_hover_background']};
                color: transparent;
                border: none;
            }}

            QTreeView::branch:selected:hover {{
                background-color: {self.colors['highlight_light_blue']};
                color: transparent;
                border: none;
            }}

            QTreeView::branch:has-siblings:!adjoins-item {{
                border-image: none;
                image: none;
            }}

            QTreeView::branch:has-siblings:adjoins-item {{
                border-image: none;
                image: none;
            }}

            QTreeView::branch:!has-children:!has-siblings:adjoins-item {{
                border-image: none;
                image: none;
            }}

            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                image: url(resources/icons/feather_icons/chevron-right.svg);
                padding: 2px;
            }}

            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                image: url(resources/icons/feather_icons/chevron-down.svg);
                padding: 2px;
            }}

            /* HEADER VIEWS */
            QHeaderView {{
                background-color: {self.colors['table_header_background']};
                color: {self.colors['table_text']};
                border: none;
                border-bottom: 1px solid {self.colors['border_color']};
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['medium_weight']};
                padding: 0px;
            }}

            QHeaderView::section {{
                background-color: {self.colors['table_header_background']};
                color: {self.colors['table_text']};
                border: none;
                border-right: 1px solid {self.colors['border_color']};
                padding: 4px 8px;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['medium_weight']};
                text-align: left;
            }}

            QHeaderView::section:hover {{
                background-color: {self.colors['table_hover_background']};
                color: {self.colors['table_text']};
            }}

            QHeaderView::section:pressed {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
            }}

            QHeaderView::section:first {{
                border-left: none;
            }}

            QHeaderView::section:last {{
                border-right: none;
            }}

            QHeaderView::down-arrow {{
                image: url(resources/icons/feather_icons/chevron-down.svg);
                width: 12px;
                height: 12px;
                padding-right: 4px;
            }}

            QHeaderView::up-arrow {{
                image: url(resources/icons/feather_icons/chevron-up.svg);
                width: 12px;
                height: 12px;
                padding-right: 4px;
            }}

            /* FileTreeView specific styling */
            FileTreeView::item:hover {{
                background-color: {self.colors['table_hover_background']};
                color: {self.colors['table_text']};
                border: none;
            }}

            FileTreeView::item:selected {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
                border: none;
            }}

            FileTreeView::item:selected:hover {{
                background-color: {self.colors['highlight_light_blue']};
                color: {self.colors['table_selection_text']};
                border: none;
            }}

            FileTreeView::branch:hover {{
                background-color: {self.colors['table_hover_background']} !important;
                color: transparent !important;
                border: none !important;
            }}

            FileTreeView::branch:selected {{
                background-color: {self.colors['table_selection_background']} !important;
                color: transparent !important;
                border: none !important;
            }}

            FileTreeView::branch:selected:hover {{
                background-color: {self.colors['highlight_light_blue']} !important;
                color: transparent !important;
                border: none !important;
            }}

            /* MetadataTreeView specific styling */
            MetadataTreeView {{
                color: {self.colors['table_text']};
                background-color: {self.colors['table_background']};
            }}

            MetadataTreeView[placeholder="false"] {{
                color: {self.colors['table_text']} !important;
                background-color: {self.colors['table_background']} !important;
            }}

            MetadataTreeView[placeholder="false"]::item {{
                color: {self.colors['table_text']} !important;
                background-color: transparent;
            }}

            MetadataTreeView[placeholder="false"]::item:hover {{
                background-color: {self.colors['table_hover_background']} !important;
                color: {self.colors['table_text']} !important;
                border: none;
            }}

            MetadataTreeView[placeholder="false"]::item:selected {{
                background-color: {self.colors['table_selection_background']} !important;
                color: {self.colors['table_selection_text']} !important;
                border: none;
            }}

            MetadataTreeView[placeholder="false"]::item:selected:hover {{
                background-color: {self.colors['highlight_light_blue']} !important;
                color: {self.colors['table_selection_text']} !important;
                border: none;
            }}

            MetadataTreeView[placeholder="true"]::item {{
                color: gray;
                selection-background-color: transparent;
                background-color: transparent;
            }}

            MetadataTreeView[placeholder="true"]::item:hover {{
                background-color: transparent !important;
                color: gray !important;
                border: none !important;
            }}

            MetadataTreeView[placeholder="true"]::item:selected {{
                background-color: transparent !important;
                color: gray !important;
                border: none !important;
            }}

            /* CHECKBOXES */
            QCheckBox {{
                color: {self.colors['app_text']};
                spacing: 8px;
                font-size: {self.fonts['interface_size']};
            }}

            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {self.colors['input_border']};
                border-radius: 3px;
                background-color: {self.colors['input_background']};
            }}

            QCheckBox::indicator:unchecked {{
                image: url(resources/icons/feather_icons/square.svg);
                background-color: {self.colors['input_background']};
                border-color: {self.colors['input_border']};
            }}

            QCheckBox::indicator:checked {{
                image: url(resources/icons/feather_icons/check-square.svg);
                background-color: {self.colors['input_background']};
                border-color: {self.colors['input_border']};
            }}

            QCheckBox::indicator:hover {{
                border-color: {self.colors['input_border_hover']};
                background-color: {self.colors['input_background_hover']};
            }}

            QCheckBox::indicator:focus {{
                border-color: {self.colors['input_border_focus']};
                background-color: {self.colors['input_background_focus']};
            }}

            /* FINAL TRANSFORM CONTAINER COMBOBOX STYLING */
            FinalTransformContainer QComboBox {{
                background-color: {self.colors['combo_background']};
                border: 1px solid {self.colors['combo_border']};
                border-radius: 4px;
                color: {self.colors['combo_text']};
                padding: 2px 6px;
                min-height: 18px;
                margin: 0px;
                font-size: {self.fonts['interface_size']};
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
            }}

            FinalTransformContainer QComboBox:hover {{
                background-color: {self.colors['combo_background_hover']};
                border-color: {self.colors['input_border_hover']};
            }}

            FinalTransformContainer QComboBox:focus {{
                border-color: {self.colors['input_border_focus']};
                background-color: {self.colors['combo_background_hover']};
                outline: none;
            }}

            FinalTransformContainer QComboBox QAbstractItemView {{
                background-color: {self.colors['combo_dropdown_background']};
                color: {self.colors['combo_text']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 6px;
                outline: none;
                selection-background-color: {self.colors['combo_item_background_selected']};
                selection-color: {self.colors['input_selection_text']};
                font-size: {self.fonts['interface_size']};
                margin: 0px;
                padding: 0px;
            }}

            FinalTransformContainer QComboBox QAbstractItemView::item {{
                background-color: transparent;
                color: {self.colors['combo_text']};
                padding: 6px 8px;
                border: none;
                min-height: 18px;
                border-radius: 3px;
                margin: 1px;
            }}

            FinalTransformContainer QComboBox QAbstractItemView::item:hover {{
                background-color: {self.colors['combo_item_background_hover']};
                color: {self.colors['combo_text']};
                border-radius: 3px;
            }}

            FinalTransformContainer QComboBox QAbstractItemView::item:selected {{
                background-color: {self.colors['combo_item_background_selected']};
                color: {self.colors['input_selection_text']};
                border-radius: 3px;
            }}

            /* FinalTransformContainer specific checkbox styling */
            FinalTransformContainer QCheckBox {{
                color: {self.colors['app_text']};
                font-size: {self.fonts['interface_size']};
                spacing: 8px;
            }}

            FinalTransformContainer QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {self.colors['input_border']};
                border-radius: 3px;
                background-color: {self.colors['input_background']};
            }}

            FinalTransformContainer QCheckBox::indicator:unchecked {{
                image: url(resources/icons/feather_icons/square.svg);
                background-color: {self.colors['input_background']};
                border-color: {self.colors['input_border']};
            }}

            FinalTransformContainer QCheckBox::indicator:checked {{
                image: url(resources/icons/feather_icons/check-square.svg);
                background-color: {self.colors['input_background']};
                border-color: {self.colors['input_border']};
            }}

            FinalTransformContainer QCheckBox::indicator:hover {{
                border-color: {self.colors['input_border_hover']};
                background-color: {self.colors['input_background_hover']};
            }}

            /* Greeklish checkbox */
            FinalTransformContainer QCheckBox[objectName="greeklish_checkbox"]::indicator:focus {{
                border-color: {self.colors['input_border']};
                background-color: {self.colors['input_background']};
            }}

            /* SPECIFIED TEXT AND COUNTER MODULE STYLING */
            QWidget[objectName*="SpecifiedText"] QLineEdit,
            QWidget[objectName*="Counter"] QLineEdit {{
                background-color: {self.colors['input_background']};
                border: 2px solid {self.colors['input_border']};
                border-radius: 4px;
                color: {self.colors['input_text']};
                padding: 3px 8px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
                min-height: 18px;
                font-size: {self.fonts['interface_size']};
                margin: 1px;
            }}

            QWidget[objectName*="SpecifiedText"] QLineEdit:hover,
            QWidget[objectName*="Counter"] QLineEdit:hover {{
                background-color: {self.colors['input_background_hover']};
                border-color: {self.colors['input_border_hover']};
            }}

            QWidget[objectName*="SpecifiedText"] QLineEdit:focus,
            QWidget[objectName*="Counter"] QLineEdit:focus {{
                border-color: {self.colors['input_border_focus']};
                background-color: {self.colors['input_background_focus']};
            }}

            QWidget[objectName*="SpecifiedText"] QLineEdit[error="true"],
            QWidget[objectName*="Counter"] QLineEdit[error="true"] {{
                border: 2px solid #cc4444;
                background-color: #3d1e1e;
                color: #ffaaaa;
                margin: 1px;
            }}

            /* Counter and Metadata module layouts */
            QWidget[objectName*="Counter"] QHBoxLayout,
            QWidget[objectName*="Metadata"] QHBoxLayout {{
                spacing: 4px;
                margin: 3px;
            }}

            QWidget[objectName*="Counter"] QLabel {{
                background-color: transparent;
                color: {self.colors['app_text']};
                border: none;
                padding: 2px 4px;
                margin: 1px;
                font-size: {self.fonts['interface_size']};
            }}

            /* COUNTER MODULE INPUT FIELDS */
            CounterModule QLineEdit {{
                background-color: {self.colors['input_background']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                color: {self.colors['input_text']};
                padding: 2px 6px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
                min-height: 18px;
                font-size: {self.fonts['interface_size']};
                text-align: right;
                qproperty-alignment: AlignRight;
            }}

            /* SPLITTERS */
            QSplitter {{
                background-color: {self.colors['app_background']};
            }}

            QSplitter::handle {{
                background-color: {self.colors['separator_background']};
            }}

            QSplitter::handle:horizontal {{
                width: 6px;
                margin: 0px;
            }}

            QSplitter::handle:vertical {{
                height: 6px;
                margin: 0px;
            }}

            QSplitter::handle:hover {{
                background-color: {self.colors['separator_light']};
            }}

            /* RENAME MODULES AREA */
            QScrollArea[objectName="rename_modules_scroll"] {{
                border: 4px solid #444444 !important;
                border-radius: 8px;
                background-color: {self.colors['scroll_area_background']} !important;
            }}

            QScrollArea[objectName="rename_modules_scroll"] QAbstractScrollArea::viewport {{
                background-color: {self.colors['scroll_area_background']} !important;
            }}

            QWidget[objectName="scroll_content_widget"] {{
                background-color: transparent;
            }}

            /* FOOTER SEPARATOR */
            QFrame[objectName="footerSeparator"] {{
                background-color: {self.colors['separator_background']};
                border: none;
                max-height: 4px;
                min-height: 4px;
            }}

            /* TOOLTIPS */
            QToolTip {{
                background-color: {self.colors['tooltip_background']};
                color: {self.colors['tooltip_text']};
                border: 1px solid {self.colors['tooltip_border']};
                border-radius: 6px;
                padding: 2px 4px;
                font-size: {self.fonts['interface_size']};
            }}

            /* Custom Error Tooltip */
            .ErrorTooltip {{
                background-color: {self.colors['tooltip_error_background']};
                color: {self.colors['tooltip_error_text']};
                border: 1px solid {self.colors['tooltip_error_border']};
                border-radius: 6px;
                padding: 2px 4px;
                font-size: {self.fonts['interface_size']};
                font-weight: normal;
            }}

            /* Custom Warning Tooltip */
            .WarningTooltip {{
                background-color: {self.colors['tooltip_warning_background']};
                color: {self.colors['tooltip_warning_text']};
                border: 1px solid {self.colors['tooltip_warning_border']};
                border-radius: 6px;
                padding: 2px 4px;
                font-size: {self.fonts['interface_size']};
                font-weight: normal;
            }}

            /* Custom Info Tooltip */
            .InfoTooltip {{
                background-color: {self.colors['tooltip_info_background']};
                color: {self.colors['tooltip_info_text']};
                border: 1px solid {self.colors['tooltip_info_border']};
                border-radius: 6px;
                padding: 2px 4px;
                font-size: {self.fonts['interface_size']};
                font-weight: normal;
            }}

            /* Custom Success Tooltip */
            .SuccessTooltip {{
                background-color: {self.colors['tooltip_success_background']};
                color: {self.colors['tooltip_success_text']};
                border: 1px solid {self.colors['tooltip_success_border']};
                border-radius: 6px;
                padding: 2px 4px;
                font-size: {self.fonts['interface_size']};
                font-weight: normal;
            }}

            /* CONTEXT MENUS */
            QMenu {{
                background-color: #232323;
                color: {self.colors['dialog_text']};
                border: none;
                border-radius: 8px;
                padding: 4px;
                font-size: {self.fonts['interface_size']};
            }}

            QMenu::item {{
                background-color: transparent;
                color: {self.colors['dialog_text']};
                padding: 6px 16px;
                border-radius: 6px;
                margin: 1px;
                font-size: {self.fonts['interface_size']};
            }}

            QMenu::item:hover {{
                background-color: {self.colors['table_hover_background']};
                color: {self.colors['dialog_text']};
                border-radius: 6px;
            }}

            QMenu::item:selected {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['input_selection_text']};
                border-radius: 6px;
            }}

            QMenu::item:pressed {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['input_selection_text']};
                border-radius: 6px;
            }}

            QMenu::item:disabled {{
                color: #555555;
                background-color: transparent;
            }}

            QMenu::separator {{
                background-color: #5a5a5a;
                height: 1px;
                margin: 2px 8px;
            }}

            /* DIALOGS */
            QDialog {{
                background-color: #232323;
                color: {self.colors['dialog_text']};
            }}

            /* TABS */
            QTabWidget::pane {{
                border: 1px solid {self.colors['border_color']};
                background-color: {self.colors['app_background']};
            }}

            QTabBar::tab {{
                background-color: {self.colors['button_background']};
                color: {self.colors['button_text']};
                border: 1px solid {self.colors['border_color']};
                padding: 6px 12px;
                margin-right: 2px;
                font-size: {self.fonts['interface_size']};
            }}

            QTabBar::tab:selected {{
                background-color: {self.colors['accent_color']};
                color: {self.colors['input_selection_text']};
                border-bottom: 2px solid {self.colors['accent_color']};
            }}

            QTabBar::tab:hover:!selected {{
                background-color: {self.colors['button_background_hover']};
            }}

            /* Force background for any potential container */
            QComboBox QAbstractItemView * {{
                background-color: {self.colors['combo_dropdown_background']} !important;
            }}

            /* Target any potential frame or container inside dropdown */
            QComboBox QFrame {{
                background-color: {self.colors['combo_dropdown_background']} !important;
                border: none !important;
                margin: 0px !important;
                padding: 0px !important;
            }}

            QComboBox QWidget {{
                background-color: {self.colors['combo_dropdown_background']} !important;
            }}

            /* Force remove any potential white space at top/bottom */
            QComboBox QAbstractItemView::item:first-child {{
                margin-top: 0px !important;
                padding-top: 6px !important;
            }}

            QComboBox QAbstractItemView::item:last-child {{
                margin-bottom: 0px !important;
                padding-bottom: 6px !important;
            }}

            /* Simplified styling for all combo boxes within rename modules */
            QWidget[class="RenameModule"] QComboBox QAbstractItemView {{
                padding: 4px; /* Add some padding to the dropdown view */
                margin: 0px;
            }}

            QWidget[class="RenameModule"] QComboBox QAbstractItemView::item {{
                margin: 0px; /* Remove margin from items */
                padding: 4px 8px; /* Control spacing with padding */
            }}

        """

    def get_color(self, color_key: str) -> str:
        """Get a color value by key."""
        return self.colors.get(color_key, "#ffffff")

    def set_theme(self, theme_name: str):
        """Change theme (for future expansion)."""
        self.theme_name = theme_name

    def apply_windows_font_fixes(self, main_window: QMainWindow):
        """Apply Windows-specific font fixes."""

    def _apply_windows_combobox_fixes(self, app: QApplication):
        """Apply Windows-specific ComboBox dropdown fixes."""
        from core.pyqt_imports import QComboBox

        for widget in app.allWidgets():
            if isinstance(widget, QComboBox):
                widget.setStyleSheet(
                    f"""
                    QComboBox {{
                        background-color: {self.colors['combo_background']};
                        border: 1px solid {self.colors['combo_border']};
                        border-radius: 4px;
                        color: {self.colors['combo_text']};
                        padding: 2px 6px;
                        min-height: 18px;
                        font-size: {self.fonts['interface_size']};
                    }}

                    QComboBox:hover {{
                        background-color: {self.colors['combo_background_hover']};
                        border-color: {self.colors['input_border_hover']};
                    }}

                    QComboBox:focus {{
                        border-color: {self.colors['input_border_focus']};
                        background-color: {self.colors['combo_background_hover']};
                    }}

                    QComboBox QAbstractItemView {{
                        background-color: {self.colors['combo_dropdown_background']} !important;
                        color: {self.colors['combo_text']} !important;
                        border: 1px solid {self.colors['input_border']} !important;
                        border-radius: 6px !important;
                        outline: none !important;
                        selection-background-color: {self.colors['combo_item_background_selected']} !important;
                        selection-color: {self.colors['input_selection_text']} !important;
                        font-size: {self.fonts['interface_size']} !important;
                        margin: 0px !important;
                        padding: 0px !important;
                    }}

                    QComboBox QAbstractItemView::item {{
                        background-color: transparent !important;
                        color: {self.colors['combo_text']} !important;
                        padding: 6px 8px !important;
                        border: none !important;
                        min-height: 18px !important;
                        border-radius: 3px !important;
                        margin: 1px !important;
                    }}

                    QComboBox QAbstractItemView::item:hover {{
                        background-color: {self.colors['combo_item_background_hover']} !important;
                        color: {self.colors['combo_text']} !important;
                    }}

                    QComboBox QAbstractItemView::item:selected {{
                        background-color: {self.colors['combo_item_background_selected']} !important;
                        color: {self.colors['input_selection_text']} !important;
                    }}
                """
                )
