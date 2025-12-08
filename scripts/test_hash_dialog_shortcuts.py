#!/usr/bin/env python3
"""Test script for hash results dialog shortcuts and persistence."""

import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt5.QtWidgets import QApplication

from widgets.results_table_dialog import ResultsTableDialog


def main():
    """Test hash results dialog with shortcuts and persistence."""
    app = QApplication.instance() or QApplication(sys.argv)

    # Apply theme - just set the stylesheet without window
    from utils.theme_engine import ThemeEngine
    theme = ThemeEngine()
    app.setStyleSheet(theme._get_complete_stylesheet())

    # Sample hash data
    test_data = {
        "file_001.mp4": "a1b2c3d4e5f6",
        "file_002.jpg": "1234567890ab",
        "file_003.xml": "abcdef123456",
        "file_004.mp4": "fedcba654321",
        "file_005.jpg": "9876543210fe",
    }

    # Create and show dialog
    dialog = ResultsTableDialog(
        parent=None,
        title="Hash Verification Test",
        left_header="Filename",
        right_header="Checksum",
        data=test_data,
        config_key="hash_list_test"
    )

    print("=" * 60)
    print("HASH RESULTS DIALOG - PERSISTENCE & SHORTCUTS TEST")
    print("=" * 60)
    print()
    print("Test Instructions:")
    print("1. Window opens with defaults (or saved geometry)")
    print("2. Try Ctrl+T → should auto-fit BOTH columns to content")
    print("3. Try Ctrl+Shift+T → should reset to default widths")
    print("4. Resize window and columns manually")
    print("5. Close dialog")
    print("6. Run script again → should restore your changes!")
    print()
    print("Watch the terminal logs for:")
    print("  • 'Loading config for key: hash_list_test'")
    print("  • 'Loaded geometry from...' (should show values 2nd time)")
    print("  • 'Loaded column widths from...' (should show values 2nd time)")
    print("  • ' Applied geometry' (if found)")
    print("  • ' Applied column widths' (if found)")
    print("  • 'Saving config for key...' (on close)")
    print("  • ' Config saved to disk'")
    print("  • 'Verification - geometry/columns' (confirms save)")
    print()
    print("Config file: ~/.config/oncutf/user_config.json")
    print("Config key: hash_list_test")
    print("=" * 60)

    dialog.exec_()

    return 0


if __name__ == "__main__":
    sys.exit(main())
