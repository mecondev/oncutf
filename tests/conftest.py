"""
Module: conftest.py

Author: Michael Economou
Date: 2025-05-31

Global pytest configuration and fixtures for the oncutf test suite.
Includes CI-friendly setup for PyQt5 testing and common fixtures.
"""

import os
import sys

# Add project root to sys.path so 'widgets', 'models', etc. can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers if not already added via pyproject.toml
    config.addinivalue_line("markers", "gui: mark test as requiring GUI")
    config.addinivalue_line("markers", "local_only: mark test as local environment only")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle CI environment."""
    # Check if we're in CI environment
    is_ci = "CI" in os.environ or "GITHUB_ACTIONS" in os.environ

    if is_ci:
        # Skip GUI tests in CI
        skip_gui = pytest.mark.skip(reason="GUI tests don't work on CI")
        skip_local = pytest.mark.skip(reason="Local-only tests skipped on CI")

        for item in items:
            if "gui" in item.keywords:
                item.add_marker(skip_gui)
            if "local_only" in item.keywords:
                item.add_marker(skip_local)


@pytest.fixture(scope="session")
def ci_environment():
    """Fixture to detect CI environment."""
    return "CI" in os.environ or "GITHUB_ACTIONS" in os.environ


@pytest.fixture(scope="session")
def pyqt5_available():
    """Fixture to check PyQt5 availability."""
    try:
        import PyQt5  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.fixture
def mock_theme_colors():
    """Fixture providing mock theme colors for testing."""
    return {
        "table_text": "#000000",
        "table_background": "#ffffff",
        "table_selection_text": "#ffffff",
        "table_selection_background": "#0078d4",
        "table_hover_background": "#f0f0f0"
    }


@pytest.fixture
def sample_metadata():
    """Fixture providing sample metadata for testing."""
    return {
        "EXIF": {
            "Camera Make": "Canon",
            "Camera Model": "EOS R5",
            "ISO": "100",
            "F-Stop": "f/2.8"
        },
        "File": {
            "File Name": "test_image.jpg",
            "File Size": "2.5 MB",
            "File Type": "JPEG"
        },
        "GPS": {
            "Latitude": "37.7749° N",
            "Longitude": "122.4194° W"
        }
    }
