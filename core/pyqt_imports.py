"""
Module: qt_imports.py

Author: Michael Economou
Date: 2025-05-31

qt_imports.py
Centralized PyQt5 imports to reduce import clutter in main files.
Groups related Qt classes together for better organization.
"""

# Core Qt classes
from PyQt5.QtCore import (
    QAbstractTableModel,
    QByteArray,
    QDir,
    QEasingCurve,
    QElapsedTimer,
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QItemSelectionRange,
    QMimeData,
    QModelIndex,
    QMutex,
    QMutexLocker,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    QResource,
    QSize,
    QSortFilterProxyModel,
    QStringListModel,
    Qt,
    QThread,
    QTimer,
    QUrl,
    QVariant,
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
    QFontDatabase,
    QFontMetrics,
    QIcon,
    QIntValidator,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
    QScreen,
    QStandardItem,
    QStandardItemModel,
)

# SVG support
try:
    from PyQt5.QtSvg import QSvgRenderer
    SVG_AVAILABLE = True
except ImportError:
    QSvgRenderer = None
    SVG_AVAILABLE = False

# Widget classes for UI components
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileSystemModel,
    QFrame,
    QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QProxyStyle,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QShortcut,
    QSizePolicy,
    QSplashScreen,
    QSplitter,
    QStyle,
    QStyledItemDelegate,
    QStyleFactory,
    QStyleOption,

    QStyleOptionViewItem,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Re-export all imports for easy access
__all__ = [
    # Core
    'QAbstractTableModel', 'QByteArray', 'QDir', 'QEasingCurve', 'QElapsedTimer', 'QEvent', 'QItemSelection', 'QItemSelectionModel',
    'QItemSelectionRange', 'QMimeData', 'QModelIndex', 'QMutex', 'QMutexLocker', 'QObject', 'QPoint', 'QPropertyAnimation', 'QRect', 'QResource', 'QSize', 'QSortFilterProxyModel', 'QStringListModel', 'Qt', 'QThread',
    'QTimer', 'QUrl', 'QVariant', 'pyqtSignal', 'pyqtSlot',

    # GUI
    'QColor', 'QCursor', 'QDesktopServices', 'QDrag', 'QDragEnterEvent', 'QDragMoveEvent', 'QDropEvent', 'QFont', 'QFontDatabase', 'QFontMetrics', 'QIcon', 'QIntValidator', 'QKeyEvent',
    'QKeySequence', 'QMouseEvent', 'QPainter', 'QPalette', 'QPen', 'QPixmap', 'QScreen', 'QStandardItem',
    'QStandardItemModel',

    # SVG
    'QSvgRenderer', 'SVG_AVAILABLE',

    # Widgets
    'QAbstractItemView', 'QAction', 'QApplication', 'QButtonGroup', 'QCheckBox', 'QComboBox', 'QCompleter', 'QDialog', 'QDialogButtonBox', 'QFileDialog',
    'QFileSystemModel', 'QFrame', 'QGraphicsOpacityEffect', 'QGraphicsDropShadowEffect', 'QGridLayout', 'QGroupBox', 'QHBoxLayout',
    'QHeaderView', 'QLabel', 'QLineEdit', 'QMainWindow', 'QMenu', 'QMessageBox', 'QProgressBar', 'QPushButton', 'QRadioButton', 'QScrollArea', 'QShortcut',
    'QProxyStyle', 'QSizePolicy', 'QSplashScreen', 'QSplitter', 'QStyle', 'QStyleOption', 'QStyledItemDelegate', 'QStyleFactory', 'QStyleOptionViewItem', 'QTableWidget', 'QTableWidgetItem', 'QTableView', 'QTextEdit', 'QTreeView', 'QTreeWidget', 'QTreeWidgetItem',
    'QVBoxLayout', 'QWidget',
]
