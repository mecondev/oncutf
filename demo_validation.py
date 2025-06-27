#!/usr/bin/env python3
"""
Simple demo for metadata validation system

Author: Michael Economou
Date: 2025-01-28

Quick demo to test the metadata validation widgets.
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from widgets.metadata_validated_input import MetadataValidatedLineEdit, MetadataValidatedTextEdit


class ValidationDemo(QMainWindow):
    """Simple validation demo window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Metadata Validation Demo")
        self.setGeometry(100, 100, 500, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Title
        layout.addWidget(QLabel("Metadata Validation Demo"))
        layout.addWidget(QLabel("Try typing invalid characters in Title field: < > : / \\ | ? *"))

        # Title field (blocks invalid chars)
        layout.addWidget(QLabel("Title Field (blocks invalid chars):"))
        self.title_widget = MetadataValidatedLineEdit(field_name="Title")
        self.title_widget.setPlaceholderText("Enter title...")
        layout.addWidget(self.title_widget)

        # Artist field (allows all chars)
        layout.addWidget(QLabel("Artist Field (allows all chars):"))
        self.artist_widget = MetadataValidatedLineEdit(field_name="Artist")
        self.artist_widget.setPlaceholderText("Enter artist...")
        layout.addWidget(self.artist_widget)

        # Description field (multiline)
        layout.addWidget(QLabel("Description Field (multiline):"))
        self.description_widget = MetadataValidatedTextEdit(field_name="Description")
        self.description_widget.setPlaceholderText("Enter description...")
        layout.addWidget(self.description_widget)

        # Status
        self.status_label = QLabel("Ready to test...")
        layout.addWidget(self.status_label)

        # Connect signals
        self.title_widget.validation_changed.connect(
            lambda valid: self.status_label.setText(f"Title: {'✅ Valid' if valid else '❌ Invalid'}")
        )


def main():
    app = QApplication(sys.argv)

    # Basic styling
    app.setStyleSheet("""
        QLineEdit, QTextEdit {
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 3px;
        }
    """)

    window = ValidationDemo()
    window.show()

    print("🚀 Validation Demo Started!")
    print("Try typing invalid characters in the Title field...")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
