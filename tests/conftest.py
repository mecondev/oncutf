"""Module: conftest.py

Author: Michael Economou
Date: 2025-05-09

Global pytest configuration and fixtures for the oncutf test suite.
Includes CI-friendly setup for PyQt5 testing and common fixtures.
"""

import atexit
import os
import platform
import signal
import sys
from types import ModuleType

# Add project root to sys.path so 'widgets', 'models', etc. can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

_SESSION_QAPP = None
_QT_MESSAGE_HANDLER_INSTALLED = False
try:
    from PyQt5.QtCore import qInstallMessageHandler
    from PyQt5.QtWidgets import QApplication

    _SESSION_QAPP = QApplication.instance() or QApplication([])
    if not _QT_MESSAGE_HANDLER_INSTALLED:
        def _qt_message_handler(_msg_type, _context, message):
            if "Must construct a QGuiApplication" in message:
                return

        qInstallMessageHandler(_qt_message_handler)
        _QT_MESSAGE_HANDLER_INSTALLED = True
except ImportError:
    _SESSION_QAPP = None


@pytest.fixture(autouse=True)
def neutralize_import_side_effects(monkeypatch):
    """Prevent import-time side effects that modify global state.

    This fixture inserts a noop `utils.logger_setup.ConfigureLogger` module
    into sys.modules and patches signal.signal and atexit.register to harmless
    callables, ensuring that importing modules like `main.py` does not:
    - create log directories/files on disk,
    - register signal handlers globally,
    - register atexit callbacks globally.

    This fixture is autouse, so it applies to all tests automatically.
    """
    # Fake utils.logger_setup to prevent ConfigureLogger from creating log dirs
    fake_logger = ModuleType("oncutf.utils.logger_setup")
    fake_logger.ConfigureLogger = lambda *_args, **_kwargs: None
    original_logger = sys.modules.get("oncutf.utils.logger_setup")
    sys.modules["oncutf.utils.logger_setup"] = fake_logger

    # Replace signal.signal and atexit.register with noop callables
    # to prevent modification of global state during tests
    monkeypatch.setattr(signal, "signal", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(atexit, "register", lambda *_args, **_kwargs: None)

    yield

    # Cleanup: restore original modules
    if original_logger is not None:
        sys.modules["oncutf.utils.logger_setup"] = original_logger
    else:
        sys.modules.pop("oncutf.utils.logger_setup", None)


@pytest.fixture(autouse=True)
def preserve_os_name():
    """Preserve os.name to prevent pathlib issues in VS Code test runner.

    Some tests modify os.name to test cross-platform behavior. This can cause
    issues with the VS Code pytest extension which calls pathlib.Path.cwd()
    after tests complete. If os.name is set to 'posix' on Windows, pathlib
    will try to instantiate PosixPath which fails on Windows.

    This fixture ensures os.name is always restored to its original value.
    """
    original_os_name = os.name
    yield
    # Force restore os.name to original value
    os.name = original_os_name


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers if not already added via pyproject.toml
    config.addinivalue_line("markers", "gui: mark test as requiring GUI")
    config.addinivalue_line("markers", "local_only: mark test as local environment only")


def pytest_sessionstart(session) -> None:
    """Ensure a QApplication exists before any test collection side effects."""
    _ = session
    try:
        from PyQt5.QtWidgets import QApplication

        if QApplication.instance() is None:
            QApplication([])
    except ImportError:
        return


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
            from PyQt5.QtCore import QCoreApplication
            from PyQt5.QtWidgets import QApplication

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
    """Cleanup after all tests.

    CRITICAL: This must restore os.name BEFORE returning control to pytest/VS Code,
    otherwise pathlib.Path.cwd() in the VS Code extension will fail with
    'cannot instantiate PosixPath on your system' error on Windows.
    """
    # MUST restore os.name first, before any other cleanup
    # Some tests (like test_get_user_config_dir_unix) change os.name to 'posix'
    # If not restored, VS Code pytest extension will crash when calling pathlib.Path.cwd()
    actual_os_name = "nt" if platform.system() == "Windows" else "posix"
    os.name = actual_os_name

    # Do not call app.quit() here to avoid QGuiApplication warnings
    # during pytest teardown. Let the process exit naturally.
