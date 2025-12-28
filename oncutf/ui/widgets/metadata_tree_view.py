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

import os
import traceback
from typing import Any

from oncutf.config import METADATA_TREE_USE_PROXY
from oncutf.core.pyqt_imports import (
    QAbstractItemView,
    QCursor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QModelIndex,
    QSortFilterProxyModel,
    QStandardItemModel,
    Qt,
    QTreeView,
    QWidget,
    pyqtSignal,
)
from oncutf.ui.behaviors.metadata_scroll_behavior import MetadataScrollBehavior
from oncutf.ui.mixins.metadata_cache_mixin import MetadataCacheMixin
from oncutf.ui.mixins.metadata_context_menu_mixin import MetadataContextMenuMixin
from oncutf.ui.mixins.metadata_edit_mixin import MetadataEditMixin
from oncutf.ui.widgets.metadata_tree.cache_handler import MetadataTreeCacheHandler
from oncutf.ui.widgets.metadata_tree.drag_handler import MetadataTreeDragHandler
from oncutf.ui.widgets.metadata_tree.modifications_handler import MetadataTreeModificationsHandler
from oncutf.ui.widgets.metadata_tree.search_handler import MetadataTreeSearchHandler
from oncutf.ui.widgets.metadata_tree.selection_handler import MetadataTreeSelectionHandler
from oncutf.ui.widgets.metadata_tree.view_config import MetadataTreeViewConfig
from oncutf.utils.filesystem.path_utils import find_parent_with_attribute, paths_equal
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.metadata.cache_helper import MetadataCacheHelper
from oncutf.utils.shared.timer_manager import schedule_scroll_adjust
from oncutf.utils.ui.placeholder_helper import create_placeholder_helper

# ApplicationContext integration
try:
    from oncutf.core.application_context import get_app_context
except ImportError:
    get_app_context = None

# Command system integration
try:
    from oncutf.core.metadata import get_metadata_command_manager
    from oncutf.core.metadata.commands import EditMetadataFieldCommand, ResetMetadataFieldCommand
except ImportError:
    get_metadata_command_manager = None
    EditMetadataFieldCommand = None
    ResetMetadataFieldCommand = None

# Unified metadata manager integration
try:
    from oncutf.core.metadata import UnifiedMetadataManager
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


class MetadataTreeView(
    MetadataCacheMixin, MetadataEditMixin, MetadataContextMenuMixin, QTreeView
):
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
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        self.rebuild_requested.connect(self._render_metadata_view_impl, Qt.QueuedConnection)
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
        logger.debug("[MetadataTree] Local shortcuts setup: F5=refresh", extra={"dev_only": True})

    def _lazy_init_controller(self) -> None:
        """Lazy initialization of controller layer."""
        try:
            from oncutf.core.metadata import get_metadata_staging_manager
            from oncutf.ui.widgets.metadata_tree.controller import create_metadata_tree_controller

            staging_manager = get_metadata_staging_manager()
            self._controller = create_metadata_tree_controller(staging_manager=staging_manager)

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
        """Initialize the metadata cache helper. Delegates to cache handler."""
        self._cache_handler.initialize_cache_helper()

    def _get_cache_helper(self) -> MetadataCacheHelper | None:
        """Get the MetadataCacheHelper instance, initializing if needed. Delegates to cache handler."""
        return self._cache_handler.get_cache_helper()

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
        from oncutf.core.theme_manager import get_theme_manager
        from oncutf.ui.delegates.ui_delegates import MetadataTreeItemDelegate

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
        if hasattr(self, "placeholder_helper"):
            self.placeholder_helper.update_position()

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
        """Override the setModel method to set minimum column widths after the model is set.
        """
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

    # =====================================
    # Scroll Position Memory (delegated to MetadataScrollBehavior)
    # =====================================

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

    def _update_metadata_in_cache(self, key_path: str, new_value: str) -> None:
        """Update the metadata value in the cache to persist changes.
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
        """Override scrollTo to prevent automatic scrolling when selections change.
        Scroll position is managed manually via the scroll position memory system.
        This prevents the table from moving when selecting cells from column 1.
        """
        if self._is_placeholder_mode:
            # In placeholder mode, use normal scrolling
            super().scrollTo(index, hint)  # type: ignore[arg-type]
            return

        # In normal mode, do nothing - scroll position is managed manually
        # This prevents Qt from automatically scrolling when selections change
        return

    def focusOutEvent(self, event):
        """Handle focus loss events."""
        super().focusOutEvent(event)

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
        """Shows empty state using unified placeholder helper.
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
        """Clears the metadata tree view and shows a placeholder message.
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
        logger.debug(
            "[MetadataTree] Emitting rebuild_requested signal (context=%s)",
            context,
            extra={"dev_only": True},
        )
        self.rebuild_requested.emit(metadata, context)

    def _render_metadata_view_impl(self, metadata: dict[str, Any], context: str = "") -> None:
        """Actually builds the metadata tree and displays it.
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
            # Try to determine file path for scroll position memory
            self._set_current_file_from_metadata(metadata)

            # Use controller for building tree model
            # All business logic (display data prep, extended key detection)
            # is handled by the service layer
            if self._controller is None:
                self._lazy_init_controller()

            # Prepare minimal display state - service handles all the logic
            from oncutf.ui.widgets.metadata_tree.model import MetadataDisplayState

            display_state = MetadataDisplayState(file_path=self._current_file_path)

            # Pass __extended__ flag to display state for service to handle
            if metadata.get("__extended__"):
                display_state.is_extended_metadata = True

            # Set rebuild lock BEFORE model operations
            self._rebuild_in_progress = True
            logger.debug(
                "[MetadataTree] Rebuild lock acquired (context=%s)",
                context,
                extra={"dev_only": True},
            )

            # Build tree model using controller - delegates ALL logic to service
            tree_model = self._controller.build_qt_model(metadata, display_state)

            # Store display_data for later use (from metadata directly)
            self._current_display_data = dict(metadata)

            # Get filename for logging
            filename = metadata.get("FileName", "unknown")

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
                if delegate and hasattr(delegate, "hovered_index"):
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
                if delegate and hasattr(delegate, "hovered_index"):
                    delegate.hovered_index = None
                self.setModel(None)
                self.setModel(tree_model)
                self._current_tree_model = tree_model

            # Always expand all - no collapse functionality
            self.expandAll()

            # Update header visibility for content mode
            self._update_header_visibility()

            # Update information label with metadata count
            self._update_information_label(self._current_display_data)

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
            from oncutf.core.metadata import get_metadata_staging_manager

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
        """Update metadata display based on parent selection. Delegates to selection handler."""
        self._selection_handler.update_from_parent_selection()

    def refresh_metadata_from_selection(self) -> None:
        """Convenience method that triggers metadata update from parent selection.
        Can be called from parent window when selection changes. Delegates to selection handler.
        """
        self._selection_handler.refresh_metadata_from_selection()

    def _on_refresh_shortcut(self) -> None:
        """Handle F5 shortcut press - refresh metadata with status message.
        """
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
        self.clear_scroll_memory()

        # Clear all staged changes
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()
        if staging_manager:
            staging_manager.clear_all()

        self.clear_view()
        # Update header visibility for placeholder mode
        self._update_header_visibility()
        # Disable search field when changing folders
        self._update_search_field_state(False)

    def display_file_metadata(self, file_item: Any, context: str = "file_display") -> None:
        """Display metadata for a specific file item.
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
            from oncutf.utils.filesystem.path_normalizer import normalize_path

            normalized_path = normalize_path(file_item.full_path)

            # Check if we have stale modifications
            if self._scroll_behavior._path_in_dict(normalized_path, self.modified_items_per_file):
                logger.debug(
                    "[MetadataTree] Clearing stale modifications for %s on metadata display",
                    file_item.filename,
                    extra={"dev_only": True},
                )
                self._scroll_behavior._remove_from_path_dict(normalized_path, self.modified_items_per_file)
                # Also clear current modifications if this is the current file
                if paths_equal(normalized_path, self._current_file_path):
                    self.modified_items.clear()

            self.display_metadata(display_metadata, context=context)
        else:
            self.clear_view()

        # Update header visibility after file metadata display
        self._update_header_visibility()

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
        if get_app_context is None:
            return None
        try:
            return get_app_context()
        except RuntimeError:
            # ApplicationContext not ready yet
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
