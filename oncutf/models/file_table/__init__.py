"""oncutf.models.file_table package.

Modular implementation of the file table model.

Components:
- FileTableModel: Main model class (thin orchestrator)
- IconManager: Status icons and tooltips
- SortManager: File sorting logic
- ColumnManager: Column visibility and mapping
- DataProvider: Qt model data interface
- FileOperationsManager: File add/remove/refresh

Author: Michael Economou
Date: 2026-01-01
"""

from oncutf.models.file_table.data_provider import DataProvider
from oncutf.models.file_table.file_table_model import FileTableModel
from oncutf.models.file_table.icon_manager import IconManager
from oncutf.models.file_table.model_column_manager import ColumnManager
from oncutf.models.file_table.model_file_operations import FileOperationsManager
from oncutf.models.file_table.sort_manager import SortManager

__all__ = [
    "FileTableModel",
    "IconManager",
    "SortManager",
    "ColumnManager",
    "DataProvider",
    "FileOperationsManager",
]
