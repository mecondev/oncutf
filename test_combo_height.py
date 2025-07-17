#!/usr/bin/env python3
"""
Test script to compare combo box heights between different modules.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QLabel, QComboBox, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt
from widgets.metadata_widget import MetadataWidget
from modules.base_module import BaseRenameModule
from modules.counter_module import CounterModule
from utils.theme_engine import ThemeEngine


class ComboHeightTestWindow(QWidget):
    """Test window to compare combo box heights."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Combo Box Height Test")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout(self)

        # Add title
        title = QLabel("Combo Box Height Comparison Test")
        title.setStyleSheet("font-weight: bold; font-size: 16px; margin: 10px;")
        layout.addWidget(title)

        # Add description
        description = QLabel(
            "This test compares combo box heights between different modules:\n"
            "1. Direct combo box (reference)\n"
            "2. MetadataWidget combo box\n"
            "3. CounterModule combo box (inherits from BaseRenameModule)\n"
            "Look for differences in item heights in the dropdowns."
        )
        description.setStyleSheet("margin: 10px; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(description)

        # Test 1: Direct combo box
        direct_section = QLabel("Test 1: Direct ComboBox (Reference)")
        direct_section.setStyleSheet("font-weight: bold; margin-top: 15px; color: #333;")
        layout.addWidget(direct_section)

        direct_layout = QHBoxLayout()
        self.direct_combo = QComboBox()
        self.direct_combo.addItems(["Option 1", "Option 2", "Option 3", "Option 4"])
        direct_layout.addWidget(self.direct_combo)
        direct_layout.addStretch()
        layout.addLayout(direct_layout)

        # Test 2: MetadataWidget
        metadata_section = QLabel("Test 2: MetadataWidget ComboBox")
        metadata_section.setStyleSheet("font-weight: bold; margin-top: 15px; color: #333;")
        layout.addWidget(metadata_section)

        self.metadata_widget = MetadataWidget(parent=self)
        layout.addWidget(self.metadata_widget)

        # Test 3: CounterModule (inherits from BaseRenameModule)
        counter_section = QLabel("Test 3: CounterModule ComboBox (BaseRenameModule)")
        counter_section.setStyleSheet("font-weight: bold; margin-top: 15px; color: #333;")
        layout.addWidget(counter_section)

        self.counter_module = CounterModule(parent=self)
        layout.addWidget(self.counter_module)

        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "1. Click on each combo box to open the dropdown\n"
            "2. Compare the height of items in each dropdown\n"
            "3. Look for any white space above/below items\n"
            "4. The CounterModule should show the height issue"
        )
        instructions.setStyleSheet("margin: 10px; padding: 10px; background-color: #e8f4fd; border-radius: 5px;")
        layout.addWidget(instructions)

        # Status section
        self.status_label = QLabel("Ready for testing - click on combo boxes to compare heights")
        self.status_label.setStyleSheet("margin: 10px; padding: 10px; background-color: #d4edda; border-radius: 5px;")
        layout.addWidget(self.status_label)

        # Test buttons
        button_layout = QHBoxLayout()

        check_styles_btn = QPushButton("Check Applied Styles")
        check_styles_btn.clicked.connect(self.check_applied_styles)
        button_layout.addWidget(check_styles_btn)

        layout.addLayout(button_layout)

    def check_applied_styles(self):
        """Check what styles are applied to each combo box."""
        try:
            status_text = "Applied Styles:\n"

            # Check direct combo
            direct_style = self.direct_combo.styleSheet()
            status_text += f"Direct Combo Style: {'Custom' if direct_style else 'Global Theme'}\n"

            # Check metadata widget combo
            metadata_style = self.metadata_widget.options_combo.styleSheet()
            status_text += f"MetadataWidget Combo Style: {'Custom' if metadata_style else 'Global Theme'}\n"

            # Check counter module combo (if it has one)
            counter_combos = self.counter_module.findChildren(QComboBox)
            if counter_combos:
                counter_style = counter_combos[0].styleSheet()
                status_text += f"CounterModule Combo Style: {'Custom' if counter_style else 'Global Theme'}\n"
            else:
                status_text += f"CounterModule Combo Style: No combo found\n"

            # Check base module style
            base_style = self.counter_module.styleSheet()
            status_text += f"Base Module Style: {'Custom' if base_style else 'Global Theme'}\n"

            self.status_label.setText(status_text)
            self.status_label.setStyleSheet("margin: 10px; padding: 10px; background-color: #e2e3e5; border-radius: 5px;")

        except Exception as e:
            self.status_label.setText(f"Error checking styles: {e}")
            self.status_label.setStyleSheet("margin: 10px; padding: 10px; background-color: #f8d7da; border-radius: 5px;")


def main():
    """Run the test application."""
    app = QApplication(sys.argv)

    # Apply theme
    theme = ThemeEngine()
    # Create a dummy main window for theme application
    dummy_window = QWidget()
    theme.apply_complete_theme(app, dummy_window)

    # Set application properties
    app.setApplicationName("Combo Box Height Test")
    app.setApplicationVersion("1.0")

    # Create and show test window
    window = ComboHeightTestWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
