"""
tree_icon_delegate.py

Simple QStyledItemDelegate for tree views that changes icon colors based on selection state.
Uses the SimpleIconInverter for clean icon replacement.

Author: Michael Economou
Date: 2025-06-30
"""

from core.qt_imports import Qt, QIcon, QStyledItemDelegate, QTreeView

from .simple_icon_inverter import get_dark_icon_for_selection
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class TreeViewIconDelegate(QStyledItemDelegate):
    """
    Simple delegate that changes tree view icons based on selection state.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("[TreeViewIconDelegate] Initialized", extra={"dev_only": True})

    def paint(self, painter, option, index):
        """
        Paint with dark icons for selected items.
        """
        tree_view = self.parent()
        if not isinstance(tree_view, QTreeView):
            super().paint(painter, option, index)
            return

        # Check if this item is selected and is the first column (icon column)
        selection_model = tree_view.selectionModel()
        is_selected = selection_model is not None and selection_model.isSelected(index)

        if index.column() == 0 and is_selected:
            # Get the original icon
            original_icon = index.model().data(index, Qt.DecorationRole)

            if original_icon and isinstance(original_icon, QIcon):
                # Determine if it's a folder
                is_folder = False
                model = index.model()
                if hasattr(model, 'isDir'):
                    is_folder = model.isDir(index)

                # Get dark version
                dark_icon = get_dark_icon_for_selection(original_icon, is_folder)

                # Create modified option with dark icon
                modified_option = option.__class__(option)

                # Paint everything normally first
                super().paint(painter, modified_option, index)

                # Get the icon rectangle and paint our dark icon
                style = tree_view.style()
                icon_rect = style.subElementRect(style.SE_ItemViewItemDecoration, modified_option, tree_view)

                if not icon_rect.isNull():
                    # Clear the original icon area and paint our dark icon
                    painter.fillRect(icon_rect, option.palette.base())
                    dark_icon.paint(painter, icon_rect, Qt.AlignCenter)

                return

        # Default painting for everything else
        super().paint(painter, option, index)
