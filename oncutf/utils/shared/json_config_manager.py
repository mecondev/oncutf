"""Module: json_config_manager.py

Author: Michael Economou
Date: 2025-06-10

json_config_manager.py
A comprehensive JSON-based configuration manager for any application.
Handles JSON serialization, deserialization, and management with support for
multiple configuration categories, automatic backups, and thread-safe operations.
"""

import json
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from oncutf.config import APP_VERSION
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

T = TypeVar("T")


class ConfigCategory[T]:
    """Base class for configuration categories with type safety and defaults."""

    def __init__(self, name: str, defaults: dict[str, Any]):
        """Initialize configuration category with name and default values."""
        self.name = name
        self.defaults = defaults
        self._data = defaults.copy()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback to default."""
        return self._data.get(key, default if default is not None else self.defaults.get(key))

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


class WindowConfig(ConfigCategory[Any]):
    """Window-specific configuration category for GUI applications."""

    def __init__(self) -> None:
        """Initialize window configuration with geometry, splitters, columns, and sort settings."""
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
            # NOTE: Sort column restoration feature tracked in TODO.md
            # Default to filename column (2) instead of color (1)
            "sort_column": 2,
            "sort_order": 0,
        }
        super().__init__("window", defaults)


class FileHashConfig(ConfigCategory[Any]):
    """File hash tracking configuration category."""

    def __init__(self) -> None:
        """Initialize file hash configuration with algorithm, cache, and cleanup settings."""
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


class AppConfig(ConfigCategory[Any]):
    """General application configuration category."""

    def __init__(self) -> None:
        """Initialize application configuration with theme, language, and recent folders."""
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


class DialogsConfig(ConfigCategory[Any]):
    """Configuration for dialog windows (geometry, column widths, etc.)."""

    def __init__(self) -> None:
        """Initialize empty dialogs configuration."""
        defaults: dict[str, Any] = {}
        super().__init__("dialogs", defaults)


class JSONConfigManager:
    """Comprehensive JSON-based configuration manager with auto-save and cache."""

    def __init__(self, app_name: str = "app", config_dir: str | None = None):
        """Initialize configuration manager with app name and config directory."""
        self.app_name = app_name
        self.config_dir = Path(config_dir or self._get_default_config_dir())
        self.config_file = self.config_dir / "config.json"
        self.backup_file = self.config_dir / "config.json.bak"

        self._lock = threading.RLock()
        self._categories: dict[str, ConfigCategory[Any]] = {}

        # Auto-save with dirty flag (reduces disk I/O)
        self._dirty = False
        self._auto_save_timer_id: str | None = None

        # In-memory cache for frequently accessed settings
        self._cache: dict[str, Any] = {}
        self._cache_enabled = False  # Will be set from config after import

        self.config_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "[JSONConfigManager] Initialized for '%s' with dir: %s",
            app_name,
            self.config_dir,
            extra={"dev_only": True},
        )

    def _get_default_config_dir(self) -> str:
        """Get default configuration directory using centralized AppPaths."""
        from oncutf.utils.paths import AppPaths

        return str(AppPaths.get_user_data_dir())

    def register_category(self, category: ConfigCategory[Any]) -> None:
        """Register a configuration category."""
        with self._lock:
            self._categories[category.name] = category

    def get_category(
        self, category_name: str, create_if_not_exists: bool = False
    ) -> ConfigCategory[Any] | None:
        """Get configuration category by name."""
        category = self._categories.get(category_name)
        if not category and create_if_not_exists:
            # Dynamically create a generic category if it doesn't exist
            logger.debug("Category '%s' not found, creating it dynamically.", category_name)
            new_category: ConfigCategory[Any] = ConfigCategory(category_name, {})
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
                from oncutf.config import DEBUG_RESET_CONFIG

                if DEBUG_RESET_CONFIG:
                    if self.config_file.exists():
                        logger.info(
                            "[DEBUG] Deleting config file for fresh start: %s",
                            self.config_file,
                        )
                        try:
                            self.config_file.unlink()
                            # Also remove backup if it exists
                            if self.backup_file.exists():
                                self.backup_file.unlink()
                            logger.info("[DEBUG] Config files deleted successfully")
                        except Exception as e:
                            logger.error("[DEBUG] Failed to delete config file: %s", e)

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
                logger.error("[JSONConfigManager] Failed to load configuration: %s", e)
                return False

    def save(self, create_backup: bool = True) -> bool:
        """Save configuration to JSON file."""
        with self._lock:
            try:
                # Flush cache before saving
                if hasattr(self, "_cache_enabled") and self._cache_enabled:
                    self._flush_cache()

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

                # Clear dirty flag after successful save
                self._dirty = False
                logger.debug("[JSONConfigManager] Configuration saved successfully")
                return True

            except Exception as e:
                logger.error("[JSONConfigManager] Failed to save configuration: %s", e)
                return False

    def _schedule_auto_save(self) -> None:
        """Schedule auto-save using timer_manager (debounced)."""
        try:
            from oncutf.config import CONFIG_AUTO_SAVE_DELAY, CONFIG_AUTO_SAVE_ENABLED
            from oncutf.utils.shared.timer_manager import (
                TimerPriority,
                TimerType,
                get_timer_manager,
            )

            if not CONFIG_AUTO_SAVE_ENABLED:
                return

            # Cancel previous timer if exists
            if self._auto_save_timer_id:
                timer_mgr = get_timer_manager()
                timer_mgr.cancel(self._auto_save_timer_id)

            # Schedule new auto-save
            timer_mgr = get_timer_manager()
            self._auto_save_timer_id = timer_mgr.schedule(
                callback=self._auto_save,
                delay=CONFIG_AUTO_SAVE_DELAY * 1000,  # Convert seconds to milliseconds
                priority=TimerPriority.BACKGROUND,
                timer_type=TimerType.GENERIC,
                timer_id=f"config_auto_save_{id(self)}",
                consolidate=True,
            )
            logger.debug(
                "[JSONConfigManager] Auto-save scheduled in %ss",
                CONFIG_AUTO_SAVE_DELAY,
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.warning("[JSONConfigManager] Failed to schedule auto-save: %s", e)

    def _auto_save(self) -> None:
        """Auto-save if dirty (called by timer)."""
        if self._dirty:
            logger.info("[JSONConfigManager] Auto-save triggered (timer)")
            self.save()

    def save_immediate(self, force: bool = True) -> bool:
        """Force immediate save (used on app/dialog close).

        Args:
            force: If True, always save. If False, only save if dirty.

        Returns:
            True if save successful, False otherwise

        """
        with self._lock:
            # Cancel pending auto-save timer
            if self._auto_save_timer_id:
                try:
                    from oncutf.utils.shared.timer_manager import get_timer_manager

                    timer_mgr = get_timer_manager()
                    timer_mgr.cancel(self._auto_save_timer_id)
                    self._auto_save_timer_id = None
                except Exception as e:
                    logger.warning("[JSONConfigManager] Failed to cancel timer: %s", e)

            # Save if dirty or forced
            if force or self._dirty:
                logger.info("[JSONConfigManager] Immediate save requested")
                return self.save()

            logger.debug("[JSONConfigManager] Immediate save skipped (not dirty)")
            return True

    def mark_dirty(self) -> None:
        """Mark config as dirty and schedule auto-save."""
        self._dirty = True
        self._schedule_auto_save()

    # =====================================
    # CACHE METHODS
    # =====================================

    def get_cached(self, category_name: str, key: str, default: Any = None) -> Any:
        """Get value from cache, fallback to category.

        Args:
            category_name: Category name
            key: Setting key
            default: Default value if not found

        Returns:
            Cached value or category value or default

        """
        if not self._cache_enabled:
            category = self.get_category(category_name)
            return category.get(key, default) if category else default

        cache_key = f"{category_name}.{key}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Not in cache, get from category and cache it
        category = self.get_category(category_name)
        value = category.get(key, default) if category else default
        self._cache[cache_key] = value
        return value

    def set_cached(self, category_name: str, key: str, value: Any) -> None:
        """Set value in cache and mark dirty.

        Args:
            category_name: Category name
            key: Setting key
            value: Value to set

        """
        cache_key = f"{category_name}.{key}"
        self._cache[cache_key] = value
        self.mark_dirty()

    def _flush_cache(self) -> None:
        """Flush cache to config categories."""
        if not self._cache:
            return

        try:
            from oncutf.config import CONFIG_CACHE_FLUSH_ON_SAVE

            if not CONFIG_CACHE_FLUSH_ON_SAVE:
                return
        except ImportError:
            pass

        for cache_key, value in self._cache.items():
            try:
                category_name, key = cache_key.split(".", 1)
                category = self.get_category(category_name, create_if_not_exists=True)
                if category:
                    category.set(key, value)
            except Exception as e:
                logger.warning(
                    "[JSONConfigManager] Failed to flush cache key '%s': %s",
                    cache_key,
                    e,
                )

        logger.debug("[JSONConfigManager] Flushed %d cache entries", len(self._cache))
        self._cache.clear()

    def clear_cache(self) -> None:
        """Clear cache without flushing to disk."""
        self._cache.clear()
        logger.debug("[JSONConfigManager] Cache cleared")

    def enable_cache(self, enabled: bool = True) -> None:
        """Enable or disable cache layer."""
        self._cache_enabled = enabled
        if not enabled:
            self.clear_cache()
        logger.debug("[JSONConfigManager] Cache %s", "enabled" if enabled else "disabled")

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
    manager.register_category(DialogsConfig())

    # NOTE: Do NOT load here! save_immediate() will reload before saving.
    # This ensures defaults are used if no file exists, and file is
    # merged-in only at save time, not at creation time.

    # Enable cache if configured
    try:
        from oncutf.config import CONFIG_CACHE_ENABLED

        manager.enable_cache(CONFIG_CACHE_ENABLED)
    except ImportError:
        manager.enable_cache(True)  # Default to enabled

    return manager


_global_manager: JSONConfigManager | None = None


def get_app_config_manager() -> JSONConfigManager:
    """Get the global application configuration manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = create_app_config_manager()
    return _global_manager


def load_config() -> dict[str, Any]:
    """Load configuration from JSON file and return as dictionary."""
    try:
        config_manager = get_app_config_manager()
        if not config_manager.config_file.exists():
            return {}

        with open(config_manager.config_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load config: %s", e)
        return {}


def save_config(config_data: dict[str, Any]) -> bool:
    """Save configuration dictionary to JSON file."""
    try:
        config_manager = get_app_config_manager()

        # Create backup if file exists
        if config_manager.config_file.exists():
            shutil.copy2(config_manager.config_file, config_manager.backup_file)

        # Save new config
        with open(config_manager.config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        logger.debug("Configuration saved to %s", config_manager.config_file)
        return True

    except Exception as e:
        logger.error("Failed to save config: %s", e)
        return False
