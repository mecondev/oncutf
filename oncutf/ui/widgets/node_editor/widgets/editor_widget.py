"""Node editor widget combining scene and view into embeddable canvas.

This module provides NodeEditorWidget, a complete node editing interface
that can be embedded in applications. It combines Scene and QDMGraphicsView
with file operations and state management.

The widget handles:
    - Scene creation and management
    - File load/save operations
    - Undo/redo state queries
    - Selection management

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox, QVBoxLayout, QWidget

from oncutf.ui.widgets.node_editor.core.scene import Scene
from oncutf.ui.widgets.node_editor.persistence.scene_json import (
    InvalidFileError,
    load_scene_from_file,
    save_scene_to_file,
)
from oncutf.ui.widgets.node_editor.utils.helpers import dump_exception

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QGraphicsItem

logger = logging.getLogger(__name__)


class NodeEditorWidget(QWidget):
    """Embeddable node editor canvas widget.

    Combines Scene and QDMGraphicsView into a single widget for
    embedding in applications. Provides file operations and
    state management.

    Attributes:
        scene_class: Scene class to instantiate.
        graphics_view_class: View class to instantiate.
        scene: Active Scene instance.
        view: Active QDMGraphicsView instance.
        filename: Current file path, or None for unsaved.
    """

    scene_class = Scene
    graphics_view_class = None

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize node editor widget.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self.filename: str | None = None

        self.init_ui()

    def init_ui(self) -> None:
        """Set up layout with scene and view."""
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.scene = self.__class__.scene_class()

        from oncutf.ui.widgets.node_editor.graphics.view import QDMGraphicsView

        if self.__class__.graphics_view_class is None:
            self.__class__.graphics_view_class = QDMGraphicsView

        self.view = self.__class__.graphics_view_class(self.scene.graphics_scene, self)
        self.layout.addWidget(self.view)

    def is_modified(self) -> bool:
        """Check if scene has unsaved changes.

        Returns:
            True if scene has been modified.
        """
        return self.scene.has_been_modified

    def is_filename_set(self) -> bool:
        """Check if file has been saved.

        Returns:
            True if filename is set, False for new graphs.
        """
        return self.filename is not None

    def get_user_friendly_filename(self) -> str:
        """Get display name with modification indicator.

        Returns:
            Filename with asterisk if modified, or 'New Graph'.
        """
        name = os.path.basename(self.filename) if self.is_filename_set() else "New Graph"
        return name + ("*" if self.is_modified() else "")

    def get_selected_items(self) -> list[QGraphicsItem]:
        """Get currently selected graphics items.

        Returns:
            List of selected QGraphicsItem instances.
        """
        return self.scene.get_selected_items()

    def has_selected_items(self) -> bool:
        """Check if any items are selected.

        Returns:
            True if selection is non-empty.
        """
        return self.get_selected_items() != []

    def can_undo(self) -> bool:
        """Check if undo operation is available.

        Returns:
            True if undo stack has entries.
        """
        return self.scene.history.can_undo()

    def can_redo(self) -> bool:
        """Check if redo operation is available.

        Returns:
            True if redo stack has entries.
        """
        return self.scene.history.can_redo()

    def file_new(self) -> None:
        """Create new empty scene.

        Clears current content and resets history.
        """
        self.scene.clear()
        self.filename = None
        self.scene.history.clear()
        self.scene.history.store_initial_history_stamp()

    def file_load(self, filename: str) -> bool:
        """Load graph from JSON file.

        Args:
            filename: Path to file to load.

        Returns:
            True if load succeeded, False on error.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            load_scene_from_file(self.scene, filename)
            self.filename = filename
            self.scene.history.clear()
            self.scene.history.store_initial_history_stamp()
            return True
        except FileNotFoundError as e:
            dump_exception(e)
            QMessageBox.warning(
                self, f"Error loading {os.path.basename(filename)}", str(e).replace("[Errno 2]", "")
            )
            return False
        except InvalidFileError as e:
            dump_exception(e)
            QMessageBox.warning(self, f"Error loading {os.path.basename(filename)}", str(e))
            return False
        finally:
            QApplication.restoreOverrideCursor()

    def file_save(self, filename: str | None = None) -> bool:
        """Save graph to JSON file.

        Args:
            filename: Path to save to. Uses current filename if None.

        Returns:
            True if save succeeded.
        """
        if filename is not None:
            self.filename = filename

        QApplication.setOverrideCursor(Qt.WaitCursor)
        save_scene_to_file(self.scene, self.filename)
        QApplication.restoreOverrideCursor()

        return True
