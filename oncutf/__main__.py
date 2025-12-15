#!/usr/bin/env python3
"""
Module: oncutf.__main__

This module allows the oncutf package to be executed as a module using:
    python -m oncutf

It serves as an alternative entry point to the root main.py script.
"""

import sys

from main import main

if __name__ == "__main__":
    sys.exit(main())
