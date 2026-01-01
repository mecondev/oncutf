import builtins
import os
import sys
from types import ModuleType


def test_app_paths_unix(monkeypatch, tmp_path):
    """Test AppPaths returns correct paths on Unix-like systems."""
    from oncutf.utils.paths import AppPaths

    # Reset cached paths
    AppPaths.reset()

    if os.name == "nt":
        # On Windows, test LOCALAPPDATA behavior
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
        path = AppPaths.get_user_data_dir()
        assert "oncutf" in str(path)
    else:
        # On Unix, test XDG_DATA_HOME behavior
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
        AppPaths.reset()  # Reset again after env change
        path = AppPaths.get_user_data_dir()
        assert str(tmp_path / "xdg_data" / "oncutf") == str(path)

    # Cleanup
    AppPaths.reset()


def test_app_paths_windows(monkeypatch, tmp_path):
    """Test AppPaths returns correct paths on Windows."""
    from oncutf.utils.paths import AppPaths

    # Reset cached paths
    AppPaths.reset()

    if os.name == "nt":
        # On Windows, test LOCALAPPDATA behavior
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
        AppPaths.reset()
        path = AppPaths.get_user_data_dir()
        assert str(tmp_path / "localappdata" / "oncutf") == str(path)
    else:
        # On Unix, just verify function works
        path = AppPaths.get_user_data_dir()
        assert "oncutf" in str(path)

    # Cleanup
    AppPaths.reset()


def test_cleanup_on_exit_calls_exiftool(monkeypatch):
    # Import main and reset internal flag
    import main

    # Ensure cleanup flag is reset
    monkeypatch.setattr(main, "_cleanup_done", False)

    # Create a fake utils.exiftool_wrapper module with a callable ExifToolWrapper
    fake_mod = ModuleType("oncutf.utils.shared.exiftool_wrapper")

    calls = {"count": 0}

    class FakeExif:
        @staticmethod
        def force_cleanup_all_exiftool_processes():
            calls["count"] += 1

    fake_mod.ExifToolWrapper = FakeExif

    # Inject into sys.modules so import inside function finds it
    sys.modules["oncutf.utils.shared.exiftool_wrapper"] = fake_mod

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
        sys.modules.pop("oncutf.utils.shared.exiftool_wrapper", None)


def test_cleanup_on_exit_handles_import_error(monkeypatch, caplog):
    import main

    # Reset flag
    monkeypatch.setattr(main, "_cleanup_done", False)

    # Ensure no utils.exiftool_wrapper present
    sys.modules.pop("utils.exiftool_wrapper", None)

    # Monkeypatch builtins.__import__ to raise for the target module to simulate import failure

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
