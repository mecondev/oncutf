#!/usr/bin/env python3
"""
Script to reset column widths to their default values from config.py
This fixes the issue where columns are saved with incorrect 100px widths
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

def reset_column_widths():
    """Reset column widths to their default values."""
    config_path = get_config_path()

    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return

    # Load current config
    with open(config_path, 'r') as f:
        config = json.load(f)

    print("Current column widths:")
    current_widths = config.get("window", {}).get("file_table_column_widths", {})
    for key, width in current_widths.items():
        print(f"  {key}: {width}px")

    # Clear the column widths to force defaults
    if "window" in config:
        config["window"]["file_table_column_widths"] = {}
        print("\nCleared saved column widths")

    # Save the updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Config updated: {config_path}")
    print("\nDefault column widths from config.py should now be used:")
    print("  filename: 524px")
    print("  file_size: 75px")
    print("  type: 50px")
    print("  modified: 134px")
    print("  status: 45px (hardcoded)")

if __name__ == "__main__":
    reset_column_widths()
