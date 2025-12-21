"""
Module: color_column_delegate.py

Author: Michael Economou
Date: 2025-12-21

Custom delegate for the color column in file table.

Handles:
- Right-click to show color grid menu
- Display of color swatch icons
- Setting color tags on files
"""

from oncutf.core.pyqt_imports import (
    QEvent,
    QStyledItemDelegate,
    Qt,
)
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ColorColumnDelegate(QStyledItemDelegate):
    """
    Custom delegate for the color column.
    
    Provides:
    - Right-click menu for color selection
    - Color swatch display
    """
    
    def __init__(self, parent=None):
        """
        Initialize the color column delegate.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        logger.debug("[ColorColumnDelegate] Initialized")
    
    def editorEvent(self, event, model, option, index):
        """
        Handle mouse events on the color column.
        
        Args:
            event: Mouse event
            model: Data model
            option: Style options
            index: Model index
            
        Returns:
            True if event was handled, False otherwise
        """
        # Right-click shows color menu
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.RightButton:
                logger.debug("[ColorColumnDelegate] Right-click detected at row %d", index.row())
                self._show_color_menu(event.globalPos(), model, index)
                return True
        
        return super().editorEvent(event, model, option, index)
    
    def _show_color_menu(self, pos, model, index):
        """
        Show the color grid menu at the specified position.
        
        Args:
            pos: Global position for menu
            model: Data model
            index: Model index of clicked cell
        """
        from oncutf.ui.widgets.color_grid_menu import ColorGridMenu
        
        logger.debug("[ColorColumnDelegate] Showing color menu at position: %s", pos)
        
        menu = ColorGridMenu()
        menu.color_selected.connect(
            lambda color: self._set_file_color(model, index, color)
        )
        
        # Position menu near click position
        menu.move(pos)
        menu.show()
    
    def _set_file_color(self, model, index, color):
        """
        Set the color tag for a file.
        
        Args:
            model: Data model
            index: Model index
            color: Selected color (hex string or "none")
        """
        logger.debug(
            "[ColorColumnDelegate] Setting color for row %d: %s",
            index.row(),
            color
        )
        
        # Get the file item from the model
        if hasattr(model, 'files') and 0 <= index.row() < len(model.files):
            file_item = model.files[index.row()]
            
            # Update the file item's color
            file_item.color = color
            
            logger.info(
                "[ColorColumnDelegate] Set color %s for file: %s",
                color,
                file_item.filename
            )
            
            # Emit dataChanged signal to refresh the cell
            model.dataChanged.emit(index, index, [Qt.DecorationRole, Qt.DisplayRole])
            
            # TODO: Persist to database
            # self._save_color_to_database(file_item.full_path, color)
        else:
            logger.warning("[ColorColumnDelegate] Invalid row index: %d", index.row())
    
    def _save_color_to_database(self, file_path, color):
        """
        Save color tag to database (placeholder for future implementation).
        
        Args:
            file_path: Full path to file
            color: Color hex string or "none"
        """
        # TODO: Implement database persistence
        # This will be added when integrating with the database manager
        pass
