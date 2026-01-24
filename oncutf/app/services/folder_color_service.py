"""Folder color service for UI isolation from core folder color command.

This service provides a clean interface for UI components to access folder color
functionality without directly depending on core.folder_color_command.

Author: Michael Economou
Date: 2026-01-24
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.core.folder_color_command import AutoColorByFolderCommand
    from oncutf.models.file_item import FileItem


class FolderColorService:
    """Service layer for folder color operations.

    Provides UI-friendly access to folder color command functionality.
    """

    def create_auto_color_command(
        self,
        file_items: list[FileItem],
        db_manager: Any,
        skip_existing: bool = True,
    ) -> AutoColorByFolderCommand:
        """Create auto color by folder command.

        Args:
            file_items: List of file items to process
            db_manager: Database manager instance
            skip_existing: If True, skip files with existing colors; if False, recolor all

        Returns:
            AutoColorByFolderCommand instance

        """
        from oncutf.core.folder_color_command import AutoColorByFolderCommand

        return AutoColorByFolderCommand(
            file_items=file_items, db_manager=db_manager, skip_existing=skip_existing
        )

    def get_files_with_existing_colors(
        self, file_items: list[FileItem], db_manager: Any
    ) -> list[str]:
        """Get list of files that already have colors assigned.

        Args:
            file_items: List of file items to check
            db_manager: Database manager instance

        Returns:
            List of file paths with existing colors

        """
        command = self.create_auto_color_command(file_items, db_manager)
        return command.get_files_with_existing_colors()

    def execute_auto_color(
        self, file_items: list[FileItem], db_manager: Any, skip_existing: bool = True
    ) -> bool:
        """Execute automatic coloring by folder.

        Args:
            file_items: List of file items to color
            db_manager: Database manager instance
            skip_existing: If True, skip files with existing colors; if False, recolor all

        Returns:
            True if successful, False otherwise

        """
        command = self.create_auto_color_command(file_items, db_manager, skip_existing=skip_existing)
        return command.execute()


# Singleton instance
_folder_color_service: FolderColorService | None = None


def get_folder_color_service() -> FolderColorService:
    """Get singleton folder color service instance.

    Returns:
        FolderColorService instance

    """
    global _folder_color_service
    if _folder_color_service is None:
        _folder_color_service = FolderColorService()
    return _folder_color_service
