"""Module: original_name_widget.py

Author: Michael Economou
Date: 2025-05-19

Rename module that reuses original filename.
"""

from oncutf.core.pyqt_imports import QHBoxLayout, QLabel, QVBoxLayout
from oncutf.modules.base_module import BaseRenameModule
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class OriginalNameWidget(BaseRenameModule):
    """Rename module widget for reusing the original filename.

    Simple module that just returns the original filename without modifications.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("module", True)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)  # Match final transformer margins
        layout.setSpacing(0)  # Match final transformer spacing

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)  # Reduce spacing

        # Simple label explaining what this module does
        self.label = QLabel("Uses the original filename")
        # Apply theme-aware styling instead of hard-coded color
        try:
            from oncutf.core.theme_manager import get_theme_manager

            theme = get_theme_manager()
            secondary_color = theme.get_color("text_secondary")
            self.label.setStyleSheet(f"color: {secondary_color}; font-style: italic;")
        except Exception:
            # Fallback to no styling (global theme will handle it)
            pass

        row.addWidget(self.label)
        row.addStretch()
        layout.addLayout(row)

        # Initialize _last_value
        self._last_value = str(self.get_data())

    def get_data(self) -> dict:
        return {"type": "original_name"}

    def set_data(self, _data: dict) -> None:
        # Nothing to set for original name module
        self._last_value = str(self.get_data())

    @staticmethod
    def is_effective_data(_data: dict) -> bool:
        """The original name module is always effective because it produces output."""
        return True
