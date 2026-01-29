"""Module: unified_metadata_protocol.py.

Author: Michael Economou
Date: 2026-01-30

Protocol definition for UnifiedMetadataManager.

This module defines the interface (Protocol) for the metadata manager,
allowing controllers to depend on abstractions rather than concrete
implementations. The concrete implementation (with Qt/PyQt dependencies)
remains in oncutf.ui.managers.metadata_unified_manager.

Usage:
    Controllers should use this protocol for type hints::

        if TYPE_CHECKING:
            from oncutf.core.metadata.unified_metadata_protocol import (
                UnifiedMetadataManagerProtocol,
            )

        class MetadataController:
            def __init__(self, metadata_manager: "UnifiedMetadataManagerProtocol"):
                ...
"""

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem


@runtime_checkable
class UnifiedMetadataManagerProtocol(Protocol):
    """Protocol for unified metadata management operations.

    Defines the interface that MetadataController needs for metadata operations.
    Implemented by oncutf.ui.managers.metadata_unified_manager.UnifiedMetadataManager.

    The concrete implementation may include Qt-specific features (signals, etc.)
    but this protocol defines only the method signatures needed by controllers.
    """

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def structured(self) -> Any:
        """Get the structured metadata manager."""
        ...

    # -------------------------------------------------------------------------
    # Loading State
    # -------------------------------------------------------------------------

    def is_loading(self) -> bool:
        """Check if metadata loading is in progress.

        Returns:
            True if currently loading metadata

        """
        ...

    def is_running_metadata_task(self) -> bool:
        """Check if there's currently a metadata task running.

        Returns:
            True if a task is running

        """
        ...

    # -------------------------------------------------------------------------
    # Mode Determination
    # -------------------------------------------------------------------------

    def determine_metadata_mode(self, modifier_state: Any = None) -> tuple[bool, bool]:
        """Determine metadata mode based on keyboard modifiers.

        Args:
            modifier_state: Qt.KeyboardModifiers or None

        Returns:
            Tuple of (load_metadata, use_extended)

        """
        ...

    def should_use_extended_metadata(self, modifier_state: Any = None) -> bool:
        """Check if extended metadata should be used.

        Args:
            modifier_state: Qt.KeyboardModifiers or None

        Returns:
            True if extended metadata should be used

        """
        ...

    # -------------------------------------------------------------------------
    # Metadata Loading
    # -------------------------------------------------------------------------

    def load_metadata_for_items(
        self,
        items: list["FileItem"],
        use_extended: bool = False,
        source: str = "unknown",
    ) -> None:
        """Load metadata for given file items.

        Args:
            items: List of FileItem objects to load metadata for
            use_extended: Whether to load extended metadata
            source: Source identifier for logging

        """
        ...

    def load_metadata_streaming(
        self,
        items: list["FileItem"],
        use_extended: bool = False,
    ) -> None:
        """Load metadata using streaming mode.

        Args:
            items: List of FileItem objects
            use_extended: Whether to load extended metadata

        """
        ...

    # -------------------------------------------------------------------------
    # Cache Operations
    # -------------------------------------------------------------------------

    def check_cached_metadata(self, file_item: "FileItem") -> dict[str, Any] | None:
        """Check for cached metadata for a file.

        Args:
            file_item: File to check

        Returns:
            Cached metadata dict or None

        """
        ...

    def has_cached_metadata(self, file_item: "FileItem") -> bool:
        """Check if file has cached metadata.

        Args:
            file_item: File to check

        Returns:
            True if metadata is cached

        """
        ...

    def check_cached_hash(self, file_item: "FileItem") -> str | None:
        """Check for cached hash for a file.

        Args:
            file_item: File to check

        Returns:
            Cached hash string or None

        """
        ...

    def has_cached_hash(self, file_item: "FileItem") -> bool:
        """Check if file has cached hash.

        Args:
            file_item: File to check

        Returns:
            True if hash is cached

        """
        ...

    # -------------------------------------------------------------------------
    # Enhanced Metadata
    # -------------------------------------------------------------------------

    def get_enhanced_metadata(
        self,
        file_item: "FileItem",
        folder_files: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Get enhanced metadata including companion files.

        Args:
            file_item: File to get metadata for
            folder_files: Optional list of files in folder

        Returns:
            Enhanced metadata dict or None

        """
        ...

    # -------------------------------------------------------------------------
    # Structured Metadata
    # -------------------------------------------------------------------------

    def get_structured_metadata(self, file_path: str) -> dict[str, Any]:
        """Get structured metadata for a file.

        Args:
            file_path: Path to file

        Returns:
            Structured metadata dict

        """
        ...

    def get_field_value(self, file_path: str, field_key: str) -> str | None:
        """Get a specific field value.

        Args:
            file_path: Path to file
            field_key: Key of field to get

        Returns:
            Field value or None

        """
        ...

    # -------------------------------------------------------------------------
    # Shortcut Methods
    # -------------------------------------------------------------------------

    def shortcut_load_metadata(self) -> None:
        """Handle Shift+M shortcut for fast metadata loading."""
        ...

    def shortcut_load_extended_metadata(self) -> None:
        """Handle Ctrl+Shift+M shortcut for extended metadata loading."""
        ...

    def shortcut_load_metadata_all(self) -> None:
        """Handle Shift+Alt+M shortcut for loading metadata for all files."""
        ...

    def shortcut_load_extended_metadata_all(self) -> None:
        """Handle Ctrl+Shift+Alt+M for extended metadata for all files."""
        ...

    # -------------------------------------------------------------------------
    # Saving
    # -------------------------------------------------------------------------

    def save_metadata_for_selected(self) -> None:
        """Save metadata for currently selected files."""
        ...

    def save_all_modified_metadata(self, is_exit_save: bool = False) -> None:
        """Save all modified metadata.

        Args:
            is_exit_save: Whether this is an exit save operation

        """
        ...

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def cleanup(self) -> None:
        """Clean up resources."""
        ...
