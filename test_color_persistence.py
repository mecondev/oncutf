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
    db = get_database_manager()

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM file_paths WHERE color_tag != "none"'
        )
        count = cursor.fetchone()[0]

        if count > 0:
            cursor.execute(
                'SELECT file_path, color_tag FROM file_paths WHERE color_tag != "none" LIMIT 10'
            )
            rows = cursor.fetchall()
            for _path, _color in rows:
                pass
        else:
            pass


def check_fileitem_loading():
    """Check if FileItem loads colors correctly."""
    db = get_database_manager()

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT file_path, color_tag FROM file_paths WHERE color_tag != "none" LIMIT 5'
        )
        rows = cursor.fetchall()

        if not rows:
            return

        all_match = True
        for file_path, expected_color in rows:
            item = FileItem.from_path(file_path)
            match = item.color == expected_color
            all_match = all_match and match



def test_folder_loading():
    """Test loading files from folder and checking colors."""
    from oncutf.core.file_load_manager import FileLoadManager

    flm = FileLoadManager()
    test_folder = "/mnt/data_1/C/250907 Nicolas"

    if not os.path.exists(test_folder):
        return

    file_paths = flm._get_files_from_folder(test_folder, recursive=False)

    # Create FileItem objects
    file_items = [FileItem.from_path(path) for path in file_paths]
    colored_items = [item for item in file_items if item.color != "none"]

    if colored_items:
        for _item in colored_items[:5]:
            pass


if __name__ == "__main__":

    try:
        check_database_colors()
        check_fileitem_loading()
        test_folder_loading()
    except Exception:
        import traceback
        traceback.print_exc()
