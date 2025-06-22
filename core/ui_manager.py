"""
ui_manager.py

Author: Michael Economou
Date: 2025-06-13

Manages UI setup and layout configuration for the main window.
Handles widget initialization, signal connections, and layout management.
"""

import platform
from typing import TYPE_CHECKING

from core.config_imports import *
from core.qt_imports import *
from models.file_table_model import FileTableModel
from utils.icons_loader import get_app_icon, get_menu_icon
from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_selection_update, schedule_ui_update
from widgets.custom_file_system_model import CustomFileSystemModel
from widgets.file_table_view import FileTableView
from widgets.file_tree_view import FileTreeView
from widgets.interactive_header import InteractiveHeader
from widgets.metadata_tree_view import MetadataTreeView
from widgets.preview_tables_view import PreviewTablesView
from widgets.rename_modules_area import RenameModulesArea

if TYPE_CHECKING:
    from main_window import MainWindow

logger = get_cached_logger(__name__)


class UIManager:
    """Manages UI setup and layout configuration for the main window."""

    def __init__(self, parent_window: 'MainWindow'):
        """Initialize UIManager with parent window reference."""
        self.parent_window = parent_window
        logger.debug("[UIManager] Initialized", extra={"dev_only": True})

    def setup_all_ui(self) -> None:
        """Setup all UI components in the correct order."""
        self.setup_main_window()
        self.setup_main_layout()
        self.setup_splitters()
        self.setup_left_panel()
        self.setup_center_panel()
        logger.debug("[UIManager] setup_center_panel() DONE - calling setup_right_panel()", extra={"dev_only": True})
        self.setup_right_panel()
        logger.debug("[UIManager] setup_right_panel() DONE", extra={"dev_only": True})
        self.setup_bottom_layout()
        self.setup_footer()
        self.setup_signals()
        self.setup_shortcuts()
        logger.debug("[UIManager] All UI components setup completed", extra={"dev_only": True})

    def setup_main_window(self) -> None:
        """Configure main window properties."""
        self.parent_window.setWindowTitle("oncutf - Batch File Renamer and More")

        # Set window icon using the centralized icon loader
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.parent_window.setWindowIcon(app_icon)
            logger.debug("[UIManager] Window icon set using icon loader", extra={"dev_only": True})
        else:
            logger.warning("[UIManager] Failed to load application icon")

        # Calculate optimal window size based on screen resolution
        optimal_size = self._calculate_optimal_window_size()
        self.parent_window.resize(optimal_size.width(), optimal_size.height())

        self.parent_window.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        # self.parent_window.center_window()
        self.parent_window.dialog_manager.center_window(self.parent_window)

    def _calculate_optimal_window_size(self):
        """Calculate optimal window size based on screen resolution and aspect ratio."""
        # Get primary screen geometry
        screen = QApplication.desktop().screenGeometry()  # type: ignore
        screen_width = screen.width()
        screen_height = screen.height()
        screen_aspect = screen_width / screen_height

        logger.debug(f"[UIManager] Screen resolution: {screen_width}x{screen_height}, aspect: {screen_aspect:.2f}", extra={"dev_only": True})

        # Define target percentages of screen size
        width_percentage = 0.75  # Use 75% of screen width
        height_percentage = 0.80  # Use 80% of screen height

        # Calculate initial size based on screen percentage
        target_width = int(screen_width * width_percentage)
        target_height = int(screen_height * height_percentage)

        # Adjust for different aspect ratios
        if screen_aspect >= 2.3:  # Ultrawide (21:9 or wider)
            # For ultrawide screens, use less width percentage to avoid too wide windows
            target_width = int(screen_width * 0.65)
            target_height = int(screen_height * 0.85)
        elif screen_aspect >= 1.7:  # Widescreen (16:9, 16:10)
            # Standard widescreen - use calculated values
            pass
        elif screen_aspect <= 1.4:  # 4:3 or close
            # For 4:3 screens, use more width and height percentage (they're usually smaller)
            target_width = int(screen_width * 0.92)  # Use 92% of width for 4:3
            target_height = int(screen_height * 0.85)

        # Ensure minimum constraints
        target_width = max(target_width, WINDOW_MIN_WIDTH)
        target_height = max(target_height, WINDOW_MIN_HEIGHT)

        # Ensure maximum reasonable size (not bigger than config fallback)
        max_width = max(WINDOW_WIDTH, 1600)  # At least config default or 1600px
        max_height = max(WINDOW_HEIGHT, 1200)  # At least config default or 1200px
        target_width = min(target_width, max_width)
        target_height = min(target_height, max_height)

        optimal_size = QSize(target_width, target_height)

        logger.debug(f"[UIManager] Calculated optimal window size: {target_width}x{target_height}", extra={"dev_only": True})
        return optimal_size

    def setup_main_layout(self) -> None:
        """Setup central widget and main layout."""
        self.parent_window.central_widget = QWidget()
        self.parent_window.setCentralWidget(self.parent_window.central_widget)
        self.parent_window.main_layout = QVBoxLayout(self.parent_window.central_widget)

    def _calculate_optimal_splitter_sizes(self, window_width: int):
        """Calculate optimal splitter sizes based on window width using percentage-based approach."""
        # Base percentages derived from good 4:3 ratios (230px sides on 1177px = ~19.5% each)
        left_percentage = 0.195   # ~19.5% for left panel
        right_percentage = 0.195  # ~19.5% for right panel

        # Calculate sizes based on percentages
        left_width = int(window_width * left_percentage)
        right_width = int(window_width * right_percentage)
        center_width = window_width - left_width - right_width

        # Apply minimum constraints to prevent panels from becoming too small
        left_min = 200   # Absolute minimum for left panel
        right_min = 200  # Absolute minimum for right panel
        center_min = 400  # Absolute minimum for center panel

        # Ensure minimums are respected
        left_width = max(left_width, left_min)
        right_width = max(right_width, right_min)

        # Recalculate center if minimums were applied
        center_width = window_width - left_width - right_width
        center_width = max(center_width, center_min)

        optimal_sizes = [left_width, center_width, right_width]

        logger.debug(f"[UIManager] Calculated splitter sizes for {window_width}px: {optimal_sizes} "
                    f"({left_width/window_width*100:.1f}%, {center_width/window_width*100:.1f}%, {right_width/window_width*100:.1f}%)", extra={"dev_only": True})
        return optimal_sizes

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

        # Search layout
        search_layout = QHBoxLayout()
        self.parent_window.metadata_search_field = QLineEdit()
        self.parent_window.metadata_search_field.setPlaceholderText("Search metadata...")
        self.parent_window.metadata_search_field.setFixedHeight(20)  # Same height as rename module combo boxes
        self.parent_window.metadata_search_field.setObjectName("metadataSearchField")  # For QSS styling

        # Add search icon as QAction (always last)
        self.parent_window.search_action = QAction(QIcon("resources/icons/feather_icons/search_dark.svg"), "Search", self.parent_window.metadata_search_field)
        self.parent_window.metadata_search_field.addAction(self.parent_window.search_action, QLineEdit.TrailingPosition)

        # Add clear icon (X) as QAction - Trailing, πριν το φακό
        self.parent_window.clear_search_action = QAction(QIcon("resources/icons/feather_icons/x_dark.svg"), "Clear", self.parent_window.metadata_search_field)
        self.parent_window.clear_search_action.triggered.connect(self._clear_metadata_search)
        # Προσθέτουμε το Χ πριν το search icon (Trailing, αλλά μπαίνει πρώτο)
        self.parent_window.metadata_search_field.addAction(self.parent_window.clear_search_action, QLineEdit.TrailingPosition)
        self.parent_window.clear_search_action.setVisible(False)  # Initially hidden

        # Set up custom context menu for search field
        self.parent_window.metadata_search_field.setContextMenuPolicy(Qt.CustomContextMenu)
        self.parent_window.metadata_search_field.customContextMenuRequested.connect(
            lambda pos: self._show_search_context_menu(pos, self.parent_window.metadata_search_field)
        )

        # QSortFilterProxyModel για το metadata tree
        from widgets.metadata_tree_view import MetadataProxyModel
        self.parent_window.metadata_proxy_model = MetadataProxyModel()
        self.parent_window.metadata_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.parent_window.metadata_proxy_model.setFilterKeyColumn(-1)  # Όλα τα columns

        # Συνδέουμε το QLineEdit με το proxy model
        self.parent_window.metadata_search_field.textChanged.connect(self._on_metadata_search_text_changed)

        search_layout.addWidget(self.parent_window.metadata_search_field)
        right_layout.addLayout(search_layout)

        # Metadata Tree View
        self.parent_window.metadata_tree_view = MetadataTreeView()
        # NOTE: files_dropped signal is no longer connected - FileTableView calls MetadataManager directly
        # Συνδέουμε το proxy model με το tree view
        self.parent_window.metadata_tree_view.setModel(self.parent_window.metadata_proxy_model)
        right_layout.addWidget(self.parent_window.metadata_tree_view)
        logger.debug("[UIManager] MetadataTreeView widget added to layout", extra={"dev_only": True})

        # Dummy initial model
        placeholder_model = QStandardItemModel()
        placeholder_model.setHorizontalHeaderLabels(["Key", "Value"])
        placeholder_item = QStandardItem("No file selected")
        placeholder_item.setTextAlignment(Qt.AlignLeft)
        placeholder_value = QStandardItem("-")
        placeholder_model.appendRow([placeholder_item, placeholder_value])
        self.parent_window.metadata_proxy_model.setSourceModel(placeholder_model)

        # Set minimum size for right panel and finalize
        self.parent_window.right_frame.setMinimumWidth(230)
        self.parent_window.horizontal_splitter.addWidget(self.parent_window.right_frame)

        # Calculate optimal splitter sizes based on current window width
        current_width = self.parent_window.width()
        optimal_splitter_sizes = self._calculate_optimal_splitter_sizes(current_width)
        self.parent_window.horizontal_splitter.setSizes(optimal_splitter_sizes)

        # Initialize MetadataTreeView with parent connections
        self.parent_window.metadata_tree_view.initialize_with_parent()

        # Initialize search state
        self.parent_window._metadata_search_text = ""  # Store current search text for session persistence

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

        # Connect metadata tree view signals for editing operations
        self.parent_window.metadata_tree_view.value_edited.connect(self.parent_window.on_metadata_value_edited)
        self.parent_window.metadata_tree_view.value_reset.connect(self.parent_window.on_metadata_value_reset)
        self.parent_window.metadata_tree_view.value_copied.connect(self.parent_window.on_metadata_value_copied)

        self.parent_window.rename_button.clicked.connect(self.parent_window.rename_files)

        # --- Connect the updated signal of RenameModulesArea to generate_preview_names ---
        self.parent_window.rename_modules_area.updated.connect(self.parent_window.request_preview_update)

        # Enable SelectionStore mode in FileTableView after signals are connected
        schedule_selection_update(self.parent_window._enable_selection_store_mode, 100)

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
            ("Ctrl+S", self.parent_window.shortcut_save_selected_metadata),
            ("Ctrl+Shift+S", self.parent_window.shortcut_save_all_metadata),
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

    def _show_search_context_menu(self, position, line_edit: QLineEdit) -> None:
        """
        Show custom context menu for the search field with consistent styling and icons.
        """
        menu = QMenu(line_edit)

        # Standard editing actions
        undo_action = QAction("Undo", menu)
        undo_action.setIcon(get_menu_icon("rotate-ccw"))
        undo_action.triggered.connect(line_edit.undo)
        undo_action.setEnabled(line_edit.isUndoAvailable())
        menu.addAction(undo_action)

        redo_action = QAction("Redo", menu)
        redo_action.setIcon(get_menu_icon("rotate-cw"))
        redo_action.triggered.connect(line_edit.redo)
        redo_action.setEnabled(line_edit.isRedoAvailable())
        menu.addAction(redo_action)

        menu.addSeparator()

        cut_action = QAction("Cut", menu)
        cut_action.setIcon(get_menu_icon("scissors"))
        cut_action.triggered.connect(line_edit.cut)
        cut_action.setEnabled(line_edit.hasSelectedText())
        menu.addAction(cut_action)

        copy_action = QAction("Copy", menu)
        copy_action.setIcon(get_menu_icon("copy"))
        copy_action.triggered.connect(line_edit.copy)
        copy_action.setEnabled(line_edit.hasSelectedText())
        menu.addAction(copy_action)

        paste_action = QAction("Paste", menu)
        paste_action.setIcon(get_menu_icon("clipboard"))  # Using clipboard as paste icon
        paste_action.triggered.connect(line_edit.paste)
        menu.addAction(paste_action)

        menu.addSeparator()

        select_all_action = QAction("Select All", menu)
        select_all_action.setIcon(get_menu_icon("check-square"))
        select_all_action.triggered.connect(line_edit.selectAll)
        select_all_action.setEnabled(bool(line_edit.text()))
        menu.addAction(select_all_action)

        # Show the menu at the cursor position
        global_pos = line_edit.mapToGlobal(position)
        menu.exec_(global_pos)

    def _on_metadata_search_text_changed(self):
        """Handle text changes in the metadata search field."""
        text = self.parent_window.metadata_search_field.text()
        self.parent_window.clear_search_action.setVisible(bool(text))
        self.parent_window._metadata_search_text = text

        # Use setFilterRegExp for better filtering with the custom proxy model
        self.parent_window.metadata_proxy_model.setFilterRegExp(text)

        # Always expand all groups after filtering to keep them open
        schedule_ui_update(self.parent_window.metadata_tree_view.expandAll, 10)

    def _clear_metadata_search(self):
        """Clear the metadata search field and hide the clear button."""
        self.parent_window.metadata_search_field.clear()
        self.parent_window.clear_search_action.setVisible(False)
        self.parent_window._metadata_search_text = ""
        self.parent_window.metadata_proxy_model.setFilterRegExp("")

        # Always expand all groups after clearing filter
        schedule_ui_update(self.parent_window.metadata_tree_view.expandAll, 10)

    def restore_metadata_search_text(self):
        """Restore the metadata search text from session storage."""
        if hasattr(self.parent_window, '_metadata_search_text') and self.parent_window._metadata_search_text:
            self.parent_window.metadata_search_field.setText(self.parent_window._metadata_search_text)
            self.parent_window.metadata_proxy_model.setFilterRegExp(self.parent_window._metadata_search_text)
