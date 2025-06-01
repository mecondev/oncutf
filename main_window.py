"""
main_window.py
Author: Michael Economou
Date: 2025-05-01

This module defines the MainWindow class, which implements the primary user interface
for the oncutf application. It includes logic for loading files from folders, launching
metadata extraction in the background, and managing user interaction such as rename previews.

Note: PyQt5 type hints are not fully supported by static type checkers.
Many of the linter warnings are false positives and can be safely ignored.
"""

# type: ignore (PyQt5 attributes not recognized by linter)

import os
import glob
import datetime
import platform
import json
from typing import Optional
import threading
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QFrame, QScrollArea, QTableWidget, QFileDialog,
    QFileSystemModel, QAbstractItemView, QSizePolicy, QHeaderView, QTableWidgetItem,
    QDesktopWidget, QGraphicsOpacityEffect, QMenu, QShortcut, QAbstractScrollArea
)
from PyQt5.QtCore import (
    Qt, QDir, QUrl, QThread, QTimer, QModelIndex, QPropertyAnimation, QMetaObject,
    QItemSelection, QItemSelectionRange, QItemSelectionModel, QSize, QEvent
)
from PyQt5.QtGui import (
    QPixmap, QBrush, QColor, QIcon, QDesktopServices, QStandardItem, QStandardItemModel,
    QKeySequence, QCursor
)

from models.file_table_model import FileTableModel
from models.file_item import FileItem

from modules.name_transform_module import NameTransformModule

from utils.filename_validator import FilenameValidator
from utils.preview_generator import generate_preview_names as generate_preview_logic
from utils.icons import create_colored_icon
from utils.icon_cache import prepare_status_icons
from utils.preview_engine import apply_rename_modules
from utils.build_metadata_tree_model import build_metadata_tree_model
from utils.metadata_cache import MetadataCache
from utils.metadata_utils import resolve_skip_metadata
from utils.renamer import Renamer
from utils.text_helpers import elide_text
from utils.icon_loader import load_metadata_icons
from utils.metadata_loader import MetadataLoader

from widgets.metadata_worker import MetadataWorker
from widgets.interactive_header import InteractiveHeader
from widgets.custom_msgdialog import CustomMessageDialog
from widgets.metadata_icon_delegate import MetadataIconDelegate
from widgets.custom_table_view import CustomTableView
from widgets.custom_tree_view import CustomTreeView
from widgets.metadata_tree_view import MetadataTreeView
from widgets.metadata_waiting_dialog import MetadataWaitingDialog
from widgets.rename_modules_area import RenameModulesArea


from config import *
from config import FILE_TABLE_COLUMN_WIDTHS

# Setup Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)

import contextlib
import re

@contextlib.contextmanager
def wait_cursor():
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        """
        Initializes the main window and sets up the layout.

        Features:
        - Load files from folders
        - Extract metadata in the background
        - Preview file renaming
        - Batch file renaming

        Drag & Drop Support:
        - You can drag folders onto the application window
        - Press Alt while dragging to enable recursive loading
        - Press Ctrl while dragging to load metadata
        - Press Ctrl+Shift while dragging to load extended metadata

        Context menu:
        - In the folder tree (right-click): options for loading, recursive loading and viewing
        - In the file table (right-click): options for selection, metadata and reloading
        """
        super().__init__()

        # --- Attributes initialization ---
        self.metadata_thread = None
        self.metadata_worker = None
        self.metadata_cache = MetadataCache()
        self._metadata_worker_cancel_requested = False
        self.metadata_loaded_paths = set()  # full paths with metadata
        self.metadata_icon_map = load_metadata_icons()
        self.force_extended_metadata = False
        self.skip_metadata_mode = DEFAULT_SKIP_METADATA # Keeps state across folder reloads
        self.metadata_loader = MetadataLoader()
        self.model = FileTableModel(parent_window=self)
        self.metadata_loader.model = self.model

        self.loading_dialog = None

        self.create_colored_icon = create_colored_icon
        self.icon_paths = prepare_status_icons()

        self.filename_validator = FilenameValidator()
        self.last_action = None  # Could be: 'folder_select', 'browse', 'rename', etc.
        self.current_folder_path = None
        self.files = []
        self.preview_map = {}  # preview_filename -> FileItem
        self._selection_sync_mode = "normal"  # values: "normal", "toggle"

        # --- Setup window and central widget ---
        self.setup_main_window()
        self.setup_main_layout()

        # --- Setup splitters and panels ---
        self.setup_splitters()
        self.setup_left_panel()
        self.setup_center_panel()
        self.setup_right_panel()

        # --- Bottom layout setup ---
        self.setup_bottom_layout()

        # --- Footer setup ---
        self.setup_footer()

        # --- Signal connections ---
        self.setup_signals()

        # --- Disable drag-out functionality ---
        self.disable_drag_out()

    # --- Method definitions ---
    def setup_main_window(self) -> None:
        """Configure main window properties."""
        self.setWindowTitle("oncutf - Batch File Renamer and More")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.center_window()

    def disable_drag_out(self) -> None:
        """
        Disable drag-out functionality for all relevant widgets.
        This prevents users from accidentally dragging files from the application to the desktop.
        """
        # Note: folder_tree settings are handled separately in setup_left_panel
        # We want to keep drag functionality for folder_tree within the application

        # Disable dragging out from file table
        if hasattr(self, "file_table_view"):
            self.file_table_view.setDragDropMode(QAbstractItemView.DropOnly)
            # Δεν θέτω setDefaultDropAction γιατί το Qt.IgnoreAction δεν υπάρχει στην PyQt5 και το default είναι CopyAction
            pass

        # Disable dragging out from metadata tree
        if hasattr(self, "metadata_tree_view"):
            self.metadata_tree_view.setDragDropMode(QAbstractItemView.DropOnly)
            self.metadata_tree_view.setDragEnabled(False)

        # Disable dragging out from preview tables
        if hasattr(self, "preview_old_name_table"):
            self.preview_old_name_table.setDragEnabled(False)
            self.preview_old_name_table.setDragDropMode(QAbstractItemView.NoDragDrop)

        if hasattr(self, "preview_new_name_table"):
            self.preview_new_name_table.setDragEnabled(False)
            self.preview_new_name_table.setDragDropMode(QAbstractItemView.NoDragDrop)

        logger.info("Drag-out functionality disabled for all widgets")

    def setup_main_layout(self) -> None:
        """Setup central widget and main layout."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

    def setup_splitters(self) -> None:
        """Setup vertical and horizontal splitters."""
        self.vertical_splitter = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.vertical_splitter)
        self.horizontal_splitter = QSplitter(Qt.Horizontal)
        self.vertical_splitter.addWidget(self.horizontal_splitter)
        self.vertical_splitter.setSizes(TOP_BOTTOM_SPLIT_RATIO)

    def setup_left_panel(self) -> None:
        """Setup left panel (folder tree)."""
        self.left_frame = QFrame()
        left_layout = QVBoxLayout(self.left_frame)
        left_layout.addWidget(QLabel("Folders"))

        self.folder_tree = CustomTreeView()
        self.tree_view = CustomTreeView()
        self.tree_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_layout.addWidget(self.tree_view)

        # Expand/collapse mode (single ή double click)
        if TREE_EXPAND_MODE == "single":
            self.folder_tree.setExpandsOnDoubleClick(False)  # Single click expand
        else:
            self.folder_tree.setExpandsOnDoubleClick(True)   # Double click expand

        btn_layout = QHBoxLayout()
        self.select_folder_button = QPushButton("Select Folder")
        self.browse_folder_button = QPushButton("Browse Folders")
        btn_layout.addWidget(self.select_folder_button)
        btn_layout.addWidget(self.browse_folder_button)
        left_layout.addLayout(btn_layout)

        self.dir_model = QFileSystemModel()
        self.dir_model.setRootPath('')
        # Τροποποιήθηκε το φίλτρο για να εμφανίζει φακέλους ΚΑΙ αρχεία με επιτρεπόμενες επεκτάσεις
        self.dir_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)

        # Προσθήκη φίλτρου για τις επιτρεπόμενες επεκτάσεις αρχείων
        name_filters = []
        for ext in ALLOWED_EXTENSIONS:
            name_filters.append(f"*.{ext}")
        self.dir_model.setNameFilters(name_filters)
        self.dir_model.setNameFilterDisables(False)  # Αυτό κρύβει τα αρχεία που δεν ταιριάζουν αντί να τα απενεργοποιεί

        self.folder_tree.setModel(self.dir_model)
        for i in range(1, 4):
            self.folder_tree.hideColumn(i)

        root = "" if platform.system() == "Windows" else "/"
        self.folder_tree.setRootIndex(self.dir_model.index(root))

        self.horizontal_splitter.addWidget(self.left_frame)

        # Οι ρυθμίσεις drag & drop γίνονται στο CustomTreeView

    def setup_center_panel(self) -> None:
        """Setup center panel (file table view)."""
        self.center_frame = QFrame()
        center_layout = QVBoxLayout(self.center_frame)

        self.files_label = QLabel("Files")
        center_layout.addWidget(self.files_label)

        self.file_table_view = CustomTableView(parent=self)
        self.file_table_view.parent_window = self
        self.file_table_view.verticalHeader().setVisible(False)
        self.file_table_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.model = FileTableModel(parent_window=self)

        self.show_file_table_placeholder("No folder selected")

        # Setup drag-drop connection
        self.file_table_view.files_dropped.connect(
            lambda paths, modifiers: self._handle_dropped_files(paths, modifiers)
        )

        # Allow only internal drag & drop or drop only (no drag out)
        self.file_table_view.setDragDropMode(QAbstractItemView.DropOnly)
        # Δεν θέτω setDefaultDropAction γιατί το Qt.IgnoreAction δεν υπάρχει στην PyQt5 και το default είναι CopyAction

        # Header setup
        self.header = InteractiveHeader(Qt.Horizontal, self.file_table_view, parent_window=self)
        self.file_table_view.setHorizontalHeader(self.header)
        # Align all headers to the left (if supported)
        if hasattr(self.header, 'setDefaultAlignment'):
            self.header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.header.setSortIndicatorShown(True)
        self.header.setSectionsClickable(True)
        self.header.setHighlightSections(True)

        self.file_table_view.setHorizontalHeader(self.header)
        self.file_table_view.setAlternatingRowColors(False)
        self.file_table_view.setShowGrid(False)
        self.file_table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table_view.setSortingEnabled(False)  # Manual sorting logic
        self.file_table_view.setWordWrap(False)

        # Row height will be controlled via CSS min-height in table_view.qss

        # Initialize header and set default row height
        header = self.file_table_view.horizontalHeader()
        vertical_header = self.file_table_view.verticalHeader()
        if vertical_header is not None:
            vertical_header.setDefaultSectionSize(22)  # Compact row height

        # Configure column sizes and behaviors
        if header:
            # Column 0: Info icon column (fixed small width)
            header.setMinimumSectionSize(23)  # PyQt5: only global min width supported
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.resizeSection(0, FILE_TABLE_COLUMN_WIDTHS["STATUS_COLUMN"])
            self.file_table_view.setColumnWidth(0, FILE_TABLE_COLUMN_WIDTHS["STATUS_COLUMN"])

            # Column 1: Filename (wide, interactive)
            header.setSectionResizeMode(1, QHeaderView.Interactive)
            header.resizeSection(1, FILE_TABLE_COLUMN_WIDTHS["FILENAME_COLUMN"])
            self.file_table_view.setColumnWidth(1, FILE_TABLE_COLUMN_WIDTHS["FILENAME_COLUMN"])

            # Column 2: Filesize (new column)
            col2_min = self.fontMetrics().horizontalAdvance("999 GB") + 50
            header.setSectionResizeMode(2, QHeaderView.Interactive)
            self.file_table_view.setColumnWidth(2, FILE_TABLE_COLUMN_WIDTHS["FILESIZE_COLUMN"])

            # Column 3: Extension (type column)
            header.setSectionResizeMode(3, QHeaderView.Interactive)
            self.file_table_view.setColumnWidth(3, FILE_TABLE_COLUMN_WIDTHS["EXTENSION_COLUMN"])

            # Column 4: Modified date
            header.setSectionResizeMode(4, QHeaderView.Stretch)
            self.file_table_view.setColumnWidth(4, FILE_TABLE_COLUMN_WIDTHS["DATE_COLUMN"])

        # Show placeholder after setup is complete
        self.show_file_table_placeholder("No folder selected")
        center_layout.addWidget(self.file_table_view)
        self.horizontal_splitter.addWidget(self.center_frame)

    def setup_right_panel(self) -> None:
        """Setup right panel (metadata tree view)."""
        self.right_frame = QFrame()
        right_layout = QVBoxLayout(self.right_frame)
        right_layout.addWidget(QLabel("Information"))

        # Expand/Collapse buttons
        self.toggle_expand_button = QPushButton("Expand All")
        self.toggle_expand_button.setCheckable(True)
        self.toggle_expand_button.setFixedWidth(120)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.toggle_expand_button)
        button_layout.addStretch()

        right_layout.addLayout(button_layout)

        # Metadata Tree View
        self.metadata_tree_view = MetadataTreeView()
        self.metadata_tree_view.setAlternatingRowColors(True)  # Enable alternating row colors
        self.metadata_tree_view.files_dropped.connect(
            lambda paths, modifiers: self.send_files_to_metadata_viewer(paths, modifiers)
        )
        self.metadata_tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.metadata_tree_view.expandToDepth(1)
        self.metadata_tree_view.setRootIsDecorated(False)
        self.metadata_tree_view.setAcceptDrops(True)
        self.metadata_tree_view.viewport().setAcceptDrops(True)
        self.metadata_tree_view.setDragDropMode(QAbstractItemView.DropOnly)
        self.metadata_tree_view.setDragEnabled(False)  # Explicitly disable dragging out

        right_layout.addWidget(self.metadata_tree_view)

        # Dummy initial model
        placeholder_model = QStandardItemModel()
        placeholder_model.setHorizontalHeaderLabels(["Key", "Value"])
        placeholder_item = QStandardItem("No file selected")
        placeholder_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        placeholder_value = QStandardItem("-")
        placeholder_model.appendRow([placeholder_item, placeholder_value])

        # self.metadata_tree_view.setModel(placeholder_model)
        self.show_empty_metadata_tree("No file selected")
        self.metadata_tree_view.expandAll()
        self.toggle_expand_button.setChecked(True)
        self.toggle_expand_button.setText("Collapse All")

        # Finalize
        self.horizontal_splitter.addWidget(self.right_frame)
        self.horizontal_splitter.setSizes(LEFT_CENTER_RIGHT_SPLIT_RATIO)

    def setup_bottom_layout(self) -> None:
        """Setup bottom layout for rename modules and preview."""
        # --- Bottom Frame: Rename Modules + Preview ---
        self.bottom_frame = QFrame()
        self.bottom_layout = QVBoxLayout(self.bottom_frame)
        self.bottom_layout.setSpacing(0)
        self.bottom_layout.setContentsMargins(0, 0, 0, 0)

        content_layout = QHBoxLayout()

        # === Left: Rename modules ===
        self.rename_modules_area = RenameModulesArea(parent=self, parent_window=self)

        # === Right: Rename preview ===
        self.preview_frame = QFrame()
        preview_layout = QVBoxLayout(self.preview_frame)
        self.old_label = QLabel("Old file(s) name(s)")
        self.new_label = QLabel("New file(s) name(s)")

        self.preview_old_name_table = QTableWidget(0, 1)
        self.preview_new_name_table = QTableWidget(0, 1)
        self.preview_icon_table = QTableWidget(0, 1)

        for table in [self.preview_old_name_table, self.preview_new_name_table]:
            table.setHorizontalScrollBarPolicy(QAbstractScrollArea.ScrollBarAsNeeded)
            table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            table.setWordWrap(False)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setSelectionMode(QAbstractItemView.NoSelection)
            table.verticalHeader().setVisible(False)
            table.setVerticalHeader(None)
            table.horizontalHeader().setVisible(False)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
            table.setAlternatingRowColors(True)  # Enable alternating row colors
            table.verticalHeader().setDefaultSectionSize(22)  # Compact row height - same as icon table
            # Disable drag & drop functionality
            table.setDragEnabled(False)
            table.setAcceptDrops(False)
            table.setDragDropMode(QAbstractItemView.NoDragDrop)
            # Row height will be controlled via CSS

        self.preview_icon_table.setObjectName("iconTable")
        self.preview_icon_table.setFixedWidth(24)
        self.preview_icon_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview_icon_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.preview_icon_table.verticalHeader().setVisible(False)
        self.preview_icon_table.setVerticalHeader(None)
        self.preview_icon_table.setShowGrid(False)
        self.preview_icon_table.horizontalHeader().setVisible(False)
        self.preview_icon_table.setHorizontalHeader(None)
        self.preview_icon_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview_icon_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview_icon_table.setShowGrid(False)
        self.preview_icon_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.preview_icon_table.setStyleSheet("background-color: #212121;")
        self.preview_icon_table.verticalHeader().setDefaultSectionSize(22)  # Compact row height

        table_pair_layout = QHBoxLayout()
        old_layout = QVBoxLayout()
        new_layout = QVBoxLayout()
        icon_layout = QVBoxLayout()

        old_layout.addWidget(self.old_label)
        old_layout.addWidget(self.preview_old_name_table)
        new_layout.addWidget(self.new_label)
        new_layout.addWidget(self.preview_new_name_table)
        icon_layout.addWidget(QLabel(" "))
        icon_layout.addWidget(self.preview_icon_table)

        table_pair_layout.addLayout(old_layout)
        table_pair_layout.addLayout(new_layout)
        table_pair_layout.addLayout(icon_layout)
        preview_layout.addLayout(table_pair_layout)

        controls_layout = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setTextFormat(Qt.RichText)

        # Status label fade effect setup
        self.status_opacity_effect = QGraphicsOpacityEffect()
        self.status_label.setGraphicsEffect(self.status_opacity_effect)
        self.status_fade_anim = QPropertyAnimation(self.status_opacity_effect, b"opacity")
        self.status_fade_anim.setDuration(800)  # ms
        self.status_fade_anim.setStartValue(1.0)
        self.status_fade_anim.setEndValue(0.3)
        controls_layout.addWidget(self.status_label, stretch=1)

        self.rename_button = QPushButton("Rename")
        self.rename_button.setEnabled(False)
        self.rename_button.setFixedWidth(120)
        controls_layout.addWidget(self.rename_button)
        preview_layout.addLayout(controls_layout)

        self.preview_frame.setLayout(preview_layout)

        content_layout.addWidget(self.rename_modules_area, stretch=1)
        content_layout.addWidget(self.preview_frame, stretch=3)
        self.bottom_layout.addLayout(content_layout)

    def setup_footer(self) -> None:
        """Setup footer with version label."""
        footer_separator = QFrame()
        footer_separator.setFrameShape(QFrame.HLine)
        footer_separator.setFrameShadow(QFrame.Sunken)

        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(10, 4, 10, 4)

        self.version_label = QLabel()
        self.version_label.setText(f"{APP_NAME} v{APP_VERSION}")
        self.version_label.setObjectName("versionLabel")
        self.version_label.setAlignment(Qt.AlignLeft)
        footer_layout.addWidget(self.version_label)
        footer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.vertical_splitter.addWidget(self.horizontal_splitter)
        self.vertical_splitter.addWidget(self.bottom_frame)
        self.vertical_splitter.setSizes([500, 300])

        self.main_layout.addWidget(footer_separator)
        self.main_layout.addWidget(footer_widget)

    def setup_signals(self) -> None:
        """
        Connects UI elements to their corresponding event handlers.
        Uses safe connections with checks for None objects.
        """
        if hasattr(self.header, 'sectionClicked'):
            self.header.sectionClicked.connect(self.sort_by_column)

        if hasattr(self.select_folder_button, 'clicked'):
            self.select_folder_button.clicked.connect(self.handle_folder_select)
        if hasattr(self.browse_folder_button, 'clicked'):
            self.browse_folder_button.clicked.connect(self.handle_browse)

        if hasattr(self.file_table_view, 'clicked'):
            self.file_table_view.clicked.connect(self.on_table_row_clicked)
        if hasattr(self.file_table_view, 'selection_changed'):
            self.file_table_view.selection_changed.connect(self.update_preview_from_selection)
        if hasattr(self.model, 'sort_changed'):
            self.model.sort_changed.connect(self.generate_preview_names)

        # Setup context menu safely
        self.file_table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        if hasattr(self.file_table_view, 'customContextMenuRequested'):
            self.file_table_view.customContextMenuRequested.connect(self.handle_table_context_menu)

        self.folder_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        if hasattr(self.folder_tree, 'customContextMenuRequested'):
            self.folder_tree.customContextMenuRequested.connect(self.handle_tree_context_menu)

        # Connect folder_tree drop event safely
        if hasattr(self.folder_tree, 'files_dropped'):
            self.folder_tree.files_dropped.connect(
                lambda paths, modifiers: self.import_folder_from_drop(paths, modifiers)
            )

        if hasattr(self.toggle_expand_button, 'toggled'):
            self.toggle_expand_button.toggled.connect(self.toggle_metadata_expand)

        # Connect scrollbars safely
        old_vscroll = getattr(self.preview_old_name_table, 'verticalScrollBar', lambda: None)()
        new_vscroll = getattr(self.preview_new_name_table, 'verticalScrollBar', lambda: None)()
        icon_vscroll = getattr(self.preview_icon_table, 'verticalScrollBar', lambda: None)()

        if old_vscroll and new_vscroll and hasattr(old_vscroll, 'valueChanged') and hasattr(new_vscroll, 'setValue'):
            old_vscroll.valueChanged.connect(new_vscroll.setValue)

        if new_vscroll and old_vscroll and hasattr(new_vscroll, 'valueChanged') and hasattr(old_vscroll, 'setValue'):
            new_vscroll.valueChanged.connect(old_vscroll.setValue)

        if old_vscroll and icon_vscroll and hasattr(old_vscroll, 'valueChanged') and hasattr(icon_vscroll, 'setValue'):
            old_vscroll.valueChanged.connect(icon_vscroll.setValue)

        if hasattr(self.rename_button, 'clicked'):
            self.rename_button.clicked.connect(self.rename_files)

        # --- Connect the updated signal of RenameModulesArea to generate_preview_names ---
        if hasattr(self.rename_modules_area, 'updated'):
            self.rename_modules_area.updated.connect(self.generate_preview_names)

        # --- Shortcuts ---
        # Fix QShortcut by connecting the signal later
        shortcut_a = QShortcut(QKeySequence("Ctrl+A"), self.file_table_view)
        shortcut_a.activated.connect(self.select_all_rows)

        shortcut_shift_a = QShortcut(QKeySequence("Ctrl+Shift+A"), self.file_table_view)
        shortcut_shift_a.activated.connect(self.clear_all_selection)

        shortcut_i = QShortcut(QKeySequence("Ctrl+I"), self.file_table_view)
        shortcut_i.activated.connect(self.invert_selection)

        shortcut_o = QShortcut(QKeySequence("Ctrl+O"), self.file_table_view)
        shortcut_o.activated.connect(self.handle_browse)

        shortcut_r = QShortcut(QKeySequence("Ctrl+R"), self.file_table_view)
        shortcut_r.activated.connect(self.force_reload)

        shortcut_m = QShortcut(QKeySequence("Ctrl+M"), self.file_table_view)
        shortcut_m.activated.connect(self.shortcut_load_metadata)

        shortcut_e = QShortcut(QKeySequence("Ctrl+E"), self.file_table_view)
        shortcut_e.activated.connect(self.shortcut_load_extended_metadata)

    def force_reload(self) -> None:
        """
        Triggered by Ctrl+R.
        If Ctrl is held, metadata scan is skipped (like Select/Browse).
        Otherwise, full reload with scan.
        """
        if not self.current_folder_path:
            self.set_status("No folder loaded.", color="gray", auto_reset=True)
            return

        if not CustomMessageDialog.question(self, "Reload Folder", "Reload current folder?", yes_text="Reload", no_text="Cancel"):
            return

        ctrl_override = bool(QApplication.keyboardModifiers() & SKIP_METADATA_MODIFIER)

        skip_metadata, user_wants_scan = resolve_skip_metadata(
            ctrl_override=ctrl_override,
            total_files=len(self.files),
            folder_path=self.current_folder_path,
            parent_window=self,
            default_skip=DEFAULT_SKIP_METADATA,
            threshold=LARGE_FOLDER_WARNING_THRESHOLD
        )

        self.skip_metadata_mode = skip_metadata

        logger.info(
            f"[ForceReload] Reloading {self.current_folder_path}, skip_metadata={skip_metadata} "
            f"(ctrl={ctrl_override}, wants_scan={user_wants_scan}, default={DEFAULT_SKIP_METADATA})"
        )

        self.load_files_from_folder(self.current_folder_path, skip_metadata=skip_metadata, force=True)

    def _find_consecutive_ranges(self, indices: list[int]) -> list[tuple[int, int]]:
        """
        Given a sorted list of indices, returns a list of (start, end) tuples for consecutive ranges.
        Example: [1,2,3,7,8,10] -> [(1,3), (7,8), (10,10)]
        """
        if not indices:
            return []
        ranges = []
        start = prev = indices[0]
        for idx in indices[1:]:
            if idx == prev + 1:
                prev = idx
            else:
                ranges.append((start, prev))
                start = prev = idx
        ranges.append((start, prev))
        return ranges

    def select_all_rows(self) -> None:
        """
        Selects all rows in the file table efficiently using select_rows_range helper.
        Shows wait cursor during the operation.
        """
        if not self.model.files:
            return
        total = len(self.model.files)
        if total == 0:
            return
        selection_model = self.file_table_view.selectionModel()
        all_checked = all(f.checked for f in self.model.files)
        all_selected = False
        if selection_model is not None:
            selected_rows = set(idx.row() for idx in selection_model.selectedRows())
            all_selected = (len(selected_rows) == total)
        if all_checked and all_selected:
            logger.debug("[SelectAll] All files already selected in both checked and selection model. No action taken.")
            return
        with wait_cursor():
            logger.info(f"[SelectAll] Selecting all {total} rows.")
            self.file_table_view.select_rows_range(0, total - 1)
            self.file_table_view.anchor_row = 0
            QTimer.singleShot(20, self.update_files_label)

    def clear_all_selection(self) -> None:
        # If everything is already deselected, do nothing
        if not self.model.files or all(not f.checked for f in self.model.files):
            logger.info("[ClearAll] All files already unselected. No action taken.")
            return
        with wait_cursor():
            selection_model = self.file_table_view.selectionModel()
            selection_model.clearSelection()
            for file in self.model.files:
                file.checked = False
            self.file_table_view.viewport().update()
            self.update_files_label()
            self.generate_preview_names()
            self.clear_metadata_view()

    def invert_selection(self) -> None:
        """
        Inverts the selection in the file table efficiently using select_rows_range helper.
        Shows wait cursor during the operation.
        """
        if not self.model.files:
            self.set_status("No files to invert selection.", color="gray", auto_reset=True)
            return
        with wait_cursor():
            selection_model = self.file_table_view.selectionModel()
            current_selected = set(idx.row() for idx in selection_model.selectedRows())
            total = len(self.model.files)
            # Uncheck all selected, check all unselected
            for row, file in enumerate(self.model.files):
                file.checked = row not in current_selected
            # Find all checked rows (i.e. those that were previously unselected)
            checked_rows = [row for row, file in enumerate(self.model.files) if file.checked]
            checked_rows.sort()
            ranges = self._find_consecutive_ranges(checked_rows)
            selection_model.clearSelection()
            logger.info(f"[InvertSelection] Selecting {len(checked_rows)} rows in {len(ranges)} ranges.")
            for start, end in ranges:
                self.file_table_view.select_rows_range(start, end)
            self.file_table_view.anchor_row = checked_rows[0] if checked_rows else 0
            self.file_table_view.viewport().update()
            self.update_files_label()
            QTimer.singleShot(10, self.generate_preview_names)
            if checked_rows:
                def show_metadata_later():
                    last_row = checked_rows[-1]
                    file_item = self.model.files[last_row]
                    metadata = file_item.metadata or self.metadata_cache.get(file_item.full_path)
                    if isinstance(metadata, dict):
                        self.display_metadata(metadata, context="invert_selection")
                    else:
                        self.clear_metadata_view()
                QTimer.singleShot(20, show_metadata_later)
            else:
                self.clear_metadata_view()

    def sort_by_column(self, column: int, order=None) -> None:
        """
        Triggered when a header section is clicked.
        Sorts the file table immediately on first click,
        toggles sort order if the same column is clicked again.
        """
        if column == 0:
            return  # Do not sort the status/info column

        header = self.file_table_view.horizontalHeader()
        if header is None:
            return

        try:
            current_column = header.sortIndicatorSection()
            current_order = header.sortIndicatorOrder()

            if column == current_column:
                new_order = Qt.DescendingOrder if current_order == Qt.AscendingOrder else Qt.AscendingOrder
            else:
                new_order = Qt.AscendingOrder

            self.model.sort(column, new_order)
            header.setSortIndicator(column, new_order)
        except Exception as e:
            logger.error(f"Error in sort_by_column: {e}")

        # Add safe viewport update with guard
        viewport = self.file_table_view.viewport()
        if viewport:
            viewport.update()

    def restore_fileitem_metadata_from_cache(self) -> None:
        """
        After a folder reload (e.g. after rename), reassigns cached metadata
        to the corresponding FileItem objects in self.model.files.

        This allows icons and previews to remain consistent without rescanning.
        """
        restored = 0
        for file in self.model.files:
            cached = safe_get_metadata(self.metadata_cache, file.full_path)
            if isinstance(cached, dict) and cached:
                file.metadata = cached
                restored += 1
        logger.info(f"[MetadataRestore] Restored metadata from cache for {restored} files.")

    def rename_files(self) -> None:
        """
        Executes the batch rename process for checked files using active rename modules.

        This method:
        - Validates preconditions (folder, files, modules)
        - Renames files using the Renamer class
        - Reloads folder from disk (skipping metadata scan)
        - Restores checked state and metadata from cache
        - Refreshes preview and icon status
        - Prompts user to open folder if rename succeeded
        """
        if not self.current_folder_path:
            self.set_status("No folder selected.", color="orange")
            return

        selected_files = [f for f in self.model.files if f.checked]
        if not selected_files:
            self.set_status("No files selected.", color="gray")
            CustomMessageDialog.show_warning(
                self, "Rename Warning", "No files are selected for renaming."
            )
            return

        rename_data = self.rename_modules_area.get_all_data()
        modules_data = rename_data.get("modules", [])
        post_transform = rename_data.get("post_transform", {})

        logger.info(f"[Rename] Starting rename process for {len(selected_files)} files...")

        renamer = Renamer(
            files=selected_files,
            modules_data=modules_data,
            metadata_cache=self.metadata_cache,
            post_transform=post_transform,
            parent=self,
            conflict_callback=CustomMessageDialog.rename_conflict_dialog,
            validator=self.filename_validator
        )

        results = renamer.rename()

        checked_paths = {f.full_path for f in self.model.files if f.checked}

        renamed_count = 0
        for result in results:
            if result.success:
                renamed_count += 1
                item = next((f for f in self.files if f.full_path == result.old_path), None)
                if item:
                    item.filename = os.path.basename(result.new_path)
                    item.full_path = result.new_path
            elif result.skip_reason:
                logger.info(f"[Rename] Skipped: {result.old_path} — Reason: {result.skip_reason}")
            elif result.error:
                logger.error(f"[Rename] Error: {result.old_path} — {result.error}")

        self.set_status(f"Renamed {renamed_count} file(s).", color="green", auto_reset=True)
        logger.info(f"[Rename] Completed: {renamed_count} renamed out of {len(results)} total")

        self.last_action = "rename"
        self.load_files_from_folder(self.current_folder_path, skip_metadata=True)

        # Restore checked state
        restored_count = 0
        for path in checked_paths:
            file = self.find_fileitem_by_path(path)
            if file:
                file.checked = True
                restored_count += 1

        # Restore metadata from cache (to FileItem.metadata)
        self.restore_fileitem_metadata_from_cache()

        # After restoring checked state, regenerate preview with new filenames
        if self.last_action == "rename":
            logger.debug("[PostRename] Regenerating preview with new filenames and restored checked state")
            self.generate_preview_names()

        # Force update info icons in column 0
        for row in range(self.model.rowCount()):
            file_item = self.model.files[row]
            if self.metadata_cache.has(file_item.full_path):
                index = self.model.index(row, 0)
                rect = self.file_table_view.visualRect(index)
                self.file_table_view.viewport().update(rect)

        self.file_table_view.viewport().update()
        logger.debug(f"[Rename] Restored {restored_count} checked out of {len(self.model.files)} files")

        if renamed_count > 0:
            if CustomMessageDialog.question(
                self,
                "Rename Complete",
                f"{renamed_count} file(s) renamed.\nOpen the folder?",
                yes_text="Open Folder",
                no_text="Close"
            ):
                QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_folder_path))

    def should_skip_folder_reload(self, folder_path: str, force: bool = False) -> bool:
        """
        Checks if the given folder is already loaded and optionally prompts the user to reload.

        Parameters:
            folder_path (str): Folder path to check
            force (bool): If True, bypasses the check and allows reload

        Returns:
            bool: True if reload should be skipped, False otherwise
        """
        if force:
            return False

        normalized_new = os.path.abspath(os.path.normpath(folder_path))
        normalized_current = os.path.abspath(os.path.normpath(self.current_folder_path or ""))

        if normalized_new == normalized_current:
            result = CustomMessageDialog.question(
                self,
                "Reload Folder",
                f"The folder '{os.path.basename(folder_path)}' is already loaded.\n\nDo you want to reload it?",
                yes_text="Reload",
                no_text="Cancel"
            )
            return not result  # Skip reload if user pressed Cancel

        return False

    def handle_folder_select(self) -> None:
        """
        It loads files from the folder currently selected in the folder tree.
        If the Ctrl key is held, metadata scanning is skipped.

        Triggered when the user clicks the 'Select Folder' button.
        """
        self.last_action = "folder_select"

        index = self.folder_tree.currentIndex()
        if not index.isValid():
            logger.warning("No folder selected in tree view.")
            return

        folder_path = self.dir_model.filePath(index)

        if self.should_skip_folder_reload(folder_path):
            return  # skip if user pressed Cancel
        else:
            force_reload = True  # user pressed Reload

        self.clear_file_table("No folder selected")
        self.clear_metadata_view()

        # Load the full directory listing
        all_files = glob.glob(os.path.join(folder_path, "*"))
        valid_files = [
            f for f in all_files
            if os.path.splitext(f)[1][1:].lower() in ALLOWED_EXTENSIONS
        ]

        skip_metadata, use_extended = self.determine_metadata_mode()
        logger.debug(f"[Modifiers] skip_metadata={skip_metadata}, use_extended={use_extended}")
        self.force_extended_metadata = use_extended
        self.skip_metadata_mode = skip_metadata

        is_large = len(valid_files) > LARGE_FOLDER_WARNING_THRESHOLD
        logger.info(
            f"Tree-selected folder: {folder_path}, skip_metadata={skip_metadata}, extended={use_extended}, "
            f"(large={is_large}, default={DEFAULT_SKIP_METADATA})",
            extra={"dev_only": True}
        )
        logger.warning(f'-> skip_metadata passed to loader: {skip_metadata}')
        self.load_files_from_folder(folder_path, skip_metadata=skip_metadata, force=force_reload)

    def handle_browse(self) -> None:
        """
        Triggered when the user clicks the 'Browse Folder' button.
        Opens a folder selection dialog, checks file count, prompts
        user if the folder is large, and optionally skips metadata scan.

        Also updates the folder tree selection to reflect the newly selected folder.
        """
        self.last_action = "browse"

        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", "/")
        if not folder_path:
            logger.info("Folder selection canceled by user.")
            return

        if self.should_skip_folder_reload(folder_path):
            return  # skip if user pressed Cancel
        else:
            force_reload = True  # user pressed Reload

        self.clear_file_table("No folder selected")
        self.clear_metadata_view()

        all_files = glob.glob(os.path.join(folder_path, "*"))
        valid_files = [
            f for f in all_files
            if os.path.splitext(f)[1][1:].lower() in ALLOWED_EXTENSIONS
        ]

        skip_metadata, use_extended = self.determine_metadata_mode()
        logger.debug(f"[Modifiers] skip_metadata={skip_metadata}, use_extended={use_extended}")
        self.force_extended_metadata = use_extended
        self.skip_metadata_mode = skip_metadata

        is_large = len(valid_files) > LARGE_FOLDER_WARNING_THRESHOLD
        logger.debug("-" * 60)
        logger.info(
            f"Tree-selected folder: {folder_path}, skip_metadata={skip_metadata}, extended={use_extended}, "
            f"(large={is_large}, default={DEFAULT_SKIP_METADATA})",
            extra={"dev_only": True}
        )

        logger.warning(f"-> skip_metadata passed to loader: {skip_metadata}")
        self.load_files_from_folder(folder_path, skip_metadata=skip_metadata, force=force_reload)

        if hasattr(self, "dir_model") and hasattr(self, "folder_tree"):
            index = self.dir_model.index(folder_path)
            if index.isValid():
                self.folder_tree.setCurrentIndex(index)
                self.folder_tree.scrollTo(index)

    def get_file_items_from_folder(self, folder_path: str) -> list[FileItem]:
        all_files = glob.glob(os.path.join(folder_path, "*"))
        file_items = []
        for file_path in sorted(all_files):
            ext = os.path.splitext(file_path)[1][1:].lower()
            if ext in ALLOWED_EXTENSIONS:
                filename = os.path.basename(file_path)
                modified = datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                file_items.append(FileItem(filename, ext, modified, full_path=file_path))
        return file_items

    def prepare_file_table(self, file_items: list[FileItem]) -> None:
        """
        Prepares the file table with the provided FileItem objects.

        This method:
        1. Sets the model to the table
        2. Updates the files list
        3. Updates the preview_map
        4. Enables the header and delegates
        5. Updates labels and preview tables

        Parameters:
            file_items (list[FileItem]): The list of files to display
        """
        # Save current column widths if available
        saved_column_widths = {}
        if self.file_table_view.model() is not None:
            header = self.file_table_view.horizontalHeader()
            if header:
                for col in range(5):  # Assuming 5 columns
                    saved_column_widths[col] = header.sectionSize(col)
                logger.debug(f"[PrepareTable] Saved column widths: {saved_column_widths}")

        # Replace any placeholder model
        current_model = self.file_table_view.model()
        if not isinstance(current_model, FileTableModel):
            logger.info("[PrepareTable] Replacing placeholder model with regular FileTableModel")
            # Clear current model first
            self.file_table_view.setModel(None)
            QApplication.processEvents()  # Ensure UI updates

        # Set all files as unselected in the model
        for f in file_items:
            f.checked = False

        # Ensure the model is FileTableModel type
        if not isinstance(self.model, FileTableModel):
            logger.info("[PrepareTable] Creating new FileTableModel")
            self.model = FileTableModel(parent_window=self)

        self.model.set_files(file_items)
        self.files = file_items
        self.model.folder_path = self.current_folder_path
        self.preview_map.clear()
        self.preview_map = {f.filename: f for f in file_items}

        # Connect model to table and force refresh
        logger.info("[PrepareTable] Connecting model to TableView")
        self.file_table_view.setModel(self.model)
        QApplication.processEvents()
        self.file_table_view.reset()  # Force complete redraw
        QApplication.processEvents()

        # Enable header and delegates
        if hasattr(self, "header") and self.header is not None:
            logger.info("[PrepareTable] Enabling header")
            self.header.setEnabled(True)  # Enable file table header

        # Column settings
        header = self.file_table_view.horizontalHeader()
        if header:
            logger.info("[PrepareTable] Setting up columns")
            # Column 0: Info icon column (fixed small width)
            header.setMinimumSectionSize(23)  # PyQt5: only global min width supported
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            self.file_table_view.setColumnWidth(0, saved_column_widths.get(0, FILE_TABLE_COLUMN_WIDTHS["STATUS_COLUMN"]))

            # Column 1: Filename (wide, interactive)
            header.setSectionResizeMode(1, QHeaderView.Interactive)
            self.file_table_view.setColumnWidth(1, saved_column_widths.get(1, FILE_TABLE_COLUMN_WIDTHS["FILENAME_COLUMN"]))

            # Column 2: Filesize (new column)
            header.setSectionResizeMode(2, QHeaderView.Interactive)
            self.file_table_view.setColumnWidth(2, saved_column_widths.get(2, FILE_TABLE_COLUMN_WIDTHS["FILESIZE_COLUMN"]))

            # Column 3: Extension (type column)
            header.setSectionResizeMode(3, QHeaderView.Interactive)
            self.file_table_view.setColumnWidth(3, saved_column_widths.get(3, FILE_TABLE_COLUMN_WIDTHS["EXTENSION_COLUMN"]))

            # Column 4: Modified date
            header.setSectionResizeMode(4, QHeaderView.Stretch)
            if 4 in saved_column_widths:
                self.file_table_view.setColumnWidth(4, saved_column_widths[4])
            else:
                self.file_table_view.setColumnWidth(4, FILE_TABLE_COLUMN_WIDTHS["DATE_COLUMN"])

        # Enable hover delegate if it exists
        if hasattr(self.file_table_view, 'hover_delegate'):
            self.file_table_view.setItemDelegate(self.file_table_view.hover_delegate)
            self.file_table_view.hover_delegate.hovered_row = -1

        # Update labels and tables
        self.update_files_label()
        self.update_preview_tables_from_pairs([])
        self.rename_button.setEnabled(False)

        # Εξασφάλιση ότι οι μπάρες κύλισης εμφανίζονται σωστά
        self.file_table_view.setHorizontalScrollBarPolicy(QAbstractScrollArea.ScrollBarAsNeeded)
        self.file_table_view.setVerticalScrollBarPolicy(QAbstractScrollArea.ScrollBarAsNeeded)

        # Final UI update using QTimer to ensure all events have been processed
        QTimer.singleShot(10, lambda: self.file_table_view.viewport().update())
        QTimer.singleShot(30, lambda: self.file_table_view.updateGeometry())  # Εξασφαλίζει ότι το μέγεθος ενημερώνεται
        QTimer.singleShot(50, lambda: self.file_table_view.update())
        QTimer.singleShot(100, lambda: QApplication.processEvents())

        # If we're coming from a rename operation and have active modules, regenerate preview
        if self.last_action == "rename":
            logger.debug("[PrepareTable] Post-rename detected, preview will be updated after checked state restore")
            # Don't generate preview here - will be done after checked state is restored

    def load_files_from_folder(self, folder_path: str, skip_metadata: bool = False, force: bool = False):
        """
        Loads files from the specified folder into the file table.
        """
        normalized_new = os.path.abspath(os.path.normpath(folder_path))
        normalized_current = os.path.abspath(os.path.normpath(self.current_folder_path or ""))
        if normalized_new == normalized_current and not force:
            logger.info(f"[FolderLoad] Ignored reload of already loaded folder: {normalized_new}")
            self.set_status("Folder already loaded.", color="gray", auto_reset=True)
            return
        logger.info(f"Loading files from folder: {folder_path} (skip_metadata={skip_metadata})")
        saved_column_widths = {}
        header = self.file_table_view.horizontalHeader()
        if header:
            for col in range(5):
                saved_column_widths[col] = header.sectionSize(col)
            logger.debug(f"[FolderLoad] Saved column widths: {saved_column_widths}")
        is_reload = self.current_folder_path is not None
        if not (self.last_action == "rename" and skip_metadata):
            self.metadata_cache.clear()
        self.current_folder_path = folder_path
        self.check_selection_and_show_metadata()
        QApplication.processEvents()
        file_items = self.get_file_items_from_folder(folder_path)
        if not file_items:
            short_name = os.path.basename(folder_path.rstrip("/\\"))
            self.clear_file_table(f"No supported files in '{short_name}'", show_placeholder=True)
            self.clear_metadata_view()
            self.header.setEnabled(False)
            self.set_status("No supported files found.", color="orange", auto_reset=True)
            return
        # Αν υπάρχουν αρχεία, καθάρισε το table χωρίς placeholder
        self.clear_file_table(show_placeholder=False)
        self.prepare_file_table(file_items)
        self.file_table_view.horizontalHeader().setSortIndicator(1, Qt.AscendingOrder)
        header = self.file_table_view.horizontalHeader()
        if header and saved_column_widths:
            for col, width in saved_column_widths.items():
                if col != 4:
                    self.file_table_view.setColumnWidth(col, width)
            logger.debug(f"[FolderLoad] Restored column widths: {saved_column_widths}")
        self.file_table_view.setHorizontalScrollBarPolicy(QAbstractScrollArea.ScrollBarAsNeeded)
        self.file_table_view.setVerticalScrollBarPolicy(QAbstractScrollArea.ScrollBarAsNeeded)
        QTimer.singleShot(10, lambda: self.file_table_view.updateGeometry())
        QTimer.singleShot(50, lambda: QApplication.processEvents())
        self.clear_metadata_view()
        if skip_metadata:
            self.set_status("Metadata scan skipped.", color="gray", auto_reset=True)
            return
        self.set_status(f"Loading metadata for {len(file_items)} files...", color="blue")
        QTimer.singleShot(100, lambda: self.start_metadata_scan([f.full_path for f in file_items if f.full_path]))

    def start_metadata_scan(self, file_paths: list[str]) -> None:
        """
        Starts the metadata scan and shows the waiting dialog.

        This method:
        - Displays the custom metadata dialog with progress
        - Connects ESC/cancel event to worker cancellation
        - Enables wait cursor during scan
        - Delegates actual work to load_metadata_in_thread()
        """
        logger.warning("[DEBUG] start_metadata_scan CALLED")
        logger.debug(f"[MetadataScan] Launch with force_extended = {self.force_extended_metadata}")

        with wait_cursor():
            is_extended = self.force_extended_metadata
            self.loading_dialog = MetadataWaitingDialog(self, is_extended=is_extended)
            self.loading_dialog.set_status("Reading metadata...")
            self.loading_dialog.set_filename("")
            self.loading_dialog.set_progress(0, len(file_paths))

            # Connect cancel (ESC or manual close) to cancel logic
            self.loading_dialog.rejected.connect(self.cancel_metadata_loading)

            self.loading_dialog.show()
            QApplication.processEvents()

            self.load_metadata_in_thread(file_paths)

    def load_metadata_in_thread(self, file_paths: list[str]) -> None:
        """
        Initializes and starts a metadata loading thread using MetadataWorker.

        This method:
        - Creates a QThread and assigns a MetadataWorker to it
        - Passes the list of file paths and extended mode flag to the worker
        - Connects worker signals (progress, finished) to appropriate slots
        - Ensures signal `progress` updates the dialog safely via on_metadata_progress()
        - Starts the thread execution with the run_batch method

        Parameters
        ----------
        file_paths : list[str]
            A list of full file paths to extract metadata from.
        """
        logger.info(f"[MainWindow] Starting metadata thread for {len(file_paths)} files")

        # Create background thread
        self.metadata_thread = QThread()

        # Create worker object (inherits from QObject)
        self.metadata_worker = MetadataWorker(
            reader=self.metadata_loader,
            metadata_cache=self.metadata_cache,
            parent=self  # gives access to model for direct FileItem metadata assignment
        )

        # Set the worker's inputs
        self.metadata_worker.file_path = file_paths
        self.metadata_worker.use_extended = self.force_extended_metadata

        # Move worker to the thread context
        self.metadata_worker.moveToThread(self.metadata_thread)

        # Connect signals
        self.metadata_thread.started.connect(self.metadata_worker.run_batch)

        # update progress bar and message
        self.metadata_worker.progress.connect(self.on_metadata_progress)

        # Signal when finished
        self.metadata_worker.finished.connect(self.handle_metadata_finished)

        # Start thread execution
        self.metadata_thread.start()

    def start_metadata_scan_for_items(self, items: list[FileItem]) -> None:
        """
        Initiates threaded metadata scanning for a specific list of FileItems.

        This is a wrapper around the existing start_metadata_scan() method, converting
        FileItem objects into file paths. It is used when metadata should be loaded for
        a subset of files (e.g. from right-click menu).

        Parameters:
            items (list[FileItem]): List of files to scan metadata for.
        """
        file_paths = [item.full_path for item in items if item.full_path]
        if not file_paths:
            self.set_status("No valid files to scan.", color="gray", auto_reset=True)
            return

        # For many files, use wait cursor during the setup phase
        if len(file_paths) >= 100:
            with wait_cursor():
                self.set_status(f"Loading metadata for {len(file_paths)} file(s)...", color="blue")
                QTimer.singleShot(200, lambda: self.start_metadata_scan(file_paths))
        else:
            self.set_status(f"Loading metadata for {len(file_paths)} file(s)...", color="blue")
            QTimer.singleShot(200, lambda: self.start_metadata_scan(file_paths))

    def shortcut_load_metadata(self) -> None:
        """
        Loads standard (non-extended) metadata for currently selected files.

        Uses the custom selected_rows from the file_table_view, not Qt's selectionModel().
        """
        selected_rows = self.file_table_view.selected_rows
        selected = [self.model.files[r] for r in selected_rows if 0 <= r < len(self.model.files)]

        self.force_extended_metadata = False
        with wait_cursor():
            self.metadata_loader.load(selected, force=False, cache=self.metadata_cache)

        if selected:
            last = selected[-1]
            metadata = last.metadata or self.metadata_cache.get(last.full_path)
            if isinstance(metadata, dict):
                self.display_metadata(metadata, context="shortcut_load_metadata")

        for file in selected:
            row = self.model.files.index(file)
            for col in range(self.model.columnCount()):
                idx = self.model.index(row, col)
                self.file_table_view.viewport().update(self.file_table_view.visualRect(idx))

    def shortcut_load_extended_metadata(self) -> None:
        """
        Loads extended metadata for selected files via custom selection system.

        Uses shift+Ctrl+E to trigger. Shows wait dialog if multiple files.
        """
        if self.is_running_metadata_task():
            logger.warning("[Shortcut] Metadata scan already running — shortcut ignored.")
            return

        selected_rows = self.file_table_view.selected_rows
        selected = [self.model.files[r] for r in selected_rows if 0 <= r < len(self.model.files)]

        if not selected:
            self.set_status("No files selected.", color="gray", auto_reset=True)
            return

        files_to_load = [
            f for f in selected
            if not self.metadata_loader.has_extended(f.full_path, self.metadata_cache)
        ]

        if files_to_load and not self.confirm_large_files(files_to_load):
            return

        self.force_extended_metadata = True

        if files_to_load:
            if len(files_to_load) > 1:
                self.start_metadata_scan_for_items(files_to_load)
                return
            else:
                with wait_cursor():
                    self.metadata_loader.load(files_to_load, force=False, cache=self.metadata_cache, use_extended=True)

        last = selected[-1]
        metadata = last.metadata or self.metadata_cache.get(last.full_path)
        if isinstance(metadata, dict) and metadata:
            self.display_metadata(metadata, context="shortcut_load_extended_metadata")

    def display_metadata(self, metadata: Optional[dict], context: str = "") -> None:
        """
        Validates and displays metadata safely in the UI.

        Args:
            metadata (dict or None): The metadata to display.
            context (str): Optional source for logging (e.g. 'doubleclick', 'worker')
        """
        if not isinstance(metadata, dict) or not metadata:
            logger.warning(f"[display_metadata] Invalid metadata ({type(metadata)}) from {context}: {metadata}")
            self.clear_metadata_view()
            return

        self._render_metadata_view(metadata)
        self.toggle_expand_button.setEnabled(True)  # Enable expand/collapse button
        # If metadata_tree_view has a header, enable it
        if hasattr(self.metadata_tree_view, 'header') and callable(self.metadata_tree_view.header):
            header = self.metadata_tree_view.header()
            if header:
                header.setEnabled(True)

    def _render_metadata_view(self, metadata: dict) -> None:
        """
        Actually builds the metadata tree and displays it.
        Assumes metadata is a non-empty dict.

        Includes fallback protection in case called with invalid metadata.
        """
        if not isinstance(metadata, dict):
            logger.error(f"[render_metadata_view] Called with invalid metadata: {type(metadata)} → {metadata}")
            self.clear_metadata_view()
            return

        try:
            display_data = dict(metadata)
            filename = metadata.get("FileName")
            if filename:
                display_data["FileName"] = filename

            tree_model = build_metadata_tree_model(display_data)
            self.metadata_tree_view.setModel(tree_model)
            self.metadata_tree_view.expandAll()
            self.toggle_expand_button.setChecked(True)
            self.toggle_expand_button.setText("Collapse All")

        except Exception as e:
            logger.exception(f"[render_metadata_view] Unexpected error while rendering: {e}")
            self.clear_metadata_view()

    def check_selection_and_show_metadata(self) -> None:
        """
        Displays metadata of the currently selected (focused) file in the table view.
        If no selection or no metadata exists, clears the metadata tree.
        Uses guards for None objects.
        """
        selection_model = getattr(self.file_table_view, 'selectionModel', lambda: None)()
        if selection_model is None:
            self.clear_metadata_view()
            return

        try:
            selected_rows = selection_model.selectedRows()
            if not selected_rows:
                self.clear_metadata_view()
                return

            # Prefer currentIndex if it's valid and selected
            current_index = selection_model.currentIndex()
            target_index = None

            if (
                current_index.isValid()
                and current_index in selected_rows
                and 0 <= current_index.row() < len(self.model.files)
            ):
                target_index = current_index
            else:
                target_index = selected_rows[0]  # fallback

            if 0 <= target_index.row() < len(self.model.files):
                file_item = self.model.files[target_index.row()]
                metadata = file_item.metadata or safe_get_metadata(self.metadata_cache, file_item.full_path)

                if isinstance(metadata, dict) and metadata:
                    display_metadata = dict(metadata)
                    display_metadata["FileName"] = file_item.filename
                    self.display_metadata(display_metadata, context="check_selection_and_show_metadata")
                    return
        except Exception as e:
            logger.error(f"Error showing metadata: {e}")

        self.clear_metadata_view()

    def reload_current_folder(self) -> None:
        # Optional: adjust if flags need to be preserved
        if self.current_folder_path:
            self.load_files_from_folder(self.current_folder_path, skip_metadata=False)

    def update_module_dividers(self) -> None:
        for index, module in enumerate(self.rename_modules):
            if hasattr(module, "divider"):
                module.divider.setVisible(index > 0)

    def handle_header_toggle(self, _) -> None:
        """
        Triggered when column 0 header is clicked.
        Toggles selection and checked state of all files (efficient, like Ctrl+A).
        """
        if not self.model.files:
            return

        total = len(self.model.files)
        all_selected = all(file.checked for file in self.model.files)
        selection_model = self.file_table_view.selectionModel()

        with wait_cursor():
            if all_selected:
                # Unselect all
                selection_model.clearSelection()
                for file in self.model.files:
                    file.checked = False
            else:
                # Select all efficiently
                self.file_table_view.select_rows_range(0, total - 1)
                for file in self.model.files:
                    file.checked = True
                self.file_table_view.anchor_row = 0

            self.file_table_view.viewport().update()
            self.update_files_label()
            self.generate_preview_names()
            self.check_selection_and_show_metadata()

    def generate_preview_names(self) -> None:
        """
        Generate new preview names for all selected files using current rename modules.
        Updates the preview map and UI elements accordingly.
        """
        selected_files = [f for f in self.model.files if f.checked]
        rename_data = self.rename_modules_area.get_all_data()
        modules_data = rename_data.get("modules", [])
        post_transform = rename_data.get("post_transform", {})

        logger.debug(f"[Preview] modules_data: {modules_data}")
        logger.debug(f"[Preview] post_transform: {post_transform}")

        # Fast path: if all modules are no-op (e.g. Specified Text is empty and no post_transform)
        is_noop = (
            not modules_data or
            all(
                m.get("type") == "Specified Text" and not m.get("text")
                for m in modules_data
            ) and not post_transform
        )

        self.preview_map.clear()
        self.preview_map = {file.filename: file for file in selected_files}

        if is_noop:
            logger.debug("[Preview] Fast path: no-op modules, skipping preview/validation.")
            # No preview/validation needed, just identity mapping
            name_pairs = [(f.filename, f.filename) for f in selected_files]
            self.update_preview_tables_from_pairs(name_pairs)
            self.rename_button.setEnabled(False)
            self.rename_button.setToolTip("No changes to apply")
            return

        logger.debug("[Preview] Running full preview/validation for selected files.")

        name_pairs = []

        for idx, file in enumerate(selected_files):
            try:
                # Split filename into basename and extension
                import os
                basename, extension = os.path.splitext(file.filename)

                # Apply modules to basename only
                new_fullname = apply_rename_modules(modules_data, idx, file, self.metadata_cache)
                # Αφαίρεσε το extension αν υπάρχει ήδη (ώστε να δουλεύει μόνο με το basename)
                if extension and new_fullname.lower().endswith(extension.lower()):
                    new_basename = new_fullname[:-(len(extension))]
                else:
                    new_basename = new_fullname

                logger.debug(f"Modules: {modules_data}")
                logger.debug(f"Output from modules: {new_basename}")

                # Apply name transform (case, separator) to basename only
                if NameTransformModule.is_effective(post_transform):
                    new_basename = NameTransformModule.apply_from_data(post_transform, new_basename)
                    logger.debug(f"Transform applied: {new_basename}")

                # Validate only the basename
                from utils.validation import is_valid_filename_text
                if not is_valid_filename_text(new_basename):
                    logger.warning(f"Invalid basename generated: {new_basename}")
                    name_pairs.append((file.filename, file.filename))
                    continue
                # Add extension (with dot) only at the end
                if extension:
                    new_name = f"{new_basename}{extension}"
                else:
                    new_name = new_basename
                logger.debug(f"[Preview] {file.filename} -> {new_name}")
                name_pairs.append((file.filename, new_name))
                logger.debug(f"[Preview] Generating for {[f.filename for f in selected_files]}", extra={"dev_only": True})

            except Exception as e:
                logger.warning(f"Failed to generate preview for {file.filename}: {e}")
                name_pairs.append((file.filename, file.filename))

        # Map new name → FileItem only when name changed
        for old_name, new_name in name_pairs:
            if old_name != new_name:
                file_item = self.preview_map.get(old_name)
                if file_item:
                    self.preview_map[new_name] = file_item
                    logger.debug(f"[Preview] preview_map updated: {old_name} -> {new_name}")

        self.update_preview_tables_from_pairs(name_pairs)

        # Enable rename button if any name has changed
        valid_pairs = [p for p in name_pairs if p[0] != p[1]]
        self.rename_button.setEnabled(bool(valid_pairs))
        tooltip_msg = f"{len(valid_pairs)} files will be renamed." if valid_pairs else "No changes to apply"
        self.rename_button.setToolTip(tooltip_msg)
        logger.debug(f"[PreviewMap] Keys: {list(self.preview_map.keys())}", extra={"dev_only": True})

    def compute_max_filename_width(self, file_list: list[FileItem]) -> int:
        """
        Calculates the ideal column width in pixels based on the longest filename.

        The width is estimated as: 8 * length of longest filename,
        clamped between 250 and 1000 pixels. This ensures a readable but bounded width
        for the filename column in the preview table.

        Args:
            file_list (list[FileItem]): A list of FileItem instances to analyze.

        Returns:
            int: Pixel width suitable for displaying the longest filename.
        """
        # Get the length of the longest filename (in characters)
        max_len = max((len(file.filename) for file in file_list), default=0)

        # Convert length to pixels (roughly 8 px per character), then clamp
        pixel_width = 8 * max_len
        clamped_width = min(max(pixel_width, 250), 1000)

        logger.debug(f'Longest filename length: {max_len} chars -> width: {clamped_width} px (clamped)')
        return clamped_width

    def center_window(self) -> None:
        """
        Centers the application window on the user's screen.

        It calculates the screen's center point and moves the window
        so its center aligns with that. This improves the initial UX
        by avoiding awkward off-center placement.

        Returns:
            None
        """
        # Get current geometry of the window
        window_geometry = self.frameGeometry()

        # Get the center point of the available screen
        screen_center = QDesktopWidget().availableGeometry().center()

        # Move the window geometry so that its center aligns with screen center
        window_geometry.moveCenter(screen_center)

        # Reposition the window's top-left corner to match the new centered geometry
        self.move(window_geometry.topLeft())

        logger.debug("Main window centered on screen.")

    def confirm_large_folder(self, file_list: list[str], folder_path: str) -> bool:
        """
        Warns if folder is big and asks user if they want to scan metadata.
        Returns True to scan metadata, False to skip only metadata.
        """
        if len(file_list) > LARGE_FOLDER_WARNING_THRESHOLD:
            proceed = CustomMessageDialog.question(
                self,
                "Large Folder",
                f"This folder contains {len(file_list)} supported files.\n"
                "Metadata scan may take time. Scan metadata?",
                yes_text="Scan",
                no_text="Skip Metadata"
            )
            logger.info(
                "Large-folder dialog: user chose %s metadata scan for %s",
                "scan" if proceed else "skip",
                folder_path
            )
            return proceed
        return True

    def check_large_files(self, files: list[FileItem]) -> list[FileItem]:
        """
        Returns a list of files over the configured size threshold (in MB).
        """
        limit_bytes = EXTENDED_METADATA_SIZE_LIMIT_MB * 1024 * 1024
        large_files = []
        for f in files:
            try:
                if os.path.getsize(f.full_path) > limit_bytes:
                    large_files.append(f)
            except Exception as e:
                logger.warning(f"[SizeCheck] Could not get size for {f.filename}: {e}")
        return large_files

    def confirm_large_files(self, files: list[FileItem]) -> bool:
        """
        Checks for large files and asks the user whether to proceed.
        Returns False if user cancels. True if OK.
        """
        large_files = self.check_large_files(files)
        if not large_files:
            return True

        names = "\n".join(f.filename for f in large_files[:5])
        if len(large_files) > 5:
            names += "\n..."

        if not CustomMessageDialog.question(
            self,
            "Warning: Large Files",
            f"{len(large_files)} of the selected files are larger than {EXTENDED_METADATA_SIZE_LIMIT_MB} MB.\n\n"
            f"{names}\n\n"
            "Extended metadata scan may be slow or fail. Do you want to continue?",
            yes_text="Continue",
            no_text="Cancel"
        ):
            return False

        return True

    def update_files_label(self) -> None:
        """
        Updates the UI label that displays the count of selected files.

        If no files are loaded, the label shows a default "Files".
        Otherwise, it shows how many files are currently selected
        out of the total number loaded.
        """
        total = len(self.model.files)
        selected = sum(1 for f in self.model.files if f.checked) if total else 0

        if total == 0:
            self.files_label.setText("Files (0)")
        else:
            self.files_label.setText(f"Files ({total} loaded, {selected} selected)")

    def fade_status_to_ready(self) -> None:
        """
        Fades out the current status, then shows 'Ready' without fading.
        """
        self.status_fade_anim.stop()
        self.status_fade_anim.start()

        def show_ready_clean():
            if hasattr(self, "status_fade_anim"):
                self.status_fade_anim.stop()
            if hasattr(self, "status_opacity_effect"):
                self.status_opacity_effect.setOpacity(1.0)
            self.status_label.setStyleSheet("")  # reset color
            self.status_label.setText("Ready")

        QTimer.singleShot(self.status_fade_anim.duration(), show_ready_clean)

    def set_status(self, text: str, color: str = "", auto_reset: bool = False, reset_delay: int = 3000) -> None:
        """
        Sets the status label text and optional color. Supports auto-reset with fade effect.
        """
        # Always reset opacity to full when setting new text
        if hasattr(self, "status_opacity_effect"):
            self.status_opacity_effect.setOpacity(1.0)

        self.status_label.setText(text)
        if color:
            self.status_label.setStyleSheet(f"color: {color};")
        else:
            self.status_label.setStyleSheet("")

        if auto_reset:
            if hasattr(self, "_status_timer") and self._status_timer:
                self._status_timer.stop()
            else:
                self._status_timer = QTimer(self)

            self._status_timer.setSingleShot(True)
            self._status_timer.timeout.connect(lambda: self.fade_status_to_ready())
            self._status_timer.start(reset_delay)

    def get_identity_name_pairs(self) -> list[tuple[str, str]]:
        """
        Returns a list of (original, new) filename pairs, where each 'new' filename is the same as the 'original' filename.
        This is used to populate the preview tables when the user has not yet configured any rename modules.
        """
        return [
            (file.filename, file.filename)
            for file in self.model.files
            if file.checked
        ]

    def update_preview_tables_from_pairs(self, name_pairs: list[tuple[str, str]]) -> None:
        self.preview_old_name_table.setRowCount(0)
        self.preview_new_name_table.setRowCount(0)
        self.preview_icon_table.setRowCount(0)

        if not name_pairs:
            self.status_label.setText("No files selected.")
            return

        all_names = [name for pair in name_pairs for name in pair]
        max_width = max((self.fontMetrics().horizontalAdvance(name) for name in all_names), default=250)
        adjusted_width = max(316, max_width) + 100
        self.preview_old_name_table.setColumnWidth(0, adjusted_width)
        self.preview_new_name_table.setColumnWidth(0, adjusted_width)

        seen, duplicates = set(), set()
        for _, new in name_pairs:
            if new in seen:
                duplicates.add(new)
            else:
                seen.add(new)

        stats = {"unchanged": 0, "invalid": 0, "duplicate": 0, "valid": 0}

        for row, (old_name, new_name) in enumerate(name_pairs):
            self.preview_old_name_table.insertRow(row)
            self.preview_new_name_table.insertRow(row)
            self.preview_icon_table.insertRow(row)

            old_item = QTableWidgetItem(old_name)
            new_item = QTableWidgetItem(new_name)

            if old_name == new_name:
                status = "unchanged"
                tooltip = "Unchanged filename"
            else:
                is_valid, _ = self.filename_validator.is_valid_filename(new_name)
                if not is_valid:
                    status = "invalid"
                    tooltip = "Invalid filename"
                elif new_name in duplicates:
                    status = "duplicate"
                    tooltip = "Duplicate name"
                else:
                    status = "valid"
                    tooltip = "Ready to rename"

            file_item = self.preview_map.get(new_name)
            if not file_item:
                continue

            if not getattr(file_item, "metadata", None):
                tooltip += " [No metadata available]"

            stats[status] += 1

            icon_item = QTableWidgetItem()
            icon_path = self.icon_paths.get(status)
            if icon_path:
                icon = QIcon(QPixmap(icon_path).scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                icon_item.setIcon(icon)
            icon_item.setToolTip(tooltip)

            self.preview_old_name_table.setItem(row, 0, old_item)
            self.preview_new_name_table.setItem(row, 0, new_item)
            self.preview_icon_table.setItem(row, 0, icon_item)

        status_msg = (
            f"<img src='{self.icon_paths['valid']}' width='14' height='14' style='vertical-align: middle';/>"
            f"<span style='color:#ccc;'> Valid: {stats['valid']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{self.icon_paths['unchanged']}' width='14' height='14' style='vertical-align: middle';/>"
            f"<span style='color:#ccc;'> Unchanged: {stats['unchanged']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{self.icon_paths['invalid']}' width='14' height='14' style='vertical-align: middle';/>"
            f"<span style='color:#ccc;'> Invalid: {stats['invalid']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{self.icon_paths['duplicate']}' width='14' height='14' style='vertical-align: middle';/>"
            f"<span style='color:#ccc;'> Duplicates: {stats['duplicate']}</span>"
        )
        self.status_label.setText(status_msg)

    def on_metadata_progress(self, current: int, total: int) -> None:
        """
        Slot connected to the `progress` signal of the MetadataWorker.

        This method updates the loading dialog's progress bar and message label
        as metadata files are being processed in the background.

        Args:
            current (int): Number of files analyzed so far (1-based index).
            total (int): Total number of files to analyze.
        """
        if self.metadata_worker is None:
            logger.warning("Progress signal received after worker was already cleaned up — ignoring.")
            return

        logger.debug(f"Metadata progress update: {current} of {total}")

        if getattr(self, "loading_dialog", None):
            self.loading_dialog.set_progress(current, total)

            # Show filename of current file (current-1 because progress starts at 1)
            if 0 <= current - 1 < len(self.metadata_worker.file_path):
                filename = os.path.basename(self.metadata_worker.file_path[current - 1])
                self.loading_dialog.set_filename(filename)
            else:
                self.loading_dialog.set_filename("")

            # Optional: update the label only once at the beginning
            if current == 1:
                self.loading_dialog.set_status("Reading metadata...")

            # Force immediate UI refresh
            QApplication.processEvents()
        else:
            logger.warning("Loading dialog not available during progress update — skipping UI update.")

    def handle_metadata_finished(self) -> None:
        """
        Slot called when the MetadataWorker finishes processing.

        This method:
        - Closes the loading dialog
        - Updates file info icons based on metadata availability and type (fast/extended)
        - Regenerates preview names
        - Displays metadata for selected file (if exactly one is selected)
        - Cleans up metadata worker and thread
        """
        logger.warning(f"[MainWindow] handle_metadata_finished() in thread: {threading.current_thread().name}")
        logger.debug("[MainWindow] Metadata loading finished.", extra={"dev_only": True})

        # --- 1. Close loading dialog if visible
        if getattr(self, "loading_dialog", None):
            logger.debug("[MainWindow] Closing loading dialog.")
            self.loading_dialog.deleteLater()
            self.loading_dialog = None

        # --- 2. Cancel cursor and internal flags
        self.force_extended_metadata = False
        self._restore_cursor()

        # --- 3. Validate file model before proceeding
        if not hasattr(self, "model") or not getattr(self.model, "files", None):
            logger.warning("[MainWindow] File model is not initialized or empty.")
            return

        # --- 4. Update icons based on metadata status
        from widgets.view_helpers import update_info_icon  # move to top if static
        for row in range(self.model.rowCount()):
            file_item = self.model.files[row]
            if self.metadata_cache.has(file_item.full_path):
                try:
                    is_extended = self.metadata_cache.is_extended(file_item.full_path)
                    logger.debug(f"[MainWindow] {file_item.filename}: is_extended = {is_extended}")
                    status = "extended" if is_extended else "loaded"
                except Exception as e:
                    logger.warning(f"[MainWindow] Failed to determine metadata type for {file_item.filename}: {e}")
                    status = "loaded"

                update_info_icon(self.file_table_view, self.model, file_item.full_path)

        # --- 5. Regenerate preview names
        self.generate_preview_names()

        # --- 6. Show metadata for single file selection
        selected_files = self.get_selected_files()
        if len(selected_files) == 1:
            file_item = selected_files[0]
            metadata = file_item.metadata or self.metadata_cache.get(file_item.full_path)

            if isinstance(metadata, dict) and metadata:
                logger.debug(f"[MainWindow] Displaying metadata for {file_item.full_path}")
                self.display_metadata(metadata, context="handle_metadata_finished")
            else:
                logger.warning(f"[MainWindow] No valid metadata to display for {file_item.filename}")
        else:
            logger.debug("[MainWindow] Metadata view not updated — selection is empty or multiple.")

        # --- 7. Cleanup thread and worker
        self.cleanup_metadata_worker()

    def cleanup_metadata_worker(self) -> None:
        """
        Safely shuts down and deletes the metadata worker and its thread.

        This method ensures that:
        - The thread is properly stopped (using quit + wait)
        - The worker and thread are deleted using deleteLater
        - All references are cleared to avoid leaks or crashes
        """
        if self.metadata_thread:
            if self.metadata_thread.isRunning():
                logger.debug("[MainWindow] Quitting metadata thread...")
                self.metadata_thread.quit()
                self.metadata_thread.wait()
                logger.debug("[MainWindow] Metadata thread has stopped.")

            self.metadata_thread.deleteLater()
            self.metadata_thread = None
            logger.debug("[MainWindow] Metadata thread deleted.")

        if self.metadata_worker:
            self.metadata_worker.deleteLater()
            self.metadata_worker = None
            logger.debug("[MainWindow] Metadata worker deleted.")

        self.force_extended_metadata = False

    def get_selected_files(self) -> list:
        """
        Returns a list of FileItem objects currently selected (blue-highlighted) in the table view.
        Uses guards for None objects.
        """
        selection_model = getattr(self.file_table_view, 'selectionModel', lambda: None)()
        if selection_model is None:
            return []

        try:
            selected_indexes = selection_model.selectedRows()
            return [self.model.files[i.row()] for i in selected_indexes if 0 <= i.row() < len(self.model.files)]
        except Exception as e:
            logger.error(f"Error getting selected files: {e}")
            return []

    def find_fileitem_by_path(self, path: str) -> Optional[FileItem]:
        """
        Finds and returns the FileItem corresponding to the given file path.

        Args:
            path (str): Full file path.

        Returns:
            FileItem or None
        """
        for file_item in self.model.files:
            if file_item.full_path == path:
                return file_item
        return None

    def _restore_cursor(self) -> None:
        """
        Restores the cursor to its default appearance.

        This method is used after a metadata scan or any long-running operation
        that sets the cursor to a busy state. Because override cursors are pushed
        onto a stack, we must pop all of them off to fully restore the default.

        After restoring the cursor, we manually process events to ensure that
        the cursor is visually updated immediately.
        """
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        # Ensure the change is reflected immediately
        QApplication.processEvents()

    def cancel_metadata_loading(self, retry_count: int = 0) -> None:
        """
        Called when the user presses ESC or closes the metadata dialog during scan.

        This method:
        - Restores the mouse cursor immediately
        - Updates the UI to inform user that cancellation is in progress
        - Attempts to cancel the active MetadataWorker
        - Retries cancel up to 3 times if worker has not yet been created

        Parameters
        ----------
        retry_count : int, optional
            Internal counter for retry attempts if the worker is not yet available.
        """
        logger.info("[MainWindow] User requested cancellation of metadata scan.")

        # --- 1. Restore wait cursor immediately
        QApplication.restoreOverrideCursor()

        # --- 2. Inform user via dialog, if visible
        dialog = getattr(self, "loading_dialog", None)
        if dialog:
            dialog.set_status("Canceling metadata scan…")
            dialog.set_filename("")  # Optional: clear filename during cancel

            # Schedule dialog close after 1 sec
            QTimer.singleShot(1000, dialog.deleteLater)
            QTimer.singleShot(1000, lambda: setattr(self, "loading_dialog", None))
        else:
            logger.debug("[MainWindow] Cancel requested but loading dialog not found.")

        # --- 3. Attempt to cancel the metadata worker
        worker = getattr(self, "metadata_worker", None)
        if worker:
            if not getattr(worker, "_cancelled", False):
                logger.debug("[MainWindow] Calling metadata_worker.cancel()")
                worker.cancel()
            else:
                logger.info("[MainWindow] MetadataWorker already marked as cancelled.")
        else:
            # --- Retry if the worker hasn't been created yet
            if retry_count < 3:
                logger.warning(f"[MainWindow] metadata_worker is None — retrying cancel in 150ms (attempt {retry_count + 1})")
                QTimer.singleShot(150, lambda: self.cancel_metadata_loading(retry_count + 1))
            else:
                logger.error("[MainWindow] Cancel failed: metadata_worker was never created after multiple attempts.")

    def on_metadata_error(self, message: str) -> None:
        """
        Handles unexpected errors during metadata loading.

        - Restores the UI cursor
        - Closes the progress dialog
        - Cleans up worker and thread
        - Shows an error message to the user

        Args:
            message (str): The error message to display.
        """
        logger.error(f"Metadata error: {message}")

        # 1. Restore busy cursor
        self._restore_cursor()

        # 2. Close the loading dialog
        if getattr(self, "loading_dialog", None):
            logger.info("Closing loading dialog due to error.")
            self.loading_dialog.close()
            self.loading_dialog = None
        else:
            logger.warning("No loading dialog found during error handling.")

        # 3. Clean up worker and thread
        self.cleanup_metadata_worker()

        # 4. Notify user
        CustomMessageDialog.show_warning(self, "Metadata Error", f"Failed to read metadata:\n\n{message}")

    def is_running_metadata_task(self) -> bool:
        """
        Returns True if a metadata thread is currently active.

        This helps prevent overlapping metadata scans by checking if
        a previous background task is still running.

        Returns
        -------
        bool
            True if metadata_thread exists and is running, False otherwise.
        """
        running = (
            getattr(self, "metadata_thread", None) is not None
            and self.metadata_thread.isRunning()
        )
        logger.debug(f"Metadata task running? {running}")

        return (
            self.metadata_thread is not None and
            self.metadata_thread.isRunning()
        )

    def on_table_row_clicked(self, index: QModelIndex) -> None:
        """
        Triggered when a user clicks on a file row in the table.
        Displays the metadata for the selected file in the right panel.
        """
        if not self.model.files:
            logger.info("No files in model — click ignored.")
            return

        row = index.row()
        if row < 0 or row >= len(self.model.files):
            logger.warning("Invalid row clicked (out of range). Ignored.")
            return

        # Ignore checkbox column clicks
        if index.column() == 0:
            return

        self.check_selection_and_show_metadata()

    def prompt_file_conflict(self, target_path: str) -> str:
        """
        Ask user what to do if the target file already exists.
        Returns: 'overwrite', 'skip', or 'cancel'
        """
        response = CustomMessageDialog.choice(
            self,
            "File Exists",
            f"The file:\n{target_path}\nalready exists. What would you like to do?",
            buttons={
                "Overwrite": "overwrite",
                "Skip": "skip",
                "Cancel": "cancel"
            }
        )
        return response

    def toggle_metadata_expand(self, checked: bool) -> None:
        if checked:
            self.metadata_tree_view.expandAll()
            self.toggle_expand_button.setText("Collapse All")
        else:
            self.metadata_tree_view.collapseAll()
            self.toggle_expand_button.setText("Expand All")

    def clear_file_table(self, message: str = "No folder selected", show_placeholder: bool = True) -> None:
        """
        Clears the file table and shows a placeholder message if requested.
        Uses guards for None objects.
        """
        logger.info(f"[ClearFileTable] Clearing table and displaying message: {message}")
        self.clear_metadata_view()
        self.file_table_view.setModel(None)
        QApplication.processEvents()
        self.model.set_files([])
        if show_placeholder:
            self.show_file_table_placeholder(message)
        if hasattr(self, "header") and self.header is not None:
            self.header.setEnabled(False)
        self.update_files_label()

        # Add guards for viewport update
        viewport = self.file_table_view.viewport()
        if viewport:
            QTimer.singleShot(10, lambda: viewport.update())
        QTimer.singleShot(50, lambda: self.file_table_view.update())

    def show_file_table_placeholder(self, message: str = "No files loaded") -> None:
        """
        Displays a placeholder row in the file table with a message.

        This method creates a temporary model with a placeholder message.
        Important: This temporary model will be replaced later by the regular
        FileTableModel when files are loaded.

        Parameters:
            message (str): The message to display in the placeholder row
        """
        # Save column widths before changing the model
        saved_column_widths = {}
        header = self.file_table_view.horizontalHeader()
        if header:
            for col in range(5):  # Assuming 5 columns
                saved_column_widths[col] = header.sectionSize(col)
            logger.debug(f"[Placeholder] Saved column widths: {saved_column_widths}")

        # Save reference to current model
        current_model = self.file_table_view.model()

        # Delete current model if it's not the FileTableModel
        if current_model and current_model is not self.model:
            logger.info(f"[Placeholder] Removing current model of type: {type(current_model)}")
            self.file_table_view.setModel(None)
            QApplication.processEvents()  # Ensure UI updates

        # Create placeholder model
        placeholder_model = QStandardItemModel()
        placeholder_model.setHorizontalHeaderLabels(["", "Filename", "Size", "Type", "Modified"])

        # Create row items
        row = [
            QStandardItem(),
            QStandardItem(message),
            QStandardItem(),
            QStandardItem(),
            QStandardItem()
        ]

        # Style placeholder items
        for i, item in enumerate(row):
            font = item.font()
            font.setItalic(True)
            item.setFont(font)

            item.setForeground(QColor("#888888"))  # Χρήση χρώματος αντί για Qt.gray
            item.setEnabled(False)  # Disable placeholder items
            item.setSelectable(False)

            # Optional: center align only the message column
            if i == 1:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignCenter)

        placeholder_model.appendRow(row)

        # Save the placeholder model as a property so we can
        # recognize it later and replace it properly
