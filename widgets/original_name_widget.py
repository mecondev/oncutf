"""
Module: original_name_widget.py

Author: Michael Economou
Date: 2025-06-15

Rename module that reuses original filename.
"""

from core.pyqt_imports import QHBoxLayout, QLabel, QVBoxLayout
from modules.base_module import BaseRenameModule
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class OriginalNameWidget(BaseRenameModule):
    """
    Rename module widget for reusing the original filename.

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
        self.label.setStyleSheet("color: #999; font-style: italic;")

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
    def is_effective(_data: dict) -> bool:
        """
        The original name module is always effective because it produces output.
        """
        return True
