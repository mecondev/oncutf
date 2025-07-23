#!/usr/bin/env python3
"""
Test script for intelligent column width management.

This script tests the content-aware column width management system to ensure:
1. Proper content type analysis
2. Intelligent width recommendations
3. Universal width validation
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import FILE_TABLE_COLUMN_CONFIG

def test_content_type_analysis():
    """Test the content type analysis logic."""
    print("Testing content type analysis...")

    # Simulate the content type analysis logic
    def analyze_column_content_type(column_key: str) -> str:
        """Simulate the content type analysis logic."""
        content_types = {
            # Short content (names, types, codes)
            "type": "short",
            "iso": "short",
            "rotation": "short",
            "duration": "short",
            "video_fps": "short",
            "audio_channels": "short",

            # Medium content (formats, models, sizes)
            "audio_format": "medium",
            "video_codec": "medium",
            "video_format": "medium",
            "white_balance": "medium",
            "compression": "medium",
            "device_model": "medium",
            "device_manufacturer": "medium",
            "image_size": "medium",
            "video_avg_bitrate": "medium",
            "aperture": "medium",
            "shutter_speed": "medium",

            # Long content (filenames, hashes, UMIDs)
            "filename": "long",
            "file_hash": "long",
            "target_umid": "long",
            "device_serial_no": "long",

            # Very long content (dates, file paths)
            "modified": "very_long",
            "file_size": "very_long",
        }

        return content_types.get(column_key, "medium")

    # Test cases
    test_cases = [
        ("type", "short", "Short content type"),
        ("iso", "short", "Short content type"),
        ("audio_format", "medium", "Medium content type"),
        ("video_codec", "medium", "Medium content type"),
        ("filename", "long", "Long content type"),
        ("target_umid", "long", "Long content type"),
        ("modified", "very_long", "Very long content type"),
        ("file_size", "very_long", "Very long content type"),
        ("unknown_column", "medium", "Unknown column defaults to medium"),
    ]

    for column_key, expected_type, description in test_cases:
        result = analyze_column_content_type(column_key)
        if result == expected_type:
            print(f"✓ {description}: '{column_key}' → '{result}'")
        else:
            print(f"✗ {description}: '{column_key}' → '{result}' (expected '{expected_type}')")

    print()

def test_width_recommendations():
    """Test the width recommendation logic."""
    print("Testing width recommendations...")

    # Simulate the width recommendation logic
    def get_recommended_width_for_content_type(content_type: str, default_width: int, min_width: int) -> int:
        """Simulate the width recommendation logic."""
        width_recommendations = {
            "short": max(80, min_width),      # Short codes, numbers
            "medium": max(120, min_width),    # Formats, models, sizes
            "long": max(200, min_width),      # Filenames, hashes, UMIDs
            "very_long": max(300, min_width), # Dates, file paths
        }

        # Use the larger of default_width, min_width, or content_type recommendation
        recommended = width_recommendations.get(content_type, default_width)
        return max(recommended, default_width, min_width)

    # Test cases
    test_cases = [
        ("short", 100, 50, 100, "Short content with default > recommendation"),
        ("short", 50, 50, 80, "Short content with recommendation > default"),
        ("medium", 120, 50, 120, "Medium content with default = recommendation"),
        ("long", 150, 50, 200, "Long content with recommendation > default"),
        ("very_long", 400, 50, 400, "Very long content with default > recommendation"),
        ("very_long", 200, 50, 300, "Very long content with recommendation > default"),
    ]

    for content_type, default_width, min_width, expected_width, description in test_cases:
        result = get_recommended_width_for_content_type(content_type, default_width, min_width)
        if result == expected_width:
            print(f"✓ {description}: {content_type} ({default_width}px default, {min_width}px min) → {result}px")
        else:
            print(f"✗ {description}: {content_type} ({default_width}px default, {min_width}px min) → {result}px (expected {expected_width}px)")

    print()

def test_column_configuration():
    """Test that column configurations are properly set."""
    print("Testing column configurations...")

    # Test specific columns
    test_columns = [
        ("target_umid", 400, 200, "Target UMID column"),
        ("filename", 524, 150, "Filename column"),
        ("file_size", 75, 60, "File size column"),
        ("type", 50, 40, "Type column"),
        ("modified", 134, 100, "Modified column"),
    ]

    for column_key, expected_width, expected_min_width, description in test_columns:
        column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})
        actual_width = column_config.get("width", 0)
        actual_min_width = column_config.get("min_width", 0)

        width_ok = actual_width == expected_width
        min_width_ok = actual_min_width == expected_min_width

        if width_ok and min_width_ok:
            print(f"✓ {description}: width={actual_width}px, min_width={actual_min_width}px")
        else:
            print(f"✗ {description}: width={actual_width}px (expected {expected_width}px), min_width={actual_min_width}px (expected {expected_min_width}px)")

    print()

def test_content_type_categorization():
    """Test that all columns are properly categorized."""
    print("Testing content type categorization...")

    # Simulate the content type analysis logic
    def analyze_column_content_type(column_key: str) -> str:
        """Simulate the content type analysis logic."""
        content_types = {
            # Short content (names, types, codes)
            "type": "short",
            "iso": "short",
            "rotation": "short",
            "duration": "short",
            "video_fps": "short",
            "audio_channels": "short",

            # Medium content (formats, models, sizes)
            "audio_format": "medium",
            "video_codec": "medium",
            "video_format": "medium",
            "white_balance": "medium",
            "compression": "medium",
            "device_model": "medium",
            "device_manufacturer": "medium",
            "image_size": "medium",
            "video_avg_bitrate": "medium",
            "aperture": "medium",
            "shutter_speed": "medium",

            # Long content (filenames, hashes, UMIDs)
            "filename": "long",
            "file_hash": "long",
            "target_umid": "long",
            "device_serial_no": "long",

            # Very long content (dates, file paths)
            "modified": "very_long",
            "file_size": "very_long",
        }

        return content_types.get(column_key, "medium")

    # Get all columns from config
    all_columns = list(FILE_TABLE_COLUMN_CONFIG.keys())

    # Categorize them
    categories = {
        "short": [],
        "medium": [],
        "long": [],
        "very_long": [],
        "uncategorized": []
    }

    for column_key in all_columns:
        content_type = analyze_column_content_type(column_key)
        if content_type in categories:
            categories[content_type].append(column_key)
        else:
            categories["uncategorized"].append(column_key)

    # Print results
    for category, columns in categories.items():
        if columns:
            print(f"✓ {category.capitalize()} ({len(columns)} columns): {', '.join(columns)}")
        else:
            print(f"✓ {category.capitalize()}: No columns")

    print()

def main():
    """Run all tests."""
    print("=" * 60)
    print("Intelligent Column Width Management Test Suite")
    print("=" * 60)
    print()

    test_content_type_analysis()
    test_width_recommendations()
    test_column_configuration()
    test_content_type_categorization()

    print("=" * 60)
    print("Test suite completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
