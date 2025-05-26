"""
hover_delegate.py

Custom QStyledItemDelegate that enables full-row hover highlight.
The hover background color is provided via constructor and is applied
only when the row is not selected.

Author: Michael Economou
Date: 2025-05-21
"""

from PyQt5.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem
from PyQt5.QtGui import QPainter, QColor, QPen, QPalette
from PyQt5.QtCore import QModelIndex


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
        Custom painting for full-row hover and custom selection, respecting QSS.

        - Uses self.hovered_row for hover feedback.
        - Uses table.selected_rows (custom selection) for full-row selection.
        - Applies QSS-defined highlight color from QPalette.
        - Avoids drawing full row manually — lets each cell draw its own background safely.
        """
        table = self.parent()
        model = table.model()
        row = index.row()

        # Remove ugly focus border (dotted)
        if option.state & QStyle.State_HasFocus:
            option.state &= ~QStyle.State_HasFocus

        # Determine states
        is_selected = hasattr(table, "selected_rows") and row in table.selected_rows
        is_hovered = row == self.hovered_row

        if is_selected:
            print(f"[DELEGATE PAINT] SELECTED ROW: {row} (selected_rows={getattr(table, 'selected_rows', None)})")
        if is_hovered:
            print(f"[DELEGATE PAINT] HOVERED ROW: {row}")

        # Set background fill color
        background_color = None
        if is_selected:
            background_color = option.palette.color(QPalette.Highlight)
            if is_hovered:
                background_color = background_color.lighter(115)
        elif is_hovered and not is_selected:
            background_color = self.hover_color

        # Paint background if needed
        if background_color:
            painter.save()
            painter.fillRect(option.rect, background_color)
            painter.restore()

        # Optional: draw border for selected row (only on column 0)
        if is_selected and index.column() == table.horizontalHeader().logicalIndex(table.model().columnCount() - 1):
            painter.save()
            border_color = option.palette.color(QPalette.Highlight).darker(120)
            pen = QPen(border_color)
            pen.setWidth(1)
            painter.setPen(pen)

            # Draw full row rect border
            col_start = 0
            col_end = model.columnCount() - 1
            rect_start = table.visualRect(model.index(row, col_start))
            rect_end = table.visualRect(model.index(row, col_end))
            full_rect = rect_start.united(rect_end)

            painter.drawRect(full_rect.adjusted(0, 0, -1, -1))
            painter.restore()

        # (context-focused row dash border feature removed)

        # Finally, paint cell content (text, icon, etc.)
        # Remove Qt selection and mouse-over state so QSS does not apply selection or hover background
        option.state &= ~QStyle.State_Selected
        option.state &= ~QStyle.State_MouseOver
        super().paint(painter, option, index)
