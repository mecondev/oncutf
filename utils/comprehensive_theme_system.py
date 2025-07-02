"""
Comprehensive theme system for OnCutF application.
Extracts all colors from existing QSS files for complete QSS migration.
"""

from typing import Dict, Union
from core.qt_imports import QColor, QWidget, QScrollArea, QApplication, QLineEdit, QComboBox, QPushButton
import config


class ComprehensiveThemeColors:
    """Complete color definitions extracted from existing QSS files."""

    # All colors extracted from dark theme QSS files
    DARK = {
                # Base application colors
        'app_background': '#212121',
        'app_text': '#f0ebd8',

        # Input field colors
        'input_background': '#181818',
        'input_text': '#f0ebd8',
        'input_border': '#3a3b40',
        'input_border_hover': '#555555',
        'input_border_focus': '#748cab',
        'input_background_hover': '#1f1f1f',
        'input_background_focus': '#1a1a1a',
        'input_selection_bg': '#748cab',
        'input_selection_text': '#0d1321',

        # Button colors
        'button_background': '#2a2a2a',
        'button_text': '#f0ebd8',
        'button_background_hover': '#3e5c76',
        'button_background_pressed': '#748cab',
        'button_text_pressed': '#0d1321',
        'button_background_disabled': '#232323',
        'button_text_disabled': '#888888',
        'button_border': '#3a3b40',

        # ComboBox colors
        'combo_background': '#2a2a2a',
        'combo_text': '#f0ebd8',
        'combo_background_hover': '#3e5c76',
        'combo_background_pressed': '#748cab',
        'combo_text_pressed': '#0d1321',
        'combo_background_selected_hover': '#8a9bb4',
        'combo_dropdown_background': '#181818',
        'combo_item_background_hover': '#3e5c76',
        'combo_item_background_selected': '#748cab',
        'combo_border': '#3a3b40',

        # Table/Tree view colors
        'table_background': '#181818',
        'table_text': '#f0ebd8',
        'table_alternate_background': '#1f1f1f',
        'table_selection_background': '#748cab',
        'table_selection_text': '#0d1321',
        'table_header_background': '#181818',
        'table_hover_background': '#3e5c76',

        # Scroll area colors
        'scroll_area_background': '#181818',
        'scroll_track_background': '#2c2c2c',
        'scroll_handle_background': '#555555',
        'scroll_handle_hover': '#4a6fa5',
        'scroll_handle_pressed': '#748cab',

        # Module/Card colors
        'module_background': '#181818',
        'module_border': '#3a3b40',
        'module_border_hover': '#555555',
        'module_border_focus': '#748cab',

        # Dialog colors
        'dialog_background': '#2a2a2a',
        'dialog_text': '#f0ebd8',

        # Tooltip colors
        'tooltip_background': '#2b2b2b',
        'tooltip_text': '#f0ebd8',
        'tooltip_border': '#555555',
        'tooltip_error_background': '#3d1e1e',
        'tooltip_error_text': '#ffaaaa',
        'tooltip_error_border': '#cc4444',
        'tooltip_warning_background': '#3d3d1e',
        'tooltip_warning_text': '#ffffaa',
        'tooltip_warning_border': '#cccc44',
        'tooltip_info_background': '#1e2d3d',
        'tooltip_info_text': '#aaccff',
        'tooltip_info_border': '#4488cc',
        'tooltip_success_background': '#1e3d1e',
        'tooltip_success_text': '#aaffaa',
        'tooltip_success_border': '#44cc44',

        # Separator colors
        'separator_background': '#444444',
        'separator_light': '#555555',
        'separator_dark': '#3a3b40',

        # Special colors
        'highlight_blue': '#4a6fa5',
        'highlight_light_blue': '#8a9bb4',
        'accent_color': '#748cab',
        'muted_text': '#888888',
        'border_color': '#3a3b40',
        'border_hover': '#555555',
        'border_focus': '#666666',

        # Extra colors found in QSS files
        'very_dark_background': '#0d1321',
        'medium_background': '#2c2c2c',
        'bright_background': '#5a5a5a',
        'light_border': '#666666',
        'disabled_background': '#181818',
        'disabled_text': '#888888',
    }


class ComprehensiveThemeApplier:
    """Applies comprehensive theming to all UI elements."""

    def __init__(self, theme_name: str = "dark"):
        self.theme_name = theme_name or config.THEME_NAME
        self.colors = ComprehensiveThemeColors.DARK  # Only dark for now

    def apply_to_scroll_area(self, scroll_area: QScrollArea):
        """Apply complete scroll area styling."""
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: 2px solid {self.colors['module_border']};
                border-radius: 8px;
                background-color: {self.colors['scroll_area_background']};
            }}
            QScrollArea > QWidget {{
                background-color: {self.colors['scroll_area_background']};
            }}
            QScrollArea QScrollBar:vertical {{
                background: {self.colors['scroll_track_background']};
                width: 12px;
                border-radius: 6px;
                margin: 0px;
            }}
            QScrollArea QScrollBar::handle:vertical {{
                background: {self.colors['scroll_handle_background']};
                min-height: 20px;
                border-radius: 6px;
            }}
            QScrollArea QScrollBar::handle:vertical:hover {{
                background: {self.colors['scroll_handle_hover']};
            }}
            QScrollArea QScrollBar::handle:vertical:pressed {{
                background: {self.colors['scroll_handle_pressed']};
            }}
            QScrollArea QScrollBar::add-line:vertical,
            QScrollArea QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 22px;
            }}
        """)

        # Also set palette as backup
        palette = scroll_area.palette()
        palette.setColor(scroll_area.backgroundRole(), QColor(self.colors['scroll_area_background']))
        scroll_area.setPalette(palette)
        scroll_area.setAutoFillBackground(True)

    def apply_to_module_widget(self, widget: QWidget):
        """Apply complete module widget styling."""
        widget.setStyleSheet(f"""
            QWidget[objectName="RenameModuleWidget"] {{
                background-color: {self.colors['module_background']};
                border: 1px solid {self.colors['module_border']};
                border-radius: 6px;
                margin: 4px;
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox {{
                background-color: {self.colors['input_background']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                color: {self.colors['input_text']};
                padding: 2px 8px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox:hover {{
                background-color: {self.colors['input_background_hover']};
                border-color: {self.colors['input_border_hover']};
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox:focus {{
                border-color: {self.colors['input_border_focus']};
                background-color: {self.colors['input_background_focus']};
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox::drop-down {{
                border: none;
                background-color: transparent;
                width: 20px;
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox::down-arrow {{
                image: url(resources/icons/feather_icons/chevron-down.svg);
                width: 12px;
                height: 12px;
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox QAbstractItemView {{
                background-color: {self.colors['combo_dropdown_background']};
                color: {self.colors['combo_text']};
                selection-background-color: {self.colors['combo_item_background_selected']};
                selection-color: {self.colors['input_selection_text']};
                border: 1px solid {self.colors['input_border']};
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox QAbstractItemView::item {{
                padding: 4px;
                border: none;
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox QAbstractItemView::item:hover {{
                background-color: {self.colors['combo_item_background_hover']};
                color: {self.colors['combo_text']};
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox QAbstractItemView::item:selected {{
                background-color: {self.colors['combo_item_background_selected']};
                color: {self.colors['input_selection_text']};
            }}
            QWidget[objectName="RenameModuleWidget"] QLineEdit {{
                background-color: {self.colors['input_background']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                color: {self.colors['input_text']};
                padding: 2px 6px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
            }}
            QWidget[objectName="RenameModuleWidget"] QLineEdit:hover {{
                background-color: {self.colors['input_background_hover']};
                border-color: {self.colors['input_border_hover']};
            }}
            QWidget[objectName="RenameModuleWidget"] QLineEdit:focus {{
                border-color: {self.colors['input_border_focus']};
                background-color: {self.colors['input_background_focus']};
            }}
            QWidget[objectName="RenameModuleWidget"] QPushButton {{
                background-color: {self.colors['button_background']};
                border: 1px solid {self.colors['button_border']};
                border-radius: 4px;
                color: {self.colors['button_text']};
                padding: 2px 8px;
                min-height: 20px;
            }}
            QWidget[objectName="RenameModuleWidget"] QPushButton:hover {{
                background-color: {self.colors['button_background_hover']};
                border-color: {self.colors['input_border_focus']};
            }}
            QWidget[objectName="RenameModuleWidget"] QPushButton:pressed {{
                background-color: {self.colors['button_background_pressed']};
                color: {self.colors['button_text_pressed']};
            }}
            QWidget[objectName="RenameModuleWidget"] QPushButton:disabled {{
                background-color: {self.colors['button_background_disabled']};
                color: {self.colors['button_text_disabled']};
                border-color: {self.colors['separator_dark']};
            }}
            QWidget[objectName="RenameModuleWidget"] QLabel {{
                color: {self.colors['input_text']};
                background-color: transparent;
            }}
        """)

    def apply_to_application(self, app: QApplication):
        """Apply base application styling."""
        app.setStyleSheet(f"""
            QApplication {{
                background-color: {self.colors['app_background']};
                color: {self.colors['app_text']};
            }}
        """)

    def apply_to_main_window(self, window: QWidget):
        """Apply main window styling."""
        window.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['app_background']};
                color: {self.colors['app_text']};
            }}
            QWidget {{
                background-color: {self.colors['app_background']};
                color: {self.colors['app_text']};
            }}
        """)

    def set_theme(self, theme_name: str):
        """Change theme (for future expansion)."""
        self.theme_name = theme_name
        # For now only dark theme supported
        self.colors = ComprehensiveThemeColors.DARK
