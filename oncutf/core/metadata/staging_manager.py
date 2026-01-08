"""Module: metadata_staging_manager.py

Author: Michael Economou
Date: 2025-11-25

Manages staged metadata changes that have not yet been saved to disk.
Acts as the single source of truth for pending modifications, decoupling
the UI from the save logic.
"""

from oncutf.core.pyqt_imports import QObject, pyqtSignal
from oncutf.utils.filesystem.path_normalizer import normalize_path
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataStagingManager(QObject):
    """Manages staged metadata changes.

    This class maintains a registry of all metadata changes that have been
    made by the user but not yet saved to disk. It provides methods to
    stage, unstage, and retrieve changes, emitting signals to update the UI.
    """

    # Signals
    # Emitted when a specific field is staged: (file_path, key, value)
    change_staged = pyqtSignal(str, str, str)
    # Emitted when a specific field is unstaged/cleared: (file_path, key)
    change_unstaged = pyqtSignal(str, str)
    # Emitted when all changes for a file are cleared: (file_path)
    file_cleared = pyqtSignal(str)
    # Emitted when all changes are cleared
    all_cleared = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize the staging manager with empty change tracking."""
        super().__init__(parent)
        # Structure: { normalized_file_path: { key: value } }
        self._staged_changes: dict[str, dict[str, str]] = {}
        logger.debug("MetadataStagingManager initialized", extra={"dev_only": True})

    def stage_change(self, file_path: str, key: str, value: str) -> None:
        """Stage a metadata change for a file.

        Args:
            file_path: The full path to the file.
            key: The metadata key (e.g., "Rotation", "XMP:Title").
            value: The new value.

        """
        norm_path = normalize_path(file_path)

        if norm_path not in self._staged_changes:
            self._staged_changes[norm_path] = {}

        self._staged_changes[norm_path][key] = str(value)

        logger.info("[Staging] Staged change for %s: %s = %s", file_path, key, value)

        self.change_staged.emit(file_path, key, str(value))

    def get_staged_changes(self, file_path: str) -> dict[str, str]:
        """Get all staged changes for a specific file.

        Args:
            file_path: The full path to the file.

        Returns:
            Dictionary of {key: value} for staged changes.

        """
        norm_path = normalize_path(file_path)
        return self._staged_changes.get(norm_path, {}).copy()

    def get_all_staged_changes(self) -> dict[str, dict[str, str]]:
        """Get all staged changes for all files.

        Returns:
            Dictionary of {normalized_path: {key: value}}.

        """
        return {k: v.copy() for k, v in self._staged_changes.items()}

    def has_staged_changes(self, file_path: str) -> bool:
        """Check if a file has any staged changes."""
        norm_path = normalize_path(file_path)
        return norm_path in self._staged_changes and bool(self._staged_changes[norm_path])

    def clear_staged_change(self, file_path: str, key: str) -> None:
        """Clear a specific staged change for a file.

        Args:
            file_path: The full path to the file.
            key: The metadata key to clear.

        """
        norm_path = normalize_path(file_path)
        if norm_path in self._staged_changes and key in self._staged_changes[norm_path]:
            del self._staged_changes[norm_path][key]
            logger.debug(
                "[Staging] Cleared specific change for %s: %s",
                file_path,
                key,
                extra={"dev_only": True},
            )

            # Remove file entry if no more changes
            if not self._staged_changes[norm_path]:
                del self._staged_changes[norm_path]
                self.file_cleared.emit(file_path)
            else:
                self.change_unstaged.emit(file_path, key)

    def clear_staged_changes(self, file_path: str) -> None:
        """Clear all staged changes for a specific file (e.g., after save).

        Args:
            file_path: The full path to the file.

        """
        norm_path = normalize_path(file_path)
        if norm_path in self._staged_changes:
            del self._staged_changes[norm_path]
            logger.debug("[Staging] Cleared changes for %s", file_path, extra={"dev_only": True})
            self.file_cleared.emit(file_path)

    def clear_all(self) -> None:
        """Clear all staged changes."""
        self._staged_changes.clear()
        logger.debug("[Staging] Cleared all staged changes", extra={"dev_only": True})
        self.all_cleared.emit()

    def has_any_staged_changes(self) -> bool:
        """Check if there are any staged changes across all files."""
        return bool(self._staged_changes)

    def get_modified_files(self) -> list[str]:
        """Get list of normalized paths for files with staged changes."""
        return list(self._staged_changes.keys())


# Global instance
_metadata_staging_manager_instance = None


def get_metadata_staging_manager() -> MetadataStagingManager | None:
    """Get the global MetadataStagingManager instance."""
    return _metadata_staging_manager_instance


def set_metadata_staging_manager(manager: MetadataStagingManager) -> None:
    """Set the global MetadataStagingManager instance."""
    global _metadata_staging_manager_instance
    _metadata_staging_manager_instance = manager
