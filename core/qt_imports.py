"""
qt_imports.py

Author: Michael Economou
Date: 2025-01-27

Centralized PyQt5 imports to reduce import clutter in main files.
Groups related Qt classes together for better organization.
"""

# Core Qt classes
from PyQt5.QtCore import (
    QDir,
    QElapsedTimer,
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QMimeData,
    QModelIndex,
    QPoint,
    QPropertyAnimation,
    Qt,
    QThread,
    QTimer,
    QUrl,
    pyqtSignal,
)

# GUI classes for drawing, events, and visual elements
from PyQt5.QtGui import (
    QCursor,
    QDesktopServices,
    QDrag,
    QDropEvent,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)

# Widget classes for UI components
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDesktopWidget,
    QFileDialog,
    QFileSystemModel,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QShortcut,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

# Re-export all imports for easy access
__all__ = [
    # Core
    'QDir', 'QElapsedTimer', 'QEvent', 'QItemSelection', 'QItemSelectionModel',
    'QMimeData', 'QModelIndex', 'QPoint', 'QPropertyAnimation', 'Qt', 'QThread',
    'QTimer', 'QUrl', 'pyqtSignal',

    # GUI
    'QCursor', 'QDesktopServices', 'QDrag', 'QDropEvent', 'QKeyEvent',
    'QKeySequence', 'QMouseEvent', 'QPixmap', 'QStandardItem',
    'QStandardItemModel',

    # Widgets
    'QAbstractItemView', 'QApplication', 'QDesktopWidget', 'QFileDialog',
    'QFileSystemModel', 'QFrame', 'QGraphicsOpacityEffect', 'QHBoxLayout',
    'QHeaderView', 'QLabel', 'QMainWindow', 'QMenu', 'QPushButton', 'QShortcut',
    'QSizePolicy', 'QSplitter', 'QTableWidget', 'QTableWidgetItem', 'QTableView',
    'QVBoxLayout', 'QWidget',
]
