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

    # -- config -----------------------------------------------------------

    def test_get_config_dir_linux(self, tmp_path, monkeypatch):
        """On Linux, config dir uses XDG_CONFIG_HOME."""
        if platform.system() != "Linux":
            return
        from oncutf.utils.paths import AppPaths

        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        AppPaths.reset()
        result = AppPaths.get_config_dir()
        assert str(tmp_path / "cfg" / "oncut" / "oncutf") == str(result)

    def test_get_config_path(self):
        """Test that get_config_path returns config.json in the config dir."""
        from oncutf.utils.paths import AppPaths

        result = AppPaths.get_config_path()
        assert isinstance(result, Path)
        assert result.name == "config.json"
        assert "oncutf" in str(result)
        # config must NOT be inside the data dir on Linux
        if platform.system() == "Linux":
            assert ".local/share" not in str(result)

    # -- data -------------------------------------------------------------

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

    # -- cache ------------------------------------------------------------

    def test_get_cache_dir_linux(self, tmp_path, monkeypatch):
        """On Linux, cache dir uses XDG_CACHE_HOME (separate from data)."""
        if platform.system() != "Linux":
            return
        from oncutf.utils.paths import AppPaths

        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg_cache"))
        AppPaths.reset()
        result = AppPaths.get_cache_dir()
        assert str(tmp_path / "xdg_cache" / "oncut" / "oncutf") == str(result)
        # Must not be inside the data dir
        assert ".local/share" not in str(result)

    def test_get_cache_dir_is_separate_from_data(self):
        """Cache dir must be a different root from data dir on Linux/macOS."""
        if platform.system() not in ("Linux", "Darwin"):
            return
        from oncutf.utils.paths import AppPaths

        cache = AppPaths.get_cache_dir()
        data = AppPaths.get_user_data_dir()
        assert not str(cache).startswith(str(data))

    def test_get_cache_dir(self):
        """Test that get_cache_dir returns a path containing oncutf."""
        from oncutf.utils.paths import AppPaths

        result = AppPaths.get_cache_dir()
        assert isinstance(result, Path)
        assert "oncutf" in str(result)

    def test_get_thumbnails_dir(self):
        """Test that get_thumbnails_dir returns correct path inside cache dir."""
        from oncutf.utils.paths import AppPaths

        result = AppPaths.get_thumbnails_dir()
        assert isinstance(result, Path)
        assert result.name == "thumbnails"
        # thumbnails must be inside the cache dir
        cache = AppPaths.get_cache_dir()
        assert str(result).startswith(str(cache))

    # -- tools ------------------------------------------------------------

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

    # -- reset ------------------------------------------------------------

    def test_reset_clears_all_cached_dirs(self, tmp_path, monkeypatch):
        """Test that reset() clears all three cached paths."""
        from oncutf.utils.paths import AppPaths

        if platform.system() == "Darwin":
            # macOS: verify internal state cleared
            AppPaths.reset()
            assert AppPaths._user_data_dir is None
            assert AppPaths._config_dir is None
            assert AppPaths._cache_dir is None
            AppPaths.get_user_data_dir()
            AppPaths.get_config_dir()
            AppPaths.get_cache_dir()
            AppPaths.reset()
            assert AppPaths._user_data_dir is None
            assert AppPaths._config_dir is None
            assert AppPaths._cache_dir is None
        elif os.name == "nt":
            monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "first"))
            AppPaths.reset()
            path1 = AppPaths.get_user_data_dir()
            monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "second"))
            AppPaths.reset()
            path2 = AppPaths.get_user_data_dir()
            assert path1 != path2
        else:
            monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "d1"))
            monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "c1"))
            monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "k1"))
            AppPaths.reset()
            data1 = AppPaths.get_user_data_dir()
            cfg1 = AppPaths.get_config_dir()
            cache1 = AppPaths.get_cache_dir()

            monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "d2"))
            monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "c2"))
            monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "k2"))
            AppPaths.reset()
            data2 = AppPaths.get_user_data_dir()
            cfg2 = AppPaths.get_config_dir()
            cache2 = AppPaths.get_cache_dir()

            assert data1 != data2
            assert cfg1 != cfg2
            assert cache1 != cache2


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
