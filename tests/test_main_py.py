import importlib
import os
import sys
from types import ModuleType

import builtins
import pytest


def test_get_user_config_dir_unix(monkeypatch, tmp_path):
    # Ensure non-Windows branch uses XDG_CONFIG_HOME when set
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    from main import get_user_config_dir

    path = get_user_config_dir("myapp")
    assert str(tmp_path / "xdg" / "myapp") == path


def test_get_user_config_dir_windows(monkeypatch, tmp_path):
    # Simulate Windows environment by setting os.name and APPDATA
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))

    from main import get_user_config_dir

    path = get_user_config_dir("oncutf")
    assert str(tmp_path / "appdata" / "oncutf") == path


def test_cleanup_on_exit_calls_exiftool(monkeypatch):
    # Import main and reset internal flag
    import main

    # Ensure cleanup flag is reset
    monkeypatch.setattr(main, "_cleanup_done", False)

    # Create a fake utils.exiftool_wrapper module with a callable ExifToolWrapper
    fake_mod = ModuleType("utils.exiftool_wrapper")

    calls = {"count": 0}


    class FakeExif:
        @staticmethod
        def force_cleanup_all_exiftool_processes():
            calls["count"] += 1


    fake_mod.ExifToolWrapper = FakeExif

    # Inject into sys.modules so import inside function finds it
    sys.modules["utils.exiftool_wrapper"] = fake_mod

    try:
        # First call should invoke the fake cleanup
        main.cleanup_on_exit()
        assert calls["count"] == 1
        assert main._cleanup_done is True

        # Second call should be a no-op (already cleaned)
        main.cleanup_on_exit()
        assert calls["count"] == 1

    finally:
        # Clean up our injected module
        sys.modules.pop("utils.exiftool_wrapper", None)


def test_cleanup_on_exit_handles_import_error(monkeypatch, caplog):
    import main

    # Reset flag
    monkeypatch.setattr(main, "_cleanup_done", False)

    # Ensure no utils.exiftool_wrapper present
    sys.modules.pop("utils.exiftool_wrapper", None)

    # Monkeypatch builtins.__import__ to raise for the target module to simulate import failure
    import builtins

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "utils.exiftool_wrapper" or name.endswith("exiftool_wrapper"):
            raise ModuleNotFoundError("simulated import failure")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        main.cleanup_on_exit()
    finally:
        # restore import to avoid affecting other tests
        monkeypatch.setattr(builtins, "__import__", real_import)

    # We expect the function to catch the ImportError and log a warning
    assert any("Error in emergency cleanup" in rec.getMessage() for rec in caplog.records)
