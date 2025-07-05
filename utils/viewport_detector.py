"""
utils/viewport_detector.py
Author: Michael Economou
Date: 2025-01-31

Viewport detection utility for lazy metadata loading.
Detects which files are currently visible in table views for smart loading priorities.
"""

import logging
from typing import List, Tuple, Optional
from PyQt5.QtWidgets import QAbstractItemView, QTableView
from PyQt5.QtCore import QModelIndex

from models.file_item import FileItem

logger = logging.getLogger(__name__)


class ViewportDetector:
    """
    Utility class for detecting visible items in table views.
    Used by LazyMetadataManager to prioritize loading for visible files.
    """

    @staticmethod
    def get_visible_files(table_view: QTableView, file_model) -> List[FileItem]:
        """
        Get list of files currently visible in the table viewport.

        Args:
            table_view: The QTableView to analyze
            file_model: The file model containing FileItem objects

        Returns:
            List[FileItem]: Files currently visible in viewport
        """
        if not table_view or not file_model or not hasattr(file_model, 'files'):
            return []

        try:
            # Get viewport geometry
            viewport = table_view.viewport()
            if not viewport:
                return []

            # Get visible row range
            visible_range = ViewportDetector._get_visible_row_range(table_view)
            if not visible_range:
                return []

            start_row, end_row = visible_range

            # Extract visible files
            visible_files = []
            for row in range(start_row, min(end_row + 1, len(file_model.files))):
                if 0 <= row < len(file_model.files):
                    visible_files.append(file_model.files[row])

            logger.debug(f"[ViewportDetector] Found {len(visible_files)} visible files (rows {start_row}-{end_row})")
            return visible_files

        except Exception as e:
            logger.warning(f"[ViewportDetector] Error detecting visible files: {e}")
            return []

    @staticmethod
    def _get_visible_row_range(table_view: QTableView) -> Optional[Tuple[int, int]]:
        """
        Get the range of rows currently visible in the table viewport.

        Args:
            table_view: The QTableView to analyze

        Returns:
            Tuple[int, int]: (start_row, end_row) or None if cannot determine
        """
        try:
            # Get viewport rectangle
            viewport_rect = table_view.viewport().rect()

            # Get top-left and bottom-right points of viewport
            top_left_point = viewport_rect.topLeft()
            bottom_right_point = viewport_rect.bottomRight()

            # Get model indexes at these points
            top_left_index = table_view.indexAt(top_left_point)
            bottom_right_index = table_view.indexAt(bottom_right_point)

            # Extract row numbers
            if top_left_index.isValid():
                start_row = top_left_index.row()
            else:
                start_row = 0

            if bottom_right_index.isValid():
                end_row = bottom_right_index.row()
            else:
                # If bottom-right is not valid, estimate based on viewport height
                row_height = table_view.rowHeight(0) if table_view.model().rowCount() > 0 else 20
                visible_rows = max(1, viewport_rect.height() // row_height)
                end_row = start_row + visible_rows - 1

            # Ensure valid range
            if start_row < 0:
                start_row = 0

            if end_row < start_row:
                end_row = start_row

            return (start_row, end_row)

        except Exception as e:
            logger.warning(f"[ViewportDetector] Error getting visible row range: {e}")
            return None

    @staticmethod
    def get_expanded_visible_range(
        table_view: QTableView,
        file_model,
        expansion_factor: float = 0.5
    ) -> List[FileItem]:
        """
        Get visible files plus an expanded range for prefetching.

        Args:
            table_view: The QTableView to analyze
            file_model: The file model containing FileItem objects
            expansion_factor: How much to expand beyond visible area (0.5 = 50% more)

        Returns:
            List[FileItem]: Files in expanded visible range
        """
        if not table_view or not file_model or not hasattr(file_model, 'files'):
            return []

        try:
            visible_range = ViewportDetector._get_visible_row_range(table_view)
            if not visible_range:
                return []

            start_row, end_row = visible_range
            visible_count = end_row - start_row + 1

            # Calculate expansion
            expansion_rows = int(visible_count * expansion_factor)

            # Expand range
            expanded_start = max(0, start_row - expansion_rows)
            expanded_end = min(len(file_model.files) - 1, end_row + expansion_rows)

            # Extract files in expanded range
            expanded_files = []
            for row in range(expanded_start, expanded_end + 1):
                if 0 <= row < len(file_model.files):
                    expanded_files.append(file_model.files[row])

            logger.debug(f"[ViewportDetector] Expanded range: {len(expanded_files)} files (rows {expanded_start}-{expanded_end})")
            return expanded_files

        except Exception as e:
            logger.warning(f"[ViewportDetector] Error getting expanded visible range: {e}")
            return []

    @staticmethod
    def is_file_visible(table_view: QTableView, file_model, file_item: FileItem) -> bool:
        """
        Check if a specific file is currently visible in the viewport.

        Args:
            table_view: The QTableView to check
            file_model: The file model containing FileItem objects
            file_item: The FileItem to check visibility for

        Returns:
            bool: True if file is visible, False otherwise
        """
        try:
            visible_files = ViewportDetector.get_visible_files(table_view, file_model)
            return any(f.full_path == file_item.full_path for f in visible_files)

        except Exception as e:
            logger.warning(f"[ViewportDetector] Error checking file visibility: {e}")
            return False

    @staticmethod
    def get_viewport_center_file(table_view: QTableView, file_model) -> Optional[FileItem]:
        """
        Get the file at the center of the current viewport.

        Args:
            table_view: The QTableView to analyze
            file_model: The file model containing FileItem objects

        Returns:
            FileItem: File at viewport center, or None if cannot determine
        """
        try:
            visible_range = ViewportDetector._get_visible_row_range(table_view)
            if not visible_range:
                return None

            start_row, end_row = visible_range
            center_row = (start_row + end_row) // 2

            if 0 <= center_row < len(file_model.files):
                return file_model.files[center_row]

            return None

        except Exception as e:
            logger.warning(f"[ViewportDetector] Error getting viewport center file: {e}")
            return None
