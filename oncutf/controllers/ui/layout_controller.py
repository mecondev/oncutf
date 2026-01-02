"""Layout Controller.

Author: Michael Economou
Date: 2026-01-02

Handles UI layout setup: panels, splitters, and widget hierarchy.
"""

import platform
from typing import TYPE_CHECKING

from PyQt5.QtCore import QDir, QStringListModel, Qt
from PyQt5.QtGui import QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QCompleter,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from oncutf.config import (
    ALLOWED_EXTENSIONS,
    APP_NAME,
    APP_VERSION,
    LOWER_SECTION_LEFT_MIN_SIZE,
    LOWER_SECTION_RIGHT_MIN_SIZE,
    LOWER_SECTION_SPLIT_RATIO,
    METADATA_TREE_USE_CUSTOM_DELEGATE,
    TOP_BOTTOM_SPLIT_RATIO,
)
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.ui.icons_loader import get_menu_icon
from oncutf.utils.ui.tooltip_helper import TooltipHelper, TooltipType

if TYPE_CHECKING:
    from oncutf.ui.main_window import MainWindow

logger = get_cached_logger(__name__)


class LayoutController:
    """Controller for UI layout and panel setup.

    Responsibilities:
    - Main layout and central widget
    - Splitter configuration
    - Left panel (folder tree)
    - Center panel (file table)
    - Right panel (metadata tree)
    - Bottom layout (rename modules + preview)
    - Footer
    """

    def __init__(self, parent_window: "MainWindow"):
        """Initialize controller with parent window reference.

        Args:
            parent_window: The main application window
        """
        self.parent_window = parent_window
        logger.debug("LayoutController initialized", extra={"dev_only": True})

    def setup(self) -> None:
        """Setup all layout components in order."""
        self._setup_main_layout()
        self._setup_splitters()
        self._setup_left_panel()
        self._setup_center_panel()
        logger.debug("setup_center_panel() completed", extra={"dev_only": True})
        self._setup_right_panel()
        logger.debug("setup_right_panel() completed", extra={"dev_only": True})
        self._setup_bottom_layout()
        self._setup_footer()

    def _setup_main_layout(self) -> None:
        """Setup central widget and main layout."""
        self.parent_window.central_widget = QWidget()
        self.parent_window.setCentralWidget(self.parent_window.central_widget)
        self.parent_window.main_layout = QVBoxLayout(self.parent_window.central_widget)

    def _calculate_optimal_splitter_sizes(self, window_width: int):
        """Calculate optimal splitter sizes based on window width.

        Args:
            window_width: Current window width in pixels

        Returns:
            List of sizes [left, center, right]
        """
        # Delegate to SplitterManager if available
        if hasattr(self.parent_window, "splitter_manager"):
            return self.parent_window.splitter_manager.calculate_optimal_splitter_sizes(
                window_width
            )

        # Fallback to legacy calculation
        return self._legacy_calculate_optimal_splitter_sizes(window_width)

    def _legacy_calculate_optimal_splitter_sizes(self, window_width: int):
        """Legacy splitter size calculation (kept as fallback).

        Args:
            window_width: Current window width in pixels

        Returns:
            List of sizes [left, center, right]
        """
        # Smart percentage calculation based on screen width
        if window_width >= 2560:  # 4K/Ultrawide screens
            left_percentage = 0.12
            right_percentage = 0.18
        elif window_width >= 1920:  # Full HD and above
            left_percentage = 0.15
            right_percentage = 0.20
        elif window_width >= 1366:  # Common laptop resolution
            left_percentage = 0.18
            right_percentage = 0.22
        else:  # Small screens
            left_percentage = 0.20
            right_percentage = 0.25

        # Calculate sizes based on percentages
        left_width = int(window_width * left_percentage)
        right_width = int(window_width * right_percentage)
        center_width = window_width - left_width - right_width

        # Apply minimum constraints
        left_min = 200
        right_min = 200
        center_min = 400

        left_width = max(left_width, left_min)
        right_width = max(right_width, right_min)

        center_width = window_width - left_width - right_width
        center_width = max(center_width, center_min)

        # For very wide screens, cap the side panels
        if window_width >= 2560:
            left_max = 300
            right_max = 450

            if left_width > left_max:
                extra_left = left_width - left_max
                left_width = left_max
                center_width += extra_left

            if right_width > right_max:
                extra_right = right_width - right_max
                right_width = right_max
                center_width += extra_right

        optimal_sizes = [left_width, center_width, right_width]

        logger.debug(
            "Legacy calculated splitter sizes for %dpx: %s",
            window_width,
            optimal_sizes,
            extra={"dev_only": True},
        )
        return optimal_sizes

    def _setup_splitters(self) -> None:
        """Setup vertical and horizontal splitters."""
        self.parent_window.vertical_splitter = QSplitter(Qt.Vertical)  # type: ignore
        self.parent_window.main_layout.addWidget(self.parent_window.vertical_splitter)

        self.parent_window.horizontal_splitter = QSplitter(Qt.Horizontal)  # type: ignore
        self.parent_window.vertical_splitter.addWidget(self.parent_window.horizontal_splitter)
        self.parent_window.vertical_splitter.setSizes(TOP_BOTTOM_SPLIT_RATIO)

        # Set minimum sizes for all panels to 80px
        self.parent_window.horizontal_splitter.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )

    def _setup_left_panel(self) -> None:
        """Setup left panel (folder tree)."""
        # Lazy import: Only load when setting up left panel
        from oncutf.ui.widgets.custom_file_system_model import CustomFileSystemModel
        from oncutf.ui.widgets.file_tree_view import FileTreeView

        self.parent_window.left_frame = QFrame()
        left_layout = QVBoxLayout(self.parent_window.left_frame)
        left_layout.addWidget(QLabel("Folders"))

        self.parent_window.folder_tree = FileTreeView()
        self.parent_window.folder_tree.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.parent_window.folder_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.parent_window.folder_tree.setAlternatingRowColors(True)
        left_layout.addWidget(self.parent_window.folder_tree)

        # Use default Qt behavior (double-click to expand/collapse)
        self.parent_window.folder_tree.setExpandsOnDoubleClick(True)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)

        self.parent_window.select_folder_button = QPushButton("  Import")
        self.parent_window.select_folder_button.setIcon(get_menu_icon("folder"))
        self.parent_window.select_folder_button.setFixedHeight(24)
        self.parent_window.select_folder_button.setFixedWidth(90)

        self.parent_window.browse_folder_button = QPushButton("  Browse")
        self.parent_window.browse_folder_button.setIcon(get_menu_icon("folder-plus"))
        self.parent_window.browse_folder_button.setFixedHeight(24)
        self.parent_window.browse_folder_button.setFixedWidth(90)
        TooltipHelper.setup_tooltip(
            self.parent_window.browse_folder_button, "Browse folder (Ctrl+O)", TooltipType.INFO
        )

        # Add buttons aligned to right
        btn_layout.addStretch()
        btn_layout.addWidget(self.parent_window.select_folder_button)
        btn_layout.addWidget(self.parent_window.browse_folder_button)
        left_layout.addLayout(btn_layout)

        self.parent_window.dir_model = CustomFileSystemModel()

        # Set root path based on platform
        root = "" if platform.system() == "Windows" else "/"
        self.parent_window.dir_model.setRootPath(root)
        self.parent_window.dir_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)

        # Adding filter for allowed file extensions
        name_filters = [f"*.{ext}" for ext in ALLOWED_EXTENSIONS]
        self.parent_window.dir_model.setNameFilters(name_filters)
        self.parent_window.dir_model.setNameFilterDisables(False)

        self.parent_window.folder_tree.setModel(self.parent_window.dir_model)

        for i in range(1, 4):
            self.parent_window.folder_tree.hideColumn(i)

        # Set root index
        self.parent_window.folder_tree.setRootIndex(self.parent_window.dir_model.index(root))

        # Set minimum size for left panel and add to splitter
        self.parent_window.left_frame.setMinimumWidth(230)
        self.parent_window.horizontal_splitter.addWidget(self.parent_window.left_frame)

    def _setup_center_panel(self) -> None:
        """Setup center panel (file table view)."""
        # Lazy import: Only load when setting up center panel
        from oncutf.ui.widgets.file_table_view import FileTableView
        from oncutf.ui.widgets.interactive_header import InteractiveHeader

        self.parent_window.center_frame = QFrame()
        center_layout = QVBoxLayout(self.parent_window.center_frame)

        self.parent_window.files_label = QLabel("Files")
        center_layout.addWidget(self.parent_window.files_label)

        self.parent_window.file_table_view = FileTableView(parent=self.parent_window)
        self.parent_window.file_table_view.parent_window = self.parent_window
        self.parent_window.file_table_view.verticalHeader().setVisible(False)
        self.parent_window.file_table_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.parent_window.file_table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.parent_window.file_table_view.setModel(self.parent_window.file_model)

        # Header setup
        self.parent_window.header = InteractiveHeader(
            Qt.Horizontal, self.parent_window.file_table_view, parent_window=self.parent_window
        )
        self.parent_window.file_table_view.setHorizontalHeader(self.parent_window.header)
        if hasattr(self.parent_window.header, "setDefaultAlignment"):
            self.parent_window.header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.parent_window.header.setSortIndicatorShown(False)
        self.parent_window.header.setSectionsClickable(False)
        self.parent_window.header.setHighlightSections(False)

        self.parent_window.file_table_view.setHorizontalHeader(self.parent_window.header)
        self.parent_window.file_table_view.setAlternatingRowColors(True)
        self.parent_window.file_table_view.setShowGrid(False)
        self.parent_window.file_table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.parent_window.file_table_view.setSortingEnabled(False)
        self.parent_window.file_table_view.setWordWrap(False)

        # Initialize header and set default row height
        self.parent_window.file_table_view.horizontalHeader()
        self.parent_window.file_table_view.verticalHeader().setDefaultSectionSize(22)

        # Show placeholder after setup is complete
        self.parent_window.file_table_view.set_placeholder_visible(True)

        center_layout.addWidget(self.parent_window.file_table_view)
        self.parent_window.center_frame.setMinimumWidth(230)
        self.parent_window.horizontal_splitter.addWidget(self.parent_window.center_frame)

    def _setup_right_panel(self) -> None:
        """Setup right panel (metadata tree view)."""
        # Lazy import: Only load when setting up right panel
        from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

        self.parent_window.right_frame = QFrame()
        right_layout = QVBoxLayout(self.parent_window.right_frame)

        # Information label with dynamic metadata count
        self.parent_window.information_label = QLabel("Information")
        self.parent_window.information_label.setObjectName("informationLabel")
        right_layout.addWidget(self.parent_window.information_label)

        # Search layout
        self._setup_metadata_search(right_layout)

        # Metadata Tree View
        self.parent_window.metadata_tree_view = MetadataTreeView()

        if METADATA_TREE_USE_CUSTOM_DELEGATE:
            from oncutf.ui.delegates.ui_delegates import MetadataTreeItemDelegate

            metadata_delegate = MetadataTreeItemDelegate(self.parent_window.metadata_tree_view)
            self.parent_window.metadata_tree_view.setItemDelegate(metadata_delegate)
            metadata_delegate.install_event_filter(self.parent_window.metadata_tree_view)
            logger.debug("MetadataTreeItemDelegate enabled", extra={"dev_only": True})
        else:
            logger.debug("MetadataTreeItemDelegate disabled via config", extra={"dev_only": True})

        # Connect the proxy model to the tree view
        self.parent_window.metadata_tree_view.setModel(self.parent_window.metadata_proxy_model)
        right_layout.addWidget(self.parent_window.metadata_tree_view)
        logger.debug("MetadataTreeView widget added to layout", extra={"dev_only": True})

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
        self.parent_window._metadata_search_text = ""

    def _setup_metadata_search(self, parent_layout: QVBoxLayout) -> None:
        """Setup metadata search field and related components.

        Args:
            parent_layout: Parent layout to add search components to
        """
        from oncutf.ui.widgets.metadata_tree.view import MetadataProxyModel
        from oncutf.utils.filesystem.path_utils import get_icons_dir

        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 2)

        self.parent_window.metadata_search_field = QLineEdit()
        self.parent_window.metadata_search_field.setPlaceholderText("Search metadata...")
        self.parent_window.metadata_search_field.setFixedHeight(18)
        self.parent_window.metadata_search_field.setObjectName("metadataSearchField")
        self.parent_window.metadata_search_field.setEnabled(False)

        # Add search icon
        search_icon_path = get_icons_dir() / "feather_icons" / "search_dark.svg"
        self.parent_window.search_action = QAction(
            QIcon(str(search_icon_path)), "Search", self.parent_window.metadata_search_field
        )
        self.parent_window.metadata_search_field.addAction(
            self.parent_window.search_action, QLineEdit.TrailingPosition
        )

        # Add clear icon
        clear_icon_path = get_icons_dir() / "feather_icons" / "x_dark.svg"
        self.parent_window.clear_search_action = QAction(
            QIcon(str(clear_icon_path)), "Clear", self.parent_window.metadata_search_field
        )
        self.parent_window.metadata_search_field.addAction(
            self.parent_window.clear_search_action, QLineEdit.TrailingPosition
        )
        self.parent_window.clear_search_action.setVisible(False)

        # Set up custom context menu
        self.parent_window.metadata_search_field.setContextMenuPolicy(Qt.CustomContextMenu)

        # Setup QCompleter for smart metadata suggestions
        self.parent_window.metadata_search_completer = QCompleter()
        self.parent_window.metadata_search_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.parent_window.metadata_search_completer.setFilterMode(Qt.MatchContains)
        self.parent_window.metadata_search_completer.setCompletionMode(QCompleter.PopupCompletion)

        self.parent_window.metadata_suggestions_model = QStringListModel()
        self.parent_window.metadata_search_completer.setModel(
            self.parent_window.metadata_suggestions_model
        )
        self.parent_window.metadata_search_field.setCompleter(
            self.parent_window.metadata_search_completer
        )

        # Proxy model for the metadata tree
        self.parent_window.metadata_proxy_model = MetadataProxyModel()
        self.parent_window.metadata_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.parent_window.metadata_proxy_model.setFilterKeyColumn(-1)

        search_layout.addWidget(self.parent_window.metadata_search_field)
        parent_layout.addLayout(search_layout)

    def _setup_bottom_layout(self) -> None:
        """Setup bottom layout for rename modules and preview."""
        # Lazy imports
        from oncutf.ui.widgets.final_transform_container import FinalTransformContainer
        from oncutf.ui.widgets.preview_tables_view import PreviewTablesView
        from oncutf.ui.widgets.rename_modules_area import RenameModulesArea

        self.parent_window.bottom_frame = QFrame()
        self.parent_window.bottom_layout = QVBoxLayout(self.parent_window.bottom_frame)
        self.parent_window.bottom_layout.setSpacing(0)
        self.parent_window.bottom_layout.setContentsMargins(0, 4, 0, 0)

        # Create horizontal splitter for lower section
        self.parent_window.lower_section_splitter = QSplitter(Qt.Horizontal)  # type: ignore

        # === Left side: Two vertical containers ===
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(4)

        # Top container: Rename modules area
        self.parent_window.rename_modules_area = RenameModulesArea(
            parent=left_container, parent_window=self.parent_window
        )
        left_layout.addWidget(self.parent_window.rename_modules_area, stretch=1)

        left_layout.addSpacing(8)

        # Bottom container: Final transform container
        self.parent_window.final_transform_container = FinalTransformContainer(
            parent=left_container
        )
        left_layout.addWidget(self.parent_window.final_transform_container)

        left_container.setMinimumWidth(LOWER_SECTION_LEFT_MIN_SIZE)

        # === Right: Preview tables view ===
        self.parent_window.preview_tables_view = PreviewTablesView(parent=self.parent_window)

        # Setup bottom controls
        self._setup_bottom_controls()

        # Create preview frame
        self.parent_window.preview_frame = QFrame()
        preview_layout = QVBoxLayout(self.parent_window.preview_frame)
        preview_layout.setContentsMargins(10, 0, 0, 0)
        preview_layout.addWidget(self.parent_window.preview_tables_view)
        preview_layout.addLayout(self._controls_layout)

        self.parent_window.preview_frame.setMinimumWidth(LOWER_SECTION_RIGHT_MIN_SIZE)

        # Add widgets to splitter
        self.parent_window.lower_section_splitter.addWidget(left_container)
        self.parent_window.lower_section_splitter.addWidget(self.parent_window.preview_frame)

        self.parent_window.lower_section_splitter.setCollapsible(0, True)
        self.parent_window.lower_section_splitter.setCollapsible(1, True)

        # Set initial sizes based on LOWER_SECTION_SPLIT_RATIO
        total_ratio = sum(LOWER_SECTION_SPLIT_RATIO)
        left_ratio = LOWER_SECTION_SPLIT_RATIO[0] / total_ratio
        right_ratio = LOWER_SECTION_SPLIT_RATIO[1] / total_ratio

        current_width = self.parent_window.width()
        left_size = int(current_width * left_ratio)
        right_size = int(current_width * right_ratio)

        self.parent_window.lower_section_splitter.setSizes([left_size, right_size])
        self.parent_window.lower_section_splitter.setStretchFactor(0, LOWER_SECTION_SPLIT_RATIO[0])
        self.parent_window.lower_section_splitter.setStretchFactor(1, LOWER_SECTION_SPLIT_RATIO[1])

        self.parent_window.bottom_layout.addWidget(self.parent_window.lower_section_splitter)

    def _setup_bottom_controls(self) -> None:
        """Setup bottom controls (status label and rename button)."""
        from oncutf.core.ui_managers.status_manager import StatusManager

        self._controls_layout = QHBoxLayout()
        self.parent_window.status_label = QLabel("")
        self.parent_window.status_label.setTextFormat(Qt.RichText)

        # Initialize StatusManager
        self.parent_window.status_manager = StatusManager(
            status_label=self.parent_window.status_label
        )

        self.parent_window.rename_button = QPushButton("Rename Files")
        self.parent_window.rename_button.setEnabled(False)
        self.parent_window.rename_button.setFixedWidth(120)

        self._controls_layout.addWidget(self.parent_window.status_label)
        self._controls_layout.addStretch()
        self._controls_layout.addWidget(self.parent_window.rename_button)

    def _setup_footer(self) -> None:
        """Setup footer with version label."""
        footer_separator = QFrame()
        footer_separator.setFrameShape(QFrame.HLine)
        footer_separator.setFrameShadow(QFrame.Sunken)
        footer_separator.setObjectName("footerSeparator")

        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(10, 2, 10, 2)

        # Menu button
        self.parent_window.menu_button = QPushButton()
        self.parent_window.menu_button.setIcon(get_menu_icon("menu"))
        self.parent_window.menu_button.setFixedSize(20, 20)
        TooltipHelper.setup_tooltip(self.parent_window.menu_button, "Menu", TooltipType.INFO)
        self.parent_window.menu_button.setObjectName("menuButton")

        self.parent_window.version_label = QLabel()
        self.parent_window.version_label.setText(f"{APP_NAME} v{APP_VERSION}")
        self.parent_window.version_label.setObjectName("versionLabel")
        self.parent_window.version_label.setAlignment(Qt.AlignLeft)

        footer_layout.addWidget(self.parent_window.menu_button)
        footer_layout.addSpacing(8)
        footer_layout.addWidget(self.parent_window.version_label)
        footer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer_widget.setFixedHeight(24)

        self.parent_window.vertical_splitter.addWidget(self.parent_window.horizontal_splitter)
        self.parent_window.vertical_splitter.addWidget(self.parent_window.bottom_frame)
        self.parent_window.vertical_splitter.setSizes([500, 300])

        self.parent_window.main_layout.addWidget(footer_separator)
        self.parent_window.main_layout.addWidget(footer_widget)
