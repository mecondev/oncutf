"""oncutf.ui.behaviors.metadata_edit package.

Modular implementation of metadata editing behavior.

Components:
- MetadataEditBehavior: Main behavior class (thin orchestrator)
- EditableWidget: Protocol for host widget interface
- FieldDetector: Field type detection utilities
- TreeNavigator: Tree path operations
- EditOperations: Edit dialogs and operations
- RotationHandler: Rotation-specific operations
- ResetHandler: Reset operations
- UndoRedoHandler: Undo/redo support

Author: Michael Economou
Date: 2026-01-01
"""

from oncutf.ui.behaviors.metadata_edit.edit_operations import EditOperations
from oncutf.ui.behaviors.metadata_edit.field_detector import (
    FieldDetector,
    get_date_type_from_field,
    is_date_time_field,
    is_editable_metadata_field,
    normalize_metadata_field_name,
)
from oncutf.ui.behaviors.metadata_edit.metadata_edit_behavior import (
    EditableWidget,
    MetadataEditBehavior,
)
from oncutf.ui.behaviors.metadata_edit.reset_handler import ResetHandler
from oncutf.ui.behaviors.metadata_edit.rotation_handler import RotationHandler
from oncutf.ui.behaviors.metadata_edit.tree_navigator import TreeNavigator
from oncutf.ui.behaviors.metadata_edit.undo_redo_handler import UndoRedoHandler

__all__ = [
    # Handlers
    "EditOperations",
    "EditableWidget",
    "FieldDetector",
    # Main classes
    "MetadataEditBehavior",
    "ResetHandler",
    "RotationHandler",
    "TreeNavigator",
    "UndoRedoHandler",
    "get_date_type_from_field",
    # Utility functions
    "is_date_time_field",
    "is_editable_metadata_field",
    "normalize_metadata_field_name",
]
