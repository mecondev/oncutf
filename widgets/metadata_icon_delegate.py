"""
metadata_icon_delegate.py

Author: Michael Economou
Date: 2025-05-20

This module defines a custom delegate for displaying metadata status icons
in the first column of a QTableView. It visually represents whether metadata
is loaded, missing, or partially available, using color-coded icons and tooltips.

It is used in the main file table of the Batch File Renamer GUI.
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QStyledItemDelegate, QStyleOptionViewItem, QWidget, QToolTip, QAbstractItemView,
)
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtCore import QModelIndex, QRect, Qt, QEvent


class MetadataIconDelegate(QStyledItemDelegate):
    """
    A delegate for rendering metadata status icons in a table column.
    """

    def __init__(self, icon_map: dict[str, QPixmap], parent: Optional[QWidget] = None) -> None:
        """
        Initializes the delegate with a mapping of status keys to icons.

        Args:
            icon_map (dict): A dictionary mapping status strings (e.g., 'loaded', 'missing')
                             to corresponding QPixmap icons.
            parent (QWidget, optional): Optional parent widget.
        """
        super().__init__(parent)
        self.icon_map = icon_map

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """
        Paints only the scaled info icon, without any background color.
        """
        status = index.data(Qt.UserRole)
        icon = self.icon_map.get(status)

        if icon:
            scaled_icon = icon.scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            icon_rect = QRect(
                option.rect.left() + (option.rect.width() - scaled_icon.width()) // 2,
                option.rect.top() + (option.rect.height() - scaled_icon.height()) // 2,
                scaled_icon.width(),
                scaled_icon.height()
            )

            painter.drawPixmap(icon_rect, scaled_icon)
        else:
            # Optional fallback: render nothing or default
            pass

    def helpEvent(
        self,
        event: QEvent,
        view: QAbstractItemView,
        option: QStyleOptionViewItem,
        index: QModelIndex
    ) -> bool:
        """
        Displays tooltips for metadata status icons.

        Args:
            event (QEvent): The tooltip event.
            view (QAbstractItemView): The table view.
            option (QStyleOptionViewItem): Style options.
            index (QModelIndex): Index for the cell.

        Returns:
            bool: True if tooltip was shown, else fallback.
        """
        if event.type() == QEvent.ToolTip:
            status = index.data(Qt.UserRole)
            if status == 'loaded':
                QToolTip.showText(event.globalPos(), "Metadata loaded (full)")
            elif status == 'partial':
                QToolTip.showText(event.globalPos(), "Partial metadata available")
            elif status == 'missing':
                QToolTip.showText(event.globalPos(), "No metadata found")
            elif status == 'invalid':
                QToolTip.showText(event.globalPos(), "Invalid file or corrupted metadata")
            else:
                QToolTip.showText(event.globalPos(), "Unknown metadata status")
            return True

        return super().helpEvent(event, view, option, index)
