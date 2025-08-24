"""
Module: unified_column_service.py

Author: Michael Economou
Date: 2025-08-24

Unified Column Service for OnCutF Application

This module provides a centralized, simplified column management system that replaces
the complex multi-layer configuration approach with a single source of truth.

Key Features:
- Single configuration source (config.py + user overrides)
- Simplified caching with automatic invalidation
- Type-safe column operations
- Performance-optimized configuration loading
- Backward compatibility with existing APIs

Classes:
    ColumnConfig: Individual column configuration
    UnifiedColumnService: Main service class
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

from core.pyqt_imports import Qt
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ColumnAlignment(Enum):
    """Column text alignment options."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass(frozen=True)
class ColumnConfig:
    """
    Immutable column configuration.
    
    This replaces the scattered configuration dictionaries with a type-safe,
    validated configuration object.
    """
    key: str
    title: str
    default_visible: bool
    removable: bool
    width: int
    min_width: int
    alignment: ColumnAlignment
    
    @property
    def qt_alignment(self) -> Qt.AlignmentFlag:
        """Get Qt alignment constant for this column."""
        alignment_map = {
            ColumnAlignment.LEFT: Qt.AlignLeft | Qt.AlignVCenter,
            ColumnAlignment.CENTER: Qt.AlignCenter,
            ColumnAlignment.RIGHT: Qt.AlignRight | Qt.AlignVCenter,
        }
        return alignment_map[self.alignment]


class UnifiedColumnService:
    """
    Unified column management service.
    
    This service provides a single API for all column-related operations,
    replacing the complex multi-layer approach with a simple, cached service.
    """
    
    def __init__(self):
        """Initialize the service with empty cache."""
        self._config_cache: Optional[Dict[str, ColumnConfig]] = None
        self._visible_columns_cache: Optional[List[str]] = None
        self._column_mapping_cache: Optional[Dict[int, str]] = None
        self._user_settings_cache: Optional[Dict[str, Any]] = None
    
    def _get_main_window(self):
        """Get main window using multiple fallback methods."""
        # Method 1: Try application context
        try:
            from core.application_context import get_app_context
            app_context = get_app_context()
            main_window = getattr(app_context, 'main_window', None)
            if main_window:
                return main_window
        except (ImportError, AttributeError, RuntimeError):
            pass
        
        # Method 2: Try to find via QApplication
        try:
            from core.pyqt_imports import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.allWidgets():
                    if widget.__class__.__name__ == 'MainWindow':
                        return widget
        except (ImportError, AttributeError, RuntimeError):
            pass
        
        return None
        
    def get_column_config(self, column_key: str) -> Optional[ColumnConfig]:
        """
        Get configuration for a specific column.
        
        Args:
            column_key: The column identifier
            
        Returns:
            ColumnConfig object or None if column doesn't exist
        """
        if self._config_cache is None:
            self._load_configuration()
            
        return self._config_cache.get(column_key)
    
    def get_all_columns(self) -> Dict[str, ColumnConfig]:
        """Get all column configurations."""
        if self._config_cache is None:
            self._load_configuration()
            
        return self._config_cache.copy()
    
    def get_visible_columns(self) -> List[str]:
        """Get list of visible column keys in display order."""
        if self._visible_columns_cache is None:
            self._compute_visible_columns()
            
        return self._visible_columns_cache.copy()
    
    def get_column_mapping(self) -> Dict[int, str]:
        """
        Get column index to key mapping.
        
        Returns:
            Dictionary mapping column indices to column keys.
            Note: Index 0 is reserved for status column.
        """
        if self._column_mapping_cache is None:
            self._compute_column_mapping()
            
        return self._column_mapping_cache.copy()
    
    def get_column_width(self, column_key: str) -> int:
        """
        Get effective width for a column (user override or default).
        
        Args:
            column_key: The column identifier
            
        Returns:
            Column width in pixels
        """
        # Check user settings first
        user_settings = self._get_user_settings()
        column_widths = user_settings.get("file_table_column_widths", {})
        
        if column_key in column_widths:
            return column_widths[column_key]
            
        # Fall back to default configuration
        config = self.get_column_config(column_key)
        return config.width if config else 100
    
    def set_column_width(self, column_key: str, width: int) -> None:
        """
        Set user override for column width.
        
        Args:
            column_key: The column identifier
            width: Width in pixels
        """
        # This would integrate with the window config manager
        # For now, we'll implement a simple approach
        user_settings = self._get_user_settings()
        if "file_table_column_widths" not in user_settings:
            user_settings["file_table_column_widths"] = {}
            
        user_settings["file_table_column_widths"][column_key] = width
        self._save_user_settings(user_settings)
    
    def is_column_visible(self, column_key: str) -> bool:
        """Check if a column is currently visible."""
        return column_key in self.get_visible_columns()
    
    def set_column_visibility(self, column_key: str, visible: bool) -> None:
        """
        Set column visibility.
        
        Args:
            column_key: The column identifier
            visible: Whether column should be visible
        """
        user_settings = self._get_user_settings()
        if "file_table_columns" not in user_settings:
            user_settings["file_table_columns"] = {}
            
        user_settings["file_table_columns"][column_key] = visible
        self._save_user_settings(user_settings)
        
        # Invalidate caches
        self._visible_columns_cache = None
        self._column_mapping_cache = None
    
    def invalidate_cache(self) -> None:
        """Invalidate all caches to force reload on next access."""
        self._config_cache = None
        self._visible_columns_cache = None
        self._column_mapping_cache = None
        self._user_settings_cache = None
        
        logger.debug("[UnifiedColumnService] Cache invalidated")
    
    def _load_configuration(self) -> None:
        """Load column configuration from config.py."""
        from config import FILE_TABLE_COLUMN_CONFIG
        
        config_dict = {}
        
        for key, raw_config in FILE_TABLE_COLUMN_CONFIG.items():
            try:
                # Convert string alignment to enum
                alignment_str = raw_config.get("alignment", "left")
                alignment = ColumnAlignment(alignment_str)
                
                config = ColumnConfig(
                    key=key,
                    title=raw_config["title"],
                    default_visible=raw_config["default_visible"],
                    removable=raw_config["removable"],
                    width=raw_config["width"],
                    min_width=raw_config["min_width"],
                    alignment=alignment
                )
                
                config_dict[key] = config
                
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"[UnifiedColumnService] Invalid config for column {key}: {e}")
                continue
        
        self._config_cache = config_dict
        logger.debug(f"[UnifiedColumnService] Loaded {len(config_dict)} column configurations")
    
    def _compute_visible_columns(self) -> None:
        """Compute list of visible columns based on configuration and user settings."""
        if self._config_cache is None:
            self._load_configuration()
        
        user_settings = self._get_user_settings()
        column_visibility = user_settings.get("file_table_columns", {})
        
        visible_columns = []
        
        for key, config in self._config_cache.items():
            # Use user setting if available, otherwise use default
            is_visible = column_visibility.get(key, config.default_visible)
            if is_visible:
                visible_columns.append(key)
        
        # Sort by display order (could be customized later)
        # For now, maintain the order from FILE_TABLE_COLUMN_CONFIG
        from config import FILE_TABLE_COLUMN_CONFIG
        config_order = list(FILE_TABLE_COLUMN_CONFIG.keys())
        visible_columns.sort(key=lambda x: config_order.index(x) if x in config_order else 999)
        
        self._visible_columns_cache = visible_columns
        logger.debug(f"[UnifiedColumnService] Computed visible columns: {visible_columns}")
    
    def _compute_column_mapping(self) -> None:
        """Compute column index to key mapping."""
        visible_columns = self.get_visible_columns()
        
        # Column 0 is reserved for status column
        mapping = {}
        for i, column_key in enumerate(visible_columns):
            mapping[i + 1] = column_key
        
        self._column_mapping_cache = mapping
        logger.debug(f"[UnifiedColumnService] Computed column mapping: {mapping}")
    
    def _get_user_settings(self) -> Dict[str, Any]:
        """Get user settings with caching, compatible with existing header menu system."""
        if self._user_settings_cache is None:
            try:
                # Try to get from main window config manager first (same as header menu)
                main_window = self._get_main_window()
                
                if main_window and hasattr(main_window, "window_config_manager"):
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    self._user_settings_cache = window_config._data.copy()
                    logger.debug(f"[UnifiedColumnService] Loaded settings from window config manager")
                else:
                    # Fallback to direct JSON loading
                    from utils.json_config_manager import load_config
                    config = load_config()
                    self._user_settings_cache = config.get("window", {})
                    logger.debug(f"[UnifiedColumnService] Loaded settings from JSON fallback")
                    
            except Exception as e:
                logger.warning(f"[UnifiedColumnService] Failed to load user settings: {e}")
                # Final fallback - empty settings
                self._user_settings_cache = {}
        
        return self._user_settings_cache
    
    def _save_user_settings(self, settings: Dict[str, Any]) -> None:
        """Save user settings and invalidate cache, compatible with existing system."""
        try:
            # Try to save via main window config manager first (same as header menu)
            main_window = self._get_main_window()
            
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                
                # Update the window config with new settings
                for key, value in settings.items():
                    window_config.set(key, value)
                
                config_manager.save()
                logger.debug(f"[UnifiedColumnService] Saved settings via window config manager")
            else:
                # Fallback to direct JSON saving
                from utils.json_config_manager import load_config, save_config
                config = load_config()
                config["window"] = settings
                save_config(config)
                logger.debug(f"[UnifiedColumnService] Saved settings via JSON fallback")
            
            # Invalidate cache
            self._user_settings_cache = None
            
        except Exception as e:
            logger.error(f"[UnifiedColumnService] Failed to save user settings: {e}")


# Global service instance
_column_service_instance: Optional[UnifiedColumnService] = None


def get_column_service() -> UnifiedColumnService:
    """
    Get the global column service instance.
    
    Returns:
        Singleton UnifiedColumnService instance
    """
    global _column_service_instance
    
    if _column_service_instance is None:
        _column_service_instance = UnifiedColumnService()
        logger.debug("[UnifiedColumnService] Created global instance")
    
    return _column_service_instance


def invalidate_column_service() -> None:
    """Invalidate the global column service (useful for testing)."""
    global _column_service_instance
    
    if _column_service_instance is not None:
        _column_service_instance.invalidate_cache()
        logger.debug("[UnifiedColumnService] Global instance cache invalidated")
