#!/usr/bin/env python3
"""Module: oncutf.__main__.

This module allows the oncutf package to be executed as a module using:
    python -m oncutf

It serves as an alternative entry point to the root main.py script.
"""

import os
import sys

# Add parent directory (project root) to path to find main.py
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import main

if __name__ == "__main__":
    sys.exit(main())
