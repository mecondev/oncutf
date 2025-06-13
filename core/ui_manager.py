"""
ui_manager.py

Author: Michael Economou
Date: 2025-06-13

Manages UI setup and layout configuration for the main window.
Handles all UI component initialization, layout setup, and signal connections.
"""

import platform
from typing import TYPE_CHECKING

from core.config_imports import *
from core.qt_imports import *
from models.file_table_model import FileTableModel
from utils.icons_loader import get_menu_icon
from utils.logger_helper import get_logger
from widgets.custom_file_system_model import CustomFileSystemModel
from widgets.file_table_view import FileTableView
from widgets.file_tree_view import FileTreeView
from widgets.interactive_header import InteractiveHeader
from widgets.metadata_tree_view import MetadataTreeView
from widgets.preview_tables_view import PreviewTablesView
from widgets.rename_modules_area import RenameModulesArea

if TYPE_CHECKING:
    from main_window import MainWindow

logger = get_logger(__name__)


class UIManager:
    """Manages UI setup and layout configuration for the main window."""

    def __init__(self, parent_window: 'MainWindow'):
        """Initialize UIManager with parent window reference."""
        self.parent_window = parent_window
        logger.debug("[UIManager] Initialized")

    def setup_all_ui(self) -> None:
        """Setup all UI components in the correct order."""
        self.setup_main_window()
        self.setup_main_layout()
        self.setup_splitters()
        self.setup_left_panel()
        self.setup_center_panel()
        self.setup_right_panel()
        self.setup_bottom_layout()
        self.setup_footer()
        self.setup_signals()
        self.setup_shortcuts()
        logger.debug("[UIManager] All UI components setup completed")

    def setup_main_window(self) -> None:
        """Configure main window properties."""
        self.parent_window.setWindowTitle("oncutf - Batch File Renamer and More")
        self.parent_window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.parent_window.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.parent_window.center_window()

    def setup_main_layout(self) -> None:
        """Setup central widget and main layout."""
        self.parent_window.central_widget = QWidget()
        self.parent_window.setCentralWidget(self.parent_window.central_widget)
        self.parent_window.main_layout = QVBoxLayout(self.parent_window.central_widget)

    def setup_splitters(self) -> None:
        """Setup vertical and horizontal splitters."""
        self.parent_window.vertical_splitter = QSplitter(Qt.Vertical)  # type: ignore
        self.parent_window.main_layout.addWidget(self.parent_window.vertical_splitter)

        self.parent_window.horizontal_splitter = QSplitter(Qt.Horizontal)  # type: ignore
        self.parent_window.vertical_splitter.addWidget(self.parent_window.horizontal_splitter)
        self.parent_window.vertical_splitter.setSizes(TOP_BOTTOM_SPLIT_RATIO)

        # Set minimum sizes for all panels to 80px
        self.parent_window.horizontal_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setup_left_panel(self) -> None:
        """Setup left panel (folder tree)."""
        self.parent_window.left_frame = QFrame()
        left_layout = QVBoxLayout(self.parent_window.left_frame)
        left_layout.addWidget(QLabel("Folders"))

        self.parent_window.folder_tree = FileTreeView()
        self.parent_window.folder_tree.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.parent_window.folder_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.parent_window.folder_tree.setAlternatingRowColors(True)  # Enable alternating row colors
        left_layout.addWidget(self.parent_window.folder_tree)

        # Expand/collapse mode (single or double click)
        if TREE_EXPAND_MODE == "single":
            self.parent_window.folder_tree.setExpandsOnDoubleClick(False)  # Single click expand
        else:
            self.parent_window.folder_tree.setExpandsOnDoubleClick(True)   # Double click expand

        btn_layout = QHBoxLayout()
        self.parent_window.select_folder_button = QPushButton("  Import")
        self.parent_window.select_folder_button.setIcon(get_menu_icon("folder"))
        self.parent_window.select_folder_button.setFixedWidth(100)
        self.parent_window.browse_folder_button = QPushButton("  Browse")
        self.parent_window.browse_folder_button.setIcon(get_menu_icon("folder-plus"))
        self.parent_window.browse_folder_button.setFixedWidth(100)

        # Add buttons with fixed positioning - no stretching
        btn_layout.addWidget(self.parent_window.select_folder_button)
        btn_layout.addSpacing(4)  # 4px spacing between buttons
        btn_layout.addWidget(self.parent_window.browse_folder_button)
        btn_layout.addStretch()  # Push buttons to left, allow empty space on right
        left_layout.addLayout(btn_layout)

        self.parent_window.dir_model = CustomFileSystemModel()
        self.parent_window.dir_model.setRootPath('')
        self.parent_window.dir_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)

        # Adding filter for allowed file extensions
        name_filters = []
        for ext in ALLOWED_EXTENSIONS:
            name_filters.append(f"*.{ext}")
        self.parent_window.dir_model.setNameFilters(name_filters)
        self.parent_window.dir_model.setNameFilterDisables(False)  # This hides files that don't match instead of disabling them

        self.parent_window.folder_tree.setModel(self.parent_window.dir_model)

        for i in range(1, 4):
            self.parent_window.folder_tree.hideColumn(i)

        # Header configuration is now handled by FileTreeView.configure_header_for_scrolling()
        # when setModel() is called

        root = "" if platform.system() == "Windows" else "/"
        self.parent_window.folder_tree.setRootIndex(self.parent_window.dir_model.index(root))

        # Set minimum size for left panel and add to splitter
        self.parent_window.left_frame.setMinimumWidth(230)
        self.parent_window.horizontal_splitter.addWidget(self.parent_window.left_frame)

    def setup_center_panel(self) -> None:
        """Setup center panel (file table view)."""
        self.parent_window.center_frame = QFrame()
        center_layout = QVBoxLayout(self.parent_window.center_frame)

        self.parent_window.files_label = QLabel("Files")
        center_layout.addWidget(self.parent_window.files_label)

        self.parent_window.file_table_view = FileTableView(parent=self.parent_window)
        self.parent_window.file_table_view.parent_window = self.parent_window
        self.parent_window.file_table_view.verticalHeader().setVisible(False)
        self.parent_window.file_table_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.parent_window.file_table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.parent_window.file_model = FileTableModel(parent_window=self.parent_window)
        self.parent_window.file_table_view.setModel(self.parent_window.file_model)

        # Header setup
        self.parent_window.header = InteractiveHeader(Qt.Horizontal, self.parent_window.file_table_view, parent_window=self.parent_window)
        self.parent_window.file_table_view.setHorizontalHeader(self.parent_window.header)
        # Align all headers to the left (if supported)
        if hasattr(self.parent_window.header, 'setDefaultAlignment'):
            self.parent_window.header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.parent_window.header.setSortIndicatorShown(False)
        self.parent_window.header.setSectionsClickable(False)
        self.parent_window.header.setHighlightSections(False)

        self.parent_window.file_table_view.setHorizontalHeader(self.parent_window.header)
        self.parent_window.file_table_view.setAlternatingRowColors(True)
        self.parent_window.file_table_view.setShowGrid(False)
        self.parent_window.file_table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.parent_window.file_table_view.setSortingEnabled(False)  # Manual sorting logic
        self.parent_window.file_table_view.setWordWrap(False)

        # Initialize header and set default row height
        self.parent_window.file_table_view.horizontalHeader()
        self.parent_window.file_table_view.verticalHeader().setDefaultSectionSize(22)  # Compact row height

        # Column configuration is now handled by FileTableView._configure_columns()
        # when setModel() is called

        # Show placeholder after setup is complete
        self.parent_window.file_table_view.set_placeholder_visible(True)
        center_layout.addWidget(self.parent_window.file_table_view)
        # Set minimum size for center panel and add to splitter
        self.parent_window.center_frame.setMinimumWidth(230)
        self.parent_window.horizontal_splitter.addWidget(self.parent_window.center_frame)

    def setup_right_panel(self) -> None:
        """Setup right panel (metadata tree view)."""
        self.parent_window.right_frame = QFrame()
        right_layout = QVBoxLayout(self.parent_window.right_frame)
        right_layout.addWidget(QLabel("Information"))

        # Expand/Collapse buttons
        self.parent_window.toggle_expand_button = QPushButton("Expand All")
        self.parent_window.toggle_expand_button.setIcon(get_menu_icon("chevrons-down"))
        self.parent_window.toggle_expand_button.setCheckable(True)
        self.parent_window.toggle_expand_button.setFixedWidth(120)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.parent_window.toggle_expand_button)
        button_layout.addStretch()

        right_layout.addLayout(button_layout)

        # Metadata Tree View
        self.parent_window.metadata_tree_view = MetadataTreeView()
        self.parent_window.metadata_tree_view.files_dropped.connect(self.parent_window.load_metadata_from_dropped_files)
        right_layout.addWidget(self.parent_window.metadata_tree_view)

        # Dummy initial model
        placeholder_model = QStandardItemModel()
        placeholder_model.setHorizontalHeaderLabels(["Key", "Value"])
        placeholder_item = QStandardItem("No file selected")
        placeholder_item.setTextAlignment(Qt.AlignLeft)
        placeholder_value = QStandardItem("-")
        placeholder_model.appendRow([placeholder_item, placeholder_value])

        # Set minimum size for right panel and finalize
        self.parent_window.right_frame.setMinimumWidth(230)
        self.parent_window.horizontal_splitter.addWidget(self.parent_window.right_frame)
        self.parent_window.horizontal_splitter.setSizes(LEFT_CENTER_RIGHT_SPLIT_RATIO)

        # Initialize MetadataTreeView with parent connections
        self.parent_window.metadata_tree_view.initialize_with_parent()

    def setup_bottom_layout(self) -> None:
        """Setup bottom layout for rename modules and preview."""
        # --- Bottom Frame: Rename Modules + Preview ---
        self.parent_window.bottom_frame = QFrame()
        self.parent_window.bottom_layout = QVBoxLayout(self.parent_window.bottom_frame)
        self.parent_window.bottom_layout.setSpacing(0)
        self.parent_window.bottom_layout.setContentsMargins(0, 0, 0, 0)

        content_layout = QHBoxLayout()

        # === Left: Rename modules ===
        self.parent_window.rename_modules_area = RenameModulesArea(parent=self.parent_window, parent_window=self.parent_window)

        # === Right: Preview tables view ===
        self.parent_window.preview_tables_view = PreviewTablesView(parent=self.parent_window)

        # Connect status updates from preview view
        self.parent_window.preview_tables_view.status_updated.connect(self.parent_window._update_status_from_preview)

        # Setup bottom controls
        controls_layout = QHBoxLayout()
        self.parent_window.status_label = QLabel("")
        self.parent_window.status_label.setTextFormat(Qt.RichText)

        # Initialize StatusManager now that status_label exists
        from core.status_manager import StatusManager
        self.parent_window.status_manager = StatusManager(status_label=self.parent_window.status_label)

        self.parent_window.rename_button = QPushButton("Rename Files")
        self.parent_window.rename_button.setEnabled(False)
        self.parent_window.rename_button.setFixedWidth(120)

        controls_layout.addWidget(self.parent_window.status_label)
        controls_layout.addStretch()
        controls_layout.addWidget(self.parent_window.rename_button)

        # Create preview frame
        self.parent_window.preview_frame = QFrame()
        preview_layout = QVBoxLayout(self.parent_window.preview_frame)
        preview_layout.addWidget(self.parent_window.preview_tables_view)
        preview_layout.addLayout(controls_layout)

        content_layout.addWidget(self.parent_window.rename_modules_area, stretch=1)
        content_layout.addWidget(self.parent_window.preview_frame, stretch=3)
        self.parent_window.bottom_layout.addLayout(content_layout)

    def setup_footer(self) -> None:
        """Setup footer with version label."""
        footer_separator = QFrame()
        footer_separator.setFrameShape(QFrame.HLine)
        footer_separator.setFrameShadow(QFrame.Sunken)

        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(10, 4, 10, 4)

        self.parent_window.version_label = QLabel()
        self.parent_window.version_label.setText(f"{APP_NAME} v{APP_VERSION}")
        self.parent_window.version_label.setObjectName("versionLabel")
        self.parent_window.version_label.setAlignment(Qt.AlignLeft)
        footer_layout.addWidget(self.parent_window.version_label)
        footer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.parent_window.vertical_splitter.addWidget(self.parent_window.horizontal_splitter)
        self.parent_window.vertical_splitter.addWidget(self.parent_window.bottom_frame)
        self.parent_window.vertical_splitter.setSizes([500, 300])

        self.parent_window.main_layout.addWidget(footer_separator)
        self.parent_window.main_layout.addWidget(footer_widget)

    def setup_signals(self) -> None:
        """Connect UI elements to their corresponding event handlers."""
        self.parent_window.installEventFilter(self.parent_window)

        self.parent_window.header.sectionClicked.connect(self.parent_window.sort_by_column)

        self.parent_window.select_folder_button.clicked.connect(self.parent_window.handle_folder_import)
        self.parent_window.browse_folder_button.clicked.connect(self.parent_window.handle_browse)

        # Connect folder_tree for drag & drop operations
        self.parent_window.folder_tree.item_dropped.connect(self.parent_window.load_single_item_from_drop)
        self.parent_window.folder_tree.folder_selected.connect(self.parent_window.handle_folder_import)

        # Connect splitter resize to adjust tree view column width
        self.parent_window.horizontal_splitter.splitterMoved.connect(self.parent_window.on_horizontal_splitter_moved)
        # Connect vertical splitter resize for debugging
        self.parent_window.vertical_splitter.splitterMoved.connect(self.parent_window.on_vertical_splitter_moved)
        # Connect callbacks for both tree view and file table view
        self.parent_window.horizontal_splitter.splitterMoved.connect(self.parent_window.folder_tree.on_horizontal_splitter_moved)
        self.parent_window.vertical_splitter.splitterMoved.connect(self.parent_window.folder_tree.on_vertical_splitter_moved)
        self.parent_window.horizontal_splitter.splitterMoved.connect(self.parent_window.file_table_view.on_horizontal_splitter_moved)
        self.parent_window.vertical_splitter.splitterMoved.connect(self.parent_window.file_table_view.on_vertical_splitter_moved)

        # Connect splitter movements to preview tables view
        self.parent_window.vertical_splitter.splitterMoved.connect(self.parent_window.preview_tables_view.handle_splitter_moved)

        self.parent_window.file_table_view.clicked.connect(self.parent_window.on_table_row_clicked)
        self.parent_window.file_table_view.selection_changed.connect(self.parent_window.update_preview_from_selection)
        self.parent_window.file_table_view.files_dropped.connect(self.parent_window.load_files_from_dropped_items)
        self.parent_window.file_model.sort_changed.connect(self.parent_window.request_preview_update)
        self.parent_window.file_table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.parent_window.file_table_view.customContextMenuRequested.connect(self.parent_window.handle_table_context_menu)

        # Toggle button connection is now handled by MetadataTreeView
        # self.parent_window.toggle_expand_button.toggled.connect(self.parent_window.toggle_metadata_expand)

        self.parent_window.rename_button.clicked.connect(self.parent_window.rename_files)

        # --- Connect the updated signal of RenameModulesArea to generate_preview_names ---
        self.parent_window.rename_modules_area.updated.connect(self.parent_window.request_preview_update)

        # Enable SelectionStore mode in FileTableView after signals are connected
        QTimer.singleShot(100, self.parent_window._enable_selection_store_mode)

    def setup_shortcuts(self) -> None:
        """Initialize all keyboard shortcuts for file table actions."""
        self.parent_window.shortcuts = []

        # File table shortcuts
        file_table_shortcuts = [
            ("Ctrl+A", self.parent_window.select_all_rows),
            ("Ctrl+Shift+A", self.parent_window.clear_all_selection),
            ("Ctrl+I", self.parent_window.invert_selection),
            ("Ctrl+O", self.parent_window.handle_browse),
            ("Ctrl+R", self.parent_window.force_reload),
            ("Ctrl+M", self.parent_window.shortcut_load_metadata),
            ("Ctrl+E", self.parent_window.shortcut_load_extended_metadata),
        ]
        for key, handler in file_table_shortcuts:
            shortcut = QShortcut(QKeySequence(key), self.parent_window.file_table_view)
            shortcut.activated.connect(handler)
            self.parent_window.shortcuts.append(shortcut)

        # Global shortcuts (attached to main window)
        global_shortcuts = [
            ("Escape", self.parent_window.force_drag_cleanup),  # Global escape key
            ("Ctrl+Escape", self.parent_window.clear_file_table_shortcut),  # Clear file table
        ]
        for key, handler in global_shortcuts:
            shortcut = QShortcut(QKeySequence(key), self.parent_window)  # Attached to main window
            shortcut.activated.connect(handler)
            self.parent_window.shortcuts.append(shortcut)
