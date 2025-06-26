#!/usr/bin/env python3
"""
Test script for the new individual file export functionality.
"""

import os
import tempfile
from utils.metadata_exporter import MetadataExporter

# Mock file item class for testing
class MockFileItem:
    def __init__(self, filename, full_path, file_size=1024, metadata=None):
        self.filename = filename
        self.full_path = full_path
        self.file_size = file_size
        self.metadata = metadata or {}

def test_export():
    """Test the new export functionality."""

    # Create mock files
    test_files = [
        MockFileItem(
            "test_video.mp4",
            "/path/to/test_video.mp4",
            1024*1024*50,  # 50MB
            {
                "Duration": "00:02:30",
                "Resolution": "1920x1080",
                "Codec": "H.264",
                "Bitrate": "5000 kbps"
            }
        ),
        MockFileItem(
            "test_image.jpg",
            "/path/to/test_image.jpg",
            1024*200,  # 200KB
            {
                "Width": "1920",
                "Height": "1080",
                "Camera": "Canon EOS R5",
                "ISO": "100",
                "Aperture": "f/2.8"
            }
        )
    ]

    # Create temporary directory for export
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Testing export to: {temp_dir}")

        # Create exporter
        exporter = MetadataExporter()

        # Test JSON export
        print("\n=== Testing JSON Export ===")
        json_success = exporter.export_files(test_files, temp_dir, "json")
        print(f"JSON Export Success: {json_success}")

        # Test Markdown export
        print("\n=== Testing Markdown Export ===")
        md_success = exporter.export_files(test_files, temp_dir, "markdown")
        print(f"Markdown Export Success: {md_success}")

        # List created files
        print(f"\n=== Files created in {temp_dir} ===")
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            size = os.path.getsize(file_path)
            print(f"- {file} ({size} bytes)")

            # Show content preview for small files
            if size < 2000:
                print(f"  Content preview:")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()[:200]
                    print(f"  {content}...")
                print()

if __name__ == "__main__":
    test_export()
