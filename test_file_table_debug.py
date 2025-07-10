#!/usr/bin/env python3
"""
Test script to debug FileTableModel metadata display
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Initialize QApplication
app = QApplication(sys.argv)

from models.file_item import FileItem
from models.file_table_model import FileTableModel
from core.persistent_metadata_cache import PersistentMetadataCache

def test_file_table_model():
    """Test FileTableModel metadata display"""
    print("=== Testing FileTableModel metadata display ===")

    # Create a test file
    test_file_path = "resources/images/splash.png"

    if not os.path.exists(test_file_path):
        print(f"Test file not found: {test_file_path}")
        return

    # Create file item
    file_item = FileItem(
        path=test_file_path,
        extension=os.path.splitext(test_file_path)[1],
        modified=datetime.fromtimestamp(os.path.getmtime(test_file_path))
    )

    # Create file table model
    model = FileTableModel()

    # Set parent window to enable metadata cache access
    class MockParentWindow:
        def __init__(self):
            self.metadata_cache = PersistentMetadataCache()

    mock_parent = MockParentWindow()
    model.parent_window = mock_parent

    model.set_files([file_item])

    # Test if image_size column shows data
    print(f"\nTesting image_size column:")

    # Get visible columns
    visible_columns = model.get_visible_columns()
    print(f"Visible columns: {visible_columns}")

    # Check if image_size is in visible columns
    if 'image_size' in visible_columns:
        print("image_size column is visible")

        # Get column index
        col_index = visible_columns.index('image_size') + 1  # +1 for status column
        print(f"image_size column index: {col_index}")

        # Get data for this column
        index = model.createIndex(0, col_index)
        data = model.data(index, Qt.DisplayRole)
        print(f"image_size data: {data}")

        # Test the _get_column_data method directly
        column_data = model._get_column_data(file_item, 'image_size', Qt.DisplayRole)
        print(f"Direct _get_column_data result: {column_data}")

    else:
        print("image_size column is NOT visible")

        # Test with image_size added to visible columns
        print("\nAdding image_size to visible columns...")
        test_columns = {'image_size': True}
        model.update_visible_columns(test_columns)

        visible_columns = model.get_visible_columns()
        print(f"Updated visible columns: {visible_columns}")

        if 'image_size' in visible_columns:
            col_index = visible_columns.index('image_size') + 1
            index = model.createIndex(0, col_index)
            data = model.data(index, Qt.DisplayRole)
            print(f"image_size data after update: {data}")

    # Test duration column
    print(f"\nTesting duration column:")
    duration_columns = {'duration': True}
    model.update_visible_columns(duration_columns)

    visible_columns = model.get_visible_columns()
    print(f"Visible columns with duration: {visible_columns}")

    if 'duration' in visible_columns:
        col_index = visible_columns.index('duration') + 1
        index = model.createIndex(0, col_index)
        data = model.data(index, Qt.DisplayRole)
        print(f"duration data: {data}")

        # Test the _get_column_data method directly
        column_data = model._get_column_data(file_item, 'duration', Qt.DisplayRole)
        print(f"Direct duration _get_column_data result: {column_data}")

if __name__ == "__main__":
    test_file_table_model()
