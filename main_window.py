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
from typing import TYPE_CHECKING, List, Tuple, Dict
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QFrame, QScrollArea, QTableWidget, QTableView, QTreeView, QFileDialog,
    QFileSystemModel, QAbstractItemView, QAbstractScrollArea, QSizePolicy, QProgressBar,
    QHeaderView, QTableWidgetItem, QDesktopWidget, QMessageBox
)
from PyQt5.QtCore import Qt, QDir, QRect, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QPalette, QFont, QBrush, QColor, QIcon, QPixmap, QPainter,
    QStandardItemModel, QStandardItem
)

from models.file_table_model import FileTableModel
from models.file_item import FileItem
from widgets.checkbox_header import CheckBoxHeader
from widgets.rename_module_widget import RenameModuleWidget
from widgets.custom_msgdialog import CustomMessageDialog
from utils.filename_validator import FilenameValidator
from utils.preview_generator import generate_preview_names as generate_preview_logic
from utils.icons import create_colored_icon
from utils.icon_cache import prepare_status_icons
from utils.metadata_reader import MetadataReader
from utils.build_metadata_tree_model import build_metadata_tree_model
from widgets.metadata_worker import MetadataWorker
from config import *

# Initialize Logger
from logger_helper import get_logger
logger = get_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        """
        Initializes the main window and sets up the layout.
        """
        super().__init__()

        self.metadata_thread = None
        self.metadata_worker = None
        self.loading_dialog = None
        self.metadata_cache = {}
        self._metadata_worker_cancel_requested = False

        # --- Window setup ---
        self.setWindowTitle("Batch File Renamer")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.center_window()
        self.filename_validator = FilenameValidator()

        self.create_colored_icon = create_colored_icon
        self.icon_paths = prepare_status_icons()
        self.metadata_reader = MetadataReader()
        self.metadata_cache = {}  # filename → metadata dict

        # Central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        # Main vertical splitter
        self.vertical_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(self.vertical_splitter)

        # Top horizontal splitter: tree view | file table | metadata
        self.splitter = QSplitter(Qt.Horizontal)
        self.vertical_splitter.addWidget(self.splitter)

        # Left panel: Tree View
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

        # Center panel: Table view for file listing
        self.center_frame = QFrame()
        center_layout = QVBoxLayout(self.center_frame)
        self.files_label = QLabel("Files")
        center_layout.addWidget(self.files_label)

        self.table_view = QTableView()
        self.header = CheckBoxHeader(Qt.Horizontal, self.table_view, parent_window=self)
        self.model = FileTableModel(parent_window=self)
        self.table_view.setModel(self.model)
        self.table_view.setHorizontalHeader(self.header)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSortingEnabled(True)
        self.table_view.setWordWrap(False)
        self.table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table_view.setColumnWidth(0, 23)
        self.table_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table_view.setColumnWidth(2, 55)
        self.table_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table_view.setColumnWidth(3, 135)
        center_layout.addWidget(self.table_view)

        # Right panel and more will continue in the next chunk...
        # Right panel: Metadata viewer
        self.right_frame = QFrame()
        right_layout = QVBoxLayout(self.right_frame)
        right_layout.addWidget(QLabel("Information"))

        self.metadata_tree_view = QTreeView()
        self.metadata_tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.metadata_tree_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.metadata_tree_view.setHeaderHidden(False)
        self.metadata_tree_view.setExpandsOnDoubleClick(True)
        self.metadata_tree_view.setUniformRowHeights(True)
        self.metadata_tree_view.setAnimated(True)
        right_layout.addWidget(self.metadata_tree_view)

        self.splitter.addWidget(self.left_frame)
        self.splitter.addWidget(self.center_frame)
        self.splitter.addWidget(self.right_frame)
        self.splitter.setSizes([250, 600, 150])

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
        self.rename_modules = []
        module_layout.addWidget(self.module_scroll_area)

        # === Right: Rename preview ===
        self.preview_frame = QFrame()
        preview_layout = QVBoxLayout(self.preview_frame)
        self.old_label = QLabel("Old file(s) name(s)")
        self.new_label = QLabel("New file(s) name(s)")

        self.old_name_table = QTableWidget(0, 1)
        self.new_name_table = QTableWidget(0, 1)
        self.icon_table = QTableWidget(0, 1)

        for table in [self.old_name_table, self.new_name_table]:
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            table.setWordWrap(False)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setSelectionMode(QAbstractItemView.NoSelection)
            table.verticalHeader().setVisible(False)
            table.setVerticalHeader(None)
            table.horizontalHeader().setVisible(False)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)

        self.icon_table.setObjectName("iconTable")
        self.icon_table.setFixedWidth(24)
        self.icon_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.icon_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.icon_table.verticalHeader().setVisible(False)
        self.icon_table.setVerticalHeader(None)
        self.icon_table.horizontalHeader().setVisible(False)
        self.icon_table.setHorizontalHeader(None)
        self.icon_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.icon_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.icon_table.setShowGrid(False)
        self.icon_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)

        table_pair_layout = QHBoxLayout()
        old_layout = QVBoxLayout()
        new_layout = QVBoxLayout()
        icon_layout = QVBoxLayout()

        old_layout.addWidget(self.old_label)
        old_layout.addWidget(self.old_name_table)
        new_layout.addWidget(self.new_label)
        new_layout.addWidget(self.new_name_table)
        icon_layout.addWidget(QLabel(" "))
        icon_layout.addWidget(self.icon_table)

        table_pair_layout.addLayout(old_layout)
        table_pair_layout.addLayout(new_layout)
        table_pair_layout.addLayout(icon_layout)
        preview_layout.addLayout(table_pair_layout)

        controls_layout = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setTextFormat(Qt.RichText)
        controls_layout.addWidget(self.status_label, stretch=1)

        self.rename_button = QPushButton("Rename")
        self.rename_button.setEnabled(False)
        self.rename_button.setFixedWidth(120)
        controls_layout.addWidget(self.rename_button)
        preview_layout.addLayout(controls_layout)

        content_layout.addWidget(self.module_frame, stretch=1)
        content_layout.addWidget(self.preview_frame, stretch=3)
        self.bottom_layout.addLayout(content_layout)

        # --- Footer ---
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

        self.vertical_splitter.addWidget(self.splitter)
        self.vertical_splitter.addWidget(self.bottom_frame)
        self.vertical_splitter.setSizes([485, 235])

        layout.addWidget(self.vertical_splitter)
        layout.addWidget(footer_separator)
        layout.addWidget(footer_widget)

        self.setup_signals()
        self.current_folder_path = None
        self.add_rename_module()
    def rename_files(self) -> None:
        """
        Rename files based on the rename preview table.
        Asks the user for overwrite confirmation. Updates status label accordingly.
        """
        if not self.current_folder_path:
            self.status_label.setText("No folder selected.")
            return

        overwrite_existing = CustomMessageDialog.question(
            self,
            "Overwrite Behavior",
            "A file with the new name already exists. Overwrite?",
            yes_text="Overwrite",
            no_text="Skip"
        )

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            total_files = sum(file.checked for file in self.model.files)
            if total_files == 0:
                self.status_label.setText("No files selected for renaming.")
                return

            renamed_count = 0
            preview_pairs = [
                (self.old_name_table.item(r, 0).text(),
                 self.new_name_table.item(r, 0).text())
                for r in range(self.old_name_table.rowCount())
            ]
            preview_dict = dict(preview_pairs)

            for file in self.model.files:
                if not file.checked:
                    continue

                old_name = file.filename
                new_name = preview_dict.get(old_name, old_name)
                old_path = os.path.join(self.current_folder_path, old_name)
                new_path = os.path.join(self.current_folder_path, new_name)

                if os.path.exists(new_path) and not overwrite_existing:
                    self.status_label.setText(f"Skipped (exists): {new_name}")
                    continue

                try:
                    os.rename(old_path, new_path)
                    renamed_count += 1
                except Exception as e:
                    logger.error(f"Failed to rename '{old_name}' → '{new_name}': {e}")
                    CustomMessageDialog.information(
                        self,
                        "Rename Failed",
                        f"Failed to rename '{old_name}' → '{new_name}': {e}"
                    )
                    continue

            self.load_files_from_folder(self.current_folder_path)
        finally:
            QApplication.restoreOverrideCursor()
            self.status_label.setText(f"Renamed {renamed_count} file(s).")

    def setup_signals(self) -> None:
        """
        Connects UI elements to their corresponding event handlers.
        """
        self.select_folder_button.clicked.connect(self.handle_select)
        self.browse_folder_button.clicked.connect(self.handle_browse)
        self.table_view.clicked.connect(self.on_table_row_clicked)
        self.model.sort_changed.connect(self.generate_preview_names)
        self.rename_button.clicked.connect(self.rename_files)

        self.old_name_table.verticalScrollBar().valueChanged.connect(
            self.new_name_table.verticalScrollBar().setValue
        )
        self.new_name_table.verticalScrollBar().valueChanged.connect(
            self.old_name_table.verticalScrollBar().setValue
        )
        self.old_name_table.verticalScrollBar().valueChanged.connect(
            self.icon_table.verticalScrollBar().setValue
        )

    def add_rename_module(self) -> None:
        """
        Adds a new rename module widget to the scroll area.
        """
        module = RenameModuleWidget()
        self.rename_modules.append(module)
        module.add_button.clicked.connect(self.add_rename_module)
        module.remove_requested.connect(lambda m=module: self.remove_rename_module(m))

        if hasattr(module, "updated"):
            module.updated.connect(self.generate_preview_names)

        self.module_scroll_layout.addWidget(module)
        self.update_module_dividers()
        self.generate_preview_names()

    def remove_rename_module(self, module_widget) -> None:
        """
        Removes a rename module from the scroll area.
        """
        if len(self.rename_modules) <= 1:
            self.status_label.setText("At least one module must remain.")
            return

        if module_widget in self.rename_modules:
            self.rename_modules.remove(module_widget)

        self.module_scroll_layout.removeWidget(module_widget)
        module_widget.setParent(None)
        module_widget.deleteLater()

        self.update_module_dividers()
        self.generate_preview_names()

    def update_module_dividers(self) -> None:
        """
        Updates the divider visibility between rename modules.
        """
        for index, module in enumerate(self.rename_modules):
            if hasattr(module, "divider"):
                module.divider.setVisible(index > 0)

    def load_files_from_folder(self, folder_path: str, skip_metadata: bool = False) -> None:
        """
        Loads supported files from the given folder into the table model.
        Optionally launches metadata scanning in a background thread (unless Ctrl is held).

        Args:
            folder_path (str): Absolute path to the folder.
            skip_metadata (bool): If True, metadata scan is skipped (e.g. Ctrl key pressed).
        """
        # Prevent loading if a scan is already in progress
        if self.metadata_thread and self.metadata_thread.isRunning():
            logger.warning("Metadata scan already running — folder change blocked.")
            CustomMessageDialog.information(
                self,
                "Busy",
                "Metadata is still being scanned. Please cancel or wait."
            )
            return

        logger.info(">>> load_files_from_folder CALLED for: %s", folder_path)

        # --- File discovery ---
        self.current_folder_path = folder_path
        all_files = glob.glob(os.path.join(folder_path, "*"))

        self.model.beginResetModel()
        self.model.files.clear()
        self.model.folder_path = folder_path

        for file_path in sorted(all_files):
            ext = os.path.splitext(file_path)[1][1:].lower()
            if ext in ALLOWED_EXTENSIONS:
                filename = os.path.basename(file_path)
                modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                self.model.files.append(FileItem(filename, ext, modified))
        self.model.endResetModel()

        logger.info("Loaded %d supported files from %s", len(self.model.files), folder_path)

        # --- UI sync ---
        self.header.update_state(self.model.files)
        self.update_files_label()
        self.generate_preview_names()

        if skip_metadata:
            logger.info("Skipping metadata scan (Ctrl was pressed).")
            return

        # --- Start metadata scan ---
        file_paths = [
            os.path.join(folder_path, file.filename)
            for file in self.model.files
        ]

        logger.info("Preparing metadata loading for %d files", len(file_paths))

        # Set wait cursor to indicate work
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        # Show custom dialog
        self.loading_dialog = CustomMessageDialog.show_waiting(self, "Analyzing files...")
        logger.info("Loading dialog shown.")

        if not self.loading_dialog.progress_bar:
            logger.warning("Loading dialog has no progress bar.")

        # Set progress range before starting worker
        self.loading_dialog.set_progress_range(len(file_paths))

        # Use a slight delay to allow GUI to render first
        QTimer.singleShot(200, lambda: self.load_metadata_in_thread(file_paths))

    def handle_header_toggle(self, checked: bool) -> None:
        """
        Triggered when the 'select all' checkbox in the table header is toggled.

        Applies the checked state to all files in the model, refreshes the UI,
        and regenerates the filename preview.

        Args:
            checked (bool): True if checkbox is checked, False if unchecked.
        """
        logger.debug("Header checkbox toggled: %s", checked)

        # Apply checked state to all files
        for file in self.model.files:
            file.checked = checked

        # Refresh table and preview
        self.table_view.viewport().update()
        self.header.update_state(self.model.files)
        self.update_files_label()
        self.generate_preview_names()

    def generate_preview_names(self) -> None:
        """
        Generates and updates the preview name tables based on:
        - The current selection of files
        - The active rename modules

        It performs validation, detects duplicates or errors,
        and enables/disables the Rename button accordingly.
        """
        # Collect rename instructions from all active modules
        modules_data = [module.get_data() for module in self.rename_modules]

        # Filter selected files from the model
        selected_files = [file for file in self.model.files if file.checked]

        if not selected_files:
            logger.debug("No files selected — disabling Rename button and clearing preview.")
            self.rename_button.setEnabled(False)
            self.rename_button.setToolTip("No files selected")
            self.update_preview_tables_from_pairs([])
            return

        logger.debug("Generating preview names for %d selected files using %d modules.",
                    len(selected_files), len(modules_data))

        # Run the preview generation logic
        new_names, has_error, tooltip_msg = generate_preview_logic(
            files=selected_files,
            modules_data=modules_data,
            validator=self.filename_validator
        )

        # Update preview tables with the result
        self.update_preview_tables_from_pairs(new_names)

        # Update Rename button state and tooltip
        self.rename_button.setEnabled(not has_error)
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

        logger.debug("Longest filename length: %d chars → width: %d px (clamped)", max_len, clamped_width)
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

    def handle_browse(self: 'MainWindow') -> None:
        """
        Triggered when the user clicks the 'Browse Folder' button.
        Opens a folder selection dialog, checks file count, prompts
        user if the folder is large, and optionally skips metadata scan.

        Also updates the folder tree selection to reflect the newly selected folder.
        """
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", "/")
        if not folder_path:
            logger.info("Folder selection canceled by user.")
            return

        # Count supported files in the selected folder
        all_files = glob.glob(os.path.join(folder_path, "*"))
        valid_files = [f for f in all_files if os.path.splitext(f)[1][1:].lower() in ALLOWED_EXTENSIONS]

        if len(valid_files) > LARGE_FOLDER_WARNING_THRESHOLD:
            proceed = CustomMessageDialog.question(
                self,
                "Large Folder",
                f"This folder contains {len(valid_files)} supported files.\n"
                "Scanning may take time. Continue?",
                yes_text="Proceed",
                no_text="Cancel"
            )
            if not proceed:
                logger.info("User canceled loading large folder: %s", folder_path)
                return

        # Detect keyboard modifiers
        modifiers = QApplication.keyboardModifiers()
        skip_metadata = modifiers & Qt.ControlModifier
        logger.info("Folder selected: %s", folder_path)
        logger.info("Ctrl pressed (skip_metadata)? %s", bool(skip_metadata))

        self.load_files_from_folder(folder_path, skip_metadata=skip_metadata)

        # Update folder tree to reflect selection
        if hasattr(self, "dir_model") and hasattr(self, "tree_view"):
            index = self.dir_model.index(folder_path)
            if index.isValid():
                self.tree_view.setCurrentIndex(index)
                self.tree_view.scrollTo(index)

    def handle_select(self) -> None:
        """
        Triggered when the user clicks the 'Select Folder' button.

        It loads files from the folder currently selected in the folder tree.
        If the Ctrl key is held, metadata scanning is skipped.

        This function:
        - Validates the selected folder index.
        - Reads keyboard modifiers.
        - Delegates file loading to load_files_from_folder().
        """
        index = self.tree_view.currentIndex()
        if not index.isValid():
            logger.warning("No folder selected in tree view.")
            return

        folder_path = self.dir_model.filePath(index)

        # Check if Ctrl is held to optionally skip metadata scan
        modifiers = QApplication.keyboardModifiers()
        skip_metadata = modifiers & Qt.ControlModifier

        logger.info("Folder selected via tree: %s", folder_path)
        logger.debug("Ctrl modifier pressed? %s", bool(skip_metadata))

        self.load_files_from_folder(folder_path, skip_metadata=skip_metadata)

    def update_files_label(self) -> None:
        """
        Updates the UI label that displays the count of selected files.

        If no files are loaded, the label shows a default "Files".
        Otherwise, it shows how many files are currently selected
        out of the total number loaded.
        """
        total_files = len(self.model.files)
        selected_files = sum(file.checked for file in self.model.files)

        if total_files == 0:
            self.files_label.setText("Files")
        else:
            self.files_label.setText(f"Files {selected_files} selected from {total_files}")

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
        Updates the preview tables with original and new filenames,
        applying color-coded icons and tooltips to indicate status
        (valid, unchanged, invalid, duplicate).

        Args:
            name_pairs (list[tuple[str, str]]): List of (original, new) filename pairs.
        """
        self.old_name_table.setRowCount(0)
        self.new_name_table.setRowCount(0)
        self.icon_table.setRowCount(0)

        # Dynamically calculate column width based on filename lengths
        all_names = [name for pair in name_pairs for name in pair]
        max_width = max((self.fontMetrics().horizontalAdvance(name) for name in all_names), default=250)
        adjusted_width = max(250, max_width) + 100
        self.old_name_table.setColumnWidth(0, adjusted_width)
        self.new_name_table.setColumnWidth(0, adjusted_width)

        # Detect duplicates among new names
        seen, duplicates = set(), set()
        for _, new in name_pairs:
            if new in seen:
                duplicates.add(new)
            else:
                seen.add(new)

        # Track preview status counts
        stats = {"unchanged": 0, "invalid": 0, "duplicate": 0, "valid": 0}

        for row, (old_name, new_name) in enumerate(name_pairs):
            self.old_name_table.insertRow(row)
            self.new_name_table.insertRow(row)
            self.icon_table.insertRow(row)

            old_item = QTableWidgetItem(old_name)
            new_item = QTableWidgetItem(new_name)

            # Determine status for this filename pair
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

            stats[status] += 1

            # Icon with shape/color per status
            icon_pixmap = self.create_colored_icon(
                fill_color=PREVIEW_COLORS[status],
                shape=PREVIEW_INDICATOR_SHAPE,
                size_x=16,
                size_y=16,
                border_color="#222222",
                border_thickness=1
            )

            icon_item = QTableWidgetItem()
            icon_item.setIcon(QIcon(icon_pixmap))
            icon_item.setToolTip(tooltip)

            # Optionally color background
            if USE_PREVIEW_BACKGROUND:
                bg = QBrush(QColor(PREVIEW_COLORS[status]))
                old_item.setBackground(bg)
                new_item.setBackground(bg)
                icon_item.setBackground(bg)

            # Add row items
            self.old_name_table.setItem(row, 0, old_item)
            self.new_name_table.setItem(row, 0, new_item)
            self.icon_table.setItem(row, 0, icon_item)

        # Compose and update status summary
        status_msg = (
            f"<img src='{self.icon_paths['valid']}' width='14' height='14'/> "
            f"<span style='color:#ccc;'>Valid: {stats['valid']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{self.icon_paths['unchanged']}' width='14' height='14'/> "
            f"<span style='color:#ccc;'>Unchanged: {stats['unchanged']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{self.icon_paths['invalid']}' width='14' height='14'/> "
            f"<span style='color:#ccc;'>Invalid: {stats['invalid']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{self.icon_paths['duplicate']}' width='14' height='14'/> "
            f"<span style='color:#ccc;'>Duplicates: {stats['duplicate']}</span>"
        )
        self.status_label.setText(status_msg)

    def load_metadata_in_thread(self, file_paths: list[str]) -> None:
        """
        Starts metadata analysis in a background thread using MetadataWorker.

        This method ensures the UI remains responsive by offloading file metadata
        extraction to a separate QThread. It performs the following steps:

        1. Clean up any previous metadata task.
        2. Prevent re-entry if a task is already running.
        3. Show the busy cursor to indicate a background operation.
        4. Prepare absolute paths to all selected files.
        5. Set up the QThread and assign the MetadataWorker to it.
        6. Connect signals for progress reporting and proper cleanup.
        7. Start the thread, which triggers the metadata loading asynchronously.
        """
        # Step 1: Clean up any previous task (if user switched folders quickly)
        self.cleanup_metadata_worker()

        # Step 2: Protect against concurrent execution
        if self.is_running_metadata_task():
            logger.warning("Worker already running — skipping new metadata scan.")
            return

        # Step 3: Indicate background work with a wait cursor
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Step 4: Resolve full paths from current model
        files = [
            os.path.join(self.current_folder_path, f.filename)
            for f in self.model.files
        ]

        # Step 5: Create the thread and move worker into it
        self.metadata_thread = QThread(self)
        self.metadata_worker = MetadataWorker(self.metadata_reader)
        self.metadata_worker.moveToThread(self.metadata_thread)

        # Step 6: Connect signals

        # a) Metadata progress updates
        self.metadata_worker.progress.connect(self.on_metadata_progress)

        # b) When done, update UI and clean up
        self.metadata_worker.finished.connect(self.finish_metadata_loading)

        # c) Ensure proper teardown when work completes
        self.metadata_worker.finished.connect(self.metadata_thread.quit)
        self.metadata_worker.finished.connect(self.metadata_worker.deleteLater)
        self.metadata_thread.finished.connect(self.metadata_thread.deleteLater)

        # Step 7: Start processing as soon as thread begins
        self.metadata_thread.started.connect(lambda: self.metadata_worker.load_batch(files))

        logger.info("Starting metadata analysis for %d files", len(files))
        self.metadata_thread.start()

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

        logger.debug("Metadata progress update: %d of %d", current, total)

        if getattr(self, "loading_dialog", None):
            self.loading_dialog.set_progress(current, total)
            self.loading_dialog.set_message(f"Analyzing file {current} of {total}...")
        else:
            logger.warning("Loading dialog not available during progress update — skipping UI update.")

    def finish_metadata_loading(self, metadata_dict: dict) -> None:
        """
        Slot called when the metadata worker completes successfully.

        Finalizes the metadata scan by updating the internal cache and UI,
        closing the progress dialog, and restoring the cursor. Teardown of
        the background worker and thread is performed last.

        Args:
            metadata_dict (dict): Dictionary containing filename → metadata.
        """
        if self.metadata_worker is None:
            logger.warning("Received 'finished' signal after cleanup — ignoring.")
            return

        logger.info("Metadata loading complete. Loaded metadata for %d files.", len(metadata_dict))

        # 1) Save metadata results and update the UI status label
        self.metadata_cache = metadata_dict
        self.status_label.setText(f"Metadata loaded for {len(metadata_dict)} files.")

        # 2) Immediately close the loading dialog if it's still showing
        if self.loading_dialog:
            self.loading_dialog.accept()
            self.loading_dialog = None
        else:
            logger.debug("Loading dialog already closed before finish handler.")

        # 3) Defer cursor restoration to next event loop cycle
        QTimer.singleShot(0, self._restore_cursor)

        # 4) Teardown background resources (signals, thread, worker)
        self.cleanup_metadata_worker()

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

    def cancel_metadata_loading(self) -> None:
        """
        Triggered when the user clicks 'Cancel' during metadata scanning.

        Steps:
        1. Restore the cursor immediately for better UX.
        2. Update the progress dialog to inform the user that cancellation is in progress.
        3. Close the dialog after a short delay (for readability).
        4. Signal the metadata worker to stop (if it's active).
        """
        logger.info("User requested cancellation of metadata scan.")

        # 1. Restore cursor immediately
        QApplication.restoreOverrideCursor()

        # 2. Inform user via dialog (if shown)
        if self.loading_dialog:
            self.loading_dialog.set_message("Canceling metadata scan…")

            # Let user read the message briefly, then close
            QTimer.singleShot(1000, self.loading_dialog.accept)
            QTimer.singleShot(1000, lambda: setattr(self, "loading_dialog", None))
        else:
            logger.warning("Cancel requested but loading dialog was not active.")

        # 3. Signal cancellation to the worker
        if self.metadata_worker:
            if not self.metadata_worker._cancelled:
                logger.debug("Calling metadata_worker.cancel()")
                self.metadata_worker.cancel()
            else:
                logger.info("Worker was already cancelled — no need to signal again.")
        else:
            logger.warning("Cancel requested but metadata_worker is None.")

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
            self.metadata_thread = None

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
        logger.error("Metadata error: %s", message)

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
        QMessageBox.critical(self, "Metadata Error", f"Failed to read metadata:\n\n{message}")

    def closeEvent(self, event):
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
        logger.debug("Metadata task running? %s", running)
        return running

    def populate_metadata_table(self, metadata: dict) -> None:
        """
        Populates the metadata table view with key-value pairs.

        This function clears any existing rows and inserts the provided metadata.
        Each dictionary item is added as a row in the model, with the key in the
        first column and the corresponding value in the second.

        Args:
            metadata (dict): A dictionary where keys are metadata tags and
                            values are their associated data.
        """
        # Ensure cursor is restored in case it was left in busy mode
        QApplication.restoreOverrideCursor()

        model = build_metadata_tree_model(metadata)
        self.metadata_tree_view.setModel(model)
        self.metadata_tree_view.expandToDepth(1)
        self.metadata_tree_view.resizeColumnToContents(0)
        logger.debug("Metadata table populated with %d entries.", len(metadata))

    def on_table_row_clicked(self, index) -> None:
        """
        Slot connected to the itemSelectionChanged signal of the table view.

        Populates the metadata tree view with the metadata of the clicked row.
        Supports nested dictionaries and lists via expandable tree structure.

        Args:
            index (QModelIndex): The index of the clicked row.
        """
        if index.column() == 0:
            return

        filename = self.model.files[index.row()].filename
        metadata = self.metadata_cache.get(filename, {})

        logger.debug("Row clicked: %s", filename)
        if metadata:
            logger.debug("Metadata found for %s", filename)
        else:
            logger.warning("No metadata found for %s", filename)

        tree_model = build_metadata_tree_model(metadata)
        self.metadata_tree_view.setModel(tree_model)
        self.metadata_tree_view.expandAll()

