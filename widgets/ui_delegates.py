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
    QRect,
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
        """Custom paint method with full-row background and custom text colors."""
        tree_view = self.parent()

        hovered = self.hovered_index
        is_hovered = bool(
            hovered
            and hovered.isValid()
            and index.row() == hovered.row()
            and index.parent() == hovered.parent()
        )

        is_selected = False
        if isinstance(tree_view, QTreeView):
            sel = tree_view.selectionModel()
            if sel is not None:
                # Unify selection per row: base it on column 0
                is_selected = sel.isSelected(index.sibling(index.row(), 0))

        # Decide background color
        bg_color = None
        if is_selected and is_hovered:
            bg_color = get_qcolor("highlight_light_blue")
        elif is_selected:
            bg_color = get_qcolor("table_selection_background")
        elif is_hovered:
            bg_color = get_qcolor("table_hover_background")

        # --- FULL ROW BACKGROUND PAINTING ---
        if isinstance(tree_view, QTreeView) and index.model() is not None and bg_color is not None:
            model = index.model()

            # Paint full row only once, on column 0
            if index.column() == 0:
                first_index = index.sibling(index.row(), 0)
                last_index = index.sibling(index.row(), model.columnCount(index.parent()) - 1)

                row_rect_start = tree_view.visualRect(first_index)
                row_rect_end = tree_view.visualRect(last_index)
                full_row_rect = row_rect_start.united(row_rect_end)

                # Extend to the right edge of the viewport for "real" full-row effect
                if tree_view.viewport():
                    viewport_rect = tree_view.viewport().rect()
                    full_row_rect.setLeft(viewport_rect.left())
                    full_row_rect.setRight(viewport_rect.right())

                painter.save()
                painter.fillRect(full_row_rect, bg_color)
                painter.restore()
        # ------------------------------------

        custom_foreground = index.data(Qt.ItemDataRole.ForegroundRole)
        item_flags = index.flags()
        is_selectable = bool(item_flags & Qt.ItemFlag.ItemIsSelectable)

        if custom_foreground is not None:
            if isinstance(custom_foreground, QBrush):
                text_color = custom_foreground.color()
            elif isinstance(custom_foreground, QColor):
                text_color = custom_foreground
            else:
                text_color = get_qcolor("combo_text")
        elif is_selected and is_hovered:
            text_color = get_qcolor("table_selection_text")
        elif is_selected:
            text_color = get_qcolor("table_text")
        elif not is_selectable:
            text_color = get_qcolor("text_secondary")
        else:
            text_color = get_qcolor("combo_text")

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        # Remove default hover/selection paints (we already drew backgrounds)
        opt.state &= ~QStyle.StateFlag.State_Selected
        opt.state &= ~QStyle.StateFlag.State_MouseOver

        # If we have bg_color, sync palette so Qt doesn't "undo" our background
        if bg_color:
            opt.palette.setColor(QPalette.ColorRole.Base, bg_color)
            opt.palette.setColor(QPalette.ColorRole.Window, bg_color)
            opt.palette.setColor(QPalette.ColorRole.Highlight, bg_color)

        # Ensure palette uses our text color in every state
        for group in (
            QPalette.ColorGroup.Active,
            QPalette.ColorGroup.Inactive,
            QPalette.ColorGroup.Disabled,
        ):
            opt.palette.setColor(group, QPalette.ColorRole.Text, text_color)
            opt.palette.setColor(group, QPalette.ColorRole.WindowText, text_color)
            opt.palette.setColor(group, QPalette.ColorRole.ButtonText, text_color)
            opt.palette.setColor(group, QPalette.ColorRole.HighlightedText, text_color)

        # Let Qt handle icon/text/branch painting with the modified palette
        QStyledItemDelegate.paint(self, painter, opt, index)

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
    """TreeView delegate for metadata tree with custom foreground colors.

    Features:
    - Full-row hover/selection backgrounds
    - Respects ForegroundRole for modified keys (yellow #ffe343 + bold)
    - Text visible in all states (normal, hover, selected)
    """

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Initialize style option and force bold font for modified items."""
        super().initStyleOption(option, index)

        custom_fg = index.data(Qt.ItemDataRole.ForegroundRole)
        if custom_fg is not None:
            option.font.setBold(True)
