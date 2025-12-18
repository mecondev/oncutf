"""
Tests for FilesystemService.

Author: Michael Economou
Date: December 18, 2025

Tests the filesystem operations service implementation.
"""

from __future__ import annotations

from pathlib import Path

from oncutf.services.filesystem_service import FilesystemService
from oncutf.services.interfaces import FilesystemServiceProtocol


class TestFilesystemServiceProtocolCompliance:
    """Tests for protocol compliance."""

    def test_implements_filesystem_service_protocol(self) -> None:
        """Test that FilesystemService implements FilesystemServiceProtocol."""
        service = FilesystemService()
        assert isinstance(service, FilesystemServiceProtocol)


class TestFilesystemServiceFileExists:
    """Tests for file_exists method."""

    def test_file_exists_returns_true_for_file(self, tmp_path: Path) -> None:
        """Test that file_exists returns True for existing file."""
        service = FilesystemService()
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        assert service.file_exists(test_file) is True

    def test_file_exists_returns_false_for_nonexistent(self, tmp_path: Path) -> None:
        """Test that file_exists returns False for non-existent path."""
        service = FilesystemService()
        nonexistent = tmp_path / "nonexistent.txt"

        assert service.file_exists(nonexistent) is False

    def test_file_exists_returns_false_for_directory(self, tmp_path: Path) -> None:
        """Test that file_exists returns False for directory."""
        service = FilesystemService()

        assert service.file_exists(tmp_path) is False


class TestFilesystemServiceDirectoryExists:
    """Tests for directory_exists method."""

    def test_directory_exists_returns_true(self, tmp_path: Path) -> None:
        """Test that directory_exists returns True for existing dir."""
        service = FilesystemService()

        assert service.directory_exists(tmp_path) is True

    def test_directory_exists_returns_false_for_file(self, tmp_path: Path) -> None:
        """Test that directory_exists returns False for file."""
        service = FilesystemService()
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        assert service.directory_exists(test_file) is False


class TestFilesystemServiceGetFileInfo:
    """Tests for get_file_info method."""

    def test_get_file_info_returns_info(self, tmp_path: Path) -> None:
        """Test that get_file_info returns correct info."""
        service = FilesystemService()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        info = service.get_file_info(test_file)

        assert info["name"] == "test.txt"
        assert info["stem"] == "test"
        assert info["extension"] == ".txt"
        assert info["size"] == 12  # len("test content")
        assert "mtime" in info
        assert "ctime" in info

    def test_get_file_info_returns_empty_for_nonexistent(
        self, tmp_path: Path
    ) -> None:
        """Test that get_file_info returns empty dict for non-existent."""
        service = FilesystemService()
        nonexistent = tmp_path / "nonexistent.txt"

        info = service.get_file_info(nonexistent)

        assert info == {}

    def test_get_file_info_returns_empty_for_directory(
        self, tmp_path: Path
    ) -> None:
        """Test that get_file_info returns empty dict for directory."""
        service = FilesystemService()

        info = service.get_file_info(tmp_path)

        assert info == {}


class TestFilesystemServiceRenameFile:
    """Tests for rename_file method."""

    def test_rename_file_success(self, tmp_path: Path) -> None:
        """Test successful file rename."""
        service = FilesystemService()
        source = tmp_path / "source.txt"
        target = tmp_path / "target.txt"
        source.write_text("content")

        result = service.rename_file(source, target)

        assert result is True
        assert not source.exists()
        assert target.exists()
        assert target.read_text() == "content"

    def test_rename_file_nonexistent_source(self, tmp_path: Path) -> None:
        """Test rename with non-existent source."""
        service = FilesystemService()
        source = tmp_path / "nonexistent.txt"
        target = tmp_path / "target.txt"

        result = service.rename_file(source, target)

        assert result is False

    def test_rename_file_source_is_directory(self, tmp_path: Path) -> None:
        """Test rename with directory as source."""
        service = FilesystemService()
        target = tmp_path / "target.txt"

        result = service.rename_file(tmp_path, target)

        assert result is False

    def test_rename_file_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that rename creates parent directory if needed."""
        service = FilesystemService()
        source = tmp_path / "source.txt"
        target = tmp_path / "subdir" / "target.txt"
        source.write_text("content")

        result = service.rename_file(source, target)

        assert result is True
        assert target.exists()


class TestFilesystemServiceCopyFile:
    """Tests for copy_file method."""

    def test_copy_file_success(self, tmp_path: Path) -> None:
        """Test successful file copy."""
        service = FilesystemService()
        source = tmp_path / "source.txt"
        target = tmp_path / "target.txt"
        source.write_text("content")

        result = service.copy_file(source, target)

        assert result is True
        assert source.exists()  # Source still exists
        assert target.exists()
        assert target.read_text() == "content"

    def test_copy_file_nonexistent_source(self, tmp_path: Path) -> None:
        """Test copy with non-existent source."""
        service = FilesystemService()
        source = tmp_path / "nonexistent.txt"
        target = tmp_path / "target.txt"

        result = service.copy_file(source, target)

        assert result is False


class TestFilesystemServiceDeleteFile:
    """Tests for delete_file method."""

    def test_delete_file_success(self, tmp_path: Path) -> None:
        """Test successful file deletion."""
        service = FilesystemService()
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = service.delete_file(test_file)

        assert result is True
        assert not test_file.exists()

    def test_delete_file_nonexistent(self, tmp_path: Path) -> None:
        """Test delete of non-existent file returns True."""
        service = FilesystemService()
        nonexistent = tmp_path / "nonexistent.txt"

        result = service.delete_file(nonexistent)

        assert result is True

    def test_delete_file_directory(self, tmp_path: Path) -> None:
        """Test delete of directory returns False."""
        service = FilesystemService()

        result = service.delete_file(tmp_path)

        assert result is False


class TestFilesystemServiceListDirectory:
    """Tests for list_directory method."""

    def test_list_directory_returns_files(self, tmp_path: Path) -> None:
        """Test list_directory returns files."""
        service = FilesystemService()
        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.txt").write_text("2")
        (tmp_path / "file3.py").write_text("3")

        files = service.list_directory(tmp_path)

        assert len(files) == 3

    def test_list_directory_with_pattern(self, tmp_path: Path) -> None:
        """Test list_directory with pattern filter."""
        service = FilesystemService()
        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.txt").write_text("2")
        (tmp_path / "file3.py").write_text("3")

        files = service.list_directory(tmp_path, pattern="*.txt")

        assert len(files) == 2
        assert all(f.suffix == ".txt" for f in files)

    def test_list_directory_recursive(self, tmp_path: Path) -> None:
        """Test recursive directory listing."""
        service = FilesystemService()
        (tmp_path / "file1.txt").write_text("1")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("2")

        files = service.list_directory(tmp_path, pattern="*.txt", recursive=True)

        assert len(files) == 2

    def test_list_directory_nonexistent(self, tmp_path: Path) -> None:
        """Test list_directory with non-existent path."""
        service = FilesystemService()
        nonexistent = tmp_path / "nonexistent"

        files = service.list_directory(nonexistent)

        assert files == []


class TestFilesystemServiceGetFreeSpace:
    """Tests for get_free_space method."""

    def test_get_free_space_returns_positive(self, tmp_path: Path) -> None:
        """Test that get_free_space returns positive value."""
        service = FilesystemService()

        free_space = service.get_free_space(tmp_path)

        assert free_space > 0

    def test_get_free_space_for_file(self, tmp_path: Path) -> None:
        """Test get_free_space works with file path."""
        service = FilesystemService()
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        free_space = service.get_free_space(test_file)

        assert free_space > 0
