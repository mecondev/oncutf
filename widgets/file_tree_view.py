"""
Module: file_tree_view.py

Author: Michael Economou
Date: 2025-05-31

file_tree_view.py
Implements a custom tree view with clean single-item drag implementation.
No reliance on Qt built-in drag system - everything is manual and controlled.
Single item selection only - no multi-selection complexity.
"""

import contextlib
import os

from config import ALLOWED_EXTENSIONS
from core.drag_manager import DragManager
from core.drag_visual_manager import (
    DragVisualManager,
    end_drag_visual,
    start_drag_visual,
    update_drag_feedback_for_widget,
)
from core.modifier_handler import decode_modifiers_to_flags
from core.pyqt_imports import (
    QAbstractItemView,
    QApplication,
    QCursor,
    QEvent,
    QHeaderView,
    QKeyEvent,
    QMouseEvent,
    Qt,
    QTreeView,
    pyqtSignal,
)
from utils.drag_zone_validator import DragZoneValidator
from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_scroll_adjust

logger = get_cached_logger(__name__)


class FileTreeView(QTreeView):
    """
    Custom tree view with clean single-item drag & drop implementation.

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

        # Connect expand/collapse signals for wait cursor
        self.expanded.connect(self._on_item_expanded)
        self.collapsed.connect(self._on_item_collapsed)

        # Initialize file system watcher for drive detection
        self._setup_file_system_watcher()

    def _setup_file_system_watcher(self) -> None:
        """Setup QFileSystemWatcher to detect drive changes."""
        try:
            from PyQt5.QtCore import QFileSystemWatcher, QTimer

            self.file_system_watcher = QFileSystemWatcher()
            self.file_system_watcher.setObjectName("FileTreeViewFSWatcher")

            # Watch common drive locations
            import platform

            if platform.system() == "Windows":
                # Watch root drives on Windows
                import string

                for drive in string.ascii_uppercase:
                    drive_path = f"{drive}:\\"
                    try:
                        if os.path.exists(drive_path):
                            self.file_system_watcher.addPath(drive_path)
                            logger.debug(
                                f"[FileTreeView] Watching drive: {drive_path}",
                                extra={"dev_only": True},
                            )
                    except Exception:
                        pass
            elif platform.system() == "Darwin":
                # Watch /Volumes on macOS
                for watch_path in ["/Volumes"]:
                    try:
                        if os.path.exists(watch_path):
                            self.file_system_watcher.addPath(watch_path)
                            logger.debug(
                                f"[FileTreeView] Watching mount point: {watch_path}",
                                extra={"dev_only": True},
                            )
                    except Exception as e:
                        logger.warning(f"[FileTreeView] Failed to watch {watch_path}: {e}")
            else:
                # Watch /media and /mnt on Linux
                for watch_path in ["/media", "/mnt"]:
                    try:
                        if os.path.exists(watch_path):
                            self.file_system_watcher.addPath(watch_path)
                            logger.debug(
                                f"[FileTreeView] Watching mount point: {watch_path}",
                                extra={"dev_only": True},
                            )
                    except Exception as e:
                        logger.warning(f"[FileTreeView] Failed to watch {watch_path}: {e}")
            # Connect signals
            self.file_system_watcher.directoryChanged.connect(self._on_drive_changed)

            # Debounce timer to avoid multiple rapid updates
            self._drive_change_timer = QTimer()
            self._drive_change_timer.setSingleShot(True)
            self._drive_change_timer.timeout.connect(self._refresh_tree_on_drive_change)
            self._drive_change_timer.setInterval(500)  # Wait 500ms before refreshing

            logger.debug(
                "[FileTreeView] File system watcher initialized",
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.warning(f"[FileTreeView] Failed to setup file system watcher: {e}")
            self.file_system_watcher = None  # Set to None if setup fails

    def closeEvent(self, event) -> None:
        """Clean up resources before closing."""
        try:
            # Stop the drive change timer
            if hasattr(self, "_drive_change_timer") and self._drive_change_timer is not None:
                self._drive_change_timer.stop()
                self._drive_change_timer.blockSignals(True)
                self._drive_change_timer.deleteLater()
                self._drive_change_timer = None

            # Properly cleanup file system watcher
            if hasattr(self, "file_system_watcher") and self.file_system_watcher is not None:
                # Disconnect all signals
                with contextlib.suppress(RuntimeError, TypeError):
                    self.file_system_watcher.directoryChanged.disconnect()

                # Clear all watched paths
                watched_paths = self.file_system_watcher.directories()
                for path in watched_paths:
                    with contextlib.suppress(Exception):
                        self.file_system_watcher.removePath(path)

                # Block signals and delete
                self.file_system_watcher.blockSignals(True)
                self.file_system_watcher.deleteLater()
                self.file_system_watcher = None

            logger.debug("[FileTreeView] Cleanup completed", extra={"dev_only": True})

        except Exception as e:
            logger.error(f"[FileTreeView] Error during cleanup: {e}")

        # Call parent closeEvent
        super().closeEvent(event)

    def _on_drive_changed(self, path: str) -> None:
        """Handle drive changes detected by QFileSystemWatcher."""
        if not hasattr(self, "_drive_change_timer") or self._drive_change_timer is None:
            return

        logger.debug(
            f"[FileTreeView] Drive changed detected: {path}",
            extra={"dev_only": True},
        )

        # Restart debounce timer
        try:
            self._drive_change_timer.stop()
            self._drive_change_timer.start()
        except RuntimeError:
            # Timer was deleted
            pass

    def _refresh_tree_on_drive_change(self) -> None:
        """Refresh the file tree after drive changes."""
        try:
            model = self.model()
            if not model or not hasattr(model, "refresh"):
                logger.debug(
                    "[FileTreeView] Model doesn't support refresh",
                    extra={"dev_only": True},
                )
                return

            # Get current selected path before refresh
            current_path = self.get_selected_path()

            # Refresh the model
            model.refresh()

            # Restore selection if possible
            if current_path and os.path.exists(current_path):
                self.select_path(current_path)
                logger.debug(
                    f"[FileTreeView] Tree refreshed and selection restored: {current_path}",
                    extra={"dev_only": True},
                )
            else:
                logger.debug(
                    "[FileTreeView] Tree refreshed (selection lost)",
                    extra={"dev_only": True},
                )

        except RuntimeError:
            # Widget was deleted
            logger.debug("[FileTreeView] Widget deleted during refresh", extra={"dev_only": True})
        except Exception as e:
            logger.error(f"[FileTreeView] Error refreshing tree on drive change: {e}")

    def _setup_branch_icons(self) -> None:
        """Setup custom branch icons for better cross-platform compatibility."""
        try:
            from utils.icons_loader import get_menu_icon

            # Try to load custom icons
            _closed_icon = get_menu_icon("chevron-right")
            _open_icon = get_menu_icon("chevron-down")

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
            logger.warning(f"[FileTreeView] Failed to setup custom branch icons: {e}")
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
                    f"[FileTreeView] Content exceeds viewport ({content_width} > {viewport_width}) - enabling scrollbar",
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
                    f"[FileTreeView] Cleaned {cursor_count} stuck cursors after drag",
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

        # Start enhanced visual feedback
        visual_manager = DragVisualManager.get_instance()
        drag_type = visual_manager.get_drag_type_from_path(clicked_path)
        start_drag_visual(drag_type, clicked_path, "file_tree")

        # Set initial drag widget for zone validation
        logger.debug(
            "[FileTreeView] Setting up initial drag widget for zone validation",
            extra={"dev_only": True},
        )
        DragZoneValidator.set_initial_drag_widget("file_tree", "FileTreeView")

        # Start drag feedback timer for real-time visual updates using timer_manager
        if hasattr(self, "_drag_feedback_timer_id") and self._drag_feedback_timer_id:
            from utils.timer_manager import cancel_timer

            cancel_timer(self._drag_feedback_timer_id)

        # Schedule repeated updates using timer_manager
        self._start_drag_feedback_loop()

        logger.debug(
            f"[FileTreeView] Custom drag started: {clicked_path}", extra={"dev_only": True}
        )

    def _start_drag_feedback_loop(self):
        """Start repeated drag feedback updates using timer_manager"""
        from utils.timer_manager import schedule_ui_update

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
                f"[FileTreeView] Custom drag ended (cancelled): {self._drag_path}",
                extra={"dev_only": True},
            )
            return

        # Check if we dropped on a valid target (only FileTableView allowed)
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        logger.debug(
            f"[FileTreeView] Widget under cursor: {widget_under_cursor}", extra={"dev_only": True}
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
                    f"[FileTreeView] Checking parent: {parent.__class__.__name__}",
                    extra={"dev_only": True},
                )

                # Check with visual manager
                if visual_manager.is_valid_drop_target(parent, "file_tree"):
                    logger.debug(
                        f"[FileTreeView] Valid drop target found: {parent.__class__.__name__}",
                        extra={"dev_only": True},
                    )
                    self._handle_drop_on_table()
                    valid_drop = True
                    break

                # Also check viewport of FileTableView
                if hasattr(parent, "parent") and parent.parent():
                    if visual_manager.is_valid_drop_target(parent.parent(), "file_tree"):
                        logger.debug(
                            f"[FileTreeView] Valid drop target found via viewport: {parent.parent().__class__.__name__}",
                            extra={"dev_only": True},
                        )
                        self._handle_drop_on_table()
                        valid_drop = True
                        break

                # Check for policy violations
                if parent.__class__.__name__ in ["FileTreeView", "MetadataTreeView"]:
                    logger.debug(
                        f"[FileTreeView] Rejecting drop on {parent.__class__.__name__} (policy violation)",
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
            from utils.timer_manager import cancel_timer

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
                    f"[FileTreeView] Restored folder selection: {self._drag_path}",
                    extra={"dev_only": True},
                )

        logger.debug(
            f"[FileTreeView] Custom drag ended: {self._drag_path} (valid_drop: {valid_drop})",
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
            f"[FileTreeView] Dropped: {self._drag_path} ({action})", extra={"dev_only": True}
        )

    def _is_valid_drag_target(self, path: str) -> bool:
        """Check if path is valid for dragging"""
        if os.path.isdir(path):
            return True

        # For files, check extension
        _, ext = os.path.splitext(path)
        if ext.startswith("."):
            ext = ext[1:].lower()

        if ext not in ALLOWED_EXTENSIONS:
            logger.debug(
                f"[FileTreeView] Skipping drag for non-allowed extension: {ext}",
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
        return

    def _on_item_expanded(self, _index):
        """Handle item expansion with wait cursor for better UX"""
        from utils.cursor_helper import wait_cursor
        from utils.timer_manager import schedule_ui_update

        def show_wait_cursor():
            """Show wait cursor briefly during folder expansion"""
            with wait_cursor():
                # Brief delay to show wait cursor during expansion
                QApplication.processEvents()
                schedule_ui_update(lambda: None, delay=100)  # 100ms delay for visibility

        # Schedule wait cursor for expansion
        schedule_ui_update(show_wait_cursor, delay=1)
        logger.debug("[FileTreeView] Item expanded with wait cursor", extra={"dev_only": True})

    def _on_item_collapsed(self, _index):
        """Handle item collapse - no wait cursor needed as it's instant"""
        logger.debug("[FileTreeView] Item collapsed", extra={"dev_only": True})


# =====================================
# DRAG CANCEL FILTER (Global Instance)
# =====================================


class DragCancelFilter:
    """
    Filter that prevents selection clearing during drag operations.

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
