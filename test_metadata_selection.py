#!/usr/bin/env python3
"""
Test script για να δοκιμάσω την επιλογή metadata με logging.
"""

import sys
import os
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] [%(name)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Import the necessary modules
from core.selection_manager import SelectionManager
from utils.metadata_cache_helper import MetadataCacheHelper
from models.file_item import FileItem

def test_selection_logic():
    """Test the selection logic with metadata."""
    print("Testing selection logic with metadata...")

    # Create a test file with metadata
    test_file = FileItem("/test/file.jpg", ".jpg", "2025-01-01 12:00:00")
    test_file.metadata = {
        "EXIF": {
            "Make": "Canon",
            "Model": "EOS 5D",
            "Orientation": "1"
        },
        "File": {
            "FileSize": "1024000",
            "FileType": "JPEG"
        }
    }

    # Test cache helper
    cache_helper = MetadataCacheHelper()
    metadata = cache_helper.get_metadata_for_file(test_file)

    print(f"File: {test_file.filename}")
    print(f"Metadata available: {bool(metadata)}")
    if metadata:
        print(f"Metadata keys: {list(metadata.keys())}")
        print(f"EXIF data: {metadata.get('EXIF', {})}")

    # Test with empty file
    empty_file = FileItem("/test/empty.jpg", ".jpg", "2025-01-01 12:00:00")
    empty_metadata = cache_helper.get_metadata_for_file(empty_file)
    print(f"\nEmpty file metadata: {bool(empty_metadata)}")

    print("\nTest completed!")

if __name__ == "__main__":
    test_selection_logic()
