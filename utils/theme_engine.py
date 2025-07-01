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


class ThemeEngine:
    """
    Complete theme manager that replaces all QSS files with programmatic styling.
    Handles all UI components with precise control over styling.
    """

    def __init__(self, theme_name: str = "dark"):
        self.theme_name = theme_name or config.THEME_NAME
        self.colors = ComprehensiveThemeColors.DARK  # Only dark for now

        # Font definitions using Inter fonts
        self.fonts = {
            'base_family': get_inter_family('base'),
            'medium_family': get_inter_family('medium'),
            'semibold_family': get_inter_family('headers'),
            'base_weight': get_inter_css_weight('base'),
            'medium_weight': get_inter_css_weight('medium'),
            'semibold_weight': get_inter_css_weight('headers'),
            'base_size': '9pt',
            'interface_size': '9pt',
            'tree_size': '10pt',
            'small_size': '8pt',
            'large_size': '11pt',
            'title_size': '14pt'
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
        self._apply_tooltip_styling()

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
                width: 2px;
                margin: 2px 0px;
            }}

            QSplitter::handle:vertical {{
                height: 2px;
                margin: 0px 2px;
            }}

            QSplitter::handle:hover {{
                background-color: {self.colors['separator_light']};
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
                margin: 22px 0px 22px 0px;
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
                height: 22px;
                border-radius: 6px;
            }}

            QScrollBar:horizontal {{
                background: {self.colors['scroll_track_background']};
                height: 12px;
                border-radius: 6px;
                margin: 0px 22px 0px 22px;
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
                width: 22px;
                border-radius: 6px;
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
                border: 1px solid {self.colors['button_border']};
                border-radius: 4px;
                color: {self.colors['button_text']};
                padding: 6px 12px;
                min-height: 24px;
                font-family: "{self.fonts['medium_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['interface_size']};
                font-weight: {self.fonts['medium_weight']};
            }}

            QPushButton:hover {{
                background-color: {self.colors['button_background_hover']};
                border-color: {self.colors['input_border_focus']};
            }}

            QPushButton:pressed {{
                background-color: {self.colors['button_background_pressed']};
                color: {self.colors['button_text_pressed']};
            }}

            QPushButton:disabled {{
                background-color: {self.colors['button_background_disabled']};
                color: {self.colors['button_text_disabled']};
                border-color: {self.colors['border_color']};
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
                margin: 22px 0px 22px 0px;
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
                height: 22px;
                border-radius: 6px;
            }}

            QScrollBar:horizontal {{
                background: {self.colors['scroll_track_background']};
                height: 12px;
                border-radius: 6px;
                margin: 0px 22px 0px 22px;
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
                width: 22px;
                border-radius: 6px;
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
                background-color: {self.colors['table_background']};
                color: {self.colors['table_text']};
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['base_size']};
                font-weight: {self.fonts['base_weight']};
                padding: 4px;
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

        # Apply to all table views
        for widget in parent.findChildren(QTableView):
            widget.setStyleSheet(table_style)

    def _apply_tree_view_styling(self, parent: QWidget):
        """Apply tree view styling (replaces tree_view.qss)."""
        tree_style = f"""
            QTreeView {{
                background-color: {self.colors['table_background']};
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
                padding: 4px;
                border-radius: 8px;
                font-family: "{self.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                font-size: {self.fonts['tree_size']};
                font-weight: {self.fonts['base_weight']};
            }}
        """

        # Apply to all tree views
        for widget in parent.findChildren(QTreeView):
            widget.setStyleSheet(tree_style)

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

    def _apply_tooltip_styling(self):
        """Apply tooltip styling (replaces tooltip.qss)."""
        # Tooltip styling is handled globally by Qt
        pass

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

    def set_theme(self, theme_name: str):
        """Change theme (for future expansion)."""
        self.theme_name = theme_name
        # For now only dark theme supported
        self.colors = ComprehensiveThemeColors.DARK
