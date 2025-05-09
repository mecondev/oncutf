"""
Module: main_window.py

Author: Michael Economou
Date: 2025-05-01

This module defines the MainWindow class, which implements the primary user interface
for the oncutf application. The MainWindow provides a comprehensive
interface for browsing folders, selecting files, configuring rename operations through
modular components, previewing name changes, and executing batch file renaming.

The interface is divided into several key areas:
- A folder tree view for navigating the file system
- A file table for selecting and displaying files to be renamed
- An information panel showing metadata for selected files
- A module area where rename operations can be configured
- A preview area showing original and new filenames with validation indicators
- Controls for executing rename operations

Classes:
    MainWindow: The main application window and interface controller.

Usage:
    from main_window import MainWindow
"""


import os
import glob
import datetime
import platform
from typing import TYPE_CHECKING, List, Tuple, Dict
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QFrame, QScrollArea, QTableWidget, QTableView, QTreeView,
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
from workers.metadata_worker import MetadataWorker
from config import *

# Initialize Logger
from logger_helper import get_logger
logger = get_logger(__name__)


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        """
        Initializes the main window and sets up the layout.

        The main window is the central element of the application, hosting the folder tree,
        file list, metadata, and rename module areas.

        The layout is divided into two parts: the vertical splitter and the footer. The vertical
        splitter contains the folder tree, file list, and metadata areas. The footer contains
        the application version label and a separator.

        The window is set up with a central widget and a layout. The layout is divided into
        three parts: the vertical splitter, the bottom frame, and the footer. The vertical
        splitter contains the folder tree, file list, and metadata areas. The bottom frame
        contains the rename module and preview areas. The footer contains the application
        version label and a separator.

        The window is set up with a size of 1200x900 and a minimum size of 800x500. The window
        is centered on the screen and a filename validator is created.

        The color scheme is set up using the create_colored_icon function and the icons are
        prepared using the prepare_status_icons function.

        The signals are set up using the setup_signals method.

        The current folder path is initialized to None and the add_rename_module method is
        called to add the first rename module.

        :return: None
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


        # --- Central layout ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        # --- Vertical splitter ---
        self.vertical_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(self.vertical_splitter)

        # --- Top splitter (tree + files + info) ---
        self.splitter = QSplitter(Qt.Horizontal)
        self.vertical_splitter.addWidget(self.splitter)

        # --- Left: Tree view ---
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

        # --- Center: File list ---
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

        # --- Right: Metadata ---
        self.right_frame = QFrame()
        right_layout = QVBoxLayout(self.right_frame)
        right_layout.addWidget(QLabel("Information"))

        # --- Metadata Table Setup
        self.metadata_table_view = QTableView()
        self.metadata_table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.metadata_table_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.metadata_table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.metadata_table_view.verticalHeader().setVisible(False)
        self.metadata_model = QStandardItemModel(self)
        self.metadata_model.setColumnCount(2)
        self.metadata_model.setHorizontalHeaderLabels(["Key", "Value"])
        self.metadata_table_view.horizontalHeader().setStretchLastSection(True)
        self.metadata_table_view.setModel(self.metadata_model)
        right_layout.addWidget(self.metadata_table_view)

        # --- Splitter sizes ---
        self.splitter.addWidget(self.left_frame)
        self.splitter.addWidget(self.center_frame)
        self.splitter.addWidget(self.right_frame)
        self.splitter.setSizes([250, 600, 150])

        # --- Bottom frame: modules + preview ---
        self.bottom_frame = QFrame()
        self.bottom_layout = QVBoxLayout(self.bottom_frame)
        self.bottom_layout.setSpacing(0)
        self.bottom_layout.setContentsMargins(0, 0, 0, 0)

        # --- Horizontal layout inside bottom frame ---
        content_layout = QHBoxLayout()

        # === MODULE AREA (LEFT) ===
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

        # === PREVIEW AREA (RIGHT) ===
        self.preview_frame = QFrame()
        preview_layout = QVBoxLayout(self.preview_frame)

        self.old_label = QLabel("Old file(s) name(s)")
        self.new_label = QLabel("New file(s) name(s)")

        self.old_name_table = QTableWidget(0, 1)
        self.old_name_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.old_name_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.old_name_table.setWordWrap(False)
        self.old_name_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.old_name_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.old_name_table.verticalHeader().setVisible(False)
        self.old_name_table.setVerticalHeader(None)
        self.old_name_table.horizontalHeader().setVisible(False)
        self.old_name_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)

        self.new_name_table = QTableWidget(0, 1)
        self.new_name_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.new_name_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.new_name_table.setWordWrap(False)
        self.new_name_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.new_name_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.new_name_table.verticalHeader().setVisible(False)
        self.new_name_table.setVerticalHeader(None)
        self.new_name_table.horizontalHeader().setVisible(False)
        self.new_name_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)

        self.icon_table = QTableWidget(0, 1)
        self.icon_table.setObjectName("iconTable")  # Σημαντικό για το QSS!
        self.icon_table.setFixedWidth(24)
        # self.icon_table.setColumnWidth(0, 40)
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

        footer_separator = QFrame()
        footer_separator.setFrameShape(QFrame.HLine)
        footer_separator.setFrameShadow(QFrame.Sunken)

        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(10, 4, 10, 4)
        self.version_label = QLabel("oncutf v1.0")
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
        Rename files according to the preview table.

        Shows a progress bar and counts the number of files that were actually renamed.
        If a file with the new name already exists, asks the user about overwrite behavior.
        Shows a wait cursor during the operation.
        """
        if not self.current_folder_path:
            self.status_label.setText("No folder selected.")
            return

        # Ask overwrite behavior once
        overwrite_existing = CustomMessageDialog.question(
            self,
            "Overwrite Behavior",
            "A file with the new name already exists. Overwrite?",
            yes_text="Overwrite",
            no_text="Skip"
        )

        # Set wait cursor
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Count selected files
            total_files = sum(file.checked for file in self.model.files)
            if total_files == 0:
                self.status_label.setText("No files selected for renaming.")
                return

            # # Setup progress bar
            # self.rename_progress.setVisible(True)
            # self.rename_progress.setRange(0, total_files)
            # self.rename_progress.setValue(0)
            # self.status_label.setText("Renaming files...")

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

                # Skip if exists and user chose to skip
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

                self.rename_progress.setValue(renamed_count)

            # Reload file list at the end
            self.load_files_from_folder(self.current_folder_path)
        finally:
            # Restore cursor and finalize UI
            QApplication.restoreOverrideCursor()
            self.rename_progress.setVisible(False)
            self.status_label.setText(f"Renamed {renamed_count} file(s).")

    # TODO: For large batches, consider offloading this method to a QThread or
    # using QRunnable+QThreadPool to keep the UI responsive during renaming.

    def setup_signals(self) -> None:
        """
        Sets up signal connections for the UI components.

        Connects button clicks to their respective handlers for selecting and browsing folders,
        selecting files, generating preview names, and renaming files. Synchronizes the vertical
        scroll bars of the old and new name tables, as well as the icon table, to maintain
        consistent scrolling behavior across these views.
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

        Connects the module's add button to the add_rename_module method, and
        the remove button to the remove_rename_module method. Also connects
        the module's updated signal to the generate_preview_names method.

        Adds the module to the scroll layout, and calls update_module_dividers
        to ensure that the dividers are correctly placed. Finally, calls
        generate_preview_names to update the preview names.

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
        Removes the given rename module widget from the scroll area.

        If the given module is present in the list of rename modules, it is removed.
        The module is then removed from the scroll layout, and its parent is set to
        None. The module is then deleted. Finally, the dividers are updated and the
        preview names are regenerated.

        :param module_widget: The rename module widget to remove.
        :type module_widget: RenameModuleWidget
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
        Updates the visibility of the divider widgets between rename modules.

        The divider between two rename modules is only visible if the module
        above it is not the first module in the list.

        """
        for index, module in enumerate(self.rename_modules):
            if hasattr(module, "divider"):
                module.divider.setVisible(index > 0)

    def load_files_from_folder(self, folder_path: str, skip_metadata: bool = False) -> None:
        """
        Loads supported files from the given folder into the model and optionally
        launches metadata extraction in a separate thread.

        Args:
            folder_path (str): The path of the folder to scan.
            skip_metadata (bool): If True, metadata analysis is skipped.
        """
        logger.info(">>> load_files_from_folder CALLED for: %s", folder_path)

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

        # Sync state
        self.header.update_state(self.model.files)
        self.update_files_label()
        self.generate_preview_names()

        if skip_metadata:
            logger.info("Skipping metadata scan (Ctrl was pressed).")
            return

        # Otherwise, begin metadata loading
        self.table_view.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        file_paths = [os.path.join(folder_path, file.filename) for file in self.model.files]

        logger.info("Creating loading dialog...")
        QApplication.processEvents()
        self.loading_dialog = CustomMessageDialog.show_waiting(self, "Analyzing files...")
        logger.info("Dialog shown. Proceeding with metadata worker.")

        # Check if progress bar exists
        if not self.loading_dialog.progress_bar:
            logger.warning("Loading dialog has no progress bar.")

        # Set the total count early — BEFORE worker starts
        self.loading_dialog.set_progress_range(len(file_paths))

        logger.info("Loading metadata for %d files", len(file_paths))
        # Delay for testing
        QTimer.singleShot(200, lambda: self.load_metadata_in_thread(file_paths))

    def handle_header_toggle(self, checked: bool) -> None:
        """
        Called when the checkbox in the header is toggled.

        Sets all files to the given checked state and triggers UI updates.

        :param checked: The checked state to set for all files.
        :type checked: bool
        """
        for file in self.model.files:
            file.checked = checked

        self.table_view.viewport().update()
        self.header.update_state(self.model.files)
        self.update_files_label()
        self.generate_preview_names()

    def generate_preview_names(self) -> None:
        """
        Updates the preview tables by generating new filenames based on the
        active rename modules and the currently selected files.

        Called when the user toggles the checkbox in the header, selects a
        different folder, or adds/removes a rename module.

        :return: None
        """
        modules_data = [m.get_data() for m in self.rename_modules]

        selected_files = [f for f in self.model.files if f.checked]
        if not selected_files:
            self.rename_button.setEnabled(False)
            self.rename_button.setToolTip("No files selected")
            self.update_preview_tables_from_pairs([])
            return

        new_names, has_error, tooltip_msg = generate_preview_logic(
            files=selected_files,
            modules_data=modules_data,
            validator=self.filename_validator
        )

        self.update_preview_tables_from_pairs(new_names)
        self.rename_button.setEnabled(not has_error)
        self.rename_button.setToolTip(tooltip_msg)

    def compute_max_filename_width(self, file_list: list[FileItem]) -> int:
        """
        Computes the maximum width (in pixels) needed to display the longest filename in
        the given list of FileItem objects.

        The width is computed as 8 times the length of the longest filename, but capped
        between 250 and 1000 pixels.

        :param file_list: A list of FileItem objects.
        :return: The maximum width needed to display the longest filename.
        :rtype: int
        """
        max_len = max((len(file.filename) for file in file_list), default=0)
        return min(max(8 * max_len, 250), 1000)

    def center_window(self) -> None:
        """
        Centers the main window on the screen.

        Computes the geometry of the window and its center point, then moves
        the window to the center of the screen by setting its top-left corner
        to the screen center point minus half of the window's width and height.

        :return: None
        """
        window_geometry = self.frameGeometry()
        screen_center = QDesktopWidget().availableGeometry().center()
        window_geometry.moveCenter(screen_center)
        self.move(window_geometry.topLeft())

    def handle_browse(self: 'MainWindow') -> None:
        """
        Opens a folder selection dialog and loads files from the selected folder.

        If Ctrl is held, metadata scan is skipped.
        ALT key is commented out due to Linux window manager conflicts.

        Also updates the tree view to reflect the selected folder.
        """
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", "/")

        if folder_path:
            # Detect keyboard modifiers
            modifiers = QApplication.keyboardModifiers()
            skip_metadata = modifiers & Qt.ControlModifier

            # ALT key support disabled for now
            # skip_metadata = modifiers & Qt.AltModifier

            logger.info("Folder selected: %s", folder_path)
            logger.info("Ctrl pressed? %s", bool(skip_metadata))

            self.load_files_from_folder(folder_path, skip_metadata=skip_metadata)

            # Update tree view to reflect selected folder
            if hasattr(self, "dir_model") and hasattr(self, "tree_view"):
                index = self.dir_model.index(folder_path)
                if index.isValid():
                    self.tree_view.setCurrentIndex(index)
                    self.tree_view.scrollTo(index)

    def handle_select(self) -> None:
        """
        Loads files from the folder currently selected in the tree view.

        If Ctrl is held while clicking, metadata scan is skipped.
        """
        index = self.tree_view.currentIndex()
        if not index.isValid():
            logger.warning("No folder selected in tree view.")
            return

        folder_path = self.dir_model.filePath(index)

        modifiers = QApplication.keyboardModifiers()
        skip_metadata = modifiers & Qt.ControlModifier

        # ALT is commented out due to window manager conflict
        # skip_metadata = modifiers & Qt.AltModifier

        logger.info("Folder selected via tree: %s", folder_path)
        logger.info("Ctrl pressed? %s", bool(skip_metadata))

        self.load_files_from_folder(folder_path, skip_metadata=skip_metadata)

    def update_files_label(self) -> None:
        """
        Updates the label displaying the number of selected files.

        Updates the label text according to the current selection state of the files.
        If there are no files, the label shows "Files". If there are files, the label
        shows how many of them are selected from the total number of files.

        :return: None
        """
        total = len(self.model.files)
        selected = sum(1 for file in self.model.files if file.checked)

        if total == 0:
            self.files_label.setText("Files")
        else:
            self.files_label.setText(f"Files {selected} selected from {total}")

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
        Updates preview tables with color-coded icons and tooltips based on filename validity.

        Args:
            name_pairs (list[tuple[str, str]]): List of (original, new) filename pairs.
        """
        # logger.info("Updating preview tables with %d name pairs", len(name_pairs))

        self.old_name_table.setRowCount(0)
        self.new_name_table.setRowCount(0)
        self.icon_table.setRowCount(0)

        all_names = [name for pair in name_pairs for name in pair]
        max_width = max([self.fontMetrics().horizontalAdvance(name) for name in all_names], default=250)
        adjusted_width = max(250, max_width) + 100
        self.old_name_table.setColumnWidth(0, adjusted_width)
        self.new_name_table.setColumnWidth(0, adjusted_width)

        seen = set()
        duplicates = set()
        for _, new in name_pairs:
            if new in seen:
                duplicates.add(new)
            else:
                seen.add(new)

        stats = {"unchanged": 0, "invalid": 0, "duplicate": 0, "valid": 0}

        for row, (old_name, new_name) in enumerate(name_pairs):
            self.old_name_table.insertRow(row)
            self.new_name_table.insertRow(row)
            self.icon_table.insertRow(row)

            old_item = QTableWidgetItem(old_name)
            new_item = QTableWidgetItem(new_name)

            status = "valid"
            tooltip = "Ready to rename"

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

            stats[status] += 1

            # Create icon
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

            if USE_PREVIEW_BACKGROUND:
                bg = QBrush(QColor(PREVIEW_COLORS[status]))
                old_item.setBackground(bg)
                new_item.setBackground(bg)
                icon_item.setBackground(bg)

            self.old_name_table.setItem(row, 0, old_item)
            self.new_name_table.setItem(row, 0, new_item)
            self.icon_table.setItem(row, 0, icon_item)
            # logger.info(status)
        # Update status bar
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
        Launch metadata loading in a background QThread.

        Steps:
        1. Tear down any existing worker/thread.
        2. Guard against concurrent runs.
        3. Switch cursor to busy.
        4. Prepare full file paths.
        5. Create QThread + worker, move worker to thread.
        6. Wire up all signals (progress, finish, cleanup).
        7. Start thread, which will invoke load_batch().
        """

        # 1) Clean up any in-flight task (without touching UI cursor/dialog)
        self.cleanup_metadata_worker()

        # 2) Prevent multiple simultaneous runs
        if self.is_running_metadata_task():
            logger.warning("Worker already running — skipping new metadata scan.")
            return

        # 3) Show busy cursor
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # 4) Build absolute paths list from the model
        files = [
            os.path.join(self.current_folder_path, f.filename)
            for f in self.model.files
        ]

        # 5) Instantiate thread and worker, and move worker into the new thread
        self.metadata_thread = QThread(self)
        self.metadata_worker = MetadataWorker(self.metadata_reader)
        self.metadata_worker.moveToThread(self.metadata_thread)

        # 6) Connect signals

        #   a) Update progress bar in the main GUI
        self.metadata_worker.progress.connect(self.on_metadata_progress)

        #   b) On successful finish, restore cursor, close dialog, update UI
        self.metadata_worker.finished.connect(self.finish_metadata_loading)

        #   c) Thread teardown: quit & delete both thread and worker when done
        self.metadata_worker.finished.connect(self.metadata_thread.quit)
        self.metadata_worker.finished.connect(self.metadata_worker.deleteLater)
        self.metadata_thread.finished.connect(self.metadata_thread.deleteLater)

        # 7) When the thread starts, kick off the actual loading job
        self.metadata_thread.started.connect(lambda: self.metadata_worker.load_batch(files))

        logger.info(f"Starting metadata analysis for {len(files)} files")
        self.metadata_thread.start()

    def on_metadata_progress(self, current: int, total: int) -> None:
        """
        Slot connected to the progress signal of the metadata worker.

        Updates the progress dialog with the current and total number of files being analyzed.

        Args:
            current (int): Number of files analyzed so far.
            total (int): Total number of files to be analyzed.
        """
        logger.debug("Progress: %d / %d", current, total)

        if getattr(self, "loading_dialog", None):
            self.loading_dialog.set_progress(current, total)
            self.loading_dialog.set_message(f"Analyzing file {current} of {total}...")
        else:
            logger.warning("Progress update received but loading_dialog is None")

    def finish_metadata_loading(self, metadata_dict):
        """
        Called when metadata_worker emits finished successfully.
        Update UI, close dialog, then restore cursor _after_ the event loop
        has had την ευκαιρία να επεξεργαστεί το override cursor.
        """
        logger.info("Done loading metadata.")

        # 1) Save results & update status
        self.metadata_cache = metadata_dict
        self.status_label.setText(f"Metadata loaded for {len(metadata_dict)} files.")

        # 2) Close the progress dialog immediately
        if self.loading_dialog:
            self.loading_dialog.accept()
            self.loading_dialog = None

        # 3) Schedule cursor restore on the next event loop iteration
        QTimer.singleShot(0, self._restore_cursor)

        # 4) Finally, clean up thread/worker signals
        logger.debug("Re-enabling table view after metadata loading")
        self.table_view.setEnabled(True)
        self.cleanup_metadata_worker()

    def _restore_cursor(self):
        """
        Pop the override-cursor stack and force immediate repaint.
        """
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
        QApplication.processEvents()

    def cancel_metadata_loading(self):
        """
        User-requested cancel: signal worker, restore cursor, show 'Canceling…',
        then close dialog after a short delay and clean up.
        """
        logger.info("User cancelled metadata scan.")
        # Signal the worker to cancel its task
        if self.metadata_worker:
            self.metadata_worker.cancel()

        # Restore cursor and inform the user
        QApplication.restoreOverrideCursor()
        if self.loading_dialog:
            self.loading_dialog.set_message("Canceling metadata scan…")
            # Close dialog after delay, to let message be read
            QTimer.singleShot(1000, self.loading_dialog.accept)
            # Clear reference after it’s closed
            QTimer.singleShot(1000, lambda: setattr(self, "loading_dialog", None))
            logger.debug("Re-enabling table view after metadata loading")
            QTimer.singleShot(1000, lambda: self.table_view.setEnabled(True))
        # Finally, tear down thread/worker
        self.cleanup_metadata_worker()

    def cleanup_metadata_worker(self):
        """
        Tear down any in-flight metadata worker and thread.
        Only handles background teardown, no UI cursor or dialog logic here.
        """
        # Disconnect progress signal if still connected
        if getattr(self, "metadata_worker", None):
            try:
                self.metadata_worker.progress.disconnect(self.on_metadata_progress)
                logger.debug("Disconnected metadata_worker.progress signal.")
            except (RuntimeError, TypeError):
                logger.debug("No active connection to disconnect.")
            finally:
                self.metadata_worker = None

        # Quit and delete the QThread
        if getattr(self, "metadata_thread", None):
            logger.debug("Stopping metadata thread.")
            self.metadata_thread.quit()
            self.metadata_thread.wait()
            self.metadata_thread = None

    def on_metadata_error(self, message: str) -> None:
        """
        Slot connected to the error signal of the metadata worker.

        Restores the UI cursor, closes and deletes the progress dialog,
        and displays an error message with the given message.

        Args:
            message (str): The error message from the metadata worker.
        """
        logger.error("Metadata error: %s", message)

        QApplication.restoreOverrideCursor()

        if hasattr(self, "loading_dialog") and self.loading_dialog:
            self.loading_dialog.close()
            self.loading_dialog = None
            logger.info("Loading dialog closed after error.")

        # here we stop the worker and thread
        try:
            if self.metadata_worker:
                self.metadata_worker.cancel()
                self.metadata_worker.progress.disconnect(self.on_metadata_progress)
        except Exception as e:
            logger.debug("Could not disconnect progress: %s", e)

        if self.metadata_thread:
            self.metadata_thread.quit()
            self.metadata_thread.wait()
            self.metadata_thread = None

        QMessageBox.critical(self, "Metadata Error", f"Failed to read metadata:\n{message}")

    def closeEvent(self, event):
        self.cleanup_metadata_worker()
        super().closeEvent(event)

    def is_running_metadata_task(self) -> bool:
        """
        Checks whether the metadata worker and thread are currently running.

        Returns
        -------
        bool
            True if the worker and thread are alive and active, False otherwise.
        """
        return (
            getattr(self, "metadata_thread", None) is not None
            and self.metadata_thread.isRunning()
        )

    def populate_metadata_table(self, metadata: dict) -> None:
        """
        Populate the existing metadata model with new rows.

        Args:
            metadata (dict): mapping of metadata tag → value
        """
        # Restore normal cursor if you set it to waiting before
        QApplication.restoreOverrideCursor()

        # 1. Clear all previous rows
        row_count = self.metadata_model.rowCount()
        if row_count:
            self.metadata_model.removeRows(0, row_count)

        # 2. Append each key/value pair as a new row
        for key, value in metadata.items():
            items = [
                QStandardItem(str(key)),
                QStandardItem(str(value))
            ]
            self.metadata_model.appendRow(items)

        # 3. Resize columns to fit their contents
        self.metadata_table_view.resizeColumnsToContents()

    def on_table_row_clicked(self, index) -> None:
        """
        Slot connected to the itemSelectionChanged signal of the table view.

        Populates the metadata table with the metadata of the clicked row.

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


        self.populate_metadata_table(metadata)
