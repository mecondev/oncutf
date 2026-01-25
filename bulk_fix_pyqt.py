#!/usr/bin/env python3
"""Bulk replace pyqt_imports using grep results."""

import subprocess
import sys

# Qt module mapping
QT_MAP = {
    'QObject': 'QtCore', 'Qt': 'QtCore', 'QTimer': 'QtCore',
    'pyqtSignal': 'QtCore', 'QModelIndex': 'QtCore', 'QEvent': 'QtCore',
    'QKeyEvent': 'QtCore', 'QItemSelection': 'QtCore',
    'QItemSelectionRange': 'QtCore', 'QItemSelectionModel': 'QtCore',
    'QPoint': 'QtCore', 'QRect': 'QtCore', 'QSize': 'QtCore',
    'QUrl': 'QtCore', 'QMimeData': 'QtCore', 'QByteArray': 'QtCore',
    'QAbstractTableModel': 'QtCore', 'QSortFilterProxyModel': 'QtCore',
    'QDateTime': 'QtCore', 'QDate': 'QtCore', 'QTime': 'QtCore',
    'QVariant': 'QtCore', 'QThread': 'QtCore', 'QMutex': 'QtCore',
    'QMutexLocker': 'QtCore',

    'QIcon': 'QtGui', 'QPixmap': 'QtGui', 'QCursor': 'QtGui',
    'QFontMetrics': 'QtGui', 'QPainter': 'QtGui', 'QColor': 'QtGui',
    'QFont': 'QtGui', 'QPalette': 'QtGui', 'QBrush': 'QtGui',
    'QDragEnterEvent': 'QtGui', 'QDragMoveEvent': 'QtGui', 'QDropEvent': 'QtGui',
    'QHelpEvent': 'QtGui', 'QCloseEvent': 'QtGui', 'QPainterPath': 'QtGui',

    'QApplication': 'QtWidgets', 'QWidget': 'QtWidgets',
    'QMessageBox': 'QtWidgets', 'QDialog': 'QtWidgets',
    'QVBoxLayout': 'QtWidgets', 'QHBoxLayout': 'QtWidgets',
    'QLabel': 'QtWidgets', 'QPushButton': 'QtWidgets',
    'QFileDialog': 'QtWidgets', 'QProgressBar': 'QtWidgets',
    'QSizePolicy': 'QtWidgets', 'QCheckBox': 'QtWidgets',
    'QSpinBox': 'QtWidgets', 'QLineEdit': 'QtWidgets',
    'QComboBox': 'QtWidgets', 'QAction': 'QtWidgets',
    'QMenu': 'QtWidgets', 'QIntValidator': 'QtWidgets',
}


def fix_simple_imports():
    """Fix simple single-line imports."""
    # QObject, pyqtSignal
    subprocess.run([
        'find', 'oncutf', 'tests', 'examples', 'scripts', 'main.py',
        '-name', '*.py', '-type', 'f',
        '-exec', 'sed', '-i',
        's/from oncutf\\.core\\.pyqt_imports import QObject, pyqtSignal$/from PyQt5.QtCore import QObject, pyqtSignal/g',
        '{}', ';'
    ])

    # QObject, QTimer, pyqtSignal
    subprocess.run([
        'find', 'oncutf', 'tests', 'examples', 'scripts', 'main.py',
        '-name', '*.py', '-type', 'f',
        '-exec', 'sed', '-i',
        's/from oncutf\\.core\\.pyqt_imports import QObject, QTimer, pyqtSignal$/from PyQt5.QtCore import QObject, QTimer, pyqtSignal/g',
        '{}', ';'
    ])

    # QApplication, Qt
    subprocess.run([
        'find', 'oncutf', 'tests', 'examples', 'scripts', 'main.py',
        '-name', '*.py', '-type', 'f',
        '-exec', 'sed', '-i',
        's/from oncutf\\.core\\.pyqt_imports import QApplication, Qt$/from PyQt5.QtWidgets import QApplication\\nfrom PyQt5.QtCore import Qt/g',
        '{}', ';'
    ])

    # QWidget
    subprocess.run([
        'find', 'oncutf', 'tests', 'examples', 'scripts', 'main.py',
        '-name', '*.py', '-type', 'f',
        '-exec', 'sed', '-i',
        's/from oncutf\\.core\\.pyqt_imports import QWidget$/from PyQt5.QtWidgets import QWidget/g',
        '{}', ';'
    ])

    # QPixmap
    subprocess.run([
        'find', 'oncutf', 'tests', 'examples', 'scripts', 'main.py',
        '-name', '*.py', '-type', 'f',
        '-exec', 'sed', '-i',
        's/from oncutf\\.core\\.pyqt_imports import QPixmap$/from PyQt5.QtGui import QPixmap/g',
        '{}', ';'
    ])

    # QThread
    subprocess.run([
        'find', 'oncutf', 'tests', 'examples', 'scripts', 'main.py',
        '-name', '*.py', '-type', 'f',
        '-exec', 'sed', '-i',
        's/from oncutf\\.core\\.pyqt_imports import QThread$/from PyQt5.QtCore import QThread/g',
        '{}', ';'
    ])

    # QMutexLocker
    subprocess.run([
        'find', 'oncutf', 'tests', 'examples', 'scripts', 'main.py',
        '-name', '*.py', '-type', 'f',
        '-exec', 'sed', '-i',
        's/from oncutf\\.core\\.pyqt_imports import QMutexLocker$/from PyQt5.QtCore import QMutexLocker/g',
        '{}', ';'
    ])


def main():
    print("Fixing simple import patterns...")
    fix_simple_imports()

    # Count remaining
    result = subprocess.run(
        ['grep', '-r', 'from oncutf.core.pyqt_imports import', '.', '--include=*.py'],
        capture_output=True,
        text=True
    )

    remaining = len([l for l in result.stdout.splitlines() if '.venv' not in l])
    print(f"\nRemaining files with pyqt_imports: {remaining}")

    if remaining > 0:
        print("\nRemaining imports (need manual fix):")
        for line in result.stdout.splitlines():
            if '.venv' not in line:
                print(f"  {line}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
