"""
Module: base_module.py

Author: Michael Economou
Date: 2025-05-31

Base module for all rename modules.
"""

import logging

from core.pyqt_imports import QWidget, pyqtSignal

logger = logging.getLogger(__name__)


class BaseRenameModule(QWidget):
    """
    Base widget for rename modules. Provides protection against redundant
    signal emissions and recursive triggers (e.g., via setStyleSheet).
    """

    updated = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("class", "RenameModule")
        self._last_value: str = ""
        self._is_validating: bool = False

    def emit_if_changed(self, value: str) -> None:
        """
        Emits the updated signal only if the value differs from the last known.
        """
        logger.debug(
            f"[Signal] {self.__class__.__name__} emit_if_changed: old={getattr(self, '_last_value', None)!r} new={value!r}"
        )

        if not hasattr(self, "_last_value"):
            self._last_value = value
            self.updated.emit(self)  # Emit on first value too
            return

        if value == self._last_value or self._is_validating:
            return

        self._last_value = value
        self.updated.emit(self)

    def block_signals_while(self, widget: QWidget, func: callable) -> None:
        """
        Temporarily blocks signals for a widget while executing a function.
        """
        widget.blockSignals(True)
        try:
            func()
        finally:
            widget.blockSignals(False)

    def is_effective(self) -> bool:
        """
        Returns True if this module should affect the output filename.
        By default, delegates to the staticmethod is_effective(data).
        """
        return self.__class__.is_effective(self.get_data())

    def _ensure_theme_inheritance(self) -> None:
        """
        Ensure that child widgets inherit theme styles properly.
        This is needed because child widgets sometimes don't inherit
        the global application stylesheet correctly.

        Override this method in subclasses to provide specific styling.
        """
        try:
            # Get theme colors
            from utils.theme_engine import ThemeEngine

            theme = ThemeEngine()

            # Apply base module styling - minimal styles to avoid affecting combo boxes
            module_styles = f"""
                QLabel {{
                    background-color: transparent;
                    color: {theme.get_color('app_text')};
                    border: none;
                    padding: 2px;
                    margin: 0px;
                }}

                QLineEdit {{
                    background-color: {theme.get_color('input_background')};
                    border: 1px solid {theme.get_color('input_border')};
                    border-radius: 4px;
                    color: {theme.get_color('input_text')};
                    padding: 2px 8px;
                    font-family: "{theme.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                    font-size: {theme.fonts['base_size']};
                }}

                QLineEdit:hover {{
                    background-color: {theme.get_color('input_background_hover')};
                    border-color: {theme.get_color('input_border_hover')};
                }}

                QLineEdit:focus {{
                    background-color: {theme.get_color('input_background_focus')};
                    border-color: {theme.get_color('input_border_focus')};
                }}

                QPushButton {{
                    background-color: {theme.get_color('button_background')};
                    color: {theme.get_color('button_text')};
                    border: 1px solid {theme.get_color('button_border')};
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-family: "{theme.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                    font-size: {theme.fonts['base_size']};
                }}

                QPushButton:hover {{
                    background-color: {theme.get_color('button_background_hover')};
                }}

                QPushButton:pressed {{
                    background-color: {theme.get_color('button_background_pressed')};
                    color: {theme.get_color('button_text_pressed')};
                }}

                QPushButton:disabled {{
                    background-color: {theme.get_color('button_background_disabled')};
                    color: {theme.get_color('button_text_disabled')};
                }}
            """

            # Apply styles to the module
            self.setStyleSheet(module_styles)

            logger.debug(f"[{self.__class__.__name__}] Theme inheritance ensured")

        except Exception as e:
            logger.warning(f"[{self.__class__.__name__}] Failed to ensure theme inheritance: {e}")
