#!/usr/bin/env python
"""
Test script for companion files edge cases:
- Non-Sony XML files in same folder
- SRT subtitle files
- Mixed companion types
"""

import os
import sys
import tempfile

# Setup sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.companion_files_helper import CompanionFilesHelper


def create_mixed_test_files():
    """Create test files with various companion types."""
    temp_dir = tempfile.mkdtemp(prefix="oncutf_mixed_companion_test_")
    print(f"Created test directory: {temp_dir}")

    # Create main MP4 file
    mp4_path = os.path.join(temp_dir, "movie.MP4")
    with open(mp4_path, "wb") as f:
        f.write(b'\x00\x00\x00\x20ftypmp42')
        f.write(b'\x00' * 100)

    # Create Sony XML companion (should be detected)
    sony_xml_path = os.path.join(temp_dir, "movieM01.XML")
    sony_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<NonRealTimeMeta>
    <Device manufacturer="Sony" modelName="FX30" serialNo="12345"/>
    <VideoFormat videoCodec="XAVC S" audioCodec="PCM">
        <VideoFrame formatFps="25p" pixel="3840x2160"/>
    </VideoFormat>
</NonRealTimeMeta>'''

    with open(sony_xml_path, "w", encoding="utf-8") as f:
        f.write(sony_xml_content)

    # Create non-Sony XML file (should NOT be detected as companion)
    other_xml_path = os.path.join(temp_dir, "config.xml")
    other_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Configuration>
    <Settings>
        <Quality>High</Quality>
        <Resolution>4K</Resolution>
    </Settings>
</Configuration>'''

    with open(other_xml_path, "w", encoding="utf-8") as f:
        f.write(other_xml_content)

    # Create random XML with similar name (should NOT be detected)
    random_xml_path = os.path.join(temp_dir, "movie_backup.xml")
    with open(random_xml_path, "w", encoding="utf-8") as f:
        f.write(other_xml_content)

    # Create SRT subtitle file (should be detected as companion)
    srt_path = os.path.join(temp_dir, "movie.srt")
    srt_content = '''1
00:00:01,000 --> 00:00:03,000
Hello world!

2
00:00:04,000 --> 00:00:06,000
This is a subtitle.'''

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    # Create VTT subtitle file (should be detected as companion)
    vtt_path = os.path.join(temp_dir, "movie.vtt")
    vtt_content = '''WEBVTT

00:01.000 --> 00:03.000
Hello from VTT!'''

    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write(vtt_content)

    return {
        "temp_dir": temp_dir,
        "mp4": mp4_path,
        "sony_xml": sony_xml_path,
        "other_xml": other_xml_path,
        "random_xml": random_xml_path,
        "srt": srt_path,
        "vtt": vtt_path
    }


def test_companion_detection_edge_cases():
    """Test companion detection with various file types."""
    print("\n=== Testing Companion Detection Edge Cases ===")

    files = create_mixed_test_files()

    try:
        # Get all files in the directory
        folder_files = [
            files["mp4"], files["sony_xml"], files["other_xml"],
            files["random_xml"], files["srt"], files["vtt"]
        ]

        # Test companion detection for MP4
        companions = CompanionFilesHelper.find_companion_files(files["mp4"], folder_files)

        print("\nFiles in test directory:")
        for key, path in files.items():
            if key != "temp_dir":
                print(f"  {key}: {os.path.basename(path)}")

        print("\nDetected companions for movie.MP4:")
        for companion in companions:
            print(f"  ✓ {os.path.basename(companion)}")

        # Expected companions: movieM01.XML, movie.srt, movie.vtt
        expected_companions = [
            os.path.basename(files["sony_xml"]),   # movieM01.XML
            os.path.basename(files["srt"]),        # movie.srt
            os.path.basename(files["vtt"])         # movie.vtt
        ]

        detected_names = [os.path.basename(c) for c in companions]

        print(f"\nExpected companions: {expected_companions}")
        print(f"Detected companions: {detected_names}")

        # Check each expected companion
        for expected in expected_companions:
            if expected in detected_names:
                print(f"✓ {expected} correctly detected")
            else:
                print(f"✗ {expected} NOT detected")

        # Check for false positives
        unexpected = [
            os.path.basename(files["other_xml"]),     # config.xml
            os.path.basename(files["random_xml"])     # movie_backup.xml
        ]

        for unexpected_file in unexpected:
            if unexpected_file in detected_names:
                print(f"⚠ {unexpected_file} incorrectly detected as companion")
            else:
                print(f"✓ {unexpected_file} correctly ignored")

        return files

    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


def test_metadata_extraction():
    """Test metadata extraction from different companion types."""
    print("\n=== Testing Metadata Extraction ===")

    files = create_mixed_test_files()

    try:
        # Test Sony XML metadata extraction
        sony_metadata = CompanionFilesHelper.extract_companion_metadata(files["sony_xml"])
        print(f"\nSony XML metadata ({os.path.basename(files['sony_xml'])}):")
        for key, value in sony_metadata.items():
            print(f"  {key}: {value}")

        # Test non-Sony XML (should return empty or minimal metadata)
        other_metadata = CompanionFilesHelper.extract_companion_metadata(files["other_xml"])
        print(f"\nNon-Sony XML metadata ({os.path.basename(files['other_xml'])}):")
        for key, value in other_metadata.items():
            print(f"  {key}: {value}")

        # Test SRT file (should return empty metadata - SRT is not parsed for metadata)
        srt_metadata = CompanionFilesHelper.extract_companion_metadata(files["srt"])
        print(f"\nSRT subtitle metadata ({os.path.basename(files['srt'])}):")
        if srt_metadata:
            for key, value in srt_metadata.items():
                print(f"  {key}: {value}")
        else:
            print("  (No metadata extracted from SRT - expected behavior)")

        return files

    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


def cleanup_test_files(files):
    """Clean up test files."""
    try:
        import shutil
        shutil.rmtree(files["temp_dir"], ignore_errors=True)
        print(f"✓ Cleaned up test directory: {files['temp_dir']}")
    except Exception as e:
        print(f"⚠ Failed to cleanup: {e}")


def main():
    """Run companion files edge case tests."""
    print("OnCutF Companion Files Edge Cases Test")
    print("=" * 50)

    files = None

    try:
        # Test 1: Companion Detection Edge Cases
        files = test_companion_detection_edge_cases()

        # Test 2: Metadata Extraction
        test_metadata_extraction()

        print("\n" + "=" * 50)
        print("✓ All edge case tests completed!")

    except Exception as e:
        print(f"\n✗ Tests failed: {e}")
        return False

    finally:
        if files:
            cleanup_test_files(files)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
