"""
Theme styling helper for OnCutF application.
Provides cross-platform, reliable styling with easy theme switching.
"""

from typing import Dict
from core.qt_imports import QColor, QWidget, QScrollArea


class ThemeColors:
    """Theme color definitions for easy switching between light/dark themes."""

    # Dark theme colors
    DARK = {
        'scroll_area_bg': '#181818',
        'module_bg': '#232323',
        'module_border': '#333333',
        'input_bg': '#181818',
        'input_border': '#3a3b40',
        'input_hover_bg': '#232323',
        'input_hover_border': '#555555',
        'input_focus_border': '#748cab',
        'text_color': '#f0ebd8',
        'button_bg': '#2a2a2a',
        'button_hover_bg': '#3e5c76',
        'button_pressed_bg': '#748cab',
        'button_pressed_text': '#0d1321',
    }

    # Light theme colors (for future use)
    LIGHT = {
        'scroll_area_bg': '#f5f5f5',
        'module_bg': '#ffffff',
        'module_border': '#cccccc',
        'input_bg': '#ffffff',
        'input_border': '#cccccc',
        'input_hover_bg': '#f0f0f0',
        'input_hover_border': '#999999',
        'input_focus_border': '#4a6fa5',
        'text_color': '#333333',
        'button_bg': '#e0e0e0',
        'button_hover_bg': '#d0d0d0',
        'button_pressed_bg': '#4a6fa5',
        'button_pressed_text': '#ffffff',
    }


class RenameModuleStyleHelper:
    """Helper class to apply custom styling to rename module widgets."""

    @staticmethod
    def apply_module_background(widget: QWidget, theme: str = 'dark'):
        """Apply background styling to a rename module widget."""
        colors = ThemeColors.DARK if theme == 'dark' else ThemeColors.LIGHT

        # Apply styling using QSS which is more reliable for background colors
        widget.setStyleSheet(f"""
            QWidget[objectName="RenameModuleWidget"] {{
                background-color: {colors['module_bg']};
                border: 1px solid {colors['module_border']};
                border-radius: 6px;
                margin: 4px;
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox {{
                background-color: {colors['input_bg']};
                border: 1px solid {colors['input_border']};
                border-radius: 4px;
                color: {colors['text_color']};
                padding: 2px 8px;
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox:hover {{
                background-color: {colors['input_hover_bg']};
                border-color: {colors['input_hover_border']};
            }}
            QWidget[objectName="RenameModuleWidget"] QComboBox:focus {{
                border-color: {colors['input_focus_border']};
            }}
            QWidget[objectName="RenameModuleWidget"] QLineEdit {{
                background-color: {colors['input_bg']};
                border: 1px solid {colors['input_border']};
                border-radius: 4px;
                color: {colors['text_color']};
                padding: 2px 6px;
                selection-background-color: {colors['input_focus_border']};
                selection-color: {colors['button_pressed_text']};
            }}
            QWidget[objectName="RenameModuleWidget"] QLineEdit:hover {{
                background-color: {colors['input_hover_bg']};
                border-color: {colors['input_hover_border']};
            }}
            QWidget[objectName="RenameModuleWidget"] QLineEdit:focus {{
                border-color: {colors['input_focus_border']};
            }}
            QWidget[objectName="RenameModuleWidget"] QPushButton {{
                background-color: {colors['button_bg']};
                border: 1px solid {colors['input_border']};
                border-radius: 4px;
                color: {colors['text_color']};
                padding: 2px;
            }}
            QWidget[objectName="RenameModuleWidget"] QPushButton:hover {{
                background-color: {colors['button_hover_bg']};
                border-color: {colors['input_focus_border']};
            }}
            QWidget[objectName="RenameModuleWidget"] QPushButton:pressed {{
                background-color: {colors['button_pressed_bg']};
                color: {colors['button_pressed_text']};
            }}
        """)

    @staticmethod
    def apply_scroll_area_background(scroll_area: QScrollArea, theme: str = 'dark'):
        """Apply background styling to rename modules scroll area."""
        colors = ThemeColors.DARK if theme == 'dark' else ThemeColors.LIGHT

        # Apply styling using QSS
        scroll_area.setStyleSheet(f"""
            QScrollArea[objectName="rename_modules_scroll"] {{
                border: 2px solid {colors['module_border']};
                border-radius: 8px;
                background-color: {colors['scroll_area_bg']};
            }}
            QScrollArea[objectName="rename_modules_scroll"] > QWidget {{
                background-color: {colors['scroll_area_bg']};
            }}
        """)

        # Also set palette as backup
        palette = scroll_area.palette()
        palette.setColor(scroll_area.backgroundRole(), QColor(colors['scroll_area_bg']))
        scroll_area.setPalette(palette)
        scroll_area.setAutoFillBackground(True)

        # Also style the viewport
        viewport = scroll_area.viewport()
        if viewport:
            viewport_palette = viewport.palette()
            viewport_palette.setColor(viewport.backgroundRole(), QColor(colors['scroll_area_bg']))
            viewport.setPalette(viewport_palette)
            viewport.setAutoFillBackground(True)
