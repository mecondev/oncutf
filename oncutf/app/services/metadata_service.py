"""Metadata service for UI isolation from core metadata infrastructure.

This service provides a clean interface for UI components to access metadata-related
functionality without directly depending on core.metadata internals.

Author: Michael Economou
Date: 2026-01-24
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.core.metadata import MetadataStagingManager, UnifiedMetadataManager
    from oncutf.core.metadata.commands import (
        EditMetadataFieldCommand,
        ResetMetadataFieldCommand,
    )


class MetadataService:
    """Service layer for metadata operations.

    Provides UI-friendly access to metadata staging and unified metadata managers.
    Lazy-loads managers on first use to avoid circular dependencies.
    """

    def __init__(self) -> None:
        """Initialize metadata service."""
        self._staging_manager: MetadataStagingManager | None = None
        self._unified_manager: UnifiedMetadataManager | None = None

    @property
    def staging_manager(self) -> MetadataStagingManager:
        """Get metadata staging manager (lazy-loaded)."""
        if self._staging_manager is None:
            from oncutf.core.metadata import get_metadata_staging_manager

            self._staging_manager = get_metadata_staging_manager()
        return self._staging_manager

    @property
    def unified_manager(self) -> UnifiedMetadataManager:
        """Get unified metadata manager (lazy-loaded)."""
        if self._unified_manager is None:
            from oncutf.core.metadata import UnifiedMetadataManager

            self._unified_manager = UnifiedMetadataManager()
        return self._unified_manager

    # Staging Manager Operations
    def get_staged_value(self, file_path: str, key: str) -> Any:
        """Get staged metadata value for a file.

        Args:
            file_path: Path to file
            key: Metadata key to retrieve

        Returns:
            Staged value or None if not staged

        """
        return self.staging_manager.get_staged_value(file_path, key)

    def has_staged_changes(self, file_path: str) -> bool:
        """Check if file has staged metadata changes.

        Args:
            file_path: Path to file

        Returns:
            True if file has staged changes

        """
        return self.staging_manager.has_staged_changes(file_path)

    def clear_staged_changes(self, file_path: str | None = None) -> None:
        """Clear staged metadata changes.

        Args:
            file_path: File to clear changes for (None = all files)

        """
        if file_path is None:
            self.staging_manager.clear()
        else:
            self.staging_manager.clear_file(file_path)

    # Unified Manager Operations
    def get_metadata(self, file_path: str) -> dict[str, Any]:
        """Get all metadata for a file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary of metadata key-value pairs

        """
        return self.unified_manager.get_metadata(file_path)

    def get_field(self, file_path: str, key: str) -> Any:
        """Get specific metadata field value.

        Args:
            file_path: Path to file
            key: Metadata key to retrieve

        Returns:
            Field value or None if not found

        """
        return self.unified_manager.get_field(file_path, key)

    # Command Creation (factory methods)
    def create_edit_command(
        self, file_path: str, key: str, new_value: Any, old_value: Any | None = None
    ) -> EditMetadataFieldCommand:
        """Create edit metadata field command.

        Args:
            file_path: Path to file
            key: Metadata key to edit
            new_value: New value to set
            old_value: Previous value (for undo)

        Returns:
            EditMetadataFieldCommand instance

        """
        from oncutf.core.metadata.commands import EditMetadataFieldCommand

        return EditMetadataFieldCommand(file_path, key, new_value, old_value)

    def create_reset_command(
        self, file_path: str, key: str, staged_value: Any
    ) -> ResetMetadataFieldCommand:
        """Create reset metadata field command.

        Args:
            file_path: Path to file
            key: Metadata key to reset
            staged_value: Staged value to reset

        Returns:
            ResetMetadataFieldCommand instance

        """
        from oncutf.core.metadata.commands import ResetMetadataFieldCommand

        return ResetMetadataFieldCommand(file_path, key, staged_value)


# Singleton instance
_metadata_service: MetadataService | None = None


def get_metadata_service() -> MetadataService:
    """Get singleton metadata service instance.

    Returns:
        MetadataService instance

    """
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = MetadataService()
    return _metadata_service
