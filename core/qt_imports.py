"""
qt_imports.py

Author: Michael Economou
Date: 2025-05-01

Centralized PyQt5 imports to reduce import clutter in main files.
Groups related Qt classes together for better organization.
"""

# Core Qt classes
from PyQt5.QtCore import (
    QDir,
    QEasingCurve,
    QElapsedTimer,
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QMimeData,
    QModelIndex,
    QMutex,
    QObject,
    QPoint,
    QPropertyAnimation,
    QSize,
    QSortFilterProxyModel,
    Qt,
    QThread,
    QTimer,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)

# GUI classes for drawing, events, and visual elements
from PyQt5.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
    QDrag,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QFont,
    QFontMetrics,
    QIcon,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)

# Widget classes for UI components
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDesktopWidget,
    QDialog,
    QFileDialog,
    QFileSystemModel,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QShortcut,
    QSizePolicy,
    QSplashScreen,
    QSplitter,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

# Re-export all imports for easy access
__all__ = [
    # Core
    'QDir', 'QEasingCurve', 'QElapsedTimer', 'QEvent', 'QItemSelection', 'QItemSelectionModel',
    'QMimeData', 'QModelIndex', 'QMutex', 'QObject', 'QPoint', 'QPropertyAnimation', 'QSize', 'QSortFilterProxyModel', 'Qt', 'QThread',
    'QTimer', 'QUrl', 'pyqtSignal', 'pyqtSlot',

    # GUI
    'QColor', 'QCursor', 'QDesktopServices', 'QDrag', 'QDragEnterEvent', 'QDragMoveEvent', 'QDropEvent', 'QFont', 'QFontMetrics', 'QIcon', 'QKeyEvent',
    'QKeySequence', 'QMouseEvent', 'QPainter', 'QPalette', 'QPen', 'QPixmap', 'QStandardItem',
    'QStandardItemModel',

    # Widgets
    'QAbstractItemView', 'QAction', 'QApplication', 'QCheckBox', 'QComboBox', 'QDesktopWidget', 'QDialog', 'QFileDialog',
    'QFileSystemModel', 'QFrame', 'QGraphicsOpacityEffect', 'QHBoxLayout',
    'QHeaderView', 'QLabel', 'QLineEdit', 'QMainWindow', 'QMenu', 'QProgressBar', 'QPushButton', 'QScrollArea', 'QShortcut',
    'QSizePolicy', 'QSplashScreen', 'QSplitter', 'QStyle', 'QStyledItemDelegate', 'QStyleOptionViewItem', 'QTableWidget', 'QTableWidgetItem', 'QTableView', 'QTextEdit', 'QTreeView',
    'QVBoxLayout', 'QWidget',
]
