#!/usr/bin/env python3
"""
Test script for ColorGridMenu widget.

Run: python scripts/test_color_grid_menu.py
"""

import sys
from pathlib import Path

# Add oncutf to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oncutf.core.pyqt_imports import QApplication, QPushButton, QVBoxLayout, QWidget
from oncutf.ui.widgets.color_grid_menu import ColorGridMenu


class TestWindow(QWidget):
    """Test window with button to show color grid menu."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ColorGridMenu Test")
        self.resize(300, 100)

        layout = QVBoxLayout(self)

        btn = QPushButton("Show Color Menu")
        btn.clicked.connect(self.show_color_menu)
        layout.addWidget(btn)

        self.result_label = QPushButton("Selected: None")
        self.result_label.setEnabled(False)
        layout.addWidget(self.result_label)

    def show_color_menu(self):
        """Show the color grid menu."""
        menu = ColorGridMenu(self)
        menu.color_selected.connect(self.on_color_selected)

        # Position below the button
        pos = self.mapToGlobal(self.rect().bottomLeft())
        menu.move(pos)
        menu.show()

    def on_color_selected(self, color: str):
        """Handle color selection."""
        print(f"Color selected: {color}")
        self.result_label.setText(f"Selected: {color}")

        # Update button background if not "none"
        if color != "none":
            self.result_label.setStyleSheet(f"background-color: {color};")
        else:
            self.result_label.setStyleSheet("")


def main():
    app = QApplication(sys.argv)

    # Apply dark theme
    app.setStyle("Fusion")

    window = TestWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
