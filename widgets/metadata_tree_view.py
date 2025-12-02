"""Custom QTreeView widget with drag-and-drop metadata loading support.

This module defines a custom QTreeView widget that supports drag-and-drop functionality
for triggering metadata loading in the Batch File Renamer GUI.
The view accepts file drops ONLY from the internal file table of the application,
and emits signals for metadata operations.

Features:
- Drag & drop support from internal file table only
- Intelligent scroll position memory per file with smooth animation
- Context menu for metadata editing (copy, edit, reset)
- Placeholder mode for empty content
- Modified item tracking with visual indicators

Expected usage:
- Drag files from the file table (but not from external sources)
- Drop onto the metadata tree
- The main window connects to signals and triggers selective metadata loading

Designed for integration with MainWindow and MetadataReader.

Author: Michael Economou
Date: 2025-05-31
"""

import contextlib
import os
import traceback
from typing import Any

from config import METADATA_TREE_COLUMN_WIDTHS, METADATA_TREE_USE_PROXY
from core.theme_manager import get_theme_manager
from core.pyqt_imports import (
    QAbstractItemView,
    QAction,
    QApplication,
    QCursor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QHeaderView,
    QMenu,
    QModelIndex,
    QPalette,
    QPoint,
    QSortFilterProxyModel,
    QStandardItemModel,
    Qt,
    QTreeView,
    QWidget,
    pyqtSignal,
)
from utils.logger_factory import get_cached_logger
from utils.metadata_cache_helper import MetadataCacheHelper
from utils.path_utils import find_parent_with_attribute, paths_equal
from utils.placeholder_helper import create_placeholder_helper
from utils.timer_manager import schedule_drag_cleanup, schedule_scroll_adjust, schedule_ui_update
from widgets.metadata_edit_dialog import MetadataEditDialog

# ApplicationContext integration
try:
    from core.application_context import get_app_context
except ImportError:
    get_app_context = None

# Command system integration
try:
    from core.metadata_command_manager import get_metadata_command_manager
    from core.metadata_commands import EditMetadataFieldCommand, ResetMetadataFieldCommand
except ImportError:
    get_metadata_command_manager = None
    EditMetadataFieldCommand = None
    ResetMetadataFieldCommand = None

# Unified metadata manager integration
try:
    from core.unified_metadata_manager import UnifiedMetadataManager
except ImportError:
    UnifiedMetadataManager = None

logger = get_cached_logger(__name__)


class MetadataProxyModel(QSortFilterProxyModel):
    """Custom proxy model for metadata tree filtering."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setRecursiveFilteringEnabled(True)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """
        Custom filter logic for metadata tree.

        Shows a row if:
        1. The row itself matches the filter
        2. Any of its children match the filter
        3. Its parent matches the filter
        """
        if not self.filterRegExp().pattern():
            return True

        source_model = self.sourceModel()
        if not source_model:
            return True

        # Get the current item
        index = source_model.index(source_row, 0, source_parent)
        if not index.isValid():
            return True

        # Check if current item matches (key or value)
        key_index = source_model.index(source_row, 0, source_parent)
        value_index = source_model.index(source_row, 1, source_parent)

        key_text = source_model.data(key_index, Qt.ItemDataRole.DisplayRole) or ""
        value_text = source_model.data(value_index, Qt.ItemDataRole.DisplayRole) or ""

        pattern = self.filterRegExp().pattern()

        # Check if this item matches
        if pattern.lower() in key_text.lower() or pattern.lower() in value_text.lower():
            return True

        # Check if any child matches
        if source_model.hasChildren(index):
            for i in range(source_model.rowCount(index)):
                if self.filterAcceptsRow(i, index):
                    return True

        return False


class MetadataTreeView(QTreeView):
    """
    Custom tree view that accepts file drag & drop to trigger metadata loading.
    Only accepts drops from the application's file table, not external sources.
    Includes intelligent scroll position memory per file with smooth animation.
    Uses unified placeholder helper for consistent empty state display.

    Signals:
        value_copied: Emitted when a metadata value is copied to clipboard
        value_edited: Emitted when a metadata value is edited
        value_reset: Emitted when a metadata value is reset
    """

    # NOTE: files_dropped signal removed - FileTableView now calls MetadataManager directly

    # Signals for metadata operations
    value_copied = pyqtSignal(str)
    value_edited = pyqtSignal(str, str, str)
    value_reset = pyqtSignal(str)
    # Signal for queued metadata tree rebuilds (thread-safe via Qt event queue)
    rebuild_requested = pyqtSignal(dict, str)  # metadata, context

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)

        # Unified placeholder helper
        self.placeholder_helper = create_placeholder_helper(self, "metadata_tree", icon_size=120)

        # Modified metadata items per file
        self.modified_items_per_file: dict[str, set[str]] = {}
        self.modified_items: set[str] = set()

        # Rebuild lock to prevent concurrent model swaps (race condition protection)
        self._rebuild_in_progress = False
        self._pending_rebuild_request: tuple | None = None  # (metadata, context)

        # Context menu setup
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self._current_menu = None

        # Track if we're in placeholder mode
        self._is_placeholder_mode: bool = True

        # Toggle for metadata proxy usage (configurable for debugging)
        self._use_proxy = METADATA_TREE_USE_PROXY
        if not self._use_proxy:
            logger.warning(
                "[MetadataTree] Metadata proxy disabled via config", extra={"dev_only": True}
            )

        # Display level for metadata filtering (load from config)
        # Note: This must be set before any metadata loading

        # Keep reference to the currently assigned tree model to avoid GC crashes
        self._current_tree_model: QStandardItemModel | None = None
        self._placeholder_model: QStandardItemModel | None = None

        # Scroll position memory: {file_path: scroll_position}
        self._scroll_positions: dict[str, int] = {}
        self._current_file_path: str | None = None
        self._current_display_data: dict[str, Any] = {}
        self._pending_restore_timer_id: str | None = None

        # Expanded items per file: {file_path: [expanded_item_paths]}
        self._expanded_items_per_file: dict[str, list] = {}

        # Unified placeholder helper (replaces old QLabel/QPixmap approach)
        self.placeholder_helper = create_placeholder_helper(self, "metadata_tree", icon_size=120)

        # Setup standard view properties
        self._setup_tree_view_properties()

        # Note: using default delegate and QSS for tree row rendering

        # Setup icon delegate for selected state icon changes

        # Timer for update debouncing
        self._update_timer_id = None

        # Initialize MetadataCacheHelper for unified cache access
        self._cache_helper = None

        # Initialize cache helper when parent is available
        self._initialize_cache_helper()

        # Initialize direct metadata loader
        self._direct_loader = None
        self._initialize_direct_loader()

        # Connect rebuild signal with QueuedConnection for thread-safe model operations
        # This ensures all rebuilds go through Qt event queue and execute in main thread
        self.rebuild_requested.connect(
            self._render_metadata_view_impl,
            Qt.QueuedConnection
        )
        logger.debug(
            "[MetadataTree] QueuedConnection established for rebuild_requested signal",
            extra={"dev_only": True},
        )

        # Setup local keyboard shortcuts for undo/redo
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        """Setup local keyboard shortcuts for metadata tree."""
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QShortcut

        from config import UNDO_REDO_SETTINGS

        # Undo shortcut (Ctrl+Z)
        self.undo_shortcut = QShortcut(QKeySequence(UNDO_REDO_SETTINGS["UNDO_SHORTCUT"]), self)
        self.undo_shortcut.activated.connect(self._undo_metadata_operation)

        # Redo shortcut (Ctrl+R)
        self.redo_shortcut = QShortcut(QKeySequence(UNDO_REDO_SETTINGS["REDO_SHORTCUT"]), self)
        self.redo_shortcut.activated.connect(self._redo_metadata_operation)

        logger.debug("[MetadataTree] Local shortcuts initialized (Ctrl+Z, Ctrl+R)", extra={"dev_only": True})

    def wheelEvent(self, event) -> None:
        """Update hover state after scroll to track cursor position smoothly."""
        super().wheelEvent(event)

        # Update hover after scroll to reflect current cursor position
        delegate = self.itemDelegate()
        if delegate and hasattr(delegate, "hovered_index"):
            pos = self.viewport().mapFromGlobal(QCursor.pos())
            new_index = self.indexAt(pos)
            old_index = delegate.hovered_index

            # Only update if hover changed
            if new_index != old_index:
                delegate.hovered_index = new_index if new_index.isValid() else None
                # Repaint both old and new hover areas
                if old_index and old_index.isValid():
                    self.viewport().update(self.visualRect(old_index))
                if new_index.isValid():
                    self.viewport().update(self.visualRect(new_index))

    def _initialize_cache_helper(self) -> None:
        """Initialize the metadata cache helper."""
        try:
            # Use the persistent cache instance from parent window if available
            parent_window = self._get_parent_with_file_table()
            cache_instance = None
            if parent_window and hasattr(parent_window, "metadata_cache"):
                cache_instance = parent_window.metadata_cache

            self._cache_helper = MetadataCacheHelper(cache_instance)
            logger.debug(
                "[MetadataTreeView] MetadataCacheHelper initialized (with persistent cache)",
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.error(f"[MetadataTreeView] Failed to initialize MetadataCacheHelper: {e}")
            self._cache_helper = None

    def _get_cache_helper(self) -> MetadataCacheHelper | None:
        """Get the MetadataCacheHelper instance, initializing if needed."""
        # Always check if we need to initialize or re-initialize (if cache backend is missing)
        if self._cache_helper is None or (
            self._cache_helper and self._cache_helper.metadata_cache is None
        ):
            self._initialize_cache_helper()
        return self._cache_helper

    def _initialize_direct_loader(self) -> None:
        """Initialize the direct metadata loader."""
        try:
            if UnifiedMetadataManager is not None:
                self._direct_loader = UnifiedMetadataManager()
                logger.debug(
                    "[MetadataTreeView] UnifiedMetadataManager initialized",
                    extra={"dev_only": True},
                )
            else:
                logger.debug(
                    "[MetadataTreeView] UnifiedMetadataManager not available",
                    extra={"dev_only": True},
                )
                self._direct_loader = None
        except Exception as e:
            logger.error(f"[MetadataTreeView] Failed to initialize UnifiedMetadataManager: {e}")
            self._direct_loader = None

    def _get_direct_loader(self):
        """Get the UnifiedMetadataManager instance, initializing if needed."""
        if self._direct_loader is None:
            self._initialize_direct_loader()
        return self._direct_loader

    def _setup_tree_view_properties(self) -> None:
        """Configure standard tree view properties."""
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setUniformRowHeights(True)
        self.expandToDepth(1)
        self.setRootIsDecorated(True)  # Show expand/collapse arrows for consistency
        self.setItemsExpandable(True)  # Ensure items can be expanded/collapsed
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setAlternatingRowColors(True)

    def _setup_icon_delegate(self) -> None:
        """Setup the icon delegate for selection-based icon changes."""
        # Icon delegate functionality removed for simplicity

    # =====================================
    # Path-Safe Dictionary Operations
    # =====================================

    def _path_in_dict(self, path: str, path_dict: dict[str, Any]) -> bool:
        """
        Check if a path exists in dictionary using path-aware comparison.

        Args:
            path: Path to look for
            path_dict: Dictionary with path keys

        Returns:
            bool: True if path exists in dictionary
        """
        if not path or not path_dict:
            return False

        # First try direct lookup (fastest)
        if path in path_dict:
            return True

        # If not found, try normalized path comparison
        return any(paths_equal(path, existing_path) for existing_path in path_dict)

    def _get_from_path_dict(self, path: str, path_dict: dict[str, Any]) -> Any:
        """
        Get value from dictionary using path-aware comparison.

        Args:
            path: Path key to look for
            path_dict: Dictionary with path keys

        Returns:
            Any: Value if found, None otherwise
        """
        if not path or not path_dict:
            return None

        # First try direct lookup (fastest)
        if path in path_dict:
            return path_dict[path]

        # If not found, try normalized path comparison
        for existing_path, value in path_dict.items():
            if paths_equal(path, existing_path):
                return value

        return None

    def _set_in_path_dict(self, path: str, value: Any, path_dict: dict[str, Any]) -> None:
        """
        Set value in dictionary using path-aware key management.

        Args:
            path: Path key to set
            value: Value to set
            path_dict: Dictionary with path keys
        """
        if not path:
            return

        # Remove any existing equivalent paths first
        keys_to_remove = []
        for existing_path in path_dict:
            if paths_equal(path, existing_path):
                keys_to_remove.append(existing_path)

        for key in keys_to_remove:
            del path_dict[key]

        # Set with the new path
        path_dict[path] = value

    def _remove_from_path_dict(self, path: str, path_dict: dict[str, Any]) -> bool:
        """
        Remove path from dictionary using path-aware comparison.

        Args:
            path: Path key to remove
            path_dict: Dictionary with path keys

        Returns:
            bool: True if something was removed
        """
        if not path or not path_dict:
            return False

        removed = False
        keys_to_remove = []

        # Find all equivalent paths
        for existing_path in path_dict:
            if paths_equal(path, existing_path):
                keys_to_remove.append(existing_path)

        # Remove them
        for key in keys_to_remove:
            del path_dict[key]
            removed = True

        return removed

    def resizeEvent(self, event):
        """Handle resize events to adjust placeholder label size."""
        super().resizeEvent(event)
        if hasattr(self, "placeholder_helper"):
            self.placeholder_helper.update_position()

    # =====================================
    # Drag & Drop Methods
    # =====================================

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        Accept drag only if it comes from our application's file table.
        This is identified by the presence of our custom MIME type.
        """
        if event.mimeData().hasFormat("application/x-oncutf-filetable"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """
        Continue accepting drag move events only for items from our file table.
        """
        if event.mimeData().hasFormat("application/x-oncutf-filetable"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop events for file loading."""
        _drag_cancel_filter = getattr(self, "_drag_cancel_filter", None)
        if _drag_cancel_filter:
            _drag_cancel_filter.deactivate()

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            files = [url.toLocalFile() for url in urls if url.isLocalFile()]
            if files:
                event.acceptProposedAction()
                self._perform_drag_cleanup(_drag_cancel_filter)
                # NOTE: No longer emit signal - FileTableView handles metadata loading directly
                logger.debug(
                    f"[MetadataTreeView] Drop accepted but not processed (handled by FileTableView): {len(files)} files",
                    extra={"dev_only": True},
                )
            else:
                event.ignore()
                self._perform_drag_cleanup(_drag_cancel_filter)
        else:
            event.ignore()
            self._perform_drag_cleanup(_drag_cancel_filter)

        # Schedule drag cleanup
        schedule_drag_cleanup(self._complete_drag_cleanup, 0)

    def _perform_drag_cleanup(self, _drag_cancel_filter: Any) -> None:
        """Centralized drag cleanup logic."""
        # Force cleanup of any drag state
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
        self.viewport().update()

    def _complete_drag_cleanup(self) -> None:
        """Complete cleanup after drag operation."""
        self.viewport().update()

    # =====================================
    # Model & Column Management
    # =====================================

    def setModel(self, model: Any) -> None:
        """
        Override the setModel method to set minimum column widths after the model is set.
        """
        # Cancel any pending restore operation
        if self._pending_restore_timer_id is not None:
            self._pending_restore_timer_id = None

        # First call the parent implementation
        super().setModel(model)

        # Then set column sizes if we have a header and model
        if model and self.header():
            is_placeholder = self._detect_placeholder_mode(model)
            self._is_placeholder_mode = is_placeholder

            if is_placeholder:
                self._configure_placeholder_mode(model)
                self._current_file_path = None  # No file selected
            else:
                self._configure_normal_mode()

                # For non-placeholder mode, immediately restore scroll position
                # This prevents the "jump to 0 then scroll to final position" effect
                if self._current_file_path and self._current_file_path in self._scroll_positions:
                    # Get the saved position
                    saved_position = self._scroll_positions[self._current_file_path]

                    # Schedule scroll position restoration
                    schedule_scroll_adjust(
                        lambda: self._apply_scroll_position_immediately(saved_position), 0
                    )

            # Update header visibility after mode configuration
            self._update_header_visibility()

    def _apply_scroll_position_immediately(self, position: int) -> None:
        """Apply scroll position immediately without waiting for expandAll()."""
        if self._current_file_path and not self._is_placeholder_mode:
            scrollbar = self.verticalScrollBar()
            max_scroll = scrollbar.maximum()

            # Clamp position to valid range
            valid_position = min(position, max_scroll)
            valid_position = max(valid_position, 0)

            # Apply the position
            scrollbar.setValue(valid_position)

    def _detect_placeholder_mode(self, model: Any) -> bool:
        """Detect if the model contains placeholder content."""
        # Check if it's a proxy model and get the source model
        source_model = model
        if hasattr(model, "sourceModel") and callable(model.sourceModel):
            source_model = model.sourceModel()
            if not source_model:
                return True  # No source model = placeholder

        # Empty model (for PNG placeholder) is also placeholder mode
        if source_model.rowCount() == 0:
            return True

        if source_model.rowCount() == 1:
            root = source_model.invisibleRootItem()
            if root and root.rowCount() == 1:
                item = root.child(0, 0)
                if item and "No file" in item.text():
                    return True

        return False

    def _configure_placeholder_mode(self, _model: Any) -> None:
        """Configure view for placeholder mode with anti-flickering."""

        # Protection against repeated calls to placeholder mode - but only if ALL conditions are already met
        if (
            getattr(self, "_is_placeholder_mode", False)
            and self.placeholder_helper
            and self.placeholder_helper.is_visible()
        ):
            return  # Already fully configured for placeholder mode, no need to reconfigure

        # Only reset current file path when entering placeholder mode
        # DO NOT clear scroll positions - we want to preserve them for other files
        self._current_file_path = None

        # Use batch updates to prevent flickering during placeholder setup
        self.setUpdatesEnabled(False)

        try:
            # Show placeholder using unified helper
            if self.placeholder_helper:
                self.placeholder_helper.show()
            else:
                logger.warning("[MetadataTree] Could not show placeholder - missing helper")

            # Placeholder mode: Fixed columns, no selection, no hover, NO HORIZONTAL SCROLLBAR
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # type: ignore

            header = self.header()
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.setSectionResizeMode(1, QHeaderView.Fixed)
            # Use placeholder widths for placeholder mode
            header.resizeSection(0, METADATA_TREE_COLUMN_WIDTHS["PLACEHOLDER_KEY_WIDTH"])
            header.resizeSection(1, METADATA_TREE_COLUMN_WIDTHS["PLACEHOLDER_VALUE_WIDTH"])

            # Disable header interactions and hide header in placeholder mode
            header.setEnabled(False)
            header.setSectionsClickable(False)
            header.setSortIndicatorShown(False)
            header.hide()

            # Disable tree interactions but keep drag & drop working
            self.setSelectionMode(QAbstractItemView.NoSelection)
            self.setItemsExpandable(False)
            self.setRootIsDecorated(False)
            self.setContextMenuPolicy(Qt.NoContextMenu)
            self.setMouseTracking(False)

            # Set placeholder property for styling
            self.setProperty("placeholder", True)

        finally:
            # Re-enable updates and force a single refresh
            self.setUpdatesEnabled(True)
            if hasattr(self, "viewport") and callable(getattr(self.viewport(), "update", None)):
                self.viewport().update()

    def _configure_normal_mode(self) -> None:
        """Configure view for normal content mode with anti-flickering."""

        # Use batch updates to prevent flickering during normal mode setup
        self.setUpdatesEnabled(False)

        try:
            # Hide placeholder when showing normal content
            if self.placeholder_helper:
                self.placeholder_helper.hide()

            # Normal content mode: HORIZONTAL SCROLLBAR enabled but controlled
            self._update_scrollbar_policy_intelligently(Qt.ScrollBarAsNeeded)
            # Also ensure vertical scrollbar is set properly
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # type: ignore

            header = self.header()

            # Re-enable header interactions
            header.setEnabled(True)
            header.setSectionsClickable(True)
            header.setSortIndicatorShown(False)  # Keep sorting disabled

            # Show header when there's content
            header.show()

            # Key column: min 80px, initial 180px, max 800px
            header.setSectionResizeMode(0, QHeaderView.Interactive)
            header.setMinimumSectionSize(METADATA_TREE_COLUMN_WIDTHS["KEY_MIN_WIDTH"])
            header.resizeSection(0, METADATA_TREE_COLUMN_WIDTHS["NORMAL_KEY_INITIAL_WIDTH"])

            # Value column: min 250px, initial 500px, allows wide content without stretching
            header.setSectionResizeMode(1, QHeaderView.Interactive)
            header.resizeSection(1, METADATA_TREE_COLUMN_WIDTHS["NORMAL_VALUE_INITIAL_WIDTH"])

            # Set specific min/max sizes per column
            header.setMinimumSectionSize(METADATA_TREE_COLUMN_WIDTHS["KEY_MIN_WIDTH"])
            header.setMaximumSectionSize(METADATA_TREE_COLUMN_WIDTHS["KEY_MAX_WIDTH"])

            # Connect resize signals to immediately update display
            self._connect_column_resize_signals()

            # Re-enable tree interactions
            self.setSelectionMode(QAbstractItemView.SingleSelection)
            self.setItemsExpandable(True)
            self.setRootIsDecorated(True)  # Show expand/collapse arrows for categories
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.setMouseTracking(True)

            # Clear placeholder property
            self.setProperty("placeholder", False)
            self.setAttribute(Qt.WA_NoMousePropagation, False)

            # Force style update
            self._force_style_update()

        finally:
            # Re-enable updates and force a single refresh
            self.setUpdatesEnabled(True)
            if hasattr(self, "viewport") and callable(getattr(self.viewport(), "update", None)):
                self.viewport().update()

    def _update_header_visibility(self) -> None:
        """Update header visibility based on whether there is content in the model."""
        if not self.model():
            logger.debug("[MetadataTree] No model - header hidden", extra={"dev_only": True})
            return

        header = self.header()
        if not header:
            logger.debug(
                "[MetadataTree] No header - cannot update visibility", extra={"dev_only": True}
            )
            return

        # Hide header when in placeholder mode, show when there's content
        header.setVisible(not self._is_placeholder_mode)

        logger.debug(
            f"[MetadataTree] Header visibility: {'hidden' if self._is_placeholder_mode else 'visible'} (placeholder_mode: {self._is_placeholder_mode})",
            extra={"dev_only": True},
        )

    def _connect_column_resize_signals(self) -> None:
        """Connect column resize signals to update display immediately."""
        header = self.header()
        if header:
            # Disconnect any existing connections
            with contextlib.suppress(AttributeError, RuntimeError, TypeError):
                header.sectionResized.disconnect()

            # Connect to immediate update
            header.sectionResized.connect(self._on_column_resized)

    def _on_column_resized(self, _logical_index: int, _old_size: int, _new_size: int) -> None:
        """Handle column resize events to update display immediately."""
        # Force immediate viewport update
        self.viewport().update()

        # Update the view geometry
        self.updateGeometry()

        # Force a repaint to ensure changes are visible immediately
        self.repaint()

    def _update_scrollbar_policy_intelligently(self, target_policy: int) -> None:
        """Update scrollbar policy only if it differs from current to prevent unnecessary updates."""
        current_policy = self.horizontalScrollBarPolicy()
        if current_policy != target_policy:
            self.setHorizontalScrollBarPolicy(target_policy)

    def _make_placeholder_items_non_selectable(self, model: Any) -> None:
        """Make placeholder items non-selectable."""
        root = model.invisibleRootItem()
        item = root.child(0, 0)
        if item:
            item.setSelectable(False)
        value_item = root.child(0, 1)
        if value_item:
            value_item.setSelectable(False)

    def _force_style_update(self) -> None:
        """Force Qt style system to update."""
        self.style().unpolish(self)
        self.style().polish(self)

    # =====================================
    # Scroll Position Memory
    # =====================================

    def set_current_file_path(self, file_path: str) -> None:
        """Set the current file path and manage scroll position restoration."""
        # If it's the same file, don't do anything
        if paths_equal(self._current_file_path, file_path):
            return

        # Save current file state before switching
        self._save_current_file_state()

        # Update current file (normalize for consistent cache lookups)
        from utils.path_normalizer import normalize_path

        previous_file_path = self._current_file_path
        self._current_file_path = normalize_path(file_path) if file_path else None

        # Load state for the new file
        self._load_file_state(file_path, previous_file_path)

    def _save_current_file_state(self) -> None:
        """Save the current file's state (scroll position, expanded items)."""
        if not self._current_file_path:
            return

        # Save scroll position
        self._save_current_scroll_position()

        # Save expanded state
        model = self.model()
        if model:
            expanded_items = []
            for i in range(model.rowCount()):
                index = model.index(i, 0)
                if self.isExpanded(index):
                    expanded_items.append(index.data())
            self._expanded_items_per_file[self._current_file_path] = expanded_items

    def _load_file_state(self, file_path: str, _previous_file_path: str) -> None:
        """Load the state for a specific file with improved performance."""
        if not file_path:
            return

        # Load expanded state
        expanded_items = self._expanded_items_per_file.get(file_path, [])
        model = self.model()
        if model and expanded_items:
            for i in range(model.rowCount()):
                index = model.index(i, 0)
                if index.data() in expanded_items:
                    self.expand(index)

        # Restore scroll position immediately
        self._restore_scroll_position_for_current_file()

    def _save_current_scroll_position(self) -> None:
        """Save the current scroll position for the current file."""
        if self._current_file_path and not self._is_placeholder_mode:
            scroll_value = self.verticalScrollBar().value()
            self._scroll_positions[self._current_file_path] = scroll_value

    def _restore_scroll_position_for_current_file(self) -> None:
        """Restore the scroll position for the current file with improved UX."""
        if not self._current_file_path or self._is_placeholder_mode:
            return

        scrollbar = self.verticalScrollBar()

        # Check if this is the first time viewing this file
        if self._current_file_path not in self._scroll_positions:
            # First time viewing - go to top immediately (no animation for better UX)
            scrollbar.setValue(0)
            self._scroll_positions[self._current_file_path] = 0
        else:
            # Restore saved position
            saved_position = self._scroll_positions[self._current_file_path]

            # Validate scroll position against current content
            max_scroll = scrollbar.maximum()
            valid_position = max(0, min(saved_position, max_scroll))

            # Apply immediately for better responsiveness
            scrollbar.setValue(valid_position)

        # Clean up the timer
        if self._pending_restore_timer_id is not None:
            self._pending_restore_timer_id = None

    def _smooth_scroll_to_position(self, target_position: int) -> None:
        """Immediate scroll to position for better performance."""
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(target_position)

    def clear_scroll_memory(self) -> None:
        """Clear all saved scroll positions (useful when changing folders)."""
        self._scroll_positions.clear()
        self._current_file_path = None

        # Cancel any pending restore
        if self._pending_restore_timer_id is not None:
            self._pending_restore_timer_id = None

    def restore_scroll_after_expand(self) -> None:
        """Trigger scroll position restore after expandAll() has completed."""
        if self._current_file_path and not self._is_placeholder_mode:
            # Use a shorter delay since we now do immediate restoration in setModel
            if self._pending_restore_timer_id is not None:
                self._pending_restore_timer_id = None

                self._pending_restore_timer_id = schedule_ui_update(
                    self._restore_scroll_position_for_current_file, delay=25
                )

    # =====================================
    # Context Menu & Actions
    # =====================================

    def show_context_menu(self, position: QPoint) -> None:
        """Display context menu with available options."""
        if self._is_placeholder_mode or self.property("placeholder"):
            return

        index = self.indexAt(position)
        if not index.isValid():
            return

        # Close any existing menu
        if self._current_menu:
            self._current_menu.close()
            self._current_menu = None

        key_path = self.get_key_path(index)
        value = index.sibling(index.row(), 1).data()
        selected_files = self._get_current_selection()
        has_multiple_selection = len(selected_files) > 1

        # Check if this field can be edited (standard metadata fields)
        is_editable_field = self._is_editable_metadata_field(key_path)

        # Check if current file has modifications for this field
        has_modifications = False
        current_field_value = None
        if self._current_file_path:
            # Normalize key path for standard metadata fields
            normalized_key_path = self._normalize_metadata_field_name(key_path)

            # Check staging manager
            from core.metadata_staging_manager import get_metadata_staging_manager
            staging_manager = get_metadata_staging_manager()
            if staging_manager:
                staged_changes = staging_manager.get_staged_changes(self._current_file_path)
                has_modifications = normalized_key_path in staged_changes

            # Get current field value
            selected_files = self._get_current_selection()
            if selected_files:
                file_item = selected_files[0]
                # Use cache helper for unified access
                cache_helper = self._get_cache_helper()
                if cache_helper:
                    current_field_value = cache_helper.get_metadata_value(
                        file_item, normalized_key_path
                    )

                # Fallback to file item metadata if not in cache
                if (
                    current_field_value is None
                    and hasattr(file_item, "metadata")
                    and file_item.metadata
                ):
                    current_field_value = self._get_value_from_metadata_dict(
                        file_item.metadata, key_path
                    )

                # Default to empty string if no value found
                if current_field_value is None:
                    current_field_value = ""

        # Create menu
        menu = QMenu(self)
        self._current_menu = menu
        # Apply theme styling
        from utils.theme_engine import ThemeEngine
        theme = ThemeEngine()
        menu.setStyleSheet(theme.get_context_menu_stylesheet())

        # Edit action - enabled for editable metadata fields with single selection
        edit_action = QAction("Edit Value", menu)
        edit_action.setIcon(self._get_menu_icon("edit"))
        edit_action.triggered.connect(lambda: self.edit_value(key_path, value))
        edit_action.setEnabled(not has_multiple_selection and is_editable_field)
        menu.addAction(edit_action)

        # Reset action - enabled for editable fields with modifications
        reset_action = QAction("Reset Value", menu)
        reset_action.setIcon(self._get_menu_icon("rotate-ccw"))
        reset_action.triggered.connect(lambda: self.reset_value(key_path))
        reset_action.setEnabled(
            not has_multiple_selection and is_editable_field and has_modifications
        )
        menu.addAction(reset_action)

        # Special action for rotation fields - Set to 0°
        is_rotation_field = "rotation" in key_path.lower()
        if is_rotation_field:
            set_zero_action = QAction("Set Rotation to 0°", menu)
            set_zero_action.setIcon(self._get_menu_icon("rotate-ccw"))
            set_zero_action.triggered.connect(lambda: self.set_rotation_to_zero(key_path))

            # Enable only if: single selection + rotation field + current value is not "0"
            is_zero_rotation = (
                str(current_field_value) == "0" if current_field_value is not None else False
            )
            set_zero_enabled = not has_multiple_selection and not is_zero_rotation
            set_zero_action.setEnabled(set_zero_enabled)

            # Update tooltip based on current state
            if has_multiple_selection:
                set_zero_action.setToolTip("Single file selection required")
            elif is_zero_rotation:
                set_zero_action.setToolTip("Rotation is already set to 0°")
            else:
                set_zero_action.setToolTip(f"Set rotation to 0° (current: {current_field_value}°)")

            menu.addAction(set_zero_action)

        menu.addSeparator()

        # Add/Remove to File View toggle action
        is_column_visible = self._is_column_visible_in_file_view(key_path)

        if is_column_visible:
            file_view_action = QAction("Remove from File View", menu)
            file_view_action.setIcon(self._get_menu_icon("minus-circle"))
            file_view_action.setToolTip(f"Remove '{key_path}' column from file view")
            file_view_action.triggered.connect(lambda: self._remove_column_from_file_view(key_path))
        else:
            file_view_action = QAction("Add to File View", menu)
            file_view_action.setIcon(self._get_menu_icon("plus-circle"))
            file_view_action.setToolTip(f"Add '{key_path}' column to file view")
            file_view_action.triggered.connect(lambda: self._add_column_to_file_view(key_path))

        menu.addAction(file_view_action)

        menu.addSeparator()

        # History submenu
        history_menu = QMenu("History", menu)
        history_menu.setIcon(self._get_menu_icon("clock"))

        # Undo action
        undo_action = QAction("Undo\tCtrl+Z", history_menu)
        undo_action.setIcon(self._get_menu_icon("rotate-ccw"))
        undo_action.triggered.connect(self._undo_metadata_operation)

        # Redo action
        redo_action = QAction("Redo\tCtrl+R", history_menu)
        redo_action.setIcon(self._get_menu_icon("rotate-cw"))
        redo_action.triggered.connect(self._redo_metadata_operation)

        # Check if undo/redo are available
        try:
            from core.metadata_command_manager import get_metadata_command_manager

            command_manager = get_metadata_command_manager()
            undo_action.setEnabled(command_manager.can_undo())
            redo_action.setEnabled(command_manager.can_redo())

            # Add descriptions to tooltips
            undo_desc = command_manager.get_undo_description()
            redo_desc = command_manager.get_redo_description()
            if undo_desc:
                undo_action.setToolTip(undo_desc)
            if redo_desc:
                redo_action.setToolTip(redo_desc)

        except Exception as e:
            logger.warning(f"[MetadataTreeView] Error checking command manager status: {e}")
            undo_action.setEnabled(False)
            redo_action.setEnabled(False)

        history_menu.addAction(undo_action)
        history_menu.addAction(redo_action)

        history_menu.addSeparator()

        # Show history dialog action
        # REMOVED: This action is now only available in the file table context menu
        # to prevent duplicate dialog calls when right-clicking on file table
        # show_history_action = QAction("Show Command History...", history_menu)
        # show_history_action.setIcon(self._get_menu_icon("list"))
        # show_history_action.triggered.connect(self._show_history_dialog)
        # history_menu.addAction(show_history_action)

        menu.addMenu(history_menu)

        menu.addSeparator()

        # Copy action - always available if there's a value
        copy_action = QAction("Copy", menu)
        copy_action.setIcon(self._get_menu_icon("copy"))
        copy_action.triggered.connect(lambda: self.copy_value(value))
        copy_action.setEnabled(bool(value))
        menu.addAction(copy_action)

        # Use popup() instead of exec_() to avoid blocking
        menu.popup(self.mapToGlobal(position))

        # Connect cleanup to aboutToHide after showing
        menu.aboutToHide.connect(self._cleanup_menu)

    def _cleanup_menu(self) -> None:
        """Clean up the current menu reference."""
        self._current_menu = None

    def _get_menu_icon(self, icon_name: str):
        """Get menu icon using the same system as specified text module."""
        try:
            from utils.icons_loader import get_menu_icon

            return get_menu_icon(icon_name)
        except ImportError:
            return None

    def _is_editable_metadata_field(self, key_path: str) -> bool:
        """Check if a metadata field can be edited directly."""
        # Standard metadata fields that can be edited
        editable_fields = {
            # Rotation field
            "rotation",
            # Basic metadata fields
            "title",
            "artist",
            "author",
            "creator",
            "copyright",
            "description",
            "keywords",
            # Common EXIF/XMP/IPTC fields
            "headline",
            "imagedescription",
            "by-line",
            "copyrightnotice",
            "caption-abstract",
            "rights",
        }

        # Check if key_path contains any editable field name
        key_lower = key_path.lower()
        return any(field in key_lower for field in editable_fields)

    def _normalize_metadata_field_name(self, key_path: str) -> str:
        """Normalize metadata field names to standard form."""
        key_lower = key_path.lower()

        # Rotation field
        if "rotation" in key_lower:
            return "Rotation"

        # Title fields
        if any(field in key_lower for field in ["title", "headline", "imagedescription"]):
            return "Title"

        # Artist/Creator fields
        if any(field in key_lower for field in ["artist", "creator", "by-line"]):
            return "Artist"

        # Author fields (same as Artist for now)
        if "author" in key_lower:
            return "Author"

        # Copyright fields
        if any(field in key_lower for field in ["copyright", "rights", "copyrightnotice"]):
            return "Copyright"

        # Description fields
        if any(field in key_lower for field in ["description", "caption-abstract"]):
            return "Description"

        # Keywords
        if "keywords" in key_lower:
            return "Keywords"

        # Return as-is if no match (fallback)
        return key_path

    def get_key_path(self, index: QModelIndex) -> str:
        """
        Return the full key path for the given index.
        For example: "EXIF/DateTimeOriginal" or "XMP/Creator"
        """
        if not index.isValid():
            return ""

        # If on Value column, get the corresponding Key
        if index.column() == 1:
            index = index.sibling(index.row(), 0)

        # Get the text of the current item
        item_text = index.data()

        # Find the parent group
        parent_index = index.parent()
        if parent_index.isValid():
            parent_text = parent_index.data()
            return f"{parent_text}/{item_text}"

        return item_text

    def copy_value(self, value: Any) -> None:
        """Copy the value to clipboard and emit the value_copied signal."""
        if not value:
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(str(value))
        self.value_copied.emit(str(value))

    # =====================================
    # Metadata Editing Methods
    # =====================================

    def _get_item_path(self, index: QModelIndex) -> list[str]:
        """Get the path from root to the given index as a list of display texts.
        
        Returns:
            List of strings representing the path, e.g. ["File Info", "File Name"]
        """
        path = []
        current = index
        while current.isValid():
            path.insert(0, current.data(Qt.ItemDataRole.DisplayRole))
            current = current.parent()
        return path

    def _find_item_by_path(self, path: list[str]) -> QModelIndex | None:
        """Find an item in the tree by its path from root.
        
        Args:
            path: List of display texts from root to target item
            
        Returns:
            QModelIndex if found, None otherwise
        """
        if not path:
            return None
            
        model = self.model()
        if not model:
            return None
            
        # Start from root
        current_index = QModelIndex()
        
        for text in path:
            found = False
            row_count = model.rowCount(current_index)
            
            for row in range(row_count):
                child_index = model.index(row, 0, current_index)
                if child_index.data(Qt.ItemDataRole.DisplayRole) == text:
                    current_index = child_index
                    found = True
                    break
                    
            if not found:
                logger.debug(f"[MetadataTree] Path item not found: {text}")
                return None
                
        return current_index

    def _find_path_by_key(self, key_path: str) -> list[str] | None:
        """Find the tree path (display names) for a given metadata key path.
        
        Args:
            key_path: Metadata key like "File:FileName" or "EXIF:Make"
            
        Returns:
            List of display names from root to item, e.g. ["File Info", "File Name"]
            None if not found
        """
        model = self.model()
        if not model:
            return None
            
        # Search recursively through the tree
        def search_tree(parent_index: QModelIndex, target_key: str) -> list[str] | None:
            row_count = model.rowCount(parent_index)
            for row in range(row_count):
                index = model.index(row, 0, parent_index)
                
                # Check if this item's key matches
                item_data = index.data(Qt.ItemDataRole.UserRole)
                if item_data and isinstance(item_data, dict):
                    item_key = item_data.get("key", "")
                    if item_key == target_key:
                        # Found it! Build the path
                        return self._get_item_path(index)
                
                # Search children recursively
                child_path = search_tree(index, target_key)
                if child_path:
                    return child_path
                    
            return None
        
        return search_tree(QModelIndex(), key_path)

    def edit_value(self, key_path: str, current_value: Any) -> None:
        """Open a dialog to edit the value of a metadata field."""
        # Save current selection path before opening dialog
        current_index = self.currentIndex()
        saved_path = self._get_item_path(current_index) if current_index.isValid() else None
        
        # Fallback: if no current selection, try to find the item by key_path
        # This handles cases where the tree loses focus between edits
        if not saved_path and key_path:
            # Try to find the item by its key path
            saved_path = self._find_path_by_key(key_path)
            if saved_path:
                logger.debug(f"[MetadataTree] Using fallback path from key_path: {key_path}")
        
        # Get selected files and metadata cache
        selected_files = self._get_current_selection()
        metadata_cache = self._get_metadata_cache()

        if not selected_files:
            logger.warning("[MetadataTree] No files selected for editing")
            return

        # Normalize key path for standard metadata fields
        normalized_key_path = self._normalize_metadata_field_name(key_path)

        # Use the static method from MetadataEditDialog
        accepted, new_value, files_to_modify = MetadataEditDialog.edit_metadata_field(
            parent=self,
            selected_files=selected_files,
            metadata_cache=metadata_cache,
            field_name=normalized_key_path,
            current_value=str(current_value),
        )

        if accepted and new_value != str(current_value):
            # Use command system for undo/redo support
            command_manager = get_metadata_command_manager()
            if command_manager and EditMetadataFieldCommand:
                # Create command for each file to modify
                for file_item in files_to_modify:
                    command = EditMetadataFieldCommand(
                        file_path=file_item.full_path,
                        field_path=normalized_key_path,
                        new_value=new_value,
                        old_value=str(current_value),
                        metadata_tree_view=self,  # Pass self reference
                    )

                    # Execute command (this will update cache and UI)
                    if command_manager.execute_command(command, group_with_previous=True):
                        logger.debug(
                            f"[MetadataTree] Executed edit command for {file_item.filename}"
                        )
                    else:
                        logger.warning(
                            f"[MetadataTree] Failed to execute edit command for {file_item.filename}"
                        )
            else:
                # Fallback to old method if command system not available
                logger.warning("[MetadataTree] Command system not available, using fallback method")
                self._fallback_edit_value(
                    normalized_key_path, new_value, str(current_value), files_to_modify
                )

            # Emit signal for external listeners
            self.value_edited.emit(normalized_key_path, str(current_value), new_value)
            
            # Restore selection AFTER tree has been updated
            # Use custom timer with longer delay to ensure tree refresh completes
            if saved_path:
                schedule_ui_update(lambda: self._restore_selection(saved_path), delay=150)
        else:
            # For cancelled edits, restore immediately
            if saved_path:
                self._restore_selection(saved_path)

    def _restore_selection(self, path: list[str]) -> None:
        """Restore selection to the given path."""
        restored_index = self._find_item_by_path(path)
        if restored_index and restored_index.isValid():
            self.setCurrentIndex(restored_index)
            self.scrollTo(restored_index)
            logger.debug(f"[MetadataTree] Restored selection to: {' > '.join(path)}")
        else:
            logger.debug(f"[MetadataTree] Could not restore selection, path not found")

    def _fallback_edit_value(
        self, key_path: str, new_value: str, _old_value: str, files_to_modify: list
    ) -> None:
        """Fallback method for editing metadata without command system."""
        # Get staging manager
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        logger.info(f"[TreeView] _fallback_edit_value called: staging_manager={staging_manager}")

        if not staging_manager:
            logger.error("Staging manager not available")
            return

        success_count = 0

        for file_item in files_to_modify:
            logger.info(f"[TreeView] About to stage change: {file_item.full_path}, {key_path}, {new_value}")
            # Stage the change
            staging_manager.stage_change(file_item.full_path, key_path, new_value)
            success_count += 1

            # Update the file item's metadata status
            file_item.metadata_status = "modified"

        if success_count == 0:
            logger.warning("[MetadataTree] No files were successfully updated")
            return

        # Update the file icon status immediately
        self._update_file_icon_status()

        # Update the tree display to show the new value
        self._update_tree_item_value(key_path, new_value)

        # Force viewport update to refresh visual state
        self.viewport().update()

    def _get_original_value_from_cache(self, key_path: str) -> Any | None:
        """
        Get the original value of a metadata field from the cache.
        This should be called before resetting to get the original value.
        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return None

        file_item = selected_files[0]
        cache_helper = self._get_cache_helper()
        if not cache_helper:
            return None

        # Use cache helper for unified access
        return cache_helper.get_metadata_value(file_item, key_path)

    def _get_original_metadata_value(self, key_path: str) -> Any | None:
        """
        Get the ORIGINAL metadata value (not staged) for comparison.
        Used by smart_mark_modified to check against actual original values.
        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return None

        file_item = selected_files[0]
        cache_helper = self._get_cache_helper()
        if not cache_helper:
            return None

        # Get original metadata entry (not staged version)
        metadata_entry = cache_helper.get_cache_entry_for_file(file_item)
        if not metadata_entry or not hasattr(metadata_entry, 'data'):
            return None

        # Extract value from original metadata dict
        return self._get_value_from_metadata_dict(metadata_entry.data, key_path)

    def _get_value_from_metadata_dict(self, metadata: dict[str, Any], key_path: str) -> Any | None:
        """
        Extract a value from metadata dictionary using key path.
        """
        parts = key_path.split("/")

        if len(parts) == 1:
            # Top-level key
            return metadata.get(parts[0])
        elif len(parts) == 2:
            # Nested key (group/key)
            group, key = parts
            if group in metadata and isinstance(metadata[group], dict):
                return metadata[group].get(key)

        return None

    def set_rotation_to_zero(self, key_path: str) -> None:
        """Set rotation metadata to 0 degrees."""
        if not key_path:
            return

        # Get current file
        selected_files = self._get_current_selection()
        file_item = selected_files[0] if selected_files else None
        if not file_item:
            logger.warning("[MetadataTree] No file selected for rotation reset")
            return

        # Check if already 0
        current_value = None
        metadata = self._get_metadata_cache()
        if metadata and key_path in metadata:
            current_value = metadata[key_path]
            if current_value in ["0", "0°", 0]:
                logger.debug(
                    f"[MetadataTree] Rotation already set to 0° for {file_item.filename}",
                    extra={"dev_only": True},
                )
                return

        # Use unified metadata manager if available
        if self._direct_loader:
            try:
                # Set rotation to 0
                self._direct_loader.set_metadata_value(file_item.full_path, key_path, "0")

                # Update tree display
                self._update_tree_item_value(key_path, "0")

                # Mark as modified
                self.mark_as_modified(key_path)

                logger.debug(
                    f"[MetadataTree] Set rotation to 0° for {file_item.filename} via UnifiedMetadataManager",
                    extra={"dev_only": True},
                )

                # Emit signal
                self.value_edited.emit(key_path, "0", str(current_value) if current_value else "")

                return
            except Exception as e:
                logger.error(
                    f"[MetadataTree] Failed to set rotation via UnifiedMetadataManager: {e}"
                )

        # Fallback to manual method
        self._fallback_set_rotation_to_zero(key_path, "0", current_value if current_value else "")

    def _fallback_set_rotation_to_zero(
        self, key_path: str, new_value: str, _current_value: Any
    ) -> None:
        """Fallback method for setting rotation to zero without command system."""
        # Get staging manager
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return

        # Update metadata in staging
        selected_files = self._get_current_selection()
        for file_item in selected_files:
            staging_manager.stage_change(file_item.full_path, key_path, new_value)
            file_item.metadata_status = "modified"

        # Update the file icon status immediately
        self._update_file_icon_status()

        # Update the tree display to show the new value
        self._update_tree_item_value(key_path, new_value)

        # Force viewport update to refresh visual state
        self.viewport().update()

    def reset_value(self, key_path: str) -> None:
        """Reset a metadata value to its original value."""
        if not key_path:
            return

        # Get current file
        selected_files = self._get_current_selection()
        file_item = selected_files[0] if selected_files else None
        if not file_item:
            logger.warning("[MetadataTree] No file selected for reset")
            return

        # Get original value
        original_value = self._get_original_value_from_cache(key_path)
        if original_value is None:
            logger.warning(f"[MetadataTree] No original value found for {key_path}")
            return

        # Use unified metadata manager if available
        if self._direct_loader:
            try:
                # Reset to original value
                self._direct_loader.set_metadata_value(
                    file_item.full_path, key_path, str(original_value)
                )

                # Update tree display
                self._update_tree_item_value(key_path, str(original_value))

                # Remove from staging
                from core.metadata_staging_manager import get_metadata_staging_manager
                staging_manager = get_metadata_staging_manager()
                if staging_manager and self._current_file_path:
                    staging_manager.clear_staged_change(self._current_file_path, key_path)

                logger.debug(
                    f"[MetadataTree] Executed reset command for {file_item.filename}",
                    extra={"dev_only": True},
                )

                # Emit signal
                self.value_reset.emit(key_path)

                return
            except Exception as e:
                logger.error(f"[MetadataTree] Failed to reset via UnifiedMetadataManager: {e}")

        # Fallback to manual method
        self._fallback_reset_value(key_path, original_value)

    def _fallback_reset_value(self, key_path: str, original_value: Any) -> None:
        """Fallback method for resetting metadata without command system."""
        # Get staging manager
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        if staging_manager and self._current_file_path:
            # Remove from staging
            staging_manager.clear_staged_change(self._current_file_path, key_path)

        # Update the file icon status
        self._update_file_icon_status()

        # Update the tree display to show the original value
        if original_value is not None:
            self._update_tree_item_value(key_path, str(original_value))

        # Force viewport update to refresh visual state
        self.viewport().update()

    def _update_tree_item_value(self, _key_path: str, _new_value: str) -> None:
        """
        Update the display value of a tree item to reflect changes.
        This forces a refresh of the metadata display with modification context.
        """
        # Debounce/defers the actual tree rebuild to the UI scheduler to avoid
        # race conditions with other UI updates (e.g. file table dataChanged emits
        # and proxy model source swaps). This makes updates sequential and safe.
        def _do_update():
            # Get current metadata and force refresh with modification context
            selected_files = self._get_current_selection()
            cache_helper = self._get_cache_helper()

            if selected_files and cache_helper and len(selected_files) == 1:
                file_item = selected_files[0]
                metadata = cache_helper.get_metadata_for_file(file_item)
                if isinstance(metadata, dict) and metadata:
                    display_metadata = dict(metadata)
                    display_metadata["FileName"] = file_item.filename
                    # Use modification context to force reload
                    self.display_metadata(display_metadata, context="modification")
                    return

            # Fallback to normal update if we can't get metadata
            self.update_from_parent_selection()

        # Schedule the update on the UI scheduler with minimal delay so that
        # other pending UI operations complete first.
        schedule_ui_update(_do_update, delay=0)

    def mark_as_modified(self, key_path: str) -> None:
        """
        Mark an item as modified.
        """
        self.modified_items.add(key_path)

        # Defer icon update to avoid race conditions with tree model rebuilds
        # This ensures file table updates happen after metadata tree is fully updated
        schedule_ui_update(self._update_file_icon_status, delay=0)

        # Update the information label to reflect new modified count
        if hasattr(self, "_current_display_data") and self._current_display_data:
            self._update_information_label(self._current_display_data)

        # Update the view
        self.viewport().update()

    def smart_mark_modified(self, key_path: str, new_value: Any) -> None:
        """Mark a field as modified only if it differs from the original value."""
        # Get original value from ORIGINAL metadata cache, not staging
        original_value = self._get_original_metadata_value(key_path)

        # Convert values to strings for comparison
        new_str = str(new_value) if new_value is not None else ""
        original_str = str(original_value) if original_value is not None else ""

        if new_str != original_str:
            self.mark_as_modified(key_path)
            logger.debug(
                f"[MetadataTree] Marked as modified: {key_path} ('{original_str}' -> '{new_str}')",
                extra={"dev_only": True},
            )
        else:
            # Remove from modifications if values are the same
            if key_path in self.modified_items:
                self.modified_items.remove(key_path)
                logger.debug(
                    f"[MetadataTree] Removed modification mark: {key_path} (value restored to original)",
                    extra={"dev_only": True},
                )

    # =====================================
    # Helper Methods
    # =====================================

    def _get_parent_with_file_table(self) -> QWidget | None:
        """Find the parent window that has file_table_view attribute."""
        return find_parent_with_attribute(self, "file_table_view")

    def _get_current_selection(self):
        """Get current selection via parent traversal."""
        parent_window = self._get_parent_with_file_table()

        if not parent_window:
            return []

        # Try multiple methods to get selection
        selected_files = []

        # Method 1: Use selection model directly
        try:
            selection = parent_window.file_table_view.selectionModel()
            if selection and selection.hasSelection():
                selected_rows = selection.selectedRows()
                if selected_rows and hasattr(parent_window, "file_model"):
                    file_model = parent_window.file_model
                    for index in selected_rows:
                        row = index.row()
                        if 0 <= row < len(file_model.files):
                            selected_files.append(file_model.files[row])
        except Exception as e:
            logger.debug(f"[MetadataTree] Method 1 failed: {e}", extra={"dev_only": True})

        # Method 2: Use file table view's internal selection method
        if not selected_files:
            try:
                if hasattr(parent_window.file_table_view, "_get_current_selection"):
                    selected_rows = parent_window.file_table_view._get_current_selection()
                    if selected_rows and hasattr(parent_window, "file_model"):
                        file_model = parent_window.file_model
                        for row in selected_rows:
                            if 0 <= row < len(file_model.files):
                                selected_files.append(file_model.files[row])
            except Exception as e:
                logger.debug(f"[MetadataTree] Method 2 failed: {e}", extra={"dev_only": True})

        return selected_files

    def _get_metadata_cache(self):
        """Get metadata cache via parent traversal."""
        parent_window = self._get_parent_with_file_table()
        if parent_window and hasattr(parent_window, "metadata_cache"):
            return parent_window.metadata_cache

        return None

    def _update_file_icon_status(self) -> None:
        """
        Update the file icon in the file table to reflect modified status.
        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return

        # Get parent window and file model
        parent_window = self._get_parent_with_file_table()
        if not parent_window:
            return

        file_model = parent_window.file_model
        if not file_model:
            return

        # Get staging manager
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        # For each selected file, update its icon
        updated_rows = []
        for file_item in selected_files:
            # Check if this specific file has modified items
            file_path = file_item.full_path

            # Check if this file has modifications
            has_modifications = False

            if staging_manager:
                has_modifications = staging_manager.has_staged_changes(file_path)

            # Update icon based on whether we have modified items
            if has_modifications:
                # Set modified icon
                file_item.metadata_status = "modified"
            else:
                # Set normal loaded icon
                file_item.metadata_status = "loaded"

            # Find the row for this file item and mark for update
            for row, model_file in enumerate(file_model.files):
                if paths_equal(model_file.full_path, file_path):
                    updated_rows.append(row)
                    break

        # Emit dataChanged for all updated rows to refresh their icons
        for row in updated_rows:
            if 0 <= row < len(file_model.files):
                # Emit dataChanged specifically for the icon column (column 0)
                icon_index = file_model.index(row, 0)
                file_model.dataChanged.emit(icon_index, icon_index, [Qt.DecorationRole])

    def _reset_metadata_in_cache(self, key_path: str) -> None:
        """
        Reset the metadata value in the cache to its original state.
        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]
        cache_helper = self._get_cache_helper()
        if not cache_helper:
            return

        # Get the original value from file item metadata
        original_value = None
        if hasattr(file_item, "metadata") and file_item.metadata:
            original_value = self._get_value_from_metadata_dict(file_item.metadata, key_path)

        # Update cache with original value or remove if no original
        if original_value is not None:
            cache_helper.set_metadata_value(file_item, key_path, original_value)
        else:
            # Remove from cache if no original value
            cache_entry = cache_helper.get_cache_entry_for_file(file_item)
            if cache_entry and hasattr(cache_entry, "data") and key_path in cache_entry.data:
                del cache_entry.data[key_path]

        # Update file icon status based on remaining modified items
        if not self.modified_items:
            file_item.metadata_status = "loaded"
            cache_entry = cache_helper.get_cache_entry_for_file(file_item)
            if cache_entry:
                cache_entry.modified = False
        else:
            file_item.metadata_status = "modified"

        # Trigger UI update
        self._update_file_icon_status()

    def _update_metadata_in_cache(self, key_path: str, new_value: str) -> None:
        """
        Update the metadata value in the cache to persist changes.
        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]
        cache_helper = self._get_cache_helper()
        if cache_helper:
            # Try to set metadata value - will fail if metadata not in cache
            if not cache_helper.set_metadata_value(file_item, key_path, new_value):
                # Failed to set metadata - show error and abort
                logger.error(
                    f"[MetadataTree] Cannot edit {key_path} for {file_item.filename} - metadata not loaded"
                )
                from core.pyqt_imports import QMessageBox

                parent_window = self._get_parent_with_file_table()
                if parent_window:
                    QMessageBox.warning(
                        parent_window,
                        "Metadata Not Loaded",
                        f"Cannot edit metadata for {file_item.filename}.\n\n"
                        "Please load metadata first:\n"
                        "• Right-click → Read Fast Metadata, or\n"
                        "• Right-click → Read Extended Metadata",
                    )
                return

            # Mark the entry as modified
            cache_entry = cache_helper.get_cache_entry_for_file(file_item)
            if cache_entry:
                cache_entry.modified = True

            # Mark file item as modified
            file_item.metadata_status = "modified"

        # Trigger UI update
        self._update_file_icon_status()

    def _remove_metadata_from_cache(self, metadata: dict[str, Any], key_path: str) -> None:
        """Remove metadata entry from cache dictionary."""
        parts = key_path.split("/")

        if len(parts) == 1:
            # Top-level key
            metadata.pop(parts[0], None)
        elif len(parts) == 2:
            # Nested key (group/key)
            group, key = parts
            if group in metadata and isinstance(metadata[group], dict):
                metadata[group].pop(key, None)

    def _remove_metadata_from_file_item(self, file_item: Any, key_path: str) -> None:
        """Remove metadata entry from file item."""
        if hasattr(file_item, "metadata") and file_item.metadata:
            self._remove_metadata_from_cache(file_item.metadata, key_path)

    def _set_metadata_in_cache(
        self, metadata: dict[str, Any], key_path: str, new_value: str
    ) -> None:
        """Set metadata entry in cache dictionary."""
        parts = key_path.split("/")

        if len(parts) == 1:
            # Top-level key
            metadata[parts[0]] = new_value
        elif len(parts) == 2:
            # Nested key (group/key)
            group, key = parts

            if group not in metadata or not isinstance(metadata[group], dict):
                metadata[group] = {}
            metadata[group][key] = new_value

    def _set_metadata_in_file_item(self, file_item: Any, key_path: str, new_value: str) -> None:
        """Set metadata entry in file item. SIMPLIFIED: Rotation is always top-level."""
        if hasattr(file_item, "metadata") and file_item.metadata:
            # Special handling for rotation - it's always top-level
            if key_path.lower() == "rotation":
                # Clean up any existing rotation entries
                if "Rotation" in file_item.metadata:
                    del file_item.metadata["Rotation"]
                if "rotation" in file_item.metadata:
                    del file_item.metadata["rotation"]

                # Remove from any groups too
                for _existing_group, existing_data in list(file_item.metadata.items()):
                    if isinstance(existing_data, dict):
                        if "Rotation" in existing_data:
                            del existing_data["Rotation"]
                        if "rotation" in existing_data:
                            del existing_data["rotation"]

                # Set as top-level
                file_item.metadata["Rotation"] = new_value
            else:
                # Normal handling for non-rotation fields
                self._set_metadata_in_cache(file_item.metadata, key_path, new_value)

    # =====================================
    # Scroll Override
    # =====================================

    def scrollTo(
        self, index: QModelIndex, hint: QAbstractItemView.ScrollHint | None = None
    ) -> None:
        """
        Override scrollTo to prevent automatic scrolling when selections change.
        Scroll position is managed manually via the scroll position memory system.
        This prevents the table from moving when selecting cells from column 1.
        """
        if self._is_placeholder_mode:
            # In placeholder mode, use normal scrolling
            super().scrollTo(index, hint)  # type: ignore
            return

        # In normal mode, do nothing - scroll position is managed manually
        # This prevents Qt from automatically scrolling when selections change
        return

    def focusOutEvent(self, event):
        """Handle focus loss events."""
        super().focusOutEvent(event)

    def drawBranches(self, painter, rect, index):
        """
        Override to paint alternating row background in branch area before branches.
        
        This ensures that the branch indicators (chevrons) are visible on top of
        the alternating row background, fixing the Windows-specific rendering issue
        where the branch area did not receive alternating colors.
        """
        if self.alternatingRowColors() and index.isValid():
            # Paint alternating background in branch area
            if index.row() % 2 == 1:
                bg_color = self.palette().color(QPalette.ColorRole.AlternateBase)
            else:
                bg_color = self.palette().color(QPalette.ColorRole.Base)
            
            painter.fillRect(rect, bg_color)
        
        # Call base implementation to draw branch indicators (chevrons)
        super().drawBranches(painter, rect, index)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        # Close any open context menu on left click
        if event.button() == Qt.LeftButton and self._current_menu:
            self._current_menu.close()
            self._current_menu = None

        super().mousePressEvent(event)

    # =====================================
    # Metadata Display Management Methods
    # =====================================

    def show_empty_state(self, _message: str = "No file selected") -> None:
        """
        Shows empty state using unified placeholder helper.
        No longer creates text model - uses only the placeholder helper.
        """
        # Create empty model to trigger placeholder mode
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["", ""])
        self._placeholder_model = model
        self._current_tree_model = None

        # Use proxy model for consistency (unless disabled via config)
        parent_window = self._get_parent_with_file_table()
        use_proxy = (
            self._use_proxy and parent_window and hasattr(parent_window, "metadata_proxy_model")
        )
        if use_proxy:
            logger.debug(
                "[MetadataTree] Setting empty placeholder source model on metadata_proxy_model",
                extra={"dev_only": True},
            )
            logger.debug(
                "[MetadataTree] setSourceModel (placeholder) stack:\n" + "".join(traceback.format_stack(limit=8)),
                extra={"dev_only": True},
            )
            parent_window.metadata_proxy_model.setSourceModel(model)
            logger.debug(
                "[MetadataTree] Calling setModel(self, metadata_proxy_model) for placeholder",
                extra={"dev_only": True},
            )
            self.setModel(parent_window.metadata_proxy_model)
        else:
            logger.debug(
                "[MetadataTree] Proxy disabled - setting placeholder model directly",
                extra={"dev_only": True},
            )
            self.setModel(None)
            self.setModel(model)
        self._current_tree_model = self._placeholder_model

        # Update header visibility for placeholder mode
        self._update_header_visibility()

        # Disable search field when showing empty state
        self._update_search_field_state(False)

        # Reset information label
        parent_window = self._get_parent_with_file_table()
        if parent_window and hasattr(parent_window, "information_label"):
            parent_window.information_label.setText("Information")
            parent_window.information_label.setStyleSheet("")

        # Update header visibility for empty state
        self._update_header_visibility()

    def clear_view(self) -> None:
        """
        Clears the metadata tree view and shows a placeholder message.
        Does not clear scroll position memory when just showing placeholder.
        """
        self.show_empty_state("No file selected")
        # Update header visibility for placeholder mode
        self._update_header_visibility()
        # Disable search field when clearing view
        self._update_search_field_state(False)

    def display_metadata(self, metadata: dict[str, Any] | None, context: str = "") -> None:
        """Display metadata in the tree view."""
        if not metadata:
            self.show_empty_state("No metadata available")
            return

        try:
            # Render the metadata view
            self._render_metadata_view(metadata, context=context)

            # Update information label
            self._update_information_label(metadata)

            # Enable search field
            self._update_search_field_state(True)

            logger.debug(
                f"[MetadataTree] Displayed metadata for context: {context}",
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.error(f"[MetadataTree] Error displaying metadata: {e}")
            self.show_empty_state("Error loading metadata")

        # Update header visibility after metadata display
        self._update_header_visibility()

    def _update_search_field_state(self, enabled: bool):
        """Update the metadata search field enabled state and tooltip."""
        parent_window = self._get_parent_with_file_table()
        if not parent_window or not hasattr(parent_window, "metadata_search_field"):
            return

        search_field = parent_window.metadata_search_field

        if enabled:
            search_field.setEnabled(True)
            search_field.setReadOnly(False)
            search_field.setToolTip("Search metadata...")
            # Enable action icons
            if hasattr(parent_window, "search_action"):
                parent_window.search_action.setEnabled(True)
            if hasattr(parent_window, "clear_search_action"):
                parent_window.clear_search_action.setEnabled(True)
            # Enable completer
            if hasattr(parent_window, "metadata_search_completer"):
                parent_window.metadata_search_completer.setCompletionMode(
                    parent_window.metadata_search_completer.PopupCompletion
                )
            # Apply complete enabled styling to ensure consistency
            theme = get_theme_manager()
            search_field.setStyleSheet(
                f"""
                QLineEdit#metadataSearchField {{
                    background-color: {theme.get_color('input_bg')};
                    border: 1px solid {theme.get_color('border')};
                    border-radius: 4px;
                    color: {theme.get_color('text')};
                    padding: 2px 8px;
                    min-height: 16px;
                    max-height: 18px;
                    margin-top: 0px;
                    margin-bottom: 2px;
                }}
                QLineEdit#metadataSearchField:hover {{
                    background-color: {theme.get_color('input_hover_bg')};
                    border-color: {theme.get_color('border_hover')};
                }}
                QLineEdit#metadataSearchField:focus {{
                    border-color: {theme.get_color('accent')};
                    background-color: {theme.get_color('input_focus_bg')};
                }}
            """
            )
            # Update suggestions when enabled
            self._update_search_suggestions()
            # Restore any saved search text
            if hasattr(parent_window, "ui_manager"):
                parent_window.ui_manager.restore_metadata_search_text()
        else:
            # Properly disable the field to prevent hover/click reactions
            search_field.setEnabled(False)
            search_field.setReadOnly(True)
            search_field.setToolTip("No metadata available")
            # Disable action icons to make them appear dimmed
            if hasattr(parent_window, "search_action"):
                parent_window.search_action.setEnabled(False)
            if hasattr(parent_window, "clear_search_action"):
                parent_window.clear_search_action.setEnabled(False)
            # Disable completer
            if hasattr(parent_window, "metadata_search_completer"):
                parent_window.metadata_search_completer.setCompletionMode(
                    parent_window.metadata_search_completer.UnfilteredPopupCompletion
                )
            # Apply disabled styling with same dimensions to prevent layout shifts
            theme = get_theme_manager()
            search_field.setStyleSheet(
                f"""
                QLineEdit#metadataSearchField:disabled {{
                    background-color: {theme.get_color('input_bg')};
                    border: 1px solid {theme.get_color('border')};
                    border-radius: 4px;
                    color: {theme.get_color('text_disabled')};
                    padding: 2px 8px;
                    min-height: 16px;
                    max-height: 18px;
                    margin-top: 0px;
                    margin-bottom: 2px;
                }}
                QLineEdit#metadataSearchField:disabled:hover {{
                    background-color: {theme.get_color('input_bg')};
                    color: {theme.get_color('text_disabled')};
                    border: 1px solid {theme.get_color('border')};
                }}
            """
            )
            # Don't clear the search text - preserve it for when metadata is available again

    def _clear_search_field(self):
        """Clear the metadata search field."""
        parent_window = self._get_parent_with_file_table()
        if not parent_window:
            return

        # Call the UI manager's clear method if available
        if hasattr(parent_window, "ui_manager"):
            parent_window.ui_manager._clear_metadata_search()
        elif hasattr(parent_window, "metadata_search_field"):
            # Fallback: clear the field directly
            parent_window.metadata_search_field.clear()
            if hasattr(parent_window, "clear_search_action"):
                parent_window.clear_search_action.setVisible(False)

    def _update_search_suggestions(self):
        """Update search suggestions based on current metadata."""
        try:
            suggestions = set()

            # Get suggestions from current tree model
            model = self.model()
            if model:
                self._collect_suggestions_from_tree_model(model, suggestions)

            # Get suggestions from all loaded files
            all_files = self._get_all_loaded_files()
            for file_item in all_files:
                if hasattr(file_item, "metadata") and file_item.metadata:
                    self._collect_suggestions_from_metadata(file_item.metadata, suggestions)

            # Update search field suggestions
            if hasattr(self, "_search_field") and self._search_field:
                self._search_field.update_suggestions(sorted(suggestions))

            logger.debug(
                f"[MetadataTree] Updated search suggestions: {len(suggestions)} items",
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.error(f"[MetadataTree] Error updating search suggestions: {e}")

    def _collect_suggestions_from_tree_model(self, model, suggestions: set):
        """Collect search suggestions from the current tree model."""
        if not model:
            return

        # If it's a proxy model, get the source model
        source_model = model
        if hasattr(model, "sourceModel"):
            source_model = model.sourceModel()

        # Check if the source model has invisibleRootItem (QStandardItemModel)
        if not hasattr(source_model, "invisibleRootItem"):
            return

        # Traverse the tree model to collect keys and values
        root_item = source_model.invisibleRootItem()
        if not root_item:
            return

        for i in range(root_item.rowCount()):
            group_item = root_item.child(i)
            if not group_item:
                continue

            group_name = group_item.text()

            # Collect from group children
            for j in range(group_item.rowCount()):
                key_item = group_item.child(j, 0)  # Key column
                value_item = group_item.child(j, 1)  # Value column

                if key_item and value_item:
                    key = key_item.text()
                    value = value_item.text()

                    # Skip empty or internal keys
                    if not key or key.startswith("__"):
                        continue

                    # Add the key itself
                    suggestions.add(key)

                    # Add group:key format for grouped items
                    if group_name and group_name != "Other":
                        suggestions.add(f"{group_name}:{key}")

                    # Add values for simple strings (not too long)
                    if (
                        isinstance(value, str)
                        and len(value) < 100
                        and value not in ["-", "", "N/A"]
                    ):
                        # Add key=value format
                        suggestions.add(f"{key}={value}")

                        # Also add group:key=value for grouped items
                        if group_name and group_name != "Other":
                            suggestions.add(f"{group_name}:{key}={value}")

    def _collect_suggestions_from_metadata(self, metadata: dict, suggestions: set):
        """Collect search suggestions from a metadata dictionary."""
        if not isinstance(metadata, dict):
            return

        for key, value in metadata.items():
            # Skip internal keys
            if key.startswith("__"):
                continue

            # Add the key itself
            suggestions.add(key)

            # Handle nested dictionaries (groups)
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    # Add group:key format
                    suggestions.add(f"{key}:{nested_key}")

                    # Add values for nested items (if they're simple strings)
                    if isinstance(nested_value, str) and len(nested_value) < 100:
                        # Add key=value format for easier searching
                        suggestions.add(f"{key}:{nested_key}={nested_value}")

            # Add values for top-level items (if they're simple strings)
            elif isinstance(value, str) and len(value) < 100:
                # Add key=value format
                suggestions.add(f"{key}={value}")

            # Add numeric values as strings
            elif isinstance(value, int | float) and abs(value) < 1000000:
                suggestions.add(f"{key}={value}")

    def _get_all_loaded_files(self):
        """Get all currently loaded files from the parent window."""
        parent_window = self._get_parent_with_file_table()
        if not parent_window or not hasattr(parent_window, "file_model"):
            return []

        if parent_window.file_model and hasattr(parent_window.file_model, "files"):
            return parent_window.file_model.files

        return []

    def _render_metadata_view(self, metadata: dict[str, Any], context: str = "") -> None:
        """
        Public interface for metadata tree rebuild.
        Emits rebuild_requested signal which is processed via QueuedConnection.
        This ensures all model operations happen in the main thread via Qt event queue.
        """
        logger.debug(
            f"[MetadataTree] Emitting rebuild_requested signal (context={context})",
            extra={"dev_only": True},
        )
        self.rebuild_requested.emit(metadata, context)

    def _render_metadata_view_impl(self, metadata: dict[str, Any], context: str = "") -> None:
        """
        Actually builds the metadata tree and displays it.
        Called via QueuedConnection from rebuild_requested signal.
        Assumes metadata is a non-empty dict.

        Includes fallback protection in case called with invalid metadata.
        Uses rebuild lock to prevent concurrent model swaps that cause segfaults.
        """
        logger.debug(
            f"[MetadataTree] Processing queued rebuild request (context={context})",
            extra={"dev_only": True},
        )

        # Check if a rebuild is already in progress
        if self._rebuild_in_progress:
            logger.debug(
                f"[MetadataTree] Rebuild already in progress, deferring request (context={context})",
                extra={"dev_only": True},
            )
            # Store the pending request to process after current rebuild finishes
            self._pending_rebuild_request = (metadata, context)
            return

        if not isinstance(metadata, dict):
            logger.error(
                f"[render_metadata_view] Called with invalid metadata: {type(metadata)} → {metadata}"
            )
            self.clear_view()
            return

        try:
            # Import here to avoid circular imports
            from utils.build_metadata_tree_model import build_metadata_tree_model

            display_data = dict(metadata)
            filename = metadata.get("FileName")
            if filename:
                display_data["FileName"] = filename

            # Store display_data for later use in label updates
            self._current_display_data = display_data

            # Apply any modified values that the user has changed in the UI
            self._apply_modified_values_to_display_data(display_data)

            # Try to determine file path for scroll position memory
            self._set_current_file_from_metadata(metadata)

            # Determine if we have extended metadata and which keys are extended-only
            extended_keys = set()
            if metadata.get("__extended__"):
                # This metadata came from extended loading
                # For a proper implementation, we would need to compare with fast metadata
                # For now, we'll use a heuristic based on key patterns that are typically extended-only
                for key in display_data:
                    key_lower = key.lower()
                    # Mark keys that are typically only available in extended metadata
                    if any(
                        pattern in key_lower
                        for pattern in [
                            "accelerometer",
                            "gyro",
                            "pitch",
                            "roll",
                            "yaw",
                            "segment",
                            "embedded",
                            "extended",
                        ]
                    ):
                        extended_keys.add(key)

            # Get modified keys from staging manager
            modified_keys = set()
            from core.metadata_staging_manager import get_metadata_staging_manager
            staging_manager = get_metadata_staging_manager()
            if staging_manager and self._current_file_path:
                staged_changes = staging_manager.get_staged_changes(self._current_file_path)
                modified_keys = set(staged_changes.keys())

            # Set rebuild lock BEFORE model operations
            self._rebuild_in_progress = True
            logger.debug(
                f"[MetadataTree] Rebuild lock acquired (context={context})",
                extra={"dev_only": True},
            )

            tree_model = build_metadata_tree_model(
                display_data, modified_keys, extended_keys, "all"
            )

            # Use proxy model for filtering instead of setting model directly
            parent_window = self._get_parent_with_file_table()
            use_proxy = (
                self._use_proxy and parent_window and hasattr(parent_window, "metadata_proxy_model")
            )
            if use_proxy:
                # CRITICAL: Disconnect view from model BEFORE changing source model
                # This prevents Qt internal race conditions during model swap
                logger.debug(
                    f"[MetadataTree] Disconnecting view before model swap for file '{filename}'",
                    extra={"dev_only": True},
                )
                # Clear delegate hover state when model changes to prevent stale index references
                delegate = self.itemDelegate()
                if delegate and hasattr(delegate, 'hovered_index'):
                    delegate.hovered_index = None
                self.setModel(None)  # Temporarily disconnect view from proxy model
                self._current_tree_model = None

                # Log and set the source model to the proxy model (debug help for race conditions)
                logger.debug(
                    f"[MetadataTree] Setting source model on metadata_proxy_model for file '{filename}'",
                    extra={"dev_only": True},
                )
                logger.debug(
                    "[MetadataTree] setSourceModel stack:\n" + "".join(traceback.format_stack(limit=8)),
                    extra={"dev_only": True},
                )
                parent_window.metadata_proxy_model.setSourceModel(tree_model)
                self._current_tree_model = tree_model

                # Reconnect view to proxy model AFTER source model is set
                logger.debug(
                    "[MetadataTree] Reconnecting view (setModel metadata_proxy_model)",
                    extra={"dev_only": True},
                )
                self.setModel(parent_window.metadata_proxy_model)  # Use self.setModel() not super()
            else:
                # Fallback: set model directly if proxy model is disabled or unavailable
                logger.debug(
                    f"[MetadataTree] Proxy disabled/unavailable - setting model directly for file '{filename}'",
                    extra={"dev_only": True},
                )
                # Clear delegate hover state when model changes to prevent stale index references
                delegate = self.itemDelegate()
                if delegate and hasattr(delegate, 'hovered_index'):
                    delegate.hovered_index = None
                self.setModel(None)
                self.setModel(tree_model)
                self._current_tree_model = tree_model

            # Always expand all - no collapse functionality
            self.expandAll()

            # Update header visibility for content mode
            self._update_header_visibility()

            # Update information label with metadata count
            self._update_information_label(display_data)

            # Update header visibility for content mode
            self._update_header_visibility()

            # Trigger scroll position restore AFTER expandAll
            self.restore_scroll_after_expand()

            # Update header visibility for content mode
            self._update_header_visibility()

        except Exception as e:
            logger.exception(f"[render_metadata_view] Unexpected error while rendering: {e}")
            self.clear_view()
        finally:
            # ALWAYS release rebuild lock, even on error
            self._rebuild_in_progress = False
            logger.debug(
                f"[MetadataTree] Rebuild lock released (context={context})",
                extra={"dev_only": True},
            )

            # Process any pending rebuild request
            if self._pending_rebuild_request:
                pending_metadata, pending_context = self._pending_rebuild_request
                self._pending_rebuild_request = None
                logger.debug(
                    f"[MetadataTree] Emitting deferred rebuild signal (context={pending_context})",
                    extra={"dev_only": True},
                )
                # Emit signal - it will be queued automatically via QueuedConnection
                self.rebuild_requested.emit(pending_metadata, pending_context)

    def _update_information_label(self, display_data: dict[str, Any]) -> None:
        """Update the information label with metadata statistics."""
        try:
            from config import METADATA_ICON_COLORS

            # Get parent window and information label
            parent_window = self._get_parent_with_file_table()
            if not parent_window or not hasattr(parent_window, "information_label"):
                return

            # Get staging manager for modified count
            from core.metadata_staging_manager import get_metadata_staging_manager
            staging_manager = get_metadata_staging_manager()

            # Count total fields
            total_fields = 0

            def count_fields(data):
                nonlocal total_fields
                for _key, value in data.items():
                    if isinstance(value, dict):
                        count_fields(value)
                    else:
                        total_fields += 1

            count_fields(display_data)

            # Count modified fields from staging manager
            modified_fields = 0
            if staging_manager and self._current_file_path:
                staged_changes = staging_manager.get_staged_changes(self._current_file_path)
                modified_fields = len(staged_changes)

            # Build information label text with styling
            if total_fields == 0:
                # Empty state
                parent_window.information_label.setText("Information")
                parent_window.information_label.setStyleSheet("")
            elif modified_fields > 0:
                # Has modifications - show count with modified color
                info_text = f"Fields: {total_fields} | Modified: {modified_fields}"
                parent_window.information_label.setText(info_text)
                # Set yellow color for modified count
                label_style = f"color: {METADATA_ICON_COLORS['modified']};"
                parent_window.information_label.setStyleSheet(label_style)
            else:
                # No modifications
                info_text = f"Fields: {total_fields}"
                parent_window.information_label.setText(info_text)
                parent_window.information_label.setStyleSheet("")

        except Exception as e:
            logger.debug(f"Error updating information label: {e}", extra={"dev_only": True})

    def _apply_modified_values_to_display_data(self, display_data: dict[str, Any]) -> None:
        """
        Apply any modified values from the Staging Manager to the display data.
        """
        # Get current file
        selected_files = self._get_current_selection()
        if not selected_files or len(selected_files) != 1:
            return

        file_path = selected_files[0].full_path

        # Get staging manager
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return

        # Get staged changes
        staged_changes = staging_manager.get_staged_changes(file_path)
        if not staged_changes:
            return

        # Apply changes to display_data
        for key_path, value in staged_changes.items():
            # Special handling for rotation - it's always top-level
            if key_path.lower() == "rotation":
                display_data["Rotation"] = value
                continue

            # Handle other fields normally
            parts = key_path.split("/")

            if len(parts) == 1:
                # Top-level key
                display_data[parts[0]] = value
            elif len(parts) == 2:
                # Nested key (group/key)
                group, key = parts
                if group not in display_data or not isinstance(display_data[group], dict):
                    display_data[group] = {}
                display_data[group][key] = value

        # Clean up any empty groups
        self._cleanup_empty_groups(display_data)

    def _cleanup_empty_groups(self, display_data: dict[str, Any]) -> None:
        """
        Remove any empty groups from display_data.
        This prevents showing empty group headers in the tree.
        """
        empty_groups = []

        # Get staging manager
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        # Check which groups have modified items
        groups_with_modifications = set()

        if staging_manager and self._current_file_path:
            staged_changes = staging_manager.get_staged_changes(self._current_file_path)
            for key_path in staged_changes:
                if "/" in key_path:
                    group_name = key_path.split("/")[0]
                    groups_with_modifications.add(group_name)

        for group_name, group_data in display_data.items():
            if isinstance(group_data, dict) and len(group_data) == 0:
                # Don't remove groups that have modified items (they will be populated)
                if group_name not in groups_with_modifications:
                    empty_groups.append(group_name)

        for group_name in empty_groups:
            display_data.pop(group_name, None)

    def _set_current_file_from_metadata(self, metadata: dict[str, Any]) -> None:
        """Set current file from metadata if available."""
        try:
            # Try to get file path from metadata
            file_path = metadata.get("File:Directory", "")
            filename = metadata.get("File:FileName", "")

            if file_path and filename:
                full_path = os.path.join(file_path, filename)
                if os.path.exists(full_path):
                    self.set_current_file_path(full_path)
                    logger.debug(
                        f"[MetadataTree] Set current file from metadata: {full_path}",
                        extra={"dev_only": True},
                    )
                    return

            # Try alternative metadata fields
            for field in ["SourceFile", "File:FileName", "System:FileName"]:
                if field in metadata:
                    potential_path = metadata[field]
                    if os.path.exists(potential_path):
                        self.set_current_file_path(potential_path)
                        logger.debug(
                            f"[MetadataTree] Set current file from {field}: {potential_path}",
                            extra={"dev_only": True},
                        )
                        return

        except Exception as e:
            logger.debug(f"Error determining current file: {e}", extra={"dev_only": True})

    # =====================================
    # Selection-based Metadata Management
    # =====================================

    def update_from_parent_selection(self) -> None:
        """Update metadata display based on parent selection."""
        try:
            # Get current selection from parent
            selection = self._get_current_selection()
            if not selection:
                # Try alternative method to get selection if first method failed
                parent_window = self._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "file_table_view"):
                    file_table_view = parent_window.file_table_view
                    if hasattr(file_table_view, "_get_current_selection"):
                        selected_rows = file_table_view._get_current_selection()
                        if selected_rows and hasattr(parent_window, "file_model"):
                            file_model = parent_window.file_model
                            selection = [
                                file_model.files[row]
                                for row in selected_rows
                                if 0 <= row < len(file_model.files)
                            ]

                if not selection:
                    self.show_empty_state("No file selected")
                    return

            # Handle single file selection
            if len(selection) == 1:
                file_item = selection[0]
                metadata = self._try_lazy_metadata_loading(file_item, "parent_selection")
                if metadata:
                    self.display_metadata(metadata, "parent_selection")
                    logger.debug(
                        f"[MetadataTree] Updated from parent selection: {file_item.filename}",
                        extra={"dev_only": True},
                    )
                else:
                    self.show_empty_state("No metadata available")
            else:
                # Multiple files selected
                self.show_empty_state(f"{len(selection)} files selected")
                logger.debug(
                    f"[MetadataTree] Multiple files selected: {len(selection)}",
                    extra={"dev_only": True},
                )

        except Exception as e:
            logger.error(f"[MetadataTree] Error updating from parent selection: {e}")
            self.show_empty_state("Error loading metadata")

    def refresh_metadata_from_selection(self) -> None:
        """
        Convenience method that triggers metadata update from parent selection.
        Can be called from parent window when selection changes.
        """
        self.update_from_parent_selection()

    def initialize_with_parent(self) -> None:
        """
        Performs initial setup that requires parent window to be available.
        Should be called after the tree view is added to its parent.
        """
        self.show_empty_state("No file selected")
        # Initialize search field as disabled
        self._update_search_field_state(False)

    # =====================================
    # Unified Metadata Management Interface
    # =====================================

    def clear_for_folder_change(self) -> None:
        """
        Clears both view and scroll memory when changing folders.
        This is different from clear_view() which preserves scroll memory.
        """
        self.clear_scroll_memory()

        # Clear all staged changes
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()
        if staging_manager:
            staging_manager.clear_all()

        self.clear_view()
        # Update header visibility for placeholder mode
        self._update_header_visibility()
        # Disable search field when changing folders
        self._update_search_field_state(False)

    def display_file_metadata(self, file_item: Any, context: str = "file_display") -> None:
        """
        Display metadata for a specific file item.
        Handles metadata extraction from file_item or cache automatically.

        Args:
            file_item: FileItem object with metadata
            context: Context string for logging
        """
        if not file_item:
            self.clear_view()
            return

        # Try lazy loading first for better performance
        metadata = self._try_lazy_metadata_loading(file_item, context)

        if isinstance(metadata, dict) and metadata:
            display_metadata = dict(metadata)
            display_metadata["FileName"] = file_item.filename

            # Set current file path for scroll position memory
            self.set_current_file_path(file_item.full_path)

            # CRITICAL: Clear any stale modifications for this file when displaying fresh metadata
            # This prevents showing [MODIFIED] for fields that were never actually saved
            from utils.path_normalizer import normalize_path

            normalized_path = normalize_path(file_item.full_path)

            # Check if we have stale modifications
            if self._path_in_dict(normalized_path, self.modified_items_per_file):
                logger.debug(
                    f"[MetadataTree] Clearing stale modifications for {file_item.filename} on metadata display",
                    extra={"dev_only": True},
                )
                self._remove_from_path_dict(normalized_path, self.modified_items_per_file)
                # Also clear current modifications if this is the current file
                if paths_equal(normalized_path, self._current_file_path):
                    self.modified_items.clear()

            self.display_metadata(display_metadata, context=context)
        else:
            self.clear_view()

        # Update header visibility after file metadata display
        self._update_header_visibility()

    def handle_selection_change(self) -> None:
        """
        Handle selection changes from the parent file table.
        This is a convenience method that can be connected to selection signals.
        """
        self.refresh_metadata_from_selection()

    def handle_invert_selection(self, metadata: dict[str, Any] | None) -> None:
        """
        Handle metadata display after selection inversion.

        Args:
            metadata: The metadata to display, or None to clear
        """
        if isinstance(metadata, dict) and metadata:
            self.display_metadata(metadata, context="invert_selection")
        else:
            self.clear_view()

        # Update header visibility after selection inversion
        self._update_header_visibility()

    def handle_metadata_load_completion(self, metadata: dict[str, Any] | None, source: str) -> None:
        """
        Handle metadata display after a metadata loading operation completes.

        Args:
            metadata: The loaded metadata, or None if loading failed
            source: Source of the metadata loading (e.g., "worker", "cache")
        """
        if isinstance(metadata, dict) and metadata:
            self.display_metadata(metadata, context=f"load_completion_from_{source}")
        else:
            self.clear_view()

        # Update header visibility after metadata loading
        self._update_header_visibility()

        # Update file icon status after metadata loading to refresh both metadata and hash icons
        self._update_file_icon_status()

    def _get_app_context(self):
        """Get ApplicationContext with fallback to None."""
        if get_app_context is None:
            return None
        try:
            return get_app_context()
        except RuntimeError:
            # ApplicationContext not ready yet
            return None

    def should_display_metadata_for_selection(self, selected_files_count: int) -> bool:
        """
        Central logic to determine if metadata should be displayed based on selection count.

        Args:
            selected_files_count: Number of currently selected files

        Returns:
            bool: True if metadata should be displayed, False if empty state should be shown
        """
        # Only display metadata for single file selection
        return selected_files_count == 1

    def smart_display_metadata_or_empty_state(
        self, metadata: dict[str, Any] | None, selected_count: int, context: str = ""
    ) -> None:
        """Smart display logic for metadata or empty state."""
        try:
            logger.debug(
                f"[MetadataTree] smart_display_metadata_or_empty_state called: metadata={bool(metadata)}, selected_count={selected_count}, context={context}",
                extra={"dev_only": True},
            )

            if metadata and self.should_display_metadata_for_selection(selected_count):
                logger.debug(
                    f"[MetadataTree] Displaying metadata for {selected_count} selected file(s)",
                    extra={"dev_only": True},
                )
                self.display_metadata(metadata, context)
                logger.debug(
                    f"[MetadataTree] Smart display: showing metadata (context: {context})",
                    extra={"dev_only": True},
                )
            else:
                if selected_count == 0:
                    self.show_empty_state("No file selected")
                elif selected_count > 1:
                    self.show_empty_state(f"{selected_count} files selected")
                else:
                    self.show_empty_state("No metadata available")

                logger.debug(
                    f"[MetadataTree] Smart display: showing empty state (selected: {selected_count})",
                    extra={"dev_only": True},
                )

        except Exception as e:
            logger.error(f"[MetadataTree] Error in smart display: {e}")
            self.show_empty_state("Error loading metadata")

        # Update header visibility after smart display
        self._update_header_visibility()

    def get_modified_metadata(self) -> dict[str, str]:
        """
        Collect all modified metadata items for the current file.

        Returns:
            Dictionary of modified metadata in format {"EXIF/Rotation": "90"}
        """
        # Get staging manager
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return {}

        # Get current file
        selected_files = self._get_current_selection()
        if not selected_files or len(selected_files) != 1:
            return {}

        file_path = selected_files[0].full_path
        return staging_manager.get_staged_changes(file_path)

    def get_all_modified_metadata_for_files(self) -> dict[str, dict[str, str]]:
        """
        Collect all modified metadata for all files that have modifications.

        Returns:
            Dictionary mapping file paths to their modified metadata
        """
        # Get staging manager
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return {}

        return staging_manager.get_all_staged_changes()

    def clear_modifications(self) -> None:
        """
        Clear all modified metadata items for the current file.
        """
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        if staging_manager and self._current_file_path:
            staging_manager.clear_staged_changes(self._current_file_path)

        # Update the information label with current display data
        if hasattr(self, "_current_display_data") and self._current_display_data:
            self._update_information_label(self._current_display_data)

        self._update_file_icon_status()
        self.viewport().update()

    def clear_modifications_for_file(self, file_path: str) -> None:
        """
        Clear modifications for a specific file.

        Args:
            file_path: Full path of the file to clear modifications for
        """
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        if staging_manager:
            staging_manager.clear_staged_changes(file_path)

        # If this is the current file, also clear current modifications and update UI
        if paths_equal(file_path, self._current_file_path):
            # Refresh the view to remove italic style
            if hasattr(self, "display_metadata"):
                # Get current selection to refresh
                selected_files = self._get_current_selection()
                if selected_files and len(selected_files) == 1:
                    file_item = selected_files[0]
                    cache_helper = self._get_cache_helper()
                    if cache_helper:
                        metadata_entry = cache_helper.get_cache_entry_for_file(file_item)
                        if metadata_entry and hasattr(metadata_entry, "data"):
                            display_data = dict(metadata_entry.data)
                            display_data["FileName"] = file_item.filename
                            self.display_metadata(display_data, context="after_save")
            self._update_file_icon_status()
            self.viewport().update()

    def has_modifications_for_selected_files(self) -> bool:
        """
        Check if any of the currently selected files have modifications.

        Returns:
            bool: True if any selected file has modifications
        """
        # Get staging manager
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return False

        # Get selected files
        selected_files = self._get_current_selection()
        if not selected_files:
            return False

        # Check if any selected file has modifications
        for file_item in selected_files:
            if staging_manager.has_staged_changes(file_item.full_path):
                return True

        return False

    def has_any_modifications(self) -> bool:
        """
        Check if there are any modifications in any file.

        Returns:
            bool: True if any file has modifications
        """
        # Get staging manager
        from core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return False

        return staging_manager.has_any_staged_changes()

    # =====================================
    # Lazy Loading Methods
    # =====================================

    def _try_lazy_metadata_loading(
        self, file_item: Any, _context: str = ""
    ) -> dict[str, Any] | None:
        """
        Try to load metadata using simple fallback loading (lazy manager removed).

        Args:
            file_item: FileItem to load metadata for
            context: Context string for logging

        Returns:
            dict: Metadata if available, None if not cached
        """
        # Since LazyMetadataManager was removed, use direct fallback loading
        return self._fallback_metadata_loading(file_item)

    def _fallback_metadata_loading(self, file_item: Any) -> dict[str, Any] | None:
        """Fallback metadata loading method."""
        try:
            if self._cache_helper:
                metadata = self._cache_helper.get_metadata_for_file(file_item)
                if metadata:
                    logger.debug(
                        f"[MetadataTree] Loaded metadata via cache helper for {file_item.filename}",
                        extra={"dev_only": True},
                    )
                    return metadata

            logger.debug(
                f"[MetadataTree] No metadata found for {file_item.filename}",
                extra={"dev_only": True},
            )
            return None

        except Exception as e:
            logger.error(f"[MetadataTree] Error in fallback metadata loading: {e}")
            return None

    # =====================================
    # History Menu Actions
    # =====================================

    def _undo_metadata_operation(self) -> None:
        """Undo the last metadata operation from context menu."""
        try:
            from core.metadata_command_manager import get_metadata_command_manager

            command_manager = get_metadata_command_manager()

            if command_manager.undo():
                logger.info("[MetadataTreeView] Undo operation successful")

                # Get parent window for status message
                parent_window = self._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "Operation undone", success=True, auto_reset=True
                    )
            else:
                logger.info("[MetadataTreeView] No operations to undo")

                # Show status message
                parent_window = self._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "No operations to undo", success=False, auto_reset=True
                    )

        except Exception as e:
            logger.error(f"[MetadataTreeView] Error during undo operation: {e}")

    def _redo_metadata_operation(self) -> None:
        """Redo the last undone metadata operation from context menu."""
        try:
            from core.metadata_command_manager import get_metadata_command_manager

            command_manager = get_metadata_command_manager()

            if command_manager.redo():
                logger.info("[MetadataTreeView] Redo operation successful")

                # Get parent window for status message
                parent_window = self._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "Operation redone", success=True, auto_reset=True
                    )
            else:
                logger.info("[MetadataTreeView] No operations to redo")

                # Show status message
                parent_window = self._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "No operations to redo", success=False, auto_reset=True
                    )

        except Exception as e:
            logger.error(f"[MetadataTreeView] Error during redo operation: {e}")

    def _show_history_dialog(self) -> None:
        """Show metadata history dialog."""
        try:
            from widgets.metadata_history_dialog import MetadataHistoryDialog

            dialog = MetadataHistoryDialog(self)
            dialog.exec_()
        except ImportError:
            logger.warning("MetadataHistoryDialog not available")

    def _is_column_visible_in_file_view(self, key_path: str) -> bool:
        """Check if a column is already visible in the file view."""
        try:
            # Get the file table view
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return False

            # Check if column is in visible columns configuration
            visible_columns = getattr(file_table_view, "_visible_columns", {})

            # Map metadata key to column key
            column_key = self._map_metadata_key_to_column_key(key_path)
            if not column_key:
                return False

            # Check if column is visible
            from config import FILE_TABLE_COLUMN_CONFIG

            if column_key in FILE_TABLE_COLUMN_CONFIG:
                default_visible = FILE_TABLE_COLUMN_CONFIG[column_key]["default_visible"]
                return visible_columns.get(column_key, default_visible)

        except Exception as e:
            logger.warning(f"Error checking column visibility: {e}")

        return False

    def _add_column_to_file_view(self, key_path: str) -> None:
        """Add a metadata column to the file view."""
        try:
            # Get the file table view
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return

            # Map metadata key to column key
            column_key = self._map_metadata_key_to_column_key(key_path)
            if not column_key:
                return

            # Update visibility configuration
            if hasattr(file_table_view, "_visible_columns"):
                file_table_view._visible_columns[column_key] = True

                # Save configuration
                if hasattr(file_table_view, "_save_column_visibility_config"):
                    file_table_view._save_column_visibility_config()

                # Update table display (clears selection)
                if hasattr(file_table_view, "_update_table_columns"):
                    file_table_view._update_table_columns()

                logger.info(f"Added column '{key_path}' -> '{column_key}' to file view")

        except Exception as e:
            logger.error(f"Error adding column to file view: {e}")

    def _remove_column_from_file_view(self, key_path: str) -> None:
        """Remove a metadata column from the file view."""
        try:
            # Get the file table view
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return

            # Map metadata key to column key
            column_key = self._map_metadata_key_to_column_key(key_path)
            if not column_key:
                return

            # Update visibility configuration
            if hasattr(file_table_view, "_visible_columns"):
                file_table_view._visible_columns[column_key] = False

                # Save configuration
                if hasattr(file_table_view, "_save_column_visibility_config"):
                    file_table_view._save_column_visibility_config()

                # Update table display (clears selection)
                if hasattr(file_table_view, "_update_table_columns"):
                    file_table_view._update_table_columns()

                logger.info(f"Removed column '{key_path}' -> '{column_key}' from file view")

        except Exception as e:
            logger.error(f"Error removing column from file view: {e}")

    def _get_file_table_view(self):
        """Get the file table view from the parent hierarchy."""
        try:
            # Look for file table view in parent hierarchy
            parent = self.parent()
            while parent:
                if hasattr(parent, "file_table_view"):
                    return parent.file_table_view

                # Check if parent has file_table attribute
                if hasattr(parent, "file_table"):
                    return parent.file_table

                # Check for main window with file table
                if hasattr(parent, "findChild"):
                    from widgets.file_table_view import FileTableView

                    file_table = parent.findChild(FileTableView)
                    if file_table:
                        return file_table

                parent = parent.parent()

        except Exception as e:
            logger.warning(f"Error finding file table view: {e}")

        return None

    def _map_metadata_key_to_column_key(self, metadata_key: str) -> str | None:
        """Map a metadata key path to a file table column key."""
        try:
            # Create mapping from metadata keys to column keys
            metadata_to_column_mapping = {
                # Image metadata
                "EXIF:ImageWidth": "image_size",
                "EXIF:ImageHeight": "image_size",
                "EXIF:Orientation": "rotation",
                "EXIF:ISO": "iso",
                "EXIF:FNumber": "aperture",
                "EXIF:ExposureTime": "shutter_speed",
                "EXIF:WhiteBalance": "white_balance",
                "EXIF:Compression": "compression",
                "EXIF:Make": "device_manufacturer",
                "EXIF:Model": "device_model",
                "EXIF:SerialNumber": "device_serial_no",
                # Video metadata
                "QuickTime:Duration": "duration",
                "QuickTime:VideoFrameRate": "video_fps",
                "QuickTime:AvgBitrate": "video_avg_bitrate",
                "QuickTime:VideoCodec": "video_codec",
                "QuickTime:MajorBrand": "video_format",
                # Audio metadata
                "QuickTime:AudioChannels": "audio_channels",
                "QuickTime:AudioFormat": "audio_format",
                # File metadata
                "File:FileSize": "file_size",
                "File:FileType": "type",
                "File:FileModifyDate": "modified",
                "File:MD5": "file_hash",
                "File:SHA1": "file_hash",
                "File:SHA256": "file_hash",
            }

            # Direct mapping
            if metadata_key in metadata_to_column_mapping:
                return metadata_to_column_mapping[metadata_key]

            # Fuzzy matching for common patterns
            key_lower = metadata_key.lower()

            if "rotation" in key_lower or "orientation" in key_lower:
                return "rotation"
            elif "duration" in key_lower:
                return "duration"
            elif "iso" in key_lower:
                return "iso"
            elif "aperture" in key_lower or "fnumber" in key_lower:
                return "aperture"
            elif "shutter" in key_lower or "exposure" in key_lower:
                return "shutter_speed"
            elif "white" in key_lower and "balance" in key_lower:
                return "white_balance"
            elif "compression" in key_lower:
                return "compression"
            elif "make" in key_lower or "manufacturer" in key_lower:
                return "device_manufacturer"
            elif "model" in key_lower:
                return "device_model"
            elif "serial" in key_lower:
                return "device_serial_no"
            elif "framerate" in key_lower or "fps" in key_lower:
                return "video_fps"
            elif "bitrate" in key_lower:
                return "video_avg_bitrate"
            elif "codec" in key_lower:
                return "video_codec"
            elif "format" in key_lower:
                if "audio" in key_lower:
                    return "audio_format"
                elif "video" in key_lower:
                    return "video_format"
            elif "channels" in key_lower and "audio" in key_lower:
                return "audio_channels"
            elif "size" in key_lower and (
                "image" in key_lower or "width" in key_lower or "height" in key_lower
            ):
                return "image_size"
            elif "hash" in key_lower or "md5" in key_lower or "sha" in key_lower:
                return "file_hash"

        except Exception as e:
            logger.warning(f"Error mapping metadata key to column key: {e}")

        return None

    def set_placeholder_visible(self, visible: bool) -> None:
        """Show or hide the placeholder using the unified helper."""
        if hasattr(self, "placeholder_helper"):
            if visible:
                self.placeholder_helper.show()
            else:
                self.placeholder_helper.hide()
        # Update header visibility when placeholder state changes
        self._update_header_visibility()

    def update_placeholder_visibility(self):
        """Update placeholder visibility based on tree content."""
        is_empty = self._is_placeholder_mode if hasattr(self, "_is_placeholder_mode") else False
        self.set_placeholder_visible(is_empty)
        # Update header visibility when placeholder visibility changes
        self._update_header_visibility()

    def _handle_metadata_field_click(self, field: str, value: str) -> None:
        """Handle click on metadata field that might be a file path."""
        import os

        if not value:
            return

        # Try to interpret the value as a file path
        if os.path.exists(value):
            self.set_current_file_path(value)
            logger.debug(
                f"[MetadataTreeView] Set current file from metadata field '{field}': {value}"
            )
            return

        # Try to construct path from directory and filename
        file_path = None
        filename = None

        # Check if value looks like a filename
        if os.path.basename(value) == value and "." in value:
            filename = value
            # Try to get directory from current file
            if self._current_file_path:
                file_path = os.path.dirname(self._current_file_path)

        # Check if value looks like a directory
        elif os.path.isdir(value):
            file_path = value
            # Try to get filename from current file
            if self._current_file_path:
                filename = os.path.basename(self._current_file_path)

        # Try to construct full path
        if file_path and filename:
            full_path = os.path.join(file_path, filename)
            if os.path.exists(full_path):
                self.set_current_file_path(full_path)
                logger.debug(
                    f"[MetadataTreeView] Set current file from constructed path: {full_path}"
                )
                return

        # Try to find file in metadata that might be a path
        selected_files = self._get_current_selection()
        if selected_files and hasattr(selected_files[0], "metadata") and selected_files[0].metadata:
            metadata = selected_files[0].metadata
            if field in metadata:
                potential_path = metadata[field]
                if os.path.exists(potential_path):
                    self.set_current_file_path(potential_path)
                    logger.debug(
                        f"[MetadataTreeView] Set current file from metadata field '{field}': {potential_path}"
                    )
                    return
