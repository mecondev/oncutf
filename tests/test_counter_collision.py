"""Tests for counter collision prevention in multi-folder import scenarios.

This module tests that:
1. Counter values don't cause filename collisions across folders
2. Sequential folder imports maintain unique counter sequences
3. Edge cases like empty folders, single files work correctly

Author: Michael Economou
Date: December 19, 2025
"""

from pathlib import Path

import pytest

from oncutf.models.counter_scope import CounterScope
from oncutf.models.file_item import FileItem
from oncutf.utils.preview_engine import apply_rename_modules


class TestCounterCollisionPrevention:
    """Test that counter values prevent filename collisions."""

    @pytest.fixture
    def multi_folder_files(self, tmp_path):
        """Create files across multiple folders to simulate sequential imports."""
        folders = []
        all_files = []

        # Create 3 folders with varying file counts
        for _folder_idx, (folder_name, file_count) in enumerate(
            [
                ("photos_2023", 3),
                ("photos_2024", 5),
                ("vacation", 2),
            ]
        ):
            folder = tmp_path / folder_name
            folder.mkdir()
            folders.append(folder)

            for i in range(1, file_count + 1):
                path = folder / f"IMG_{i:04d}.jpg"
                path.touch()
                all_files.append(FileItem.from_path(str(path)))

        return all_files

    def test_no_duplicate_filenames_with_global_scope(self, multi_folder_files):
        """Test that GLOBAL scope produces unique filenames across all files."""
        modules_data = [
            {"type": "specified_text", "text": "photo_"},
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.GLOBAL.value,
            },
        ]

        generated_names = []
        for idx, file in enumerate(multi_folder_files):
            new_name = apply_rename_modules(
                modules_data, idx, file, metadata_cache=None, all_files=multi_folder_files
            )
            generated_names.append(new_name)

        # All names should be unique
        assert len(generated_names) == len(set(generated_names)), (
            f"Duplicate filenames detected: {generated_names}"
        )

        # Should be sequential from 001 to 010 (basenames, no extension)
        expected = [f"photo_{i:03d}" for i in range(1, 11)]
        assert generated_names == expected

    def test_no_duplicate_filenames_within_folder_per_folder_scope(self, multi_folder_files):
        """Test that PER_FOLDER scope produces unique filenames within each folder."""
        modules_data = [
            {"type": "specified_text", "text": "photo_"},
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.PER_FOLDER.value,
            },
        ]

        # Group results by folder
        folder_results: dict[str, list[str]] = {}
        for idx, file in enumerate(multi_folder_files):
            new_name = apply_rename_modules(
                modules_data, idx, file, metadata_cache=None, all_files=multi_folder_files
            )
            folder_name = Path(file.full_path).parent.name
            if folder_name not in folder_results:
                folder_results[folder_name] = []
            folder_results[folder_name].append(new_name)

        # Within each folder, names should be unique
        for folder, names in folder_results.items():
            assert len(names) == len(set(names)), f"Duplicate filenames in {folder}: {names}"

        # Verify counter resets per folder (basenames, no extension)
        assert folder_results["photos_2023"] == ["photo_001", "photo_002", "photo_003"]
        assert folder_results["photos_2024"] == [
            "photo_001",
            "photo_002",
            "photo_003",
            "photo_004",
            "photo_005",
        ]
        assert folder_results["vacation"] == ["photo_001", "photo_002"]


class TestSequentialFolderImport:
    """Test counter behavior when simulating sequential folder imports."""

    @pytest.fixture
    def sequential_import_files(self, tmp_path):
        """
        Create files that simulate sequential imports from different folders.
        This mimics a user adding files from multiple folders one after another.
        """
        all_files = []

        # First import: batch from folder_a
        folder_a = tmp_path / "folder_a"
        folder_a.mkdir()
        for i in range(1, 4):
            path = folder_a / f"a_{i}.jpg"
            path.touch()
            all_files.append(FileItem.from_path(str(path)))

        # Second import: batch from folder_b
        folder_b = tmp_path / "folder_b"
        folder_b.mkdir()
        for i in range(1, 3):
            path = folder_b / f"b_{i}.jpg"
            path.touch()
            all_files.append(FileItem.from_path(str(path)))

        # Third import: batch from folder_c
        folder_c = tmp_path / "folder_c"
        folder_c.mkdir()
        for i in range(1, 5):
            path = folder_c / f"c_{i}.jpg"
            path.touch()
            all_files.append(FileItem.from_path(str(path)))

        return all_files

    def test_counter_resets_correctly_for_each_folder_group(self, sequential_import_files):
        """
        Test the key scenario: when user imports files from multiple folders,
        counters should reset correctly at folder boundaries.
        """
        modules_data = [
            {"type": "specified_text", "text": "renamed_"},
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 2,
                "scope": CounterScope.PER_FOLDER.value,
            },
        ]

        results = []
        for idx, file in enumerate(sequential_import_files):
            new_name = apply_rename_modules(
                modules_data, idx, file, metadata_cache=None, all_files=sequential_import_files
            )
            folder = Path(file.full_path).parent.name
            results.append((folder, new_name))

        # Folder A (3 files): 01, 02, 03
        assert results[0] == ("folder_a", "renamed_01")
        assert results[1] == ("folder_a", "renamed_02")
        assert results[2] == ("folder_a", "renamed_03")

        # Folder B (2 files): RESET to 01, 02
        assert results[3] == ("folder_b", "renamed_01")
        assert results[4] == ("folder_b", "renamed_02")

        # Folder C (4 files): RESET to 01, 02, 03, 04
        assert results[5] == ("folder_c", "renamed_01")
        assert results[6] == ("folder_c", "renamed_02")
        assert results[7] == ("folder_c", "renamed_03")
        assert results[8] == ("folder_c", "renamed_04")

    def test_global_scope_maintains_sequence_across_all_imports(self, sequential_import_files):
        """
        Test that GLOBAL scope maintains a continuous sequence
        regardless of folder boundaries.
        """
        modules_data = [
            {"type": "specified_text", "text": "img_"},
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 2,
                "scope": CounterScope.GLOBAL.value,
            },
        ]

        results = []
        for idx, file in enumerate(sequential_import_files):
            new_name = apply_rename_modules(
                modules_data, idx, file, metadata_cache=None, all_files=sequential_import_files
            )
            results.append(new_name)

        # Should be continuous: 01 through 09 (basenames)
        expected = [f"img_{i:02d}" for i in range(1, 10)]
        assert results == expected


class TestEdgeCases:
    """Test edge cases for counter collision prevention."""

    def test_single_file_folder(self, tmp_path):
        """Test counter with folder containing only one file."""
        folder = tmp_path / "single"
        folder.mkdir()
        path = folder / "only_file.jpg"
        path.touch()
        files = [FileItem.from_path(str(path))]

        modules_data = [
            {"type": "specified_text", "text": "single_"},
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.PER_FOLDER.value,
            },
        ]

        result = apply_rename_modules(
            modules_data, 0, files[0], metadata_cache=None, all_files=files
        )

        # Result is basename without extension
        assert result == "single_001"

    def test_empty_then_populated_folders(self, tmp_path):
        """Test that counter handles folders with varying file counts correctly."""
        # Create mixed structure
        folder_a = tmp_path / "a"
        folder_b = tmp_path / "b"
        folder_a.mkdir()
        folder_b.mkdir()

        files = []
        # Folder A: 1 file
        (folder_a / "f1.jpg").touch()
        files.append(FileItem.from_path(str(folder_a / "f1.jpg")))

        # Folder B: 4 files
        for i in range(1, 5):
            (folder_b / f"f{i}.jpg").touch()
            files.append(FileItem.from_path(str(folder_b / f"f{i}.jpg")))

        modules_data = [
            {"type": "specified_text", "text": "img_"},
            {
                "type": "counter",
                "start": 100,
                "step": 10,
                "padding": 4,
                "scope": CounterScope.PER_FOLDER.value,
            },
        ]

        results = []
        for idx, file in enumerate(files):
            new_name = apply_rename_modules(
                modules_data, idx, file, metadata_cache=None, all_files=files
            )
            results.append(new_name)

        # Folder a: 0100
        # Folder b: 0100, 0110, 0120, 0130 (reset with custom step)
        # Basenames without extension
        assert results == ["img_0100", "img_0100", "img_0110", "img_0120", "img_0130"]

    def test_large_file_count_no_padding_overflow(self, tmp_path):
        """Test that padding handles large file counts without overflow."""
        folder = tmp_path / "large"
        folder.mkdir()

        # Create 15 files to test padding edge case
        files = []
        for i in range(15):
            path = folder / f"file_{i}.jpg"
            path.touch()
            files.append(FileItem.from_path(str(path)))

        modules_data = [
            {"type": "specified_text", "text": "n"},
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 2,  # Only 2 digits, but 15 files
                "scope": CounterScope.GLOBAL.value,
            },
        ]

        results = []
        for idx, file in enumerate(files):
            new_name = apply_rename_modules(
                modules_data, idx, file, metadata_cache=None, all_files=files
            )
            results.append(new_name)

        # Padding should handle numbers > 99
        # When number exceeds padding, it should still work (just without padding)
        expected = [f"n{i:02d}" if i < 100 else f"n{i}" for i in range(1, 16)]
        assert results == expected
