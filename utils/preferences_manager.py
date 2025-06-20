"""
preferences_manager.py
Author: Michael Economou
Date: 2025-06-20

A comprehensive JSON-based preferences manager for the oncutf application.
Handles window state, SHA files, user settings, and other persistent data.

Features:
- Type-safe preference handling with defaults
- Automatic backup creation
- Thread-safe operations
- Extensible for multiple preference categories
"""

import json
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Union, TypeVar, Generic
from datetime import datetime

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

T = TypeVar('T')


class PreferenceCategory(Generic[T]):
    """Base class for preference categories with type safety and defaults."""

    def __init__(self, name: str, defaults: Dict[str, Any]):
        self.name = name
        self.defaults = defaults
        self._data = defaults.copy()

    def get(self, key: str, default: Any = None) -> Any:
        """Get preference value with fallback to default."""
        return self._data.get(key, default or self.defaults.get(key))

    def set(self, key: str, value: Any) -> None:
        """Set preference value."""
        self._data[key] = value

    def update(self, data: Dict[str, Any]) -> None:
        """Update multiple preferences at once."""
        self._data.update(data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self._data.copy()

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load from dictionary, applying defaults for missing keys."""
        self._data = self.defaults.copy()
        self._data.update(data)


class WindowPreferences(PreferenceCategory):
    """Window-specific preferences category."""

    def __init__(self):
        defaults = {
            'geometry': {'x': 100, 'y': 100, 'width': 1200, 'height': 900},
            'window_state': 'normal',  # normal, maximized, minimized
            'splitter_states': {
                'horizontal': [250, 674, 250],
                'vertical': [500, 300]
            },
            'column_widths': {
                'file_table': [23, 345, 80, 60, 130],
                'metadata_tree': [180, 500]
            },
            'last_folder': '',
            'recursive_mode': False,
            'sort_column': 1,
            'sort_order': 0  # 0 = ascending, 1 = descending
        }
        super().__init__('window', defaults)


class FileHashPreferences(PreferenceCategory):
    """File SHA/hash tracking preferences category."""

    def __init__(self):
        defaults = {
            'enabled': True,
            'algorithm': 'sha256',
            'cache_size_limit': 10000,  # max number of entries
            'auto_cleanup_days': 30,
            'hashes': {}  # filepath -> {'hash': str, 'timestamp': str, 'size': int}
        }
        super().__init__('file_hashes', defaults)

    def add_file_hash(self, filepath: str, hash_value: str, file_size: int) -> None:
        """Add or update file hash entry."""
        hashes = self.get('hashes', {})
        hashes[filepath] = {
            'hash': hash_value,
            'timestamp': datetime.now().isoformat(),
            'size': file_size
        }
        self.set('hashes', hashes)

    def get_file_hash(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Get file hash entry if exists."""
        hashes = self.get('hashes', {})
        return hashes.get(filepath)

    def cleanup_old_entries(self) -> int:
        """Remove entries older than auto_cleanup_days. Returns count removed."""
        cleanup_days = self.get('auto_cleanup_days', 30)
        if cleanup_days <= 0:
            return 0

        cutoff_date = datetime.now().timestamp() - (cleanup_days * 24 * 3600)
        hashes = self.get('hashes', {})
        original_count = len(hashes)

        # Filter out old entries
        cleaned_hashes = {
            path: data for path, data in hashes.items()
            if datetime.fromisoformat(data['timestamp']).timestamp() > cutoff_date
        }

        self.set('hashes', cleaned_hashes)
        removed_count = original_count - len(cleaned_hashes)

        if removed_count > 0:
            logger.info(f"[PreferencesManager] Cleaned up {removed_count} old hash entries")

        return removed_count


class AppPreferences(PreferenceCategory):
    """General application preferences category."""

    def __init__(self):
        defaults = {
            'theme': 'dark',
            'language': 'en',
            'auto_save_preferences': True,
            'check_for_updates': True,
            'metadata_cache_size': 1000,
            'preview_update_delay': 100,
            'large_folder_threshold': 150,
            'extended_metadata_size_limit_mb': 500,
            'recent_folders': []
        }
        super().__init__('app', defaults)

    def add_recent_folder(self, folder_path: str, max_recent: int = 10) -> None:
        """Add folder to recent folders list."""
        recent = self.get('recent_folders', [])

        # Remove if already exists
        if folder_path in recent:
            recent.remove(folder_path)

        # Add to beginning
        recent.insert(0, folder_path)

        # Limit size
        if len(recent) > max_recent:
            recent = recent[:max_recent]

        self.set('recent_folders', recent)


class PreferencesManager:
    """
    Comprehensive preferences manager for JSON-based settings.

    Features:
    - Multiple preference categories
    - Automatic backup creation
    - Thread-safe operations
    - Default value handling
    - Auto-save capability
    """

    def __init__(self, preferences_dir: Optional[str] = None):
        self.preferences_dir = Path(preferences_dir or self._get_default_preferences_dir())
        self.preferences_file = self.preferences_dir / 'preferences.json'
        self.backup_file = self.preferences_dir / 'preferences.backup.json'

        # Thread safety
        self._lock = threading.RLock()

        # Initialize preference categories
        self.window = WindowPreferences()
        self.file_hashes = FileHashPreferences()
        self.app = AppPreferences()

        # Create preferences directory
        self.preferences_dir.mkdir(parents=True, exist_ok=True)

        # Load existing preferences
        self.load()

        logger.info(f"[PreferencesManager] Initialized with preferences dir: {self.preferences_dir}")

    def _get_default_preferences_dir(self) -> str:
        """Get default preferences directory based on OS."""
        if os.name == 'nt':  # Windows
            base_dir = os.environ.get('APPDATA', os.path.expanduser('~'))
            return os.path.join(base_dir, 'oncutf')
        else:  # Linux/Unix
            base_dir = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
            return os.path.join(base_dir, 'oncutf')

    def load(self) -> bool:
        """Load preferences from JSON file. Returns True if successful."""
        with self._lock:
            try:
                if not self.preferences_file.exists():
                    logger.info("[PreferencesManager] No preferences file found, using defaults")
                    return True

                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Load each category
                if 'window' in data:
                    self.window.from_dict(data['window'])
                if 'file_hashes' in data:
                    self.file_hashes.from_dict(data['file_hashes'])
                if 'app' in data:
                    self.app.from_dict(data['app'])

                logger.info("[PreferencesManager] Preferences loaded successfully")
                return True

            except Exception as e:
                logger.error(f"[PreferencesManager] Failed to load preferences: {e}")
                self._try_restore_backup()
                return False

    def save(self, create_backup: bool = True) -> bool:
        """Save preferences to JSON file. Returns True if successful."""
        with self._lock:
            try:
                # Create backup if requested and file exists
                if create_backup and self.preferences_file.exists():
                    shutil.copy2(self.preferences_file, self.backup_file)

                # Prepare data for saving
                data = {
                    'window': self.window.to_dict(),
                    'file_hashes': self.file_hashes.to_dict(),
                    'app': self.app.to_dict(),
                    'metadata': {
                        'last_saved': datetime.now().isoformat(),
                        'version': '1.0'
                    }
                }

                # Write to temporary file first, then rename (atomic operation)
                temp_file = self.preferences_file.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # Replace original file
                temp_file.replace(self.preferences_file)

                logger.debug("[PreferencesManager] Preferences saved successfully")
                return True

            except Exception as e:
                logger.error(f"[PreferencesManager] Failed to save preferences: {e}")
                return False

    def _try_restore_backup(self) -> bool:
        """Try to restore from backup file."""
        try:
            if self.backup_file.exists():
                shutil.copy2(self.backup_file, self.preferences_file)
                logger.info("[PreferencesManager] Restored preferences from backup")
                return self.load()
        except Exception as e:
            logger.error(f"[PreferencesManager] Failed to restore backup: {e}")
        return False

    def reset_to_defaults(self) -> None:
        """Reset all preferences to default values."""
        with self._lock:
            self.window = WindowPreferences()
            self.file_hashes = FileHashPreferences()
            self.app = AppPreferences()
            logger.info("[PreferencesManager] Reset all preferences to defaults")

    def export_preferences(self, export_path: str) -> bool:
        """Export preferences to specified file."""
        try:
            export_file = Path(export_path)
            shutil.copy2(self.preferences_file, export_file)
            logger.info(f"[PreferencesManager] Exported preferences to: {export_path}")
            return True
        except Exception as e:
            logger.error(f"[PreferencesManager] Failed to export preferences: {e}")
            return False

    def import_preferences(self, import_path: str) -> bool:
        """Import preferences from specified file."""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                logger.error(f"[PreferencesManager] Import file not found: {import_path}")
                return False

            # Backup current preferences
            self.save(create_backup=True)

            # Copy imported file
            shutil.copy2(import_file, self.preferences_file)

            # Load imported preferences
            success = self.load()
            if success:
                logger.info(f"[PreferencesManager] Imported preferences from: {import_path}")
            else:
                logger.error("[PreferencesManager] Failed to load imported preferences")

            return success

        except Exception as e:
            logger.error(f"[PreferencesManager] Failed to import preferences: {e}")
            return False

    def cleanup_file_hashes(self) -> int:
        """Clean up old file hash entries. Returns count of removed entries."""
        return self.file_hashes.cleanup_old_entries()

    def get_preferences_info(self) -> Dict[str, Any]:
        """Get information about preferences file and categories."""
        info = {
            'preferences_file': str(self.preferences_file),
            'backup_file': str(self.backup_file),
            'file_exists': self.preferences_file.exists(),
            'backup_exists': self.backup_file.exists(),
            'categories': {
                'window': len(self.window.to_dict()),
                'file_hashes': len(self.file_hashes.get('hashes', {})),
                'app': len(self.app.to_dict())
            }
        }

        if self.preferences_file.exists():
            stat = self.preferences_file.stat()
            info['file_size'] = stat.st_size
            info['last_modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()

        return info


# Global instance for easy access
_preferences_manager: Optional[PreferencesManager] = None


def get_preferences_manager(preferences_dir: Optional[str] = None) -> PreferencesManager:
    """Get global preferences manager instance (singleton pattern)."""
    global _preferences_manager
    if _preferences_manager is None:
        _preferences_manager = PreferencesManager(preferences_dir)
    return _preferences_manager


def save_preferences() -> bool:
    """Convenience function to save preferences."""
    return get_preferences_manager().save()


def load_preferences() -> bool:
    """Convenience function to load preferences."""
    return get_preferences_manager().load()
