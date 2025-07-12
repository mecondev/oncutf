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
        self._last_value: str = ""
        self._is_validating: bool = False

    def emit_if_changed(self, value: str) -> None:
        """
        Emits the updated signal only if the value differs from the last known.
        """
        logger.debug(f"[Signal] {self.__class__.__name__} emit_if_changed: old={getattr(self, '_last_value', None)!r} new={value!r}")

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
