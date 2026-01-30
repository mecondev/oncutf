"""Tests for FileGroup model.

Author: Michael Economou
Date: 2025-12-16
"""

from pathlib import Path

from oncutf.models.file_group import FileGroup
from oncutf.models.file_item import FileItem


class TestFileGroupCreation:
    """Test FileGroup creation and initialization."""

    def test_create_empty_group(self):
        """Test creating an empty FileGroup."""
        group = FileGroup(source_path=Path("/test/folder"))

        assert group.source_path == Path("/test/folder")
        assert group.file_count == 0
        assert group.is_empty is True
        assert group.recursive is False
        assert group.metadata == {}

    def test_create_group_with_files(self):
        """Test creating FileGroup with initial files."""
        file1 = FileItem.from_path("/test/folder/file1.txt")
        file2 = FileItem.from_path("/test/folder/file2.txt")

        group = FileGroup(source_path=Path("/test/folder"), files=[file1, file2], recursive=True)

        assert group.file_count == 2
        assert group.is_empty is False
        assert group.recursive is True
        assert file1 in group.files
        assert file2 in group.files

    def test_source_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        group = FileGroup(source_path="/test/folder")

        assert isinstance(group.source_path, Path)
        assert group.source_path == Path("/test/folder")


class TestFileGroupOperations:
    """Test FileGroup operations (add, remove, get)."""

    def test_add_file(self):
        """Test adding a file to a group."""
        group = FileGroup(source_path=Path("/test/folder"))
        file1 = FileItem.from_path("/test/folder/file1.txt")

        group.add_file(file1)

        assert group.file_count == 1
        assert file1 in group.files

    def test_add_duplicate_file(self):
        """Test that adding a duplicate file doesn't increase count."""
        group = FileGroup(source_path=Path("/test/folder"))
        file1 = FileItem.from_path("/test/folder/file1.txt")

        group.add_file(file1)
        group.add_file(file1)  # Add same file again

        assert group.file_count == 1

    def test_remove_file(self):
        """Test removing a file from a group."""
        file1 = FileItem.from_path("/test/folder/file1.txt")
        group = FileGroup(source_path=Path("/test/folder"), files=[file1])

        group.remove_file(file1)

        assert group.file_count == 0
        assert group.is_empty is True

    def test_remove_nonexistent_file(self):
        """Test removing a file that doesn't exist in the group."""
        file1 = FileItem.from_path("/test/folder/file1.txt")
        file2 = FileItem.from_path("/test/folder/file2.txt")
        group = FileGroup(source_path=Path("/test/folder"), files=[file1])

        group.remove_file(file2)  # Should not raise error

        assert group.file_count == 1

    def test_get_files_returns_copy(self):
        """Test that get_files returns a copy, not the original list."""
        file1 = FileItem.from_path("/test/folder/file1.txt")
        group = FileGroup(source_path=Path("/test/folder"), files=[file1])

        files_copy = group.get_files()
        files_copy.append(FileItem.from_path("/test/folder/file2.txt"))

        # Original group should not be affected
        assert group.file_count == 1


class TestFileGroupMetadata:
    """Test FileGroup metadata handling."""

    def test_metadata_initialization(self):
        """Test that metadata can be provided during creation."""
        metadata = {"timestamp": "2025-12-16", "user": "test"}
        group = FileGroup(source_path=Path("/test/folder"), metadata=metadata)

        assert group.metadata == metadata

    def test_metadata_modification(self):
        """Test that metadata can be modified after creation."""
        group = FileGroup(source_path=Path("/test/folder"))

        group.metadata["timestamp"] = "2025-12-16"

        assert "timestamp" in group.metadata
        assert group.metadata["timestamp"] == "2025-12-16"


class TestFileGroupRepresentation:
    """Test FileGroup string representation."""

    def test_repr(self):
        """Test FileGroup __repr__ method."""
        # Use Path for cross-platform compatibility
        test_path = Path("test") / "folder"
        test_file = test_path / "file1.txt"
        group = FileGroup(
            source_path=test_path,
            files=[FileItem.from_path(str(test_file))],
            recursive=True,
        )

        repr_str = repr(group)

        assert "FileGroup" in repr_str
        # Check path components exist (cross-platform)
        assert "test" in repr_str and "folder" in repr_str
        assert "file_count=1" in repr_str
        assert "recursive=True" in repr_str
