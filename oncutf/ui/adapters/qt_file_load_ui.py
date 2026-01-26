"""Qt adapter for file loading UI updates.

Author: Michael Economou
Date: 2026-01-26

Adapts FileLoadUIService to FileLoadUIPort protocol.
"""

from typing import TYPE_CHECKING, Any

from oncutf.ui.managers.file_load_ui_service import FileLoadUIService

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem


class QtFileLoadUIAdapter:
    """Adapter wrapping FileLoadUIService for FileLoadUIPort protocol."""

    def __init__(self, main_window: Any) -> None:
        """Initialize adapter with main window reference.

        Args:
            main_window: MainWindow instance for UI access

        """
        self._service = FileLoadUIService(main_window)

    def update_model_and_ui(self, items: list["FileItem"], clear: bool = True) -> None:
        """Update file model and all UI elements after loading files.

        Delegates to FileLoadUIService.

        Args:
            items: List of FileItem objects to load
            clear: Whether to clear existing files (True) or merge (False)

        """
        self._service.update_model_and_ui(items, clear)
