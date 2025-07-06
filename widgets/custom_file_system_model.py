"""
Module: custom_file_system_model.py

Author: Michael Economou
Date: 2025-07-06

custom_file_system_model.py
Custom QFileSystemModel that uses feather icons instead of OS default icons.
Provides consistent cross-platform appearance with professional feather icons
for folders, files, and expand/collapse indicators.
"""
import os
from typing import Any

from core.qt_imports import QModelIndex, Qt, QIcon, QFileSystemModel

from config import ALLOWED_EXTENSIONS
from utils.icons_loader import get_menu_icon
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class CustomFileSystemModel(QFileSystemModel):
    """
    Custom file system model that uses feather icons for consistent appearance.

    Features:
    - Custom folder icons (folder.svg)
    - File type specific icons (image.svg, video.svg, music.svg, etc.)
    - Custom expand/collapse indicators (chevron-right.svg, chevron-down.svg)
    - Professional cross-platform appearance
    """

    # File type to icon mapping
    FILE_TYPE_ICONS = {
        # Images
        'jpg': 'image',
        'jpeg': 'image',
        'png': 'image',
        'gif': 'image',
        'bmp': 'image',
        'tiff': 'image',
        'tif': 'image',
        'webp': 'image',
        'svg': 'image',
        'ico': 'image',
        'raw': 'image',
        'cr2': 'image',
        'nef': 'image',
        'dng': 'image',

        # Videos
        'mp4': 'video',
        'avi': 'video',
        'mov': 'video',
        'mkv': 'video',
        'wmv': 'video',
        'flv': 'video',
        'webm': 'video',
        'm4v': 'video',
        '3gp': 'video',
        'mpg': 'video',
        'mpeg': 'video',

        # Audio
        'mp3': 'music',
        'wav': 'music',
        'flac': 'music',
        'aac': 'music',
        'ogg': 'music',
        'wma': 'music',
        'm4a': 'music',
        'opus': 'music',

        # Text/Documents
        'txt': 'file-text',
        'md': 'file-text',
        'rtf': 'file-text',
        'doc': 'file-text',
        'docx': 'file-text',
        'pdf': 'file-text',
        'odt': 'file-text',

        # Archives
        'zip': 'archive',
        'rar': 'archive',
        '7z': 'archive',
        'tar': 'archive',
        'gz': 'archive',
        'bz2': 'archive',
        'xz': 'archive',

        # Code files
        'py': 'code',
        'js': 'code',
        'html': 'code',
        'css': 'code',
        'cpp': 'code',
        'c': 'code',
        'java': 'code',
        'php': 'code',
        'xml': 'code',
        'json': 'code',
        'yaml': 'code',
        'yml': 'code',
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        # Cache for icons to avoid recreating them
        self._icon_cache = {}

        # Preload common icons
        self._preload_icons()

        logger.debug("[CustomFileSystemModel] Initialized with feather icons", extra={"dev_only": True})

    def _preload_icons(self):
        """Preload commonly used icons into cache for better performance"""
        common_icons = ['folder', 'file', 'image', 'video', 'music', 'file-text', 'archive', 'code']

        for icon_name in common_icons:
            try:
                icon = get_menu_icon(icon_name)
                if not icon.isNull():
                    self._icon_cache[icon_name] = icon
                    logger.debug(f"[CustomFileSystemModel] Preloaded icon: {icon_name}", extra={"dev_only": True})
                else:
                    logger.warning(f"[CustomFileSystemModel] Failed to load icon: {icon_name}")
            except Exception as e:
                logger.error(f"[CustomFileSystemModel] Error loading icon {icon_name}: {e}")

    def _get_cached_icon(self, icon_name: str) -> QIcon:
        """Get icon from cache or load it if not cached"""
        if icon_name not in self._icon_cache:
            try:
                icon = get_menu_icon(icon_name)
                if not icon.isNull():
                    self._icon_cache[icon_name] = icon
                else:
                    # Fallback to default file icon
                    icon = self._icon_cache.get('file', QIcon())
                    self._icon_cache[icon_name] = icon
            except Exception as e:
                logger.error(f"[CustomFileSystemModel] Error loading icon {icon_name}: {e}")
                # Fallback to default file icon
                icon = self._icon_cache.get('file', QIcon())
                self._icon_cache[icon_name] = icon

        return self._icon_cache[icon_name]

    def _get_file_type_icon(self, file_path: str) -> str:
        """Determine the appropriate icon name based on file extension"""
        if self.isDir(self.index(file_path)):
            return 'folder'

        # Get file extension
        _, ext = os.path.splitext(file_path)
        if ext.startswith('.'):
            ext = ext[1:].lower()

        # Check if extension is in our allowed list
        if ext not in ALLOWED_EXTENSIONS:
            return 'file'  # Default icon for unsupported files

        # Return specific icon based on file type
        return self.FILE_TYPE_ICONS.get(ext, 'file')

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any: # type: ignore
        """Override data method to provide custom icons"""

        # Handle decoration role (icons)
        if role == Qt.DecorationRole: # type: ignore
            if index.isValid():
                file_path = self.filePath(index)
                if file_path:
                    icon_name = self._get_file_type_icon(file_path)
                    return self._get_cached_icon(icon_name)

        # For all other roles, use default behavior
        return super().data(index, role)

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Override to ensure proper expand/collapse behavior with optimized checking"""
        if not parent.isValid():
            return True

        file_path = self.filePath(parent)
        if file_path and self.isDir(parent):
            # Use the default Qt behavior for better performance
            # Qt's QFileSystemModel already handles this efficiently
            return super().hasChildren(parent)

        return False
