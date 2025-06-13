#!/usr/bin/env python3
"""
test_threading_demo.py

Demo script to test the new threaded file loading functionality.
This script creates a test scenario and demonstrates the cancellable file loading.
"""

import sys
import os
import tempfile
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt5.QtCore import QTimer

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.cancellable_file_loader import CancellableFileLoader
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class TestWindow(QMainWindow):
    """Simple test window for demonstrating threaded file loading."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Threaded File Loading Demo")
        self.setGeometry(100, 100, 400, 200)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Status label
        self.status_label = QLabel("Ready to test threaded file loading")
        layout.addWidget(self.status_label)

        # Test button
        self.test_button = QPushButton("Test Large Folder Loading")
        self.test_button.clicked.connect(self.test_loading)
        layout.addWidget(self.test_button)

        # Cancel button
        self.cancel_button = QPushButton("Cancel Loading")
        self.cancel_button.clicked.connect(self.cancel_loading)
        self.cancel_button.setEnabled(False)
        layout.addWidget(self.cancel_button)

        # Results label
        self.results_label = QLabel("")
        layout.addWidget(self.results_label)

        # Create cancellable loader
        self.loader = CancellableFileLoader(self)
        self.loader.files_loaded.connect(self.on_files_loaded)
        self.loader.loading_cancelled.connect(self.on_loading_cancelled)
        self.loader.loading_failed.connect(self.on_loading_failed)

    def test_loading(self):
        """Test loading a large folder (like /usr/share)."""
        test_folder = "/usr/share"  # Usually has many files

        if not os.path.exists(test_folder):
            test_folder = "/usr"  # Fallback

        if not os.path.exists(test_folder):
            self.status_label.setText("No suitable test folder found")
            return

        self.status_label.setText(f"Starting threaded scan of {test_folder}...")
        self.test_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.results_label.setText("")

        # Start loading
        self.loader.load_files_from_folder(
            test_folder,
            recursive=True,  # This will likely trigger threading
            completion_callback=self.on_completion
        )

    def cancel_loading(self):
        """Cancel the current loading operation."""
        if self.loader.is_loading():
            self.loader.cleanup()

    def on_completion(self, file_paths):
        """Handle completion callback."""
        logger.info(f"Completion callback: {len(file_paths)} files found")

    def on_files_loaded(self, file_paths):
        """Handle files loaded signal."""
        self.status_label.setText("Loading completed successfully!")
        self.results_label.setText(f"Found {len(file_paths)} supported files")
        self.test_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def on_loading_cancelled(self):
        """Handle loading cancelled signal."""
        self.status_label.setText("Loading was cancelled by user")
        self.results_label.setText("Operation cancelled")
        self.test_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def on_loading_failed(self, error_message):
        """Handle loading failed signal."""
        self.status_label.setText("Loading failed!")
        self.results_label.setText(f"Error: {error_message}")
        self.test_button.setEnabled(True)
        self.cancel_button.setEnabled(False)


def main():
    """Main function to run the demo."""
    app = QApplication(sys.argv)

    window = TestWindow()
    window.show()

    print("Demo Instructions:")
    print("1. Click 'Test Large Folder Loading' to start scanning")
    print("2. A progress dialog should appear with Esc cancellation support")
    print("3. Press Esc or click 'Cancel Loading' to test cancellation")
    print("4. Check the console for debug messages")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
