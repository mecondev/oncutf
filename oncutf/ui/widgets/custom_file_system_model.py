"""Module: custom_file_system_model.py.

Author: Michael Economou
Date: 2025-05-31

custom_file_system_model.py
Custom QFileSystemModel that uses feather icons instead of OS default icons.
Provides consistent cross-platform appearance with professional feather icons
for folders, files, and expand/collapse indicators.
"""

from pathlib import Path
from typing import Any, ClassVar

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QFileSystemModel

from oncutf.config import ALLOWED_EXTENSIONS
from oncutf.ui.helpers.icons_loader import get_menu_icon
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class CustomFileSystemModel(QFileSystemModel):
    """Custom file system model that uses feather icons for consistent appearance.

    Features:
    - Custom folder icons (folder.svg)
    - File type specific icons (image.svg, video.svg, music.svg, etc.)
    - Custom expand/collapse indicators (chevron-right.svg, chevron-down.svg)
    - Professional cross-platform appearance
    """

    # File type to icon mapping (Material Design icons)
    FILE_TYPE_ICONS: ClassVar[dict[str, str]] = {
        # Images (Material Design: image.svg)
        "jpg": "image",
        "jpeg": "image",
        "png": "image",
        "gif": "image",
        "bmp": "image",
        "tiff": "image",
        "tif": "image",
        "webp": "image",
        "svg": "image",
        "ico": "image",
        "raw": "image",
        "cr2": "image",
        "nef": "image",
        "dng": "image",
        "arw": "image",
        "orf": "image",
        "rw2": "image",
        # Videos (Material Design: movie.svg)
        "mp4": "movie",
        "avi": "movie",
        "mov": "movie",
        "mkv": "movie",
        "mts": "movie",
        "wmv": "movie",
        "flv": "movie",
        "webm": "movie",
        "m4v": "movie",
        "3gp": "movie",
        "mpg": "movie",
        "mpeg": "movie",
        # Audio (Material Design: audio_file.svg)
        "mp3": "audio_file",
        "wav": "audio_file",
        "flac": "audio_file",
        "aac": "audio_file",
        "ogg": "audio_file",
        "wma": "audio_file",
        "m4a": "audio_file",
        "opus": "audio_file",
        "alac": "audio_file",
        # Text/Documents (Material Design: description.svg)
        "txt": "description",
        "md": "description",
        "rtf": "description",
        "doc": "description",
        "docx": "description",
        "pdf": "description",
        "odt": "description",
        "xls": "description",
        "xlsx": "description",
        "ppt": "description",
        "pptx": "description",
        "csv": "description",
        # Archives (Material Design: folder_zip.svg)
        "zip": "folder_zip",
        "rar": "folder_zip",
        "7z": "folder_zip",
        "tar": "folder_zip",
        "gz": "folder_zip",
        "bz2": "folder_zip",
        "xz": "folder_zip",
        "tgz": "folder_zip",
        # Code files (Material Design: code.svg)
        "py": "code",
        "js": "code",
        "html": "code",
        "css": "code",
        "cpp": "code",
        "c": "code",
        "java": "code",
        "php": "code",
        "xml": "code",
        "json": "code",
        "yaml": "code",
        "yml": "code",
    }

    def __init__(self, parent=None):
        """Initialize the file system model with icon caching and preloading."""
        super().__init__(parent)

        # Cache for icons to avoid recreating them
        self._icon_cache = {}

        # Preload common icons
        self._preload_icons()

        logger.debug(
            "[CustomFileSystemModel] Initialized with feather icons",
            extra={"dev_only": True},
        )

    def _preload_icons(self):
        """Preload commonly used icons into cache for better performance."""
        common_icons = [
            "folder",
            "draft",
            "image",
            "movie",
            "audio_file",
            "description",
            "folder_zip",
            "code",
        ]

        for icon_name in common_icons:
            try:
                icon = get_menu_icon(icon_name)
                if not icon.isNull():
                    self._icon_cache[icon_name] = icon
                    logger.debug(
                        "[CustomFileSystemModel] Preloaded icon: %s",
                        icon_name,
                        extra={"dev_only": True},
                    )
                else:
                    logger.warning(
                        "[CustomFileSystemModel] Failed to load icon: %s",
                        icon_name,
                    )
            except Exception:
                logger.exception(
                    "[CustomFileSystemModel] Error loading icon %s",
                    icon_name,
                )

    def _get_cached_icon(self, icon_name: str) -> QIcon:
        """Get icon from cache or load it if not cached."""
        if icon_name not in self._icon_cache:
            try:
                icon = get_menu_icon(icon_name)
                if not icon.isNull():
                    self._icon_cache[icon_name] = icon
                else:
                    # Fallback to default file icon
                    icon = self._icon_cache.get("draft", QIcon())
                    self._icon_cache[icon_name] = icon
            except Exception:
                logger.exception(
                    "[CustomFileSystemModel] Error loading icon %s",
                    icon_name,
                )
                # Fallback to default file icon
                icon = self._icon_cache.get("draft", QIcon())
                self._icon_cache[icon_name] = icon

        return self._icon_cache[icon_name]

    def _get_file_type_icon(self, file_path: str) -> str:
        """Determine the appropriate icon name based on file extension."""
        if self.isDir(self.index(file_path)):
            return "folder"

        # Get file extension
        ext = Path(file_path).suffix
        if ext.startswith("."):
            ext = ext[1:].lower()

        # Check if extension is in our allowed list
        if ext not in ALLOWED_EXTENSIONS:
            return "draft"  # Default icon for unsupported files

        # Return specific icon based on file type
        return self.FILE_TYPE_ICONS.get(ext, "draft")

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Override data method to provide custom icons."""
        # Handle decoration role (icons)
        if role == Qt.DecorationRole and index.isValid():
            file_path = self.filePath(index)
            if file_path:
                icon_name = self._get_file_type_icon(file_path)
                return self._get_cached_icon(icon_name)

        # For all other roles, use default behavior
        return super().data(index, role)

    def hasChildren(self, parent: QModelIndex | None = None) -> bool:
        """Override to ensure proper expand/collapse behavior with optimized checking."""
        if parent is None:
            parent = QModelIndex()

        if not parent.isValid():
            return True

        file_path = self.filePath(parent)
        if file_path and self.isDir(parent):
            # Use the default Qt behavior for better performance
            # Qt's QFileSystemModel already handles this efficiently
            return super().hasChildren(parent)

        return False

    def refresh(self, index: QModelIndex | None = None) -> None:
        """Refresh the file system model to detect new/removed drives.

        This method updates the model by clearing and reloading file system data,
        which is useful when drives are connected/disconnected.

        Args:
            index: The model index to refresh (default: root)

        """
        if index is None:
            index = QModelIndex()

        try:
            # If no index provided, refresh the root (all drives)
            if not index.isValid():
                # Get the current root path
                root_path = self.rootPath()

                # Force a complete model reset to refresh drive list
                # This is necessary because QFileSystemModel caches drive information
                self.beginResetModel()
                try:
                    # Clear the model completely
                    self.setRootPath("")

                    # Force Qt to re-scan the filesystem by accessing the model
                    # This triggers internal cache invalidation
                    self.fetchMore(QModelIndex())

                    # If root path was empty (showing all drives), use "My Computer" or root
                    if not root_path or root_path == "":
                        # On Windows, empty path shows "My Computer" with all drives
                        # Reset to empty again to force re-scan
                        self.setRootPath("")
                    else:
                        # Reload the specific root path
                        self.setRootPath(root_path)
                finally:
                    self.endResetModel()

                logger.info(
                    "[CustomFileSystemModel] Refreshed file system from: %s",
                    root_path or "My Computer",
                )
            else:
                # Refresh specific index
                self.directoryLoaded.emit(self.filePath(index))
                logger.debug(
                    "[CustomFileSystemModel] Refreshed index: %s",
                    self.filePath(index),
                    extra={"dev_only": True},
                )

        except Exception:
            logger.exception("[CustomFileSystemModel] Error refreshing model")
