#!/usr/bin/env python3
"""Quick test for ResultsTableDialog styling."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.pyqt_imports import QApplication
from utils.theme_engine import ThemeEngine
from widgets.results_table_dialog import ResultsTableDialog


def main():
    app = QApplication(sys.argv)

    # Apply theme
    theme = ThemeEngine()
    theme.apply_complete_theme(app, None)

    # Create test data
    test_data = {
        "file_001.mp4": "A1B2C3D4",
        "file_002.jpg": "E5F6G7H8",
        "file_003.xml": "I9J0K1L2",
        "file_004.mp4": "M3N4O5P6",
        "file_005.jpg": "Q7R8S9T0",
        "file_006.xml": "U1V2W3X4",
        "file_007.mp4": "Y5Z6A7B8",
        "file_008.jpg": "C9D0E1F2",
    }

    # Show dialog
    dialog = ResultsTableDialog(
        parent=None,
        title="Test Hash Results",
        left_header="Filename",
        right_header="Checksum",
        data=test_data,
        config_key="hash_list_test",
    )

    dialog.exec_()

    return 0


if __name__ == "__main__":
    sys.exit(main())
