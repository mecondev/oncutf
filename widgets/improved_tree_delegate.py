"""
Βελτιωμένος TreeViewItemDelegate που διορθώνει το πρόβλημα με το βάψιμο κενού χώρου
"""

import os
from core.pyqt_imports import (
    QBrush,
    QColor,
    QPen,
    QPalette,
    QStyle,
    QStyledItemDelegate,
    Qt,
)


class TreeViewItemDelegate(QStyledItemDelegate):
    """Custom delegate for TreeView items that properly handles background painting."""

    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.theme = theme

    def paint(self, painter, option, index):
        """Custom paint method that correctly handles indented items."""
        # Save original rect
        original_rect = option.rect

        # Get the item's indent level
        tree_view = self.parent()
        indent = tree_view.indentation() if tree_view else 20
        level = 0
        parent = index.parent()
        while parent.isValid():
            level += 1
            parent = parent.parent()

        # Calculate the actual content area (excluding indent)
        content_left = original_rect.left() + (level * indent)
        content_rect = original_rect.adjusted(0, 0, 0, 0)
        content_rect.setLeft(content_left)

        # Only paint background in the content area (not the indent area)
        if option.state & QStyle.State_Selected:
            painter.fillRect(
                content_rect,  # Μόνο το content area, όχι το indent
                QColor(self.theme.get_color("combo_item_background_selected")),
            )
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(
                content_rect,  # Μόνο το content area, όχι το indent
                QColor(self.theme.get_color("combo_item_background_hover")),
            )

        # Set text color based on state
        if option.state & QStyle.State_Selected:
            text_color = QColor(self.theme.get_color("input_selection_text"))
        else:
            text_color = QColor(self.theme.get_color("combo_text"))

        # Draw the text in the content area with proper color
        text = index.data(Qt.DisplayRole)
        if text:
            painter.save()
            painter.setPen(text_color)

            # Text rect with padding inside content area
            text_rect = content_rect.adjusted(4, 0, -4, 0)
            painter.drawText(
                text_rect,
                Qt.AlignLeft | Qt.AlignVCenter,
                str(text),
            )
            painter.restore()


def get_cross_platform_icon_path(icon_name):
    """
    Επιστρέφει cross-platform path για εικόνες.

    Args:
        icon_name: Το όνομα της εικόνας (π.χ. "chevron-right.svg")

    Returns:
        str: Cross-platform path για χρήση σε QSS
    """
    # Βρίσκουμε το base directory του project
    # Υποθέτουμε ότι καλείται από modules που είναι στο project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_dir, "resources", "icons", "feather_icons", icon_name)

    # Normalize path για Windows/Unix compatibility
    normalized_path = os.path.normpath(icon_path)

    # Convert backslashes to forward slashes for QSS (Qt expects forward slashes)
    qss_path = normalized_path.replace("\\", "/")

    return qss_path


class HierarchicalComboBoxHelper:
    """Helper class για cross-platform styling του HierarchicalComboBox"""

    @staticmethod
    def get_cross_platform_stylesheet():
        """Επιστρέφει cross-platform stylesheet για το HierarchicalComboBox"""

        # Get cross-platform paths
        chevron_down_path = get_cross_platform_icon_path("chevron-down.svg")
        chevron_right_path = get_cross_platform_icon_path("chevron-right.svg")
        chevrons_down_path = get_cross_platform_icon_path("chevrons-down.svg")

        return f"""
            QComboBox {{
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px 8px;
                background: white;
                min-height: 20px;
            }}

            QComboBox::down-arrow {{
                image: url({chevrons_down_path});
                width: 12px;
                height: 12px;
            }}

            QTreeView {{
                background: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                outline: none;
                min-width: 200px;
                max-height: 300px;
            }}

            QTreeView::item {{
                padding: 4px 8px;
                border: none;
                min-height: 20px;
            }}

            QTreeView::item:hover {{
                background-color: #f0f0f0;
            }}

            QTreeView::item:selected {{
                background-color: #0078d4;
                color: white;
            }}

            QTreeView::branch {{
                background: transparent;
            }}

            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                image: url({chevron_right_path});
            }}

            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                image: url({chevron_down_path});
            }}
        """


# Παράδειγμα χρήσης στο HierarchicalComboBox
class ImprovedHierarchicalComboBox:
    """Βελτιωμένη έκδοση με cross-platform support"""

    def _apply_styling(self):
        """Apply cross-platform styling for the hierarchical combo box."""
        # Χρησιμοποιούμε τον helper για cross-platform stylesheet
        stylesheet = HierarchicalComboBoxHelper.get_cross_platform_stylesheet()
        self.setStyleSheet(stylesheet)

    def __init__(self, parent=None):
        # ... existing init code ...

        # Set custom delegate with cross-platform support
        from utils.theme_engine import ThemeEngine
        theme = ThemeEngine()
        self.tree_view.setItemDelegate(TreeViewItemDelegate(self.tree_view, theme))

        # Apply cross-platform styling
        self._apply_styling()
