#!/usr/bin/env python3
"""
Script to create a minimal config.json with test column widths
"""

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

def create_test_config():
    """Create a minimal config.json with test column widths."""
    config_path = get_config_path()

    # Create minimal config with test column widths
    config = {
        "window": {
            "geometry": {
                "x": 192,
                "y": 106,
                "width": 1536,
                "height": 845
            },
            "window_state": "normal",
            "splitter_states": {
                "horizontal": [321, 864, 321],
                "vertical": [488, 293]
            },
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
            "last_folder": "",
            "recursive_mode": False,
            "sort_column": 1,
            "sort_order": 0,
            "column_states": {
                "file_table": {
                    "user_preferences": {},
                    "manual_flags": {}
                },
                "metadata_tree": {
                    "user_preferences": {},
                    "manual_flags": {}
                }
            }
        },
        "file_hashes": {
            "enabled": True,
            "algorithm": "CRC32",
            "cache_size_limit": 10000,
            "auto_cleanup_days": 30,
            "hashes": {}
        },
        "app": {
            "theme": "dark",
            "language": "en",
            "auto_save_config": True,
            "recent_folders": []
        },
        "_metadata": {
            "last_saved": "2025-07-12T23:00:00.000000",
            "version": "v1.3",
            "app_name": "oncutf"
        }
    }

    # Save the config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Created config file: {config_path}")
    print("Test column widths:")
    for key, width in config["window"]["file_table_column_widths"].items():
        print(f"  {key}: {width}px")
    print("\nThese should be loaded when the app starts")

if __name__ == "__main__":
    create_test_config()
