"""
hover_delegate.py

Custom QStyledItemDelegate that enables full-row hover highlight.
The hover background color is provided via constructor and is applied
only when the row is not selected.

Author: Michael Economou
Date: 2025-05-21
"""

from PyQt5.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem, QTableView
from PyQt5.QtGui import QPainter, QColor, QPen, QPalette, QIcon
from PyQt5.QtCore import QModelIndex, Qt


class HoverItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, hover_color: str = "#2e3b4e"):
        """
        Initializes the hover delegate.

        Args:
            parent: The parent widget.
            hover_color: The background color to use for hovered rows.
        """
        super().__init__(parent)
        self.hovered_row: int = -1
        self.hover_color: QColor = QColor(hover_color)

    def update_hover_row(self, row: int) -> None:
        """
        Updates the row that should be highlighted on hover.
        """
        self.hovered_row = row

    def paint(self, painter, option, index):
        """
        Custom painting for full-row hover and selection with proper icon handling.

        - Always paints background for hover/selection to override alternate colors
        - Icons in column 0 paint over the background
        - Adds borders for selected rows
        - Proper text colors for selection state
        - Handles alternate row colors internally
        """
        table = self.parent()
        if not isinstance(table, QTableView):
            super().paint(painter, option, index)
            return

        model = table.model()
        row = index.row()
        column = index.column()

        # Remove ugly focus border (dotted)
        if option.state & QStyle.State_HasFocus:
            option.state &= ~QStyle.State_HasFocus

        selection_model = table.selectionModel() if table else None
        is_selected = selection_model is not None and selection_model.isSelected(index)
        is_hovered = row == self.hovered_row

        # Determine background color in priority order:
        # 1. Selection + Hover
        # 2. Selection
        # 3. Hover
        # 4. Alternate row color
        # 5. Default background

        background_color = None
        if is_selected and is_hovered:
            # Selected + hovered: slightly lighter than normal selection
            background_color = QColor("#8a9bb4")
        elif is_selected:
            # Normal selection color
            background_color = QColor("#748cab")
        elif is_hovered:
            # Hover color - paint over alternate background
            background_color = self.hover_color
        elif row % 2 == 1:
            # Alternate row color for odd rows (only if not selected/hovered)
            background_color = QColor("#232323")
        # For even rows, use default background (no painting needed)

        if background_color:
            painter.save()
            painter.fillRect(option.rect, background_color)
            painter.restore()

        # Draw border for selected rows (only on the last column to avoid overlaps)
        if is_selected and model and column == model.columnCount() - 1:
            painter.save()
            border_color = QColor("#748cab").darker(130)
            painter.setPen(QPen(border_color, 1))

            # Calculate full row rect
            col_start = 0
            col_end = model.columnCount() - 1
            rect_start = table.visualRect(model.index(row, col_start))
            rect_end = table.visualRect(model.index(row, col_end))
            full_rect = rect_start.united(rect_end)

            painter.drawRect(full_rect.adjusted(0, 0, -1, -1))
            painter.restore()

        # For column 0 (icons), use custom painting to ensure icons appear over background
        if column == 0:
            # Get the icon from the model's DecorationRole
            icon_data = model.data(index, Qt.DecorationRole)
            if icon_data and isinstance(icon_data, QIcon):
                # Paint icon centered in the cell
                icon_rect = option.rect.adjusted(2, 2, -2, -2)  # Small padding
                icon_data.paint(painter, icon_rect, Qt.AlignCenter)

            # Don't call super().paint() for column 0 since we handled the icon ourselves
            return

        # For all other columns, set appropriate text color and let default painting handle the rest
        text_option = QStyleOptionViewItem(option)
        if is_selected:
            text_option.palette.setColor(QPalette.Text, QColor("#0d1321"))
        else:
            text_option.palette.setColor(QPalette.Text, QColor("#f0ebd8"))

        # Let default painting handle text (will paint over our background)
        super().paint(painter, text_option, index)
