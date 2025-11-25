#!/usr/bin/env python
"""
Test script for companion files metadata integration.
Tests the metadata loading workflow with companion files enhancement.
"""

import os
import sys
import tempfile

# Setup sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test imports
from config import COMPANION_FILES_ENABLED, LOAD_COMPANION_METADATA
from core.unified_metadata_manager import UnifiedMetadataManager
from models.file_item import FileItem
from utils.companion_files_helper import CompanionFilesHelper


def create_test_files():
    """Create test MP4 and companion XML files."""
    temp_dir = tempfile.mkdtemp(prefix="oncutf_companion_test_")
    print(f"Created test directory: {temp_dir}")

    # Create test MP4 file
    mp4_path = os.path.join(temp_dir, "C8227.MP4")
    with open(mp4_path, "wb") as f:
        # Write minimal MP4 header-like content
        f.write(b'\x00\x00\x00\x20ftypmp42')
        f.write(b'\x00' * 100)

    # Create companion XML file with Sony metadata
    xml_path = os.path.join(temp_dir, "C8227M01.XML")
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<NonRealTimeMeta>
    <Device manufacturer="Sony" modelName="FX30" serialNo="12345"/>
    <RecordingMode type="normal" cacheRec="true"/>
    <CreationDate value="2024-12-15T10:30:45Z"/>
    <VideoFormat videoCodec="XAVC S" audioCodec="PCM">
        <VideoFrame formatFps="25p" pixel="3840x2160"/>
        <AudioRecordingLevel ch1="-18dB" ch2="-18dB"/>
    </VideoFormat>
</NonRealTimeMeta>'''

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return mp4_path, xml_path, temp_dir


def test_companion_detection():
    """Test that companion files are correctly detected."""
    print("\n=== Testing Companion File Detection ===")

    mp4_path, xml_path, temp_dir = create_test_files()

    try:
        # Test companion detection
        folder_files = [mp4_path, xml_path]
        companions = CompanionFilesHelper.find_companion_files(mp4_path, folder_files)

        print(f"MP4 file: {os.path.basename(mp4_path)}")
        print(f"XML file: {os.path.basename(xml_path)}")
        print(f"Detected companions: {[os.path.basename(c) for c in companions]}")

        assert len(companions) == 1, f"Expected 1 companion, got {len(companions)}"
        assert xml_path in companions, f"Expected {xml_path} in companions"

        print("✓ Companion detection works correctly")

        # Test metadata extraction
        companion_data = CompanionFilesHelper.extract_companion_metadata(xml_path)

        print("\nExtracted companion metadata:")
        for key, value in companion_data.items():
            print(f"  {key}: {value}")

        expected_keys = ["device_manufacturer", "device_model", "video_codec", "audio_codec", "video_resolution"]
        for key in expected_keys:
            assert key in companion_data, f"Expected key '{key}' not found in companion metadata"

        print("✓ Companion metadata extraction works correctly")

        return mp4_path, xml_path, temp_dir

    except Exception as e:
        print(f"✗ Test failed: {e}")
        # Cleanup on failure
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def test_metadata_enhancement():
    """Test that metadata enhancement works during metadata loading."""
    print("\n=== Testing Metadata Enhancement ===")

    mp4_path, xml_path, temp_dir = create_test_files()

    try:
        # Create mock file item
        from datetime import datetime
        file_item = FileItem(mp4_path, ".mp4", datetime.now())
        file_item.filename = os.path.basename(mp4_path)

        # Create mock metadata manager
        manager = UnifiedMetadataManager()

        # Test the enhancement method directly
        base_metadata = {
            "FileName": "C8227.MP4",
            "FileSize": "123456",
            "FileType": "MP4"
        }

        all_files = [file_item]

        enhanced_metadata = manager._enhance_metadata_with_companions(
            file_item, base_metadata, all_files
        )

        print(f"Base metadata keys: {list(base_metadata.keys())}")
        print(f"Enhanced metadata keys: {list(enhanced_metadata.keys())}")
        # Check if companion metadata was added
        companion_keys = [k for k in enhanced_metadata if k.startswith("Companion:")]
        print(f"Companion keys found: {companion_keys}")

        if COMPANION_FILES_ENABLED and LOAD_COMPANION_METADATA:
            assert len(companion_keys) > 0, "Expected companion metadata to be added"
            assert "__companion_files__" in enhanced_metadata, "Expected __companion_files__ key"

            # Check specific companion metadata
            expected_patterns = [
                "Companion:C8227M01.XML:device_manufacturer",
                "Companion:C8227M01.XML:device_model",
                "Companion:C8227M01.XML:video_codec"
            ]

            for pattern in expected_patterns:
                found = any(pattern in key for key in companion_keys)
                assert found, f"Expected companion metadata pattern '{pattern}' not found"

            print("✓ Metadata enhancement works correctly")
        else:
            print("⚠ Companion files disabled in config - enhancement skipped")

        return mp4_path, xml_path, temp_dir

    except Exception as e:
        print(f"✗ Test failed: {e}")
        # Cleanup on failure
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def cleanup_test_files(temp_dir):
    """Clean up test files."""
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"✓ Cleaned up test directory: {temp_dir}")
    except Exception as e:
        print(f"⚠ Failed to cleanup {temp_dir}: {e}")


def main():
    """Run companion files metadata integration tests."""
    print("OnCutF Companion Files Metadata Integration Test")
    print("=" * 50)

    print(f"COMPANION_FILES_ENABLED: {COMPANION_FILES_ENABLED}")
    print(f"LOAD_COMPANION_METADATA: {LOAD_COMPANION_METADATA}")

    temp_dir = None

    try:
        # Test 1: Companion Detection
        mp4_path, xml_path, temp_dir = test_companion_detection()

        # Test 2: Metadata Enhancement
        test_metadata_enhancement()

        print("\n" + "=" * 50)
        print("✓ All tests passed successfully!")
        print("✓ Companion files metadata integration is working correctly")

    except Exception as e:
        print(f"\n✗ Tests failed: {e}")
        return False

    finally:
        if temp_dir:
            cleanup_test_files(temp_dir)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
