#!/usr/bin/env python3
"""
Script to generate fonts_rc.py from fonts.qrc resource file.

Author: Michael Economou
Date: 2025-12-21

Usage:
    python scripts/generate_fonts_rc.py

This script must be run after cloning the repository or when font resources change.
It uses PyQt5's pyrcc5 tool to compile the .qrc file into a Python module.
"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Generate fonts_rc.py from fonts.qrc."""
    # Get paths relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    qrc_file = project_root / "resources" / "fonts.qrc"
    output_file = project_root / "oncutf" / "utils" / "fonts_rc.py"

    if not qrc_file.exists():
        print(f"ERROR: Resource file not found: {qrc_file}")
        return 1

    print(f"Generating {output_file.name} from {qrc_file.name}...")

    # Try pyrcc5 first (PyQt5)
    try:
        subprocess.run(
            ["pyrcc5", str(qrc_file), "-o", str(output_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"SUCCESS: Generated {output_file}")
        print(f"  Size: {output_file.stat().st_size:,} bytes")
        return 0
    except FileNotFoundError:
        print("pyrcc5 not found, trying pyside6-rcc...")
    except subprocess.CalledProcessError as e:
        print(f"pyrcc5 failed: {e.stderr}")

    # Try pyside6-rcc as fallback
    try:
        subprocess.run(
            ["pyside6-rcc", str(qrc_file), "-o", str(output_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"SUCCESS: Generated {output_file}")
        print(f"  Size: {output_file.stat().st_size:,} bytes")
        return 0
    except FileNotFoundError:
        print("pyside6-rcc not found either.")
        print("\nPlease install PyQt5 development tools:")
        print("  pip install PyQt5")
        print("  # or on Linux: sudo apt install pyqt5-dev-tools")
        return 1
    except subprocess.CalledProcessError as e:
        print(f"pyside6-rcc failed: {e.stderr}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
