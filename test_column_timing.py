#!/usr/bin/env python3
"""
Script to test column width timing fix
"""

import subprocess
import time
import json
import os
from pathlib import Path

def get_config_path():
    """Get the path to the config.json file."""
    if os.name == "nt":
        base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
        config_dir = os.path.join(base_dir, "oncutf")
    else:
        base_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        config_dir = os.path.join(base_dir, "oncutf")

    return Path(config_dir) / "config.json"

def setup_test_config():
    """Set up a test configuration with specific column widths."""
    config_path = get_config_path()

    # Create test config with specific column widths
    config = {
        "window": {
            "geometry": {"x": 192, "y": 106, "width": 1536, "height": 845},
            "window_state": "normal",
            "splitter_states": {"horizontal": [321, 864, 321], "vertical": [488, 293]},
            "file_table_column_widths": {
                "status": 45,
                "filename": 600,  # Different from default 524
                "file_size": 90,  # Different from default 75
                "type": 60,       # Different from default 50
                "modified": 150   # Different from default 134
            },
            "file_table_columns": {},
            "metadata_tree_column_widths": {},
            "metadata_tree_columns": {},
            "last_folder": "/mnt/data_1/C/ExifTest",  # Load files on startup
            "recursive_mode": False,
            "sort_column": 1,
            "sort_order": 0,
            "column_states": {
                "file_table": {"user_preferences": {}, "manual_flags": {}},
                "metadata_tree": {"user_preferences": {}, "manual_flags": {}}
            }
        },
        "file_hashes": {
            "enabled": True, "algorithm": "CRC32", "cache_size_limit": 10000,
            "auto_cleanup_days": 30, "hashes": {}
        },
        "app": {"theme": "dark", "language": "en", "auto_save_config": True, "recent_folders": []},
        "_metadata": {"last_saved": "2025-07-12T23:10:00.000000", "version": "v1.3", "app_name": "oncutf"}
    }

    # Save the config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Test config created: {config_path}")
    print("Expected column widths:")
    for key, width in config["window"]["file_table_column_widths"].items():
        print(f"  {key}: {width}px")

def test_column_timing():
    """Test the column width timing fix."""
    print("Testing column width timing fix...")

    # Set up test config
    setup_test_config()

    print("\nStarting application...")
    print("Check if the column widths are applied correctly on startup:")
    print("- filename should be 600px (not 524px)")
    print("- file_size should be 90px (not 75px)")
    print("- type should be 60px (not 50px)")
    print("- modified should be 150px (not 134px)")

    # Start the application
    subprocess.run(["python", "main.py"])

if __name__ == "__main__":
    test_column_timing()
