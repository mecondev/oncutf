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

import datetime
import glob
import os
import platform
import traceback
from typing import Optional

# Import all PyQt5 classes from centralized module
from core.qt_imports import *

# Import all config constants from centralized module
from core.config_imports import *

# Core application modules
from core.application_context import ApplicationContext
from core.drag_manager import DragManager
from core.file_loader import FileLoader
from core.file_operations_manager import FileOperationsManager
from core.modifier_handler import decode_modifiers_to_flags
from core.preview_manager import PreviewManager
from core.status_manager import StatusManager
# Data models and business logic modules
from models.file_item import FileItem
from models.file_table_model import FileTableModel
from modules.name_transform_module import NameTransformModule
# Utility functions and helpers
from utils.cursor_helper import wait_cursor, emergency_cursor_cleanup, force_restore_cursor
from utils.filename_validator import FilenameValidator
from utils.icon_cache import load_preview_status_icons, prepare_status_icons
from utils.icons import create_colored_icon
from utils.icons_loader import get_menu_icon, icons_loader, load_metadata_icons
from utils.logger_helper import get_logger
from utils.metadata_cache import MetadataCache
from utils.metadata_loader import MetadataLoader
from utils.preview_engine import apply_rename_modules
from utils.renamer import Renamer
# UI widgets and custom components
from widgets.custom_file_system_model import CustomFileSystemModel
from widgets.custom_msgdialog import CustomMessageDialog
from widgets.file_table_view import FileTableView
from widgets.file_tree_view import FileTreeView
from widgets.interactive_header import InteractiveHeader
from widgets.metadata_tree_view import MetadataTreeView
from widgets.metadata_waiting_dialog import MetadataWaitingDialog
from widgets.metadata_worker import MetadataWorker
from widgets.preview_tables_view import PreviewTablesView
from widgets.rename_modules_area import RenameModulesArea

logger = get_logger(__name__)

import contextlib


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        """Initializes the main window and sets up the layout."""
        super().__init__()

        # --- Core Application Context ---
        self.context = ApplicationContext.create_instance(parent=self)

        # --- Initialize DragManager ---
        self.drag_manager = DragManager.get_instance()

        # --- Initialize FileLoader ---
        self.file_loader = FileLoader(parent_window=self)

        # --- Initialize PreviewManager ---
        self.preview_manager = PreviewManager(parent_window=self)

        # --- Initialize FileOperationsManager ---
        self.file_operations_manager = FileOperationsManager(parent_window=self)

        # --- Initialize StatusManager ---
        self.status_manager = None  # Will be initialized after status label is created

        # --- Initialize MetadataManager ---
        self.metadata_manager = None  # Will be initialized after metadata components

        # --- Attributes initialization ---
        self.metadata_thread = None
        self.metadata_worker = None
        self.metadata_cache = MetadataCache()
        self.metadata_icon_map = load_metadata_icons()
        self.preview_icons = load_preview_status_icons()
        self.force_extended_metadata = False
        self.skip_metadata_mode = DEFAULT_SKIP_METADATA # Keeps state across folder reloads
        self.metadata_loader = MetadataLoader()
        self.file_model = FileTableModel(parent_window=self)
        self.metadata_loader.model = self.file_model

        # --- Initialize MetadataManager after dependencies are ready ---
        from core.metadata_manager import MetadataManager
        from core.selection_manager import SelectionManager
        self.metadata_manager = MetadataManager(parent_window=self)
        self.selection_manager = SelectionManager(parent_window=self)

        # Initialize theme icon loader with dark theme by default
        icons_loader.set_theme("dark")

        self.loading_dialog = None
        self.modifier_state = Qt.NoModifier # type: ignore[attr-defined]

        self.create_colored_icon = create_colored_icon
        self.icon_paths = prepare_status_icons()

        self.filename_validator = FilenameValidator()
        self.last_action = None  # Could be: 'folder_import', 'browse', 'rename', etc.
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

        # --- Shortcuts ---
        self.setup_shortcuts()

        # --- Preview update debouncing timer ---
        self.preview_update_timer = QTimer(self)
        self.preview_update_timer.setSingleShot(True)
        self.preview_update_timer.setInterval(100)  # milliseconds (reduced from 250ms for better performance)
        self.preview_update_timer.timeout.connect(self.generate_preview_names)

        # --- Emergency drag cleanup timer --- (disabled for now)
        # self.emergency_cleanup_timer = QTimer(self)
        # self.emergency_cleanup_timer.timeout.connect(self._emergency_drag_cleanup)
        # self.emergency_cleanup_timer.setInterval(5000)  # Check every 5 seconds, not 1
        # self.emergency_cleanup_timer.start()

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

        # Set minimum sizes for all panels to 80px
        self.horizontal_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setup_left_panel(self) -> None:
        """Setup left panel (folder tree)."""
        self.left_frame = QFrame()
        left_layout = QVBoxLayout(self.left_frame)
        left_layout.addWidget(QLabel("Folders"))

        self.folder_tree = FileTreeView()
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
        self.select_folder_button = QPushButton("  Import")
        self.select_folder_button.setIcon(get_menu_icon("folder"))
        self.select_folder_button.setFixedWidth(100)
        self.browse_folder_button = QPushButton("  Browse")
        self.browse_folder_button.setIcon(get_menu_icon("folder-plus"))
        self.browse_folder_button.setFixedWidth(100)

        # Add buttons with fixed positioning - no stretching
        btn_layout.addWidget(self.select_folder_button)
        btn_layout.addSpacing(4)  # 4px spacing between buttons
        btn_layout.addWidget(self.browse_folder_button)
        btn_layout.addStretch()  # Push buttons to left, allow empty space on right
        left_layout.addLayout(btn_layout)

        self.dir_model = CustomFileSystemModel()
        self.dir_model.setRootPath('')
        self.dir_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)

        # Adding filter for allowed file extensions
        name_filters = []
        for ext in ALLOWED_EXTENSIONS:
            name_filters.append(f"*.{ext}")
        self.dir_model.setNameFilters(name_filters)
        self.dir_model.setNameFilterDisables(False)  # This hides files that don't match instead of disabling them

        self.folder_tree.setModel(self.dir_model)

        for i in range(1, 4):
            self.folder_tree.hideColumn(i)

        # Header configuration is now handled by FileTreeView.configure_header_for_scrolling()
        # when setModel() is called

        root = "" if platform.system() == "Windows" else "/"
        self.folder_tree.setRootIndex(self.dir_model.index(root))

        # Set minimum size for left panel and add to splitter
        self.left_frame.setMinimumWidth(230)
        self.horizontal_splitter.addWidget(self.left_frame)

    def setup_center_panel(self) -> None:
        """Setup center panel (file table view)."""
        self.center_frame = QFrame()
        center_layout = QVBoxLayout(self.center_frame)

        self.files_label = QLabel("Files")
        center_layout.addWidget(self.files_label)

        self.file_table_view = FileTableView(parent=self)
        self.file_table_view.parent_window = self
        self.file_table_view.verticalHeader().setVisible(False)
        self.file_table_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_model = FileTableModel(parent_window=self)
        self.file_table_view.setModel(self.file_model)

        # Header setup
        self.header = InteractiveHeader(Qt.Horizontal, self.file_table_view, parent_window=self)
        self.file_table_view.setHorizontalHeader(self.header)
        # Align all headers to the left (if supported)
        if hasattr(self.header, 'setDefaultAlignment'):
            self.header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.header.setSortIndicatorShown(False)
        self.header.setSectionsClickable(False)
        self.header.setHighlightSections(False)

        self.file_table_view.setHorizontalHeader(self.header)
        self.file_table_view.setAlternatingRowColors(True)
        self.file_table_view.setShowGrid(False)
        self.file_table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table_view.setSortingEnabled(False)  # Manual sorting logic
        self.file_table_view.setWordWrap(False)

        # Initialize header and set default row height
        self.file_table_view.horizontalHeader()
        self.file_table_view.verticalHeader().setDefaultSectionSize(22)  # Compact row height

        # Column configuration is now handled by FileTableView._configure_columns()
        # when setModel() is called

        # Show placeholder after setup is complete
        self.file_table_view.set_placeholder_visible(True)
        center_layout.addWidget(self.file_table_view)
        # Set minimum size for center panel and add to splitter
        self.center_frame.setMinimumWidth(230)
        self.horizontal_splitter.addWidget(self.center_frame)

    def setup_right_panel(self) -> None:
        """Setup right panel (metadata tree view)."""
        self.right_frame = QFrame()
        right_layout = QVBoxLayout(self.right_frame)
        right_layout.addWidget(QLabel("Information"))

        # Expand/Collapse buttons
        self.toggle_expand_button = QPushButton("Expand All")
        self.toggle_expand_button.setIcon(get_menu_icon("chevrons-down"))
        self.toggle_expand_button.setCheckable(True)
        self.toggle_expand_button.setFixedWidth(120)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.toggle_expand_button)
        button_layout.addStretch()

        right_layout.addLayout(button_layout)

        # Metadata Tree View
        self.metadata_tree_view = MetadataTreeView()
        self.metadata_tree_view.files_dropped.connect(self.load_metadata_from_dropped_files)
        right_layout.addWidget(self.metadata_tree_view)

        # Dummy initial model
        placeholder_model = QStandardItemModel()
        placeholder_model.setHorizontalHeaderLabels(["Key", "Value"])
        placeholder_item = QStandardItem("No file selected")
        placeholder_item.setTextAlignment(Qt.AlignLeft)
        placeholder_value = QStandardItem("-")
        placeholder_model.appendRow([placeholder_item, placeholder_value])

        # Set minimum size for right panel and finalize
        self.right_frame.setMinimumWidth(230)
        self.horizontal_splitter.addWidget(self.right_frame)
        self.horizontal_splitter.setSizes(LEFT_CENTER_RIGHT_SPLIT_RATIO)

        # Initialize MetadataTreeView with parent connections
        self.metadata_tree_view.initialize_with_parent()

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

                        # === Right: Preview tables view ===
        self.preview_tables_view = PreviewTablesView(parent=self)

        # Connect status updates from preview view
        self.preview_tables_view.status_updated.connect(self._update_status_from_preview)

        # Setup bottom controls
        controls_layout = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setTextFormat(Qt.RichText)

        # Initialize StatusManager now that status_label exists
        self.status_manager = StatusManager(status_label=self.status_label)

        # Status label fade effect setup (kept for compatibility but not used by StatusManager)
        self.status_opacity_effect = QGraphicsOpacityEffect()
        self.status_label.setGraphicsEffect(self.status_opacity_effect)
        self.status_fade_anim = QPropertyAnimation(self.status_opacity_effect, b"opacity")
        self.status_fade_anim.setDuration(800)  # ms
        self.status_fade_anim.setStartValue(1.0)
        self.status_fade_anim.setEndValue(0.3)
        controls_layout.addWidget(self.status_label, stretch=1)

        self.rename_button = QPushButton("  Rename")
        self.rename_button.setIcon(get_menu_icon("edit"))
        self.rename_button.setEnabled(False)
        self.rename_button.setFixedWidth(100)
        controls_layout.addWidget(self.rename_button)

        # Create preview frame container
        self.preview_frame = QFrame()
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.addWidget(self.preview_tables_view)
        preview_layout.addLayout(controls_layout)

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

    def _update_status_from_preview(self, status_html: str) -> None:
        """Update the status label from preview widget status updates."""
        self.status_manager.update_status_from_preview(status_html)



    def setup_signals(self) -> None:
        """
        Connects UI elements to their corresponding event handlers.
        """
        self.installEventFilter(self)

        self.header.sectionClicked.connect(self.sort_by_column)

        self.select_folder_button.clicked.connect(self.handle_folder_import)
        self.browse_folder_button.clicked.connect(self.handle_browse)

        # Connect folder_tree for drag & drop operations
        self.folder_tree.item_dropped.connect(self.load_single_item_from_drop)
        self.folder_tree.folder_selected.connect(self.handle_folder_import)

        # Connect splitter resize to adjust tree view column width
        self.horizontal_splitter.splitterMoved.connect(self.on_horizontal_splitter_moved)
        # Connect vertical splitter resize for debugging
        self.vertical_splitter.splitterMoved.connect(self.on_vertical_splitter_moved)
        # Connect callbacks for both tree view and file table view
        self.horizontal_splitter.splitterMoved.connect(self.folder_tree.on_horizontal_splitter_moved)
        self.vertical_splitter.splitterMoved.connect(self.folder_tree.on_vertical_splitter_moved)
        self.horizontal_splitter.splitterMoved.connect(self.file_table_view.on_horizontal_splitter_moved)
        self.vertical_splitter.splitterMoved.connect(self.file_table_view.on_vertical_splitter_moved)

        # Connect splitter movements to preview tables view
        self.vertical_splitter.splitterMoved.connect(self.preview_tables_view.handle_splitter_moved)

        self.file_table_view.clicked.connect(self.on_table_row_clicked)
        self.file_table_view.selection_changed.connect(self.update_preview_from_selection)
        self.file_table_view.files_dropped.connect(self.load_files_from_dropped_items)
        self.file_model.sort_changed.connect(self.request_preview_update)
        self.file_table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table_view.customContextMenuRequested.connect(self.handle_table_context_menu)

        # Toggle button connection is now handled by MetadataTreeView
        # self.toggle_expand_button.toggled.connect(self.toggle_metadata_expand)



        self.rename_button.clicked.connect(self.rename_files)

        # --- Connect the updated signal of RenameModulesArea to generate_preview_names ---
        self.rename_modules_area.updated.connect(self.request_preview_update)

        # Enable SelectionStore mode in FileTableView after signals are connected
        QTimer.singleShot(100, self._enable_selection_store_mode)

    def setup_shortcuts(self) -> None:
        """
        Initializes all keyboard shortcuts for file table actions.
        Stores them in self.shortcuts to avoid garbage collection.
        """
        self.shortcuts = []

        # File table shortcuts
        file_table_shortcuts = [
            ("Ctrl+A", self.select_all_rows),
            ("Ctrl+Shift+A", self.clear_all_selection),
            ("Ctrl+I", self.invert_selection),
            ("Ctrl+O", self.handle_browse),
            ("Ctrl+R", self.force_reload),
            ("Ctrl+M", self.shortcut_load_metadata),
            ("Ctrl+E", self.shortcut_load_extended_metadata),
        ]
        for key, handler in file_table_shortcuts:
            shortcut = QShortcut(QKeySequence(key), self.file_table_view)
            shortcut.activated.connect(handler)
            self.shortcuts.append(shortcut)

        # Global shortcuts (attached to main window)
        global_shortcuts = [
            ("Escape", self.force_drag_cleanup),  # Global escape key
            ("Ctrl+Escape", self.clear_file_table_shortcut),  # Clear file table
        ]
        for key, handler in global_shortcuts:
            shortcut = QShortcut(QKeySequence(key), self)  # Attached to main window
            shortcut.activated.connect(handler)
            self.shortcuts.append(shortcut)

    def clear_file_table_shortcut(self) -> None:
        """
        Clear file table triggered by Ctrl+Escape shortcut.
        """
        logger.info("[MainWindow] CLEAR TABLE: Ctrl+Escape key pressed")

        if not self.file_model.files:
            logger.info("[MainWindow] CLEAR TABLE: No files to clear")
            self.set_status("No files to clear", color="gray", auto_reset=True, reset_delay=1000)
            return

        # Clear the file table
        self.clear_file_table("Press Escape to clear, or drag folders here")
        self.current_folder_path = None  # Reset current folder
        self.set_status("File table cleared", color="blue", auto_reset=True, reset_delay=1000)
        logger.info("[MainWindow] CLEAR TABLE: File table cleared successfully")

    def force_drag_cleanup(self) -> None:
        """
        Force cleanup of any active drag operations.
        Triggered by Escape key globally.
        """
        logger.info("[MainWindow] FORCE CLEANUP: Escape key pressed")

        drag_manager = DragManager.get_instance()

        # Check if there's any stuck cursor or drag state
        has_override_cursor = QApplication.overrideCursor() is not None
        has_active_drag = drag_manager.is_drag_active()

        if not has_override_cursor and not has_active_drag:
            logger.info("[MainWindow] FORCE CLEANUP: No cursors or drags to clean")
            return

        # Clean any stuck cursors first
        cursor_count = 0
        while QApplication.overrideCursor() and cursor_count < 5:
            QApplication.restoreOverrideCursor()
            cursor_count += 1

        # Clean drag manager state if needed
        if has_active_drag:
            drag_manager.force_cleanup()

        # Clean widget states
        self._cleanup_widget_drag_states()

        # Report what was cleaned
        if cursor_count > 0 or has_active_drag:
            self.set_status("Drag cancelled", color="blue", auto_reset=True, reset_delay=1000)
            logger.info(f"[MainWindow] FORCE CLEANUP: Cleaned {cursor_count} cursors, drag_active={has_active_drag}")
        else:
            logger.info("[MainWindow] FORCE CLEANUP: Nothing to clean")

    def _cleanup_widget_drag_states(self) -> None:
        """Clean up internal drag states in all widgets (lightweight version)."""
        # Only clean essential drag state, let widgets handle their own cleanup
        if hasattr(self, 'folder_tree'):
            if hasattr(self.folder_tree, '_dragging'):
                self.folder_tree._dragging = False

        if hasattr(self, 'file_table_view'):
            if hasattr(self.file_table_view, '_drag_start_pos'):
                self.file_table_view._drag_start_pos = None

        logger.debug("[MainWindow] Widget drag states cleaned")

    def _emergency_drag_cleanup(self) -> None:
        """
        Emergency cleanup that runs every 5 seconds to catch stuck cursors.
        Only acts if cursor has been stuck for multiple checks.
        """
        app = QApplication.instance()
        if not app:
            return

        # Check if cursor looks stuck in drag mode
        current_cursor = app.overrideCursor()
        if current_cursor:
            cursor_shape = current_cursor.shape()
            # Common drag cursor shapes that might be stuck
            drag_cursors = [Qt.DragMoveCursor, Qt.DragCopyCursor, Qt.DragLinkCursor, Qt.ClosedHandCursor]

            if cursor_shape in drag_cursors:
                drag_manager = DragManager.get_instance()
                if not drag_manager.is_drag_active():
                    # Initialize stuck count if not exists
                    if not hasattr(self, '_stuck_cursor_count'):
                        self._stuck_cursor_count = 0

                    self._stuck_cursor_count += 1

                    # Only cleanup after 2 consecutive detections (10 seconds total)
                    if self._stuck_cursor_count >= 2:
                        logger.warning(f"[Emergency] Stuck drag cursor detected for {self._stuck_cursor_count * 5}s, forcing cleanup")
                        drag_manager.force_cleanup()
                        self.set_status("Stuck cursor fixed", color="green", auto_reset=True, reset_delay=1000)
                        self._stuck_cursor_count = 0
                    else:
                        logger.debug(f"[Emergency] Suspicious cursor detected ({self._stuck_cursor_count}/2)")
                else:
                    # Reset count if drag is actually active
                    self._stuck_cursor_count = 0
            else:
                # Reset count if cursor is not drag-related
                self._stuck_cursor_count = 0
        else:
            # Reset count if no override cursor
            self._stuck_cursor_count = 0

    def eventFilter(self, obj, event):
        """
        Captures global keyboard modifier state (Ctrl, Shift).
        """
        if event.type() in (QEvent.KeyPress, QEvent.KeyRelease):
            self.modifier_state = QApplication.keyboardModifiers()
            logger.debug(f"[Modifiers] eventFilter saw: {event.type()} with modifiers={int(event.modifiers())}", extra={"dev_only": True})

        return super().eventFilter(obj, event)

    def request_preview_update(self) -> None:
        """
        Schedules a delayed update of the name previews.
        Instead of calling generate_preview_names directly every time something changes,
        the timer is restarted so that the actual update occurs only when
        changes stop for the specified duration (250ms).
        """
        if self.preview_update_timer.isActive():
            self.preview_update_timer.stop()
        self.preview_update_timer.start()

    def force_reload(self) -> None:
        """
        Triggered by Ctrl+R.
        If Ctrl is held, metadata scan is skipped (like Select/Browse).
        Otherwise, full reload with scan.
        """
        # Update current state of modifier keys
        self.modifier_state = QApplication.keyboardModifiers()

        if not self.current_folder_path:
            self.set_status("No folder loaded.", color="gray", auto_reset=True)
            return

        if not CustomMessageDialog.question(self, "Reload Folder", "Reload current folder?", yes_text="Reload", no_text="Cancel"):
            return

        # Use determine_metadata_mode method instead of deprecated resolve_skip_metadata
        skip_metadata, use_extended = self.determine_metadata_mode()
        self.force_extended_metadata = use_extended
        self.skip_metadata_mode = skip_metadata

        logger.info(
            f"[ForceReload] Reloading {self.current_folder_path}, skip_metadata={skip_metadata} "
            f"(use_extended={use_extended})"
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
        """Delegates to SelectionManager."""
        self.selection_manager.select_all_rows()

    def clear_all_selection(self) -> None:
        """Delegates to SelectionManager."""
        self.selection_manager.clear_all_selection()

    def invert_selection(self) -> None:
        """Delegates to SelectionManager."""
        self.selection_manager.invert_selection()

    def sort_by_column(self, column: int, order: Qt.SortOrder = None, force_order: Qt.SortOrder = None) -> None:
        """
        Sorts the file table based on clicked header column or context menu.
        Toggle logic unless a force_order is explicitly provided.
        """
        if column == 0:
            return  # Do not sort the status/info column

        header = self.file_table_view.horizontalHeader()
        current_column = header.sortIndicatorSection()
        current_order = header.sortIndicatorOrder()

        if force_order is not None:
            new_order = force_order
        elif column == current_column:
            new_order = Qt.DescendingOrder if current_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            new_order = Qt.AscendingOrder

        self.file_model.sort(column, new_order)
        header.setSortIndicator(column, new_order)

    def restore_fileitem_metadata_from_cache(self) -> None:
        """
        After a folder reload (e.g. after rename), reassigns cached metadata
        to the corresponding FileItem objects in self.file_model.files.

        This allows icons and previews to remain consistent without rescanning.
        """
        restored = 0
        for file in self.file_model.files:
            cached = self.metadata_cache.get(file.full_path)
            if isinstance(cached, dict) and cached:
                file.metadata = cached
                restored += 1
        logger.info(f"[MetadataRestore] Restored metadata from cache for {restored} files.")

    def rename_files(self) -> None:
        """
        Execute the batch rename process for checked files using active rename modules.

        This method handles the complete rename workflow including validation,
        execution, folder reload, and state restoration.
        """
        selected_files = [f for f in self.file_model.files if f.checked]
        rename_data = self.rename_modules_area.get_all_data()
        modules_data = rename_data.get("modules", [])
        post_transform = rename_data.get("post_transform", {})

        # Store checked paths for restoration
        checked_paths = {f.full_path for f in self.file_model.files if f.checked}

        # Use FileOperationsManager to perform rename
        renamed_count = self.file_operations_manager.rename_files(
            selected_files=selected_files,
            modules_data=modules_data,
            post_transform=post_transform,
            metadata_cache=self.metadata_cache,
            filename_validator=self.filename_validator,
            current_folder_path=self.current_folder_path
        )

        if renamed_count == 0:
            return

        # Post-rename workflow
        self.last_action = "rename"
        self.load_files_from_folder(self.current_folder_path, skip_metadata=True)

        # Restore checked state
        restored_count = 0
        for path in checked_paths:
            file = self.find_fileitem_by_path(path)
            if file:
                file.checked = True
                restored_count += 1

        # Restore metadata from cache
        self.restore_fileitem_metadata_from_cache()

        # Regenerate preview with new filenames
        if self.last_action == "rename":
            logger.debug("[PostRename] Regenerating preview with new filenames and restored checked state")
            self.request_preview_update()

        # Force update info icons in column 0
        for row in range(self.file_model.rowCount()):
            file_item = self.file_model.files[row]
            if self.metadata_cache.has(file_item.full_path):
                index = self.file_model.index(row, 0)
                rect = self.file_table_view.visualRect(index)
                self.file_table_view.viewport().update(rect)

        self.file_table_view.viewport().update()
        logger.debug(f"[Rename] Restored {restored_count} checked out of {len(self.file_model.files)} files")

    def should_skip_folder_reload(self, folder_path: str, force: bool = False) -> bool:
        """Delegates to FileOperationsManager for folder reload check."""
        return self.file_operations_manager.should_skip_folder_reload(
            folder_path, self.current_folder_path, force
        )

    def get_file_items_from_folder(self, folder_path: str) -> list[FileItem]:
        """Get FileItem objects from folder_path. Returns empty list if folder doesn't exist."""
        return self.file_loader.get_file_items_from_folder(folder_path)

    def prepare_file_table(self, file_items: list[FileItem]) -> None:
        """
        Prepare the file table view with the given file items.

        Delegates the core table preparation to the FileTableView and handles
        application-specific logic like updating labels and preview maps.

        Args:
            file_items: List of FileItem objects to display in the table
        """
        # Delegate table preparation to the view itself
        self.file_table_view.prepare_table(file_items)

        # Handle application-specific setup
        self.files = file_items
        self.file_model.folder_path = self.current_folder_path
        self.preview_map = {f.filename: f for f in file_items}

        # Enable header and update UI elements
        if hasattr(self, "header") and self.header is not None:
            self.header.setEnabled(True)

        self.update_files_label()
        self.update_preview_tables_from_pairs([])
        self.rename_button.setEnabled(False)

        # If we're coming from a rename operation and have active modules, regenerate preview
        if self.last_action == "rename":
            logger.debug("[PrepareTable] Post-rename detected, preview will be updated after checked state restore")

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
        self.metadata_tree_view.refresh_metadata_from_selection() # reset metadata tree

        file_items = self.get_file_items_from_folder(folder_path)

        if not file_items:
            self.metadata_tree_view.clear_view()
            self.header.setEnabled(False)
            self.set_status("No supported files found.", color="orange", auto_reset=True)
            return

        self.prepare_file_table(file_items)
        self.sort_by_column(1, Qt.AscendingOrder)
        self.metadata_tree_view.clear_view()

        if skip_metadata:
            self.set_status("Metadata scan skipped.", color="gray", auto_reset=True)
            return

        self.set_status(f"Loading metadata for {len(file_items)} files...", color="#3377ff")
        QTimer.singleShot(100, lambda: self.start_metadata_scan([f.full_path for f in file_items if f.full_path]))

    def start_metadata_scan(self, file_paths: list[str]) -> None:
        """Delegates to MetadataManager for metadata scan initiation."""
        self.metadata_manager.start_metadata_scan(file_paths)

    def load_metadata_in_thread(self, file_paths: list[str]) -> None:
        """Delegates to MetadataManager for thread-based metadata loading."""
        self.metadata_manager.load_metadata_in_thread(file_paths)

    def start_metadata_scan_for_items(self, items: list[FileItem]) -> None:
        """Delegates to MetadataManager for FileItem-based metadata scanning."""
        self.metadata_manager.start_metadata_scan_for_items(items)

    def shortcut_load_metadata(self) -> None:
        """Delegates to MetadataManager for shortcut-based metadata loading."""
        self.metadata_manager.shortcut_load_metadata()

    def shortcut_load_extended_metadata(self) -> None:
        """Delegates to MetadataManager for extended metadata shortcut loading."""
        self.metadata_manager.shortcut_load_extended_metadata()





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
        if not self.file_model.files:
            return

        total = len(self.file_model.files)
        all_selected = all(file.checked for file in self.file_model.files)
        selection_model = self.file_table_view.selectionModel()

        with wait_cursor():
            if all_selected:
                # Unselect all
                selection_model.clearSelection()
                for file in self.file_model.files:
                    file.checked = False
            else:
                # Select all efficiently
                self.file_table_view.select_rows_range(0, total - 1)
                for file in self.file_model.files:
                    file.checked = True
                self.file_table_view.anchor_row = 0

            self.file_table_view.viewport().update()
            self.update_files_label()
            self.request_preview_update()
            self.metadata_tree_view.refresh_metadata_from_selection()

    def generate_preview_names(self) -> None:
        """
        Generate new preview names for all selected files using current rename modules.
        Updates the preview map and UI elements accordingly.
        """
        selected_files = [f for f in self.file_model.files if f.checked]
        logger.debug("[Preview] Triggered! Selected rows: %s", [f.filename for f in selected_files], extra={"dev_only": True})

        if not selected_files:
            logger.debug("[Preview] No selected files — skipping preview generation.", extra={"dev_only": True})
            self.update_preview_tables_from_pairs([])
            self.rename_button.setEnabled(False)
            return

        # Get rename data and modules
        rename_data = self.rename_modules_area.get_all_data()
        all_modules = self.rename_modules_area.get_all_module_instances()

        # Use PreviewManager to generate previews
        name_pairs, has_changes = self.preview_manager.generate_preview_names(
            selected_files, rename_data, self.metadata_cache, all_modules
        )

        # Update preview map from manager
        self.preview_map = self.preview_manager.get_preview_map()

        # Handle UI updates based on results
        if not name_pairs:
            # No modules at all → clear preview completely
            self.update_preview_tables_from_pairs([])
            self.rename_button.setEnabled(False)
            self.set_status("No rename modules defined.", color="#888888", auto_reset=True)
            return

        if not has_changes:
            # Modules exist but inactive → show identity mapping
            self.rename_button.setEnabled(False)
            self.rename_button.setToolTip("No changes to apply")
            self.update_preview_tables_from_pairs(name_pairs)
            self.set_status("Rename modules present but inactive.", color="#888888", auto_reset=True)
            return

        # Update preview tables with changes
        self.update_preview_tables_from_pairs(name_pairs)

        # Enable rename button and set tooltip
        valid_pairs = [p for p in name_pairs if p[0] != p[1]]
        self.rename_button.setEnabled(bool(valid_pairs))
        tooltip_msg = f"{len(valid_pairs)} files will be renamed." if valid_pairs else "No changes to apply"
        self.rename_button.setToolTip(tooltip_msg)

    def compute_max_filename_width(self, file_list: list[FileItem]) -> int:
        """Delegates to PreviewManager for filename width calculation."""
        return self.preview_manager.compute_max_filename_width(file_list)

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
        """Delegates to FileOperationsManager for large folder confirmation."""
        return self.file_operations_manager.confirm_large_folder(file_list, folder_path)

    def check_large_files(self, files: list[FileItem]) -> list[FileItem]:
        """Delegates to FileOperationsManager for large file checking."""
        return self.file_operations_manager.check_large_files(files)

    def confirm_large_files(self, files: list[FileItem]) -> bool:
        """Delegates to FileOperationsManager for large file confirmation."""
        return self.file_operations_manager.confirm_large_files(files)

    def update_files_label(self) -> None:
        """
        Updates the UI label that displays the count of selected files.

        If no files are loaded, the label shows a default "Files".
        Otherwise, it shows how many files are currently selected
        out of the total number loaded.
        """
        total = len(self.file_model.files)
        selected = sum(1 for f in self.file_model.files if f.checked) if total else 0

        self.status_manager.update_files_label(self.files_label, total, selected)

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
        Sets the status label text and optional color. Delegates to StatusManager.
        """
        self.status_manager.set_status(text, color, auto_reset, reset_delay)

    def get_identity_name_pairs(self) -> list[tuple[str, str]]:
        """Delegates to FileOperationsManager for identity name pairs."""
        return self.file_operations_manager.get_identity_name_pairs(self.file_model.files)

    def update_preview_tables_from_pairs(self, name_pairs: list[tuple[str, str]]) -> None:
        """
        Updates all three preview tables using the PreviewTablesView.

        Args:
            name_pairs (list[tuple[str, str]]): List of (old_name, new_name) pairs
                generated during preview generation.
        """
        # Delegate to the preview tables view
        self.preview_tables_view.update_from_pairs(
            name_pairs,
            self.preview_icons,
            self.icon_paths,
            self.filename_validator
        )

    def on_metadata_progress(self, current: int, total: int) -> None:
        """Delegates to MetadataManager for progress updates."""
        self.metadata_manager.on_metadata_progress(current, total)

    def handle_metadata_finished(self) -> None:
        """Delegates to MetadataManager for handling completion."""
        self.metadata_manager.handle_metadata_finished()

    def cleanup_metadata_worker(self) -> None:
        """Delegates to MetadataManager for worker cleanup."""
        self.metadata_manager.cleanup_metadata_worker()

    def get_selected_files(self) -> list:
        """
        Returns a list of FileItem objects currently selected (blue-highlighted) in the table view.
        """
        selected_indexes = self.file_table_view.selectionModel().selectedRows()
        return [self.file_model.files[i.row()] for i in selected_indexes if 0 <= i.row() < len(self.file_model.files)]

    def find_fileitem_by_path(self, path: str) -> Optional[FileItem]:
        """Delegates to FileOperationsManager for finding FileItem by path."""
        return self.file_operations_manager.find_fileitem_by_path(self.file_model.files, path)

    def cancel_metadata_loading(self) -> None:
        """Delegates to MetadataManager for cancellation."""
        self.metadata_manager.cancel_metadata_loading()

    def on_metadata_error(self, message: str) -> None:
        """Delegates to MetadataManager for error handling."""
        self.metadata_manager.on_metadata_error(message)

    def is_running_metadata_task(self) -> bool:
        """Delegates to MetadataManager to check if metadata task is running."""
        return self.metadata_manager.is_running_metadata_task()

    def on_table_row_clicked(self, index: QModelIndex) -> None:
        """
        Triggered when a user clicks on a file row in the table.
        Displays the metadata for the selected file in the right panel.
        """
        if not self.file_model.files:
            logger.info("No files in model — click ignored.")
            return

        row = index.row()
        if row < 0 or row >= len(self.file_model.files):
            logger.warning("Invalid row clicked (out of range). Ignored.")
            return

        # Ignore checkbox column clicks
        if index.column() == 0:
            return

        self.metadata_tree_view.refresh_metadata_from_selection()

    def prompt_file_conflict(self, target_path: str) -> str:
        """Delegates to FileOperationsManager for file conflict resolution."""
        return self.file_operations_manager.prompt_file_conflict(target_path)



    def clear_file_table(self, message: str = "No folder selected") -> None:
        """
        Clears the file table and shows a placeholder message.
        """
        # Clear scroll position memory when changing folders
        self.metadata_tree_view.clear_for_folder_change()
        self.file_model.set_files([])  # reset model with empty list
        self.file_table_view.set_placeholder_visible(True)  # Show placeholder when empty
        self.header.setEnabled(False) # disable header
        self.status_manager.clear_file_table_status(self.files_label, message)
        self.update_files_label()

        # Update scrollbar visibility after clearing table
        self.file_table_view._update_scrollbar_visibility()



    def get_common_metadata_fields(self) -> list[str]:
        """
        Returns the intersection of metadata keys from all checked files.
        """
        selected_files = [f for f in self.file_model.files if f.checked]
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
                - skip_metadata: True if NO modifiers are pressed (default) or if Ctrl is NOT pressed
                - use_extended: True if Ctrl+Shift is pressed
        """
        modifiers = self.modifier_state
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)

        skip_metadata = not ctrl
        use_extended = ctrl and shift

        # [DEBUG] Modifiers: Ctrl=%s, Shift=%s", skip_metadata, use_extended
        return skip_metadata, use_extended

    def determine_metadata_mode(self) -> tuple[bool, bool]:
        """Delegates to MetadataManager for metadata mode determination."""
        return self.metadata_manager.determine_metadata_mode(self.modifier_state)


    def should_use_extended_metadata(self) -> bool:
        """Delegates to MetadataManager for extended metadata decision."""
        return self.metadata_manager.should_use_extended_metadata(self.modifier_state)

    def update_preview_from_selection(self, selected_rows: list[int]) -> None:
        """Delegates to SelectionManager."""
        self.selection_manager.update_preview_from_selection(selected_rows)

    def handle_table_context_menu(self, position) -> None:
        """
        Handles the right-click context menu for the file table.

        Supports:
        - Metadata load (normal / extended) for selected or all files
        - Invert selection, select all, reload folder
        - Uses custom selection state from file_table_view.selected_rows
        """
        if not self.file_model.files:
            return

        from utils.icons_loader import get_menu_icon

        self.file_table_view.indexAt(position)
        total_files = len(self.file_model.files)

        # Get selected rows from custom selection model
        selected_rows = self.file_table_view.selected_rows
        selected_files = [self.file_model.files[r] for r in selected_rows if 0 <= r < total_files]

        menu = QMenu(self)

        # --- Metadata actions ---
        action_load_sel = menu.addAction(get_menu_icon("file"), "Load metadata for selected file(s)")
        action_load_all = menu.addAction(get_menu_icon("folder"), "Load metadata for all files")
        action_load_ext_sel = menu.addAction(get_menu_icon("file-plus"), "Load extended metadata for selected file(s)")
        action_load_ext_all = menu.addAction(get_menu_icon("folder-plus"), "Load extended metadata for all files")

        menu.addSeparator()

        # --- Selection actions ---
        action_invert = menu.addAction(get_menu_icon("refresh-cw"), "Invert selection (Ctrl+I)")
        action_select_all = menu.addAction(get_menu_icon("check-square"), "Select all (Ctrl+A)")
        action_deselect_all = menu.addAction(get_menu_icon("square"), "Deselect all")

        menu.addSeparator()

        # --- Other actions ---
        action_reload = menu.addAction(get_menu_icon("refresh-cw"), "Reload folder (Ctrl+R)")

        menu.addSeparator()

        # --- Disabled future options ---
        action_save_sel = menu.addAction(get_menu_icon("save"), "Save metadata for selected file(s)")
        action_save_all = menu.addAction(get_menu_icon("save"), "Save metadata for all files")
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
            self.load_metadata_for_items(selected_files, use_extended=False, source="context_menu")

        elif action == action_load_ext_sel:
            self.load_metadata_for_items(selected_files, use_extended=True, source="context_menu")

        elif action == action_load_all:
            self.load_metadata_for_items(self.file_model.files, use_extended=False, source="context_menu_all")

        elif action == action_load_ext_all:
            self.load_metadata_for_items(self.file_model.files, use_extended=True, source="context_menu_all")

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
        if 0 <= row < len(self.file_model.files):
            file = self.file_model.files[row]
            logger.info(f"[DoubleClick] Requested metadata reload for: {file.filename}")

            # Check if Shift was pressed for extended metadata
            use_extended = bool(int(modifiers) & int(Qt.ShiftModifier))
            logger.debug(f"[Modifiers] Shift held → use_extended={use_extended}")

            selected_indexes = self.file_table_view.selectionModel().selectedRows()
            selected_files = [self.file_model.files[i.row()] for i in selected_indexes if 0 <= i.row() < len(self.file_model.files)]

            # If user pressed Shift (for extended) and has multiple files selected,
            # limit to only the file that was double-clicked to avoid mistakes
            if use_extended and len(selected_files) > 1:
                    logger.debug(f"[ShiftFix] Qt range selection detected on Shift+DoubleClick — keeping only clicked file: {file.filename}", extra={"dev_only": True})
                    selected_files = [file]

            # Use the unified method
            self.load_metadata_for_items(selected_files, use_extended=use_extended, source="double_click")

    def closeEvent(self, event) -> None:
        """
        Called when the main window is about to close.

        Ensures any background metadata threads are cleaned up
        properly before the application exits.
        """
        logger.info("Main window closing. Cleaning up metadata worker.")
        self.cleanup_metadata_worker()

        if hasattr(self.metadata_loader, "close"):
            self.metadata_loader.close()

        # Clean up application context
        if hasattr(self, 'context'):
            self.context.cleanup()

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
        self.metadata_tree_view.clear_view()
        self.current_folder_path = folder_path

        return self.file_loader.prepare_folder_load(folder_path, clear=clear)

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
        """
        Loads files from a list of file or folder paths.

        Args:
            file_paths: List of absolute file or folder paths
            clear: Whether to clear existing items before loading (True = replace, False = merge)
        """
        if not file_paths:
            if clear:
                self.file_table_view.set_placeholder_visible(True)
            return

        # Use FileLoader to get file items
        new_file_items = self.file_loader.load_files_from_paths(file_paths, clear=clear)

        if clear:
            # Replace mode: clear everything and load new files
            logger.debug(f"[Load] Replace mode: loading {len(new_file_items)} new files")
            self.file_table_view.prepare_table(new_file_items)
            final_items = new_file_items
        else:
            # Merge mode: add to existing files, avoiding duplicates
            existing_items = self.file_model.files if self.file_model else []
            existing_paths = {item.full_path for item in existing_items}

            # Filter out duplicates
            unique_new_items = [item for item in new_file_items if item.full_path not in existing_paths]

            logger.debug(f"[Load] Merge mode: {len(existing_items)} existing + {len(unique_new_items)} new = {len(existing_items) + len(unique_new_items)} total")

            if unique_new_items:
                # Combine existing + new
                final_items = existing_items + unique_new_items

                # Use prepare_table with combined list
                self.file_table_view.prepare_table(final_items)
            else:
                logger.info(f"[Load] No new files to add (all {len(new_file_items)} files already exist)")
                final_items = existing_items

        # Handle application-specific setup
        self.files = final_items
        self.preview_map = {f.filename: f for f in final_items}

        # Configure sorting and header after prepare_table
        self.file_table_view.setSortingEnabled(True)
        if hasattr(self, "header"):
            self.header.setSectionsClickable(True)
            self.header.setSortIndicatorShown(True)
            self.header.setEnabled(True)

        self.file_table_view.sortByColumn(1, Qt.AscendingOrder)
        self.file_table_view.set_placeholder_visible(len(final_items) == 0)
        self.file_table_view.scrollToTop()
        self.update_preview_tables_from_pairs([])
        self.update_files_label()

    def load_metadata_from_dropped_files(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Called when user drops files onto metadata tree.
        Maps filenames to FileItem objects and triggers forced metadata loading.
        """
        file_items = []
        for path in paths:
            filename = os.path.basename(path)
            file = next((f for f in self.file_model.files if f.filename == filename), None)
            if file:
                file_items.append(file)

        if not file_items:
            logger.info("[Drop] No matching files found in table.")
            return

        # New logic for FileTable → MetadataTree drag:
        # - No modifiers: fast metadata (normal metadata loading)
        # - Shift: extended metadata
        shift = bool(modifiers & Qt.ShiftModifier)
        use_extended = shift

        logger.debug(f"[Modifiers] File drop on metadata tree: shift={shift} → extended={use_extended}")

        # Always load metadata (no skip option for metadata tree drops)
        self.load_metadata_for_items(file_items, use_extended=use_extended, source="dropped_files")

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

            # Use passed modifiers (from drag start) instead of current state
            self.modifier_state = modifiers if modifiers != Qt.NoModifier else QApplication.keyboardModifiers()

            # Use safe casting via helper method
            skip_metadata, use_extended = self.determine_metadata_mode()
            logger.debug(f"[Drop] Using stored modifiers: {modifiers}, skip_metadata={skip_metadata}, use_extended={use_extended}")

            self.force_extended_metadata = use_extended
            self.skip_metadata_mode = skip_metadata

            logger.debug(f"[Drop] skip_metadata={skip_metadata}, use_extended={use_extended}")

            # Centralized loading logic
            self.prepare_folder_load(folder_path)

            # Get loaded items (from self.file_model or retrieved from paths if needed)
            items = self.file_model.files

            if not self.skip_metadata_mode:
                self.load_metadata_for_items(
                    items,
                    use_extended=self.force_extended_metadata,
                    source="folder_drop"
                )

            # Update folder tree selection (UI logic)
            if hasattr(self.dir_model, "index"):
                index = self.dir_model.index(folder_path)
                self.folder_tree.setCurrentIndex(index)

            # Trigger label update and ensure repaint
            self.file_table_view.viewport().update()
            self.update_files_label()
        else:
            # Load directly dropped files with modifier support
            self.load_files_from_paths(paths, clear=True)

            # Apply modifier logic for individual files
            ctrl = bool(modifiers & Qt.ControlModifier)
            shift = bool(modifiers & Qt.ShiftModifier)
            skip_metadata = not ctrl
            use_extended = ctrl and shift

            logger.debug(f"[Drop] Individual files: ctrl={ctrl}, shift={shift} → skip={skip_metadata}, extended={use_extended}")

            # Define selection function to call after metadata loading (or immediately if skipping)
            def select_dropped_files():
                logger.warning(f"[Drop] *** CALLING select_dropped_files with {len(paths)} paths ***")
                self.file_table_view.select_dropped_files(paths)

            # Load metadata if not skipping
            if not skip_metadata:
                items = self.file_model.files
                self.load_metadata_for_items(items, use_extended=use_extended, source="individual_file_drop")
                # Select files AFTER metadata loading with a delay
                logger.debug(f"[Drop] Scheduling selection after metadata with 100ms delay", extra={"dev_only": True})
                QTimer.singleShot(100, select_dropped_files)
            else:
                logger.info(f"[Drop] Skipping metadata for {len(paths)} individual files (no Ctrl modifier)")
                # Select files immediately if not loading metadata
                logger.warning(f"[Drop] *** SCHEDULING selection immediately with 50ms delay ***")
                QTimer.singleShot(50, select_dropped_files)

        # After loading files + metadata
        self.show_metadata_status()

    def handle_browse(self) -> None:
        """
        Browse and select a folder, then import its files.

        Modifier logic (checked AFTER folder selection):
        - Normal: Replace + shallow
        - Shift: Merge + shallow
        - Ctrl: Replace + recursive
        - Ctrl+Shift: Merge + recursive

        Triggered when the user clicks the 'Browse' button.
        Updates the folder tree selection to reflect the newly selected folder.
        """
        self.last_action = "browse"

        # Get current folder path
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", "/")
        if not folder_path:
            logger.info("Folder selection canceled by user.")
            return

        if self.should_skip_folder_reload(folder_path):
            return  # skip if user pressed Cancel

        # Capture modifiers AFTER dialog closes (when user is ready to confirm the action)
        modifiers = QApplication.keyboardModifiers()
        self.modifier_state = modifiers

        # Decode modifier combination using centralized logic
        merge_mode, recursive, action_type = decode_modifiers_to_flags(modifiers)

        logger.debug(f"[Browse] Captured modifiers after dialog: {modifiers} → {action_type}")
        logger.info(f"[Browse] Folder: {folder_path} ({action_type})")

        # Use folder drop logic for consistency
        with wait_cursor():
            self._handle_folder_drop(folder_path, merge_mode, recursive)

        # Update tree selection
        if hasattr(self, "dir_model") and hasattr(self, "folder_tree"):
            index = self.dir_model.index(folder_path)
            if index.isValid():
                self.folder_tree.setCurrentIndex(index)
                self.folder_tree.scrollTo(index)

        # After loading files
        self.update_files_label()
        self.show_metadata_status()

    def handle_folder_import(self) -> None:
        """
        Import files from the folder currently selected in the folder tree.

        Modifier logic (checked when clicking Import button):
        - Normal: Replace + shallow
        - Shift: Merge + shallow
        - Ctrl: Replace + recursive
        - Ctrl+Shift: Merge + recursive

        Triggered when the user clicks the 'Import' button or presses Enter on folder tree.
        """
        # Get current folder index first
        index = self.folder_tree.currentIndex()
        if not index.isValid():
            logger.warning("No folder selected in folder tree.")
            return

        folder_path = self.dir_model.filePath(index)

        if self.should_skip_folder_reload(folder_path):
            return

        # Capture modifiers at the moment of action (when user clicks Import)
        modifiers = QApplication.keyboardModifiers()
        self.modifier_state = modifiers
        self.last_action = "folder_import"

        # Decode modifier combination using centralized logic
        merge_mode, recursive, action_type = decode_modifiers_to_flags(modifiers)

        logger.debug(f"[Import] Captured modifiers at click: {modifiers} → {action_type}")
        logger.info(f"[Import] Folder: {folder_path} ({action_type})")

        # Use folder drop logic for consistency
        with wait_cursor():
            self._handle_folder_drop(folder_path, merge_mode, recursive)

        # After loading files
        self.update_files_label()
        self.show_metadata_status()

    def load_single_item_from_drop(self, path: str, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Called when user drops a single file or folder from the tree onto file table view.
        Handles the new 4-modifier logic:
        - Normal: Replace + shallow
        - Ctrl: Replace + recursive
        - Shift: Merge + shallow
        - Ctrl+Shift: Merge + recursive
        """
        # Use centralized file loader
        self.file_loader.handle_drop_operation(path, modifiers)

    def _has_deep_content(self, folder_path: str) -> bool:
        """Check if folder has any supported files in deeper levels (beyond root)"""
        return self.file_loader.has_deep_content(folder_path)

    def _handle_folder_drop(self, folder_path: str, merge_mode: bool, recursive: bool) -> None:
        """Handle folder drop with merge/replace and recursive options"""
        self.file_loader.handle_folder_drop(folder_path, merge_mode, recursive)

    def _handle_file_drop(self, file_path: str, merge_mode: bool) -> None:
        """Handle single file drop with merge/replace options"""
        self.file_loader.handle_file_drop(file_path, merge_mode)

    def load_metadata_for_items(
        self,
        items: list[FileItem],
        use_extended: bool = False,
        source: str = "unknown"
    ) -> None:
        """Delegates to MetadataManager for unified metadata loading."""
        self.metadata_manager.load_metadata_for_items(items, use_extended, source)

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement - logic delegated to individual views"""
        sizes = self.horizontal_splitter.sizes()
        logger.debug(f"[HorizontalSplitter] Moved - Position: {pos}, Index: {index}, Sizes: {sizes} (Left: {sizes[0]}px, Center: {sizes[1]}px, Right: {sizes[2]}px)", extra={"dev_only": True})

        # Individual views handle their own adjustments via their callback methods

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement for debugging optimal sizes"""
        sizes = self.vertical_splitter.sizes()
        logger.debug(f"[VerticalSplitter] Moved - Position: {pos}, Index: {index}, Sizes: {sizes} (Top: {sizes[0]}px, Bottom: {sizes[1]}px)", extra={"dev_only": True})

    def show_metadata_status(self) -> None:
        """
        Shows a status bar message indicating the number of loaded files
        and the type of metadata scan performed (skipped, basic, extended).
        """
        num_files = len(self.file_model.files)
        self.status_manager.show_metadata_status(num_files, self.skip_metadata_mode, self.force_extended_metadata)

    def _enable_selection_store_mode(self):
        """Enable SelectionStore mode in FileTableView once ApplicationContext is ready."""
        try:
            self.file_table_view.enable_selection_store_mode()

            # Connect SelectionStore signals to MainWindow handlers
            from core.application_context import get_app_context
            context = get_app_context()
            if context and context.selection_store:
                # Connect selection changed signal to existing preview update
                context.selection_store.selection_changed.connect(self.update_preview_from_selection)
                logger.debug("[MainWindow] Connected SelectionStore signals", extra={"dev_only": True})

            logger.info("[MainWindow] SelectionStore mode enabled in FileTableView")
        except Exception as e:
            logger.warning(f"[MainWindow] Failed to enable SelectionStore mode: {e}")


