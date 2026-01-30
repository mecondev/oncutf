"""Metadata service for UI isolation from core metadata infrastructure.

This service provides a clean interface for UI components to access metadata-related
functionality without directly depending on core.metadata internals.

Author: Michael Economou
Date: 2026-01-24
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.core.metadata import MetadataStagingManager
    from oncutf.core.metadata.commands import (
        EditMetadataFieldCommand,
        ResetMetadataFieldCommand,
    )
    from oncutf.core.metadata.unified_metadata_protocol import (
        UnifiedMetadataManagerProtocol,
    )


class MetadataService:
    """Service layer for metadata operations.

    Provides UI-friendly access to metadata staging and unified metadata managers.
    Lazy-loads managers on first use to avoid circular dependencies.
    """

    def __init__(self, unified_manager: UnifiedMetadataManagerProtocol) -> None:
        """Initialize metadata service.

        Args:
            unified_manager: Unified metadata manager instance (required)

        """
        self._staging_manager: MetadataStagingManager | None = None
        self._unified_manager: UnifiedMetadataManagerProtocol = unified_manager

    @property
    def staging_manager(self) -> MetadataStagingManager:
        """Get metadata staging manager (lazy-loaded)."""
        if self._staging_manager is None:
            from oncutf.core.metadata import get_metadata_staging_manager

            manager = get_metadata_staging_manager()
            if manager is None:
                raise RuntimeError("MetadataStagingManager not initialized")
            self._staging_manager = manager
        return self._staging_manager

    @property
    def unified_manager(self) -> UnifiedMetadataManagerProtocol:
        """Get unified metadata manager."""
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
        staged_changes = self.staging_manager.get_staged_changes(file_path)
        return staged_changes.get(key) if staged_changes else None

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
            self.staging_manager.clear_all()
        else:
            self.staging_manager.clear_staged_changes(file_path)

    # Unified Manager Operations
    def get_metadata(self, file_path: str) -> dict[str, Any]:
        """Get all metadata for a file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary of metadata key-value pairs

        """
        # TODO: Implement when UnifiedMetadataManager API is finalized
        # return self.unified_manager.get_metadata(file_path)
        return {}

    def get_field(self, file_path: str, key: str) -> Any:
        """Get specific metadata field value.

        Args:
            file_path: Path to file
            key: Metadata key to retrieve

        Returns:
            Field value or None if not found

        """
        # TODO: Implement when UnifiedMetadataManager API is finalized
        # return self.unified_manager.get_field(file_path, key)
        return None

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
        self,
        file_path: str,
        key: str,
        staged_value: Any,
        original_value: Any | None = None,
    ) -> ResetMetadataFieldCommand:
        """Create reset metadata field command.

        Args:
            file_path: Path to file
            key: Metadata key to reset
            staged_value: Staged value to reset
            original_value: Original value before staging

        Returns:
            ResetMetadataFieldCommand instance

        """
        from oncutf.core.metadata.commands import ResetMetadataFieldCommand

        return ResetMetadataFieldCommand(file_path, key, staged_value, original_value)


# Singleton instance
_metadata_service: MetadataService | None = None


def get_metadata_service(
    unified_manager: UnifiedMetadataManagerProtocol | None = None,
) -> MetadataService:
    """Get singleton metadata service instance.

    Args:
        unified_manager: Unified metadata manager instance.
            Required on first call, optional on subsequent calls.
            If not provided on first call, raises RuntimeError.

    Returns:
        MetadataService instance

    Raises:
        RuntimeError: If called for the first time without unified_manager

    """
    global _metadata_service
    if _metadata_service is None:
        if unified_manager is None:
            raise RuntimeError(
                "UnifiedMetadataManager must be provided on first call to get_metadata_service(). "
                "Ensure bootstrap_orchestrator initializes the service properly."
            )
        _metadata_service = MetadataService(unified_manager)
    return _metadata_service
