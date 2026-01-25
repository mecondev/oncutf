"""Module: results_table_model.py.

Author: Michael Economou
Date: 2025-11-23

Custom QAbstractTableModel for results table dialog (hash results, etc.).

Features:
- Two-column table with customizable headers
- Alternating row colors
- Efficient data storage and retrieval
- Standard Qt model interface
"""

from typing import Any

from oncutf.core.pyqt_imports import (
    QAbstractTableModel,
    Qt,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ResultsTableModel(QAbstractTableModel):
    """Custom model for results table with two columns."""

    def __init__(self, data: dict[str, Any] | None = None, parent: Any = None) -> None:
        """Initialize the results table model."""
        super().__init__(parent)
        self._model_data: list[tuple[str, Any]] = list(
            (data or {}).items()
        )  # Store as list of tuples for O(1) access
        self.left_header = "Item"
        self.right_header = "Value"

    def rowCount(self, _parent: Any = None) -> int:
        """Return number of rows."""
        return len(self._model_data)

    def columnCount(self, _parent: Any = None) -> int:
        """Return number of columns (always 2)."""
        return 2

    def data(self, index: Any, role: int = Qt.DisplayRole) -> Any:
        """Return data for given index and role."""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row >= len(self._model_data):
            return None

        left_val, right_val = self._model_data[row]

        if role == Qt.DisplayRole:
            return str(left_val) if col == 0 else str(right_val)

        if role == Qt.ToolTipRole:
            return str(left_val) if col == 0 else str(right_val)

        return None

    def headerData(self, section: int, orientation: Any, role: int = Qt.DisplayRole) -> Any:
        """Return header data."""
        if role == Qt.TextAlignmentRole and orientation == Qt.Horizontal:
            return Qt.AlignLeft | Qt.AlignVCenter

        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            return self.left_header if section == 0 else self.right_header

        return str(section + 1)

    def set_headers(self, left_header: str, right_header: str) -> None:
        """Set custom header texts."""
        self.left_header = left_header
        self.right_header = right_header
        self.headerDataChanged.emit(Qt.Horizontal, 0, 1)

    def set_data(self, data: dict[str, Any]) -> None:
        """Replace all data and refresh view."""
        self.beginResetModel()
        self._model_data = list(data.items())
        self.endResetModel()
