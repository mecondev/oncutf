"""
Module: mocks.py

Author: Michael Economou
Date: 2025-05-12

Mock objects for testing - Windows/Linux/Greek compatible
"""

import os
import tempfile


class MockFileItem:
    """Mock FileItem that works cross-platform with proper path normalization."""

    def __init__(self, *, filename="mockfile.mp3", date=None, metadata=None):
        self.filename = filename
        # Use temp directory for cross-platform compatibility
        temp_dir = tempfile.gettempdir()
        # Normalize path for Windows/Linux compatibility
        self.full_path = os.path.normpath(os.path.join(temp_dir, "mock", "path", filename))
        self.date = date
        self.metadata = metadata or {}
