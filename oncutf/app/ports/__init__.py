"""Ports - Protocol interfaces for infrastructure dependencies.

Define interfaces that infrastructure layer implements:
- MetadataProvider
- HashProvider
- Filesystem
- CacheStore
- DatabaseRepository
- UI Dialogs and Updates
- Drag State Management

Author: Michael Economou
Date: 2026-01-22
"""

from oncutf.app.ports.conflict_resolution import ConflictResolutionPort
from oncutf.app.ports.drag_state import DragStatePort
from oncutf.app.ports.metadata import CacheStore, MetadataProvider, MetadataWriter
from oncutf.app.ports.metadata_editing import MetadataEditPort
from oncutf.app.ports.results_display import ResultsDisplayPort
from oncutf.app.ports.ui_update import UIUpdatePort
from oncutf.app.ports.user_interaction import ProgressReporter, StatusReporter, UserDialogPort

__all__ = [
    "CacheStore",
    "ConflictResolutionPort",
    "DragStatePort",
    "MetadataEditPort",
    "MetadataProvider",
    "MetadataWriter",
    "ProgressReporter",
    "ResultsDisplayPort",
    "StatusReporter",
    "UIUpdatePort",
    "UserDialogPort",
]
