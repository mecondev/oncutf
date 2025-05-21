"""
main_window.py
Author: Michael Economou
Date: 2025-05-01

This module defines the MainWindow class, which implements the primary user interface
for the oncutf application. It includes logic for loading files from folders, launching
metadata extraction in the background, and managing user interaction such as rename previews.
"""

import os
import glob
import datetime
import platform
import json
from typing import TYPE_CHECKING, List, Tuple, Dict
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QFrame, QScrollArea, QTableWidget, QTreeView, QFileDialog,
    QFileSystemModel, QAbstractItemView,  QSizePolicy, QHeaderView, QTableWidgetItem,
    QDesktopWidget, QGraphicsOpacityEffect, QMenu, QShortcut
)
from PyQt5.QtCore import (
    Qt, QDir, QUrl, QThread, QTimer, QModelIndex, QPropertyAnimation, QMetaObject,
    QItemSelection, QItemSelectionRange, QItemSelectionModel
)
from PyQt5.QtGui import (
    QPixmap, QBrush, QColor, QIcon, QDesktopServices, QStandardItem, QStandardItemModel,
    QKeySequence
)

from models.file_table_model import FileTableModel
from models.file_item import FileItem
from utils.filename_validator import FilenameValidator
from utils.preview_generator import generate_preview_names as generate_preview_logic
from utils.icons import create_colored_icon
from utils.icon_cache import prepare_status_icons
from utils.preview_engine import apply_rename_modules
from utils.metadata_reader import MetadataReader
from utils.build_metadata_tree_model import build_metadata_tree_model
from utils.metadata_cache import MetadataCache
from utils.metadata_utils import resolve_skip_metadata
from utils.renamer import Renamer
from utils.text_helpers import elide_text
from utils.icon_loader import load_metadata_icons
from widgets.metadata_worker import MetadataWorker
from widgets.checkbox_header import CheckBoxHeader
from widgets.rename_module_widget import RenameModuleWidget
from widgets.custom_msgdialog import CustomMessageDialog
from widgets.metadata_icon_delegate import MetadataIconDelegate
from widgets.custom_table_view import CustomTableView
from widgets.metadata_tree_view import MetadataTreeView

from config import *

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


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

        self.loading_dialog = None

        self.create_colored_icon = create_colored_icon
        self.icon_paths = prepare_status_icons()

        self.metadata_icon_map = load_metadata_icons()
        self.metadata_reader = MetadataReader()
        self.skip_metadata_mode = DEFAULT_SKIP_METADATA # Keeps state across folder reloads

        self.filename_validator = FilenameValidator()
        self.last_action = None  # Could be: 'folder_select', 'browse', 'rename', etc.
        self.current_folder_path = None
        self.files = []
        self.rename_modules = []
        self.preview_map = {}  # preview_filename -> FileItem


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
        self.vertical_splitter = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.vertical_splitter)

        self.horizontal_splitter = QSplitter(Qt.Horizontal)
        self.vertical_splitter.addWidget(self.horizontal_splitter)
        self.vertical_splitter.setSizes([485, 235])

    def setup_left_panel(self) -> None:
        """Setup left panel (folder tree)."""
        self.left_frame = QFrame()
        left_layout = QVBoxLayout(self.left_frame)
        left_layout.addWidget(QLabel("Folders"))

        self.tree_view = QTreeView()
        self.tree_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_layout.addWidget(self.tree_view)

        btn_layout = QHBoxLayout()
        self.select_folder_button = QPushButton("Select Folder")
        self.browse_folder_button = QPushButton("Browse Folders")
        btn_layout.addWidget(self.select_folder_button)
        btn_layout.addWidget(self.browse_folder_button)
        left_layout.addLayout(btn_layout)

        self.dir_model = QFileSystemModel()
        self.dir_model.setRootPath('')
        self.dir_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs)
        self.tree_view.setModel(self.dir_model)
        for i in range(1, 4):
            self.tree_view.hideColumn(i)

        root = "" if platform.system() == "Windows" else "/"
        self.tree_view.setRootIndex(self.dir_model.index(root))

        self.horizontal_splitter.addWidget(self.left_frame)

    def setup_center_panel(self) -> None:
        """Setup center panel (file table view)."""
        self.center_frame = QFrame()
        center_layout = QVBoxLayout(self.center_frame)

        self.files_label = QLabel("Files")
        center_layout.addWidget(self.files_label)

        self.file_table_view = CustomTableView()
        self.file_table_view.verticalHeader().setVisible(False)
        self.file_table_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.header = CheckBoxHeader(Qt.Horizontal, self.file_table_view, parent_window=self)
        self.model = FileTableModel(parent_window=self)
        self.show_file_table_placeholder("No folder selected")

        # Table View column adjustments
        self.file_table_view.setHorizontalHeader(self.header)
        self.header.setEnabled(False)
        self.file_table_view.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self.file_table_view.setAlternatingRowColors(True)
        self.file_table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table_view.setSortingEnabled(True)
        self.file_table_view.setWordWrap(False)

        # Column size setup
        self.file_table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.file_table_view.setColumnWidth(0, 23)

        self.file_table_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.file_table_view.horizontalHeader().resizeSection(1, 400)  # filename (default wide)

        self.file_table_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.file_table_view.setColumnWidth(2, 60)  # type column (4 letters approx.)

        self.file_table_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.file_table_view.setColumnWidth(3, 140)  # modified date-time

        self.metadata_delegate = MetadataIconDelegate(icon_map=self.metadata_icon_map)
        self.file_table_view.setItemDelegateForColumn(0, self.metadata_delegate)

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
        self.metadata_tree_view.files_dropped.connect(self.handle_dropped_files)
        self.metadata_tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.metadata_tree_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.metadata_tree_view.setUniformRowHeights(True)
        self.metadata_tree_view.expandToDepth(1)
        self.metadata_tree_view.setRootIsDecorated(False)
        self.metadata_tree_view.setAcceptDrops(True)
        self.metadata_tree_view.viewport().setAcceptDrops(True)
        self.metadata_tree_view.setDragDropMode(QAbstractItemView.DropOnly)

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
        self.horizontal_splitter.setSizes([250, 550, 200])

    def setup_bottom_layout(self) -> None:
        """Setup bottom layout for rename modules and preview."""
        # --- Bottom Frame: Rename Modules + Preview ---
        self.bottom_frame = QFrame()
        self.bottom_layout = QVBoxLayout(self.bottom_frame)
        self.bottom_layout.setSpacing(0)
        self.bottom_layout.setContentsMargins(0, 0, 0, 0)

        content_layout = QHBoxLayout()

        # === Left: Rename modules ===
        self.module_frame = QFrame()
        module_layout = QVBoxLayout(self.module_frame)

        self.module_scroll_area = QScrollArea()
        self.module_scroll_area.setWidgetResizable(True)
        self.module_scroll_widget = QWidget()

        self.module_scroll_layout = QVBoxLayout(self.module_scroll_widget)
        self.module_scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.module_scroll_layout.setSpacing(2)
        self.module_scroll_layout.setAlignment(Qt.AlignTop)
        self.module_scroll_area.setWidget(self.module_scroll_widget)
        module_layout.addWidget(self.module_scroll_area)

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

        self.preview_icon_table.setObjectName("iconTable")
        self.preview_icon_table.setFixedWidth(24)
        self.preview_icon_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview_icon_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.preview_icon_table.verticalHeader().setVisible(False)
        self.preview_icon_table.setVerticalHeader(None)
        self.preview_icon_table.horizontalHeader().setVisible(False)
        self.preview_icon_table.setHorizontalHeader(None)
        self.preview_icon_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview_icon_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview_icon_table.setShowGrid(False)
        self.preview_icon_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)

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

        self.module_frame.setLayout(module_layout)
        self.preview_frame.setLayout(preview_layout)

        content_layout.addWidget(self.module_frame, stretch=1)
        content_layout.addWidget(self.preview_frame, stretch=3)
        self.bottom_layout.addLayout(content_layout)

        # Add default rename module
        self.add_rename_module()

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
        self.vertical_splitter.setSizes([485, 235])

        self.main_layout.addWidget(footer_separator)
        self.main_layout.addWidget(footer_widget)

    def setup_signals(self) -> None:
        """
        Connects UI elements to their corresponding event handlers.
        """
        self.select_folder_button.clicked.connect(self.handle_folder_select)
        self.browse_folder_button.clicked.connect(self.handle_browse)

        self.file_table_view.clicked.connect(self.on_table_row_clicked)
        self.file_table_view.selectionModel().selectionChanged.connect(self.sync_selection_to_checked)
        self.model.sort_changed.connect(self.generate_preview_names)

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

        self.file_table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table_view.customContextMenuRequested.connect(self.handle_table_context_menu)

        self.file_table_view.doubleClicked.connect(self.handle_file_double_click)

        # --- Shortcuts ---
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.force_reload)
        QShortcut(QKeySequence("Ctrl+Shift+A"), self, activated=self.clear_all_selection)
        QShortcut(QKeySequence("Ctrl+I"), self, activated=self.invert_selection)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.handle_browse)

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

    def clear_all_selection(self) -> None:
        self.file_table_view.clearSelection()

    def invert_selection(self) -> None:
        selection_model = self.file_table_view.selectionModel()
        all_rows = self.model.rowCount()

        new_selection = QItemSelection()

        for row in range(all_rows):
            is_selected = selection_model.isRowSelected(row, QModelIndex())
            file = self.model.files[row]

            if is_selected:
                # Αφαίρεση από επιλογή και αποεπιλογή checkbox
                file.checked = False
            else:
                # Add to selection and set checked = True
                top_left = self.model.index(row, 0)
                bottom_right = self.model.index(row, self.model.columnCount() - 1)
                selection_range = QItemSelectionRange(top_left, bottom_right)
                new_selection.append(selection_range)
                file.checked = True

        # Ενημέρωση του πίνακα
        selection_model.clearSelection()
        selection_model.select(new_selection, QItemSelectionModel.Select)
        self.after_check_change()

    def rename_files(self) -> None:
        """
        Executes the file renaming process using active rename modules.
        Handles validation, conflict resolution, and updates FileItem attributes
        without touching the metadata cache (no remap).
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

        modules_data = [mod.to_dict() for mod in self.rename_modules]
        if not modules_data:
            self.set_status("No rename modules are active.", color="gray")
            CustomMessageDialog.show_warning(
                self, "Rename Warning", "No rename modules are active."
            )
            return

        logger.info(f"Starting rename process for {len(selected_files)} files...")

        # Instantiate the renamer logic
        renamer = Renamer(
            files=selected_files,
            modules_data=modules_data,
            metadata_cache=self.metadata_cache,  # remains unchanged
            parent=self,
            conflict_callback=CustomMessageDialog.rename_conflict_dialog,
            validator=self.filename_validator
        )

        results = renamer.rename()

        # Save current checked files before rename
        checked_paths = {f.full_path for f in self.model.files if f.checked}

        renamed_count = 0
        for result in results:
            if result.success:
                renamed_count += 1
                # Update FileItem filename and path to reflect rename
                item = next((f for f in self.files if f.full_path == result.old_path), None)
                if item:
                    item.filename = os.path.basename(result.new_path)
                    item.full_path = result.new_path
            elif result.skip_reason:
                logger.info(f"Skipped: {result.old_path} — Reason: {result.skip_reason}")
            elif result.error:
                logger.error(f"Error: {result.old_path} — {result.error}")

        self.set_status(f"Renamed {renamed_count} file(s).", color="green", auto_reset=True)
        logger.info(f"Rename process completed: {renamed_count} renamed, {len(results)} total")

        # Reload folder, skipping metadata scan to reuse existing cache
        self.last_action = "rename"
        self.load_files_from_folder(self.current_folder_path, skip_metadata=True)

        # Restore checked state after reload
        for file in self.model.files:
            file.checked = file.full_path in checked_paths

        self.header.update_state(self.model.files)
        self.file_table_view.viewport().update()
        logger.debug(f"[Rename] Restored {sum(f.checked for f in self.model.files)} checked out of {len(self.model.files)} files")

        # Ask user if they want to open the folder
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

        index = self.tree_view.currentIndex()
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

        ctrl_override = bool(QApplication.keyboardModifiers() & SKIP_METADATA_MODIFIER)

        skip_metadata, user_wants_scan = resolve_skip_metadata(
            ctrl_override=ctrl_override,
            total_files=len(valid_files),
            folder_path=folder_path,
            parent_window=self,
            default_skip=DEFAULT_SKIP_METADATA,
            threshold=LARGE_FOLDER_WARNING_THRESHOLD
        )

        self.skip_metadata_mode = skip_metadata

        is_large = len(valid_files) > LARGE_FOLDER_WARNING_THRESHOLD
        logger.info(
            f"Tree-selected folder: {folder_path}, skip_metadata={skip_metadata} "
            f"(ctrl={ctrl_override}, large={is_large}, wants_scan={user_wants_scan}, default={DEFAULT_SKIP_METADATA})"
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

        ctrl_override = bool(QApplication.keyboardModifiers() & SKIP_METADATA_MODIFIER)

        skip_metadata, user_wants_scan = resolve_skip_metadata(
            ctrl_override=ctrl_override,
            total_files=len(valid_files),
            folder_path=folder_path,
            parent_window=self,
            default_skip=DEFAULT_SKIP_METADATA,
            threshold=LARGE_FOLDER_WARNING_THRESHOLD
        )

        self.skip_metadata_mode = skip_metadata

        is_large = len(valid_files) > LARGE_FOLDER_WARNING_THRESHOLD
        logger.info(
            f"Tree-selected folder: {folder_path}, skip_metadata={skip_metadata} "
            f"(ctrl={ctrl_override}, large={is_large}, wants_scan={user_wants_scan}, default={DEFAULT_SKIP_METADATA})"
        )

        logger.warning(f"-> skip_metadata passed to loader: {skip_metadata}")
        self.load_files_from_folder(folder_path, skip_metadata=skip_metadata, force=force_reload)

        if hasattr(self, "dir_model") and hasattr(self, "tree_view"):
            index = self.dir_model.index(folder_path)
            if index.isValid():
                self.tree_view.setCurrentIndex(index)
                self.tree_view.scrollTo(index)

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

        self.header.setEnabled(True)
        self.header.update_state(file_items)
        self.update_files_label()
        self.update_preview_tables_from_pairs([])
        self.rename_button.setEnabled(False)
        self.file_table_view.viewport().update()

    def load_files_from_folder(self, folder_path: str, skip_metadata: bool = False, force: bool = False):

        normalized_new = os.path.abspath(os.path.normpath(folder_path))
        normalized_current = os.path.abspath(os.path.normpath(self.current_folder_path or ""))

        if normalized_new == normalized_current and not force:
            logger.info(f"[FolderLoad] Ignored reload of already loaded folder: {normalized_new}")
            self.set_status("Folder already loaded.", color="gray", auto_reset=True)
            return

        logger.info(f"Loading files from folder: {folder_path} (skip_metadata={skip_metadata})")

        if not (skip_metadata and self.last_action == "rename"):
            self.metadata_cache.clear()

        self.current_folder_path = folder_path
        self.metadata_loaded_paths.clear()

        file_items = self.get_file_items_from_folder(folder_path)

        if not file_items:
            short_name = os.path.basename(folder_path.rstrip("/\\"))
            self.show_file_table_placeholder(f"No supported files in '{short_name}'")
            self.clear_metadata_view()
            self.header.setEnabled(False)
            self.header.update_state([])
            self.set_status("No supported files found.", color="orange", auto_reset=True)
            return

        self.prepare_file_table(file_items)

        if skip_metadata:
            self.set_status("Metadata scan skipped.", color="gray", auto_reset=True)
            return

        self.set_status(f"Loading metadata for {len(file_items)} files...", color="blue")
        QTimer.singleShot(100, lambda: self.start_metadata_scan([f.full_path for f in file_items if f.full_path]))

    def start_metadata_scan(self, file_paths: list[str]) -> None:
        """
        Called slightly delayed to ensure UI is ready before metadata thread starts.
        """
        logger.warning("[DEBUG] start_metadata_scan CALLED")
        self.loading_dialog = CustomMessageDialog.show_waiting(self, "Analyzing files...")
        logger.warning("[DEBUG] show_waiting returned dialog")
        self.loading_dialog.activateWindow()
        self.loading_dialog.rejected.connect(self.cancel_metadata_loading)
        self.loading_dialog.set_progress_range(len(file_paths))

        self.load_metadata_in_thread(file_paths)

    def load_metadata_in_thread(self, file_paths: list[str] = None) -> None:
        logger.warning("[DEBUG] load_metadata_in_thread CALLED")
        self.cleanup_metadata_worker()

        if self.is_running_metadata_task():
            logger.warning("Worker already running — skipping new metadata scan.")
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Fallback: use all files if no specific file list is provided
        if file_paths is None:
            file_paths = [
                os.path.join(self.current_folder_path, f.filename)
                for f in self.model.files
            ]

        self.metadata_thread = QThread(self)
        self.metadata_worker = MetadataWorker(
            reader=self.metadata_reader,
            metadata_cache=self.metadata_cache,
            parent=None  # must be None to avoid parent thread interference
        )
        logger.warning(f"[DEBUG] MetadataWorker CREATED → {self.metadata_worker}")
        self.metadata_worker.moveToThread(self.metadata_thread)

        self.metadata_worker.progress.connect(self.on_metadata_progress)
        self.metadata_worker.finished.connect(self.finish_metadata_loading)
        self.metadata_worker.finished.connect(self.metadata_thread.quit)
        self.metadata_worker.finished.connect(self.metadata_worker.deleteLater)
        self.metadata_thread.finished.connect(self.metadata_thread.deleteLater)

        self.metadata_worker.file_path = file_paths

        # Safest possible launch: invoke run_batch directly inside thread
        self.metadata_thread.started.connect(lambda: QMetaObject.invokeMethod(
            self.metadata_worker,
            "run_batch",
            Qt.QueuedConnection
        ))

        logger.info(f"Starting metadata analysis for {len(file_paths)} files")
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

        self.set_status(f"Loading metadata for {len(file_paths)} file(s)...", color="blue")
        QTimer.singleShot(100, lambda: self.start_metadata_scan(file_paths))

    def load_metadata_for_files(self, file_items: list[FileItem], force: bool = False) -> None:
        """
        Loads metadata for the given list of FileItem objects.

        If the list contains a single file, metadata is loaded directly using the reader.
        For multiple files, a scan is initiated unless metadata already exists.

        Args:
            file_items (list[FileItem]): The files to process.
            force (bool): If True, load metadata even if already cached.
        """
        if not file_items:
            return

        if len(file_items) == 1:
            item = file_items[0]
            if not item or not item.full_path:
                return

            metadata = self.metadata_reader.read(item.full_path)
            if metadata:
                if force or item.metadata is None:
                    item.metadata = metadata
                    self.metadata_cache.set(item.full_path, metadata)
                    self.metadata_loaded_paths.add(item.full_path)
                    self.finish_metadata_loading({item.full_path: metadata})
            return

        if not force:
            file_items = [f for f in file_items if f.metadata is None]

        if file_items:
            self.start_metadata_scan_for_items(file_items)

    def reload_current_folder(self) -> None:
        # Optional: adjust if flags need to be preserved
        if self.current_folder_path:
            self.load_files_from_folder(self.current_folder_path, skip_metadata=False)

    def update_module_dividers(self) -> None:
        for index, module in enumerate(self.rename_modules):
            if hasattr(module, "divider"):
                module.divider.setVisible(index > 0)

    def add_rename_module(self) -> None:
        """
        Adds a new rename module widget to the scroll area.
        """
        module = RenameModuleWidget(parent_window=self)
        self.rename_modules.append(module)

        module.add_button.clicked.connect(self.add_rename_module)
        module.remove_requested.connect(lambda m=module: self.remove_rename_module(m))

        self.module_scroll_layout.addWidget(module)

        # --- Logging ---
        QTimer.singleShot(0, lambda: logger.info(
            f"[MainWindow] Added module of type: {getattr(module.current_module_widget, '__class__', type(None)).__name__}"
        ))

        self.update_module_dividers()

    def remove_rename_module(self, module_widget) -> None:
        """
        Removes a rename module from the scroll area.
        """
        if len(self.rename_modules) <= 1:
            msg = "You must have at least one active rename module."
            self.status_label.setText(msg)
            logger.info(f"[MainWindow] Prevented removal: {msg}")
            return

        try:
            self.rename_modules.remove(module_widget)

            # If there is a loaded module inside the wrapper:
            module_type = getattr(module_widget.current_module_widget, '__class__', type(None)).__name__
            logger.info(f"[MainWindow] Removed module of type: {module_type}")
        except ValueError:
            logger.warning("[MainWindow] Tried to remove unknown module (not in list).")

        self.module_scroll_layout.removeWidget(module_widget)
        module_widget.setParent(None)
        module_widget.deleteLater()
        logger.debug("[MainWindow] Module widget deleted and removed from layout.")

        self.update_module_dividers()
        logger.debug("[MainWindow] Module dividers updated after removal.")

        self.generate_preview_names()
        logger.debug("[MainWindow] Preview names regenerated after module removal.")

    def handle_header_toggle(self, checked: bool) -> None:
        """
        Triggered when the 'select all' checkbox in the table header is toggled.

        Applies the checked state to all files in the model, refreshes the UI,
        and regenerates the filename preview.

        Args:
            checked (bool): True if checkbox is checked, False if unchecked.
        """
        logger.debug(f'Header checkbox toggled: {checked}')

        # Apply checked state to all files
        for file in self.model.files:
            file.checked = checked

        # Refresh table and preview
        self.file_table_view.viewport().update()
        self.header.update_state(self.model.files)
        self.update_files_label()
        self.generate_preview_names()

    def generate_preview_names(self) -> None:
        """
        Generate new preview names for all selected files using current rename modules.
        Updates the preview map and UI elements accordingly.
        """
        selected_files = [f for f in self.model.files if f.checked]
        modules_data = [mod.to_dict(preview=True) for mod in self.rename_modules]

        self.preview_map.clear()
        self.preview_map = {file.filename: file for file in selected_files}

        name_pairs = []

        for idx, file in enumerate(selected_files):
            try:
                new_name = apply_rename_modules(modules_data, idx, file, self.metadata_cache)
                logger.debug(f"[Preview] {file.filename} -> {new_name}")
                name_pairs.append((file.filename, new_name))
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
        adjusted_width = max(250, max_width) + 100
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
            current (int): Number of files analyzed so far.
            total (int): Total number of files to analyze.
        """
        if self.metadata_worker is None:
            logger.warning("Progress signal received after worker was already cleaned up — ignoring.")
            return

        logger.debug(f"Metadata progress update: {current} of {total}")

        if getattr(self, "loading_dialog", None):
            self.loading_dialog.set_progress(current, total)
            self.loading_dialog.set_message(f"Analyzing file {current} of {total}...")
        else:
            logger.warning("Loading dialog not available during progress update — skipping UI update.")

    def finish_metadata_loading(self, metadata_dict: dict) -> None:
        """
        Slot called when the metadata worker completes successfully.

        Finalizes the metadata scan by updating the internal cache and UI,
        injecting metadata into file items, and restoring UI state. Also
        tears down the background thread and worker.

        Args:
            metadata_dict (dict): Dictionary containing filename -> metadata.
        """
        if self.metadata_worker is None:
            logger.warning("Received 'finished' signal after cleanup — ignoring.")
            return

        logger.info(f"Metadata loading complete. Loaded metadata for {len(metadata_dict)} files.")

        # Save metadata results and update the UI status label
        # self.metadata_cache.clear()
        self.metadata_cache.update(metadata_dict)

        count = len(metadata_dict)
        self.set_status(f"Metadata loaded for {count} file{'s' if count != 1 else ''}.", color="green", auto_reset=True)

        # Inject metadata into FileItems
        for file_item in self.files:
            filename = file_item.filename
            metadata = metadata_dict.get(filename)
            if isinstance(metadata, dict):
                file_item.metadata = metadata.copy()
            else:
                logger.warning(f"No valid metadata for {filename} — defaulting to empty dict.")
                file_item.metadata = {}

        # Immediately close the loading dialog if it's still showing
        if self.loading_dialog:
            self.loading_dialog.accept()
            self.loading_dialog = None
        else:
            logger.debug("Loading dialog already closed before finish handler.")

        # Restore cursor on next event loop cycle
        QTimer.singleShot(0, self._restore_cursor)

        # Disconnect signals, stop thread, and cleanup worker
        self.cleanup_metadata_worker()

        # Trigger preview refresh after metadata update
        self.generate_preview_names()

        # Add loaded paths to set
        for path in metadata_dict:
            self.metadata_loaded_paths.add(path)

        # Notify UI that metadata has changed
        self.model.dataChanged.emit(
            self.model.index(0, 0),
            self.model.index(len(self.model.files) - 1, 0),
            [Qt.UserRole]
)
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
        Called when the user presses ESC or closes the dialog during metadata scan.
        Retries once or twice if the worker isn't ready yet.
        """
        logger.info("User requested cancellation of metadata scan.")

        # 1. Restore cursor immediately
        QApplication.restoreOverrideCursor()

        # 2. Inform user via dialog (if shown)
        if self.loading_dialog:
            self.loading_dialog.set_message("Canceling metadata scan…")
            QTimer.singleShot(1000, self.loading_dialog.accept)
            QTimer.singleShot(1000, lambda: setattr(self, "loading_dialog", None))
        else:
            logger.debug("Cancel requested but loading dialog was not active.")

        # 3. Try to cancel worker if exists
        if self.metadata_worker:
            if not self.metadata_worker._cancelled:
                logger.debug("Calling metadata_worker.cancel()")
                self.metadata_worker.cancel()
            else:
                logger.info("Worker already marked as cancelled.")
        else:
            if retry_count < 3:
                logger.warning(f"metadata_worker is None — will retry cancel in 150ms (attempt {retry_count + 1})")
                QTimer.singleShot(150, lambda: self.cancel_metadata_loading(retry_count + 1))
            else:
                logger.error("Cancel failed: metadata_worker was never created.")

    def cleanup_metadata_worker(self) -> None:
        """
        Safely disconnect and tear down the metadata worker and its thread.
        This method is strictly for background cleanup and does NOT touch:
        - the progress/loading dialog
        - the override cursor
        """
        # 1. Disconnect progress signal from worker
        if getattr(self, "metadata_worker", None):
            try:
                self.metadata_worker.progress.disconnect(self.on_metadata_progress)
                logger.debug("Disconnected metadata_worker.progress signal.")
            except (RuntimeError, TypeError):
                logger.debug("Signal was already disconnected or worker not connected.")
            finally:
                self.metadata_worker = None
        else:
            logger.debug("No metadata_worker to disconnect.")

        # 2. Stop and delete the metadata thread
        if getattr(self, "metadata_thread", None):
            if self.metadata_thread.isRunning():
                logger.debug("Quitting metadata thread...")
                self.metadata_thread.quit()
                self.metadata_thread.wait()
                logger.debug("Metadata thread has been stopped.")

            self.metadata_thread = None  # IMPORTANT: we clear (the reference) for good

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

    def closeEvent(self, event) -> None:
        """
        Called when the main window is about to close.

        Ensures any background metadata threads are cleaned up
        properly before the application exits.
        """
        logger.info("Main window closing. Cleaning up metadata worker.")
        self.cleanup_metadata_worker()
        super().closeEvent(event)

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

        file_item = self.model.files[row]
        logger.debug(f"Row clicked: {file_item.filename}")

        # Prefer metadata from FileItem
        metadata = getattr(file_item, "metadata", None)

        if not metadata and file_item.full_path:
            # Fallback to cache if no metadata assigned
            metadata = self.metadata_cache.get(file_item.full_path)

        if isinstance(metadata, dict):
            # Update the filename in metadata display only
            display_metadata = dict(metadata)
            display_metadata["FileName"] = file_item.filename

            logger.debug(f"Metadata found for {file_item.filename}, displaying {len(display_metadata)} entries.")
            tree_model = build_metadata_tree_model(display_metadata)
            self.metadata_tree_view.setModel(tree_model)
            self.metadata_tree_view.expandAll()
            self.toggle_expand_button.setChecked(True)
            self.toggle_expand_button.setText("Collapse All")
        else:
            logger.warning(f"No metadata found for {file_item.filename}")
            self.show_empty_metadata_tree("No information available")

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
        self.model.set_files([])  # reset model with empty list
        self.show_file_table_placeholder(message)
        self.header.setEnabled(False) # disable header
        self.header.update_state([])

        self.update_files_label()

    def show_file_table_placeholder(self, message: str = "No files loaded") -> None:
        """
        Displays a placeholder row in the file table with a message.
        """
        placeholder_model = QStandardItemModel()
        placeholder_model.setHorizontalHeaderLabels(["", "Filename", "Type", "Modified"])

        row = [QStandardItem(), QStandardItem(message), QStandardItem(), QStandardItem()]

        for i, item in enumerate(row):
            font = item.font()
            font.setItalic(True)
            item.setFont(font)

            item.setForeground(Qt.gray)
            item.setEnabled(True)
            item.setSelectable(False)

            # Optional: center align only the message column
            if i == 1:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignCenter)

        placeholder_model.appendRow(row)
        self.file_table_view.setModel(placeholder_model)

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

    def handle_table_context_menu(self, position) -> None:
        """
        Handles the right-click context menu for the file table.
        Only shows actions relevant to metadata and selection logic.
        """
        index = self.file_table_view.indexAt(position)
        menu = QMenu(self)

        file_item = None

        if not self.model.files:
            action_none = menu.addAction("No files available")
            action_none.setEnabled(False)
            menu.exec_(self.file_table_view.viewport().mapToGlobal(position))
            return

        if index.isValid() and 0 <= index.row() < len(self.model.files):
            file_item = self.model.files[index.row()]
            short_name = elide_text(file_item.filename, MAX_LABEL_LENGTH)
            action_one = menu.addAction(f"Load metadata for '{short_name}'")
            action_one.setToolTip(f"<b>Full name:</b><br>{file_item.filename}")
            menu.addSeparator()
        else:
            action_one = None

        action_selected = menu.addAction("Load metadata for selected files")
        action_all = menu.addAction("Load metadata for all files")
        menu.addSeparator()

        action_invert = menu.addAction("🔁 Invert selection (Ctrl+I)")
        action_force_reload = menu.addAction("🔁 Reload folder (Ctrl+R)")

        # Execute menu
        action = menu.exec_(self.file_table_view.viewport().mapToGlobal(position))

        if action == action_one and file_item:
            self.load_metadata_for_files([file_item])
        elif action == action_selected:
            selected_indexes = self.file_table_view.selectionModel().selectedRows()
            selected = [self.model.files[i.row()] for i in selected_indexes if 0 <= i.row() < len(self.model.files)]
            self.load_metadata_for_files(selected)
        elif action == action_all:
            self.load_metadata_for_files(self.model.files)
        elif action == action_invert:
            self.invert_selection()
        elif action == action_force_reload:
            self.load_files_from_folder(self.current_folder_path, skip_metadata=False)

    def after_check_change(self) -> None:
        """
        Called after the checked state of any file is modified.

        Triggers UI refresh for the file table, updates the header state and label,
        and regenerates the filename preview.
        """
        self.file_table_view.viewport().update()
        self.header.update_state(self.model.files)
        self.update_files_label()
        self.generate_preview_names()

    def sync_selection_to_checked(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        """
        Syncs visual row selection with the internal .checked state,
        and updates preview if selection changed.
        """
        selection_model = self.file_table_view.selectionModel()
        selected_rows = set(idx.row() for idx in selection_model.selectedRows())
        changed = False

        for row, file in enumerate(self.model.files):
            is_selected = row in selected_rows
            if file.checked != is_selected:
                file.checked = is_selected
                changed = True

        if changed:
            self.file_table_view.viewport().update()
            self.header.update_state(self.model.files)
            self.update_files_label()
            self.generate_preview_names()

    def handle_file_double_click(self, index: QModelIndex) -> None:
        """
        Loads metadata for the file (even if already loaded), on double-click.
        """
        row = index.row()
        if 0 <= row < len(self.model.files):
            file = self.model.files[row]
            logger.info(f"[DoubleClick] Requested metadata reload for: {file.filename}")
            self.load_metadata_for_files([file], force=True)

    def handle_dropped_files(self, paths: list[str]) -> None:
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

        if len(file_items) > LARGE_FOLDER_WARNING_THRESHOLD:
            if not CustomMessageDialog.question(
                self,
                "Load metadata",
                f"Load metadata for {len(file_items)} files?",
                yes_text="Yes",
                no_text="Cancel"
            ):
                logger.info(f"[Drop] User cancelled metadata loading for {len(file_items)} files.")
                return

        logger.info(f"[Drop] Triggering metadata load for {len(file_items)} file(s)...")
        self.load_metadata_for_files(file_items, force=True)


