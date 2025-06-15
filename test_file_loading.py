#!/usr/bin/env python3
"""
Test script to debug file loading issues
"""

import sys
import os
sys.path.append('.')

from PyQt5.QtCore import QCoreApplication
from core.unified_file_worker import UnifiedFileWorker
from core.unified_file_loader import UnifiedFileLoader
from config import ALLOWED_EXTENSIONS

def test_unified_worker(test_path):
    """Test UnifiedFileWorker directly"""
    print(f"🧪 Testing UnifiedFileWorker with: {test_path}")

    worker = UnifiedFileWorker()
    worker.setup_scan(test_path, recursive=False)

    results = []

    # Connect signals
    def on_files_found(files):
        results.extend(files)
        print(f"✅ Worker found {len(files)} files:")
        for f in files[:5]:  # Show first 5
            print(f"  - {f}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")

    def on_error(error):
        print(f"❌ Worker error: {error}")

    def on_finished(success):
        print(f"🏁 Worker finished: success={success}")

    worker.files_found.connect(on_files_found)
    worker.error_occurred.connect(on_error)
    worker.finished_scanning.connect(on_finished)

    # Run synchronously
    worker.start()
    worker.wait()

    return results

def test_unified_loader(test_path):
    """Test UnifiedFileLoader"""
    print(f"\n🧪 Testing UnifiedFileLoader with: {test_path}")

    # Create QCoreApplication for Qt functionality
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])

    loader = UnifiedFileLoader()

    results = []

    # Connect signals
    def on_files_loaded(files):
        results.extend(files)
        print(f"✅ Loader loaded {len(files)} files:")
        for f in files[:5]:  # Show first 5
            print(f"  - {f}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")

    def on_loading_failed(error):
        print(f"❌ Loader error: {error}")

    loader.files_loaded.connect(on_files_loaded)
    loader.loading_failed.connect(on_loading_failed)

    # Test folder loading
    if os.path.isdir(test_path):
        loader.load_folder(test_path, recursive=False)
    else:
        loader.load_files([test_path], recursive=False)

    # Process events to ensure signals are handled
    app.processEvents()

    return results

def main():
    # Test with current directory
    test_path = "."

    print(f"📁 Testing file loading with path: {os.path.abspath(test_path)}")
    print(f"🎯 Allowed extensions: {ALLOWED_EXTENSIONS}")

    # List some files in the directory
    try:
        files = os.listdir(test_path)
        video_files = [f for f in files if any(f.lower().endswith('.' + ext) for ext in ALLOWED_EXTENSIONS)]
        print(f"📋 Directory contains {len(files)} items, {len(video_files)} with allowed extensions:")
        for f in files[:10]:
            is_allowed = any(f.lower().endswith('.' + ext) for ext in ALLOWED_EXTENSIONS)
            marker = "✅" if is_allowed else "  "
            print(f"  {marker} {f}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
    except Exception as e:
        print(f"❌ Cannot list directory: {e}")
        return

    # Test worker
    worker_results = test_unified_worker(test_path)

    # Test loader
    loader_results = test_unified_loader(test_path)

    print(f"\n📊 Summary:")
    print(f"  Worker found: {len(worker_results)} files")
    print(f"  Loader found: {len(loader_results)} files")

if __name__ == "__main__":
    main()
