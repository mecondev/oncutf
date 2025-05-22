"""
metadata_loader.py

Author: Michael Economou
Date: 2025-05-22

This module contains the MetadataLoader class which abstracts and manages
metadata loading and display logic for the oncutf application. It supports
loading with or without forcing, avoids re-reading cached data, and updates
the UI components (metadata tree view and info icons) accordingly.
"""

import os
from typing import List
from models.file_item import FileItem
from PyQt5.QtCore import QTimer, Qt

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class MetadataLoader:
    def __init__(self, window):
        """
        Initializes the metadata loader with a reference to the main window.

        Args:
            window (MainWindow): The parent application window.
        """
        self.window = window

    def load(self, file_items: List[FileItem], force: bool = False) -> None:
        """
        Loads metadata for the given file items with optional force reload.
        Avoids redundant reads using cache, updates FileItem metadata, and
        refreshes both the metadata tree and the info icons in the file table.

        Args:
            file_items (List[FileItem]): The files to load metadata for.
            force (bool): If True, metadata will be read from disk even if cached.
        """
        if not file_items:
            self.window.set_status("No files selected for metadata.", color="gray", auto_reset=True)
            return

        to_load = []

        for item in file_items:
            norm_path = os.path.abspath(os.path.normpath(item.full_path))
            is_cached = self.window.metadata_cache.has(norm_path)
            from_cache = self.window.metadata_cache.get(norm_path)

            print(f"[LOADER] Check: {norm_path} → has={is_cached} → keys: {list(from_cache.keys()) if isinstance(from_cache, dict) else from_cache}")

            if force or not is_cached:
                # Schedule for loading
                to_load.append(item)
            elif not item.metadata:
                # Assign metadata from cache to FileItem
                print(f"[LOADER] Assigning cached metadata to FileItem: {item.filename}")
                item.metadata = from_cache

        if to_load:
            # Launch metadata scan asynchronously
            logger.info(f"[MetadataLoader] Loading {len(to_load)} files (force={force})")

            # Ensure metadata view is cleared if no selection exists
            selection = self.window.file_table_view.selectionModel().selectedRows()
            if not selection:
                self.window.clear_metadata_view()

            QTimer.singleShot(100, lambda: self.window.start_metadata_scan_for_items(to_load))
            return  # Exit early — will display metadata after scan is complete

        # --- All metadata is already cached or force is False ---

        # Decide what to display in the metadata tree
        selection = self.window.file_table_view.selectionModel().selectedRows()

        if selection:
            # Show metadata for selected (focused) file
            self.window.check_selection_and_show_metadata()
        else:
            # No active selection — cleanly clear the tree view
            self.window.clear_metadata_view()

        # Repaint info icons for all involved rows
        for item in file_items:
            try:
                row = self.window.model.files.index(item)
                for col in range(self.window.model.columnCount()):
                    idx = self.window.model.index(row, col)
                    self.window.file_table_view.viewport().update(
                        self.window.file_table_view.visualRect(idx)
                    )
            except ValueError:
                continue
