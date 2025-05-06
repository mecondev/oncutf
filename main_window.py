# main_window.py
# Author: Firstname Lastname
# Date: 2025-05-01
# Description: The main window of the application

import os
import glob
import datetime
import platform
from typing import TYPE_CHECKING, List, Tuple, Dict
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QFrame, QScrollArea, QTableWidget, QTableView, QTreeView,
    QFileSystemModel, QAbstractItemView, QAbstractScrollArea, QSizePolicy, QProgressBar, QHeaderView,
    QTableWidgetItem, QDesktopWidget
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
from utils.file_loader import FileLoaderMixin
from utils.filename_validator import FilenameValidator
from utils.preview_generator import generate_preview_names as generate_preview_logic
from utils.icons import create_colored_icon
from utils.icon_cache import prepare_status_icons
from utils.metadata_reader import MetadataReader
from workers.metadata_worker import MetadataWorker

from config import *
import logging
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow, FileLoaderMixin):

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

        # --- Window setup ---
        self.setWindowTitle("Batch File Renamer")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.center_window()
        self.filename_validator = FilenameValidator()

        self.create_colored_icon = create_colored_icon
        self.icon_paths = prepare_status_icons()
        self.metadata_reader = MetadataReader()


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
        self.metadata_table_view = QTableView()
        self.metadata_table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.metadata_table_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.metadata_table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.metadata_table_view.verticalHeader().setVisible(False)
        right_layout.addWidget(self.metadata_table_view)

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

        self.rename_progress = QProgressBar()
        self.rename_progress.setFixedWidth(120)
        self.rename_progress.setVisible(False)
        controls_layout.addWidget(self.rename_progress)

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
        self.version_label = QLabel("Batch File Renamer v1.0")
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
        if not self.current_folder_path:
            self.status_label.setText("No folder selected.")
            return

        total_files = sum(file.checked for file in self.model.files)
        if total_files == 0:
            self.status_label.setText("No files selected for renaming.")
            return

        choice = QMessageBox.question(
            self,
            "Overwrite Behavior",
            "If a file with the new name already exists, what should we do?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        overwrite_existing = (choice == QMessageBox.StandardButton.Yes)

        self.rename_progress.setVisible(True)
        self.rename_progress.setRange(0, total_files)
        self.rename_progress.setValue(0)
        self.status_label.setText("Renaming files...")

        renamed_count = 0
        for index, file in enumerate(self.model.files):
            if not file.checked:
                continue

            preview_pairs = [(self.old_name_table.item(r, 0).text(), self.new_name_table.item(r, 0).text())
                            for r in range(self.old_name_table.rowCount())]
            preview_dict = dict(preview_pairs)
            new_name = preview_dict.get(file.filename, file.filename)

            old_path = os.path.join(self.current_folder_path, file.filename)
            new_path = os.path.join(self.current_folder_path, new_name)

            try:
                if os.path.exists(new_path):
                    if not overwrite_existing:
                        self.status_label.setText(f"Skipped (exists): {new_name}")
                        continue

                os.rename(old_path, new_path)
                renamed_count += 1

            except Exception as e:
                logger.error(f"Failed to rename '{file.filename}' → '{new_name}': {e}")
                self.status_label.setText(f"Error: {file.filename} → {new_name}")
                continue

            self.rename_progress.setValue(renamed_count)

        self.rename_progress.setVisible(False)
        self.status_label.setText(f"Renamed {renamed_count} file(s).")

        self.load_files_from_folder(self.current_folder_path)

    def setup_signals(self) -> None:
        self.select_folder_button.clicked.connect(self.handle_select)
        self.browse_folder_button.clicked.connect(self.handle_browse)
        self.table_view.clicked.connect(self.on_file_selected)
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
        for index, module in enumerate(self.rename_modules):
            if hasattr(module, "divider"):
                module.divider.setVisible(index > 0)

    def load_files_from_folder(self, folder_path: str) -> None:
        self.current_folder_path = folder_path
        all_files = glob.glob(os.path.join(folder_path, "*"))
        logger.info("current file path: %s", self.current_folder_path)
        self.model.beginResetModel()
        self.model.files.clear()

        for file_path in sorted(all_files):
            ext = os.path.splitext(file_path)[1][1:].lower()
            if ext in ALLOWED_EXTENSIONS:
                filename = os.path.basename(file_path)
                date = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                self.model.files.append(FileItem(filename, ext, date))

        self.model.endResetModel()

        self.header.update_state(self.model.files)
        self.update_files_label()
        self.generate_preview_names()

    def handle_header_toggle(self, checked: bool) -> None:
        for file in self.model.files:
            file.checked = checked

        self.table_view.viewport().update()
        self.header.update_state(self.model.files)
        self.update_files_label()
        self.generate_preview_names()

    def generate_preview_names(self) -> None:
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
        max_len = max((len(file.filename) for file in file_list), default=0)
        return min(max(8 * max_len, 250), 1000)

    def center_window(self) -> None:
        window_geometry = self.frameGeometry()
        screen_center = QDesktopWidget().availableGeometry().center()
        window_geometry.moveCenter(screen_center)
        self.move(window_geometry.topLeft())

    def update_files_label(self) -> None:
        total = len(self.model.files)
        selected = sum(1 for file in self.model.files if file.checked)

        if total == 0:
            self.files_label.setText("Files")
        else:
            self.files_label.setText(f"Files {selected} selected from {total}")

    def get_identity_name_pairs(self) -> list[tuple[str, str]]:
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
        adjusted_width = max(250, max_width) + 20
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

    def on_file_selected(self, index):
        logger.info("File selected")
        row = index.row()
        file_item = self.model.files[row]
        file_path = self.current_folder_path

        metadata = self.metadata_reader.read_specific_fields(file_path, [
            "FileName", "FileSize", "CreateDate", "ModifyDate", "Duration", "MIMEType"
        ])
        logger.info("file_item: %s", file_item)
        logger.info("file_path: %s", file_path)
        self.populate_metadata_table(metadata)

    def populate_metadata_table(self, metadata: dict):
        logger.info("Populating metadata table")
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Key", "Value"])

        for key, value in metadata.items():
            model.appendRow([
                QStandardItem(str(key)),
                QStandardItem(str(value))
            ])

        self.metadata_table_view.setModel(model)
        self.metadata_table_view.resizeColumnsToContents()

    def load_metadata_in_thread(self, file_path: str):
        self.thread = QThread()
        self.worker = MetadataWorker(file_path)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_metadata_ready)
        self.worker.error.connect(self.on_metadata_error)

        # Clean-up
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_metadata_ready(self, metadata: dict):
        self.metadata_table_view.setRowCount(0)
        self.metadata_table_view.setColumnCount(2)
        self.metadata_table_view.setHorizontalHeaderLabels(["Tag", "Value"])

        for row, (key, value) in enumerate(metadata.items()):
            self.metadata_table_view.insertRow(row)
            self.metadata_table_view.setItem(row, 0, QTableWidgetItem(str(key)))
            self.metadata_table_view.setItem(row, 1, QTableWidgetItem(str(value)))

    def on_metadata_error(self, message: str):
        QMessageBox.critical(self, "Metadata Error", f"Failed to read metadata:\n{message}")
