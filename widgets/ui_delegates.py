"""Custom QStyledItemDelegate classes for enhanced UI components.

This module provides custom delegates for enhanced UI components:
- FileTableHoverDelegate: Full-row hover highlight for file tables
- ComboBoxItemDelegate: Themed styling for combobox dropdown items
- TreeViewItemDelegate: Hierarchical item painting with proper hover tracking

Author: Michael Economou
Date: 2025-05-31
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import QEvent, QModelIndex

from core.pyqt_imports import (
    QBrush,
    QColor,
    QCursor,
    QIcon,
    QPainter,
    QPalette,
    QPen,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    Qt,
    QTableView,
    QTreeView,
    QWidget,
)
from utils.logger_factory import get_cached_logger
from utils.theme import get_qcolor, get_theme_color

if TYPE_CHECKING:
    from utils.theme_engine import ThemeEngine

logger = get_cached_logger(__name__)


class ComboBoxItemDelegate(QStyledItemDelegate):
    """Custom delegate to render QComboBox dropdown items with theme and proper states."""

    def __init__(self, parent: QWidget | None = None, theme: "ThemeEngine | None" = None) -> None:
        super().__init__(parent)
        self.theme = theme

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().initStyleOption(option, index)

        if not self.theme:
            return

        # Use font from theme for absolute consistency
        option.font.setFamily(self.theme.fonts["base_family"])
        option.font.setPointSize(int(self.theme.fonts["interface_size"].replace("pt", "")))
        # Height same as QComboBox fixedHeight (24px to match new height)
        option.rect.setHeight(24)

        # Handle disabled item (grayout)
        if not (index.flags() & Qt.ItemFlag.ItemIsEnabled):
            option.palette.setBrush(
                QPalette.ColorRole.Text, QBrush(QColor(self.theme.get_color("disabled_text")))
            )
            option.font.setItalic(True)
            # Disabled items should not have hover/selected background
            option.palette.setBrush(QPalette.ColorRole.Highlight, QBrush(QColor("transparent")))
        else:
            # Handle selected/hover colors for enabled items
            if option.state & QStyle.StateFlag.State_Selected:
                option.palette.setBrush(
                    QPalette.ColorRole.Text,
                    QBrush(QColor(self.theme.get_color("input_selection_text"))),
                )
                option.palette.setBrush(
                    QPalette.ColorRole.Highlight,
                    QBrush(QColor(self.theme.get_color("combo_item_background_selected"))),
                )
            elif option.state & QStyle.StateFlag.State_MouseOver:
                option.palette.setBrush(
                    QPalette.ColorRole.Text, QBrush(QColor(self.theme.get_color("combo_text")))
                )
                option.palette.setBrush(
                    QPalette.ColorRole.Highlight,
                    QBrush(
                        QColor(self.theme.get_color("table_hover_background"))
                    ),  # Use same hover color as file table
                )
            else:
                # Normal state
                option.palette.setBrush(
                    QPalette.ColorRole.Text, QBrush(QColor(self.theme.get_color("combo_text")))
                )
                option.palette.setBrush(QPalette.ColorRole.Highlight, QBrush(QColor("transparent")))


class FileTableHoverDelegate(QStyledItemDelegate):
    """Custom delegate for file table items with full-row hover highlighting."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the hover delegate.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        self.hovered_row: int = -1

        # Get colors from theme system
        self.hover_color: QColor = get_qcolor("table_hover_background")

    def update_hover_row(self, row: int) -> None:
        """Update the row that should be highlighted on hover."""
        self.hovered_row = row

    def leaveEvent(self, event) -> None:  # noqa: ARG002
        """Handle mouse leave events to hide tooltips."""
        # Hide any active tooltips when mouse leaves the delegate
        from utils.tooltip_helper import TooltipHelper

        parent_widget = self.parent()
        if isinstance(parent_widget, QWidget):
            TooltipHelper.clear_tooltips_for_widget(parent_widget)

        # Note: QStyledItemDelegate doesn't have leaveEvent, this is for compatibility

    def enterEvent(self, event) -> None:  # noqa: ARG002
        """Handle mouse enter events to restore hover state."""
        # Update hover state when mouse enters the delegate
        table = self.parent()
        if isinstance(table, QTableView):
            viewport = table.viewport()
            if viewport:
                pos = viewport.mapFromGlobal(QCursor.pos())
                index = table.indexAt(pos)
                hovered_row = index.row() if index.isValid() else -1
                self.update_hover_row(hovered_row)

        # Note: QStyledItemDelegate doesn't have enterEvent, this is for compatibility

    def focusOutEvent(self, event) -> None:  # noqa: ARG002
        """Handle focus loss events to hide tooltips."""
        # Hide any active tooltips when focus is lost
        from utils.tooltip_helper import TooltipHelper

        parent_widget = self.parent()
        if isinstance(parent_widget, QWidget):
            TooltipHelper.clear_tooltips_for_widget(parent_widget)

        # Note: QStyledItemDelegate doesn't have focusOutEvent, this is for compatibility

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """
        Custom painting for full-row hover and selection with proper icon handling.

        Features:
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
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state &= ~QStyle.StateFlag.State_HasFocus

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
            background_color = QColor(get_theme_color("highlight_light_blue"))
        elif is_selected:
            # Normal selection color
            background_color = QColor(get_theme_color("table_selection_background"))
        elif is_hovered:
            # Hover color - paint over alternate background
            background_color = self.hover_color
        elif row % 2 == 1:
            # Alternate row color for odd rows (only if not selected/hovered)
            background_color = QColor(get_theme_color("table_alternate_background"))
        # For even rows, use default background (no painting needed)

        if background_color:
            painter.save()
            painter.fillRect(option.rect, background_color)
            painter.restore()

        # Draw border for selected rows (only on the last column to avoid overlaps)
        if is_selected and model and column == model.columnCount() - 1:
            painter.save()
            border_color = QColor(get_theme_color("table_selection_background")).darker(130)
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
            icon_data = model.data(index, Qt.ItemDataRole.DecorationRole)
            if icon_data and isinstance(icon_data, QIcon):
                # Check if this is a combined icon (wider than tall) or single icon
                icon_size = icon_data.actualSize(option.rect.size())

                if icon_size.width() > icon_size.height():
                    # Combined icon - use wider rect with minimal padding
                    icon_rect = option.rect.adjusted(1, 2, -1, -2)
                else:
                    # Single icon - use square rect with normal padding
                    icon_rect = option.rect.adjusted(2, 2, -2, -2)

                icon_data.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

            # Don't call super().paint() for column 0 since we handled the icon ourselves
            return

            # For all other columns, paint everything manually - no super().paint()
        display_text = model.data(index, Qt.ItemDataRole.DisplayRole) if model else ""
        if display_text:
            # Determine text color based on selection and hover state
            if is_selected and is_hovered:
                # Selected + hovered: dark text for light blue background
                text_color = QColor(get_theme_color("table_selection_text"))
            else:
                # All other cases (normal, hover only, selected only): light text
                text_color = QColor(get_theme_color("table_text"))

            painter.save()
            painter.setPen(text_color)

            text_rect = option.rect.adjusted(4, 0, -4, 0)  # Small horizontal padding

            alignment = (
                model.data(index, Qt.ItemDataRole.TextAlignmentRole)
                if model
                else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            if not alignment:
                alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

            # Ensure alignment is usable (convert from QVariant if needed)
            if hasattr(alignment, "value"):  # QVariant case
                alignment = alignment.value()
            # Qt.Alignment objects can be used directly with drawText
            # Only fallback to default if alignment is None or invalid
            if alignment is None:
                alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

            fm = painter.fontMetrics()
            elided = fm.elidedText(
                str(display_text), Qt.TextElideMode.ElideRight, text_rect.width()
            )
            painter.drawText(text_rect, alignment, elided)
            painter.restore()


class TreeViewItemDelegate(QStyledItemDelegate):
    """Custom delegate for TreeView items that properly handles background painting."""

    def __init__(self, parent: QWidget | None = None, theme: "ThemeEngine | None" = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.hovered_index: QModelIndex | None = None
        self._tree_view: QTreeView | None = None
        logger.debug("[TreeViewItemDelegate] Initialized")

    def install_event_filter(self, tree_view: QTreeView) -> None:
        """Install event filter for hover tracking (full-row).

        We listen on the viewport for mouse move/leave, and we force a repaint
        of the whole row by keeping track of the hovered index.
        """
        self._tree_view = tree_view
        viewport = tree_view.viewport()
        if viewport:
            viewport.setMouseTracking(True)
            viewport.installEventFilter(self)

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        """Handle mouse events for hover tracking."""
        if event.type() == QEvent.Type.Leave or event.type() == QEvent.Type.HoverLeave:
            self.hovered_index = None
            obj.update()
        elif event.type() == QEvent.Type.MouseMove and self._tree_view:
            pos = event.pos()
            index = self._tree_view.indexAt(pos)
            # Unify hover per row by tracking the first column sibling
            self.hovered_index = index.sibling(index.row(), 0) if index.isValid() else None
            obj.update()
        return False

    def update_hover_row(self, row: int) -> None:
        """Deprecated method, kept for compatibility."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Custom paint method that properly handles hierarchical items with uniform full-row background painting."""
        # Save original rect
        original_rect = option.rect

        # Remove QStyle.State_MouseOver to avoid double hover painting
        if option.state & QStyle.StateFlag.State_MouseOver:
            option.state &= ~QStyle.StateFlag.State_MouseOver

        # The left edge of the content
        # Qt already handles all indentation and branch indicators in option.rect
        content_left = original_rect.left()

        # Get the text
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            super().paint(painter, option, index)
            return

        # Check if item is selectable (not a category)
        item_flags = index.flags()
        is_selectable = bool(item_flags & Qt.ItemFlag.ItemIsSelectable)

        # Paint full-row background for ALL items (categories and subcategories)
        # This ensures consistent styling like file/metadata trees
        # Use the united rect of first..last column to avoid painting over branch/chevrons
        tree_view = self.parent()
        if isinstance(tree_view, QTreeView) and index.model() is not None:
            try:
                model = index.model()
                first = index.sibling(index.row(), 0)
                last = index.sibling(index.row(), max(0, model.columnCount(index.parent()) - 1))
                first_rect = tree_view.visualRect(first)
                last_rect = tree_view.visualRect(last)
                if first_rect.isValid() and last_rect.isValid():
                    bg_rect = first_rect.united(last_rect)
                    # Extend painting to the viewport right edge for a full-row appearance
                    if isinstance(tree_view, QTreeView) and tree_view.viewport():
                        bg_rect.setRight(tree_view.viewport().rect().right())
                else:
                    bg_rect = original_rect
            except Exception:
                bg_rect = original_rect
        else:
            # Fallback to original rect if no tree view
            bg_rect = original_rect

        # Paint background based on state (normal, hover, selected, selected+hover)
        hovered = self.hovered_index
        is_hovered = bool(
            hovered
            and hovered.isValid()
            and index.row() == hovered.row()
            and index.parent() == hovered.parent()
        )

        # Determine selection by selectionModel to unify across columns
        is_selected = False
        if isinstance(tree_view, QTreeView):
            sel = tree_view.selectionModel()
            if sel is not None:
                is_selected = sel.isSelected(index.sibling(index.row(), 0))

        if is_selected and is_hovered:
            # Selected + Hover → highlight_light_blue
            painter.fillRect(bg_rect, get_qcolor("highlight_light_blue"))
        elif is_selected:
            # Selected → table_selection_background
            painter.fillRect(bg_rect, get_qcolor("table_selection_background"))
        elif is_hovered:
            # Hover → table_hover_background
            painter.fillRect(bg_rect, get_qcolor("table_hover_background"))

        # Set text color based on state and item type (icons remain unchanged)
        # First check if item has custom foreground color (e.g., modified metadata)
        custom_foreground = index.data(Qt.ItemDataRole.ForegroundRole)
        
        if custom_foreground is not None:
            # Use custom foreground color from model (for modified keys, extended metadata, etc.)
            if isinstance(custom_foreground, QBrush):
                text_color = custom_foreground.color()
            elif isinstance(custom_foreground, QColor):
                text_color = custom_foreground
            else:
                # Fallback if unknown type
                text_color = get_qcolor("combo_text")
        elif is_selected and is_hovered:
            # Selected + Hover → dark text
            text_color = get_qcolor("table_selection_text")
        elif is_selected:
            # Selected → keep light text like file table
            text_color = get_qcolor("table_text")
        elif not is_selectable:  # Categories
            text_color = get_qcolor("text_secondary")  # Dimmer color for categories
        else:
            text_color = get_qcolor("combo_text")

        # Draw the text
        painter.save()
        painter.setPen(text_color)

        # Text rect: from content_left + padding to the end of the row (with right padding)
        text_rect = original_rect.adjusted(0, 0, 0, 0)
        text_rect.setLeft(content_left + 2)  # Reduced padding from 4px to 2px
        text_rect.setRight(original_rect.right() - 4)

        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            str(text),
        )
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        """Return size hint for items - make them same height as context menu items."""
        # Get the default size hint
        size = super().sizeHint(option, index)

        # Set a consistent, compact height similar to context menu items
        # Standard context menu items are usually around 22-24 pixels
        compact_height = 24

        # Keep the width but use compact height
        size.setHeight(compact_height)

        return size


class MetadataTreeItemDelegate(TreeViewItemDelegate):
    """TreeView delegate for metadata tree that enforces table-like colors.

    Ensures text color follows table rules regardless of model ForegroundRole:
    - Normal: table_text
    - Hover: table_text
    - Selected (unhovered): table_text (stay light)
    - Selected + Hover: table_selection_text (dark)

    Backgrounds:
    - Hover: table_hover_background
    - Selected: table_selection_background
    - Selected + Hover: highlight_light_blue
    """

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paint full-row hover/selection backgrounds; leave text/icons to default.

        This restores stable behavior: the entire row highlights on hover/selection
        regardless of mouse over key/value cell, without altering text colors.
        """
        tree_view = self.parent()
        opt = QStyleOptionViewItem(option)

        # Determine hovered row (consistent across columns)
        hovered = getattr(self, "hovered_index", None)
        is_row_hovered = bool(
            hovered
            and hovered.isValid()
            and index.row() == hovered.row()
            and index.parent() == hovered.parent()
        )

        # Compute full row rect by uniting first and last visible column rects
        full_row_rect = opt.rect
        if isinstance(tree_view, QTreeView) and index.model() is not None:
            try:
                model = index.model()
                first = index.sibling(index.row(), 0)
                last = index.sibling(index.row(), max(0, model.columnCount(index.parent()) - 1))
                first_rect = tree_view.visualRect(first)
                last_rect = tree_view.visualRect(last)
                if first_rect.isValid() and last_rect.isValid():
                    full_row_rect = first_rect.united(last_rect)
                    # Extend painting to the viewport right edge for a full-row appearance
                    if isinstance(tree_view, QTreeView) and tree_view.viewport():
                        full_row_rect.setRight(tree_view.viewport().rect().right())
            except Exception:
                pass

        # Decide background color using selectionModel (row-wise), not option.state
        is_selected = False
        if isinstance(tree_view, QTreeView):
            sel = tree_view.selectionModel()
            if sel is not None:
                is_selected = sel.isSelected(index.sibling(index.row(), 0))
        if is_selected and is_row_hovered:
            painter.fillRect(full_row_rect, get_qcolor("highlight_light_blue"))
        elif is_selected:
            painter.fillRect(full_row_rect, get_qcolor("table_selection_background"))
        elif is_row_hovered:
            painter.fillRect(full_row_rect, get_qcolor("table_hover_background"))

        # Prevent default background double-painting (hover/selection)
        if opt.state & QStyle.StateFlag.State_MouseOver:
            opt.state &= ~QStyle.StateFlag.State_MouseOver
        if opt.state & QStyle.StateFlag.State_Selected:
            opt.state &= ~QStyle.StateFlag.State_Selected

        # Paint content normally (icons, text)
        super().paint(painter, opt, index)
