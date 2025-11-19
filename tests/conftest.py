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


def pytest_collection_modifyitems(session, config, items):
    """Modify test collection to handle CI environment."""
    # Reference session/config to avoid unused-argument lint warnings while
    # keeping signature compatible with pytest hookspec.
    _ = session
    _ = config

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
        "table_hover_background": "#f0f0f0",
    }


@pytest.fixture
def sample_metadata():
    """Fixture providing sample metadata for testing."""
    return {
        "EXIF": {"Camera Make": "Canon", "Camera Model": "EOS R5", "ISO": "100", "F-Stop": "f/2.8"},
        "File": {"File Name": "test_image.jpg", "File Size": "2.5 MB", "File Type": "JPEG"},
        "GPS": {"Latitude": "37.7749° N", "Longitude": "122.4194° W"},
    }


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for all GUI tests."""
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QCoreApplication
        
        # Check if QApplication already exists
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        yield app
        
        # Don't quit the app in session scope - let it live for all tests
        # Cleanup will happen via qt_cleanup fixture between tests
        
    except ImportError:
        yield None


@pytest.fixture(autouse=True)
def qt_cleanup(qapp):
    """Ensure proper Qt cleanup between tests."""
    yield
    
    if qapp:
        try:
            from PyQt5.QtCore import QCoreApplication, QTimer
            from PyQt5.QtWidgets import QApplication, QWidget
            
            # Process any pending events
            QCoreApplication.processEvents()
            
            # Find and delete all top-level widgets
            for widget in QApplication.topLevelWidgets():
                try:
                    widget.close()
                    widget.deleteLater()
                except RuntimeError:
                    pass
            
            # Process events again to clean up
            QCoreApplication.processEvents()
            
        except (RuntimeError, AttributeError, ImportError):
            pass


def pytest_sessionfinish(session, exitstatus):
    """Cleanup after all tests."""
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            try:
                app.quit()
            except RuntimeError:
                pass
    except (ImportError, RuntimeError):
        pass
