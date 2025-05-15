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
    QFileSystemModel, QAbstractItemView,  QSizePolicy, QHeaderView, QTableWidgetItem,
    QDesktopWidget, QMessageBox, QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QDir, QUrl, QThread, QTimer, QModelIndex, QPropertyAnimation
from PyQt5.QtGui import (
    QPainter, QBrush, QColor, QIcon, QDesktopServices, QStandardItem, QStandardItemModel
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
from utils.preview_engine import apply_rename_modules
from utils.metadata_reader import MetadataReader
from utils.build_metadata_tree_model import build_metadata_tree_model
from widgets.metadata_worker import MetadataWorker
from utils.metadata_cache import MetadataCache
from utils.metadata_utils import resolve_skip_metadata
from utils.renamer import Renamer

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
        self.loading_dialog = None
        self.metadata_cache = MetadataCache()
        self._metadata_worker_cancel_requested = False

        self.create_colored_icon = create_colored_icon
        self.icon_paths = prepare_status_icons()

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
    def setup_main_window(self):
        """Configure main window properties."""
        self.setWindowTitle("oncutf - Batch File Renamer and More")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.center_window()

    def setup_main_layout(self):
        """Setup central widget and main layout."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

    def setup_splitters(self):
        """Setup vertical and horizontal splitters."""
        self.vertical_splitter = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.vertical_splitter)

        self.horizontal_splitter = QSplitter(Qt.Horizontal)
        self.vertical_splitter.addWidget(self.horizontal_splitter)
        self.vertical_splitter.setSizes([485, 235])

    def setup_left_panel(self):
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

    def setup_center_panel(self):
        """Setup center panel (file table view)."""
        self.center_frame = QFrame()
        center_layout = QVBoxLayout(self.center_frame)

        self.files_label = QLabel("Files")
        center_layout.addWidget(self.files_label)

        self.file_table_view = QTableView()
        self.file_table_view.verticalHeader().setVisible(False)
        self.header = CheckBoxHeader(Qt.Horizontal, self.file_table_view, parent_window=self)
        self.model = FileTableModel(parent_window=self)
        self.show_file_table_placeholder("No folder selected")

        # Table View column adjustments
        self.file_table_view.setHorizontalHeader(self.header)
        self.header.setEnabled(False)
        self.show_file_table_placeholder("No folder selected")
        self.file_table_view.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self.file_table_view.setAlternatingRowColors(True)
        self.file_table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table_view.setSelectionMode(QAbstractItemView.NoSelection)
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

        center_layout.addWidget(self.file_table_view)
        self.horizontal_splitter.addWidget(self.center_frame)

    def setup_right_panel(self):
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
        self.metadata_tree_view = QTreeView()
        self.metadata_tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.metadata_tree_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.metadata_tree_view.setUniformRowHeights(True)
        self.metadata_tree_view.expandToDepth(1)
        self.metadata_tree_view.setRootIsDecorated(False)
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

    def setup_bottom_layout(self):
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

    def setup_footer(self):
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

    def rename_files(self) -> None:
        """
        Executes the file renaming process using active modules and updates metadata cache.
        Displays custom dialogs for conflicts or issues.
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

        # === Rename ===
        renamer = Renamer(
            files=selected_files,
            modules_data=modules_data,
            metadata_cache=self.metadata_cache,
            parent=self,
            conflict_callback=CustomMessageDialog.rename_conflict_dialog,
            validator=self.filename_validator
        )

        results = renamer.rename()

        # === Uncheck all to avoid confusion ===
        self.handle_header_toggle(checked=False)

        renamed_count = 0
        for result in results:
            if result.success:
                logger.info(f"Renamed: {result.old_path} → {result.new_path}")
                renamed_count += 1
            elif result.skip_reason:
                logger.info(f"Skipped: {result.old_path} — Reason: {result.skip_reason}")
            elif result.error:
                logger.error(f"Error: {result.old_path} — {result.error}")

        self.set_status(f"Renamed {renamed_count} file(s).", color="green", auto_reset=True)
        logger.info(f"Rename process completed: {renamed_count} renamed, {len(results)} total")

        # === Reload folder but skip metadata (για να κρατήσουμε τα παλιά με cached meta) ===
        self.last_action = "rename"
        self.load_files_from_folder(self.current_folder_path, skip_metadata=True)

        # === Ask user if they want to open folder ===
        if renamed_count > 0:
            if CustomMessageDialog.question(
                self,
                "Rename Complete",
                f"{renamed_count} file(s) renamed.\nOpen the folder?",
                yes_text="Open Folder",
                no_text="Close"
            ):
                QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_folder_path))

    def reload_current_folder(self):
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

        # if isinstance(module.current_module_widget, MetadataModule):
        #     fields = self.get_common_metadata_fields()
        #     if fields:
        #         module.current_module_widget.set_fields_from_list(fields)


        module.add_button.clicked.connect(self.add_rename_module)
        module.remove_requested.connect(lambda m=module: self.remove_rename_module(m))

        self.module_scroll_layout.addWidget(module)

        # --- Logging ---
        mod_type = getattr(module.current_module_widget, '__class__', type(None)).__name__
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

            # Αν υπάρχει φορτωμένο module μέσα στο wrapper:
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

    def load_files_from_folder(self, folder_path: str, skip_metadata: bool = False) -> None:
        """
        Loads supported files from the given folder into the table model.
        Optionally launches metadata scanning in a background thread (unless Ctrl is held).
        """
        logger.warning(f"-> ENTERED load_files_from_folder with skip_metadata = {skip_metadata}")

        if self.metadata_thread and self.metadata_thread.isRunning():
            logger.warning("Metadata scan already running — folder change blocked.")
            CustomMessageDialog.information(
                self,
                "Busy",
                "Metadata is still being scanned. Please cancel or wait."
            )
            return
        self.metadata_cache.clear()
        logger.debug("Metadata cache cleared before new folder load.")

        logger.info(f">>> load_files_from_folder CALLED for: {folder_path}")
        self.current_folder_path = folder_path

        all_files = glob.glob(os.path.join(folder_path, "*"))
        file_items = []

        for file_path in sorted(all_files):
            ext = os.path.splitext(file_path)[1][1:].lower()
            if ext in ALLOWED_EXTENSIONS:
                filename = os.path.basename(file_path)
                modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                file_items.append(FileItem(filename, ext, modified, full_path=file_path))  # ✅ προσθήκη full_path

        if not file_items:
            logger.info("No supported files found.")
            short_name = os.path.basename(folder_path.rstrip("/\\"))
            self.show_file_table_placeholder(f"No supported files in '{short_name}'")
            self.clear_metadata_view()
            self.header.setEnabled(False)
            self.header.update_state([])
            self.set_status("No supported files found.", color="orange", auto_reset=True)
            return

        # Apply model and sync UI
        self.file_table_view.setModel(self.model)
        self.model.set_files(file_items)
        self.model.folder_path = folder_path
        self.files = file_items

        logger.info("Loaded %d supported files from %s", len(file_items), folder_path)

        self.header.setEnabled(True)
        self.header.update_state(file_items)
        self.update_files_label()
        self.generate_preview_names()

        logger.warning(f"[CHECK] skip_metadata arg type: {type(skip_metadata)} → value: {skip_metadata!r}")
        if skip_metadata:
            reason = {
                "folder_select": "Ctrl held or large folder skip",
                "browse": "Ctrl held or large folder skip",
                "rename": "metadata already scanned, skip post-rename",
                None: "unknown context"
            }.get(self.last_action, self.last_action)

            logger.info("Skipping metadata scan: %s", reason)
            self.set_status("Metadata scan skipped.", color="gray", auto_reset=True)
            return

        # Prepare list of full file paths for metadata thread
        # file_paths = [os.path.join(folder_path, f.filename) for f in file_items]
        file_paths = [f.full_path for f in file_items if f.full_path]


        logger.info("Preparing metadata loading for %d files", len(file_paths))
        self.set_status(f"Loading metadata for {len(file_paths)} files...", color="blue")

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        self.loading_dialog = CustomMessageDialog.show_waiting(self, "Analyzing files...")
        logger.info("Loading dialog shown.")

        if not self.loading_dialog.progress_bar:
            logger.warning("Loading dialog has no progress bar.")

        self.loading_dialog.set_progress_range(len(file_paths))
        logger.debug("Metadata scan paths:")
        for p in file_paths:
            logger.debug(f" → {p}")

        logger.debug("Calling load_metadata_in_thread immediately.")
        self.load_metadata_in_thread(file_paths)

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
        self.file_table_view.viewport().update()
        self.header.update_state(self.model.files)
        self.update_files_label()
        self.generate_preview_names()

    def generate_preview_names(self, source_widget=None) -> None:
        """
        Generates and updates the preview name tables based on:
        - The current selection of files
        - The active rename modules

        It performs validation, detects duplicates or errors,
        and enables/disables the Rename button accordingly.
        """
        logger.info("[MainWindow] generate_preview_names triggered by: %s", source_widget.__class__.__name__ if source_widget else "Unknown")
        logger.debug("[Preview] Skip metadata mode is: %s", self.skip_metadata_mode)

        # Collect rename instructions from all active modules
        modules_data = []
        for i, module in enumerate(self.rename_modules):
            mod = module.current_module_widget
            if mod:
                try:
                    data = mod.get_data()
                    logger.debug(f"[Preview] Module {i} ({mod.__class__.__name__}) -> {data}")
                    modules_data.append(data)
                except Exception as e:
                    logger.warning(f"Error getting data from module {i}: {e}")
                    modules_data.append({})

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

        # Determine if modules are effectively "inactive"
        def is_module_active(mod: dict) -> bool:
            if mod["type"] == "specified_text":
                return bool(mod.get("text"))
            elif mod["type"] == "counter":
                return True
            elif mod["type"] == "metadata":
                return bool(mod.get("field"))
            return False

        has_active_modules = any(is_module_active(mod) for mod in modules_data)

        if not has_active_modules:
            # No module affects output: use original name
            name_pairs = [(file.filename, file.filename) for file in selected_files]
            logger.debug("[Preview] Using original filenames as preview (no active modules).")
        else:
            name_pairs = []
            for idx, file in enumerate(selected_files):
                try:
                    new_name = apply_rename_modules(modules_data, idx, file, self.metadata_cache)
                    logger.debug(f"[Preview] {file.filename} -> {new_name}")
                    name_pairs.append((file.filename, new_name))
                except Exception as e:
                    logger.warning(f"Failed to generate preview for {file.filename}: {e}")
                    name_pairs.append((file.filename, file.filename))

        # Update the tables and button states
        self.update_preview_tables_from_pairs(name_pairs)

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

        logger.debug("Longest filename length: %d chars -> width: %d px (clamped)", max_len, clamped_width)
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

    def handle_folder_select(self) -> None:
        """
        It loads files from the folder currently selected in the folder tree.
        If the Ctrl key is held, metadata scanning is skipped.

        Triggered when the user clicks the 'Select Folder' button.

        This function:
        - Validates the selected folder index.
        - Delegates file loading to load_files_from_folder().
        """
        self.last_action = "folder_select"

        index = self.tree_view.currentIndex()
        if not index.isValid():
            logger.warning("No folder selected in tree view.")
            return

        self.clear_file_table("No folder selected")
        self.clear_metadata_view()
        folder_path = self.dir_model.filePath(index)

        # Load the full directory listing
        all_files = glob.glob(os.path.join(folder_path, "*"))
        valid_files = [
            f for f in all_files
            if os.path.splitext(f)[1][1:].lower() in ALLOWED_EXTENSIONS
        ]

        # Ask user whether to scan metadata for large folders
        ctrl_override = bool(QApplication.keyboardModifiers() & SKIP_METADATA_MODIFIER)

        skip_metadata = resolve_skip_metadata(
            ctrl_override=ctrl_override,
            total_files=len(valid_files),
            folder_path=folder_path,
            parent_window=self,
            default_skip=DEFAULT_SKIP_METADATA,
            threshold=LARGE_FOLDER_WARNING_THRESHOLD
        )

        self.skip_metadata_mode = skip_metadata

        logger.info(
            "Tree-selected folder: %s, skip_metadata=%s (ctrl=%s, default=%s)",
            folder_path, skip_metadata, ctrl_override, DEFAULT_SKIP_METADATA
        )

        self.skip_metadata_mode = skip_metadata

        is_large = len(valid_files) > LARGE_FOLDER_WARNING_THRESHOLD
        # logger.info(
        #     f"Tree-selected folder: {folder_path}, skip_metadata={skip_metadata} "
        #     f"(ctrl={ctrl_override}, large={is_large}, wants_scan={user_wants_scan}, default={DEFAULT_SKIP_METADATA})"
        # )
        logger.warning("-> skip_metadata passed to loader: %s", skip_metadata)
        # Always load the file list with skip_metadata flag
        self.load_files_from_folder(folder_path, skip_metadata=skip_metadata)

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

        self.clear_file_table("No folder selected")
        self.clear_metadata_view() # reset tree view

        # Load the full directory listing
        all_files = glob.glob(os.path.join(folder_path, "*"))
        valid_files = [
            f for f in all_files
            if os.path.splitext(f)[1][1:].lower() in ALLOWED_EXTENSIONS
        ]

        # Ask user whether to scan metadata for large folders
        ctrl_override = bool(QApplication.keyboardModifiers() & SKIP_METADATA_MODIFIER)

        skip_metadata = resolve_skip_metadata(
            ctrl_override=ctrl_override,
            total_files=len(valid_files),
            folder_path=folder_path,
            parent_window=self,
            default_skip=DEFAULT_SKIP_METADATA,
            threshold=LARGE_FOLDER_WARNING_THRESHOLD
        )

        self.skip_metadata_mode = skip_metadata

        is_large = len(valid_files) > LARGE_FOLDER_WARNING_THRESHOLD
        # logger.info(
        #     f"Tree-selected folder: {folder_path}, skip_metadata={skip_metadata} "
        #     f"(ctrl={ctrl_override}, large={is_large}, wants_scan={user_wants_scan}, default={DEFAULT_SKIP_METADATA})"
        # )

        # Always load the file list with skip_metadata flag
        logger.warning("-> skip_metadata passed to loader: %s", skip_metadata)
        self.load_files_from_folder(folder_path, skip_metadata=skip_metadata)

        # Update tree view selection to reflect chosen folder
        if hasattr(self, "dir_model") and hasattr(self, "tree_view"):
            index = self.dir_model.index(folder_path)
            if index.isValid():
                self.tree_view.setCurrentIndex(index)
                self.tree_view.scrollTo(index)

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

    def fade_status_to_ready(self):
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

    def set_status(self, text: str, color: str = "", auto_reset: bool = False, reset_delay: int = 3000):
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
        Updates the preview tables with original and new filenames,
        applying color-coded icons and tooltips to indicate status
        (valid, unchanged, invalid, duplicate).

        Args:
            name_pairs (list[tuple[str, str]]): List of (original, new) filename pairs.
        """
        self.preview_old_name_table.setRowCount(0)
        self.preview_new_name_table.setRowCount(0)
        self.preview_icon_table.setRowCount(0)

        if not name_pairs:
            self.status_label.setText("No files selected.")
            return

        # Adjust column width
        all_names = [name for pair in name_pairs for name in pair]
        max_width = max((self.fontMetrics().horizontalAdvance(name) for name in all_names), default=250)
        adjusted_width = max(250, max_width) + 100
        self.preview_old_name_table.setColumnWidth(0, adjusted_width)
        self.preview_new_name_table.setColumnWidth(0, adjusted_width)

        # Detect duplicates
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

            # Base status logic
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

            # Look up metadata for the file using preview_map
            metadata_str = ""
            missing_metadata = False
            file_item = self.preview_map.get(new_name)

            if file_item and hasattr(file_item, "metadata"):
                meta = file_item.metadata
                if isinstance(meta, dict):
                    mod_date = meta.get("ModificationDate") or meta.get("DateTimeOriginal")
                    if mod_date:
                        metadata_str = f" (mod date: {mod_date})"
                    else:
                        missing_metadata = True
                else:
                    missing_metadata = True
            else:
                missing_metadata = True

            if missing_metadata:
                metadata_str += " [No metadata available]"

            tooltip += metadata_str
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

            # Optional background
            if USE_PREVIEW_BACKGROUND:
                bg = QBrush(QColor(PREVIEW_COLORS[status]))
                old_item.setBackground(bg)
                new_item.setBackground(bg)
                icon_item.setBackground(bg)

            self.preview_old_name_table.setItem(row, 0, old_item)
            self.preview_new_name_table.setItem(row, 0, new_item)
            self.preview_icon_table.setItem(row, 0, icon_item)

        # Compose and set status bar message
        status_msg = (
            f"<img src='{self.icon_paths['valid']}' width='14' height='14' style='vertical-align: middle;'/>"
            f"<span style='color:#ccc;'>Valid: {stats['valid']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{self.icon_paths['unchanged']}' width='14' height='14' style='vertical-align: middle;'/>"
            f"<span style='color:#ccc;'>Unchanged: {stats['unchanged']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{self.icon_paths['invalid']}' width='14' height='14' style='vertical-align: middle;'/>"
            f"<span style='color:#ccc;'>Invalid: {stats['invalid']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{self.icon_paths['duplicate']}' width='14' height='14'/ style='vertical-align: middle;'>"
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
        # Clean up any previous task (if user switched folders quickly)
        self.cleanup_metadata_worker()

        # Protect against concurrent execution
        if self.is_running_metadata_task():
            logger.warning("Worker already running — skipping new metadata scan.")
            return

        # Indicate background work with a wait cursor
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Resolve full paths from current model
        files = [
            os.path.join(self.current_folder_path, f.filename)
            for f in self.model.files
        ]

        logger.debug("load_metadata_in_thread: Will process paths:")
        for f in self.model.files:
            logger.debug(f" - {f.filename} | full: {f.full_path}")

        logger.debug("Will scan metadata for paths:")
        for p in file_paths:
            logger.debug(f"  - {p}")

        # Create the thread and move worker into it
        self.metadata_thread = QThread(self)
        self.metadata_worker = MetadataWorker(self.metadata_reader, metadata_cache=self.metadata_cache)
        self.metadata_worker.moveToThread(self.metadata_thread)

        # Connect signals

        # Metadata progress updates
        self.metadata_worker.progress.connect(self.on_metadata_progress)

        # When done, update UI and clean up
        self.metadata_worker.finished.connect(self.finish_metadata_loading)

        # Ensure proper teardown when work completes
        self.metadata_worker.finished.connect(self.metadata_thread.quit)
        self.metadata_worker.finished.connect(self.metadata_worker.deleteLater)
        self.metadata_thread.finished.connect(self.metadata_thread.deleteLater)

        # Start processing as soon as thread begins
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
        injecting metadata into file items, and restoring UI state. Also
        tears down the background thread and worker.

        Args:
            metadata_dict (dict): Dictionary containing filename -> metadata.
        """
        if self.metadata_worker is None:
            logger.warning("Received 'finished' signal after cleanup — ignoring.")
            return

        logger.info("Metadata loading complete. Loaded metadata for %d files.", len(metadata_dict))

        # Save metadata results and update the UI status label
        self.metadata_cache = metadata_dict
        count = len(metadata_dict)
        self.set_status(f"Metadata loaded for {count} file{'s' if count != 1 else ''}.", color="green", auto_reset=True)

        # Inject metadata into FileItems
        for file_item in self.files:
            filename = file_item.filename
            metadata = metadata_dict.get(filename)
            if isinstance(metadata, dict):
                file_item.metadata = metadata.copy()
            else:
                logger.warning("No valid metadata for %s — defaulting to empty dict.", filename)
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

            self.metadata_thread = None  # ✅ ΣΗΜΑΝΤΙΚΟ: καθαρίζουμε οριστικά

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

        return (
            self.metadata_thread is not None and
            self.metadata_thread.isRunning()
        )

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
        logger.debug(">>> populate_metadata_table called")

        # Ensure cursor is restored in case it was left in busy mode
        QApplication.restoreOverrideCursor()

        if not metadata:
            logger.info("No metadata available for selected file.")
            self.show_empty_metadata_tree("No information available")
            return

        model = build_metadata_tree_model(metadata)
        self.metadata_tree_view.setModel(model)
        self.metadata_tree_view.expandToDepth(1)
        self.metadata_tree_view.resizeColumnToContents(0)
        self.metadata_tree_view.header().setStretchLastSection(True)
        self.metadata_tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.metadata_tree_view.header().setSectionResizeMode(1, QHeaderView.Stretch)


        logger.debug("Metadata table populated with %d entries.", len(metadata))

        """
        Slot connected to the itemSelectionChanged signal of the table view.

        Populates the metadata tree view with the metadata of the clicked row.
        Supports nested dictionaries and lists via expandable tree structure.

        Args:
            index (QModelIndex): The index of the clicked row.
        """

    def on_table_row_clicked(self, index: QModelIndex) -> None:

        # Block clicks when there are no files
        if not self.model.files:
            logger.info("No files in model — click ignored.")
            return

        row = index.row()

        # Defensive: avoid out-of-range index
        if row < 0 or row >= len(self.model.files):
            logger.warning("Invalid row clicked (out of range). Ignored.")
            return

        # Ignore clicks on checkbox column
        if index.column() == 0:
            return

        filename = self.model.files[row].filename

        file_item = next((f for f in self.model.files if f.filename == filename), None)

        if file_item:
            path = file_item.full_path if file_item and file_item.full_path else os.path.join(self.current_folder_path, filename)
            metadata = self.metadata_cache.get(path)
            if metadata is None:
                metadata = {}
        else:
            logger.warning("FileItem not found for row click: %s", filename)
            path = os.path.join(self.current_folder_path, filename)
            metadata = self.metadata_cache.get(path, {})


        logger.debug("Row clicked: %s", filename)
        if metadata:
            logger.debug("Metadata found for %s", filename)
            tree_model = build_metadata_tree_model(metadata)
            self.metadata_tree_view.setModel(tree_model)
            self.metadata_tree_view.expandAll()

            # sync toggle button state
            self.toggle_expand_button.setChecked(True)
            self.toggle_expand_button.setText("Collapse All")
        else:
            logger.warning("No metadata found for %s", filename)
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

    def clear_file_table(self, message: str = "No folder selected"):
        """
        Clears the file table and shows a placeholder message.
        """
        self.model.set_files([])  # reset model with empty list
        self.show_file_table_placeholder(message)
        self.header.setEnabled(False) # disable header
        self.header.update_state([])

        self.update_files_label()

    def set_files(self, files: list[FileItem]) -> None:
        """
        Replaces the file list and refreshes the table.
        """
        self.beginResetModel()
        self.files = files
        self.endResetModel()

    def show_file_table_placeholder(self, message: str = "No files loaded"):
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

    def show_empty_metadata_tree(self, message: str = "No file selected"):
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

    def clear_metadata_view(self):
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
