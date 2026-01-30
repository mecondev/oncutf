"""Module: color_column_delegate.py.

Author: Michael Economou
Date: 2025-12-21

Custom delegate for the color column in file table.

Handles:
- Right-click to show color grid menu
- Display of color swatch icons
- Setting color tags on files
- Proper hover/selection states (inherits from FileTableHoverDelegate)
"""

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter
from PyQt5.QtWidgets import (
    QStyle,
    QStyleOptionViewItem,
    QTableView,
)
from typing_extensions import deprecated

from oncutf.ui.delegates.ui_delegates import FileTableHoverDelegate
from oncutf.ui.theme_manager import get_theme_manager
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ColorColumnDelegate(FileTableHoverDelegate):
    """Custom delegate for the color column.

    Inherits from FileTableHoverDelegate to maintain proper hover/selection states.

    Provides:
    - Right-click menu for color selection
    - Color swatch display with proper hover/selection background
    """

    def __init__(self, parent=None):
        """Initialize the color column delegate.

        Args:
            parent: Parent widget (FileTableView)

        """
        super().__init__(parent)
        logger.debug("[ColorColumnDelegate] Initialized (inheriting hover behavior)")

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        """Custom painting for color column with proper hover/selection states.

        Paints:
        - Background color based on hover/selection state
        - Centered color swatch icon
        """
        table = self.parent()
        if not isinstance(table, QTableView):
            super().paint(painter, option, index)
            return

        model = table.model()
        row = index.row()

        # Remove ugly focus border (dotted)
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state &= ~QStyle.StateFlag.State_HasFocus

        selection_model = table.selectionModel() if table else None
        is_selected = selection_model is not None and selection_model.isSelected(index)

        # Get hovered_row from main hover_delegate (not our own)
        hovered_row = -1
        if hasattr(table, "hover_delegate") and table.hover_delegate:
            hovered_row = table.hover_delegate.hovered_row
        is_hovered = row == hovered_row

        # Determine background color (same logic as FileTableHoverDelegate)
        theme = get_theme_manager()
        background_color = None
        if is_selected and is_hovered:
            background_color = QColor(theme.get_color("selected_hover"))
        elif is_selected:
            background_color = QColor(theme.get_color("table_selection_bg"))
        elif is_hovered:
            background_color = self.hover_color
        elif row % 2 == 1:
            background_color = QColor(theme.get_color("table_alternate"))

        # Paint background if needed
        if background_color:
            painter.save()
            painter.fillRect(option.rect, background_color)
            painter.restore()

        # Paint the color swatch icon (centered)
        icon_data = model.data(index, Qt.ItemDataRole.DecorationRole) if model else None
        if icon_data and isinstance(icon_data, QIcon):
            # Center the icon in the cell
            icon_rect = option.rect.adjusted(2, 2, -2, -2)
            icon_data.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

    def editorEvent(self, event, model, option, index):
        """Handle mouse events on the color column.

        Selection behavior:
        - Right-click on non-selected row: change selection to that row, color only that row
        - Right-click on selected row: color ALL selected rows

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
            logger.debug(
                "[ColorColumnDelegate] MouseButtonPress detected - button: %s, row: %d, col: %d",
                event.button(),
                index.row(),
                index.column(),
            )
            if event.button() == Qt.RightButton:
                table = self.parent()
                if not isinstance(table, QTableView):
                    return False

                selection_model = table.selectionModel()
                clicked_row = index.row()

                # Check if clicked row is already selected
                is_row_selected = selection_model and selection_model.isRowSelected(
                    clicked_row, index.parent()
                )

                if is_row_selected:
                    # Clicked on selected row - will color all selected rows
                    selected_rows = self._get_selected_rows(table)
                    logger.info(
                        "[ColorColumnDelegate] RIGHT-CLICK on SELECTED row %d - will color %d rows",
                        clicked_row,
                        len(selected_rows),
                    )
                else:
                    # Clicked on non-selected row - change selection first
                    logger.info(
                        "[ColorColumnDelegate] RIGHT-CLICK on NON-SELECTED row %d - changing selection",
                        clicked_row,
                    )
                    table.clearSelection()
                    table.selectRow(clicked_row)

                self._show_color_menu(event.globalPos(), model, index, table)
                return True

        return super().editorEvent(event, model, option, index)

    def _get_selected_rows(self, table):
        """Get list of selected row indices."""
        selection_model = table.selectionModel()
        if not selection_model:
            return []

        selected_indexes = selection_model.selectedRows()
        return [idx.row() for idx in selected_indexes]

    def _show_color_menu(self, pos, model, index, table):
        """Show the color grid menu at the specified position.

        Args:
            pos: Global position for menu
            model: Data model
            index: Model index of clicked cell
            table: Parent table view

        """
        from oncutf.ui.widgets.color_grid_menu import ColorGridMenu

        # Get selected rows for coloring
        selected_rows = self._get_selected_rows(table)
        if not selected_rows:
            selected_rows = [index.row()]

        logger.info(
            "[ColorColumnDelegate] Creating ColorGridMenu at position: %s (rows to color: %s)",
            pos,
            selected_rows,
        )

        try:
            # Store reference to keep menu alive
            self._active_menu = ColorGridMenu()
            logger.info("[ColorColumnDelegate] ColorGridMenu created successfully")

            self._active_menu.color_selected.connect(
                lambda color: self._set_files_color(model, selected_rows, color)
            )
            logger.info("[ColorColumnDelegate] Signal connected for %d rows", len(selected_rows))

            # Position menu near click position
            self._active_menu.move(pos)
            logger.info("[ColorColumnDelegate] Menu moved to position: %s", pos)

            self._active_menu.show()
            logger.info("[ColorColumnDelegate] Menu.show() called - menu should be visible now")

        except Exception as e:
            logger.exception("[ColorColumnDelegate] ERROR creating/showing menu: %s", e)

    def _set_files_color(self, model, rows, color):
        """Set the color tag for multiple files.

        Args:
            model: Data model
            rows: List of row indices to color
            color: Selected color (hex string or "none")

        """
        logger.info(
            "[ColorColumnDelegate] Setting color %s for %d rows: %s",
            color,
            len(rows),
            rows,
        )

        if not hasattr(model, "files"):
            logger.warning("[ColorColumnDelegate] Model has no files attribute")
            from PyQt5.QtWidgets import QApplication

            QApplication.restoreOverrideCursor()
            return

        # Get database service for persistence
        from oncutf.app.services import get_database_service

        db_service = get_database_service()

        colored_count = 0
        first_index = None
        last_index = None

        # Apply colors (wait cursor already active from ColorGridMenu)
        for row in rows:
            if 0 <= row < len(model.files):
                file_item = model.files[row]
                file_item.color = color

                # Save to database via service
                db_service.set_file_color(file_item.path, color)

                colored_count += 1

                # Track range for dataChanged signal
                idx = model.index(row, 0)
                if first_index is None:
                    first_index = idx
                last_index = idx

                logger.debug(
                    "[ColorColumnDelegate] Set color %s for file: %s",
                    color,
                    file_item.filename,
                )

        # Emit dataChanged for entire range to refresh all colored cells
        if first_index is not None and last_index is not None:
            # Get the color column index
            color_col = 1  # Color column is at visual index 1
            first_color_idx = model.index(first_index.row(), color_col)
            last_color_idx = model.index(last_index.row(), color_col)
            model.dataChanged.emit(first_color_idx, last_color_idx, [Qt.DecorationRole])

        logger.info("[ColorColumnDelegate] Colored %d files with %s", colored_count, color)

        # Restore cursor after all operations complete
        from PyQt5.QtWidgets import QApplication

        QApplication.restoreOverrideCursor()
        logger.info("[ColorColumnDelegate] Cursor restored")

    @deprecated("Use _set_files_color() with single-element list. Will be removed in v2.0.")
    def _set_file_color(self, model, index, color):
        """Set the color tag for a single file (legacy method for compatibility).

        Args:
            model: Data model
            index: Model index
            color: Selected color (hex string or "none")

        """
        self._set_files_color(model, [index.row()], color)
