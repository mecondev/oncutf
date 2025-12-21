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
Date: 2025-05-21
"""

import contextlib
import os
import traceback
from typing import Any

from oncutf.config import METADATA_TREE_COLUMN_WIDTHS, METADATA_TREE_USE_PROXY
from oncutf.core.pyqt_imports import (
    QAbstractItemView,
    QApplication,
    QCursor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QHeaderView,
    QModelIndex,
    QPalette,
    QSortFilterProxyModel,
    QStandardItemModel,
    Qt,
    QTreeView,
    QWidget,
    pyqtSignal,
)
from oncutf.core.theme_manager import get_theme_manager
from oncutf.ui.mixins.metadata_cache_mixin import MetadataCacheMixin
from oncutf.ui.mixins.metadata_context_menu_mixin import MetadataContextMenuMixin
from oncutf.ui.mixins.metadata_edit_mixin import MetadataEditMixin
from oncutf.ui.mixins.metadata_scroll_mixin import MetadataScrollMixin
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.metadata_cache_helper import MetadataCacheHelper
from oncutf.utils.path_utils import find_parent_with_attribute, paths_equal
from oncutf.utils.placeholder_helper import create_placeholder_helper
from oncutf.utils.timer_manager import schedule_drag_cleanup, schedule_scroll_adjust

# ApplicationContext integration
try:
    from oncutf.core.application_context import get_app_context
except ImportError:
    get_app_context = None

# Command system integration
try:
    from oncutf.core.metadata_command_manager import get_metadata_command_manager
    from oncutf.core.metadata_commands import EditMetadataFieldCommand, ResetMetadataFieldCommand
except ImportError:
    get_metadata_command_manager = None
    EditMetadataFieldCommand = None
    ResetMetadataFieldCommand = None

# Unified metadata manager integration
try:
    from oncutf.core.unified_metadata_manager import UnifiedMetadataManager
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


class MetadataTreeView(MetadataScrollMixin, MetadataCacheMixin, MetadataEditMixin, MetadataContextMenuMixin, QTreeView):
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
        from oncutf.core.pyqt_imports import QKeySequence, QShortcut

        # F5: Refresh metadata from current selection
        # F5 refresh shortcut for metadata tree
        self._refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        self._refresh_shortcut.activated.connect(self._on_refresh_shortcut)

        # Note: Global undo/redo (Ctrl+Z, Ctrl+Shift+Z, Ctrl+Y) are registered in MainWindow
        # Context menu still provides Undo/Redo actions for mouse-based access.
        logger.debug(
            "[MetadataTree] Local shortcuts setup: F5=refresh",
            extra={"dev_only": True}
        )

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
            logger.exception("[MetadataTreeView] Failed to initialize MetadataCacheHelper: %s", e)
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
            logger.exception("[MetadataTreeView] Failed to initialize UnifiedMetadataManager: %s", e)
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

                # Check for modifiers (Shift = Extended Metadata)
                modifiers = event.keyboardModifiers()
                use_extended = bool(modifiers & Qt.ShiftModifier)

                # Trigger metadata load via parent window -> application service
                parent_window = self._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "load_metadata_for_items"):
                    # We need to convert file paths to FileItems or let the service handle paths
                    # The service expects FileItems. We need to find them in the model.
                    if hasattr(parent_window, "file_model"):
                        file_items = []
                        for file_path in files:
                            # Find item in model by path
                            for item in parent_window.file_model.files:
                                if item.path == file_path:
                                    file_items.append(item)
                                    break

                        if file_items:
                            # Ensure files are checked (selected) after drag & drop
                            for item in file_items:
                                if not item.checked:
                                    item.checked = True

                            # Update file table model to reflect changes
                            if hasattr(parent_window, "file_table_model"):
                                parent_window.file_table_model.layoutChanged.emit()

                            parent_window.load_metadata_for_items(
                                file_items,
                                use_extended=use_extended,
                                source="drag_drop"
                            )

                logger.debug(
                    "[MetadataTreeView] Drop processed: %d files (extended=%s)",
                    len(files),
                    use_extended,
                    extra={"dev_only": True},
                )

                # Don't call _perform_drag_cleanup for successful drops
                # The wait_cursor will be managed by application_service
                # Just update viewport
                self.viewport().update()
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

    # _apply_scroll_position_immediately (implemented in mixin)

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
            "[MetadataTree] Header visibility: %s (placeholder_mode: %s)",
            "hidden" if self._is_placeholder_mode else "visible",
            self._is_placeholder_mode,
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
    # Helper methods for scroll position and file state (see mixin):
    # set_current_file_path, _save_current_file_state,
    # _load_file_state, _save_current_scroll_position,
    # _restore_scroll_position_for_current_file, _smooth_scroll_to_position,
    # clear_scroll_memory, restore_scroll_after_expand

    # =====================================
    # Context Menu & Actions
    # =====================================

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
            logger.debug("[MetadataTree] Method 1 failed: %s", e, extra={"dev_only": True})

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
                logger.debug("[MetadataTree] Method 2 failed: %s", e, extra={"dev_only": True})

        return selected_files



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
                    "[MetadataTree] Cannot edit %s for %s - metadata not loaded",
                    key_path,
                    file_item.filename,
                )
                from oncutf.core.pyqt_imports import QMessageBox

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
                "[MetadataTree] setSourceModel (placeholder) stack:\n%s",
                "".join(traceback.format_stack(limit=8)),
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
                "[MetadataTree] Displayed metadata for context: %s",
                context,
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.exception("[MetadataTree] Error displaying metadata: %s", e)
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
                "[MetadataTree] Updated search suggestions: %d items",
                len(suggestions),
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.exception("[MetadataTree] Error updating search suggestions: %s", e)

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
            "[MetadataTree] Emitting rebuild_requested signal (context=%s)",
            context,
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
            "[MetadataTree] Processing queued rebuild request (context=%s)",
            context,
            extra={"dev_only": True},
        )

        # Check if a rebuild is already in progress
        if self._rebuild_in_progress:
            logger.debug(
                "[MetadataTree] Rebuild already in progress, deferring request (context=%s)",
                context,
                extra={"dev_only": True},
            )
            # Store the pending request to process after current rebuild finishes
            self._pending_rebuild_request = (metadata, context)
            return

        if not isinstance(metadata, dict):
            logger.error(
                "[render_metadata_view] Called with invalid metadata: %s -> %s",
                type(metadata),
                metadata,
            )
            self.clear_view()
            return

        try:
            # Import here to avoid circular imports
            from oncutf.utils.build_metadata_tree_model import build_metadata_tree_model

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
            from oncutf.core.metadata_staging_manager import get_metadata_staging_manager
            staging_manager = get_metadata_staging_manager()
            if staging_manager and self._current_file_path:
                staged_changes = staging_manager.get_staged_changes(self._current_file_path)
                modified_keys = set(staged_changes.keys())

            # Set rebuild lock BEFORE model operations
            self._rebuild_in_progress = True
            logger.debug(
                "[MetadataTree] Rebuild lock acquired (context=%s)",
                context,
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
                    "[MetadataTree] Disconnecting view before model swap for file '%s'",
                    filename,
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
                    "[MetadataTree] Setting source model on metadata_proxy_model for file '%s'",
                    filename,
                    extra={"dev_only": True},
                )
                logger.debug(
                    "[MetadataTree] setSourceModel stack:\n%s",
                    "".join(traceback.format_stack(limit=8)),
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
                    "[MetadataTree] Proxy disabled/unavailable - setting model directly for file '%s'",
                    filename,
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
            logger.exception("[render_metadata_view] Unexpected error while rendering: %s", e)
            self.clear_view()
        finally:
            # ALWAYS release rebuild lock, even on error
            self._rebuild_in_progress = False
            logger.debug(
                "[MetadataTree] Rebuild lock released (context=%s)",
                context,
                extra={"dev_only": True},
            )

            # Process any pending rebuild request
            if self._pending_rebuild_request:
                pending_metadata, pending_context = self._pending_rebuild_request
                self._pending_rebuild_request = None
                logger.debug(
                    "[MetadataTree] Emitting deferred rebuild signal (context=%s)",
                    pending_context,
                    extra={"dev_only": True},
                )
                # Emit signal - it will be queued automatically via QueuedConnection
                self.rebuild_requested.emit(pending_metadata, pending_context)

    def _update_information_label(self, display_data: dict[str, Any]) -> None:
        """Update the information label with metadata statistics."""
        try:
            from oncutf.config import METADATA_ICON_COLORS

            # Get parent window and information label
            parent_window = self._get_parent_with_file_table()
            if not parent_window or not hasattr(parent_window, "information_label"):
                return

            # Get staging manager for modified count
            from oncutf.core.metadata_staging_manager import get_metadata_staging_manager
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
            logger.debug("Error updating information label: %s", e, extra={"dev_only": True})

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
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager
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
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager
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
                        "[MetadataTree] Set current file from metadata: %s",
                        full_path,
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
                            "[MetadataTree] Set current file from %s: %s",
                            field,
                            potential_path,
                            extra={"dev_only": True},
                        )
                        return

        except Exception as e:
            logger.debug("Error determining current file: %s", e, extra={"dev_only": True})

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
                        "[MetadataTree] Updated from parent selection: %s",
                        file_item.filename,
                        extra={"dev_only": True},
                    )
                else:
                    self.show_empty_state("No metadata available")
            else:
                # Multiple files selected
                self.show_empty_state(f"{len(selection)} files selected")
                logger.debug(
                    "[MetadataTree] Multiple files selected: %d",
                    len(selection),
                    extra={"dev_only": True},
                )

        except Exception as e:
            logger.exception("[MetadataTree] Error updating from parent selection: %s", e)
            self.show_empty_state("Error loading metadata")

    def refresh_metadata_from_selection(self) -> None:
        """
        Convenience method that triggers metadata update from parent selection.
        Can be called from parent window when selection changes.
        """
        logger.debug("[MetadataTree] Refreshing metadata from selection", extra={"dev_only": True})
        self.update_from_parent_selection()

    def _on_refresh_shortcut(self) -> None:
        """
        Handle F5 shortcut press - refresh metadata with status message.
        """
        from oncutf.utils.cursor_helper import wait_cursor

        logger.info("[MetadataTree] F5 pressed - refreshing metadata")

        with wait_cursor():
            self.refresh_metadata_from_selection()

            # Show status message if parent window has status manager
            if hasattr(self, "parent") and callable(self.parent):
                parent = self.parent()
                if parent and hasattr(parent, "status_manager"):
                    parent.status_manager.set_file_operation_status(
                        "Metadata tree refreshed", success=True, auto_reset=True
                    )

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
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager
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
            from oncutf.utils.path_normalizer import normalize_path

            normalized_path = normalize_path(file_item.full_path)

            # Check if we have stale modifications
            if self._path_in_dict(normalized_path, self.modified_items_per_file):
                logger.debug(
                    "[MetadataTree] Clearing stale modifications for %s on metadata display",
                    file_item.filename,
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
                "[MetadataTree] smart_display_metadata_or_empty_state called: metadata=%s, selected_count=%d, context=%s",
                bool(metadata),
                selected_count,
                context,
                extra={"dev_only": True},
            )

            if metadata and self.should_display_metadata_for_selection(selected_count):
                logger.debug(
                    "[MetadataTree] Displaying metadata for %d selected file(s)",
                    selected_count,
                    extra={"dev_only": True},
                )
                self.display_metadata(metadata, context)
                logger.debug(
                    "[MetadataTree] Smart display: showing metadata (context: %s)",
                    context,
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
                    "[MetadataTree] Smart display: showing empty state (selected: %d)",
                    selected_count,
                    extra={"dev_only": True},
                )

        except Exception as e:
            logger.exception("[MetadataTree] Error in smart display: %s", e)
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
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager
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
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return {}

        return staging_manager.get_all_staged_changes()

    def clear_modifications(self) -> None:
        """
        Clear all modified metadata items for the current file.
        """
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager
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
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager
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
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager
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
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager
        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return False

        return staging_manager.has_any_staged_changes()

    # =====================================
    # Lazy Loading Methods
    # =====================================
    # =====================================
    # Lazy Loading Methods
    # =====================================

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
                "[MetadataTreeView] Set current file from metadata field '%s': %s",
                field,
                value,
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
                    "[MetadataTreeView] Set current file from constructed path: %s",
                    full_path,
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
                        "[MetadataTreeView] Set current file from metadata field '%s': %s",
                        field,
                        potential_path,
                    )
                    return
