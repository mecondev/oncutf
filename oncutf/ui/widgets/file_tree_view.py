"""Module: file_tree_view.py

Author: Michael Economou
Date: 2025-05-31

Filesystem tree view for folder navigation.

Features:
- Custom drag implementation (manual, not Qt built-in)
- Single item selection
- Filesystem monitoring for auto-refresh
- Drive mount/unmount detection
"""

import os

from oncutf.config import ALLOWED_EXTENSIONS
from oncutf.core.drag.drag_manager import DragManager
from oncutf.core.drag.drag_visual_manager import (
    DragVisualManager,
    end_drag_visual,
    start_drag_visual,
    update_drag_feedback_for_widget,
)
from oncutf.core.modifier_handler import decode_modifiers_to_flags
from oncutf.core.pyqt_imports import (
    QAbstractItemView,
    QApplication,
    QCursor,
    QEvent,
    QHeaderView,
    QKeyEvent,
    QModelIndex,
    QMouseEvent,
    Qt,
    QTreeView,
    pyqtSignal,
)
from oncutf.ui.delegates.ui_delegates import TreeViewItemDelegate
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_scroll_adjust
from oncutf.utils.ui.drag_zone_validator import DragZoneValidator

logger = get_cached_logger(__name__)


class FileTreeView(QTreeView):
    """Custom tree view with clean single-item drag & drop implementation.

    Features:
    - Manual drag control (no Qt built-in drag system)
    - Intelligent horizontal scrolling
    - Single item selection only (no multi-selection complexity)
    - 4 modifier combinations for drag behavior:
      * Normal: Replace + shallow
      * Ctrl: Replace + recursive
      * Shift: Merge + shallow
      * Ctrl+Shift: Merge + recursive
    - Automatic header configuration for optimal display
    """

    # Signals
    item_dropped = pyqtSignal(str, object)  # single path and keyboard modifiers
    folder_selected = pyqtSignal()  # Signal emitted when Return/Enter is pressed
    selection_changed = pyqtSignal(str)  # Signal emitted when selection changes (single path)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Enable drag so Qt can call startDrag, but we'll override it
        self.setDragEnabled(True)
        self.setAcceptDrops(True)  # We still need to accept drops
        self.setDragDropMode(QAbstractItemView.DragDrop)  # Enable both drag and drop

        # Configure scrollbars for optimal horizontal scrolling
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        # Configure text display for horizontal scrolling
        self.setTextElideMode(Qt.ElideNone)  # Show full content
        self.setWordWrap(False)  # Allow horizontal overflow

        # Optimize for performance and appearance
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)

        # Configure SINGLE selection only
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Setup custom branch icons for Windows compatibility
        self._setup_branch_icons()

        # Drag state tracking (simplified - only for Qt built-in drag)
        self._is_dragging = False
        self._drag_path = None
        self._drag_start_pos = None
        self._drag_feedback_timer_id = None

        # Incremental state restoration tracking
        self._pending_expand_paths: list[str] = []
        self._pending_select_path: str | None = None
        self._restore_in_progress = False

        # Flag to prevent infinite loop during directory change refresh (Windows issue)
        self._refresh_in_progress = False

        # Connect expand/collapse signals for wait cursor
        self.expanded.connect(self._on_item_expanded)
        self.collapsed.connect(self._on_item_collapsed)

        # Defer filesystem monitor setup until context is ready
        # (context is initialized later in MainWindow setup)
        self._filesystem_monitor = None
        self._filesystem_monitor_setup_pending = True
        self._last_monitored_path: str | None = None

        # Install custom tree view delegate for consistent hover/selection behavior
        from oncutf.core.theme_manager import get_theme_manager

        theme = get_theme_manager()
        self._delegate = TreeViewItemDelegate(self, theme=theme)
        self.setItemDelegate(self._delegate)
        self._delegate.install_event_filter(self)

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

    def showEvent(self, event) -> None:
        """Handle show event - setup filesystem monitor when widget becomes visible."""
        super().showEvent(event)

        # Setup filesystem monitor on first show (context should be ready by then)
        if self._filesystem_monitor_setup_pending:
            self._filesystem_monitor_setup_pending = False
            self._setup_filesystem_monitor()

    def _setup_filesystem_monitor(self) -> None:
        """Setup comprehensive filesystem monitoring."""
        try:
            from oncutf.core.file.monitor import FilesystemMonitor

            # Get FileStore and FileLoadManager from parent window if available
            file_store = None
            file_load_manager = None

            # Try multiple paths to find FileStore and FileLoadManager
            if hasattr(self, "parent") and self.parent():
                parent = self.parent()

                # Try 1: parent.context (MainWindow with context)
                if hasattr(parent, "context"):
                    if hasattr(parent.context, "file_store"):
                        file_store = parent.context.file_store
                        logger.debug(
                            "[FileTreeView] Found FileStore from parent.context",
                            extra={"dev_only": True},
                        )
                    if hasattr(parent.context, "file_load_manager"):
                        file_load_manager = parent.context.file_load_manager
                        logger.debug(
                            "[FileTreeView] Found FileLoadManager from parent.context",
                            extra={"dev_only": True},
                        )
                # Try 2: parent direct attributes
                else:
                    if hasattr(parent, "_file_store"):
                        file_store = parent._file_store
                        logger.debug(
                            "[FileTreeView] Found FileStore from parent._file_store",
                            extra={"dev_only": True},
                        )
                    if hasattr(parent, "file_load_manager"):
                        file_load_manager = parent.file_load_manager
                        logger.debug(
                            "[FileTreeView] Found FileLoadManager from parent.file_load_manager",
                            extra={"dev_only": True},
                        )

                # Try 3: Walk up parent chain looking for MainWindow
                if not file_store or not file_load_manager:
                    current = parent
                    while current is not None:
                        if hasattr(current, "context"):
                            if not file_store and hasattr(current.context, "file_store"):
                                file_store = current.context.file_store
                                logger.debug(
                                    "[FileTreeView] Found FileStore from ancestor context",
                                    extra={"dev_only": True},
                                )
                            if not file_load_manager and hasattr(
                                current.context, "file_load_manager"
                            ):
                                file_load_manager = current.context.file_load_manager
                                logger.debug(
                                    "[FileTreeView] Found FileLoadManager from ancestor context",
                                    extra={"dev_only": True},
                                )
                            if file_store and file_load_manager:
                                break
                        current = current.parent() if hasattr(current, "parent") else None

            if file_store is None:
                logger.warning(
                    "[FileTreeView] FileStore not found - auto-refresh on USB unmount won't work"
                )
            if file_load_manager is None:
                logger.warning(
                    "[FileTreeView] FileLoadManager not found - auto-refresh on USB unmount won't work"
                )

            self._filesystem_monitor = FilesystemMonitor(
                file_store=file_store, file_load_manager=file_load_manager
            )

            # Connect directory change signal for tree model refresh
            self._filesystem_monitor.directory_changed.connect(self._on_directory_changed)

            # Set custom callback for tree refresh (handles drive mount/unmount)
            self._filesystem_monitor.set_drive_change_callback(self._refresh_tree_on_drives_change)

            # Start monitoring
            self._filesystem_monitor.start()

            # Watch the current root path to pick up directory changes (Windows needs explicit watch)
            root_path = ""
            model = self.model()
            if model and hasattr(model, "rootPath"):
                try:
                    root_path = model.rootPath()
                except Exception:
                    root_path = ""

            if root_path and os.path.isdir(root_path):
                if self._filesystem_monitor.add_folder(root_path):
                    self._last_monitored_path = root_path

            logger.info("[FileTreeView] Filesystem monitor started")

        except Exception as e:
            logger.warning("[FileTreeView] Failed to setup filesystem monitor: %s", e)
            self._filesystem_monitor = None

    def _on_directory_changed(self, dir_path: str) -> None:
        """Handle directory content changed.

        Args:
            dir_path: Path of changed directory

        """
        # Prevent infinite loop if refresh triggers another directory change event
        if self._refresh_in_progress:
            logger.debug(
                "[FileTreeView] Ignoring directory change during refresh: %s",
                dir_path,
                extra={"dev_only": True}
            )
            return

        logger.debug("[FileTreeView] Directory changed: %s", dir_path, extra={"dev_only": True})

        # Save state before refresh
        expanded_paths = self._save_expanded_state()
        selected_path = self.get_selected_path()
        scroll_position = self.verticalScrollBar().value()

        # Refresh model if it supports refresh
        model = self.model()
        if model and hasattr(model, "refresh"):
            try:
                self._refresh_in_progress = True
                model.refresh()

                # Reset root index after refresh to prevent "/" from appearing
                import platform
                root = "" if platform.system() == "Windows" else "/"
                self.setRootIndex(model.index(root))

                logger.debug(
                    "[FileTreeView] Model refreshed after directory change",
                    extra={"dev_only": True},
                )
            except Exception as e:
                logger.exception("[FileTreeView] Model refresh error: %s", e)
            finally:
                self._refresh_in_progress = False

        # Restore state after model finishes loading (async)
        # QFileSystemModel loads directories asynchronously, so we need a delay
        from oncutf.utils.shared.timer_manager import schedule_ui_update
        schedule_ui_update(
            lambda: self._restore_tree_state(expanded_paths, selected_path, scroll_position),
            delay=100,
        )

    def _refresh_tree_on_drives_change(self, _drives: list[str]) -> None:
        """Refresh tree when drives change.

        Args:
            _drives: Current list of available drives (unused)

        """
        logger.info("[FileTreeView] Drives changed, refreshing tree")

        # Save state before refresh
        expanded_paths = self._save_expanded_state()
        selected_path = self.get_selected_path()
        scroll_position = self.verticalScrollBar().value()

        old_model = self.model()
        if not old_model:
            logger.debug("[FileTreeView] No model to refresh", extra={"dev_only": True})
            return

        # Get the old model's configuration
        name_filters = old_model.nameFilters() if hasattr(old_model, "nameFilters") else []
        file_filter = old_model.filter() if hasattr(old_model, "filter") else None

        try:
            # The only reliable way to refresh drives in Windows is to recreate the model
            # QFileSystemModel caches drive information and doesn't detect removals properly
            from oncutf.ui.widgets.custom_file_system_model import CustomFileSystemModel

            # Create new model with same configuration
            new_model = CustomFileSystemModel()

            # Set root path based on platform to match root index
            # This prevents "/" from appearing as a node in Linux
            import platform

            root = "" if platform.system() == "Windows" else "/"
            new_model.setRootPath(root)

            if file_filter is not None:
                new_model.setFilter(file_filter)

            if name_filters:
                new_model.setNameFilters(name_filters)
                new_model.setNameFilterDisables(False)

            # Replace the model
            self.setModel(new_model)

            # Set root index based on platform:
            # - Windows: empty root shows drives (C:, D:, etc)
            # - Linux: "/" root shows children (/bin, /boot, /etc) without showing "/" itself
            self.setRootIndex(new_model.index(root))

            # Update parent window reference if available
            parent = self.parent()
            while parent is not None:
                if hasattr(parent, "dir_model"):
                    # Delete old model
                    if old_model is not None:
                        old_model.deleteLater()
                    # Update reference
                    parent.dir_model = new_model
                    logger.debug(
                        "[FileTreeView] Parent window dir_model reference updated",
                        extra={"dev_only": True},
                    )
                    break
                parent = parent.parent() if hasattr(parent, "parent") else None

            logger.info("[FileTreeView] Model recreated successfully to reflect drive changes")

            # Restore state after model finishes loading (async)
            # QFileSystemModel loads directories asynchronously, so we need a delay
            from oncutf.utils.shared.timer_manager import schedule_ui_update
            schedule_ui_update(
                lambda: self._restore_tree_state(expanded_paths, selected_path, scroll_position),
                delay=100,
            )

        except Exception as e:
            logger.exception("[FileTreeView] Error recreating model: %s", e)
            # Restore state even on error (with delay)
            from oncutf.utils.shared.timer_manager import schedule_ui_update
            schedule_ui_update(
                lambda: self._restore_tree_state(expanded_paths, selected_path, scroll_position),
                delay=100,
            )

    def closeEvent(self, event) -> None:
        """Clean up resources before closing."""
        try:
            # Stop filesystem monitor
            if hasattr(self, "_filesystem_monitor") and self._filesystem_monitor is not None:
                try:
                    self._filesystem_monitor.stop()
                    self._filesystem_monitor.blockSignals(True)
                    self._filesystem_monitor.deleteLater()
                    self._filesystem_monitor = None
                    logger.debug(
                        "[FileTreeView] Filesystem monitor stopped", extra={"dev_only": True}
                    )
                except Exception as e:
                    logger.warning("[FileTreeView] Error stopping filesystem monitor: %s", e)

            logger.debug("[FileTreeView] Cleanup completed", extra={"dev_only": True})

        except Exception as e:
            logger.exception("[FileTreeView] Error during cleanup: %s", e)

        # Call parent closeEvent
        super().closeEvent(event)

    def _setup_branch_icons(self) -> None:
        """Setup custom branch icons for better cross-platform compatibility."""
        try:
            from oncutf.utils.ui.icons_loader import get_menu_icon

            # Try to load custom icons (skip if not found)
            try:
                _closed_icon = get_menu_icon("chevron-right")
                _open_icon = get_menu_icon("chevron-down")
            except Exception:
                # Icons not found, skip custom setup
                logger.debug(
                    "[FileTreeView] Custom branch icons not found, using Qt defaults",
                    extra={"dev_only": True},
                )
                return

            # Set the icons on the style
            style = self.style()
            if hasattr(style, "setPixmap"):
                # Note: This approach may not work in all Qt versions
                # The QSS approach is usually more reliable
                pass

            logger.debug(
                "[FileTreeView] Custom branch icons setup attempted", extra={"dev_only": True}
            )

        except Exception as e:
            logger.debug(
                "[FileTreeView] Branch icons setup skipped: %s", e, extra={"dev_only": True}
            )
            # Fallback to default Qt icons

    def _setup_icon_delegate(self) -> None:
        """Setup the icon delegate for selection-based icon changes."""
        # Icon delegate functionality removed for simplicity

    def selectionChanged(self, selected, deselected) -> None:
        """Override to emit custom signal with selected path (single item only)"""
        super().selectionChanged(selected, deselected)

        # Get single selected path
        selected_path = ""
        indexes = self.selectedIndexes()
        if indexes and self.model() and hasattr(self.model(), "filePath"):
            # Take first index (should be only one in single selection mode)
            path = self.model().filePath(indexes[0])
            if path:
                selected_path = path

        # Keep filesystem watcher aligned with the active folder so directory changes refresh the tree
        if selected_path and os.path.isdir(selected_path) and self._filesystem_monitor:
            try:
                if self._last_monitored_path:
                    self._filesystem_monitor.remove_folder(self._last_monitored_path)
                if self._filesystem_monitor.add_folder(selected_path):
                    self._last_monitored_path = selected_path
            except Exception as e:
                logger.debug(
                    "[FileTreeView] Failed to update monitored folder: %s",
                    e,
                    extra={"dev_only": True},
                )

        self.selection_changed.emit(selected_path)

    def setModel(self, model) -> None:
        """Override to configure header when model is set"""
        super().setModel(model)
        self._configure_header()

    def resizeEvent(self, event) -> None:
        """Handle resize to adjust column width for optimal horizontal scrolling"""
        super().resizeEvent(event)
        self._adjust_column_width()

    def _configure_header(self) -> None:
        """Configure header for optimal display"""
        header = self.header()
        if header:
            # Hide header completely
            header.setVisible(False)
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)

            # Hide all columns except the first (name)
            for col in range(1, self.model().columnCount() if self.model() else 4):
                self.setColumnHidden(col, True)

            logger.debug(
                "[FileTreeView] Header configured for single column display",
                extra={"dev_only": True},
            )

    def _adjust_column_width(self) -> None:
        """Adjust column width for optimal horizontal scrolling"""
        if not self.model():
            return

        header = self.header()
        if not header:
            return

        viewport_width = self.viewport().width()
        content_width = self.sizeHintForColumn(0)

        if content_width > 0:
            if content_width <= viewport_width:
                header.setSectionResizeMode(0, QHeaderView.Stretch)
                self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                logger.debug(
                    "[FileTreeView] Content fits viewport - stretching column",
                    extra={"dev_only": True},
                )
            else:
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                logger.debug(
                    "[FileTreeView] Content exceeds viewport (%d > %d) - enabling scrollbar",
                    content_width,
                    viewport_width,
                    extra={"dev_only": True},
                )

    def _on_model_changed(self) -> None:
        """Called when model data changes to update column width"""
        schedule_scroll_adjust(self._adjust_column_width, 10)

    def get_selected_path(self) -> str:
        """Get the single selected file/folder path"""
        selection_model = self.selectionModel()
        if not selection_model:
            return ""

        # Use selectedRows() for clean single selection
        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return ""

        # Get first (and only) selected item
        index = selected_rows[0]
        if self.model() and hasattr(self.model(), "filePath"):
            path = self.model().filePath(index)
            return path if path else ""

        return ""

    def select_path(self, path: str) -> None:
        """Select item by its file path"""
        if not self.model() or not hasattr(self.model(), "index"):
            return

        selection_model = self.selectionModel()
        if not selection_model:
            return

        index = self.model().index(path)
        if index.isValid():
            selection_model.clearSelection()
            selection_model.select(index, selection_model.Select | selection_model.Rows)

    def _save_expanded_state(self) -> list[str]:
        """Save currently expanded paths.

        Returns:
            List of file paths that are currently expanded

        """
        expanded_paths = []
        model = self.model()

        if not model or not hasattr(model, "filePath"):
            return expanded_paths

        visited_paths = set()  # Prevent infinite recursion

        def collect_expanded(parent_index: QModelIndex, depth: int = 0) -> None:
            """Recursively collect expanded indices with protection against infinite loops."""
            # Limit recursion depth to prevent stack overflow
            if depth > 100:
                logger.warning(
                    "[FileTreeView] Maximum recursion depth reached in _save_expanded_state",
                )
                return

            row_count = model.rowCount(parent_index)
            for row in range(row_count):
                index = model.index(row, 0, parent_index)
                if not index.isValid():
                    continue

                # Check if this index is expanded
                if self.isExpanded(index):
                    path = model.filePath(index)
                    if path:
                        # Prevent processing the same path twice (circular references)
                        if path in visited_paths:
                            continue
                        visited_paths.add(path)

                        expanded_paths.append(path)
                        # Recurse into children with increased depth
                        collect_expanded(index, depth + 1)

        # Start from root
        import platform
        root = "" if platform.system() == "Windows" else "/"
        root_index = model.index(root)
        collect_expanded(root_index, 0)

        logger.debug(
            "[FileTreeView] Saved %d expanded paths",
            len(expanded_paths),
            extra={"dev_only": True},
        )
        return expanded_paths

    def _restore_expanded_state(self, paths: list[str]) -> None:
        """Restore expanded state from saved paths.

        Args:
            paths: List of file paths to expand

        """
        model = self.model()
        if not model or not hasattr(model, "index"):
            return

        # Limit number of paths to restore to prevent performance issues
        if len(paths) > 500:
            logger.warning(
                "[FileTreeView] Too many expanded paths (%d), limiting to 500",
                len(paths),
            )
            paths = paths[:500]

        # Build complete set of paths including all parent directories
        # This ensures we expand parents before children
        all_paths_to_expand = set()

        import platform
        root = "" if platform.system() == "Windows" else "/"

        for path in paths:
            # Skip invalid or non-existent paths early to avoid filesystem scans
            if not path or not os.path.exists(path):
                continue

            # Add the path itself
            all_paths_to_expand.add(path)
            # Add all parent paths including root
            parent = os.path.dirname(path)
            while parent and parent != root:
                all_paths_to_expand.add(parent)
                parent = os.path.dirname(parent)
            # Add root if we have any paths
            if path:
                all_paths_to_expand.add(root)

        # Sort by depth (shallow to deep) to ensure parents are expanded first
        sorted_paths = sorted(all_paths_to_expand, key=lambda p: p.count(os.sep))

        restored_count = 0
        # Limit total expansion operations to prevent infinite loops
        max_operations = 1000
        for i, path in enumerate(sorted_paths):
            if i >= max_operations:
                logger.warning(
                    "[FileTreeView] Reached maximum expansion operations (%d), stopping",
                    max_operations,
                )
                break

            # Get index for this path
            try:
                index = model.index(path)
                if index.isValid():
                    self.setExpanded(index, True)
                    restored_count += 1
            except Exception as e:
                logger.debug(
                    "[FileTreeView] Failed to expand path %s: %s",
                    path,
                    e,
                    extra={"dev_only": True},
                )

        logger.debug(
            "[FileTreeView] Restored %d/%d expanded paths (including %d parents)",
            restored_count,
            len(paths),
            len(all_paths_to_expand) - len(paths),
            extra={"dev_only": True},
        )

    def _restore_tree_state(
        self, expanded_paths: list[str], selected_path: str, scroll_position: int
    ) -> None:
        """Restore complete tree state: expanded paths, selection, and scroll position.

        Args:
            expanded_paths: List of paths that were expanded
            selected_path: Path that was selected
            scroll_position: Vertical scroll position

        """
        # First restore expanded state
        self._restore_expanded_state(expanded_paths)

        # Then restore selection
        if selected_path and os.path.exists(selected_path):
            self.select_path(selected_path)
            logger.debug(
                "[FileTreeView] Restored selection: %s", selected_path, extra={"dev_only": True}
            )

        # Finally restore scroll position
        if scroll_position > 0:
            self.verticalScrollBar().setValue(scroll_position)
            logger.debug(
                "[FileTreeView] Restored scroll position: %d",
                scroll_position,
                extra={"dev_only": True},
            )

    # =====================================
    # CUSTOM RENDERING
    # =====================================

    # =====================================
    # CUSTOM SINGLE-ITEM DRAG IMPLEMENTATION
    # =====================================

    def mousePressEvent(self, event):
        """Handle mouse press for custom drag detection"""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self._is_dragging = False
            self._drag_path = None

        # Call super() to handle normal selection
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for custom drag start and real-time drop zone validation"""
        # If we're dragging, only handle drag feedback and block all other processing
        if self._is_dragging:
            # Only update drag feedback after the cursor has moved away from the FileTreeView widget
            # This prevents immediate "invalid" feedback when drag starts over the source widget
            if not self._drag_start_pos:
                self._drag_start_pos = event.pos()
            else:
                # Check if cursor has moved outside the FileTreeView widget
                cursor_pos = QCursor.pos()
                widget_under_cursor = QApplication.widgetAt(cursor_pos)

                # Check if cursor is still over this FileTreeView or its children
                current_widget = widget_under_cursor
                still_over_source = False

                while current_widget:
                    if current_widget is self:
                        still_over_source = True
                        break
                    current_widget = current_widget.parent()

                # If cursor has left the FileTreeView, start feedback
                if not still_over_source:
                    self._drag_start_pos = event.pos()
                    self._update_drag_feedback()
            # Don't call super().mouseMoveEvent() during drag to prevent hover changes
            return

        # Only proceed if left button is pressed and we have a start position
        if not (event.buttons() & Qt.LeftButton) or not self._drag_start_pos:
            # Reset drag preparation if no drag is happening
            if self._drag_start_pos:
                self._drag_start_pos = None
            super().mouseMoveEvent(event)
            return

        # Check drag distance threshold to prevent accidental drags (e.g. when clicking chevrons)
        if (
            event.pos() - self._drag_start_pos
        ).manhattanLength() < QApplication.startDragDistance():
            return

        # Start our custom drag
        logger.debug("[FileTreeView] About to start custom drag", extra={"dev_only": True})
        self._start_custom_drag()
        # Don't call super().mouseMoveEvent() after starting drag to prevent hover changes

    def mouseReleaseEvent(self, event):
        """Handle mouse release to end drag"""
        was_dragging = self._is_dragging

        # End drag first
        self._end_custom_drag()

        # Call super() for normal processing
        super().mouseReleaseEvent(event)

        # Force cursor cleanup if we were dragging
        if was_dragging:
            # Ensure all override cursors are removed
            cursor_count = 0
            while QApplication.overrideCursor() and cursor_count < 5:
                QApplication.restoreOverrideCursor()
                cursor_count += 1

            if cursor_count > 0:
                logger.debug(
                    "[FileTreeView] Cleaned %d stuck cursors after drag",
                    cursor_count,
                    extra={"dev_only": True},
                )

            # Create a fake mouse move event to restore hover state
            fake_move_event = QMouseEvent(
                QEvent.MouseMove, event.pos(), Qt.NoButton, Qt.NoButton, Qt.NoModifier
            )
            QApplication.postEvent(self, fake_move_event)

    def _start_custom_drag(self):
        """Start our custom drag operation with enhanced visual feedback"""
        if not self._drag_start_pos:
            return

        # Get the item under the mouse
        index = self.indexAt(self._drag_start_pos)
        if not index.isValid():
            return

        # Get the path under mouse
        model = self.model()
        if not model or not hasattr(model, "filePath"):
            return

        clicked_path = model.filePath(index)
        if not clicked_path or not self._is_valid_drag_target(clicked_path):
            return

        # Block drag on mount points and root drives to prevent UI freeze
        import os

        from oncutf.utils.filesystem.folder_counter import is_mount_point_or_root

        if os.path.isdir(clicked_path) and is_mount_point_or_root(clicked_path):
            logger.warning(
                "[FileTreeView] Blocked drag on mount point/root: %s",
                clicked_path,
                extra={"dev_only": True},
            )
            return

        # Store the single item being dragged
        self._drag_path = clicked_path

        # Set drag state
        self._is_dragging = True

        # Disable mouse tracking to prevent hover effects during drag
        self._original_mouse_tracking = self.hasMouseTracking()
        self.setMouseTracking(False)

        # Disable hover attribute temporarily
        self._original_hover_enabled = self.testAttribute(Qt.WA_Hover)
        self.setAttribute(Qt.WA_Hover, False)

        # Also disable hover on viewport
        self._original_viewport_hover = self.viewport().testAttribute(Qt.WA_Hover)
        self.viewport().setAttribute(Qt.WA_Hover, False)

        # Disable mouse tracking on viewport too
        self._original_viewport_tracking = self.viewport().hasMouseTracking()
        self.viewport().setMouseTracking(False)

        # Notify DragManager
        drag_manager = DragManager.get_instance()
        drag_manager.start_drag("file_tree")

        # Determine initial display info
        is_folder = os.path.isdir(clicked_path)
        # Use folder name for folders, "1 item" for files
        initial_info = os.path.basename(clicked_path) if is_folder else "1 item"

        # Start enhanced visual feedback
        visual_manager = DragVisualManager.get_instance()
        drag_type = visual_manager.get_drag_type_from_path(clicked_path)
        start_drag_visual(drag_type, initial_info, "file_tree")

        # For folders, schedule async count update (hybrid approach)
        if is_folder:
            from oncutf.utils.shared.timer_manager import schedule_ui_update

            schedule_ui_update(lambda: self._update_folder_count(clicked_path), delay=10)

        # Set initial drag widget for zone validation
        logger.debug(
            "[FileTreeView] Setting up initial drag widget for zone validation",
            extra={"dev_only": True},
        )
        DragZoneValidator.set_initial_drag_widget("file_tree", "FileTreeView")

        # Start drag feedback timer for real-time visual updates using timer_manager
        if hasattr(self, "_drag_feedback_timer_id") and self._drag_feedback_timer_id:
            from oncutf.utils.shared.timer_manager import cancel_timer

            cancel_timer(self._drag_feedback_timer_id)

        # Schedule repeated updates using timer_manager
        self._start_drag_feedback_loop()

        logger.debug(
            "[FileTreeView] Custom drag started: %s",
            clicked_path,
            extra={"dev_only": True},
        )

    def _start_drag_feedback_loop(self):
        """Start repeated drag feedback updates using timer_manager"""
        from oncutf.utils.shared.timer_manager import schedule_ui_update

        if self._is_dragging:
            self._update_drag_feedback()
            # Schedule next update
            self._drag_feedback_timer_id = schedule_ui_update(
                self._start_drag_feedback_loop, delay=50
            )

    def _update_drag_feedback(self):
        """Update visual feedback based on current cursor position during drag"""
        if not self._is_dragging:
            return

        # Use common drag feedback logic
        should_continue = update_drag_feedback_for_widget(self, "file_tree")

        # If cursor is outside application, end drag
        if not should_continue:
            self._end_custom_drag()

    def _end_custom_drag(self):
        """End our custom drag operation with enhanced visual feedback"""
        if not self._is_dragging:
            return

        # Check if drag has been cancelled by external force cleanup
        drag_manager = DragManager.get_instance()
        if not drag_manager.is_drag_active():
            logger.debug(
                "[FileTreeView] Drag was cancelled, skipping drop", extra={"dev_only": True}
            )
            # Clean up drag state without performing drop
            self._is_dragging = False
            self._drag_start_pos = None

            # Stop and cleanup drag feedback timer
            if hasattr(self, "_drag_feedback_timer") and self._drag_feedback_timer is not None:
                self._drag_feedback_timer.stop()
                self._drag_feedback_timer.deleteLater()
                self._drag_feedback_timer = None

            # Restore mouse tracking to original state
            if hasattr(self, "_original_mouse_tracking"):
                self.setMouseTracking(self._original_mouse_tracking)
                delattr(self, "_original_mouse_tracking")

            # Restore hover attribute
            if hasattr(self, "_original_hover_enabled"):
                self.setAttribute(Qt.WA_Hover, self._original_hover_enabled)
                delattr(self, "_original_hover_enabled")

            # Restore viewport attributes
            if hasattr(self, "_original_viewport_hover"):
                self.viewport().setAttribute(Qt.WA_Hover, self._original_viewport_hover)
                delattr(self, "_original_viewport_hover")

            if hasattr(self, "_original_viewport_tracking"):
                self.viewport().setMouseTracking(self._original_viewport_tracking)
                delattr(self, "_original_viewport_tracking")

            # End visual feedback
            end_drag_visual()

            # Zone validation tracking removed

            # Restore hover state with fake mouse move event
            self._restore_hover_after_drag()

            logger.debug(
                "[FileTreeView] Custom drag ended (cancelled): %s",
                self._drag_path,
                extra={"dev_only": True},
            )
            return

        # Check if we dropped on a valid target (only FileTableView allowed)
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        logger.debug(
            "[FileTreeView] Widget under cursor: %s",
            widget_under_cursor,
            extra={"dev_only": True},
        )

        # Use visual manager to validate drop target
        visual_manager = DragVisualManager.get_instance()
        valid_drop = False

        # Check if dropped on file table (strict policy: only FileTableView)
        if widget_under_cursor:
            # Look for FileTableView in parent hierarchy
            parent = widget_under_cursor
            while parent:
                logger.debug(
                    "[FileTreeView] Checking parent: %s",
                    parent.__class__.__name__,
                    extra={"dev_only": True},
                )

                # Check with visual manager
                if visual_manager.is_valid_drop_target(parent, "file_tree"):
                    logger.debug(
                        "[FileTreeView] Valid drop target found: %s",
                        parent.__class__.__name__,
                        extra={"dev_only": True},
                    )
                    self._handle_drop_on_table()
                    valid_drop = True
                    break

                # Also check viewport of FileTableView
                if hasattr(parent, "parent") and parent.parent():
                    if visual_manager.is_valid_drop_target(parent.parent(), "file_tree"):
                        logger.debug(
                            "[FileTreeView] Valid drop target found via viewport: %s",
                            parent.parent().__class__.__name__,
                            extra={"dev_only": True},
                        )
                        self._handle_drop_on_table()
                        valid_drop = True
                        break

                # Check for policy violations
                if parent.__class__.__name__ in ["FileTreeView", "MetadataTreeView"]:
                    logger.debug(
                        "[FileTreeView] Rejecting drop on %s (policy violation)",
                        parent.__class__.__name__,
                        extra={"dev_only": True},
                    )
                    break

                parent = parent.parent()

        # Log drop result
        if not valid_drop:
            logger.debug("[FileTreeView] Drop on invalid target", extra={"dev_only": True})

        # Clean up drag state
        self._is_dragging = False
        self._drag_start_pos = None

        # Stop and cleanup drag feedback timer
        if hasattr(self, "_drag_feedback_timer_id") and self._drag_feedback_timer_id:
            from oncutf.utils.shared.timer_manager import cancel_timer

            cancel_timer(self._drag_feedback_timer_id)
            self._drag_feedback_timer_id = None

        # Restore mouse tracking to original state
        if hasattr(self, "_original_mouse_tracking"):
            self.setMouseTracking(self._original_mouse_tracking)
            delattr(self, "_original_mouse_tracking")

        # Restore hover attribute
        if hasattr(self, "_original_hover_enabled"):
            self.setAttribute(Qt.WA_Hover, self._original_hover_enabled)
            delattr(self, "_original_hover_enabled")

        # Restore viewport attributes
        if hasattr(self, "_original_viewport_hover"):
            self.viewport().setAttribute(Qt.WA_Hover, self._original_viewport_hover)
            delattr(self, "_original_viewport_hover")

        if hasattr(self, "_original_viewport_tracking"):
            self.viewport().setMouseTracking(self._original_viewport_tracking)
            delattr(self, "_original_viewport_tracking")

        # End visual feedback
        end_drag_visual()

        # Clear initial drag widget tracking
        DragZoneValidator.clear_initial_drag_widget("file_tree")

        # Notify DragManager
        drag_manager.end_drag("file_tree")

        # Restore hover state with fake mouse move event
        self._restore_hover_after_drag()

        # Restore folder selection if it was lost during drag
        if self._drag_path and os.path.isdir(self._drag_path):
            # Check if the dragged folder is still selected
            current_selection = self.get_selected_path()
            if current_selection != self._drag_path:
                # Selection was lost, restore it
                self.select_path(self._drag_path)
                logger.debug(
                    "[FileTreeView] Restored folder selection: %s",
                    self._drag_path,
                    extra={"dev_only": True},
                )

        logger.debug(
            "[FileTreeView] Custom drag ended: %s (valid_drop: %s)",
            self._drag_path,
            valid_drop,
            extra={"dev_only": True},
        )

    def _restore_hover_after_drag(self):
        """Restore hover state after drag ends by sending a fake mouse move event"""
        # Get current cursor position relative to this widget
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)

        # Only restore hover if cursor is still over this widget
        if self.rect().contains(local_pos):
            # Create and post a fake mouse move event
            fake_move_event = QMouseEvent(
                QEvent.MouseMove, local_pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier
            )
            QApplication.postEvent(self, fake_move_event)

    def _update_folder_count(self, folder_path: str) -> None:
        """Update drag cursor with folder contents count (hybrid approach with timeout).

        This runs asynchronously after drag starts to provide accurate count without
        blocking the drag start. Uses timeout to prevent lag on large folders.
        """
        if not self._is_dragging or self._drag_path != folder_path:
            # Drag ended or path changed, skip update
            return

        from oncutf.core.drag.drag_visual_manager import update_source_info
        from oncutf.utils.filesystem.folder_counter import count_folder_contents

        # Check if we're in recursive mode (Ctrl pressed)
        modifiers = QApplication.keyboardModifiers()
        is_recursive = bool(modifiers & Qt.ControlModifier)

        # Count with appropriate mode
        count = count_folder_contents(
            folder_path,
            recursive=is_recursive,
            timeout_ms=100.0,  # 100ms max to keep drag responsive
        )

        # Format and update display
        display_text = count.format_display()

        # Don't add mode indicators - keep it clean and simple
        # The format is already clear from the content

        # Update cursor text
        update_source_info(display_text)

        logger.debug(
            "[FileTreeView] Updated drag count: %s (recursive=%s, timeout=%s, %.1fms)",
            display_text,
            is_recursive,
            count.timed_out,
            count.elapsed_ms,
            extra={"dev_only": True},
        )

    def _handle_drop_on_table(self):
        """Handle drop on file table with new 4-modifier logic"""
        if not self._drag_path:
            return

        # Use real-time modifiers at drop time (standard UX behavior)
        modifiers = QApplication.keyboardModifiers()

        # Emit signal with single path and modifiers
        self.item_dropped.emit(self._drag_path, modifiers)

        # Log the action for debugging using centralized logic
        _, _, action = decode_modifiers_to_flags(modifiers)

        logger.info(
            "[FileTreeView] Dropped: %s (%s)",
            self._drag_path,
            action,
            extra={"dev_only": True},
        )

    def _is_valid_drag_target(self, path: str) -> bool:
        """Check if path is valid for dragging"""
        if os.path.isdir(path):
            # Block dragging of mount points and root drives to prevent UI freeze
            from oncutf.utils.filesystem.folder_counter import is_mount_point_or_root

            if is_mount_point_or_root(path):
                logger.warning(
                    "[FileTreeView] Blocked drag of mount point/root: %s",
                    path,
                    extra={"dev_only": True},
                )
                return False
            return True

        # For files, check extension
        _, ext = os.path.splitext(path)
        if ext.startswith("."):
            ext = ext[1:].lower()

        if ext not in ALLOWED_EXTENSIONS:
            logger.debug(
                "[FileTreeView] Skipping drag for non-allowed extension: %s",
                ext,
                extra={"dev_only": True},
            )
            return False

        return True

    # =====================================
    # DROP HANDLING (unchanged)
    # =====================================

    def dragEnterEvent(self, event):
        """Accept internal drops only"""
        event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move"""
        event.ignore()

    def dropEvent(self, event):
        """Handle drop events"""
        event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave"""
        event.ignore()

    # =====================================
    # KEY HANDLING
    # =====================================

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events, including modifier changes during drag"""
        # Update drag feedback if we're currently dragging
        if self._is_dragging:
            self._update_drag_feedback()

        # Handle F5 refresh
        if event.key() == Qt.Key_F5:
            self._refresh_tree_view()
            event.accept()
            return

        # Handle Return/Enter key to emit folder_selected signal
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.folder_selected.emit()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        """Handle key release events, including modifier changes during drag"""
        # Update drag feedback if we're currently dragging
        if self._is_dragging:
            self._update_drag_feedback()

        super().keyReleaseEvent(event)

    def _refresh_tree_view(self) -> None:
        """Refresh the tree view by refreshing the underlying model."""
        from oncutf.utils.ui.cursor_helper import wait_cursor

        logger.info("[FileTreeView] F5 pressed - refreshing tree view")

        with wait_cursor():
            model = self.model()
            if model and hasattr(model, "refresh"):
                try:
                    # Save current selection and expanded state
                    current_path = self.get_selected_path()
                    expanded_paths = self._save_expanded_state()

                    # Limit expanded paths to avoid performance issues
                    if len(expanded_paths) > 100:
                        logger.info(
                            "[FileTreeView] Limiting expanded paths from %d to 100",
                            len(expanded_paths),
                        )
                        # Keep only shallowest paths (sorted by depth)
                        expanded_paths = sorted(expanded_paths, key=lambda p: p.count(os.sep))[:100]

                    model.refresh()

                    # Reset root index after refresh to prevent "/" from appearing
                    import platform
                    root = "" if platform.system() == "Windows" else "/"
                    self.setRootIndex(model.index(root))

                    # Start incremental restoration (non-blocking)
                    self._start_incremental_restore(expanded_paths, current_path)

                    logger.info("[FileTreeView] Tree view refreshed successfully")

                    # Show status message if parent window has status manager
                    if hasattr(self, "parent") and callable(self.parent):
                        parent = self.parent()
                        if parent and hasattr(parent, "status_manager"):
                            parent.status_manager.set_file_operation_status(
                                "File tree refreshed", success=True, auto_reset=True
                            )

                except Exception as e:
                    logger.exception("[FileTreeView] Error refreshing tree view: %s", e)
            else:
                logger.debug(
                    "[FileTreeView] No model or model does not support refresh",
                    extra={"dev_only": True},
                )

    def _start_incremental_restore(self, expanded_paths: list[str], selected_path: str | None) -> None:
        """Start incremental restoration of tree state (non-blocking).

        Args:
            expanded_paths: Paths to expand incrementally
            selected_path: Path to select after expansion complete
        """
        # Cancel any pending restore
        if self._restore_in_progress:
            from oncutf.utils.shared.timer_manager import get_timer_manager
            get_timer_manager().cancel("tree_incremental_restore")

        # Filter out non-existent paths early
        import platform
        root = "" if platform.system() == "Windows" else "/"

        valid_paths = []
        for path in expanded_paths:
            if path and os.path.exists(path):
                valid_paths.append(path)

        # Build parent paths and sort by depth
        all_paths_to_expand = set()
        for path in valid_paths:
            all_paths_to_expand.add(path)
            parent = os.path.dirname(path)
            while parent and parent != root:
                all_paths_to_expand.add(parent)
                parent = os.path.dirname(parent)

        # Sort by depth (shallow first) to expand parents before children
        self._pending_expand_paths = sorted(all_paths_to_expand, key=lambda p: p.count(os.sep))
        self._pending_select_path = selected_path
        self._restore_in_progress = True

        logger.debug(
            "[FileTreeView] Starting incremental restore of %d paths",
            len(self._pending_expand_paths),
            extra={"dev_only": True},
        )

        # Start the restoration process
        self._process_next_restore_batch()

    def _process_next_restore_batch(self) -> None:
        """Process next batch of paths to expand (called via timer)."""
        if not self._restore_in_progress or not self._pending_expand_paths:
            # Restoration complete - restore selection if needed
            self._restore_in_progress = False
            if self._pending_select_path and os.path.exists(self._pending_select_path):
                try:
                    self.select_path(self._pending_select_path)
                    logger.debug(
                        "[FileTreeView] Restored selection: %s",
                        self._pending_select_path,
                        extra={"dev_only": True},
                    )
                except Exception as e:
                    logger.debug(
                        "[FileTreeView] Failed to restore selection: %s",
                        e,
                        extra={"dev_only": True},
                    )
            self._pending_select_path = None
            logger.debug(
                "[FileTreeView] Incremental restore complete",
                extra={"dev_only": True},
            )
            return

        # Take next batch (10 paths at a time to keep UI responsive)
        batch_size = 10
        batch = self._pending_expand_paths[:batch_size]
        self._pending_expand_paths = self._pending_expand_paths[batch_size:]

        # Expand batch
        model = self.model()
        if model:
            for path in batch:
                try:
                    index = model.index(path)
                    if index.isValid():
                        self.setExpanded(index, True)
                except Exception as e:
                    logger.debug(
                        "[FileTreeView] Failed to expand %s: %s",
                        path,
                        e,
                        extra={"dev_only": True},
                    )

        # Schedule next batch (20ms delay to keep UI responsive)
        from oncutf.utils.shared.timer_manager import TimerType, get_timer_manager

        get_timer_manager().schedule(
            self._process_next_restore_batch,
            delay=20,
            timer_type=TimerType.UI_UPDATE,
            timer_id="tree_incremental_restore",
            consolidate=False,
        )

    def _restore_selection_after_refresh(self, path: str) -> None:
        """Restore selection after tree refresh (called via timer)."""
        try:
            if path and os.path.exists(path):
                self.select_path(path)
                logger.debug(
                    "[FileTreeView] Restored selection after refresh: %s",
                    path,
                    extra={"dev_only": True},
                )
        except Exception as e:
            logger.debug(
                "[FileTreeView] Failed to restore selection: %s",
                e,
                extra={"dev_only": True},
            )

    # =====================================
    # SPLITTER INTEGRATION (unchanged)
    # =====================================

    def on_horizontal_splitter_moved(self, _pos: int, _index: int) -> None:
        """Handle horizontal splitter movement to adjust column width"""
        schedule_scroll_adjust(self._adjust_column_width, 50)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement (placeholder for future use)"""

    def scrollTo(self, index, hint=None) -> None:
        """Override to ensure optimal scrolling behavior"""
        super().scrollTo(index, hint or QAbstractItemView.EnsureVisible)

    def wheelEvent(self, event) -> None:
        """Update hover state after scroll to track cursor position smoothly."""
        super().wheelEvent(event)

        # Update hover after scroll to reflect current cursor position
        if hasattr(self, "_delegate") and self._delegate:
            delegate = self._delegate
            if hasattr(delegate, "hovered_index"):
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

    def event(self, event):
        """Override event handling to block hover events during drag"""
        # Block hover events during drag or drag preparation (with safe attribute check)
        if (
            (hasattr(self, "_is_dragging") and self._is_dragging)
            or (hasattr(self, "_drag_start_pos") and self._drag_start_pos)
        ) and event.type() in (QEvent.HoverEnter, QEvent.HoverMove, QEvent.HoverLeave):
            return True  # Consume the event without processing

        return super().event(event)

    def startDrag(self, _supported_actions):
        """Override Qt's built-in drag to prevent it from interfering with our custom drag"""
        # Do nothing - we handle all drag operations through our custom system
        # This prevents Qt from starting its own drag which could cause hover issues
        logger.debug(
            "[FileTreeView] Built-in startDrag called but ignored - using custom drag system",
            extra={"dev_only": True},
        )

    def _on_item_expanded(self, _index):
        """Handle item expansion with wait cursor for better UX"""
        from oncutf.utils.shared.timer_manager import schedule_ui_update
        from oncutf.utils.ui.cursor_helper import wait_cursor

        def show_wait_cursor():
            """Show wait cursor briefly during folder expansion"""
            with wait_cursor():
                # Brief delay to show wait cursor during expansion
                QApplication.processEvents()
                schedule_ui_update(lambda: None, delay=100)  # 100ms delay for visibility

        # Schedule wait cursor for expansion
        schedule_ui_update(show_wait_cursor, delay=1)
        logger.debug("[FileTreeView] Item expanded with wait cursor", extra={"dev_only": True})

        # Save expanded state to config
        self._save_expanded_state_to_config()

    def _on_item_collapsed(self, _index):
        """Handle item collapse - no wait cursor needed as it's instant"""
        logger.debug("[FileTreeView] Item collapsed", extra={"dev_only": True})

        # Save expanded state to config
        self._save_expanded_state_to_config()

    def _save_expanded_state_to_config(self) -> None:
        """Save current expanded state to window config."""
        # Find parent window with config manager
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "window_config_manager"):
                parent.window_config_manager.save_window_config()
                logger.debug(
                    "[FileTreeView] Expanded state saved to config", extra={"dev_only": True}
                )
                return
            parent = parent.parent() if hasattr(parent, "parent") else None

        logger.debug(
            "[FileTreeView] No window_config_manager found, state not saved",
            extra={"dev_only": True},
        )


# =====================================
# DRAG CANCEL FILTER (Global Instance)
# =====================================


class DragCancelFilter:
    """Filter that prevents selection clearing during drag operations.

    This is used to maintain file selection when dragging from FileTableView
    to MetadataTreeView, especially when no modifier keys are pressed.
    """

    def __init__(self):
        self._active = False
        self._preserved_selection = set()

    def activate(self):
        """Activate the filter to preserve current selection"""
        self._active = True
        logger.debug(
            "[DragCancelFilter] Activated - preserving selection", extra={"dev_only": True}
        )

    def deactivate(self):
        """Deactivate the filter"""
        if self._active:
            self._active = False
            self._preserved_selection.clear()
            logger.debug("[DragCancelFilter] Deactivated", extra={"dev_only": True})

    def preserve_selection(self, selection: set):
        """Store selection to preserve during drag"""
        self._preserved_selection = selection.copy()

    def get_preserved_selection(self) -> set:
        """Get preserved selection"""
        return self._preserved_selection.copy()

    def is_active(self) -> bool:
        """Check if filter is active"""
        return self._active


# Create global instance
_drag_cancel_filter = DragCancelFilter()
