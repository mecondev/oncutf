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
    QSplitter, QFrame, QScrollArea, QTableWidget, QTreeView, QFileDialog,
    QFileSystemModel, QAbstractItemView,  QSizePolicy, QHeaderView, QTableWidgetItem,
    QDesktopWidget, QGraphicsOpacityEffect, QMenu, QShortcut
)
from PyQt5.QtCore import (
    Qt, QDir, QUrl, QThread, QTimer, QModelIndex, QPropertyAnimation, QMetaObject,
    QItemSelection, QItemSelectionRange, QItemSelectionModel, QElapsedTimer
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
from utils.icon_cache import load_preview_status_icons

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
from widgets.metadata_tree_view import MetadataTreeView
from widgets.metadata_waiting_dialog import MetadataWaitingDialog
from widgets.rename_modules_area import RenameModulesArea
from widgets.custom_tree_view import CustomTreeView


from config import *

# Setup Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)

import contextlib
import re

@contextlib.contextmanager
def wait_cursor():
    QApplication.setOverrideCursor(Qt.WaitCursor)  # type: ignore
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        """Initializes the main window and sets up the layout."""
        super().__init__()

        # --- Attributes initialization ---
        self.metadata_thread = None
        self.metadata_worker = None
        self.metadata_cache = MetadataCache()
        self._metadata_worker_cancel_requested = False
        self.metadata_loaded_paths = set()  # full paths with metadata
        self.metadata_icon_map = load_metadata_icons()
        self.preview_icons = load_preview_status_icons()
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

        # --- Preview update debouncing timer ---
        self.preview_update_timer = QTimer(self)
        self.preview_update_timer.setSingleShot(True)
        self.preview_update_timer.setInterval(250)  # milliseconds
        self.preview_update_timer.timeout.connect(self.generate_preview_names)

    # --- Method definitions ---
    def setup_main_window(self) -> None:
        """Configure main window properties."""
        self.setWindowTitle("oncutf - Batch File Renamer and More")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.center_window()

    def setup_main_layout(self) -> None:
        """Setup central widget and main layout."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

    def setup_splitters(self) -> None:
        """Setup vertical and horizontal splitters."""
        self.vertical_splitter = QSplitter(Qt.Vertical)  # type: ignore
        self.main_layout.addWidget(self.vertical_splitter)

        self.horizontal_splitter = QSplitter(Qt.Horizontal)  # type: ignore
        self.vertical_splitter.addWidget(self.horizontal_splitter)
        self.vertical_splitter.setSizes(TOP_BOTTOM_SPLIT_RATIO)

    def setup_left_panel(self) -> None:
        """Setup left panel (folder tree)."""
        self.left_frame = QFrame()
        left_layout = QVBoxLayout(self.left_frame)
        left_layout.addWidget(QLabel("Folders"))

        self.folder_tree = CustomTreeView()
        self.folder_tree.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.folder_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.folder_tree.setAlternatingRowColors(True)  # Enable alternating row colors
        left_layout.addWidget(self.folder_tree)

        # Expand/collapse mode (single or double click)
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
        self.file_table_view.setModel(self.model)

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
        self.file_table_view.setAlternatingRowColors(True)
        self.file_table_view.setShowGrid(False)
        self.file_table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table_view.setSortingEnabled(True)  # Manual sorting logic
        self.file_table_view.setWordWrap(False)

        # Initialize header and set default row height
        header = self.file_table_view.horizontalHeader()
        self.file_table_view.verticalHeader().setDefaultSectionSize(22)  # Compact row height

        header.setMinimumSectionSize(23)  # PyQt5: only global min width supported
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.file_table_view.setColumnWidth(0, 23)

        # Column 1: Filename (wide, interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.resizeSection(1, 290)
        self.file_table_view.setColumnWidth(1, 290)

        # Column 2: Filesize (new column)
        col2_min = self.fontMetrics().horizontalAdvance("999 GB") + 50
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.file_table_view.setColumnWidth(2, col2_min)

        # Column 3: Extension (type column)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.file_table_view.setColumnWidth(3, 60)

        # Column 4: Modified date
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.file_table_view.setColumnWidth(4, 140)
        # Per-section min/max width is not supported in PyQt5

        # Show placeholder after setup is complete
        self.file_table_view.set_placeholder_visible(True)
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
        self.metadata_tree_view.files_dropped.connect(self.load_metadata_from_dropped_files)
        self.metadata_tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.metadata_tree_view.setUniformRowHeights(True)
        self.metadata_tree_view.expandToDepth(1)
        self.metadata_tree_view.setRootIsDecorated(False)
        self.metadata_tree_view.setAcceptDrops(True)
        self.metadata_tree_view.viewport().setAcceptDrops(True)
        self.metadata_tree_view.setDragDropMode(QAbstractItemView.DropOnly)
        self.metadata_tree_view.setAlternatingRowColors(True)  # Enable alternating row colors
        right_layout.addWidget(self.metadata_tree_view)

        # Dummy initial model
        placeholder_model = QStandardItemModel()
        placeholder_model.setHorizontalHeaderLabels(["Key", "Value"])
        placeholder_item = QStandardItem("No file selected")
        placeholder_item.setTextAlignment(Qt.AlignLeft)
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
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
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
        """
        self.header.sectionClicked.connect(self.sort_by_column)

        self.select_folder_button.clicked.connect(self.handle_folder_select)
        self.browse_folder_button.clicked.connect(self.handle_browse)

        # Connect folder_tree for drag & drop operations
        self.folder_tree.folder_dropped.connect(self.load_files_from_dropped_items)
        self.folder_tree.folder_selected.connect(self.handle_folder_select)

        self.file_table_view.clicked.connect(self.on_table_row_clicked)
        self.file_table_view.selection_changed.connect(self.update_preview_from_selection)
        self.file_table_view.files_dropped.connect(self.load_files_from_dropped_items)
        self.model.sort_changed.connect(self.schedule_preview_update)
        self.file_table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table_view.customContextMenuRequested.connect(self.handle_table_context_menu)

        self.toggle_expand_button.toggled.connect(self.toggle_metadata_expand)

        self.preview_old_name_table.verticalScrollBar().valueChanged.connect(
            self.preview_new_name_table.verticalScrollBar().setValue
        )
        self.preview_new_name_table.verticalScrollBar().valueChanged.connect(
            self.preview_old_name_table.verticalScrollBar().setValue
        )
        self.preview_old_name_table.verticalScrollBar().valueChanged.connect(
            self.preview_icon_table.verticalScrollBar().setValue
        )

        self.rename_button.clicked.connect(self.rename_files)

        # --- Connect the updated signal of RenameModulesArea to generate_preview_names ---
        self.rename_modules_area.updated.connect(self.schedule_preview_update)

        # --- Shortcuts ---
        QShortcut(QKeySequence("Ctrl+A"), self.file_table_view, activated=self.select_all_rows)
        QShortcut(QKeySequence("Ctrl+Shift+A"), self.file_table_view, activated=self.clear_all_selection)
        QShortcut(QKeySequence("Ctrl+I"), self.file_table_view, activated=self.invert_selection)

        QShortcut(QKeySequence("Ctrl+O"), self.file_table_view, activated=self.handle_browse)
        QShortcut(QKeySequence("Ctrl+R"), self.file_table_view, activated=self.force_reload)

        QShortcut(QKeySequence("Ctrl+M"), self.file_table_view, activated=self.shortcut_load_metadata)
        QShortcut(QKeySequence("Ctrl+E"), self.file_table_view, activated=self.shortcut_load_extended_metadata)

    def request_preview_update(self):
        self.preview_update_timer.start()

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
            self.request_preview_update()
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
            self.request_preview_update()

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

    def sort_by_column(self, column: int, order: Qt.SortOrder = None) -> None:
        """
        Triggered when a header section is clicked.
        Sorts the file table immediately on first click,
        toggles sort order if the same column is clicked again.
        """
        if column == 0:
            return  # Do not sort the status/info column

        header = self.file_table_view.horizontalHeader()
        current_column = header.sortIndicatorSection()
        current_order = header.sortIndicatorOrder()

        if column == current_column:
            new_order = Qt.DescendingOrder if current_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            new_order = Qt.AscendingOrder

        self.model.sort(column, new_order)
        header.setSortIndicator(column, new_order)

    def restore_fileitem_metadata_from_cache(self) -> None:
        """
        After a folder reload (e.g. after rename), reassigns cached metadata
        to the corresponding FileItem objects in self.model.files.

        This allows icons and previews to remain consistent without rescanning.
        """
        restored = 0
        for file in self.model.files:
            cached = self.metadata_cache.get(file.full_path)
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
            self.request_preview_update()

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
        self.file_table_view.setModel(self.model)
        for f in file_items:
            f.checked = False
        self.model.set_files(file_items)
        self.files = file_items
        self.model.folder_path = self.current_folder_path
        self.preview_map.clear()
        self.preview_map = {f.filename: f for f in file_items}

        if hasattr(self, "header") and self.header is not None:
            self.header.setEnabled(True)  # Enable file table header
        # Enable hover delegate if it exists
        if hasattr(self.file_table_view, 'hover_delegate'):
            self.file_table_view.setItemDelegate(self.file_table_view.hover_delegate)
            self.file_table_view.hover_delegate.hovered_row = -1
        self.update_files_label()
        self.update_preview_tables_from_pairs([])
        self.rename_button.setEnabled(False)
        self.file_table_view.viewport().update()

        # If we're coming from a rename operation and have active modules, regenerate preview
        if self.last_action == "rename":
            logger.debug("[PrepareTable] Post-rename detected, preview will be updated after checked state restore")
            # Don't generate preview here - will be done after checked state is restored

    def load_files_from_folder(self, folder_path: str, skip_metadata: bool = False, force: bool = False):

        normalized_new = os.path.abspath(os.path.normpath(folder_path))
        normalized_current = os.path.abspath(os.path.normpath(self.current_folder_path or ""))

        if normalized_new == normalized_current and not force:
            logger.info(f"[FolderLoad] Ignored reload of already loaded folder: {normalized_new}")
            self.set_status("Folder already loaded.", color="gray", auto_reset=True)
            return

        logger.info(f"Loading files from folder: {folder_path} (skip_metadata={skip_metadata})")

        # Only skip clearing metadata cache immediately after rename action,
        # and only if metadata scan is explicitly skipped (default fast path).
        # In all other cases, always clear cache to reflect current OS state.
        if not (self.last_action == "rename" and skip_metadata):
            self.metadata_cache.clear()

        self.current_folder_path = folder_path
        self.check_selection_and_show_metadata() # reset metadata tree

        file_items = self.get_file_items_from_folder(folder_path)

        if not file_items:
            short_name = os.path.basename(folder_path.rstrip("/\\"))
            # self.show_file_table_placeholder(f"No supported files in '{short_name}'")
            self.clear_metadata_view()
            self.header.setEnabled(False)
            self.set_status("No supported files found.", color="orange", auto_reset=True)
            return

        self.prepare_file_table(file_items)
        self.sort_by_column(1, Qt.AscendingOrder)
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
        Initiates threaded metadata scanning for μια συγκεκριμένη λίστα από FileItems.
        Χρησιμοποιεί το context manager wait_cursor() αντί για show_wait_cursor_if_many_files και restore_cursor.
        """
        file_paths = [item.full_path for item in items if item.full_path]
        if not file_paths:
            self.set_status("No valid files to scan.", color="gray", auto_reset=True)
            return

        self.set_status(f"Loading metadata for {len(file_paths)} file(s)...", color="blue")
        with wait_cursor():
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
        """
        selection_model = self.file_table_view.selectionModel()
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
            metadata = file_item.metadata or self.metadata_cache.get(file_item.full_path)

            if isinstance(metadata, dict) and metadata:
                display_metadata = dict(metadata)
                display_metadata["FileName"] = file_item.filename
                self.display_metadata(display_metadata, context="check_selection_and_show_metadata")
                return

        self.clear_metadata_view()

    def reload_current_folder(self) -> None:
        # Optional: adjust if flags need to be preserved
        if self.current_folder_path:
            self.load_files_from_folder(self.current_folder_path, skip_metadata=False)
            self.sort_by_column(1, Qt.AscendingOrder)


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
            self.request_preview_update()
            self.check_selection_and_show_metadata()

    def generate_preview_names(self) -> None:
        """
        Generate new preview names for all selected files using current rename modules.
        Updates the preview map and UI elements accordingly.
        """
        timer = QElapsedTimer()
        timer.start()

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

        elapsed = timer.elapsed()
        logger.debug(f"[Performance] generate_preview_names took {elapsed} ms")

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
        """
        Updates all three preview tables:
        - Old name table (left)
        - New name table (center)
        - Status icon table (right)

        It also computes the status of each rename (unchanged, invalid, duplicate, valid),
        updates the preview_map where needed, and renders the status label at the bottom.

        Args:
            name_pairs (list[tuple[str, str]]): List of (old_name, new_name) pairs
                generated during preview generation.
        """
        # Clear all preview tables before updating
        self.preview_old_name_table.setRowCount(0)
        self.preview_new_name_table.setRowCount(0)
        self.preview_icon_table.setRowCount(0)

        if not name_pairs:
            self.status_label.setText("No files selected.")
            return

        # Calculate appropriate width for consistent column size
        all_names = [name for pair in name_pairs for name in pair]
        max_width = max((self.fontMetrics().horizontalAdvance(name) for name in all_names), default=250)
        adjusted_width = max(326, max_width) + 100
        self.preview_old_name_table.setColumnWidth(0, adjusted_width)
        self.preview_new_name_table.setColumnWidth(0, adjusted_width)

        # Precompute duplicates
        seen, duplicates = set(), set()
        for _, new_name in name_pairs:
            if new_name in seen:
                duplicates.add(new_name)
            else:
                seen.add(new_name)

        # Initialize status counters
        stats = {"unchanged": 0, "invalid": 0, "duplicate": 0, "valid": 0}

        for row, (old_name, new_name) in enumerate(name_pairs):
            self.preview_old_name_table.insertRow(row)
            self.preview_new_name_table.insertRow(row)
            self.preview_icon_table.insertRow(row)

            # Create table items
            old_item = QTableWidgetItem(old_name)
            new_item = QTableWidgetItem(new_name)

            # Determine rename status
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

            # Fetch file item and enrich tooltip if metadata is missing
            file_item = self.preview_map.get(new_name)
            if file_item and not getattr(file_item, "metadata", None):
                tooltip += " [No metadata available]"

            # Update status counts
            stats[status] += 1

            # Prepare status icon
            icon_item = QTableWidgetItem()
            icon = self.preview_icons.get(status)
            if icon:
                icon_item.setIcon(icon)
            icon_item.setToolTip(tooltip)

            # Insert items into corresponding tables
            self.preview_old_name_table.setItem(row, 0, old_item)
            self.preview_new_name_table.setItem(row, 0, new_item)
            self.preview_icon_table.setItem(row, 0, icon_item)

        # Render bottom status summary (valid, unchanged, invalid, duplicate)
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
        self.request_preview_update()


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
        """
        selected_indexes = self.file_table_view.selectionModel().selectedRows()
        return [self.model.files[i.row()] for i in selected_indexes if 0 <= i.row() < len(self.model.files)]

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

    def clear_file_table(self, message: str = "No folder selected") -> None:
        """
        Clears the file table and shows a placeholder message.
        """
        self.clear_metadata_view()
        self.model.set_files([])  # reset model with empty list
        self.file_table_view.set_placeholder_visible(False)
        self.header.setEnabled(False) # disable header
        self.status_label.setText(message)
        self.update_files_label()

    def show_empty_metadata_tree(self, message: str = "No file selected") -> None:
        """
        Displays a placeholder message in the metadata tree view.
        """

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Key", "Value"])

        key_item = QStandardItem(message)
        key_item.setTextAlignment(Qt.AlignLeft)
        font = key_item.font()
        font.setItalic(True)
        key_item.setFont(font)
        key_item.setForeground(Qt.gray)

        value_item = QStandardItem("-")
        value_item.setForeground(Qt.gray)

        model.appendRow([key_item, value_item])
        self.metadata_tree_view.setModel(model)

        self.toggle_expand_button.setChecked(False)
        self.toggle_expand_button.setText("Expand All")
        self.toggle_expand_button.setEnabled(False)  # Disable expand/collapse button
        # If metadata_tree_view has a header, disable it
        if hasattr(self.metadata_tree_view, 'header') and callable(self.metadata_tree_view.header):
            header = self.metadata_tree_view.header()
            if header:
                header.setEnabled(False)

    def clear_metadata_view(self) -> None:
        """
        Clears the metadata tree view and shows a placeholder message.
        """
        self.show_empty_metadata_tree("No file selected")

    def get_common_metadata_fields(self) -> list[str]:
        """
        Returns the intersection of metadata keys from all checked files.
        """
        selected_files = [f for f in self.model.files if f.checked]
        if not selected_files:
            return []

        common_keys = None

        for file in selected_files:
            path = file.full_path
            metadata = self.metadata_cache.get(path, {})
            keys = set(metadata.keys())

            if common_keys is None:
                common_keys = keys
            else:
                common_keys &= keys  # intersection

        return sorted(common_keys) if common_keys else []

    def set_fields_from_list(self, field_names: list[str]) -> None:
        """
        Replaces the combo box entries with the given field names.
        """
        self.combo.clear()
        for name in field_names:
            self.combo.addItem(name, userData=name)

        # Trigger signal to refresh preview
        self.updated.emit(self)

    def after_check_change(self) -> None:
        """
        Called after the checked state of any file is modified.

        Triggers UI refresh for the file table, updates the header state and label,
        and regenerates the filename preview.
        """
        self.file_table_view.viewport().update()
        self.update_files_label()
        self.request_preview_update()


    def get_modifier_flags(self) -> tuple[bool, bool]:
        """
        Checks which keyboard modifiers are currently held down.

        Returns:
            tuple: (skip_metadata: bool, use_extended: bool)
                - skip_metadata: True if Ctrl is pressed
                - use_extended: True if Shift is pressed
        """
        modifiers = QApplication.keyboardModifiers()
        skip_metadata = modifiers & Qt.ControlModifier
        use_extended = modifiers & Qt.ShiftModifier

        # [DEBUG] Modifiers: Ctrl=%s, Shift=%s", skip_metadata, use_extended
        return bool(skip_metadata), bool(use_extended)

    def determine_metadata_mode(self) -> tuple[bool, bool]:
        """
        Returns:
            tuple: (skip_metadata, use_extended)

            - skip_metadata = True  ➜ no metadata at all (default)
            - skip_metadata = False & use_extended = False ➜ fast
            - skip_metadata = False & use_extended = True ➜ extended

        Rules:
            - If Ctrl is pressed → fast
            - If Ctrl+Shift → extended
            - Else (no modifiers) → skip
        """
        modifiers = QApplication.keyboardModifiers()

        if modifiers & Qt.ControlModifier:
            use_extended = modifiers & Qt.ShiftModifier
            return False, bool(use_extended)

        return True, False

    def should_use_extended_metadata(self) -> bool:
        """
        Returns True if Shift (or Ctrl+Shift) is held,
        used in cases where metadata is always loaded (double click, drag & drop).

        This assumes that metadata will be loaded — we only decide if it's fast or extended.
        """
        modifiers = QApplication.keyboardModifiers()
        return bool(modifiers & Qt.ShiftModifier)

    def update_preview_from_selection(self, selected_rows: list[int]) -> None:
        """
        Synchronizes the checked state of files and updates preview + metadata panel,
        based on selected rows emitted from the custom table view.

        Args:
            selected_rows (list[int]): The indices of selected rows (from custom selection).
        """
        logger.debug(f"[Sync] update_preview_from_selection: {selected_rows}")
        timer = QElapsedTimer()
        timer.start()

        for row, file in enumerate(self.model.files):
            file.checked = row in selected_rows

        self.update_files_label()
        self.request_preview_update()

        # Show metadata for last selected file
        if selected_rows:
            last_row = selected_rows[-1]
            if 0 <= last_row < len(self.model.files):
                file_item = self.model.files[last_row]
                metadata = file_item.metadata or self.metadata_cache.get(file_item.full_path)
                if isinstance(metadata, dict):
                    self.display_metadata(metadata, context="update_preview_from_selection")
                else:
                    self.clear_metadata_view()
        else:
            self.clear_metadata_view()

        elapsed = timer.elapsed()
        logger.debug(f"[Performance] Full preview update took {elapsed} ms")

    def handle_table_context_menu(self, position) -> None:
        """
        Handles the right-click context menu for the file table.

        Supports:
        - Metadata load (normal / extended) for selected or all files
        - Invert selection, select all, reload folder
        - Uses custom selection state from file_table_view.selected_rows
        """
        if not self.model.files:
            return

        index = self.file_table_view.indexAt(position)
        total_files = len(self.model.files)

        # Get selected rows from custom selection model
        selected_rows = self.file_table_view.selected_rows
        selected_files = [self.model.files[r] for r in selected_rows if 0 <= r < total_files]

        menu = QMenu(self)

        # --- Metadata actions ---
        action_load_sel = menu.addAction("📄 Load metadata for selected file(s)")
        action_load_all = menu.addAction("📁 Load metadata for all files")
        action_load_ext_sel = menu.addAction("📄 Load extended metadata for selected file(s)")
        action_load_ext_all = menu.addAction("📁 Load extended metadata for all files")

        menu.addSeparator()

        # --- Selection actions ---
        action_invert = menu.addAction("🔁 Invert selection (Ctrl+I)")
        action_select_all = menu.addAction("✅ Select all (Ctrl+A)")
        action_deselect_all = menu.addAction("❌ Deselect all")
        action_deselect_all.setEnabled(total_files > 0)

        menu.addSeparator()

        # --- Other actions ---
        action_reload = menu.addAction("🔄 Reload folder (Ctrl+R)")

        menu.addSeparator()

        # --- Disabled future options ---
        action_save_sel = menu.addAction("💾 Save metadata for selected file(s)")
        action_save_all = menu.addAction("💾 Save metadata for all files")
        action_save_sel.setEnabled(False)
        action_save_all.setEnabled(False)

        # --- Enable/disable logic ---
        if not selected_files:
            action_load_sel.setEnabled(False)
            action_load_ext_sel.setEnabled(False)
            action_invert.setEnabled(total_files > 0)
        else:
            action_load_sel.setEnabled(True)
            action_load_ext_sel.setEnabled(True)

        action_load_all.setEnabled(total_files > 0)
        action_load_ext_all.setEnabled(total_files > 0)
        action_select_all.setEnabled(total_files > 0)
        action_reload.setEnabled(total_files > 0)

        # Show menu and get chosen action
        action = menu.exec_(self.file_table_view.viewport().mapToGlobal(position))

        self.file_table_view.context_focused_row = None
        self.file_table_view.viewport().update()
        # Force full repaint of the table to avoid stale selection highlight
        self.file_table_view.update()

        # === Handlers ===
        if action == action_load_sel:
            self.force_extended_metadata = False
            self.start_metadata_scan_for_items(selected_files)

        elif action == action_load_ext_sel:
            files_to_load = [
                f for f in selected_files
                if not self.metadata_loader.has_extended(f.full_path, self.metadata_cache)
            ]
            if files_to_load and not self.confirm_large_files(files_to_load):
                return

            if files_to_load:
                self.force_extended_metadata = True
                if len(files_to_load) > 1:
                    self.start_metadata_scan_for_items(files_to_load)
                else:
                    with wait_cursor():
                        self.metadata_loader.load(files_to_load, force=False, cache=self.metadata_cache, use_extended=True)
                        last = files_to_load[-1]
                        metadata = last.metadata or self.metadata_cache.get(last.full_path)
                        if isinstance(metadata, dict):
                            self.display_metadata(metadata, context="context_menu_extended_1file")

        elif action == action_load_all:
            self.force_extended_metadata = False
            self.select_all_rows()
            self.start_metadata_scan_for_items(self.model.files)

        elif action == action_load_ext_all:
            if not self.confirm_large_files(self.model.files):
                return
            self.force_extended_metadata = True
            self.start_metadata_scan_for_items(self.model.files)

        elif action == action_invert:
            self.invert_selection()

        elif action == action_select_all:
            self.select_all_rows()

        elif action == action_reload:
            self.force_reload()

        elif action == action_deselect_all:
            self.clear_all_selection()

    def handle_file_double_click(self, index: QModelIndex, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Loads metadata for the file (even if already loaded), on double-click.
        Shows wait cursor for 1 file or dialog for multiple selected.
        """
        row = index.row()
        if 0 <= row < len(self.model.files):
            file = self.model.files[row]
            logger.info(f"[DoubleClick] Requested metadata reload for: {file.filename}")

            self.force_extended_metadata = bool(int(modifiers) & int(Qt.ShiftModifier))
            logger.debug(f"[Modifiers] Shift held → use_extended={self.force_extended_metadata}")

            selected_indexes = self.file_table_view.selectionModel().selectedRows()
            selected_files = [self.model.files[i.row()] for i in selected_indexes if 0 <= i.row() < len(self.model.files)]

            # Check if Shift was held during double click
            keyboard_mods = modifiers
            if keyboard_mods & Qt.ShiftModifier:
                # If Qt has selected a large range (likely unintended), reset to only the clicked file
                # This avoids accidental multi-file extended scan due to Shift+Click behavior
                if file in selected_files and len(selected_files) > 1:
                    logger.debug(f"[ShiftFix] Qt range selection detected on Shift+DoubleClick — keeping only clicked file: {file.filename}")
                    selected_files = [file]

            if self.force_extended_metadata and not self.confirm_large_files(selected_files):
                return

            if self.force_extended_metadata and len(selected_files) > 1:
                self.start_metadata_scan_for_items(selected_files)
                return

            if self.force_extended_metadata:
                wait_cursor_cm = wait_cursor()
                wait_cursor_cm.__enter__()

            self.metadata_loader.load(
                [file],
                force=False,
                cache=self.metadata_cache,
                use_extended=self.force_extended_metadata
            )

            if self.force_extended_metadata:
                wait_cursor_cm.__exit__(None, None, None)

            metadata = file.metadata or self.metadata_cache.get(file.full_path)
            if isinstance(metadata, dict) and metadata:
                self.display_metadata(metadata, context="handle_file_double_click")
            else:
                logger.warning(f"[DoubleClick] No valid metadata to display for {file.filename}")

            row = self.model.files.index(file)
            for col in range(self.model.columnCount()):
                idx = self.model.index(row, col)
                self.file_table_view.viewport().update(self.file_table_view.visualRect(idx))

                self.display_metadata(metadata, context="handle_dropped_files")

            self.file_table_view.viewport().update()

    def closeEvent(self, event) -> None:
        """
        Called when the main window is about to close.

        Ensures any background metadata threads are cleaned up
        properly before the application exits.
        """
        logger.info("Main window closing. Cleaning up metadata worker.")
        self.cleanup_metadata_worker()

        if hasattr(self.metadata_loader, "close"):
            self.metadata_loader.close()  # ✨ new line

        super().closeEvent(event)

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """
        Prepares the application state and loads files from the specified folder
        into the file table.

        This helper consolidates common logic used in folder-based file loading
        (e.g., from folder select, browse, or dropped folder).

        Args:
            folder_path (str): Absolute path to the folder to load files from.
            clear (bool): Whether to clear the file table before loading. Defaults to True.

        Returns:
            list[str]: A list of file paths (full paths) that were successfully loaded.
        """
        self.clear_file_table("No folder selected")
        self.clear_metadata_view()

        file_items = self.get_file_items_from_folder(folder_path)
        self.current_folder_path = folder_path

        paths = [item.full_path for item in file_items]
        self.load_files_from_paths(paths, clear=clear)

        return paths

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
        """
        Loads a mix of files and folders into the file table.
        Uses existing helper for folder reading.

        Args:
            file_paths: List of absolute file or folder paths
            clear: Whether to clear existing items before loading
        """
        if clear:
            self.model.clear()

        if not file_paths:
            self.file_table_view.set_placeholder_visible(True)
            return

        file_items = []
        for path in file_paths:
            if os.path.isdir(path):
                file_items.extend(self.get_file_items_from_folder(path))
            elif os.path.isfile(path):
                ext = os.path.splitext(path)[1][1:].lower()
                if ext in ALLOWED_EXTENSIONS:
                    filename = os.path.basename(path)
                    modified = datetime.datetime.fromtimestamp(
                        os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
                    file_items.append(FileItem(filename, ext, modified, full_path=path))

        self.model.files = file_items
        self.model.layoutChanged.emit()
        print("[DEBUG] Header class after model set:", type(self.file_table_view.horizontalHeader()))
        self.file_table_view.setHorizontalHeader(self.header)

        self.file_table_view.set_placeholder_visible(len(file_items) == 0)
        self.file_table_view.scrollToTop()
        self.file_table_view.setSortingEnabled(True)
        self.file_table_view.horizontalHeader().setEnabled(True)
        self.header.setSectionsClickable(True)
        self.header.setSortIndicatorShown(True)
        self.file_table_view.sortByColumn(1, Qt.AscendingOrder)
        self.file_table_view.clearSelection()


    def load_metadata_from_dropped_files(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Called when user drops files onto metadata tree.
        Maps filenames to FileItem objects and triggers forced metadata loading.
        """
        file_items = []
        for path in paths:
            filename = os.path.basename(path)
            file = next((f for f in self.model.files if f.filename == filename), None)
            if file:
                file_items.append(file)

        if not file_items:
            logger.info("[Drop] No matching files found in table.")
            return

        self.force_extended_metadata = bool(int(modifiers) & int(Qt.ShiftModifier))
        logger.debug(f"[Modifiers] Shift held → use_extended={self.force_extended_metadata}")

        if len(file_items) > 1:
            self.start_metadata_scan_for_items(file_items)
            return

        # For a single file (either fast or extended)
        with wait_cursor():
            self.metadata_loader.load(
                file_items,
                force=False,
                cache=self.metadata_cache,
                use_extended=self.force_extended_metadata
            )

        if file_items:
            last = file_items[-1]
            metadata = self.metadata_cache.get(last.full_path)
            if isinstance(metadata, dict):
                self.display_metadata(metadata, context="load_metadata_from_dropped_files")

            self.file_table_view.viewport().update()

    def load_files_from_dropped_items(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Called when user drops files or folders onto file table view.
        Imports the dropped files into the current view.
        """
        if not paths:
            logger.info("[Drop] No files dropped in table.")
            return

        logger.info(f"[Drop] {len(paths)} file(s)/folder(s) dropped in table view")

        if len(paths) == 1 and os.path.isdir(paths[0]):
            folder_path = paths[0]
            logger.info(f"[Drop] Setting folder from drop: {folder_path}")

            # 🔁 Centralized loading logic
            self.prepare_folder_load(folder_path)

            # ✅ Update folder tree selection (UI logic)
            if hasattr(self.dir_model, "index"):
                index = self.dir_model.index(folder_path)
                self.folder_tree.setCurrentIndex(index)

            # ✅ Trigger label update and ensure repaint
            self.file_table_view.viewport().update()
            self.update_files_label()
        else:
            # Load directly dropped files
            self.load_files_from_paths(paths, clear=True)

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

        # -- Prepare + load files using helper
        paths = self.prepare_folder_load(folder_path)

        # -- Large folder warning check
        is_large = len(paths) > LARGE_FOLDER_WARNING_THRESHOLD

        # -- Metadata scan flags
        skip_metadata, use_extended = self.determine_metadata_mode()
        logger.debug(f"[Modifiers] skip_metadata={skip_metadata}, use_extended={use_extended}")
        self.force_extended_metadata = use_extended
        self.skip_metadata_mode = skip_metadata

        logger.debug("-" * 60)
        logger.info(
            f"Tree-selected folder: {folder_path}, skip_metadata={skip_metadata}, extended={use_extended}, "
            f"(large={is_large}, default={DEFAULT_SKIP_METADATA})",
            extra={"dev_only": True}
        )
        logger.warning(f"-> skip_metadata passed to loader: {skip_metadata}")

        # -- Update tree selection (optional)
        if hasattr(self, "dir_model") and hasattr(self, "folder_tree"):
            index = self.dir_model.index(folder_path)
            if index.isValid():
                self.folder_tree.setCurrentIndex(index)
                self.folder_tree.scrollTo(index)

    def handle_folder_select(self) -> None:
        """
        It loads files from the folder currently selected in the folder tree.
        If the Ctrl key is held, metadata scanning is skipped.

        Triggered when the user clicks the 'Select Folder' button.
        """
        self.last_action = "folder_select"

        index = self.folder_tree.currentIndex()
        if not index.isValid():
            logger.warning("No folder selected in folder tree.")
            return

        folder_path = self.dir_model.filePath(index)

        if self.should_skip_folder_reload(folder_path):
            return
        else:
            force_reload = True

        # -- Prepare + load files using helper
        paths = self.prepare_folder_load(folder_path)

        # -- Large folder warning check
        is_large = len(paths) > LARGE_FOLDER_WARNING_THRESHOLD

        # -- Metadata scan flags
        skip_metadata, use_extended = self.determine_metadata_mode()
        logger.debug(f"[Modifiers] skip_metadata={skip_metadata}, use_extended={use_extended}")
        self.force_extended_metadata = use_extended
        self.skip_metadata_mode = skip_metadata

        logger.info(
            f"Tree-selected folder: {folder_path}, skip_metadata={skip_metadata}, extended={use_extended}, "
            f"(large={is_large}, default={DEFAULT_SKIP_METADATA})",
            extra={"dev_only": True}
        )
        logger.warning(f"-> skip_metadata passed to loader: {skip_metadata}")

    def schedule_preview_update(self) -> None:
        """
        Προγραμματίζει μια καθυστερημένη ενημέρωση των προεπισκοπήσεων ονομάτων.
        Αντί να καλείται απευθείας η generate_preview_names κάθε φορά που αλλάζει κάτι,
        επανεκκινείται ο timer ώστε η πραγματική ενημέρωση να γίνεται μόνο όταν
        σταματήσουν οι αλλαγές για το διάστημα που έχει οριστεί (250ms).
        """
        self.preview_update_timer.start()

