"""UI Controller Protocols.

Author: Michael Economou
Date: 2026-01-03

Defines Protocol interfaces for UI controllers to enable:
- Static type checking without circular imports
- Easy mocking for tests
- Self-documenting controller dependencies

Note: Controllers cast parent_window to QWidget at runtime for Qt API calls.
The Protocols define the minimum interface each controller needs.
"""

from typing import TYPE_CHECKING, Protocol

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget

if TYPE_CHECKING:
    from PyQt5.QtCore import QStringListModel
    from PyQt5.QtWidgets import (
        QAction,
        QButtonGroup,
        QCompleter,
        QFrame,
        QLabel,
        QLineEdit,
        QPushButton,
        QShortcut,
        QSplitter,
        QStackedWidget,
        QToolButton,
        QVBoxLayout,
    )

    from oncutf.core.application_context import ApplicationContext
    from oncutf.core.ui_managers.shortcut_manager import ShortcutManager
    from oncutf.core.ui_managers.splitter_manager import SplitterManager
    from oncutf.core.ui_managers.status_manager import StatusManager
    from oncutf.models.file_table_model import FileTableModel
    from oncutf.ui.services.utility_manager import UtilityManager
    from oncutf.ui.widgets.custom_file_system_model import CustomFileSystemModel
    from oncutf.ui.widgets.file_table_view import FileTableView
    from oncutf.ui.widgets.file_tree_view import FileTreeView
    from oncutf.ui.widgets.final_transform_container import FinalTransformContainer
    from oncutf.ui.widgets.interactive_header import InteractiveHeader
    from oncutf.ui.widgets.metadata_tree.view import MetadataProxyModel, MetadataTreeView
    from oncutf.ui.widgets.preview_tables_view import PreviewTablesView
    from oncutf.ui.widgets.rename_modules_area import RenameModulesArea
    from oncutf.ui.widgets.thumbnail_viewport import ThumbnailViewportWidget


# =============================================================================
# WindowSetupController Protocol
# =============================================================================


class WindowSetupContext(Protocol):
    """Protocol for WindowSetupController dependencies.

    Attributes needed for window setup: sizing, title, icon.
    """

    context: "ApplicationContext"

    def setWindowTitle(self, title: str) -> None:
        """Set window title."""
        ...

    def setWindowIcon(self, icon: QIcon) -> None:
        """Set window icon."""
        ...

    def resize(self, w: int, h: int) -> None:
        """Resize window."""
        ...

    def setMinimumSize(self, w: int, h: int) -> None:
        """Set minimum window size."""
        ...


# =============================================================================
# ShortcutController Protocol
# =============================================================================


class ShortcutContext(Protocol):
    """Protocol for ShortcutController dependencies.

    Attributes needed for keyboard shortcut registration.
    """

    shortcuts: list["QShortcut"]
    file_table_view: "FileTableView"
    shortcut_manager: "ShortcutManager"

    # File table shortcuts
    def select_all_rows(self) -> None:
        """Select all rows in file table."""
        ...

    def clear_all_selection(self) -> None:
        """Clear file table selection."""
        ...

    def invert_selection(self) -> None:
        """Invert file table selection."""
        ...

    def shortcut_load_metadata(self) -> None:
        """Load metadata for selected files."""
        ...

    def shortcut_load_extended_metadata(self) -> None:
        """Load extended metadata."""
        ...

    def shortcut_calculate_hash_selected(self) -> None:
        """Calculate hash for selected files."""
        ...

    # Global shortcuts
    def handle_browse(self) -> None:
        """Handle folder browse."""
        ...

    def shortcut_save_all_metadata(self) -> None:
        """Save all metadata."""
        ...

    def force_drag_cleanup(self) -> None:
        """Force drag cleanup."""
        ...

    def clear_file_table_shortcut(self) -> None:
        """Clear file table."""
        ...

    def global_undo(self) -> None:
        """Global undo."""
        ...

    def global_redo(self) -> None:
        """Global redo."""
        ...

    def show_command_history(self) -> None:
        """Show command history."""
        ...


# =============================================================================
# SignalController Protocol
# =============================================================================


class SignalContext(Protocol):
    """Protocol for SignalController dependencies.

    Attributes needed for signal connections between UI components.
    """

    # Widgets
    header: "InteractiveHeader"
    select_folder_button: "QPushButton"
    browse_folder_button: "QPushButton"
    rename_button: "QPushButton"
    folder_tree: "FileTreeView"
    file_table_view: "FileTableView"
    file_model: "FileTableModel"
    metadata_tree_view: "MetadataTreeView"
    preview_tables_view: "PreviewTablesView"
    rename_modules_area: "RenameModulesArea"
    final_transform_container: "FinalTransformContainer"

    # Splitters
    horizontal_splitter: "QSplitter"
    vertical_splitter: "QSplitter"
    lower_section_splitter: "QSplitter"

    # Managers
    splitter_manager: "SplitterManager"
    utility_manager: "UtilityManager"
    status_manager: "StatusManager"

    # Search components
    metadata_search_field: "QLineEdit"
    clear_search_action: "QAction"
    metadata_proxy_model: "MetadataProxyModel"
    _metadata_search_text: str

    # Event handlers
    def installEventFilter(self, obj: object) -> None:
        """Install event filter."""
        ...

    def sort_by_column(self, column: int) -> None:
        """Sort by column."""
        ...

    def handle_folder_import(self) -> None:
        """Handle folder import."""
        ...

    def handle_browse(self) -> None:
        """Handle folder browse."""
        ...

    def rename_files(self) -> None:
        """Rename files."""
        ...

    def load_single_item_from_drop(self, path: str) -> None:
        """Load single item from drop."""
        ...

    def on_table_row_clicked(self, index: object) -> None:
        """Handle table row click."""
        ...

    def load_files_from_dropped_items(self, paths: list[str]) -> None:
        """Load files from dropped items."""
        ...

    def request_preview_update(self) -> None:
        """Request preview update."""
        ...

    def request_preview_update_debounced(self) -> None:
        """Request debounced preview update."""
        ...

    def handle_table_context_menu(self, pos: object) -> None:
        """Handle table context menu."""
        ...

    def on_metadata_value_edited(self, key: str, value: str) -> None:
        """Handle metadata value edit."""
        ...

    def on_metadata_value_reset(self, key: str) -> None:
        """Handle metadata value reset."""
        ...

    def on_metadata_value_copied(self, key: str) -> None:
        """Handle metadata value copy."""
        ...

    def _update_status_from_preview(self, status: str) -> None:
        """Update status from preview."""
        ...

    def _enable_selection_store_mode(self) -> None:
        """Enable selection store mode."""
        ...

    def force_reload(self) -> None:
        """Force reload files."""
        ...


# =============================================================================
# LayoutController Protocol
# =============================================================================


class LayoutContext(Protocol):
    """Protocol for LayoutController dependencies.

    Attributes needed for UI layout setup: panels, splitters, widgets.
    """

    # Core layout
    central_widget: "QWidget"
    main_layout: "QVBoxLayout"

    # Splitters
    vertical_splitter: "QSplitter"
    horizontal_splitter: "QSplitter"
    lower_section_splitter: "QSplitter"

    # Frames
    left_frame: "QFrame"
    center_frame: "QFrame"
    right_frame: "QFrame"
    bottom_frame: "QFrame"
    preview_frame: "QFrame"

    # Left panel
    folder_tree: "FileTreeView"
    dir_model: "CustomFileSystemModel"
    select_folder_button: "QPushButton"
    browse_folder_button: "QPushButton"

    # Center panel
    files_label: "QLabel"
    file_table_view: "FileTableView"
    thumbnail_viewport: "ThumbnailViewportWidget"
    viewport_stack: "QStackedWidget"
    file_model: "FileTableModel"
    header: "InteractiveHeader"
    viewport_buttons: dict[str, "QToolButton"]
    viewport_button_group: "QButtonGroup"

    # Right panel
    information_label: "QLabel"
    metadata_tree_view: "MetadataTreeView"
    metadata_search_field: "QLineEdit"
    search_action: "QAction"
    clear_search_action: "QAction"
    metadata_search_completer: "QCompleter"
    metadata_suggestions_model: "QStringListModel"
    metadata_proxy_model: "MetadataProxyModel"
    _metadata_search_text: str

    # Bottom panel
    bottom_layout: "QVBoxLayout"
    rename_modules_area: "RenameModulesArea"
    final_transform_container: "FinalTransformContainer"
    preview_tables_view: "PreviewTablesView"
    status_label: "QLabel"
    status_manager: "StatusManager"
    rename_button: "QPushButton"

    # Footer
    menu_button: "QPushButton"
    version_label: "QLabel"

    # Managers
    splitter_manager: "SplitterManager"

    # QMainWindow methods
    def setCentralWidget(self, widget: "QWidget") -> None:
        """Set central widget."""
        ...

    def width(self) -> int:
        """Get window width."""
        ...
