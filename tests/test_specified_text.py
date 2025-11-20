"""
Module: test_specified_text.py

Author: Michael Economou
Date: 2025-05-31

This module provides functionality for the OnCutF batch file renaming application.
"""

import warnings

from modules.specified_text_module import SpecifiedTextModule

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


def test_specified_text_simple():
    data = {"type": "specified_text", "text": "hello"}
    result = SpecifiedTextModule.apply_from_data(data, _file_item=None)
    assert result == "hello"


def test_specified_text_invalid():
    data = {"type": "specified_text", "text": "file/name"}
    result = SpecifiedTextModule.apply_from_data(data, _file_item=None)
    from config import INVALID_FILENAME_MARKER

    assert result == INVALID_FILENAME_MARKER
