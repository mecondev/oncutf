"""
Module: file_group.py

Author: Michael Economou
Date: 2025-12-16

FileGroup model for organizing files by folder/source.
Part of Phase 2: State Management Fix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from oncutf.models.file_item import FileItem


@dataclass
class FileGroup:
    """
    Represents a group of files from a common source.

    Used for:
    - Counter scope management (reset per folder)
    - Batch operations (metadata loading per folder)
    - UI organization (show folder boundaries)

    Attributes:
        source_path: The folder path this group came from
        files: List of FileItem objects in this group
        recursive: Whether files were loaded recursively
        metadata: Optional metadata about the group (e.g., load timestamp)
    """

    source_path: Path
    files: list[FileItem] = field(default_factory=list)
    recursive: bool = False
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate FileGroup after creation."""
        if not isinstance(self.source_path, Path):
            self.source_path = Path(self.source_path)

    @property
    def file_count(self) -> int:
        """Return the number of files in this group."""
        return len(self.files)

    @property
    def is_empty(self) -> bool:
        """Check if this group has no files."""
        return len(self.files) == 0

    def add_file(self, file_item: FileItem) -> None:
        """Add a file to this group."""
        if file_item not in self.files:
            self.files.append(file_item)

    def remove_file(self, file_item: FileItem) -> None:
        """Remove a file from this group."""
        if file_item in self.files:
            self.files.remove(file_item)

    def get_files(self) -> list[FileItem]:
        """Return all files in this group."""
        return self.files.copy()

    def __repr__(self) -> str:
        """Return string representation of FileGroup."""
        return (
            f"FileGroup(source_path={self.source_path}, "
            f"file_count={self.file_count}, "
            f"recursive={self.recursive})"
        )
