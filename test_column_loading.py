#!/usr/bin/env python3
"""
Test script to verify column width loading functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from widgets.file_table_view import FileTableView
from models.file_table_model import FileTableModel
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def test_column_loading():
    """Test the column width loading functionality."""
    app = QApplication(sys.argv)

    # Create table view and model
    table_view = FileTableView()
    model = FileTableModel()

    # Set the model
    table_view.setModel(model)

    # Test loading column widths
    print("Testing column width loading...")

    columns = ['filename', 'file_size', 'type', 'modified']
    for column_key in columns:
        width = table_view._load_column_width(column_key)
        print(f"Column '{column_key}': {width}px")

    print("Column width loading test completed.")

    app.quit()

if __name__ == "__main__":
    test_column_loading()
