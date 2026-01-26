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

from typing import Any

from PyQt5.QtCore import (
    QModelIndex,
    QPoint,
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QStandardItemModel
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QTreeView,
    QWidget,
)

from oncutf.config import METADATA_TREE_USE_PROXY
from oncutf.ui.behaviors.metadata_cache_behavior import MetadataCacheBehavior
from oncutf.ui.behaviors.metadata_context_menu import MetadataContextMenuBehavior
from oncutf.ui.behaviors.metadata_edit import MetadataEditBehavior
from oncutf.ui.behaviors.metadata_scroll_behavior import MetadataScrollBehavior
from oncutf.ui.widgets.metadata_tree.cache_handler import MetadataTreeCacheHandler
from oncutf.ui.widgets.metadata_tree.drag_handler import MetadataTreeDragHandler
from oncutf.ui.widgets.metadata_tree.event_handler import MetadataTreeEventHandler
from oncutf.ui.widgets.metadata_tree.modifications_handler import MetadataTreeModificationsHandler
from oncutf.ui.widgets.metadata_tree.render_handler import TreeRenderHandler
from oncutf.ui.widgets.metadata_tree.search_handler import MetadataTreeSearchHandler
from oncutf.ui.widgets.metadata_tree.selection_handler import MetadataTreeSelectionHandler
from oncutf.ui.widgets.metadata_tree.ui_state_handler import TreeUiStateHandler
from oncutf.ui.widgets.metadata_tree.view_config import MetadataTreeViewConfig
from oncutf.utils.filesystem.path_utils import find_parent_with_attribute
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_scroll_adjust
from oncutf.utils.ui.placeholder_helper import create_placeholder_helper
from oncutf.utils.ui.tooltip_helper import TreeViewTooltipFilter

# Metadata service integration (command system + unified manager)
try:
    from oncutf.app.services import get_metadata_command_manager, get_metadata_service
except ImportError:
    get_metadata_command_manager = None
    get_metadata_service = None

logger = get_cached_logger(__name__)


class MetadataProxyModel(QSortFilterProxyModel):
    """Custom proxy model for metadata tree filtering."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the proxy model with case-insensitive recursive filtering."""
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setRecursiveFilteringEnabled(True)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Custom filter logic for metadata tree.

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
    """Custom tree view that accepts file drag & drop to trigger metadata loading.
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

    def __init__(self, parent: QWidget | None = None, controller=None) -> None:
        """Initialize the metadata tree view with drag-drop support and controller."""
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)

        # Controller for layered architecture
        self._controller = controller
        if self._controller is None:
            # Lazy initialization - create controller on first use
            self._lazy_init_controller()

        # Drag handler for drag & drop operations
        self._drag_handler = MetadataTreeDragHandler(self)

        # View configuration handler
        self._view_config = MetadataTreeViewConfig(self)

        # Search handler
        self._search_handler = MetadataTreeSearchHandler(self)

        # Selection handler
        self._selection_handler = MetadataTreeSelectionHandler(self)

        # Modifications handler
        self._modifications_handler = MetadataTreeModificationsHandler(self)

        # Cache handler
        self._cache_handler = MetadataTreeCacheHandler(self)

        # Render handler for tree model building
        self._render_handler = TreeRenderHandler(self)

        # UI state handler for display orchestration
        self._ui_state_handler = TreeUiStateHandler(self)

        # Event handler for Qt events
        self._event_handler = MetadataTreeEventHandler(self)

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
        # (Note: also tracked in scroll behavior for scroll position management)

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

        # Scroll position behavior (replaces MetadataScrollMixin)
        self._scroll_behavior = MetadataScrollBehavior(self)

        # Cache interaction behavior (replaces MetadataCacheMixin)
        self._cache_behavior = MetadataCacheBehavior(self)

        # Context menu behavior (replaces MetadataContextMenuMixin)
        self._context_menu_behavior = MetadataContextMenuBehavior(self)

        # Edit behavior (replaces MetadataEditMixin)
        self._edit_behavior = MetadataEditBehavior(self)

        # Unified placeholder helper (replaces old QLabel/QPixmap approach)
        self.placeholder_helper = create_placeholder_helper(self, "metadata_tree", icon_size=120)

        # Setup standard view properties
        self._setup_tree_view_properties()

        # Note: using default delegate and QSS for tree row rendering

        # Setup icon delegate for selected state icon changes

        # Timer for update debouncing
        self._update_timer_id = None

        # Initialize direct metadata loader
        self._direct_loader = None
        self._initialize_direct_loader()

        # Connect rebuild signal with QueuedConnection for thread-safe model operations
        # This ensures all rebuilds go through Qt event queue and execute in main thread
        self.rebuild_requested.connect(self._render_metadata_view_impl, Qt.QueuedConnection)
        logger.debug(
            "[MetadataTree] QueuedConnection established for rebuild_requested signal",
            extra={"dev_only": True},
        )

        # Setup local keyboard shortcuts for undo/redo
        self._setup_shortcuts()

        # Install custom tooltip handler to use themed tooltips
        self._tooltip_filter = TreeViewTooltipFilter(self, parent=self)
        self.viewport().installEventFilter(self._tooltip_filter)

    def _setup_shortcuts(self) -> None:
        """Setup local keyboard shortcuts for metadata tree."""
        return self._event_handler.setup_shortcuts()

    def keyPressEvent(self, event):
        """Handle keyboard events for F5 refresh."""
        handled = self._event_handler.handle_key_press(event)
        if not handled:
            super().keyPressEvent(event)

    def _lazy_init_controller(self) -> None:
        """Lazy initialization of controller layer."""
        try:
            from oncutf.app.services import get_metadata_service
            from oncutf.ui.widgets.metadata_tree.controller import create_metadata_tree_controller

            metadata_service = get_metadata_service()
            self._controller = create_metadata_tree_controller(
                staging_manager=metadata_service.staging_manager
            )

            logger.debug(
                "[MetadataTree] Controller initialized (layered architecture)",
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.exception("[MetadataTree] Failed to initialize controller: %s", e)
            self._controller = None

    def wheelEvent(self, event) -> None:
        """Update hover state after scroll to track cursor position smoothly."""
        super().wheelEvent(event)
        return self._event_handler.handle_wheel_event(event)

    def _initialize_direct_loader(self) -> None:
        """Initialize the direct metadata loader. Delegates to cache handler."""
        self._cache_handler.initialize_direct_loader()

    def _get_direct_loader(self):
        """Get the UnifiedMetadataManager instance, initializing if needed. Delegates to cache handler."""
        return self._cache_handler.get_direct_loader()

    def _setup_tree_view_properties(self) -> None:
        """Configure standard tree view properties. Delegates to view config handler."""
        self._view_config.setup_tree_view_properties()

        # Install custom delegate for full-row hover and consistent painting
        from oncutf.ui.delegates.ui_delegates import MetadataTreeItemDelegate
        from oncutf.ui.theme_manager import get_theme_manager

        theme = get_theme_manager()
        delegate = MetadataTreeItemDelegate(self, theme=theme)
        delegate.install_event_filter(self)
        self.setItemDelegate(delegate)

        # Apply tree view QSS for consistent hover/selection colors
        self._apply_tree_styling(theme)

    def _apply_tree_styling(self, theme) -> None:
        """Apply consistent hover/selection styling to match file table."""
        text = theme.get_color("text")
        hover_bg = theme.get_color("table_hover_bg")
        selected_bg = theme.get_color("selected")
        selected_text = theme.get_color("selected_text")
        selected_hover_bg = theme.get_color("selected_hover")
        bg_alternate = theme.get_color("background_alternate")

        self.setStyleSheet(f"""
            QTreeView::item:hover:!selected {{
                background-color: {hover_bg};
            }}
            QTreeView::item:selected:!hover {{
                background-color: {selected_bg};
                color: {text};
            }}
            QTreeView::item:selected:hover {{
                background-color: {selected_hover_bg};
                color: {selected_text};
            }}
            QTreeView {{
                alternate-background-color: {bg_alternate};
            }}
        """)

    def _setup_icon_delegate(self) -> None:
        """Setup the icon delegate for selection-based icon changes."""
        # Icon delegate functionality removed for simplicity

    # =====================================
    # Path-Safe Dictionary Operations
    # =====================================

    def resizeEvent(self, event):
        """Handle resize events to adjust placeholder label size."""
        super().resizeEvent(event)
        return self._event_handler.handle_resize(event)

    # =====================================
    # Drag & Drop Methods
    # =====================================

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag only if it comes from our application's file table.
        Delegates to drag handler.
        """
        self._drag_handler.handle_drag_enter(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Continue accepting drag move events only for items from our file table.
        Delegates to drag handler.
        """
        self._drag_handler.handle_drag_move(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop events for file loading.
        Delegates to drag handler.
        """
        self._drag_handler.handle_drop(event)

    # =====================================
    # Model & Column Management
    # =====================================

    def setModel(self, model: Any) -> None:
        """Override the setModel method to set minimum column widths after the model is set."""
        # Cancel any pending restore operation (delegated to scroll behavior)
        if self._scroll_behavior._pending_restore_timer_id is not None:
            self._scroll_behavior._pending_restore_timer_id = None

        # First call the parent implementation
        super().setModel(model)

        # Then set column sizes if we have a header and model
        if model and self.header():
            is_placeholder = self._view_config.detect_placeholder_mode(model)
            self._is_placeholder_mode = is_placeholder
            self._scroll_behavior.set_placeholder_mode(is_placeholder)

            if is_placeholder:
                self._view_config.configure_placeholder_mode(model)
                self._scroll_behavior._current_file_path = None  # No file selected
            else:
                self._view_config.configure_normal_mode()

                # For non-placeholder mode, immediately restore scroll position
                # This prevents the "jump to 0 then scroll to final position" effect
                if (
                    self._scroll_behavior._current_file_path
                    and self._scroll_behavior._current_file_path
                    in self._scroll_behavior._scroll_positions
                ):
                    # Get the saved position
                    saved_position = self._scroll_behavior._scroll_positions[
                        self._scroll_behavior._current_file_path
                    ]

                    # Schedule scroll position restoration
                    schedule_scroll_adjust(
                        lambda: self._scroll_behavior._apply_scroll_position_immediately(
                            saved_position
                        ),
                        0,
                    )

            # Update header visibility after mode configuration
            self._view_config.update_header_visibility()

    # _apply_scroll_position_immediately (implemented in mixin)

    def _detect_placeholder_mode(self, model: Any) -> bool:
        """Detect if the model contains placeholder content. Delegates to view config."""
        return self._view_config.detect_placeholder_mode(model)

    def _configure_placeholder_mode(self, _model: Any) -> None:
        """Configure view for placeholder mode. Delegates to view config handler."""
        self._view_config.configure_placeholder_mode(_model)

    def _configure_normal_mode(self) -> None:
        """Configure view for normal content mode. Delegates to view config handler."""
        self._view_config.configure_normal_mode()

    def _update_header_visibility(self) -> None:
        """Update header visibility. Delegates to view config handler."""
        self._view_config.update_header_visibility()

    def _connect_column_resize_signals(self) -> None:
        """Connect column resize signals. Delegates to view config handler."""
        # This is called internally by _configure_normal_mode, so it's in the handler

    def _on_column_resized(self, _logical_index: int, _old_size: int, _new_size: int) -> None:
        """Handle column resize events. Delegates to view config handler."""
        self._view_config._on_column_resized(_logical_index, _old_size, _new_size)

    def _update_scrollbar_policy_intelligently(self, target_policy: int) -> None:
        """Update scrollbar policy. Delegates to view config handler."""
        self._view_config._update_scrollbar_policy_intelligently(target_policy)

    def _make_placeholder_items_non_selectable(self, model: Any) -> None:
        """Make placeholder items non-selectable. Delegates to view config handler."""
        MetadataTreeViewConfig.make_placeholder_items_non_selectable(model)

    def _force_style_update(self) -> None:
        """Force Qt style system to update. Delegates to view config handler."""
        self._view_config._force_style_update()

    # =========================================================================
    # Handler Properties - Direct Access to Internal Handlers
    # =========================================================================
    # These properties provide clean access to internal handlers for advanced use.
    # Prefer using public methods, but these are available for cases where
    # direct handler access is needed.

    @property
    def scroll(self) -> MetadataScrollBehavior:
        """Access scroll position behavior handler."""
        return self._scroll_behavior

    @property
    def cache(self) -> MetadataCacheBehavior:
        """Access cache behavior handler."""
        return self._cache_behavior

    @property
    def edit_handler(self) -> MetadataEditBehavior:
        """Access edit behavior handler."""
        return self._edit_behavior

    @property
    def context_menu(self) -> MetadataContextMenuBehavior:
        """Access context menu behavior handler."""
        return self._context_menu_behavior

    @property
    def render(self) -> TreeRenderHandler:
        """Access tree render handler."""
        return self._render_handler

    @property
    def ui_state(self) -> TreeUiStateHandler:
        """Access UI state handler."""
        return self._ui_state_handler

    @property
    def search(self) -> MetadataTreeSearchHandler:
        """Access search handler."""
        return self._search_handler

    @property
    def selection(self) -> MetadataTreeSelectionHandler:
        """Access selection handler."""
        return self._selection_handler

    @property
    def modifications(self) -> MetadataTreeModificationsHandler:
        """Access modifications handler."""
        return self._modifications_handler

    # =====================================
    # Scroll Position Memory (delegated to MetadataScrollBehavior)
    # =====================================

    @property
    def _current_file_path(self) -> str | None:
        """Get current file path from scroll behavior."""
        return self._scroll_behavior._current_file_path

    @_current_file_path.setter
    def _current_file_path(self, value: str | None) -> None:
        """Set current file path via scroll behavior."""
        if value:
            self._scroll_behavior.set_current_file_path(value)
        else:
            self._scroll_behavior._current_file_path = None

    def set_current_file_path(self, file_path: str) -> None:
        """Set the current file path and manage scroll position restoration."""
        self._scroll_behavior.set_current_file_path(file_path)

    def clear_scroll_memory(self) -> None:
        """Clear all saved scroll positions (useful when changing folders)."""
        self._scroll_behavior.clear_scroll_memory()

    def restore_scroll_after_expand(self) -> None:
        """Trigger scroll position restore after expandAll() has completed."""
        self._scroll_behavior.restore_scroll_after_expand()

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
        """Get current selection via parent traversal. Delegates to selection handler."""
        return self._selection_handler.get_current_selection()

    # =====================================
    # Context Menu Methods (delegate to behavior)
    # =====================================

    # Keep public alias for backward compatibility
    def show_context_menu(self, position: QPoint) -> None:
        """Show context menu at position (public API).
        Delegates to context menu behavior.

        Args:
            position: Position where the context menu should appear

        """
        self._context_menu_behavior.show_context_menu(position)

    # =====================================
    # Tree Item Value Update
    # =====================================

    def _update_tree_item_value(self, key_path: str, new_value: str) -> None:
        """Update tree by refreshing the entire view with updated metadata.

        Args:
            key_path: Metadata key path (can be grouped like "File Info (12 fields)/Rotation")
            new_value: New value to display

        """
        # Instead of trying to update individual items, refresh the whole tree
        # This ensures consistent state and proper styling
        logger.info(
            "[MetadataTree] _update_tree_item_value called: key_path=%s, new_value=%s, current_file=%s",
            key_path,
            new_value,
            self._current_file_path,
        )

        if not self._current_file_path:
            logger.warning("[MetadataTree] No current file path, skipping tree refresh")
            return

        # Get current file's metadata from the persistent cache (preferred).
        # Note: UnifiedMetadataManager facade does not expose a get_cache() API.
        parent_window = self._get_parent_with_file_table()
        cache_entry = None
        if parent_window is not None and hasattr(parent_window, "metadata_cache"):
            try:
                cache_entry = parent_window.metadata_cache.get_entry(self._current_file_path)
                logger.info(
                    "[MetadataTree] Got cache entry: %s",
                    "has data"
                    if (cache_entry and hasattr(cache_entry, "data") and cache_entry.data)
                    else "no data",
                )
            except Exception as e:
                logger.warning(
                    "[MetadataTree] Failed to read metadata_cache entry: %s",
                    e,
                )

        # Fallback: reuse the last displayed metadata snapshot.
        display_data = None
        if cache_entry is not None and hasattr(cache_entry, "data") and cache_entry.data:
            display_data = cache_entry.data
            logger.info("[MetadataTree] Using cache_entry.data for refresh")
        elif hasattr(self, "_current_display_data") and self._current_display_data:
            display_data = dict(self._current_display_data)
            logger.info("[MetadataTree] Using _current_display_data fallback for refresh")

        if not display_data:
            logger.warning(
                "[MetadataTree] No metadata available for refresh: %s",
                self._current_file_path,
            )
            return

        # Refresh the tree with current metadata (service will apply staged changes).
        logger.info("[MetadataTree] Calling display_metadata with context='after_edit'")
        self.display_metadata(display_data, context="after_edit")

        logger.debug(
            "[MetadataTree] Refreshed tree after edit: %s = %s",
            key_path,
            new_value,
            extra={"dev_only": True},
        )

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
        """Override scrollTo to prevent automatic scrolling when selections change.
        Scroll position is managed manually via the scroll position memory system.
        This prevents the table from moving when selecting cells from column 1.
        """
        if self._is_placeholder_mode:
            # In placeholder mode, use normal scrolling
            super().scrollTo(index, hint)
            return

        # In normal mode, do nothing - scroll position is managed manually
        # This prevents Qt from automatically scrolling when selections change
        return

    def focusOutEvent(self, event):
        """Handle focus loss events."""
        super().focusOutEvent(event)
        return self._event_handler.handle_focus_out(event)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        handled = self._event_handler.handle_mouse_press(event)
        if not handled:
            super().mousePressEvent(event)

    # =====================================
    # Metadata Display Management Methods
    # =====================================

    def show_empty_state(self, _message: str = "No file selected") -> None:
        """Shows empty state using unified placeholder helper.
        No longer creates text model - uses only the placeholder helper.
        """
        return self._ui_state_handler.display_placeholder(_message)

    def clear_view(self) -> None:
        """Clears the metadata tree view and shows a placeholder message.
        Does not clear scroll position memory when just showing placeholder.
        """
        return self._ui_state_handler.clear_tree()

    def display_metadata(self, metadata: dict[str, Any] | None, context: str = "") -> None:
        """Display metadata in the tree view."""
        return self._ui_state_handler.display_metadata(metadata, context)

    def _update_search_field_state(self, enabled: bool):
        """Update the metadata search field enabled state. Delegates to search handler."""
        self._search_handler.update_search_field_state(enabled)

    def _clear_search_field(self):
        """Clear the metadata search field. Delegates to search handler."""
        self._search_handler.clear_search_field()

    def _update_search_suggestions(self):
        """Update search suggestions. Delegates to search handler."""
        self._search_handler.update_search_suggestions()

    def _collect_suggestions_from_tree_model(self, model, suggestions: set):
        """Collect suggestions from tree model. Delegates to search handler."""
        self._search_handler._collect_suggestions_from_tree_model(model, suggestions)

    def _collect_suggestions_from_metadata(self, metadata: dict, suggestions: set):
        """Collect suggestions from metadata. Delegates to search handler."""
        self._search_handler._collect_suggestions_from_metadata(metadata, suggestions)

    def _get_all_loaded_files(self):
        """Get all loaded files. Delegates to search handler."""
        return self._search_handler._get_all_loaded_files()

    def _render_metadata_view(self, metadata: dict[str, Any], context: str = "") -> None:
        """Public interface for metadata tree rebuild.
        Emits rebuild_requested signal which is processed via QueuedConnection.
        This ensures all model operations happen in the main thread via Qt event queue.
        """
        return self._render_handler.emit_rebuild_tree(metadata, context)

    def _render_metadata_view_impl(self, metadata: dict[str, Any], context: str = "") -> None:
        """Actually builds the metadata tree and displays it.
        Called via QueuedConnection from rebuild_requested signal.
        Assumes metadata is a non-empty dict.

        Includes fallback protection in case called with invalid metadata.
        Uses rebuild lock to prevent concurrent model swaps that cause segfaults.
        """
        return self._render_handler.rebuild_tree_from_metadata(metadata, context)

    def _update_information_label(self, display_data: dict[str, Any]) -> None:
        """Update the information label with metadata statistics."""
        return self._ui_state_handler.update_information_label(display_data)

    def _set_current_file_from_metadata(self, metadata: dict[str, Any]) -> None:
        """Set current file from metadata if available."""
        return self._ui_state_handler.set_current_file_from_metadata(metadata)

    # =====================================
    # Selection-based Metadata Management
    # =====================================

    def update_from_parent_selection(self) -> None:
        """Update metadata display based on parent selection. Delegates to selection handler."""
        self._selection_handler.update_from_parent_selection()

    def refresh_metadata_from_selection(self) -> None:
        """Convenience method that triggers metadata update from parent selection.
        Can be called from parent window when selection changes. Delegates to selection handler.
        """
        self._selection_handler.refresh_metadata_from_selection()

    def _on_refresh_shortcut(self) -> None:
        """Handle F5 shortcut press - refresh metadata with status message."""
        from oncutf.utils.ui.cursor_helper import wait_cursor

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
        """Performs initial setup that requires parent window to be available.
        Should be called after the tree view is added to its parent.
        """
        self.show_empty_state("No file selected")
        # Initialize search field as disabled
        self._update_search_field_state(False)

    # =====================================
    # Unified Metadata Management Interface
    # =====================================

    def clear_for_folder_change(self) -> None:
        """Clears both view and scroll memory when changing folders.
        This is different from clear_view() which preserves scroll memory.
        """
        return self._ui_state_handler.cleanup_on_folder_change()

    def display_file_metadata(self, file_item: Any, context: str = "file_display") -> None:
        """Display metadata for a specific file item.
        Handles metadata extraction from file_item or cache automatically.

        Args:
            file_item: FileItem object with metadata
            context: Context string for logging

        """
        return self._ui_state_handler.display_file_metadata(file_item, context)

    def handle_selection_change(self) -> None:
        """Handle selection changes from the parent file table.
        This is a convenience method that can be connected to selection signals.
        Delegates to selection handler.
        """
        self._selection_handler.handle_selection_change()

    def handle_invert_selection(self, metadata: dict[str, Any] | None) -> None:
        """Handle metadata display after selection inversion.
        Delegates to selection handler.

        Args:
            metadata: The metadata to display, or None to clear

        """
        self._selection_handler.handle_invert_selection(metadata)

    def handle_metadata_load_completion(self, metadata: dict[str, Any] | None, source: str) -> None:
        """Handle metadata display after a metadata loading operation completes.

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
        try:
            from oncutf.ui.adapters.application_context import get_app_context
            return get_app_context()
        except (ImportError, RuntimeError):
            # ApplicationContext not available or not ready yet
            return None

    def should_display_metadata_for_selection(self, selected_files_count: int) -> bool:
        """Central logic to determine if metadata should be displayed based on selection count.
        Delegates to selection handler.

        Args:
            selected_files_count: Number of currently selected files

        Returns:
            bool: True if metadata should be displayed, False if empty state should be shown

        """
        return self._selection_handler.should_display_metadata_for_selection(selected_files_count)

    def smart_display_metadata_or_empty_state(
        self, metadata: dict[str, Any] | None, selected_count: int, context: str = ""
    ) -> None:
        """Smart display logic for metadata or empty state. Delegates to selection handler."""
        self._selection_handler.smart_display_metadata_or_empty_state(
            metadata, selected_count, context
        )

    def get_modified_metadata(self) -> dict[str, str]:
        """Collect all modified metadata items for the current file.
        Delegates to selection handler.

        Returns:
            Dictionary of modified metadata in format {"EXIF/Rotation": "90"}

        """
        return self._selection_handler.get_modified_metadata()

    def get_all_modified_metadata_for_files(self) -> dict[str, dict[str, str]]:
        """Collect all modified metadata for all files that have modifications.
        Delegates to modifications handler.

        Returns:
            Dictionary mapping file paths to their modified metadata

        """
        return self._modifications_handler.get_all_modified_metadata_for_files()

    def clear_modifications(self) -> None:
        """Clear all modified metadata items for the current file.
        Delegates to modifications handler.
        """
        self._modifications_handler.clear_modifications()

    def clear_modifications_for_file(self, file_path: str) -> None:
        """Clear modifications for a specific file.
        Delegates to modifications handler.

        Args:
            file_path: Full path of the file to clear modifications for

        """
        self._modifications_handler.clear_modifications_for_file(file_path)

    def has_modifications_for_selected_files(self) -> bool:
        """Check if any of the currently selected files have modifications.
        Delegates to modifications handler.

        Returns:
            bool: True if any selected file has modifications

        """
        return self._modifications_handler.has_modifications_for_selected_files()

    def has_any_modifications(self) -> bool:
        """Check if there are any modifications in any file.
        Delegates to modifications handler.

        Returns:
            bool: True if any file has modifications

        """
        return self._modifications_handler.has_any_modifications()

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
        return self._ui_state_handler.sync_placeholder_state()

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
