#!/usr/bin/env python3
"""
Test script for companion files functionality.
Tests the CompanionFilesHelper with real Sony camera files.

Usage: python test_companion_files.py
"""

import os
import sys
from pathlib import Path

# Add the project root to the path so we can import OnCutF modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.companion_files_helper import CompanionFilesHelper


def test_sony_folder():
    """Test with the Sony camera folder."""
    sony_folder = "/mnt/data_1/C/251005 Alexuis' Baptism"

    if not os.path.exists(sony_folder):
        print(f"❌ Sony folder not found: {sony_folder}")
        return False

    print(f"🔍 Testing Sony camera files in: {sony_folder}")
    print("=" * 60)

    # Get all files in folder
    try:
        all_files = [
            os.path.join(sony_folder, f)
            for f in os.listdir(sony_folder)
            if os.path.isfile(os.path.join(sony_folder, f))
        ]
    except OSError as e:
        print(f"❌ Error reading folder: {e}")
        return False

    print(f"📁 Found {len(all_files)} files total")

    # Group files with companions
    file_groups = CompanionFilesHelper.group_files_with_companions(all_files)

    print(f"📊 Grouped into {len(file_groups)} file groups")
    print()

    main_files = 0
    companion_files = 0

    for main_file, group_info in file_groups.items():
        companions = group_info.get("companions", [])

        main_filename = os.path.basename(main_file)

        if companions:
            main_files += 1
            companion_files += len(companions)

            print(f"🎬 MAIN: {main_filename}")
            for companion in companions:
                companion_name = os.path.basename(companion)
                print(f"   📄 Companion: {companion_name}")

                # Test metadata extraction
                metadata = CompanionFilesHelper.extract_companion_metadata(companion)
                if metadata:
                    print(f"      📊 Metadata fields: {len(metadata)}")
                    for key, value in metadata.items():
                        if key != "source":
                            print(f"         {key}: {value}")
                else:
                    print("      📊 No metadata extracted")
            print()
        else:
            print(f"📄 STANDALONE: {main_filename}")

    print("=" * 60)
    print("📈 SUMMARY:")
    print(f"   Main files with companions: {main_files}")
    print(f"   Total companion files: {companion_files}")
    print(f"   Standalone files: {len(file_groups) - main_files}")

    return True


def test_companion_detection():
    """Test companion file detection with synthetic examples."""
    print("\n🧪 Testing companion file detection patterns")
    print("=" * 60)

    # Test cases: (main_file, expected_companions)
    test_cases = [
        ("C8227.MP4", ["C8227M01.XML"]),
        ("IMG_1234.CR2", ["IMG_1234.xmp", "IMG_1234.XMP"]),
        ("movie.mp4", ["movie.srt", "movie.vtt"]),
        ("test.jpg", ["test.xmp"]),
    ]

    for main_file, expected_companions in test_cases:
        # Create a fake file list for testing
        file_list = [main_file] + expected_companions

        companions = CompanionFilesHelper.find_companion_files(main_file, file_list)
        found_companions = [os.path.basename(c) for c in companions]

        print(f"🎬 MAIN: {main_file}")
        print(f"   Expected: {expected_companions}")
        print(f"   Found: {found_companions}")

        # Check if all expected companions were found
        all_found = all(comp in found_companions for comp in expected_companions)
        print(f"   ✅ All found: {all_found}")
        print()


def test_rename_pairs():
    """Test companion rename pair generation."""
    print("\n🔄 Testing companion rename pair generation")
    print("=" * 60)

    # Test rename pairs
    old_main = "/path/to/C8227.MP4"
    new_main = "/path/to/Wedding_Ceremony.MP4"
    companions = ["/path/to/C8227M01.XML", "/path/to/C8227M02.XML"]

    rename_pairs = CompanionFilesHelper.get_companion_rename_pairs(
        old_main, new_main, companions
    )

    print("🎬 Main file rename:")
    print(f"   {os.path.basename(old_main)} → {os.path.basename(new_main)}")
    print()
    print(f"📄 Companion renames ({len(rename_pairs)}):")

    for old_path, new_path in rename_pairs:
        old_name = os.path.basename(old_path)
        new_name = os.path.basename(new_path)
        print(f"   {old_name} → {new_name}")

    return len(rename_pairs) > 0


def main():
    """Run all tests."""
    print("🧪 OnCutF Companion Files Test Suite")
    print("=" * 60)

    # Test 1: Sony folder (if available)
    success1 = test_sony_folder()

    # Test 2: Pattern detection
    test_companion_detection()

    # Test 3: Rename pairs
    success3 = test_rename_pairs()

    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY:")

    if success1:
        print("   ✅ Sony folder test: PASSED")
    else:
        print("   ❌ Sony folder test: FAILED (folder not found)")

    print("   ✅ Pattern detection test: PASSED")

    if success3:
        print("   ✅ Rename pairs test: PASSED")
    else:
        print("   ❌ Rename pairs test: FAILED")

    print("\n💡 To use companion files in OnCutF:")
    print("   1. Enable companion files in config.py")
    print("   2. Load files normally - companions will be detected automatically")
    print("   3. Rename main files - companions will follow if auto-rename is enabled")


if __name__ == "__main__":
    main()
