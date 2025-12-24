"""
Module: test_file_grouper.py

Author: Michael Economou
Date: 2025-12-17

Tests for file_grouper utility functions.
"""

import pytest

from oncutf.models.file_item import FileItem
from oncutf.utils.file_grouper import (
    calculate_filegroup_counter_index,
    get_file_group_index,
    group_files_by_companion,
    group_files_by_folder,
)


class TestFileGrouper:
    """Test file grouping utilities."""

    @pytest.fixture
    def sample_files_multi_folder(self, tmp_path):
        """Create sample files in multiple folders."""
        folder_a = tmp_path / "folder_a"
        folder_b = tmp_path / "folder_b"
        folder_a.mkdir()
        folder_b.mkdir()

        files = []
        # Folder A: 3 files
        for i in range(1, 4):
            path = folder_a / f"file{i}.jpg"
            path.touch()
            files.append(FileItem.from_path(str(path)))

        # Folder B: 2 files
        for i in range(4, 6):
            path = folder_b / f"file{i}.jpg"
            path.touch()
            files.append(FileItem.from_path(str(path)))

        return files

    @pytest.fixture
    def sample_companion_files(self, tmp_path):
        """Create sample companion files (RAW + JPG pairs)."""
        folder = tmp_path / "photos"
        folder.mkdir()

        files = []

        # Companion pair 1: photo1.cr2 + photo1.jpg
        cr2_1 = folder / "photo1.cr2"
        jpg_1 = folder / "photo1.jpg"
        cr2_1.touch()
        jpg_1.touch()
        files.append(FileItem.from_path(str(cr2_1)))
        files.append(FileItem.from_path(str(jpg_1)))

        # Companion pair 2: photo2.nef + photo2.jpg
        nef_2 = folder / "photo2.nef"
        jpg_2 = folder / "photo2.jpg"
        nef_2.touch()
        jpg_2.touch()
        files.append(FileItem.from_path(str(nef_2)))
        files.append(FileItem.from_path(str(jpg_2)))

        # Standalone file
        jpg_3 = folder / "photo3.jpg"
        jpg_3.touch()
        files.append(FileItem.from_path(str(jpg_3)))

        return files

    def test_group_files_by_folder(self, sample_files_multi_folder):
        """Test grouping files by folder."""
        groups = group_files_by_folder(sample_files_multi_folder)

        # Should have 2 groups (folder_a and folder_b)
        assert len(groups) == 2

        # Check file counts
        group_sizes = sorted([g.file_count for g in groups])
        assert group_sizes == [2, 3]  # folder_b: 2, folder_a: 3

        # All files should be accounted for
        total_files = sum(g.file_count for g in groups)
        assert total_files == 5

    def test_group_files_by_companion_pairs(self, sample_companion_files):
        """Test grouping companion files (RAW + JPG)."""
        groups = group_files_by_companion(sample_companion_files)

        # Should have 3 groups: 2 companion pairs + 1 standalone
        assert len(groups) == 3

        # Check group types
        companion_groups = [g for g in groups if g.metadata.get("group_type") == "companion"]
        standalone_groups = [g for g in groups if g.metadata.get("group_type") == "standalone"]

        assert len(companion_groups) == 2  # photo1 pair, photo2 pair
        assert len(standalone_groups) == 1  # photo3.jpg

        # Check companion group sizes
        for group in companion_groups:
            assert group.file_count == 2  # RAW + JPG

    def test_get_file_group_index(self, sample_files_multi_folder):
        """Test getting file group index."""
        groups = group_files_by_folder(sample_files_multi_folder)

        # Get index for first file
        first_file = sample_files_multi_folder[0]
        group_idx, file_idx = get_file_group_index(first_file, groups)

        assert group_idx >= 0
        assert file_idx >= 0

        # Verify file is in the group
        found_file = groups[group_idx].files[file_idx]
        assert found_file.full_path == first_file.full_path

    def test_get_file_group_index_not_found(self, sample_files_multi_folder, tmp_path):
        """Test getting index for file not in groups."""
        groups = group_files_by_folder(sample_files_multi_folder)

        # Create a file not in groups
        other_file_path = tmp_path / "other" / "file.jpg"
        other_file_path.parent.mkdir(exist_ok=True)
        other_file_path.touch()
        other_file = FileItem.from_path(str(other_file_path))

        group_idx, file_idx = get_file_group_index(other_file, groups)

        assert group_idx == -1
        assert file_idx == -1

    def test_calculate_filegroup_counter_index(self, sample_files_multi_folder):
        """Test calculating counter index for PER_FILEGROUP scope."""
        # Group files by folder
        groups = group_files_by_folder(sample_files_multi_folder)

        # Calculate index for each file
        indices = []
        for global_idx, file_item in enumerate(sample_files_multi_folder):
            filegroup_idx = calculate_filegroup_counter_index(
                file_item, sample_files_multi_folder, global_idx, groups
            )
            indices.append(filegroup_idx)

        # First folder has 3 files: indices should be 0, 1, 2
        # Second folder has 2 files: indices should be 0, 1
        # (Order depends on file system ordering, but within-group indices should reset)

        # Verify indices are within valid range for their groups
        for i, idx in enumerate(indices):
            group_idx, _ = get_file_group_index(sample_files_multi_folder[i], groups)
            group = groups[group_idx]
            assert 0 <= idx < group.file_count

    def test_calculate_filegroup_counter_index_default_grouping(self, sample_files_multi_folder):
        """Test counter index calculation with default folder grouping."""
        # Don't pass groups - should group by folder automatically
        for global_idx, file_item in enumerate(sample_files_multi_folder):
            filegroup_idx = calculate_filegroup_counter_index(
                file_item, sample_files_multi_folder, global_idx, groups=None
            )
            # Should return valid index
            assert filegroup_idx >= 0

    def test_companion_group_counter_indices(self, sample_companion_files):
        """Test counter indices for companion file groups."""
        groups = group_files_by_companion(sample_companion_files)

        # Each companion pair should have indices 0, 1
        companion_groups = [g for g in groups if g.metadata.get("group_type") == "companion"]

        for group in companion_groups:
            for file_idx, file_item in enumerate(group.files):
                global_idx = sample_companion_files.index(file_item)
                filegroup_idx = calculate_filegroup_counter_index(
                    file_item, sample_companion_files, global_idx, groups
                )
                assert filegroup_idx == file_idx  # Should match position in group

    def test_empty_file_list(self):
        """Test grouping with empty file list."""
        groups = group_files_by_folder([])
        assert groups == []

        groups = group_files_by_companion([])
        assert groups == []

    def test_single_file(self, tmp_path):
        """Test grouping with single file."""
        file_path = tmp_path / "single.jpg"
        file_path.touch()
        file_item = FileItem.from_path(str(file_path))

        groups = group_files_by_folder([file_item])
        assert len(groups) == 1
        assert groups[0].file_count == 1

        groups = group_files_by_companion([file_item])
        assert len(groups) == 1
        assert groups[0].file_count == 1
        assert groups[0].metadata.get("group_type") == "standalone"

    def test_companion_patterns_custom(self, tmp_path):
        """Test companion grouping with custom patterns."""
        folder = tmp_path / "custom"
        folder.mkdir()

        # Create custom pattern files
        raw = folder / "photo.raw"
        png = folder / "photo.png"
        raw.touch()
        png.touch()

        files = [FileItem.from_path(str(raw)), FileItem.from_path(str(png))]

        # Default patterns (RAW + JPG only)
        groups = group_files_by_companion(files)
        # Should be 2 standalone groups (not companions with default patterns)
        assert len(groups) == 2

        # Custom patterns (RAW + PNG)
        custom_patterns = {".raw": [".png"]}
        groups = group_files_by_companion(files, companion_patterns=custom_patterns)
        # Should be 1 companion group
        assert len(groups) == 1
        assert groups[0].metadata.get("group_type") == "companion"
        assert groups[0].file_count == 2
