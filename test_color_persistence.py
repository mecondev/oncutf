#!/usr/bin/env python3
"""
Test color persistence across sessions.

This script checks if colors are properly persisted in the database
and loaded when FileItem objects are created.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from oncutf.core.database.database_manager import get_database_manager
from oncutf.models.file_item import FileItem


def check_database_colors():
    """Check colors stored in database."""
    print("\n=== Database Color Status ===")
    db = get_database_manager()

    import sqlite3
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM file_paths WHERE color_tag != "none"'
        )
        count = cursor.fetchone()[0]
        print(f"Files with colors in DB: {count}")

        if count > 0:
            cursor.execute(
                'SELECT file_path, color_tag FROM file_paths WHERE color_tag != "none" LIMIT 10'
            )
            rows = cursor.fetchall()
            print(f"\nFirst 10 colored files:")
            for path, color in rows:
                print(f"  {os.path.basename(path)}: {color}")
        else:
            print("No files with colors found in database.")


def check_fileitem_loading():
    """Check if FileItem loads colors correctly."""
    print("\n=== FileItem Loading Test ===")
    db = get_database_manager()

    import sqlite3
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT file_path, color_tag FROM file_paths WHERE color_tag != "none" LIMIT 5'
        )
        rows = cursor.fetchall()

        if not rows:
            print("No colored files to test.")
            return

        print(f"Testing {len(rows)} files:")
        all_match = True
        for file_path, expected_color in rows:
            item = FileItem.from_path(file_path)
            match = item.color == expected_color
            all_match = all_match and match
            status = "✓" if match else "✗"
            print(
                f"  {status} {os.path.basename(file_path)}: "
                f"Expected {expected_color}, Got {item.color}"
            )

        print(f"\nAll colors loaded correctly: {all_match}")


def test_folder_loading():
    """Test loading files from folder and checking colors."""
    print("\n=== Folder Loading Test ===")
    from oncutf.core.file_load_manager import FileLoadManager

    flm = FileLoadManager()
    test_folder = "/mnt/data_1/C/250907 Nicolas"

    if not os.path.exists(test_folder):
        print(f"Test folder not found: {test_folder}")
        return

    print(f"Loading files from: {test_folder}")
    file_paths = flm._get_files_from_folder(test_folder, recursive=False)
    print(f"Total files found: {len(file_paths)}")

    # Create FileItem objects
    file_items = [FileItem.from_path(path) for path in file_paths]
    colored_items = [item for item in file_items if item.color != "none"]

    print(f"Files with colors: {len(colored_items)}")
    if colored_items:
        print("Sample colored files:")
        for item in colored_items[:5]:
            print(f"  {item.filename}: {item.color}")


if __name__ == "__main__":
    print("Color Persistence Test")
    print("=" * 50)

    try:
        check_database_colors()
        check_fileitem_loading()
        test_folder_loading()
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
