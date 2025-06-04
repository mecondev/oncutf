"""Base class for rename modules with signal optimization helpers."""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal


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
