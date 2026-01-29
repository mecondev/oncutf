"""File loading UI update service.

Author: Michael Economou
Date: 2026-01-26

Adapter service for file loading UI updates using port-adapter pattern.
"""

from typing import TYPE_CHECKING, cast

from oncutf.app.state.context import AppContext

if TYPE_CHECKING:
    from oncutf.app.ports.file_load_ui import FileLoadUIPort
    from oncutf.models.file_item import FileItem


def update_file_load_ui(items: list["FileItem"], clear: bool = True) -> None:
    """Update file model and UI after loading files.

    Delegates to registered FileLoadUIPort adapter.

    Args:
        items: List of FileItem objects to load
        clear: Whether to clear existing files (True) or merge (False)

    Raises:
        RuntimeError: If no FileLoadUIPort adapter is registered

    """
    ctx = AppContext.get_instance()
    if not ctx.has_manager("file_load_ui"):
        raise RuntimeError(
            "FileLoadUIPort adapter not registered. "
            "Call AppContext.register_manager('file_load_ui', adapter) during initialization."
        )

    adapter = cast("FileLoadUIPort", ctx.get_manager("file_load_ui"))
    adapter.update_model_and_ui(items, clear)
