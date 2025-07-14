#!/usr/bin/env python3
"""
Debug script για να ενεργοποιήσω τα debug logs για το metadata.
"""

import logging
import sys
import os

# Set up debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run the main application
from main import main

if __name__ == "__main__":
    print("Starting application with debug logging enabled...")
    sys.exit(main())
