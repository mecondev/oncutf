"""Tests for oncutf.utils.paths module."""

import os
import platform
from pathlib import Path


class TestAppPaths:
    """Test suite for AppPaths class."""

    def setup_method(self):
        """Reset AppPaths before each test."""
        from oncutf.utils.paths import AppPaths

        AppPaths.reset()

    def teardown_method(self):
        """Reset AppPaths after each test."""
        from oncutf.utils.paths import AppPaths

        AppPaths.reset()

    def test_get_user_data_dir_returns_path(self):
        """Test that get_user_data_dir returns a Path object."""
        from oncutf.utils.paths import AppPaths

        result = AppPaths.get_user_data_dir()
        assert isinstance(result, Path)
        assert "oncutf" in str(result)

    def test_get_user_data_dir_creates_directory(self, tmp_path, monkeypatch):
        """Test that get_user_data_dir creates the directory if needed."""
        from oncutf.utils.paths import AppPaths

        if os.name != "nt":
            # On Unix, use XDG_DATA_HOME
            monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
            AppPaths.reset()
            result = AppPaths.get_user_data_dir()
            assert result.exists()
            assert result.is_dir()

    def test_get_config_path(self):
        """Test that get_config_path returns correct path."""
        from oncutf.utils.paths import AppPaths

        result = AppPaths.get_config_path()
        assert isinstance(result, Path)
        assert result.name == "config.json"
        assert "oncutf" in str(result)

    def test_get_database_path(self):
        """Test that get_database_path returns correct path in data/ subdir."""
        from oncutf.utils.paths import AppPaths

        result = AppPaths.get_database_path()
        assert isinstance(result, Path)
        assert result.name == "oncutf_data.db"
        assert "data" in str(result)

    def test_get_logs_dir(self):
        """Test that get_logs_dir returns correct path."""
        from oncutf.utils.paths import AppPaths

        result = AppPaths.get_logs_dir()
        assert isinstance(result, Path)
        assert result.name == "logs"

    def test_get_cache_dir(self):
        """Test that get_cache_dir returns correct path."""
        from oncutf.utils.paths import AppPaths

        result = AppPaths.get_cache_dir()
        assert isinstance(result, Path)
        assert result.name == "cache"

    def test_get_thumbnails_dir(self):
        """Test that get_thumbnails_dir returns correct path inside cache."""
        from oncutf.utils.paths import AppPaths

        result = AppPaths.get_thumbnails_dir()
        assert isinstance(result, Path)
        assert result.name == "thumbnails"
        assert "cache" in str(result)

    def test_get_bundled_tools_dir(self):
        """Test that get_bundled_tools_dir returns bin/ directory."""
        from oncutf.utils.paths import AppPaths

        result = AppPaths.get_bundled_tools_dir()
        assert isinstance(result, Path)
        assert result.name == "bin"

    def test_get_platform_tools_subdir_windows(self, monkeypatch):
        """Test platform tools subdir on Windows."""
        from oncutf.utils.paths import AppPaths

        monkeypatch.setattr(platform, "system", lambda: "Windows")
        assert AppPaths.get_platform_tools_subdir() == "windows"

    def test_get_platform_tools_subdir_macos(self, monkeypatch):
        """Test platform tools subdir on macOS."""
        from oncutf.utils.paths import AppPaths

        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        assert AppPaths.get_platform_tools_subdir() == "macos"

    def test_get_platform_tools_subdir_linux(self, monkeypatch):
        """Test platform tools subdir on Linux."""
        from oncutf.utils.paths import AppPaths

        monkeypatch.setattr(platform, "system", lambda: "Linux")
        assert AppPaths.get_platform_tools_subdir() == "linux"

    def test_reset_clears_cache(self, tmp_path, monkeypatch):
        """Test that reset() clears the cached path."""
        from oncutf.utils.paths import AppPaths

        if os.name == "nt":
            # Windows: test LOCALAPPDATA
            monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "first"))
            AppPaths.reset()
            path1 = AppPaths.get_user_data_dir()

            monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "second"))
            AppPaths.reset()
            path2 = AppPaths.get_user_data_dir()

            assert path1 != path2
        elif platform.system() == "Darwin":
            # macOS: test that reset actually clears the cache by checking internal state
            AppPaths.reset()
            assert AppPaths._user_data_dir is None
            path1 = AppPaths.get_user_data_dir()
            assert AppPaths._user_data_dir is not None
            AppPaths.reset()
            assert AppPaths._user_data_dir is None
        else:
            # Linux: test XDG_DATA_HOME
            monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "first"))
            AppPaths.reset()
            path1 = AppPaths.get_user_data_dir()

            monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "second"))
            AppPaths.reset()
            path2 = AppPaths.get_user_data_dir()

            assert path1 != path2


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def setup_method(self):
        """Reset AppPaths before each test."""
        from oncutf.utils.paths import AppPaths

        AppPaths.reset()

    def teardown_method(self):
        """Reset AppPaths after each test."""
        from oncutf.utils.paths import AppPaths

        AppPaths.reset()

    def test_get_user_data_dir_function(self):
        """Test module-level get_user_data_dir function."""
        from oncutf.utils.paths import get_user_data_dir

        result = get_user_data_dir()
        assert isinstance(result, Path)
        assert "oncutf" in str(result)

    def test_get_config_path_function(self):
        """Test module-level get_config_path function."""
        from oncutf.utils.paths import get_config_path

        result = get_config_path()
        assert result.name == "config.json"

    def test_get_database_path_function(self):
        """Test module-level get_database_path function."""
        from oncutf.utils.paths import get_database_path

        result = get_database_path()
        assert result.name == "oncutf_data.db"

    def test_get_logs_dir_function(self):
        """Test module-level get_logs_dir function."""
        from oncutf.utils.paths import get_logs_dir

        result = get_logs_dir()
        assert result.name == "logs"
