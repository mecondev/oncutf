"""Module: base_module.py

Author: Michael Economou
Date: 2025-05-31

Base module for all rename modules.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Protocol

from oncutf.core.pyqt_imports import QWidget, pyqtSignal

logger = logging.getLogger(__name__)


class _HasGetData(Protocol):
    """Protocol for modules that can provide configuration data."""

    def get_data(self) -> dict[str, Any]:
        """Return the module's current configuration as a dict."""
        ...


class BaseRenameModule(QWidget):
    """Base widget for rename modules.

    Provides protection against redundant signal emissions and recursive triggers
    (e.g., via setStyleSheet).
    """

    updated = pyqtSignal(QWidget)

    # NOTE: Keep last_value as a simple string cache for emit throttling.
    _last_value: str
    _is_validating: bool

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize base rename module with parent widget."""
        super().__init__(parent)
        self.setProperty("class", "RenameModule")
        self._last_value = ""
        self._is_validating = False

    def emit_if_changed(self, value: str) -> None:
        """Emit the updated signal only if the value differs from the last known."""
        logger.debug(
            "[Signal] %s emit_if_changed: old=%r new=%r",
            self.__class__.__name__,
            getattr(self, "_last_value", None),
            value,
        )

        if not hasattr(self, "_last_value"):
            self._last_value = value
            self.updated.emit(self)  # Emit on first value too
            return

        if value == self._last_value or self._is_validating:
            return

        self._last_value = value
        self.updated.emit(self)

    def block_signals_while(self, widget: QWidget, func: Callable[[], Any]) -> None:
        """Temporarily block signals for a widget while executing `func`."""
        widget.blockSignals(True)
        try:
            func()
        finally:
            widget.blockSignals(False)

    def is_effective(self) -> bool:
        """Return True if this module should affect the output filename.

        Subclasses should NOT override this method.

        Instead, they should implement:
            - get_data(self) -> dict[str, Any]
            - @staticmethod is_effective_data(data: dict[str, Any]) -> bool
        """
        # We use a Protocol cast-ish pattern so mypy knows get_data exists.
        self_typed: _HasGetData = self  # type: ignore[assignment]
        return self.__class__.is_effective_data(self_typed.get_data())

    @staticmethod
    def is_effective_data(data: dict[str, Any]) -> bool:
        """Static effectiveness hook based on module data.

        Default behavior: always effective.
        Subclasses can override this as a staticmethod.
        """
        _ = data
        return True

    def _ensure_theme_inheritance(self) -> None:
        """Ensure that child widgets inherit theme styles properly.

        Override this method in subclasses to provide specific styling.
        """
        logger.debug(
            "[%s] Theme inheritance via global ThemeManager (no per-widget QSS)",
            self.__class__.__name__,
        )
