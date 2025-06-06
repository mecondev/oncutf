#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_tree_delegate.py

Author: Michael Economou
Date: 2025-06-15

Αυτό το module ορίζει έναν προσαρμοσμένο delegate για το MetadataTreeView
που υποστηρίζει την εμφάνιση εικονιδίων για τροποποιημένα στοιχεία.
"""

from PyQt5.QtWidgets import QStyledItemDelegate, QStyle
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QPalette, QColor, QIcon, QPainter, QFont

from utils.logger_helper import get_logger

logger = get_logger(__name__)

class MetadataTreeDelegate(QStyledItemDelegate):
    """
    Delegate που χειρίζεται την εμφάνιση των στοιχείων στο MetadataTreeView.
    Προσθέτει εικονίδια για τροποποιημένα στοιχεία και προσαρμόζει την εμφάνιση.
    """

    def __init__(self, parent=None, modified_icon=None, modified_color=QColor("#e67e22")):
        """
        Αρχικοποιεί τον delegate με προαιρετικό εικονίδιο για τροποποιημένα στοιχεία.

        Args:
            parent: Ο γονικός widget (συνήθως το MetadataTreeView)
            modified_icon: Προαιρετικό εικονίδιο για τροποποιημένα στοιχεία (QIcon)
            modified_color: Χρώμα για τροποποιημένα στοιχεία (QColor)
        """
        super().__init__(parent)
        self.modified_icon = modified_icon
        self.modified_color = modified_color
        self.modified_items = set()  # Σύνολο με τα paths των τροποποιημένων στοιχείων

    def set_modified_items(self, items):
        """
        Ενημερώνει το σύνολο των τροποποιημένων στοιχείων.

        Args:
            items: Σύνολο με τα paths των τροποποιημένων στοιχείων
        """
        self.modified_items = items

    def paint(self, painter, option, index):
        """
        Ζωγραφίζει το στοιχείο με προσαρμοσμένη εμφάνιση.

        Args:
            painter: QPainter για τη ζωγραφική
            option: QStyleOptionViewItem με τις επιλογές εμφάνισης
            index: QModelIndex του στοιχείου
        """
        # Πρώτα καλούμε την προεπιλεγμένη μέθοδο ζωγραφικής
        super().paint(painter, option, index)

        # Ελέγχουμε αν είναι στη στήλη Key και είναι τροποποιημένο
        if index.column() == 0:
            tree_view = self.parent()
            if hasattr(tree_view, 'get_key_path'):
                key_path = tree_view.get_key_path(index)

                if key_path in self.modified_items:
                    # Ζωγραφίζουμε ένα μικρό τετράγωνο με το χρώμα modified
                    rect = option.rect
                    indicator_rect = QRect(
                        rect.right() - 12,
                        rect.top() + (rect.height() - 8) // 2,
                        8, 8
                    )

                    painter.save()
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(self.modified_color)
                    painter.drawRect(indicator_rect)
                    painter.restore()

                    # Αν έχουμε εικονίδιο, το ζωγραφίζουμε
                    if self.modified_icon:
                        self.modified_icon.paint(
                            painter,
                            indicator_rect,
                            Qt.AlignCenter
                        )

    def sizeHint(self, option, index):
        """
        Επιστρέφει το προτεινόμενο μέγεθος για το στοιχείο.

        Args:
            option: QStyleOptionViewItem με τις επιλογές εμφάνισης
            index: QModelIndex του στοιχείου

        Returns:
            QSize: Το προτεινόμενο μέγεθος
        """
        size = super().sizeHint(option, index)

        # Αυξάνουμε ελαφρώς το πλάτος για να χωράει το εικονίδιο modified
        if index.column() == 0:
            size.setWidth(size.width() + 16)

        return size
