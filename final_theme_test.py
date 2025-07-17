#!/usr/bin/env python3
"""
Final test to verify all theme inheritance issues are resolved.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QLabel, QComboBox, QHBoxLayout
from widgets.metadata_widget import MetadataWidget
from modules.base_module import BaseRenameModule
from utils.theme_engine import ThemeEngine

def main():
    app = QApplication(sys.argv)

    # Apply theme
    theme = ThemeEngine()
    dummy_window = QWidget()
    theme.apply_complete_theme(app, dummy_window)

    # Create test window
    window = QWidget()
    window.setWindowTitle("Final Theme Test")
    window.setGeometry(100, 100, 500, 400)

    layout = QVBoxLayout(window)

    # Add title
    title = QLabel("Final Theme Inheritance Test")
    title.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
    layout.addWidget(title)

    # Test 1: Direct combo box (reference)
    ref_label = QLabel("1. Direct ComboBox (Reference):")
    ref_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
    layout.addWidget(ref_label)

    ref_combo = QComboBox()
    ref_combo.addItems(["Option 1", "Option 2", "Option 3"])
    ref_combo.setEnabled(False)
    layout.addWidget(ref_combo)

    # Test 2: MetadataWidget
    metadata_label = QLabel("2. MetadataWidget:")
    metadata_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
    layout.addWidget(metadata_label)

    metadata_widget = MetadataWidget(parent=window)
    layout.addWidget(metadata_widget)

    # Test 3: BaseRenameModule
    base_label = QLabel("3. BaseRenameModule:")
    base_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
    layout.addWidget(base_label)

    base_module = BaseRenameModule(parent=window)
    layout.addWidget(base_module)

    # Instructions
    instructions = QLabel(
        "Instructions:\n"
        "1. Select 'Hash' category in MetadataWidget\n"
        "2. All combo boxes should have consistent styling\n"
        "3. Dropdown items should not have white margins\n"
        "4. Disabled states should show correct gray colors"
    )
    instructions.setStyleSheet("margin: 10px; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
    layout.addWidget(instructions)

    window.show()

    print("Final test window opened.")
    print("Check that all combo boxes have consistent styling without white margins.")

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
