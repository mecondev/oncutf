"""Module: folder_color_command.py

Author: Michael Economou
Date: 2025-12-22

Command for auto-coloring files by folder with undo/redo support.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from oncutf.core.metadata_commands import MetadataCommand
from oncutf.utils.color_generator import ColorGenerator
from oncutf.utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.database.database_manager import DatabaseManager
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class AutoColorByFolderCommand(MetadataCommand):
    """Command for auto-coloring files by their parent folder.

    Groups files by folder and assigns a unique random color to each folder's files.
    Skips files that already have a color assigned.
    """

    def __init__(
        self,
        file_items: list[FileItem],
        db_manager: DatabaseManager,
        skip_existing: bool = True,
        color_generator: ColorGenerator | None = None,
        timestamp: datetime | None = None,
    ):
        """Initialize auto-color by folder command.

        Args:
            file_items: List of all file items in the table
            db_manager: Database manager instance
            skip_existing: If True, skip files with existing colors; if False, recolor all
            color_generator: Color generator instance (optional)
            timestamp: Command creation timestamp

        """
        # Use empty string for file_path since this is a batch operation
        super().__init__("", timestamp)
        self.file_items = file_items
        self.db_manager = db_manager
        self.skip_existing = skip_existing
        self.color_generator = color_generator or ColorGenerator()

        # Store previous colors for undo
        self.previous_colors: dict[str, str] = {}
        # Store new colors assigned
        self.new_colors: dict[str, str] = {}
        # Store folder to color mapping
        self.folder_colors: dict[str, str] = {}

    def execute(self) -> bool:
        """Execute auto-color by folder operation."""
        try:
            if self.executed:
                return True

            # Group files by folder
            folder_groups = self._group_by_folder()

            if len(folder_groups) < 2:
                logger.info("[AutoColorByFolder] Less than 2 folders found, skipping auto-color")
                return False

            # Get existing colors from all files
            existing_colors = self._get_existing_colors()

            # Assign colors to all folders
            folder_paths = sorted(folder_groups.keys())  # Sort for deterministic order
            logger.debug(
                "[AutoColorByFolder] Found %d folders: %s", len(folder_paths), folder_paths
            )

            for folder_path in folder_paths:
                # Generate unique color for this folder
                color = self.color_generator.generate_unique_color(existing_colors)
                if color is None:
                    logger.warning(
                        "[AutoColorByFolder] Failed to generate unique color for folder: %s",
                        folder_path,
                    )
                    continue

                # Store folder color mapping
                self.folder_colors[folder_path] = color
                existing_colors.add(color)

                # Apply color to all files in this folder
                for file_item in folder_groups[folder_path]:
                    # Skip if file already has a color (only if skip_existing=True)
                    if self.skip_existing and file_item.color != "none":
                        logger.debug(
                            "[AutoColorByFolder] Skipping file with existing color: %s (%s)",
                            file_item.filename,
                            file_item.color,
                        )
                        continue

                    # Store previous color for undo
                    self.previous_colors[file_item.path] = file_item.color

                    # Assign new color
                    file_item.color = color
                    self.new_colors[file_item.path] = color

                    # Save to database
                    self.db_manager.set_color_tag(file_item.path, color)

                    logger.debug(
                        "[AutoColorByFolder] Assigned color %s to file: %s",
                        color,
                        file_item.filename,
                    )

            self.executed = True
            self.undone = False

            logger.info(
                "[AutoColorByFolder] Auto-colored %d files across %d folders",
                len(self.new_colors),
                len(self.folder_colors),
            )
            return True

        except Exception:
            logger.exception("[AutoColorByFolder] Failed to execute auto-color")
            return False

    def undo(self) -> bool:
        """Undo auto-color operation."""
        try:
            if not self.can_undo():
                return False

            # Restore previous colors
            for file_item in self.file_items:
                if file_item.path in self.previous_colors:
                    old_color = self.previous_colors[file_item.path]
                    file_item.color = old_color
                    self.db_manager.set_color_tag(file_item.path, old_color)

            self.undone = True
            logger.info(
                "[AutoColorByFolder] Undone auto-color for %d files", len(self.previous_colors)
            )
            return True

        except Exception:
            logger.exception("[AutoColorByFolder] Failed to undo auto-color")
            return False

    def redo(self) -> bool:
        """Redo auto-color operation."""
        try:
            if not self.can_redo():
                return False

            # Reapply new colors
            for file_item in self.file_items:
                if file_item.path in self.new_colors:
                    new_color = self.new_colors[file_item.path]
                    file_item.color = new_color
                    self.db_manager.set_color_tag(file_item.path, new_color)

            self.undone = False
            logger.info("[AutoColorByFolder] Redone auto-color for %d files", len(self.new_colors))
            return True

        except Exception:
            logger.exception("[AutoColorByFolder] Failed to redo auto-color")
            return False

    def get_description(self) -> str:
        """Get command description."""
        return f"Auto-color {len(self.new_colors)} files by folder"

    def get_command_type(self) -> str:
        """Get command type."""
        return "auto_color_folders"

    def _group_by_folder(self) -> dict[str, list[FileItem]]:
        """Group file items by their parent folder.

        Returns:
            Dictionary mapping folder path to list of file items

        """
        folder_groups: dict[str, list[FileItem]] = {}

        for file_item in self.file_items:
            folder_path = str(Path(file_item.path).parent)

            if folder_path not in folder_groups:
                folder_groups[folder_path] = []

            folder_groups[folder_path].append(file_item)

        return folder_groups

    def _get_existing_colors(self) -> set[str]:
        """Get all existing colors from file items and database.

        Returns:
            Set of existing hex color strings

        """
        existing_colors: set[str] = set()

        # Get colors from current file items
        for file_item in self.file_items:
            if file_item.color != "none":
                existing_colors.add(file_item.color)

        # Also get colors from database (in case some are not in current table)
        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT color_tag FROM file_paths WHERE color_tag != "none"')
            rows = cursor.fetchall()
            for (color,) in rows:
                existing_colors.add(color)

        logger.debug("[AutoColorByFolder] Found %d existing colors", len(existing_colors))
        return existing_colors

    def get_files_with_existing_colors(self) -> list[str]:
        """Get list of filenames that already have colors assigned.

        Returns:
            List of filenames with existing colors (for warning dialog)

        """
        files_with_colors: list[str] = []

        for file_item in self.file_items:
            if file_item.color != "none":
                files_with_colors.append(file_item.filename)

        return files_with_colors
