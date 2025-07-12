#!/usr/bin/env python3
"""
Script to add test column widths to config.json to verify they get loaded
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

def add_test_column_widths():
    """Add test column widths to config.json."""
    config_path = get_config_path()

    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return

    # Load current config
    with open(config_path, 'r') as f:
        config = json.load(f)

    # Add test column widths
    test_widths = {
        "status": 45,
        "filename": 600,  # Different from default 524
        "file_size": 90,  # Different from default 75
        "type": 60,       # Different from default 50
        "modified": 150   # Different from default 134
    }

    if "window" in config:
        config["window"]["file_table_column_widths"] = test_widths
        print("Added test column widths:")
        for key, width in test_widths.items():
            print(f"  {key}: {width}px")

    # Save the updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Config updated: {config_path}")
    print("\nThese widths should now be loaded when the app starts")

if __name__ == "__main__":
    add_test_column_widths()
