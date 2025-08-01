"""
Module: json_config_manager.py

Author: Michael Economou
Date: 2025-06-10

json_config_manager.py
A comprehensive JSON-based configuration manager for any application.
Handles JSON serialization, deserialization, and management with support for
multiple configuration categories, automatic backups, and thread-safe operations.
"""

import json
import os
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from config import APP_VERSION
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

T = TypeVar("T")


class ConfigCategory[T]:
    """Base class for configuration categories with type safety and defaults."""

    def __init__(self, name: str, defaults: dict[str, Any]):
        self.name = name
        self.defaults = defaults
        self._data = defaults.copy()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback to default."""
        return self._data.get(key, default or self.defaults.get(key))

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._data[key] = value

    def update(self, data: dict[str, Any]) -> None:
        """Update multiple configuration values at once."""
        self._data.update(data)

    def reset(self) -> None:
        """Reset all values to defaults."""
        self._data = self.defaults.copy()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self._data.copy()

    def from_dict(self, data: dict[str, Any]) -> None:
        """Load from dictionary, applying defaults for missing keys."""
        self._data = self.defaults.copy()
        self._data.update(data)


class WindowConfig(ConfigCategory):
    """Window-specific configuration category for GUI applications."""

    def __init__(self):
        defaults = {
            "geometry": None,  # No default geometry - will trigger smart sizing
            "window_state": "normal",
            "splitter_states": {"horizontal": [250, 674, 250], "vertical": [500, 300]},
            # Dictionary-based column configuration (safer than arrays)
            "file_table_column_widths": {},  # Individual column widths by key
            "file_table_columns": {},  # Column visibility by key
            "metadata_tree_column_widths": {},  # Metadata tree column widths by key
            "metadata_tree_columns": {},  # Metadata tree column visibility by key
            "last_folder": "",
            "recursive_mode": False,
            "sort_column": 1,
            "sort_order": 0,
        }
        super().__init__("window", defaults)


class FileHashConfig(ConfigCategory):
    """File hash tracking configuration category."""

    def __init__(self):
        defaults = {
            "enabled": True,
            "algorithm": "CRC32",
            "cache_size_limit": 10000,
            "auto_cleanup_days": 30,
            "hashes": {},
        }
        super().__init__("file_hashes", defaults)

    def add_file_hash(self, filepath: str, hash_value: str, file_size: int) -> None:
        """Add or update file hash entry."""
        hashes = self.get("hashes", {})
        hashes[filepath] = {
            "hash": hash_value,
            "timestamp": datetime.now().isoformat(),
            "size": file_size,
        }
        self.set("hashes", hashes)

    def get_file_hash(self, filepath: str) -> dict[str, Any] | None:
        """Get file hash entry if exists."""
        hashes = self.get("hashes", {})
        return hashes.get(filepath)


class AppConfig(ConfigCategory):
    """General application configuration category."""

    def __init__(self):
        defaults = {
            "theme": "dark",
            "language": "en",
            "auto_save_config": True,
            "recent_folders": [],
        }
        super().__init__("app", defaults)

    def add_recent_folder(self, folder_path: str, max_recent: int = 10) -> None:
        """Add folder to recent folders list."""
        recent = self.get("recent_folders", [])

        if folder_path in recent:
            recent.remove(folder_path)

        recent.insert(0, folder_path)

        if len(recent) > max_recent:
            recent = recent[:max_recent]

        self.set("recent_folders", recent)


class JSONConfigManager:
    """Comprehensive JSON-based configuration manager."""

    def __init__(self, app_name: str = "app", config_dir: str | None = None):
        self.app_name = app_name
        self.config_dir = Path(config_dir or self._get_default_config_dir())
        self.config_file = self.config_dir / "config.json"
        self.backup_file = self.config_dir / "config.json.bak"

        self._lock = threading.RLock()
        self._categories: dict[str, ConfigCategory] = {}

        self.config_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"[JSONConfigManager] Initialized for '{app_name}' with dir: {self.config_dir}",
            extra={"dev_only": True},
        )

    def _get_default_config_dir(self) -> str:
        """Get default configuration directory based on OS."""
        if os.name == "nt":
            base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
            return os.path.join(base_dir, self.app_name)
        else:
            base_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
            return os.path.join(base_dir, self.app_name)

    def register_category(self, category: ConfigCategory) -> None:
        """Register a configuration category."""
        with self._lock:
            self._categories[category.name] = category

    def get_category(
        self, category_name: str, create_if_not_exists: bool = False
    ) -> ConfigCategory | None:
        """Get configuration category by name."""
        category = self._categories.get(category_name)
        if not category and create_if_not_exists:
            # Dynamically create a generic category if it doesn't exist
            logger.debug(f"Category '{category_name}' not found, creating it dynamically.")
            new_category = ConfigCategory(category_name, {})
            self.register_category(new_category)
            return new_category
        return category

    def list_categories(self) -> list[str]:
        """Get list of registered category names."""
        return list(self._categories.keys())

    def load(self) -> bool:
        """Load configuration from JSON file."""
        with self._lock:
            try:
                # Debug: Reset config if requested
                from config import DEBUG_RESET_CONFIG

                if DEBUG_RESET_CONFIG:
                    if self.config_file.exists():
                        logger.info(
                            f"[DEBUG] Deleting config file for fresh start: {self.config_file}"
                        )
                        try:
                            self.config_file.unlink()
                            # Also remove backup if it exists
                            if self.backup_file.exists():
                                self.backup_file.unlink()
                            logger.info("[DEBUG] Config files deleted successfully")
                        except Exception as e:
                            logger.error(f"[DEBUG] Failed to delete config file: {e}")

                if not self.config_file.exists():
                    logger.info(
                        "[JSONConfigManager] No config file found, using defaults",
                        extra={"dev_only": True},
                    )
                    return True

                with open(self.config_file, encoding="utf-8") as f:
                    data = json.load(f)

                for category_name, category in self._categories.items():
                    if category_name in data:
                        category.from_dict(data[category_name])

                logger.info(
                    "[JSONConfigManager] Configuration loaded successfully",
                    extra={"dev_only": True},
                )
                return True

            except Exception as e:
                logger.error(f"[JSONConfigManager] Failed to load configuration: {e}")
                return False

    def save(self, create_backup: bool = True) -> bool:
        """Save configuration to JSON file."""
        with self._lock:
            try:
                if create_backup and self.config_file.exists():
                    shutil.copy2(self.config_file, self.backup_file)

                data = {}
                for category_name, category in self._categories.items():
                    data[category_name] = category.to_dict()

                data["_metadata"] = {
                    "last_saved": datetime.now().isoformat(),
                    "version": f"v{APP_VERSION}",
                    "app_name": self.app_name,
                }

                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                logger.debug("[JSONConfigManager] Configuration saved successfully")
                return True

            except Exception as e:
                logger.error(f"[JSONConfigManager] Failed to save configuration: {e}")
                return False

    def get_config_info(self) -> dict[str, Any]:
        """Get information about configuration file and categories."""
        info = {
            "config_file": str(self.config_file),
            "backup_file": str(self.backup_file),
            "file_exists": self.config_file.exists(),
            "backup_exists": self.backup_file.exists(),
            "app_name": self.app_name,
            "categories": {name: len(cat.to_dict()) for name, cat in self._categories.items()},
        }

        if self.config_file.exists():
            stat = self.config_file.stat()
            info["file_size"] = stat.st_size
            info["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

        return info


def create_app_config_manager(app_name: str = "oncutf") -> JSONConfigManager:
    """Create a JSONConfigManager with default application categories."""
    manager = JSONConfigManager(app_name=app_name)

    manager.register_category(WindowConfig())
    manager.register_category(FileHashConfig())
    manager.register_category(AppConfig())

    manager.load()

    return manager


_global_manager: JSONConfigManager | None = None


def get_app_config_manager() -> JSONConfigManager:
    """Get the global application configuration manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = create_app_config_manager()
    return _global_manager


def load_config() -> dict:
    """Load configuration from JSON file and return as dictionary."""
    try:
        config_manager = get_app_config_manager()
        if not config_manager.config_file.exists():
            return {}

        with open(config_manager.config_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load config: {e}")
        return {}


def save_config(config_data: dict) -> bool:
    """Save configuration dictionary to JSON file."""
    try:
        config_manager = get_app_config_manager()

        # Create backup if file exists
        if config_manager.config_file.exists():
            shutil.copy2(config_manager.config_file, config_manager.backup_file)

        # Save new config
        with open(config_manager.config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Configuration saved to {config_manager.config_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False
