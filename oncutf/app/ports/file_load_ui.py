"""File loading UI update port.

Author: Michael Economou
Date: 2026-01-26

Protocol for UI updates after file loading operations.
Decouples core file loading logic from UI refresh operations.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem


class FileLoadUIPort(Protocol):
    """Protocol for file loading UI updates.

    Implementations handle:
    - Model updates (file_model.set_files)
    - FileStore synchronization
    - UI widget refreshes (placeholder, labels, preview tables)
    - Metadata tree coordination
    """

    def update_model_and_ui(self, items: list["FileItem"], clear: bool = True) -> None:
        """Update file model and all UI elements after loading files.

        Args:
            items: List of FileItem objects to load
            clear: Whether to clear existing files (True) or merge (False)

        """
        ...
