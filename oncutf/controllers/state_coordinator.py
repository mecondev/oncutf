"""
Module: state_coordinator.py

Author: Michael Economou
Date: 2025-12-16

Central coordinator for state changes with signal-based notifications.
Part of Phase 2: State Management Fix.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.core.pyqt_imports import QObject, pyqtSignal

if TYPE_CHECKING:
    from oncutf.core.file_store import FileStore
    from oncutf.models.file_item import FileItem


class StateCoordinator(QObject):
    """
    Central coordinator for state changes.
    
    Emits signals when state changes occur, allowing components to react
    without tight coupling. This is the single source of truth for state
    change notifications.
    
    Signals:
        files_changed: Emitted when file list changes (list[FileItem])
        selection_changed: Emitted when selection changes (set of indices)
        preview_invalidated: Emitted when preview needs refresh
        metadata_changed: Emitted when metadata cache changes (file_path: str)
    """
    
    # Signal definitions
    files_changed = pyqtSignal(list)  # list[FileItem]
    selection_changed = pyqtSignal(set)  # set of row indices
    preview_invalidated = pyqtSignal()
    metadata_changed = pyqtSignal(str)  # file_path
    
    def __init__(self, file_store: FileStore) -> None:
        """
        Initialize StateCoordinator.
        
        Args:
            file_store: The FileStore instance to coordinate
        """
        super().__init__()
        self._file_store = file_store
    
    def notify_files_changed(self, files: list[FileItem]) -> None:
        """
        Notify that the file list has changed.
        
        This will:
        1. Update the FileStore
        2. Emit files_changed signal
        3. Invalidate preview (since file list changed)
        
        Args:
            files: New list of FileItem objects
        """
        # Update file store
        self._file_store.set_loaded_files(files)
        
        # Emit signals
        self.files_changed.emit(files)
        self.preview_invalidated.emit()
    
    def notify_selection_changed(self, selected_indices: set[int]) -> None:
        """
        Notify that the selection has changed.
        
        Args:
            selected_indices: Set of selected row indices
        """
        self.selection_changed.emit(selected_indices)
    
    def notify_preview_invalidated(self) -> None:
        """
        Notify that the preview needs to be refreshed.
        
        This should be called when:
        - Rename settings change
        - File order changes
        - Filters change
        """
        self.preview_invalidated.emit()
    
    def notify_metadata_changed(self, file_path: str) -> None:
        """
        Notify that metadata for a file has changed.
        
        Args:
            file_path: Path of the file whose metadata changed
        """
        self.metadata_changed.emit(file_path)
        # Metadata changes might affect preview (e.g., metadata module)
        self.preview_invalidated.emit()
    
    def get_file_store(self) -> FileStore:
        """Get the managed FileStore instance."""
        return self._file_store
