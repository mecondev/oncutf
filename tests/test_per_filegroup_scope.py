"""Module: test_per_filegroup_scope.py

Author: Michael Economou
Date: 2025-12-17

Integration tests for PER_FILEGROUP counter scope with preview engine.
"""

import pytest

from oncutf.core.rename.preview_manager import (
    apply_rename_modules,
    calculate_scope_aware_index,
)
from oncutf.models.counter_scope import CounterScope
from oncutf.models.file_item import FileItem


class TestPerFileGroupScope:
    """Test PER_FILEGROUP counter scope integration."""

    @pytest.fixture
    def companion_files(self, tmp_path):
        """Create companion file pairs (RAW + JPG)."""
        folder = tmp_path / "photos"
        folder.mkdir()

        files = []

        # Pair 1: photo1.cr2 + photo1.jpg
        for ext in [".cr2", ".jpg"]:
            path = folder / f"photo1{ext}"
            path.touch()
            files.append(FileItem.from_path(str(path)))

        # Pair 2: photo2.nef + photo2.jpg
        for ext in [".nef", ".jpg"]:
            path = folder / f"photo2{ext}"
            path.touch()
            files.append(FileItem.from_path(str(path)))

        # Standalone
        path = folder / "photo3.jpg"
        path.touch()
        files.append(FileItem.from_path(str(path)))

        return files

    @pytest.fixture
    def multi_folder_files(self, tmp_path):
        """Create files across multiple folders."""
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

    def test_per_filegroup_scope_with_folders(self, multi_folder_files):
        """Test PER_FILEGROUP scope groups files by folder (default behavior)."""
        modules_data = [
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.PER_FILEGROUP.value,
            }
        ]

        results = []
        for idx, file_item in enumerate(multi_folder_files):
            new_name = apply_rename_modules(
                modules_data,
                idx,
                file_item,
                metadata_cache=None,
                all_files=multi_folder_files,
            )
            results.append(new_name)

        # First folder (3 files): 001.jpg, 002.jpg, 003.jpg
        # Second folder (2 files): 001.jpg, 002.jpg (counter resets!)
        assert results[0].startswith("001")
        assert results[1].startswith("002")
        assert results[2].startswith("003")
        assert results[3].startswith("001")  # Reset!
        assert results[4].startswith("002")

    def test_per_filegroup_scope_aware_index(self, multi_folder_files):
        """Test calculate_scope_aware_index with PER_FILEGROUP."""
        # Folder A has 3 files (indices 0, 1, 2)
        # Folder B has 2 files (indices 3, 4)

        # Test folder A files
        for i in range(3):
            index = calculate_scope_aware_index(
                CounterScope.PER_FILEGROUP.value,
                i,
                multi_folder_files[i],
                multi_folder_files,
            )
            assert index == i  # Within folder group

        # Test folder B files (should reset)
        for i in range(3, 5):
            index = calculate_scope_aware_index(
                CounterScope.PER_FILEGROUP.value,
                i,
                multi_folder_files[i],
                multi_folder_files,
            )
            assert index == (i - 3)  # Reset to 0, 1

    def test_per_filegroup_with_custom_start_step(self, multi_folder_files):
        """Test PER_FILEGROUP with custom start and step values."""
        modules_data = [
            {
                "type": "counter",
                "start": 10,
                "step": 5,
                "padding": 3,
                "scope": CounterScope.PER_FILEGROUP.value,
            }
        ]

        results = []
        for idx, file_item in enumerate(multi_folder_files):
            new_name = apply_rename_modules(
                modules_data,
                idx,
                file_item,
                metadata_cache=None,
                all_files=multi_folder_files,
            )
            results.append(new_name)

        # Folder A: 010, 015, 020
        # Folder B: 010, 015 (reset!)
        assert results[0].startswith("010")
        assert results[1].startswith("015")
        assert results[2].startswith("020")
        assert results[3].startswith("010")  # Reset!
        assert results[4].startswith("015")

    def test_per_filegroup_mixed_with_other_modules(self, multi_folder_files):
        """Test PER_FILEGROUP scope with other modules."""
        modules_data = [
            {"type": "specified_text", "text": "IMG"},
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 2,
                "scope": CounterScope.PER_FILEGROUP.value,
            },
        ]

        results = []
        for idx, file_item in enumerate(multi_folder_files):
            new_name = apply_rename_modules(
                modules_data,
                idx,
                file_item,
                metadata_cache=None,
                all_files=multi_folder_files,
            )
            results.append(new_name)

        # Folder A: IMG01, IMG02, IMG03
        # Folder B: IMG01, IMG02 (counter resets!)
        assert results[0].startswith("IMG01")
        assert results[1].startswith("IMG02")
        assert results[2].startswith("IMG03")
        assert results[3].startswith("IMG01")  # Reset!
        assert results[4].startswith("IMG02")

    def test_per_filegroup_single_folder(self, tmp_path):
        """Test PER_FILEGROUP with all files in single folder (same as GLOBAL)."""
        folder = tmp_path / "single"
        folder.mkdir()

        files = []
        for i in range(1, 4):
            path = folder / f"file{i}.jpg"
            path.touch()
            files.append(FileItem.from_path(str(path)))

        modules_data = [
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.PER_FILEGROUP.value,
            }
        ]

        results = []
        for idx, file_item in enumerate(files):
            new_name = apply_rename_modules(
                modules_data, idx, file_item, metadata_cache=None, all_files=files
            )
            results.append(new_name)

        # All in same folder/group: 001, 002, 003
        assert results[0].startswith("001")
        assert results[1].startswith("002")
        assert results[2].startswith("003")

    def test_per_filegroup_fallback_without_all_files(self, multi_folder_files):
        """Test PER_FILEGROUP fallback to global index when all_files is None."""
        modules_data = [
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.PER_FILEGROUP.value,
            }
        ]

        results = []
        for idx, file_item in enumerate(multi_folder_files):
            new_name = apply_rename_modules(
                modules_data,
                idx,
                file_item,
                metadata_cache=None,
                all_files=None,  # No files list!
            )
            results.append(new_name)

        # Should fallback to global: 001, 002, 003, 004, 005
        assert results[0].startswith("001")
        assert results[1].startswith("002")
        assert results[2].startswith("003")
        assert results[3].startswith("004")  # No reset!
        assert results[4].startswith("005")

    def test_per_filegroup_vs_per_folder_same_result(self, multi_folder_files):
        """Test that PER_FILEGROUP and PER_FOLDER produce same results (default grouping)."""
        per_folder_results = []
        per_filegroup_results = []

        # Test PER_FOLDER
        modules_data_folder = [
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.PER_FOLDER.value,
            }
        ]

        for idx, file_item in enumerate(multi_folder_files):
            new_name = apply_rename_modules(
                modules_data_folder,
                idx,
                file_item,
                metadata_cache=None,
                all_files=multi_folder_files,
            )
            per_folder_results.append(new_name)

        # Test PER_FILEGROUP
        modules_data_filegroup = [
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.PER_FILEGROUP.value,
            }
        ]

        for idx, file_item in enumerate(multi_folder_files):
            new_name = apply_rename_modules(
                modules_data_filegroup,
                idx,
                file_item,
                metadata_cache=None,
                all_files=multi_folder_files,
            )
            per_filegroup_results.append(new_name)

        # Both should produce same results (default filegroup is by folder)
        assert per_folder_results == per_filegroup_results
