"""
Module: test_transform_utils.py

Author: Michael Economou
Date: 2025-05-31

This module provides functionality for the OnCutF batch file renaming application.
"""

import warnings

import pytest

from utils.transform_utils import apply_transform

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


@pytest.mark.parametrize(
    "name, transform, expected",
    [
        ("My File Name", "original", "My File Name"),
        ("My File Name", "lower", "my file name"),
        ("My File Name", "UPPER", "MY FILE NAME"),
        ("My File Name", "Capitalize", "My File Name"),
        ("my file name", "Capitalize", "My File Name"),
        ("my file name", "camelCase", "myFileName"),
        ("my file name", "PascalCase", "MyFileName"),
        ("my file name", "Title Case", "My File Name"),
        ("My File Name", "snake_case", "My_File_Name"),
        ("My File Name", "kebab-case", "My-File-Name"),
        ("", "snake_case", ""),
        ("Test--Name__Mix", "snake_case", "Test-Name_Mix"),
        ("Symbols@!$%", "kebab-case", "Symbols@!$%"),
    ],
)
def test_apply_transform_basic(name, transform, expected):
    assert apply_transform(name, transform) == expected


def test_apply_transform_greeklish():
    greek = "Καλημέρα Ελλάδα"
    result = apply_transform(greek, "greeklish")
    assert isinstance(result, str)
    assert all(c.isascii() for c in result)
    assert "κ" not in result.lower() and "λ" not in result.lower()


def test_apply_transform_greeklish_passthrough():
    latin = "already_latin_text"
    result = apply_transform(latin, "greeklish")
    assert result == latin
