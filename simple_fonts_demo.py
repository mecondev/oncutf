#!/usr/bin/env python3
"""
Simple demo for Inter fonts - troubleshooting segfaults
"""

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

def main():
    # Create application first
    app = QApplication(sys.argv)

    print("✅ QApplication created")

    # Now import fonts (after QApplication exists)
    from utils.fonts import get_inter_font, get_inter_family

    print("✅ Fonts imported")

    # Create simple window
    window = QWidget()
    window.setWindowTitle("Simple Inter Fonts Test")
    window.setGeometry(200, 200, 400, 300)

    layout = QVBoxLayout(window)

    # Create simple labels
    title_font = get_inter_font('titles', 18)
    title_label = QLabel("Inter Fonts Test")
    title_label.setFont(title_font)
    layout.addWidget(title_label)

    body_font = get_inter_font('base', 12)
    body_label = QLabel("This is Inter Regular text")
    body_label.setFont(body_font)
    layout.addWidget(body_label)

    print("✅ Labels created")

    window.show()
    print("✅ Window shown")

    # Run the app
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
