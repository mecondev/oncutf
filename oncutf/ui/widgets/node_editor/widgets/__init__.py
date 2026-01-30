"""Widgets module providing reusable Qt widgets for node editor applications.

This module contains Qt widgets that can be embedded in applications:

Classes:
    QDMNodeContentWidget: Base class for customizable node content areas.
    QDMTextEdit: Text editor that integrates with view editing state.
    NodeEditorWidget: Complete canvas widget with scene and view.
    NodeEditorWindow: Full application window with menus and toolbar.

The NodeEditorWidget provides a ready-to-use node editing canvas,
while NodeEditorWindow adds complete application scaffolding with
file operations and standard editing commands.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from oncutf.ui.widgets.node_editor.widgets.content_widget import (
    QDMNodeContentWidget,
    QDMTextEdit,
)
from oncutf.ui.widgets.node_editor.widgets.editor_widget import NodeEditorWidget
from oncutf.ui.widgets.node_editor.widgets.editor_window import NodeEditorWindow

__all__ = [
    "NodeEditorWidget",
    "NodeEditorWindow",
    "QDMNodeContentWidget",
    "QDMTextEdit",
]
