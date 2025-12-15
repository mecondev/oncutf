"""
Module: view_helpers.py

Author: Michael Economou
Date: 2025-05-24

view_helpers.py
This module provides view-level helper functions for UI updates
in the Batch File Renamer GUI, such as triggering table cell refreshes
without relying on internal status propagation.
Currently includes:
- update_info_icon: visually refreshes the icon cell in column 0 for a given file.
"""

from core.pyqt_imports import QTableView
from oncutf.utils.path_utils import paths_equal


def update_info_icon(file_table_view: QTableView, model, file_path: str) -> None:
    """
    Triggers visual refresh of the icon cell in column 0 for the given file path.

    Args:
        file_table_view (QTableView): The QTableView displaying the files.
        model: The FileTableModel containing FileItem instances.
        file_path (str): The full path of the file whose icon should be updated.
    """
    for row, file_item in enumerate(model.files):
        if paths_equal(file_item.full_path, file_path):
            index = model.index(row, 0)
            rect = file_table_view.visualRect(index)
            file_table_view.viewport().update(rect)
            break
