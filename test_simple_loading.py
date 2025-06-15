#!/usr/bin/env python3
"""
Simple test for FileLoadingDialog functionality
"""

import sys
import os
sys.path.append('.')

from PyQt5.QtWidgets import QApplication
from widgets.file_loading_dialog import FileLoadingDialog
from config import ALLOWED_EXTENSIONS

def test_file_loading_dialog():
    """Test FileLoadingDialog with test_videos folder"""
    app = QApplication([])

    test_folder = "test_videos"
    if not os.path.exists(test_folder):
        print(f"❌ Test folder {test_folder} does not exist")
        return

    print(f"📁 Testing FileLoadingDialog with: {test_folder}")
    print(f"🎯 Allowed extensions: {ALLOWED_EXTENSIONS}")

    # List files in test folder
    files = os.listdir(test_folder)
    video_files = [f for f in files if any(f.lower().endswith('.' + ext) for ext in ALLOWED_EXTENSIONS)]
    print(f"📋 Test folder contains {len(files)} items, {len(video_files)} with allowed extensions:")
    for f in files:
        is_allowed = any(f.lower().endswith('.' + ext) for ext in ALLOWED_EXTENSIONS)
        marker = "✅" if is_allowed else "  "
        print(f"  {marker} {f}")

    # Test FileLoadingDialog
    results = []

    def on_files_loaded(file_paths):
        results.extend(file_paths)
        print(f"✅ FileLoadingDialog loaded {len(file_paths)} files:")
        for f in file_paths:
            print(f"  - {f}")

    dialog = FileLoadingDialog(None, on_files_loaded)

    # Load files from test folder
    dialog.load_files_with_options([test_folder], ALLOWED_EXTENSIONS, recursive=False)

    # Don't exec the dialog, just process events
    app.processEvents()

    print(f"\n📊 Summary: Found {len(results)} files")

    app.quit()

if __name__ == "__main__":
    test_file_loading_dialog()
