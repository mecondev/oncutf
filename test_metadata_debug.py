#!/usr/bin/env python3
"""
Test script to debug metadata display issues
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from models.file_item import FileItem
from core.persistent_metadata_cache import PersistentMetadataCache
from utils.metadata_loader import MetadataLoader
from datetime import datetime

def test_metadata_for_file(file_path):
    """Test metadata loading for a specific file"""
    print(f"\n=== Testing metadata for: {file_path} ===")

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    # Create file item
    file_item = FileItem(
        path=file_path,
        extension=os.path.splitext(file_path)[1],
        modified=datetime.fromtimestamp(os.path.getmtime(file_path))
    )
    print(f"File: {file_item.filename}")
    print(f"Extension: {file_item.extension}")
    print(f"Size: {file_item.size}")

    # Test metadata cache
    cache = PersistentMetadataCache()
    entry = cache.get_entry(file_path)

    if entry:
        print(f"\nMetadata cache entry found:")
        print(f"  Is extended: {entry.is_extended}")
        print(f"  Data keys: {list(entry.data.keys())}")

        # Look for duration-related keys
        duration_keys = [k for k in entry.data.keys() if 'duration' in k.lower()]
        print(f"  Duration keys: {duration_keys}")

        # Look for video/audio keys
        video_keys = [k for k in entry.data.keys() if any(term in k.lower() for term in ['video', 'audio', 'quicktime', 'media'])]
        print(f"  Video/Audio keys: {video_keys}")

        # Show some sample data
        print(f"\nSample metadata:")
        for key, value in list(entry.data.items())[:10]:
            print(f"  {key}: {value}")
    else:
        print("\nNo metadata cache entry found")

        # Try direct metadata loading
        print("\nTrying direct metadata loading...")
        loader = MetadataLoader()
        try:
            metadata = loader.load_metadata(file_path)
            if metadata:
                print(f"Direct metadata keys: {list(metadata.keys())}")

                # Look for duration-related keys
                duration_keys = [k for k in metadata.keys() if 'duration' in k.lower()]
                print(f"Duration keys: {duration_keys}")

                # Show some sample data
                print(f"\nSample direct metadata:")
                for key, value in list(metadata.items())[:10]:
                    print(f"  {key}: {value}")
            else:
                print("No direct metadata found")
        except Exception as e:
            print(f"Error loading direct metadata: {e}")

def main():
    """Main test function"""
    # Test with some sample files
    test_files = [
        "resources/images/splash.png",
        "assets/oncut_logo_dark_w_white_BG.png",
        "assets/oncut_logo_white_w_dark_BG.png"
    ]

    # Add any video files if they exist
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    for root, dirs, files in os.walk('.'):
        for file in files:
            if any(file.lower().endswith(ext) for ext in video_extensions):
                full_path = os.path.join(root, file)
                test_files.append(full_path)
                break  # Just test one video file

    for file_path in test_files:
        test_metadata_for_file(file_path)

if __name__ == "__main__":
    main()
