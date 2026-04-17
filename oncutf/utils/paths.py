r"""Module: paths.py.

Author: Michael Economou
Date: 2026-01-01

Centralized path management for oncutf application.

Follows the same three-directory XDG/platform convention as the C++ sibling
project (oncut-lut-engine).  Each platform type has a canonical home for each
class of data:

  Linux (XDG Base Directory Specification):
    Config  : $XDG_CONFIG_HOME/oncut/oncutf/   (default: ~/.config/oncut/oncutf/)
    Data    : $XDG_DATA_HOME/oncut/oncutf/     (default: ~/.local/share/oncut/oncutf/)
    Cache   : $XDG_CACHE_HOME/oncut/oncutf/    (default: ~/.cache/oncut/oncutf/)

  macOS:
    Config  : ~/Library/Application Support/oncut/oncutf/
    Data    : ~/Library/Application Support/oncut/oncutf/
    Cache   : ~/Library/Caches/oncut/oncutf/

  Windows:
    Config  : %APPDATA%\\oncut\\oncutf\\           (roaming -- synced)
    Data    : %LOCALAPPDATA%\\oncut\\oncutf\\       (local)
    Cache   : %LOCALAPPDATA%\\oncut\\oncutf\\cache\\ (local)

Usage:
    from oncutf.utils.paths import AppPaths

    config_path = AppPaths.get_config_path()
    db_path = AppPaths.get_database_path()
    logs_dir = AppPaths.get_logs_dir()
    cache_dir = AppPaths.get_cache_dir()
"""

import os
import platform
import shutil
import sys
from pathlib import Path

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Organization and application name for path construction
ORG_NAME = "oncut"
APP_NAME = "oncutf"


class AppPaths:
    """Centralized path management for the application.

    Three separate root directories are used, matching XDG conventions:

      <config_dir>/
      └── config.json              # User preferences (roaming on Windows)

      <data_dir>/
      ├── data/
      │   └── oncutf_data.db       # Main SQLite database
      ├── logs/                    # Log files
      └── tools/                   # User-installed tools (optional)

      <cache_dir>/
      ├── thumbnails/              # Thumbnail cache
      └── disk/                    # DiskCache (advanced_cache_manager)
    """

    _config_dir: Path | None = None
    _user_data_dir: Path | None = None
    _cache_dir: Path | None = None
    _initialized: bool = False

    # ------------------------------------------------------------------
    # Platform resolution helpers
    # ------------------------------------------------------------------

    @classmethod
    def _get_platform_config_dir(cls) -> Path:
        system = platform.system()
        if system == "Windows":
            base = os.environ.get("APPDATA")
            if not base:
                base = str(Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Roaming")
            return Path(base) / ORG_NAME / APP_NAME
        if system == "Darwin":
            return Path.home() / "Library" / "Application Support" / ORG_NAME / APP_NAME
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return Path(xdg) / ORG_NAME / APP_NAME
        return Path.home() / ".config" / ORG_NAME / APP_NAME

    @classmethod
    def _get_platform_data_dir(cls) -> Path:
        system = platform.system()
        if system == "Windows":
            base = os.environ.get("LOCALAPPDATA")
            if not base:
                base = str(Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Local")
            return Path(base) / ORG_NAME / APP_NAME
        if system == "Darwin":
            return Path.home() / "Library" / "Application Support" / ORG_NAME / APP_NAME
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            return Path(xdg) / ORG_NAME / APP_NAME
        return Path.home() / ".local" / "share" / ORG_NAME / APP_NAME

    @classmethod
    def _get_platform_cache_dir(cls) -> Path:
        system = platform.system()
        if system == "Windows":
            base = os.environ.get("LOCALAPPDATA")
            if not base:
                base = str(Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Local")
            return Path(base) / ORG_NAME / APP_NAME / "cache"
        if system == "Darwin":
            return Path.home() / "Library" / "Caches" / ORG_NAME / APP_NAME
        xdg = os.environ.get("XDG_CACHE_HOME")
        if xdg:
            return Path(xdg) / ORG_NAME / APP_NAME
        return Path.home() / ".cache" / ORG_NAME / APP_NAME

    # ------------------------------------------------------------------
    # Legacy paths (used only for one-time migration)
    # ------------------------------------------------------------------

    @classmethod
    def _get_legacy_data_dir(cls) -> Path:
        """Legacy flat path (pre org-prefix) for one-time migration."""
        system = platform.system()
        if system == "Windows":
            base = os.environ.get("LOCALAPPDATA")
            if not base:
                base = str(Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Local")
            return Path(base) / APP_NAME
        if system == "Darwin":
            return Path.home() / "Library" / "Application Support" / APP_NAME
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            return Path(xdg) / APP_NAME
        return Path.home() / ".local" / "share" / APP_NAME

    @classmethod
    def _get_legacy_all_in_data_dir(cls) -> Path:
        """Pre-XDG-split path where config and cache lived inside data dir."""
        return cls._get_platform_data_dir()

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @classmethod
    def get_config_dir(cls) -> Path:
        """Return the config root directory, creating it if necessary."""
        if cls._config_dir is None:
            cls._config_dir = cls._get_platform_config_dir()

            # One-time migration: config.json was previously inside the data dir
            legacy_cfg = cls._get_legacy_all_in_data_dir() / "config.json"
            new_cfg = cls._config_dir / "config.json"
            if legacy_cfg.exists() and not new_cfg.exists():
                cls._config_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(legacy_cfg), str(new_cfg))
                legacy_cfg.unlink()
                logger.info(
                    "[AppPaths] Migrated config: %s -> %s", legacy_cfg, new_cfg
                )

        cls._config_dir.mkdir(parents=True, exist_ok=True)
        return cls._config_dir

    @classmethod
    def get_user_data_dir(cls) -> Path:
        """Return the data root directory, creating it if necessary."""
        if cls._user_data_dir is None:
            cls._user_data_dir = cls._get_platform_data_dir()

            # One-time migration: legacy flat path (pre org-prefix) -> org-prefixed
            legacy_dir = cls._get_legacy_data_dir()
            if (
                legacy_dir != cls._user_data_dir
                and legacy_dir.exists()
                and not cls._user_data_dir.exists()
            ):
                cls._user_data_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(legacy_dir), str(cls._user_data_dir))
                logger.info(
                    "[AppPaths] Migrated data directory: %s -> %s",
                    legacy_dir,
                    cls._user_data_dir,
                )

        cls._user_data_dir.mkdir(parents=True, exist_ok=True)

        if not cls._initialized:
            logger.info("[AppPaths] Data directory  : %s", cls._user_data_dir)
            logger.info("[AppPaths] Config directory: %s", cls._get_platform_config_dir())
            logger.info("[AppPaths] Cache directory : %s", cls._get_platform_cache_dir())
            cls._initialized = True

        return cls._user_data_dir

    @classmethod
    def get_config_path(cls) -> Path:
        """Return path to config.json."""
        return cls.get_config_dir() / "config.json"

    @classmethod
    def get_database_path(cls) -> Path:
        """Return path to main SQLite database (inside data dir)."""
        data_dir = cls.get_user_data_dir() / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "oncutf_data.db"

    @classmethod
    def get_logs_dir(cls) -> Path:
        """Return path to logs directory (inside data dir)."""
        logs_dir = cls.get_user_data_dir() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir

    @classmethod
    def get_cache_dir(cls) -> Path:
        """Return the cache root directory, creating it if necessary.

        On Linux this is $XDG_CACHE_HOME/oncut/oncutf/ (~/.cache/oncut/oncutf/).
        Previously the cache lived inside the data dir; a one-time migration
        moves it on first access.
        """
        if cls._cache_dir is None:
            cls._cache_dir = cls._get_platform_cache_dir()

            # One-time migration: cache/ was previously a sub-dir of the data dir
            legacy_cache = cls._get_legacy_all_in_data_dir() / "cache"
            if legacy_cache.exists() and not cls._cache_dir.exists():
                cls._cache_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(legacy_cache), str(cls._cache_dir))
                logger.info(
                    "[AppPaths] Migrated cache: %s -> %s", legacy_cache, cls._cache_dir
                )

        cls._cache_dir.mkdir(parents=True, exist_ok=True)
        return cls._cache_dir

    @classmethod
    def get_thumbnails_dir(cls) -> Path:
        """Return path to thumbnails directory (inside cache dir)."""
        thumbnails_dir = cls.get_cache_dir() / "thumbnails"
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        return thumbnails_dir

    @classmethod
    def get_user_tools_dir(cls) -> Path:
        """Return path to user-installed tools directory (inside data dir)."""
        tools_dir = cls.get_user_data_dir() / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        return tools_dir

    @classmethod
    def get_bundled_tools_dir(cls) -> Path:
        """Return path to bundled tools directory.

        For PyInstaller frozen executables, returns the _MEIPASS directory.
        For development, returns the project's bin/ directory.
        """
        if getattr(sys, "frozen", False):
            base_path = Path(getattr(sys, "_MEIPASS", "."))
        else:
            # oncutf/utils/paths.py -> oncutf/utils/ -> oncutf/ -> project root
            base_path = Path(__file__).parent.parent.parent
        return base_path / "bin"

    @classmethod
    def get_platform_tools_subdir(cls) -> str:
        """Return platform-specific tools subdirectory name."""
        system = platform.system()
        if system == "Windows":
            return "windows"
        if system == "Darwin":
            return "macos"
        return "linux"

    @classmethod
    def reset(cls) -> None:
        """Reset all cached paths (used in tests)."""
        cls._config_dir = None
        cls._user_data_dir = None
        cls._cache_dir = None
        cls._initialized = False


# ---------------------------------------------------------------------------
# Convenience functions for backward compatibility
# ---------------------------------------------------------------------------

def get_user_data_dir() -> Path:
    """Get user data directory."""
    return AppPaths.get_user_data_dir()


def get_config_path() -> Path:
    """Get config.json path."""
    return AppPaths.get_config_path()


def get_database_path() -> Path:
    """Get database path."""
    return AppPaths.get_database_path()


def get_logs_dir() -> Path:
    """Get logs directory."""
    return AppPaths.get_logs_dir()
