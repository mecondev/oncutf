"""Icon service facade - provides icon loading without direct UI dependencies.

Author: Michael Economou
Date: 2026-01-22

This facade wraps icon loading utilities from utils/ui, allowing core modules
to access icons without violating boundary rules. Part of Phase A boundary-first
refactoring (250121_summary.md).

Usage:
    from oncutf.app.services.icons import load_preview_status_icons, get_menu_icon
    
    # In initialization code
    icons = load_preview_status_icons()
    
    # In context menus
    icon = get_menu_icon("file")
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.core.pyqt_imports import QIcon, QPixmap


def load_preview_status_icons(size: tuple[int, int] | None = None) -> dict[str, "QIcon"]:
    """Loads and scales preview status icons (valid, invalid, etc.) for use in the UI.
    
    Facade for utils.ui.icon_cache.load_preview_status_icons().
    
    Args:
        size: Size to scale icons to. Default uses PREVIEW_INDICATOR_SIZE from config.
        
    Returns:
        Mapping from status to QIcon.
    """
    from oncutf.utils.ui.icon_cache import load_preview_status_icons as _load
    
    return _load(size)


def prepare_status_icons(base_dir: str | None = None) -> dict[str, str]:
    """Prepares and caches status icons by creating colored icons if they do not exist.
    
    Facade for utils.ui.icon_cache.prepare_status_icons().
    
    Args:
        base_dir: The base directory where icons will be stored. Defaults to project icons dir.
        
    Returns:
        A dictionary mapping icon names to their file paths.
    """
    from oncutf.utils.ui.icon_cache import prepare_status_icons as _prepare
    
    return _prepare(base_dir)


def create_colored_icon(
    fill_color: str,
    shape: str = "circle",
    size_x: int = 10,
    size_y: int = 10,
    border_color: str | None = None,
    border_thickness: int = 0,
) -> "QPixmap":
    """Creates a small colored shape (circle or rectangle) as a QPixmap icon.
    
    Facade for utils.ui.icon_utilities.create_colored_icon().
    
    Args:
        fill_color: Fill color in hex (e.g. "#ff0000").
        shape: "circle" or "square". Default is "circle".
        size_x: Width of the shape. Default is 10.
        size_y: Height of the shape. Default is 10.
        border_color: Optional border color in hex (e.g. "#ffffff").
        border_thickness: Optional border thickness in pixels.
        
    Returns:
        A QPixmap with the desired shape and color.
    """
    from oncutf.utils.ui.icon_utilities import create_colored_icon as _create
    
    return _create(fill_color, shape, size_x, size_y, border_color, border_thickness)


def load_metadata_icons(base_dir: str | None = None) -> dict[str, "QPixmap"]:
    """Loads metadata status icons for the file table's first column.
    
    Facade for utils.ui.icons_loader.load_metadata_icons().
    
    Args:
        base_dir: Base directory where icon files are stored (optional, kept for compatibility)
        
    Returns:
        Dictionary mapping status names to QPixmap objects
    """
    from oncutf.utils.ui.icons_loader import load_metadata_icons as _load
    
    return _load(base_dir)


def get_icons_loader():
    """Returns the global icons_loader instance.
    
    Facade for utils.ui.icons_loader.icons_loader singleton.
    
    Returns:
        ThemeIconLoader instance
    """
    from oncutf.utils.ui.icons_loader import icons_loader
    
    return icons_loader


def get_menu_icon(name: str) -> "QIcon":
    """Get an icon specifically for use in menus.
    
    Facade for icons_loader.get_menu_icon().
    
    Args:
        name: The icon name (without extension)
        
    Returns:
        QIcon object for the requested icon
    """
    from oncutf.utils.ui.icons_loader import icons_loader
    
    return icons_loader.get_menu_icon(name)
