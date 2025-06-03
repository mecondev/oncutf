'''
custom_tree_view.py

Author: Michael Economou
Date: 2025-06-05

Implements a custom tree view with modified drag & drop behavior
to prevent drag-out to external applications while preserving
internal drag & drop functionality.
'''

import os
from PyQt5.QtWidgets import QTreeView, QAbstractItemView, QApplication, QFileSystemModel
from PyQt5.QtCore import Qt, QMimeData, QEvent, QPoint, QUrl, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QDrag, QMouseEvent, QKeyEvent
from utils.logger_helper import get_logger
from config import ALLOWED_EXTENSIONS

logger = get_logger(__name__)

class DragCancelFilter(QObject):
    """
    Global event filter to forcefully cancel any lingering drag operations.
    This is installed on QApplication to catch events like Escape key presses
    and mouse clicks that should terminate drag operations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False

    def activate(self):
        """Activate this filter to start monitoring for drag termination events"""
        self._active = True
        logger.debug("[DragFilter] Activated")

    def deactivate(self):
        """Deactivate this filter when drag has properly terminated"""
        self._active = False
        logger.debug("[DragFilter] Deactivated")

    def eventFilter(self, obj, event):
        """Filter events to catch drag termination signals"""
        if not self._active:
            return False

        # Mouse press or release should terminate drag
        if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            logger.debug("[DragFilter] Caught mouse event, forcing drag cleanup")
            self._cleanup_drag()
            return False  # Don't consume the event

        # Escape key should terminate drag
        if event.type() == QEvent.KeyPress:
            key_event = event  # type: QKeyEvent
            if key_event.key() == Qt.Key_Escape:
                logger.debug("[DragFilter] Caught Escape key, forcing drag cleanup")
                self._cleanup_drag()
                return True  # Consume the escape key event

        return False  # Don't consume other events

    def _cleanup_drag(self):
        """Force cleanup of any drag operation"""
        # Restore cursor
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        # Immediately process events to update UI
        QApplication.processEvents()

        # Deactivate filter
        self.deactivate()

# Create a single global instance
_drag_cancel_filter = DragCancelFilter()

class CustomTreeView(QTreeView):
    """
    Custom tree view that prevents drag-out to external applications
    while preserving internal drag & drop functionality.
    """
    # Signal emitted when files are dropped onto the tree view
    files_dropped = pyqtSignal(list, object)  # list of paths and keyboard modifiers

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        # Επιτρέπουμε εσωτερικό drag & drop, όχι μόνο DragOnly
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDropIndicatorShown(True)
        self._drag_start_position = None
        self._dragging = False

        # Install drag cancel filter on application if not already
        app = QApplication.instance()
        if app:
            # Install the global event filter to catch all mouse/key events
            app.installEventFilter(_drag_cancel_filter)

    def mousePressEvent(self, event):
        """Store initial position for drag detection"""
        if event.button() == Qt.LeftButton:
            self._drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Custom implementation to allow internal drag & drop but prevent external"""
        if not (event.buttons() & Qt.LeftButton) or not self._drag_start_position:
            return super().mouseMoveEvent(event)

        # Αν δεν έχουμε κινηθεί αρκετά, δεν ξεκινάμε drag
        if (event.pos() - self._drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return super().mouseMoveEvent(event)

        # Αποτρέπουμε πολλαπλά drag events
        if self._dragging:
            return

        # Ξεκινάμε custom drag αντί για το προεπιλεγμένο
        self._dragging = True
        self.startInternalDrag(event.pos())

        # Explicitly reset drag state and start position
        self._dragging = False
        self._drag_start_position = None

        # Let the parent class handle any remaining mouse move behavior
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events to ensure drag state is properly reset.
        This provides an additional safety measure to prevent lingering drag operations.
        """
        # Reset drag state variables on any mouse release
        self._dragging = False
        self._drag_start_position = None

        # Force UI refresh
        self.viewport().update()

        # Process the event normally
        super().mouseReleaseEvent(event)

        # Process any pending events to ensure UI is updated
        QApplication.processEvents()

        # Force fake mouse release to break Qt drag session (cross-platform) με μικρή καθυστέρηση για να τελειώσει το animation
        def send_fake_release():
            fake_event = QMouseEvent(QEvent.MouseButtonRelease, QPoint(-1, -1), Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
            QApplication.postEvent(self, fake_event)
        QTimer.singleShot(100, send_fake_release)

    def startInternalDrag(self, position):
        """
        Start a drag operation that works within the application.
        Allow dragging folders and files from tree view to other components like file table.
        """
        index = self.indexAt(position)
        if not index.isValid():
            index = self.currentIndex()
            if not index.isValid():
                return

        # Get model and file path of the selected item
        model = self.model()
        if not hasattr(model, 'filePath'):
            logger.warning("Model does not support filePath method")
            return

        path = model.filePath(index)
        if not path:
            return

        # Check if it's a directory or file
        is_dir = os.path.isdir(path)

        # For files, check if it has an allowed extension
        if not is_dir:
            _, ext = os.path.splitext(path)
            if ext.startswith('.'):
                ext = ext[1:].lower()
            if ext not in ALLOWED_EXTENSIONS:
                logger.debug(f"Skipping drag for non-allowed file extension: {ext}")
                return

        # Activate the global drag cancel filter
        _drag_cancel_filter.activate()

        # Create drag object with MIME data
        drag = QDrag(self)
        mimeData = QMimeData()

        # Always include our internal custom MIME type
        mimeData.setData("application/x-oncutf-internal", path.encode())

        # Also include standard formats for internal drops to file table
        # Unlike before, we DO want to allow drag to other internal components
        mimeData.setText(path)
        mimeData.setUrls([QUrl.fromLocalFile(path)])

        # Set the MIME data to the drag object
        drag.setMimeData(mimeData)

        # Reset drag state flag before execution to prevent nested drags
        self._dragging = False

        # Execute the drag with all possible actions to ensure proper termination
        try:
            # Use exec() instead of exec_ (which is Python 2 compatible name)
            # Support all actions to ensure proper termination regardless of target
            result = drag.exec(Qt.CopyAction | Qt.MoveAction | Qt.LinkAction)
            logger.debug(f"Drag completed with result: {result}")
            if result == 0:
                logger.debug("Drag was not accepted by any target, forcing cleanup.")
                self._complete_drag_cleanup()
        except Exception as e:
            logger.error(f"Drag operation failed: {e}")
        finally:
            # Force complete cleanup of any drag state
            while QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()

            # Ensure filter is deactivated
            _drag_cancel_filter.deactivate()

            # Make sure the dragging flag is reset
            self._dragging = False
            self._drag_start_position = None

            # Force repaint to clear any visual artifacts
            self.viewport().update()

            # Force immediate processing of all pending events
            QApplication.processEvents()

        # Create a zero-delay timer to ensure complete cleanup after event loop returns
        QTimer.singleShot(0, self._complete_drag_cleanup)

    def _complete_drag_cleanup(self):
        """
        Additional cleanup method called after drag operation to ensure
        all drag state is completely reset.
        """
        self._dragging = False
        self._drag_start_position = None

        # Restore cursor if needed
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        # Ensure filter is deactivated
        _drag_cancel_filter.deactivate()

        self.viewport().update()
        QApplication.processEvents()

        # Force fake mouse release to break Qt drag session (cross-platform) με μικρή καθυστέρηση για να τελειώσει το animation
        def send_fake_release():
            fake_event = QMouseEvent(QEvent.MouseButtonRelease, QPoint(-1, -1), Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
            QApplication.postEvent(self, fake_event)
        QTimer.singleShot(100, send_fake_release)

    def dragEnterEvent(self, event):
        """
        Override to reject all drag enter events. No drops are allowed on the tree view.
        """
        event.ignore()

    def dragMoveEvent(self, event):
        """
        Override to reject all drag move events. No drops are allowed on the tree view.
        """
        event.ignore()

    def dropEvent(self, event):
        """
        Override to reject all drop events. No drops are allowed on the tree view.
        """
        event.ignore()

    def dragLeaveEvent(self, event):
        logger.debug("[DragDrop] dragLeaveEvent on tree view, forcing cleanup.")
        self._complete_drag_cleanup()
        event.ignore()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Handles key press events in the tree view.
        Pressing Enter or Return triggers the folder load action (like Select Folder).
        """
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if hasattr(self.parent(), "handle_folder_select"):
                self.parent().handle_folder_select()
                return
        super().keyPressEvent(event)

