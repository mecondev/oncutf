#!/usr/bin/env python3
"""
Test script to verify column alignment in file table.
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.pyqt_imports import QApplication, QMainWindow, QVBoxLayout, QWidget, Qt
from models.file_table_model import FileTableModel
from models.file_item import FileItem
from widgets.file_table_view import FileTableView

def main():
    app = QApplication(sys.argv)

    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Column Alignment Test")
    window.resize(800, 400)

    # Create central widget
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    window.setCentralWidget(central_widget)

    # Create model and view
    model = FileTableModel()
    view = FileTableView()
    view.setModel(model)

    # Add test files with different sizes to see alignment
    test_files = [
        FileItem('/test/small.jpg', 'jpg', datetime.now()),
        FileItem('/test/medium_size_file.png', 'png', datetime.now()),
        FileItem('/test/very_large_file_name.mp4', 'mp4', datetime.now()),
    ]

    # Set different sizes to test alignment
    test_files[0].size = 1024  # 1 KB
    test_files[1].size = 5242880  # 5 MB
    test_files[2].size = 1073741824  # 1 GB

    model.files = test_files
    model.layoutChanged.emit()

    # Set wider columns to see alignment effect
    view.setColumnWidth(1, 200)  # filename
    view.setColumnWidth(2, 120)  # file_size
    view.setColumnWidth(3, 80)   # type
    view.setColumnWidth(4, 150)  # modified

    layout.addWidget(view)

    print("Testing column alignment:")
    print("- File Size column should be RIGHT aligned")
    print("- Type column should be RIGHT aligned")
    print("- Filename should be LEFT aligned")
    print("- Modified should be CENTER aligned")
    print("\nClose the window to exit.")

    window.show()
    return app.exec_()

if __name__ == '__main__':
    main()
