"""
test_file_entry.py

Test suite for FileEntry dataclass.
"""

from datetime import datetime

from models.file_entry import FileEntry


class TestFileEntryCreation:
    """Test FileEntry creation and initialization."""

    def test_basic_creation(self):
        """Test creating FileEntry with minimum fields."""
        entry = FileEntry(
            full_path="/path/to/file.txt",
            filename="file.txt",
            extension="txt",
        )

        assert entry.full_path == "/path/to/file.txt"
        assert entry.filename == "file.txt"
        assert entry.extension == "txt"
        assert entry.size == 0
        assert not entry.checked
        assert entry.metadata_status == "none"

    def test_creation_with_all_fields(self):
        """Test creating FileEntry with all fields."""
        modified = datetime(2024, 1, 1, 12, 0, 0)

        entry = FileEntry(
            full_path="/path/to/file.jpg",
            filename="file.jpg",
            extension="jpg",
            size=1024,
            modified=modified,
            checked=True,
            metadata_status="loaded",
        )

        assert entry.size == 1024
        assert entry.modified == modified
        assert entry.checked
        assert entry.metadata_status == "loaded"

    def test_extension_normalization(self):
        """Test that extensions are normalized (lowercase, no dot)."""
        entry1 = FileEntry(full_path="/path/file.TXT", filename="file.TXT", extension=".TXT")
        assert entry1.extension == "txt"

        entry2 = FileEntry(full_path="/path/file.JPG", filename="file.JPG", extension="JPG")
        assert entry2.extension == "jpg"

    def test_filename_validation(self):
        """Test filename validation against path."""
        # Should log warning but work
        entry = FileEntry(
            full_path="/path/to/actual.txt",
            filename="wrong.txt",  # Mismatch
            extension="txt",
        )

        # Filename should be corrected
        assert entry.filename == "actual.txt"


class TestFileEntryFromPath:
    """Test creating FileEntry from file path."""

    def test_from_path_basic(self, tmp_path):
        """Test from_path with real file."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        entry = FileEntry.from_path(str(test_file))

        assert entry.filename == "test.txt"
        assert entry.extension == "txt"
        assert entry.size > 0
        assert isinstance(entry.modified, datetime)

    def test_from_path_no_extension(self, tmp_path):
        """Test from_path with file without extension."""
        test_file = tmp_path / "README"
        test_file.write_text("Readme content")

        entry = FileEntry.from_path(str(test_file))

        assert entry.filename == "README"
        assert entry.extension == ""

    def test_from_path_nonexistent(self):
        """Test from_path with nonexistent file."""
        entry = FileEntry.from_path("/nonexistent/file.txt")

        assert entry.filename == "file.txt"
        assert entry.extension == "txt"
        assert entry.size == 0


class TestFileEntryProperties:
    """Test FileEntry properties and methods."""

    def test_path_alias(self):
        """Test path property (backward compatibility)."""
        entry = FileEntry(full_path="/path/to/file.txt", filename="file.txt", extension="txt")
        assert entry.path == entry.full_path

    def test_name_alias(self):
        """Test name property (backward compatibility)."""
        entry = FileEntry(full_path="/path/to/file.txt", filename="file.txt", extension="txt")
        assert entry.name == entry.filename

    def test_metadata_property(self):
        """Test metadata property access."""
        entry = FileEntry(full_path="/path/to/file.txt", filename="file.txt", extension="txt")

        assert entry.metadata == {}
        assert not entry.has_metadata

        # Add metadata
        entry.metadata = {"key": "value"}
        assert entry.has_metadata
        assert entry.metadata["key"] == "value"

    def test_metadata_extended_property(self):
        """Test metadata_extended property."""
        entry = FileEntry(full_path="/path/to/file.txt", filename="file.txt", extension="txt")

        assert not entry.metadata_extended

        entry.metadata = {"__extended__": True, "data": "value"}
        assert entry.metadata_extended

    def test_human_readable_size(self):
        """Test human-readable size formatting."""
        entry = FileEntry(
            full_path="/path/to/file.txt",
            filename="file.txt",
            extension="txt",
            size=1024,
        )

        size_str = entry.get_human_readable_size()
        assert "KB" in size_str or "kB" in size_str


class TestFileEntryConversion:
    """Test FileEntry conversion methods."""

    def test_to_dict(self):
        """Test to_dict conversion."""
        modified = datetime(2024, 1, 1, 12, 0, 0)
        entry = FileEntry(
            full_path="/path/to/file.txt",
            filename="file.txt",
            extension="txt",
            size=1024,
            modified=modified,
            checked=True,
        )

        data = entry.to_dict()

        assert data["full_path"] == "/path/to/file.txt"
        assert data["filename"] == "file.txt"
        assert data["extension"] == "txt"
        assert data["size"] == 1024
        assert data["checked"] is True
        assert "modified" in data

    def test_from_file_item(self):
        """Test converting from legacy FileItem."""
        # Mock FileItem
        class MockFileItem:
            def __init__(self):
                self.full_path = "/path/to/file.txt"
                self.filename = "file.txt"
                self.extension = "txt"
                self.size = 2048
                self.modified = datetime(2024, 1, 1)
                self.checked = True
                self.metadata_status = "loaded"
                self.metadata = {"key": "value"}

        file_item = MockFileItem()
        entry = FileEntry.from_file_item(file_item)

        assert entry.full_path == file_item.full_path
        assert entry.filename == file_item.filename
        assert entry.extension == file_item.extension
        assert entry.size == file_item.size
        assert entry.checked == file_item.checked
        assert entry.metadata_status == file_item.metadata_status
        assert entry.metadata == file_item.metadata


class TestFileEntryStringRepresentation:
    """Test FileEntry string representations."""

    def test_str(self):
        """Test __str__ representation."""
        entry = FileEntry(full_path="/path/to/file.txt", filename="file.txt", extension="txt")
        assert str(entry) == "FileEntry(file.txt)"

    def test_repr(self):
        """Test __repr__ representation."""
        modified = datetime(2024, 1, 1, 12, 0, 0)
        entry = FileEntry(
            full_path="/path/to/file.txt",
            filename="file.txt",
            extension="txt",
            size=1024,
            modified=modified,
        )

        repr_str = repr(entry)
        assert "FileEntry" in repr_str
        assert "file.txt" in repr_str
        assert "txt" in repr_str
