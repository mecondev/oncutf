#!/usr/bin/env python3
"""
Test script to reproduce the column disappearing issue.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.pyqt_imports import QApplication
from models.file_table_model import FileTableModel
from models.file_item import FileItem
from utils.logger_setup import ConfigureLogger

# Configure logging
config_dir = os.path.expanduser("~/.config/oncutf")
logs_dir = os.path.join(config_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)
ConfigureLogger(log_name="test_column", log_dir=logs_dir)

logger = logging.getLogger()

def create_test_files():
    """Create some test files for testing."""
    test_dir = Path("/tmp/oncutf_test")
    test_dir.mkdir(exist_ok=True)

    test_files = []
    for i in range(3):
        file_path = test_dir / f"test{i+1}.txt"
        file_path.write_text(f"Test content {i+1}")
        test_files.append(str(file_path))

    return test_files

def test_column_operations():
    """Test adding columns to see if content disappears."""

    # Create a minimal QApplication
    app = QApplication([])

    # Create a test model
    model = FileTableModel()

    # Create some test files
    test_file_paths = create_test_files()
    test_files = [FileItem.from_path(path) for path in test_file_paths]

    # Set the files
    print("Setting test files...")
    model.set_files(test_files)

    # Check initial state
    print(f"Initial column count: {model.columnCount()}")
    print(f"Initial row count: {model.rowCount()}")
    print(f"Initial visible columns: {model.get_visible_columns()}")

    # Try to add a column
    print("\nAdding 'Artist' metadata column...")
    current_columns = model.get_visible_columns()
    new_columns = current_columns + ['Artist']

    print(f"Current columns: {current_columns}")
    print(f"New columns: {new_columns}")

    # Update columns
    model.update_visible_columns(new_columns)

    # Check state after adding column
    print(f"After adding column - Column count: {model.columnCount()}")
    print(f"After adding column - Row count: {model.rowCount()}")
    print(f"After adding column - Visible columns: {model.get_visible_columns()}")

    # Try to get data from the model
    print("\nTesting data retrieval:")
    for row in range(model.rowCount()):
        for col in range(model.columnCount()):
            data = model.data(model.index(row, col))
            print(f"Row {row}, Col {col}: {data}")

    print("\nTest completed!")

if __name__ == "__main__":
    test_column_operations()
