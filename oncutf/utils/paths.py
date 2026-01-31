"""Module: paths.py.

Author: Michael Economou
Date: 2026-01-01

Centralized path management for oncutf application.

This module provides a unified interface for accessing all application paths:
- User data directory (config, database, logs)
- Cache directory (thumbnails, temp files)
- Bundled tools directory (for PyInstaller)

Platform-specific behavior:
- Windows: %LOCALAPPDATA%/oncutf/
- Linux: ~/.local/share/oncutf/
- macOS: ~/Library/Application Support/oncutf/

Usage:
    from oncutf.utils.paths import AppPaths

    config_path = AppPaths.get_config_path()
    db_path = AppPaths.get_database_path()
    logs_dir = AppPaths.get_logs_dir()
"""

import os
import platform
import sys
from pathlib import Path

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Application name for path construction
APP_NAME = "oncutf"


class AppPaths:
    """Centralized path management for the application.

    This class provides static methods for accessing all application paths
    in a cross-platform manner. Paths are lazily created when first accessed.

    Directory Structure:
        <user_data_dir>/
        ├── config.json          # Application configuration
        ├── logs/                # Log files
        │   └── oncutf_YYYY-MM-DD.log
        ├── data/                # Persistent data
        │   └── oncutf_data.db   # Main SQLite database
        ├── cache/               # Temporary cache
        │   └── thumbnails/      # Thumbnail cache
        └── tools/               # User-installed tools (optional)
            ├── exiftool/
            └── ffmpeg/
    """

    _user_data_dir: Path | None = None
    _initialized: bool = False

    @classmethod
    def _get_platform_data_dir(cls) -> Path:
        """Get platform-specific user data directory.

        Returns:
            Path to user data directory based on OS.

        """
        system = platform.system()

        if system == "Windows":
            # Windows: Use LOCALAPPDATA for app data
            base = os.environ.get("LOCALAPPDATA")
            if not base:
                base = Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Local"
            return Path(base) / APP_NAME

        elif system == "Darwin":
            # macOS: Use Application Support
            return Path.home() / "Library" / "Application Support" / APP_NAME

        else:
            # Linux and others: Use XDG_DATA_HOME or ~/.local/share
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if xdg_data:
                return Path(xdg_data) / APP_NAME
            return Path.home() / ".local" / "share" / APP_NAME

    @classmethod
    def get_user_data_dir(cls) -> Path:
        """Get the user data directory, creating it if necessary.

        Returns:
            Path to user data directory.

        """
        if cls._user_data_dir is None:
            cls._user_data_dir = cls._get_platform_data_dir()

        # Ensure directory exists
        cls._user_data_dir.mkdir(parents=True, exist_ok=True)

        if not cls._initialized:
            logger.info("[AppPaths] User data directory: %s", cls._user_data_dir)
            cls._initialized = True

        return cls._user_data_dir

    @classmethod
    def get_config_path(cls) -> Path:
        """Get path to config.json file.

        Returns:
            Path to configuration file.

        """
        return cls.get_user_data_dir() / "config.json"

    @classmethod
    def get_database_path(cls) -> Path:
        """Get path to main SQLite database.

        Returns:
            Path to database file in data/ subdirectory.

        """
        data_dir = cls.get_user_data_dir() / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "oncutf_data.db"

    @classmethod
    def get_logs_dir(cls) -> Path:
        """Get path to logs directory.

        Returns:
            Path to logs directory.

        """
        logs_dir = cls.get_user_data_dir() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir

    @classmethod
    def get_cache_dir(cls) -> Path:
        """Get path to cache directory (thumbnails, temp files).

        Returns:
            Path to cache directory.

        """
        cache_dir = cls.get_user_data_dir() / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @classmethod
    def get_thumbnails_dir(cls) -> Path:
        """Get path to thumbnails cache directory.

        Returns:
            Path to thumbnails directory.

        """
        thumbnails_dir = cls.get_cache_dir() / "thumbnails"
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        return thumbnails_dir

    @classmethod
    def get_user_tools_dir(cls) -> Path:
        """Get path to user-installed tools directory.

        This directory is for tools installed by the user (not bundled).

        Returns:
            Path to user tools directory.

        """
        tools_dir = cls.get_user_data_dir() / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        return tools_dir

    @classmethod
    def get_bundled_tools_dir(cls) -> Path:
        """Get path to bundled tools directory.

        For PyInstaller frozen executables, returns the _MEIPASS directory.
        For development, returns the project's bin/ directory.

        Returns:
            Path to bundled tools directory.

        """
        if getattr(sys, "frozen", False):
            # Running as compiled exe - use _MEIPASS for bundled resources
            base_path = Path(getattr(sys, "_MEIPASS", "."))
        else:
            # Running from source - go up to project root
            # oncutf/utils/paths.py -> oncutf/utils/ -> oncutf/ -> project root
            base_path = Path(__file__).parent.parent.parent

        return base_path / "bin"

    @classmethod
    def get_platform_tools_subdir(cls) -> str:
        """Get platform-specific tools subdirectory name.

        Returns:
            Subdirectory name: 'windows', 'macos', or 'linux'.

        """
        system = platform.system()
        if system == "Windows":
            return "windows"
        elif system == "Darwin":
            return "macos"
        else:
            return "linux"

    @classmethod
    def reset(cls) -> None:
        """Reset cached paths (mainly for testing).

        This clears the cached user data directory path.
        """
        cls._user_data_dir = None
        cls._initialized = False


# Convenience functions for backward compatibility
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
