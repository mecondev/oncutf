from typing import List, Optional, Set

from core.unified_file_loader import UnifiedFileLoader
from utils.logger_factory import get_cached_logger

from .file_loading_dialog import FileLoadingDialog
from .file_loading_progress_dialog import FileLoadingProgressDialog

logger = get_cached_logger(__name__)

class FileLoadManager:
    """
    Manages file loading operations with progress tracking and cancellation support.
    Uses a worker thread to prevent UI freezing during file loading.
    Now supports both FileLoadingDialog and UnifiedFileLoader for different scenarios.
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.allowed_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ts', '.mts', '.m2ts'}

        # Initialize unified file loader for advanced scenarios
        self.unified_loader = UnifiedFileLoader(parent)

    def load_files_from_paths(self, paths: List[str], on_files_loaded: Optional[callable] = None) -> None:
        """
        Load files from the given paths using a worker thread.
        Shows a progress dialog and allows cancellation.
        """
        # Use the new ProgressDialog-based file loading dialog
        dialog = FileLoadingProgressDialog(self.parent, on_files_loaded)
        dialog.load_files(paths, self.allowed_extensions)
        dialog.exec_()

    def load_files_with_unified_loader(self, paths: List[str], on_files_loaded: Optional[callable] = None) -> None:
        """
        Load files using UnifiedFileLoader for automatic mode selection.
        Alternative to the standard FileLoadingDialog approach.
        """
        logger.info(f"[FileLoadManager] load_files_with_unified_loader: {len(paths)} paths")

        self.unified_loader.load_files(
            paths,
            completion_callback=on_files_loaded
        )

    def load_single_item_from_drop(self, path: str, modifiers: Optional[Set[str]] = None) -> None:
        """
        Handle loading a single item from drag & drop.
        Shows progress dialog and allows cancellation.
        """
        self.load_files_from_paths([path])

    def set_allowed_extensions(self, extensions: Set[str]) -> None:
        """Update the set of allowed file extensions."""
        self.allowed_extensions = extensions
        if hasattr(self.unified_loader, 'allowed_extensions'):
            self.unified_loader.allowed_extensions = extensions
