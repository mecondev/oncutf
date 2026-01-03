"""Main application window for node editor.

This module provides NodeEditorWindow, a complete QMainWindow with
menus, actions, status bar, and settings persistence. It wraps
NodeEditorWidget to provide a ready-to-use application.

Features:
    - File menu: New, Open, Save, Save As, Exit
    - Edit menu: Undo, Redo, Cut, Copy, Paste, Delete
    - Status bar with mouse position display
    - Window title with filename and modification indicator
    - Persistent window geometry settings

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

import json
import os

from PyQt5.QtCore import QPoint, QSettings, QSize
from PyQt5.QtWidgets import QAction, QApplication, QFileDialog, QLabel, QMainWindow, QMessageBox

from oncutf.ui.widgets.node_editor.widgets.editor_widget import NodeEditorWidget


class NodeEditorWindow(QMainWindow):
    """Complete application window for node editing.

    Provides full application interface with menus, status bar,
    and settings persistence. Subclass to customize behavior
    or add additional menus.

    Attributes:
        node_editor_widget_class: Widget class for central editor.
        nodeeditor: Active NodeEditorWidget instance.
        name_company: Company name for QSettings storage.
        name_product: Product name for QSettings storage.
    """

    node_editor_widget_class = NodeEditorWidget

    def __init__(self) -> None:
        """Initialize main window with menus and central widget."""
        super().__init__()

        self.name_company = 'oncut'
        self.name_product = 'NodeEditor'

        self.init_ui()

    def init_ui(self) -> None:
        """Set up window with actions, menus, and central widget."""
        self.create_actions()
        self.create_menus()

        self.nodeeditor = self.__class__.node_editor_widget_class(self)
        self.nodeeditor.scene.add_has_been_modified_listener(self.set_title)
        self.setCentralWidget(self.nodeeditor)

        self.create_status_bar()

        self.set_title()
        self.show()

    def sizeHint(self) -> QSize:
        """Get recommended window size.

        Returns:
            QSize with default dimensions.
        """
        return QSize(800, 600)

    def create_status_bar(self) -> None:
        """Set up status bar with mouse position label."""
        self.statusBar().showMessage("")
        self.status_mouse_pos = QLabel("")
        self.statusBar().addPermanentWidget(self.status_mouse_pos)
        self.nodeeditor.view.scene_pos_changed.connect(self.on_scene_pos_changed)

    def create_actions(self) -> None:
        """Create QAction instances for menus."""
        self.actNew = QAction(
            '&New', self, shortcut='Ctrl+N',
            statusTip="Create new graph", triggered=self.on_file_new
        )
        self.actOpen = QAction(
            '&Open', self, shortcut='Ctrl+O',
            statusTip="Open file", triggered=self.on_file_open
        )
        self.actSave = QAction(
            '&Save', self, shortcut='Ctrl+S',
            statusTip="Save file", triggered=self.on_file_save
        )
        self.actSaveAs = QAction(
            'Save &As...', self, shortcut='Ctrl+Shift+S',
            statusTip="Save file as...", triggered=self.on_file_save_as
        )
        self.actExit = QAction(
            'E&xit', self, shortcut='Ctrl+Q',
            statusTip="Exit application", triggered=self.close
        )

        self.actUndo = QAction(
            '&Undo', self, shortcut='Ctrl+Z',
            statusTip="Undo last operation", triggered=self.on_edit_undo
        )
        self.actRedo = QAction(
            '&Redo', self, shortcut='Ctrl+Shift+Z',
            statusTip="Redo last operation", triggered=self.on_edit_redo
        )
        self.actCut = QAction(
            'Cu&t', self, shortcut='Ctrl+X',
            statusTip="Cut to clipboard", triggered=self.on_edit_cut
        )
        self.actCopy = QAction(
            '&Copy', self, shortcut='Ctrl+C',
            statusTip="Copy to clipboard", triggered=self.on_edit_copy
        )
        self.actPaste = QAction(
            '&Paste', self, shortcut='Ctrl+V',
            statusTip="Paste from clipboard", triggered=self.on_edit_paste
        )
        self.actDelete = QAction(
            '&Delete', self, shortcut='Del',
            statusTip="Delete selected items", triggered=self.on_edit_delete
        )

    def create_menus(self) -> None:
        """Create File and Edit menus."""
        self.create_file_menu()
        self.create_edit_menu()

    def create_file_menu(self) -> None:
        """Populate File menu with actions."""
        menubar = self.menuBar()
        self.fileMenu = menubar.addMenu('&File')
        self.fileMenu.addAction(self.actNew)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.actOpen)
        self.fileMenu.addAction(self.actSave)
        self.fileMenu.addAction(self.actSaveAs)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.actExit)

    def create_edit_menu(self) -> None:
        """Populate Edit menu with actions."""
        menubar = self.menuBar()
        self.editMenu = menubar.addMenu('&Edit')
        self.editMenu.addAction(self.actUndo)
        self.editMenu.addAction(self.actRedo)
        self.editMenu.addSeparator()
        self.editMenu.addAction(self.actCut)
        self.editMenu.addAction(self.actCopy)
        self.editMenu.addAction(self.actPaste)
        self.editMenu.addSeparator()
        self.editMenu.addAction(self.actDelete)

    def set_title(self) -> None:
        """Update window title with current filename."""
        title = "Node Editor - "
        title += self.get_current_node_editor_widget().get_user_friendly_filename()
        self.setWindowTitle(title)

    def closeEvent(self, event) -> None:
        """Prompt to save before closing.

        Args:
            event: Qt close event.
        """
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def is_modified(self) -> bool:
        """Check if current scene has unsaved changes.

        Returns:
            True if scene is modified.
        """
        nodeeditor = self.get_current_node_editor_widget()
        if nodeeditor is None:
            return False
        return nodeeditor.is_modified()

    def get_current_node_editor_widget(self) -> NodeEditorWidget:
        """Get the active node editor widget.

        Returns:
            NodeEditorWidget instance.
        """
        return self.centralWidget()

    def maybe_save(self) -> bool:
        """Prompt user to save if modified.

        Returns:
            True to continue, False to cancel operation.
        """
        if not self.is_modified():
            return True

        res = QMessageBox.warning(
            self, "About to lose your work?",
            "The document has been modified.\n Do you want to save your changes?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )

        if res == QMessageBox.Save:
            return self.on_file_save()
        elif res == QMessageBox.Cancel:
            return False

        return True

    def on_scene_pos_changed(self, x: int, y: int) -> None:
        """Update status bar with mouse position.

        Args:
            x: Scene X coordinate.
            y: Scene Y coordinate.
        """
        self.status_mouse_pos.setText(f"Scene Pos: [{x}, {y}]")

    def get_file_dialog_directory(self) -> str:
        """Get starting directory for file dialogs.

        Returns:
            Directory path string.
        """
        return ''

    def get_file_dialog_filter(self) -> str:
        """Get file type filter for dialogs.

        Returns:
            Filter string for QFileDialog.
        """
        return 'Graph (*.json);;All files (*)'

    def on_file_new(self) -> None:
        """Create new empty graph after save prompt."""
        current_nodeeditor = self.get_current_node_editor_widget()
        if current_nodeeditor and self.maybe_save():
            current_nodeeditor.file_new()
            self.set_title()

    def on_file_open(self) -> None:
        """Open file dialog and load selected graph."""
        current_nodeeditor = self.get_current_node_editor_widget()
        if not current_nodeeditor:
            return

        if self.maybe_save():
            fname, filter = QFileDialog.getOpenFileName(
                self, 'Open graph from file',
                self.get_file_dialog_directory(),
                self.get_file_dialog_filter()
            )
            if fname != '' and os.path.isfile(fname):
                current_nodeeditor.file_load(fname)
                self.set_title()

    def on_file_save(self) -> bool:
        """Save to current file or prompt for filename.

        Returns:
            True if save succeeded.
        """
        current_nodeeditor = self.get_current_node_editor_widget()
        if current_nodeeditor is not None:
            if not current_nodeeditor.is_filename_set():
                return self.on_file_save_as()

            current_nodeeditor.file_save()
            self.statusBar().showMessage(
                f"Successfully saved {current_nodeeditor.filename}", 5000
            )

            if hasattr(current_nodeeditor, "set_title"):
                current_nodeeditor.set_title()
            else:
                self.set_title()

            return True

        return False

    def on_file_save_as(self) -> bool:
        """Prompt for filename and save graph.

        Returns:
            True if save succeeded.
        """
        current_nodeeditor = self.get_current_node_editor_widget()
        if current_nodeeditor is not None:
            fname, filter = QFileDialog.getSaveFileName(
                self, 'Save graph to file',
                self.get_file_dialog_directory(),
                self.get_file_dialog_filter()
            )
            if fname == '':
                return False

            self.on_before_save_as(current_nodeeditor, fname)
            current_nodeeditor.file_save(fname)
            self.statusBar().showMessage(
                f"Successfully saved as {current_nodeeditor.filename}", 5000
            )

            if hasattr(current_nodeeditor, "set_title"):
                current_nodeeditor.set_title()
            else:
                self.set_title()

            return True

        return False

    def on_before_save_as(self, current_nodeeditor: NodeEditorWidget, filename: str) -> None:
        """Hook called before Save As completes.

        Override to perform actions before saving with new name.

        Args:
            current_nodeeditor: Widget being saved.
            filename: New filename path.
        """

    def on_edit_undo(self) -> None:
        """Undo last operation."""
        if self.get_current_node_editor_widget():
            self.get_current_node_editor_widget().scene.history.undo()

    def on_edit_redo(self) -> None:
        """Redo last undone operation."""
        if self.get_current_node_editor_widget():
            self.get_current_node_editor_widget().scene.history.redo()

    def on_edit_delete(self) -> None:
        """Delete selected items."""
        if self.get_current_node_editor_widget():
            self.get_current_node_editor_widget().view.delete_selected()

    def on_edit_cut(self) -> None:
        """Cut selected items to clipboard."""
        if self.get_current_node_editor_widget():
            data = self.get_current_node_editor_widget().scene.clipboard.serialize_selected(delete=True)
            str_data = json.dumps(data, indent=4)
            QApplication.instance().clipboard().setText(str_data)

    def on_edit_copy(self) -> None:
        """Copy selected items to clipboard."""
        if self.get_current_node_editor_widget():
            data = self.get_current_node_editor_widget().scene.clipboard.serialize_selected(delete=False)
            str_data = json.dumps(data, indent=4)
            QApplication.instance().clipboard().setText(str_data)

    def on_edit_paste(self) -> None:
        """Paste items from clipboard."""
        if self.get_current_node_editor_widget():
            raw_data = QApplication.instance().clipboard().text()

            try:
                data = json.loads(raw_data)
            except ValueError:
                return

            if 'nodes' not in data:
                return

            self.get_current_node_editor_widget().scene.clipboard.deserialize_from_clipboard(data)

    def read_settings(self) -> None:
        """Restore window geometry from persistent settings."""
        settings = QSettings(self.name_company, self.name_product)
        pos = settings.value('pos', QPoint(200, 200))
        size = settings.value('size', QSize(400, 400))
        self.move(pos)
        self.resize(size)

    def write_settings(self) -> None:
        """Save window geometry to persistent settings."""
        settings = QSettings(self.name_company, self.name_product)
        settings.setValue('pos', self.pos())
        settings.setValue('size', self.size())
