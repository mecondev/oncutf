"""
Programmatic Theme Manager for OnCutF application.
Replaces all QSS files with Python-based styling for better cross-platform compatibility.
"""

from typing import Dict, Optional, List, Any
from core.qt_imports import (
    QApplication, QWidget, QMainWindow, QScrollArea, QLineEdit, QComboBox,
    QPushButton, QLabel, QTableView, QTreeView, QDialog, QSplitter,
    QGroupBox, QCheckBox, QFrame
)
from utils.comprehensive_theme_system import ComprehensiveThemeColors
from utils.fonts import get_inter_family, get_inter_css_weight
import config
import platform


class ThemeEngine:
    """
    Complete theme manager that replaces all QSS files with programmatic styling.
    Handles all UI components with precise control over styling.
    """

    def __init__(self, theme_name: str = "dark"):
        self.theme_name = theme_name or config.THEME_NAME
        self.colors = ComprehensiveThemeColors.DARK  # Only dark for now

        # Font definitions using Inter fonts with platform-specific adjustments
        is_windows = platform.system() == "Windows"

        # Adjust font sizes and weights for Windows compatibility
        base_size = '8pt' if is_windows else '9pt'
        tree_size = '9pt' if is_windows else '10pt'
        base_weight = 300 if is_windows else get_inter_css_weight('base')  # Lighter on Windows

        # Font family with Windows-specific fallbacks
        base_family = get_inter_family('base')
        if is_windows:
            # Add Windows-specific fallbacks for better rendering
            font_fallback = f'"{base_family}", "Segoe UI", "Tahoma", "Arial", sans-serif'
        else:
            font_fallback = f'"{base_family}", "Segoe UI", "Arial", sans-serif'

        self.fonts = {
            'base_family': base_family,
            'font_fallback': font_fallback,
            'medium_family': get_inter_family('medium'),
            'semibold_family': get_inter_family('headers'),
            'base_weight': base_weight,
            'medium_weight': get_inter_css_weight('medium'),
            'semibold_weight': get_inter_css_weight('headers'),
            'base_size': base_size,
            'interface_size': base_size,
            'tree_size': tree_size,
            'small_size': '7pt' if is_windows else '8pt',
            'large_size': '10pt' if is_windows else '11pt',
            'title_size': '13pt' if is_windows else '14pt'
        }

    def apply_complete_theme(self, app: QApplication, main_window: QMainWindow):
        """Apply complete theming to the entire application."""
        # Clear any existing stylesheets
        app.setStyleSheet("")
        main_window.setStyleSheet("")

        # Apply base application styling
        self._apply_base_styling(app, main_window)

                # Apply component-specific styling
        self._apply_input_styling(main_window)
        self._apply_button_styling(main_window)
        self._apply_combo_box_styling(main_window)
        self._apply_table_view_styling(main_window)
        self._apply_tree_view_styling(main_window)
        self._apply_scroll_area_styling(main_window)
        self._apply_dialog_styling(main_window)
        self._apply_context_menu_styling()
        self._apply_tooltip_styling()

        # Apply Windows-specific font fixes
        self.apply_windows_font_fixes(main_window)

    def _apply_base_styling(self, app: QApplication, main_window: QMainWindow):
        """Apply base application and main window styling (replaces base.qss)."""
        base_style = f"""
            QMainWindow {{
                background-color: {self.colors['app_background']};
                color: {self.colors['app_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['base_size']};
                font-weight: {self.fonts['base_weight']};
            }}

            QWidget {{
                background-color: {self.colors['app_background']};
                color: {self.colors['app_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['base_size']};
                font-weight: {self.fonts['base_weight']};
            }}

            QLabel {{
                background-color: transparent;
                color: {self.colors['app_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['base_size']};
                font-weight: {self.fonts['base_weight']};
                border: none;
                border-radius: 0px;
                padding: 2px;
                margin: 0px;
            }}

            QFrame {{
                border: none;
                background-color: {self.colors['app_background']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
            }}

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

            /* Footer separator styling */
            QFrame[objectName="footerSeparator"] {{
                background-color: {self.colors['separator_background']};
                border: none;
                min-height: 4px;
                max-height: 4px;
            }}

            QTabWidget::pane {{
                border: 1px solid {self.colors['border_color']};
                background-color: {self.colors['app_background']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
            }}

            QTabWidget::tab-bar {{
                alignment: center;
            }}

            QTabBar::tab {{
                background-color: {self.colors['button_background']};
                color: {self.colors['button_text']};
                border: 1px solid {self.colors['border_color']};
                padding: 6px 12px;
                margin-right: 2px;
                font-family: "{self.fonts['medium_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['medium_weight']};
            }}

            QTabBar::tab:selected {{
                background-color: {self.colors['accent_color']};
                color: {self.colors['input_selection_text']};
                border-bottom: 2px solid {self.colors['accent_color']};
            }}

            QTabBar::tab:hover:!selected {{
                background-color: {self.colors['button_background_hover']};
            }}

            /* Global scrollbar styling for all widgets */
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
                border-radius: 0px;
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
                border-radius: 0px;
            }}

            /* Remove page step background */
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """

        app.setStyleSheet(base_style)

    def _apply_input_styling(self, parent: QWidget):
        """Apply input field styling (replaces parts of dialogs.qss and base.qss)."""
        input_style = f"""
            QLineEdit {{
                background-color: {self.colors['input_background']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                color: {self.colors['input_text']};
                padding: 4px 8px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
                min-height: 20px;
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['base_weight']};
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
                border-color: {self.colors['border_color']};
            }}

            /* Specific styling for metadata search field */
            QLineEdit#metadataSearchField {{
                background-color: {self.colors['input_background']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                color: {self.colors['input_text']};
                padding: 2px 8px;
                min-height: 16px;
                max-height: 18px;
                margin-top: 0px;
                margin-bottom: 2px;
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['base_weight']};
            }}

            QLineEdit#metadataSearchField:enabled:hover {{
                background-color: {self.colors['input_background_hover']};
                border-color: {self.colors['input_border_hover']};
            }}

            QLineEdit#metadataSearchField:enabled:focus {{
                border-color: {self.colors['input_border_focus']};
                background-color: {self.colors['input_background_focus']};
            }}

            QLineEdit#metadataSearchField:disabled {{
                background-color: {self.colors['disabled_background']};
                color: {self.colors['disabled_text']};
                border-color: {self.colors['border_color']};
            }}

            QLineEdit#metadataSearchField:disabled:hover {{
                background-color: {self.colors['disabled_background']};
                color: {self.colors['disabled_text']};
                border-color: {self.colors['border_color']};
            }}

            QTextEdit, QPlainTextEdit {{
                background-color: {self.colors['input_background']};
                color: {self.colors['input_text']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 8px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['base_weight']};
            }}

            QTextEdit:hover, QPlainTextEdit:hover {{
                background-color: {self.colors['input_background_hover']};
                border-color: {self.colors['input_border_hover']};
            }}

            QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {self.colors['input_border_focus']};
                background-color: {self.colors['input_background_focus']};
            }}
        """

        # Apply to all input widgets
        for widget in parent.findChildren(QLineEdit):
            widget.setStyleSheet(input_style)

    def _apply_button_styling(self, parent: QWidget):
        """Apply button styling (replaces buttons.qss)."""
        button_style = f"""
            QPushButton {{
                background-color: {self.colors['button_background']};
                border: none;
                border-radius: 8px;
                color: {self.colors['button_text']};
                padding: 4px 12px 4px 8px;
                font-family: "{self.fonts['medium_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['medium_weight']};
            }}

            QPushButton:hover {{
                background-color: {self.colors['button_background_hover']};
                border: none;
            }}

            QPushButton:pressed {{
                background-color: {self.colors['button_background_pressed']};
                color: {self.colors['button_text_pressed']};
                border: none;
            }}

            QPushButton:disabled {{
                background-color: {self.colors['button_background_disabled']};
                color: {self.colors['button_text_disabled']};
                border: none;
            }}

            QPushButton:default {{
                border: 2px solid {self.colors['accent_color']};
                background-color: {self.colors['accent_color']};
                color: {self.colors['input_selection_text']};
                font-weight: {self.fonts['semibold_weight']};
            }}

            QPushButton:default:hover {{
                background-color: {self.colors['highlight_blue']};
                border-color: {self.colors['highlight_blue']};
            }}

            /* Specific styling for FinalTransformContainer buttons */
            FinalTransformContainer QPushButton {{
                background-color: {self.colors['button_background']};
                border: none;
                border-radius: 6px;
                color: {self.colors['button_text']};
                padding: 2px;
                margin: 0px;
                font-family: "{self.fonts['medium_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['medium_weight']};
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }}

            FinalTransformContainer QPushButton:hover {{
                background-color: {self.colors['button_background_hover']};
                border: none;
            }}

            FinalTransformContainer QPushButton:pressed {{
                background-color: {self.colors['button_background_pressed']};
                color: {self.colors['button_text_pressed']};
                border: none;
            }}

            FinalTransformContainer QPushButton:disabled {{
                background-color: {self.colors['button_background_disabled']};
                color: {self.colors['button_text_disabled']};
                border: none;
            }}

            QCheckBox {{
                color: {self.colors['app_text']};
                spacing: 8px;
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['base_weight']};
            }}

            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {self.colors['input_border']};
                border-radius: 3px;
                background-color: {self.colors['input_background']};
            }}

            QCheckBox::indicator:hover {{
                border-color: {self.colors['input_border_hover']};
                background-color: {self.colors['input_background_hover']};
            }}

            QCheckBox::indicator:checked {{
                background-color: {self.colors['accent_color']};
                border-color: {self.colors['accent_color']};
            }}

            QCheckBox::indicator:checked:hover {{
                background-color: {self.colors['highlight_blue']};
                border-color: {self.colors['highlight_blue']};
            }}
        """

        # Apply to all button widgets
        for widget in parent.findChildren(QPushButton):
            widget.setStyleSheet(button_style)
        for widget in parent.findChildren(QCheckBox):
            widget.setStyleSheet(button_style)

    def _apply_combo_box_styling(self, parent: QWidget):
        """Apply combo box styling (replaces combo_box.qss)."""
        combo_style = f"""
            QComboBox {{
                background-color: {self.colors['combo_background']};
                border: 1px solid {self.colors['combo_border']};
                border-radius: 4px;
                color: {self.colors['combo_text']};
                padding: 4px 8px;
                min-height: 20px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['base_weight']};
                margin: 0px;
            }}

            QComboBox:hover {{
                background-color: {self.colors['combo_background_hover']};
                border-color: {self.colors['input_border_hover']};
            }}

            QComboBox:focus {{
                border-color: {self.colors['input_border_focus']};
            }}

            QComboBox:on {{
                background-color: {self.colors['combo_background_pressed']};
                color: {self.colors['combo_text_pressed']};
            }}

            QComboBox::drop-down {{
                border: none;
                background-color: transparent;
                width: 20px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }}

            QComboBox::down-arrow {{
                image: url(resources/icons/feather_icons/chevron-down.svg);
                width: 12px;
                height: 12px;
            }}

            QComboBox::down-arrow:on {{
                image: url(resources/icons/feather_icons/chevron-up.svg);
            }}

            QComboBox QAbstractItemView {{
                background-color: {self.colors['combo_dropdown_background']};
                color: {self.colors['combo_text']};
                selection-background-color: {self.colors['combo_item_background_selected']};
                selection-color: {self.colors['input_selection_text']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                outline: none;
                margin: 0px;
                padding: 0px;
            }}

            QComboBox QAbstractItemView::item {{
                padding: 6px 8px;
                border: none;
                min-height: 20px;
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
                background-color: {self.colors['combo_background_selected_hover']};
                color: {self.colors['input_selection_text']};
            }}

            QComboBox QAbstractItemView::item:selected:focus {{
                background-color: {self.colors['combo_item_background_selected']};
                color: {self.colors['input_selection_text']};
            }}

            /* Comprehensive combo box dropdown styling with proper selection handling */
            QComboBox QAbstractItemView {{
                background-color: {self.colors['combo_dropdown_background']};
                color: {self.colors['combo_text']};
                selection-background-color: {self.colors['combo_item_background_selected']};
                selection-color: {self.colors['input_selection_text']};
                show-decoration-selected: 1;
            }}

            QComboBox QAbstractItemView::item {{
                background-color: transparent;
                color: {self.colors['combo_text']};
                padding: 4px 8px;
                border: none;
                min-height: 18px;
            }}

            QComboBox QAbstractItemView::item:hover {{
                background-color: {self.colors['combo_item_background_hover']};
                color: {self.colors['combo_text']};
            }}

            /* Current selected item (the one that shows in the closed ComboBox) */
            QComboBox QAbstractItemView::item:selected {{
                background-color: {self.colors['combo_item_background_selected']};
                color: {self.colors['input_selection_text']};
            }}

            /* Current item when hovering over it */
            QComboBox QAbstractItemView::item:selected:hover {{
                background-color: {self.colors['highlight_light_blue']};
                color: {self.colors['input_selection_text']};
            }}

            /* Ensure current item remains visible when not hovering */
            QComboBox QAbstractItemView::item:current {{
                background-color: {self.colors['combo_item_background_selected']};
                color: {self.colors['input_selection_text']};
                border: 1px solid {self.colors['accent_color']};
            }}

            /* Current item when hovering */
            QComboBox QAbstractItemView::item:current:hover {{
                background-color: {self.colors['highlight_light_blue']};
                color: {self.colors['input_selection_text']};
                border: 1px solid {self.colors['accent_color']};
            }}

            /* Specific styling for FinalTransformContainer combo boxes */
            FinalTransformContainer QComboBox {{
                background-color: {self.colors['combo_background']};
                border: 1px solid {self.colors['combo_border']};
                border-radius: 4px;
                color: {self.colors['combo_text']};
                padding: 2px 6px;
                min-height: 18px;
                max-height: 18px;
                min-width: 126px;
                max-width: 126px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['base_weight']};
            }}

            /* Force transparent background for FinalTransformContainer to prevent white corners */
            FinalTransformContainer {{
                background-color: transparent !important;
                border: none !important;
            }}

            FinalTransformContainer > QWidget {{
                background-color: transparent !important;
            }}

            /* Ensure combo boxes have proper background without white corners */
            FinalTransformContainer QComboBox {{
                background-color: {self.colors['combo_background']};
                border: 1px solid {self.colors['combo_border']};
                border-radius: 4px;
                color: {self.colors['combo_text']};
                padding: 2px 6px;
                min-height: 18px;
                max-height: 18px;
                min-width: 126px;
                max-width: 126px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['base_weight']};
            }}

            /* Comprehensive fix for ComboBox white corners and proper background handling */
            QComboBox {{
                background-clip: padding-box;
                background-origin: padding-box;
                background-attachment: scroll;
            }}

            /* Specific styling for rename module widgets to prevent white corners */
            QWidget[objectName="RenameModuleWidget"] {{
                background-color: {self.colors['module_background']};
                border: 1px solid {self.colors['module_border']};
                border-radius: 6px;
                margin: 4px;
                padding: 2px;
            }}

            QWidget[objectName="RenameModuleWidget"] QComboBox {{
                background-color: {self.colors['combo_background']};
                border: 1px solid {self.colors['combo_border']};
                border-radius: 4px;
                color: {self.colors['combo_text']};
                padding: 2px 6px;
                margin: 0px;
                background-clip: padding-box;
                background-origin: padding-box;
                background-attachment: scroll;
            }}

            /* Force ComboBox to have solid background without inheritance issues */
            QComboBox:enabled {{
                background-color: {self.colors['combo_background']};
            }}

            QComboBox:hover {{
                background-color: {self.colors['combo_background_hover']};
            }}

            QComboBox:disabled {{
                background-color: {self.colors['disabled_background']};
            }}

            /* Ensure scroll area content widget has proper background */
            QScrollArea > QWidget {{
                background-color: {self.colors['scroll_area_background']};
            }}

            /* Specific fix for scroll areas containing ComboBoxes */
            QScrollArea {{
                background-color: {self.colors['scroll_area_background']};
            }}

            FinalTransformContainer QComboBox::drop-down {{
                border: none !important;
                background-color: transparent !important;
                width: 18px !important;
                subcontrol-origin: padding !important;
                subcontrol-position: center right !important;
            }}

            FinalTransformContainer QComboBox::down-arrow {{
                image: url(resources/icons/feather_icons/chevron-down.svg) !important;
                width: 10px !important;
                height: 10px !important;
            }}

            FinalTransformContainer QComboBox::down-arrow:on {{
                image: url(resources/icons/feather_icons/chevron-up.svg) !important;
            }}

            FinalTransformContainer QComboBox:hover {{
                background-color: {self.colors['combo_background_hover']};
                border-color: {self.colors['input_border_hover']};
            }}

            FinalTransformContainer QComboBox:focus {{
                border-color: {self.colors['input_border_focus']};
            }}

            FinalTransformContainer QComboBox:on {{
                background-color: {self.colors['combo_background_pressed']};
                color: {self.colors['combo_text_pressed']};
            }}

            FinalTransformContainer QComboBox::drop-down {{
                border: none;
                background-color: transparent;
                width: 18px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }}

            FinalTransformContainer QComboBox::down-arrow {{
                image: url(resources/icons/feather_icons/chevron-down.svg);
                width: 10px;
                height: 10px;
            }}

            FinalTransformContainer QComboBox::down-arrow:on {{
                image: url(resources/icons/feather_icons/chevron-up.svg);
            }}

            FinalTransformContainer QComboBox QAbstractItemView {{
                background-color: {self.colors['combo_dropdown_background']};
                color: {self.colors['combo_text']};
                selection-background-color: {self.colors['combo_item_background_selected']};
                selection-color: {self.colors['input_selection_text']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                outline: none;
            }}

            FinalTransformContainer QComboBox QAbstractItemView::item {{
                padding: 4px 6px;
                border: none;
                min-height: 16px;
            }}

            FinalTransformContainer QComboBox QAbstractItemView::item:hover {{
                background-color: {self.colors['combo_item_background_hover']};
                color: {self.colors['combo_text']};
            }}

            FinalTransformContainer QComboBox QAbstractItemView::item:selected {{
                background-color: {self.colors['combo_item_background_selected']} !important;
                color: {self.colors['input_selection_text']} !important;
            }}

            FinalTransformContainer QComboBox QAbstractItemView::item:selected:hover {{
                background-color: {self.colors['combo_background_selected_hover']} !important;
                color: {self.colors['input_selection_text']} !important;
            }}

            FinalTransformContainer QComboBox QAbstractItemView::item:selected:focus {{
                background-color: {self.colors['combo_item_background_selected']} !important;
                color: {self.colors['input_selection_text']} !important;
            }}

            /* FinalTransformContainer widget styling */
            FinalTransformContainer {{
                background-color: transparent;
                border: none;
            }}

            FinalTransformContainer QLabel {{
                background-color: transparent;
                color: {self.colors['app_text']};
                border: none;
            }}

            /* RenameModuleWidget styling for transparent background */
            RenameModuleWidget {{
                background-color: transparent !important;
                border: none !important;
            }}

            RenameModuleWidget > QWidget {{
                background-color: transparent !important;
            }}

            /* Force all child widgets to be transparent */
            RenameModuleWidget * {{
                background-color: transparent !important;
            }}

            /* Ensure RenameModuleWidget combo boxes have proper background without white corners */
            RenameModuleWidget QComboBox {{
                background-color: {self.colors['combo_background']} !important;
                border: 1px solid {self.colors['combo_border']} !important;
                border-radius: 4px !important;
                color: {self.colors['combo_text']} !important;
                padding: 2px 6px !important;
                selection-background-color: {self.colors['input_selection_bg']} !important;
                selection-color: {self.colors['input_selection_text']} !important;
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif !important;
                font-size: {self.fonts['interface_size']} !important;
                font-weight: {self.fonts['base_weight']} !important;
            }}

            RenameModuleWidget QComboBox::drop-down {{
                border: none !important;
                background-color: transparent !important;
                width: 18px !important;
                subcontrol-origin: padding !important;
                subcontrol-position: center right !important;
            }}

            RenameModuleWidget QComboBox::down-arrow {{
                image: url(resources/icons/feather_icons/chevron-down.svg) !important;
                width: 10px !important;
                height: 10px !important;
            }}

            RenameModuleWidget QComboBox::down-arrow:on {{
                image: url(resources/icons/feather_icons/chevron-up.svg) !important;
            }}

            /* Counter module button styling */
            CounterModule QPushButton {{
                background-color: {self.colors['button_background']} !important;
                border: none !important;
                border-radius: 4px !important;
                color: {self.colors['button_text']} !important;
                padding: 2px !important;
                margin: 0px !important;
                min-width: 22px !important;
                max-width: 22px !important;
                min-height: 22px !important;
                max-height: 22px !important;
                font-family: "{self.fonts['medium_family']}", "Segoe UI", Arial, sans-serif !important;
                font-size: {self.fonts['interface_size']} !important;
                font-weight: {self.fonts['medium_weight']} !important;
            }}

            CounterModule QPushButton:hover {{
                background-color: {self.colors['button_background_hover']} !important;
                border: none !important;
            }}

            CounterModule QPushButton:pressed {{
                background-color: {self.colors['button_background_pressed']} !important;
                color: {self.colors['button_text_pressed']} !important;
                border: none !important;
            }}

            CounterModule QPushButton:disabled {{
                background-color: {self.colors['button_background_disabled']} !important;
                color: {self.colors['button_text_disabled']} !important;
                border: none !important;
            }}

            RenameModuleWidget QComboBox {{
                background-color: {self.colors['combo_background']};
                border: 1px solid {self.colors['combo_border']};
                border-radius: 4px;
                color: {self.colors['combo_text']};
                padding: 2px 6px;
                selection-background-color: {self.colors['input_selection_bg']};
                selection-color: {self.colors['input_selection_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['base_weight']};
            }}

            RenameModuleWidget QComboBox:hover {{
                background-color: {self.colors['combo_background_hover']};
                border-color: {self.colors['input_border_hover']};
            }}

            RenameModuleWidget QComboBox:focus {{
                border-color: {self.colors['input_border_focus']};
            }}

            RenameModuleWidget QComboBox:on {{
                background-color: {self.colors['combo_background_pressed']};
                color: {self.colors['combo_text_pressed']};
            }}

            RenameModuleWidget QComboBox::drop-down {{
                border: none;
                background-color: transparent;
                width: 18px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }}

            RenameModuleWidget QComboBox::down-arrow {{
                image: url(resources/icons/feather_icons/chevron-down.svg);
                width: 10px;
                height: 10px;
            }}

            RenameModuleWidget QComboBox::down-arrow:on {{
                image: url(resources/icons/feather_icons/chevron-up.svg);
            }}

            RenameModuleWidget QComboBox QAbstractItemView {{
                background-color: {self.colors['combo_dropdown_background']};
                color: {self.colors['combo_text']};
                selection-background-color: {self.colors['combo_item_background_selected']};
                selection-color: {self.colors['input_selection_text']};
                border: 1px solid {self.colors['input_border']};
                border-radius: 4px;
                outline: none;
            }}

            RenameModuleWidget QComboBox QAbstractItemView::item {{
                padding: 4px 6px;
                border: none;
                min-height: 16px;
            }}

            RenameModuleWidget QComboBox QAbstractItemView::item:hover {{
                background-color: {self.colors['combo_item_background_hover']};
                color: {self.colors['combo_text']};
            }}

            RenameModuleWidget QComboBox QAbstractItemView::item:selected {{
                background-color: {self.colors['combo_item_background_selected']} !important;
                color: {self.colors['input_selection_text']} !important;
            }}

            RenameModuleWidget QComboBox QAbstractItemView::item:selected:hover {{
                background-color: {self.colors['combo_background_selected_hover']} !important;
                color: {self.colors['input_selection_text']} !important;
            }}

            RenameModuleWidget QComboBox QAbstractItemView::item:selected:focus {{
                background-color: {self.colors['combo_item_background_selected']} !important;
                color: {self.colors['input_selection_text']} !important;
            }}

            RenameModuleWidget QLabel {{
                background-color: transparent;
                color: {self.colors['app_text']};
                border: none;
            }}
        """

        # Apply to all combo box widgets
        for widget in parent.findChildren(QComboBox):
            widget.setStyleSheet(combo_style)

    def _apply_scroll_area_styling(self, parent: QWidget):
        """Apply scroll area and scrollbar styling (replaces scrollbars.qss)."""
        scroll_style = f"""
            QScrollArea {{
                border: 1px solid {self.colors['border_color']};
                border-radius: 4px;
                background-color: {self.colors['scroll_area_background']};
            }}

            QScrollArea > QWidget {{
                background-color: {self.colors['scroll_area_background']};
            }}

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
                border-radius: 0px;
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
                border-radius: 0px;
            }}

            /* Remove page step background */
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """

        # Apply to all scroll areas
        for widget in parent.findChildren(QScrollArea):
            widget.setStyleSheet(scroll_style)

    def _apply_table_view_styling(self, parent: QWidget):
        """Apply table view styling (replaces table_view.qss)."""
        table_style = f"""
            QTableView, QTableWidget {{
                background-color: {self.colors['table_background']};
                color: {self.colors['table_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['base_size']};
                font-weight: {self.fonts['base_weight']};
                alternate-background-color: {self.colors['table_alternate_background']};
                gridline-color: transparent;
                border: none;
                border-radius: 8px;
                selection-background-color: {self.colors['table_selection_background']};
                selection-color: {self.colors['table_selection_text']};
                show-decoration-selected: 0;
                outline: none;
            }}

            QTableWidget::item {{
                border: none;
                background-color: transparent;
                color: {self.colors['table_text']};
                padding: 2px 4px;
                border-radius: 6px;
                min-height: 16px;
            }}

            /* QTableView items: basic text color only - delegate handles backgrounds */
            QTableView::item {{
                color: {self.colors['table_text']};
                background-color: transparent;
                border: none;
                padding: 2px 4px;
                min-height: 16px;
            }}

            /* Alternative row styling for QTableWidget (preview tables) */
            QTableWidget::item:alternate {{
                background-color: {self.colors['table_alternate_background']};
                color: {self.colors['table_text']};
            }}

            /* QTableWidget specific styling (for preview tables) */
            QTableWidget::item:hover {{
                background-color: {self.colors['table_hover_background']};
                color: {self.colors['table_text']};
            }}

            QTableWidget::item:selected {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
                border: none;
            }}

            QTableWidget::item:selected:hover {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
            }}

            QTableWidget::item:selected:focus {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
                outline: none;
            }}

            /* Enable proper alternate colors for QTableWidget */
            QTableWidget {{
                alternate-background-color: {self.colors['table_alternate_background']};
            }}

            /* Icon table specific styling (third preview table) */
            QTableWidget[objectName="iconTable"] {{
                background-color: {self.colors['button_background_disabled']};
                border: none;
            }}

            /* FileTableView normal mode styling - basic background only */
            FileTableView[placeholder="false"] {{
                background-color: {self.colors['table_background']};
                color: {self.colors['table_text']};
            }}

            /* FileTableView items: basic text color only - delegate handles backgrounds */
            FileTableView[placeholder="false"]::item {{
                color: {self.colors['table_text']};
                background-color: transparent;
                border: none;
                padding: 2px 4px;
            }}

            /* FileTableView placeholder mode styling - keep normal background */
            FileTableView[placeholder="true"] {{
                background-color: {self.colors['table_background']};
            }}

            FileTableView[placeholder="true"]::item {{
                color: {self.colors['table_text']} !important;  /* FORCE TEXT VISIBLE EVEN IN PLACEHOLDER */
                background-color: transparent;
            }}

            FileTableView[placeholder="true"]::item:hover {{
                background-color: transparent;
            }}

            FileTableView[placeholder="true"]::item:selected {{
                background-color: transparent;
            }}

            /* Table Header styling */
            QTableView QHeaderView::section {{
                background-color: {self.colors['table_header_background']};
                color: {self.colors['table_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: 10pt;
                font-weight: {self.fonts['base_weight']};
                padding: 2px 4px;
                border: none;
                border-radius: 8px;
            }}

            QTableView QHeaderView::section:hover {{
                background-color: {self.colors['table_hover_background']};
                border: none;
            }}

            QTableView QHeaderView::section:pressed {{
                background-color: {self.colors['accent_color']};
                color: {self.colors['input_selection_text']};
            }}
        """

                        # Apply to all table views with specific priority
        for widget in parent.findChildren(QTableView):
            widget.setStyleSheet(table_style)

    def _apply_table_view_styling_globally(self, app: QApplication):
        """Apply table view styling globally to override base styling."""
        table_style = f"""
            /* Force table background with highest priority */
            QTableView {{
                background-color: {self.colors['table_background']} !important;
                color: {self.colors['table_text']} !important;
            }}

            QTableWidget {{
                background-color: {self.colors['table_background']} !important;
                color: {self.colors['table_text']} !important;
            }}

            FileTableView {{
                background-color: {self.colors['table_background']} !important;
                color: {self.colors['table_text']} !important;
            }}

            /* Table Header styling */
            QTableView QHeaderView::section, FileTableView QHeaderView::section {{
                background-color: {self.colors['table_header_background']} !important;
                color: {self.colors['table_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: 10pt;
                font-weight: {self.fonts['base_weight']};
                padding: 2px 4px;
                border: none;
                border-radius: 8px;
            }}
        """

        # Apply globally to ensure it overrides base styling
        current_style = app.styleSheet()
        app.setStyleSheet(current_style + "\n" + table_style)

    def _apply_tree_view_styling(self, parent: QWidget):
        """Apply tree view styling (replaces tree_view.qss)."""
        tree_style = f"""
            QTreeView {{
                background-color: {self.colors['table_background']};
                color: {self.colors['table_text']};
                font-family: {self.fonts['font_fallback']};
                font-size: {self.fonts['tree_size']};
                font-weight: {self.fonts['base_weight']};
                alternate-background-color: {self.colors['table_alternate_background']};
                border: none;
                show-decoration-selected: 1;
                selection-background-color: {self.colors['table_selection_background']};
                selection-color: {self.colors['table_selection_text']};
                outline: none;
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
                background-color: #8a9bb4;
                color: {self.colors['table_selection_text']};
                border: none;
            }}

            QTreeView::item:selected:focus {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
                border: none;
                outline: none;
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
                background-color: #8a9bb4;
                color: {self.colors['table_selection_text']};
                border: none;
            }}

            FileTreeView::branch:hover {{
                background-color: {self.colors['table_hover_background']};
                color: transparent;
                border: none;
            }}

            FileTreeView::branch:selected {{
                background-color: {self.colors['table_selection_background']};
                color: transparent;
                border: none;
            }}

            FileTreeView::branch:selected:hover {{
                background-color: #8a9bb4;
                color: transparent;
                border: none;
            }}

            /* MetadataTreeView specific styling */
            MetadataTreeView {{
                color: {self.colors['table_text']};
                background-color: {self.colors['table_background']};
            }}

            MetadataTreeView[placeholder="false"] {{
                color: {self.colors['table_text']};
                background-color: {self.colors['table_background']};
            }}

            MetadataTreeView[placeholder="true"] {{
                background-color: {self.colors['table_background']};
            }}

            MetadataTreeView[placeholder="false"]::item {{
                color: {self.colors['table_text']};
                background-color: transparent;
            }}

            MetadataTreeView[placeholder="false"]::item:hover {{
                background-color: {self.colors['table_hover_background']};
                color: {self.colors['table_text']};
                border: none;
            }}

            MetadataTreeView[placeholder="false"]::item:selected {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
                border: none;
            }}

            MetadataTreeView[placeholder="false"]::item:selected:hover {{
                background-color: #8a9bb4;
                color: {self.colors['table_selection_text']};
                border: none;
            }}

            MetadataTreeView[placeholder="true"]::item {{
                color: gray;
                selection-background-color: transparent;
                background-color: transparent;
            }}

            MetadataTreeView[placeholder="true"]::item:hover {{
                background-color: transparent;
                color: gray;
                border: none;
            }}

            MetadataTreeView[placeholder="true"]::item:selected {{
                background-color: transparent;
                color: gray;
                border: none;
            }}

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
                background-color: #8a9bb4;
                color: transparent;
                border: none;
            }}

            QTreeView::branch:has-siblings:!adjoins-item {{
                border-image: none;
                image: none;
                background: {self.colors['table_background']};
            }}

            QTreeView::branch:has-siblings:adjoins-item {{
                border-image: none;
                image: none;
                background: {self.colors['table_background']};
            }}

            QTreeView::branch:!has-children:!has-siblings:adjoins-item {{
                border-image: none;
                image: none;
                background: {self.colors['table_background']};
            }}

            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                image: url(resources/icons/feather_icons/chevron-right.svg);
                width: 12px;
                height: 12px;
            }}

            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                image: url(resources/icons/feather_icons/chevron-down.svg);
                width: 12px;
                height: 12px;
            }}

            QTreeView QHeaderView::section {{
                background-color: {self.colors['table_background']};
                color: {self.colors['table_text']};
                border: none;
                padding: 2px 4px;
                border-radius: 8px;
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: 10pt;
                font-weight: {self.fonts['base_weight']};
            }}
        """

        # Apply to all tree views
        for widget in parent.findChildren(QTreeView):
            widget.setStyleSheet(tree_style)

    def _apply_tree_view_styling_globally(self, app: QApplication):
        """Apply tree view styling globally to override base styling."""
        tree_style = f"""
            QTreeView, FileTreeView, MetadataTreeView {{
                background-color: {self.colors['table_background']} !important;
                color: {self.colors['table_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['tree_size']};
                font-weight: {self.fonts['base_weight']};
                alternate-background-color: {self.colors['table_alternate_background']};
                border: none;
                show-decoration-selected: 1;
                selection-background-color: {self.colors['table_selection_background']};
                selection-color: {self.colors['table_selection_text']};
                outline: none;
            }}

            QTreeView QHeaderView::section, FileTreeView QHeaderView::section, MetadataTreeView QHeaderView::section {{
                background-color: {self.colors['table_background']} !important;
                color: {self.colors['table_text']};
                border: none;
                padding: 2px 4px;
                border-radius: 8px;
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: 10pt;
                font-weight: {self.fonts['base_weight']};
            }}
        """

        # Apply globally to ensure it overrides base styling
        current_style = app.styleSheet()
        app.setStyleSheet(current_style + "\n" + tree_style)

    def _apply_dialog_styling(self, parent: QWidget):
        """Apply dialog styling (replaces dialogs.qss)."""
        dialog_style = f"""
            QDialog {{
                background-color: {self.colors['dialog_background']};
                color: {self.colors['dialog_text']};
                border: 1px solid {self.colors['border_color']};
                border-radius: 8px;
            }}

            QGroupBox {{
                color: {self.colors['app_text']};
                border: 1px solid {self.colors['border_color']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: 600;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: {self.colors['app_background']};
            }}

            QLabel {{
                color: {self.colors['app_text']};
                background-color: transparent;
            }}

            QProgressBar {{
                border: 1px solid {self.colors['border_color']};
                border-radius: 4px;
                background-color: {self.colors['input_background']};
                text-align: center;
                color: {self.colors['app_text']};
                min-height: 20px;
            }}

            QProgressBar::chunk {{
                background-color: {self.colors['accent_color']};
                border-radius: 3px;
            }}

            QSlider::groove:horizontal {{
                border: 1px solid {self.colors['border_color']};
                height: 6px;
                background-color: {self.colors['input_background']};
                border-radius: 3px;
            }}

            QSlider::handle:horizontal {{
                background-color: {self.colors['accent_color']};
                border: 1px solid {self.colors['accent_color']};
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}

            QSlider::handle:horizontal:hover {{
                background-color: {self.colors['highlight_blue']};
                border-color: {self.colors['highlight_blue']};
            }}
        """

        # Apply to all dialog-related widgets
        for widget in parent.findChildren(QDialog):
            widget.setStyleSheet(dialog_style)
        for widget in parent.findChildren(QGroupBox):
            widget.setStyleSheet(dialog_style)

    def _apply_context_menu_styling(self):
        """Apply context menu styling globally."""
        # Apply global context menu styling to the application
        menu_style = f"""
            /* Context Menu styling */
            QMenu {{
                background-color: {self.colors['dialog_background']};
                color: {self.colors['app_text']};
                border: none;
                border-radius: 8px;
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['base_weight']};
            }}

            QMenu::item {{
                background-color: transparent;
                color: {self.colors['app_text']};
                padding: 6px 16px;
                border-radius: 6px;
                margin: 1px;
            }}

            QMenu::item:hover {{
                background-color: {self.colors['table_hover_background']};
                color: {self.colors['app_text']};
                border-radius: 6px;
            }}

            QMenu::item:selected {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
                border-radius: 6px;
            }}

            QMenu::item:pressed {{
                background-color: {self.colors['table_selection_background']};
                color: {self.colors['table_selection_text']};
                border-radius: 6px;
            }}

            QMenu::item:disabled {{
                color: {self.colors['disabled_text']};
                background-color: transparent;
            }}

            QMenu::separator {{
                background-color: {self.colors['separator_light']};
                height: 1px;
                margin: 2px 8px;
            }}
        """

        # Get current application and add menu styling
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            current_style = app.styleSheet()
            app.setStyleSheet(current_style + "\n" + menu_style)

    def _apply_tooltip_styling(self):
        """Apply tooltip styling (replaces tooltip.qss)."""
        # Apply global tooltip styling to the application
        tooltip_style = f"""
            /* Enhanced standard tooltip */
            QToolTip {{
                background-color: {self.colors['tooltip_background']};
                color: {self.colors['tooltip_text']};
                border: 1px solid {self.colors['tooltip_border']};
                border-radius: 6px;
                padding: 2px 4px;
                font-size: {self.fonts['interface_size']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-weight: {self.fonts['base_weight']};
            }}

            /* Custom Error Tooltip */
            .ErrorTooltip {{
                background-color: {self.colors['tooltip_error_background']};
                color: {self.colors['tooltip_error_text']};
                border: 1px solid {self.colors['tooltip_error_border']};
                border-radius: 6px;
                padding: 2px 4px;
                font-size: {self.fonts['interface_size']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-weight: {self.fonts['base_weight']};
            }}

            /* Custom Warning Tooltip */
            .WarningTooltip {{
                background-color: {self.colors['tooltip_warning_background']};
                color: {self.colors['tooltip_warning_text']};
                border: 1px solid {self.colors['tooltip_warning_border']};
                border-radius: 6px;
                padding: 2px 4px;
                font-size: {self.fonts['interface_size']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-weight: {self.fonts['base_weight']};
            }}

            /* Custom Info Tooltip */
            .InfoTooltip {{
                background-color: {self.colors['tooltip_info_background']};
                color: {self.colors['tooltip_info_text']};
                border: 1px solid {self.colors['tooltip_info_border']};
                border-radius: 6px;
                padding: 2px 4px;
                font-size: {self.fonts['interface_size']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-weight: {self.fonts['base_weight']};
            }}

            /* Custom Success Tooltip */
            .SuccessTooltip {{
                background-color: {self.colors['tooltip_success_background']};
                color: {self.colors['tooltip_success_text']};
                border: 1px solid {self.colors['tooltip_success_border']};
                border-radius: 6px;
                padding: 2px 4px;
                font-size: {self.fonts['interface_size']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-weight: {self.fonts['base_weight']};
            }}
        """

        # Get current application and add tooltip styling
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            current_style = app.styleSheet()
            app.setStyleSheet(current_style + "\n" + tooltip_style)

    def apply_to_widget(self, widget: QWidget, component_type: str = "auto"):
        """Apply styling to a specific widget."""
        if component_type == "auto":
            component_type = widget.__class__.__name__.lower()

        if "scroll" in component_type:
            self._apply_scroll_area_styling(widget)
        elif "table" in component_type:
            self._apply_table_view_styling(widget)
        elif "tree" in component_type:
            self._apply_tree_view_styling(widget)
        elif "combo" in component_type:
            self._apply_combo_box_styling(widget)
        elif "button" in component_type or "push" in component_type:
            self._apply_button_styling(widget)
        elif "line" in component_type or "text" in component_type:
            self._apply_input_styling(widget)
        elif "dialog" in component_type:
            self._apply_dialog_styling(widget)

    def get_color(self, color_key: str) -> str:
        """Get a specific color from the theme."""
        return self.colors.get(color_key, "#ffffff")

    def _fix_table_backgrounds(self, parent: QWidget):
        """Fix table and tree view backgrounds using palette."""
        from core.qt_imports import QColor, QTableView, QTreeView

        # Find all table and tree views and set their background programmatically
        for widget in parent.findChildren(QTableView):
            palette = widget.palette()
            palette.setColor(widget.backgroundRole(), QColor(self.colors['table_background']))
            widget.setPalette(palette)
            widget.setAutoFillBackground(True)

        for widget in parent.findChildren(QTreeView):
            palette = widget.palette()
            palette.setColor(widget.backgroundRole(), QColor(self.colors['table_background']))
            widget.setPalette(palette)
            widget.setAutoFillBackground(True)

    def set_theme(self, theme_name: str):
        """Change theme (for future expansion)."""
        self.theme_name = theme_name
        # For now only dark theme supported
        self.colors = ComprehensiveThemeColors.DARK

    def apply_windows_font_fixes(self, main_window: QMainWindow):
        """Apply Windows-specific font fixes for better cross-platform compatibility."""
        if platform.system() != "Windows":
            return

        # Apply Windows-specific metadata tree styling
        windows_tree_style = f"""
            QTreeView {{
                font-family: "Segoe UI", "Tahoma", "Arial", sans-serif;
                font-size: 9pt;
                font-weight: 300;
            }}

            MetadataTreeView {{
                font-family: "Segoe UI", "Tahoma", "Arial", sans-serif;
                font-size: 9pt;
                font-weight: 300;
            }}

            QStandardItem {{
                font-family: "Segoe UI", "Tahoma", "Arial", sans-serif;
                font-size: 9pt;
                font-weight: 300;
            }}
        """

        # Apply the Windows-specific styling
        current_style = main_window.styleSheet()
        main_window.setStyleSheet(current_style + windows_tree_style)
