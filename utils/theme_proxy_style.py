"""
Theme styling helper for OnCutF application.
Provides cross-platform, reliable styling with easy theme switching.
"""

from utils.comprehensive_theme_system import ComprehensiveThemeApplier
from core.qt_imports import QWidget, QScrollArea
import config


class RenameModuleStyleHelper:
    """Helper class to apply custom styling to rename module widgets."""

    @staticmethod
    def apply_module_background(widget: QWidget, theme: str = "dark"):
        """Apply background styling to a rename module widget."""
        theme = theme or config.THEME_NAME
        applier = ComprehensiveThemeApplier(theme)
        applier.apply_to_module_widget(widget)

    @staticmethod
    def apply_scroll_area_background(scroll_area: QScrollArea, theme: str = "dark"):
        """Apply background styling to rename modules scroll area."""
        theme = theme or config.THEME_NAME
        applier = ComprehensiveThemeApplier(theme)
        applier.apply_to_scroll_area(scroll_area)
