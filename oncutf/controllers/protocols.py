"""Module: protocols.py.

Author: Michael Economou
Date: 2026-01-30

Protocols for controller dependencies.

This module defines Protocol classes that allow controllers to depend on
abstractions rather than concrete UI implementations. This enables:
- UI-agnostic controllers that can be tested without Qt
- Clean separation between business logic and presentation
- Dependency injection of UI components

Usage:
    Controllers should depend on these protocols via TYPE_CHECKING imports.
    Concrete implementations (in oncutf.ui) implement these protocols.
"""

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem


@runtime_checkable
class TableManagerProtocol(Protocol):
    """Protocol for table management operations.

    Defines the interface that FileLoadController needs for table operations.
    Implemented by oncutf.ui.managers.table_manager.TableManager.
    """

    def clear_file_table(self, message: str = "No folder selected") -> None:
        """Clear the file table and show a placeholder message.

        Args:
            message: Placeholder message to display

        """
        ...

    def get_selected_files(self) -> list["FileItem"]:
        """Get currently selected files.

        Returns:
            List of selected FileItem objects

        """
        ...


@runtime_checkable
class RenameManagerProtocol(Protocol):
    """Protocol for rename management operations.

    Defines the interface that RenameController needs for rename operations.
    Implemented by oncutf.ui.managers.rename_manager.RenameManager.
    """

    def rename_files(self) -> None:
        """Execute the batch rename process for checked files."""
        ...

    def post_rename_workflow(
        self,
        renamed_count: int,
        checked_paths: set[str],
        selected_paths: set[str],
    ) -> None:
        """Execute post-rename workflow.

        Args:
            renamed_count: Number of files renamed
            checked_paths: Set of paths that were checked before rename
            selected_paths: Set of paths that were selected before rename

        """
        ...


@runtime_checkable
class MetadataExporterProtocol(Protocol):
    """Protocol for metadata export operations.

    Defines the interface that MetadataController needs for exporting.
    Implemented by oncutf.ui.managers.metadata_exporter.MetadataExporter.
    """

    def export_files(
        self,
        files: list[Any],
        output_dir: str,
        format_type: str = "json",
    ) -> bool:
        """Export metadata for a list of files.

        Args:
            files: List of file items to export
            output_dir: Directory to save export files
            format_type: Export format ("json", "markdown", "csv")

        Returns:
            True if export successful

        """
        ...


@runtime_checkable
class ValidationDialogProtocol(Protocol):
    """Protocol for validation dialog interactions.

    Defines the interface for showing validation issues to users.
    This allows controllers to request user decisions without
    directly importing UI dialog classes.
    """

    def show_validation_issues(self, validation_result: Any) -> str:
        """Show validation issues dialog and get user decision.

        Args:
            validation_result: ValidationResult object with issues

        Returns:
            User decision: "skip", "cancel", or "refresh"

        """
        ...
