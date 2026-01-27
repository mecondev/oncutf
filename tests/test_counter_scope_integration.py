"""Module: test_counter_scope_integration.py

Author: Michael Economou
Date: 2025-12-17

Integration tests for counter scope feature with preview_engine.
Tests that counter scope (GLOBAL, PER_FOLDER, PER_EXTENSION) correctly
affects counter values during preview generation.
"""

import os
from pathlib import Path

import pytest

from oncutf.models.counter_scope import CounterScope
from oncutf.models.file_item import FileItem
from oncutf.core.rename.preview_manager import apply_rename_modules, calculate_scope_aware_index


class TestCounterScopeIntegration:
    """Test counter scope integration with preview engine."""

    @pytest.fixture
    def sample_files(self, tmp_path):
        """Create sample files in different folders and extensions."""
        # Folder structure:
        # folder_a/
        #   file1.jpg
        #   file2.jpg
        #   file3.png
        # folder_b/
        #   file4.jpg
        #   file5.txt

        folder_a = tmp_path / "folder_a"
        folder_b = tmp_path / "folder_b"
        folder_a.mkdir()
        folder_b.mkdir()

        files = []
        # Folder A
        for i, ext in [(1, ".jpg"), (2, ".jpg"), (3, ".png")]:
            path = folder_a / f"file{i}{ext}"
            path.touch()
            files.append(FileItem.from_path(str(path)))

        # Folder B
        for i, ext in [(4, ".jpg"), (5, ".txt")]:
            path = folder_b / f"file{i}{ext}"
            path.touch()
            files.append(FileItem.from_path(str(path)))

        return files

    def test_global_scope_counters_sequential(self, sample_files):
        """Test GLOBAL scope: counters should be sequential across all files."""
        modules_data = [
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.GLOBAL.value,
            }
        ]

        results = []
        for idx, file in enumerate(sample_files):
            new_name = apply_rename_modules(
                modules_data, idx, file, metadata_cache=None, all_files=sample_files
            )
            # Strip extension
            basename = os.path.splitext(new_name)[0]
            results.append(basename)

        # Should be 001, 002, 003, 004, 005 (global sequence)
        assert results == ["001", "002", "003", "004", "005"]

    def test_per_folder_scope_resets_at_folder_boundaries(self, sample_files):
        """Test PER_FOLDER scope: counters reset at folder boundaries."""
        modules_data = [
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.PER_FOLDER.value,
            }
        ]

        results = []
        for idx, file in enumerate(sample_files):
            new_name = apply_rename_modules(
                modules_data, idx, file, metadata_cache=None, all_files=sample_files
            )
            basename = os.path.splitext(new_name)[0]
            results.append((basename, Path(file.full_path).parent.name))

        # Should be: folder_a: 001, 002, 003, folder_b: 001, 002
        assert results[0] == ("001", "folder_a")  # file1.jpg
        assert results[1] == ("002", "folder_a")  # file2.jpg
        assert results[2] == ("003", "folder_a")  # file3.png
        assert results[3] == ("001", "folder_b")  # file4.jpg (reset!)
        assert results[4] == ("002", "folder_b")  # file5.txt

    def test_per_extension_scope_resets_at_extension_changes(self, sample_files):
        """Test PER_EXTENSION scope: counters reset for different extensions."""
        modules_data = [
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.PER_EXTENSION.value,
            }
        ]

        results = []
        for idx, file in enumerate(sample_files):
            new_name = apply_rename_modules(
                modules_data, idx, file, metadata_cache=None, all_files=sample_files
            )
            basename = os.path.splitext(new_name)[0]
            ext = os.path.splitext(file.filename)[1]
            results.append((basename, ext))

        # Should be: .jpg: 001, 002, .png: 001, .jpg: 003, .txt: 001
        assert results[0] == ("001", ".jpg")  # file1.jpg
        assert results[1] == ("002", ".jpg")  # file2.jpg
        assert results[2] == ("001", ".png")  # file3.png (reset - different ext!)
        assert results[3] == ("003", ".jpg")  # file4.jpg (continue .jpg sequence)
        assert results[4] == ("001", ".txt")  # file5.txt (reset - different ext!)

    def test_scope_aware_index_calculation_global(self, sample_files):
        """Test calculate_scope_aware_index with GLOBAL scope."""
        for i in range(len(sample_files)):
            index = calculate_scope_aware_index(
                CounterScope.GLOBAL.value, i, sample_files[i], sample_files
            )
            assert index == i  # Should return unchanged

    def test_scope_aware_index_calculation_per_folder(self, sample_files):
        """Test calculate_scope_aware_index with PER_FOLDER scope."""
        # folder_a has 3 files (indices 0, 1, 2)
        # folder_b has 2 files (indices 3, 4)

        # Folder A files
        assert (
            calculate_scope_aware_index(
                CounterScope.PER_FOLDER.value, 0, sample_files[0], sample_files
            )
            == 0
        )
        assert (
            calculate_scope_aware_index(
                CounterScope.PER_FOLDER.value, 1, sample_files[1], sample_files
            )
            == 1
        )
        assert (
            calculate_scope_aware_index(
                CounterScope.PER_FOLDER.value, 2, sample_files[2], sample_files
            )
            == 2
        )

        # Folder B files (should reset)
        assert (
            calculate_scope_aware_index(
                CounterScope.PER_FOLDER.value, 3, sample_files[3], sample_files
            )
            == 0
        )  # Reset!
        assert (
            calculate_scope_aware_index(
                CounterScope.PER_FOLDER.value, 4, sample_files[4], sample_files
            )
            == 1
        )

    def test_scope_aware_index_calculation_per_extension(self, sample_files):
        """Test calculate_scope_aware_index with PER_EXTENSION scope."""
        # .jpg: indices 0, 1, 3 (file1, file2, file4)
        # .png: index 2 (file3)
        # .txt: index 4 (file5)

        assert (
            calculate_scope_aware_index(
                CounterScope.PER_EXTENSION.value, 0, sample_files[0], sample_files
            )
            == 0
        )  # First .jpg
        assert (
            calculate_scope_aware_index(
                CounterScope.PER_EXTENSION.value, 1, sample_files[1], sample_files
            )
            == 1
        )  # Second .jpg
        assert (
            calculate_scope_aware_index(
                CounterScope.PER_EXTENSION.value, 2, sample_files[2], sample_files
            )
            == 0
        )  # First .png
        assert (
            calculate_scope_aware_index(
                CounterScope.PER_EXTENSION.value, 3, sample_files[3], sample_files
            )
            == 2
        )  # Third .jpg
        assert (
            calculate_scope_aware_index(
                CounterScope.PER_EXTENSION.value, 4, sample_files[4], sample_files
            )
            == 0
        )  # First .txt

    def test_counter_with_start_and_step_per_folder(self, sample_files):
        """Test counter with custom start/step values in PER_FOLDER scope."""
        modules_data = [
            {
                "type": "counter",
                "start": 10,
                "step": 5,
                "padding": 3,
                "scope": CounterScope.PER_FOLDER.value,
            }
        ]

        results = []
        for idx, file in enumerate(sample_files):
            new_name = apply_rename_modules(
                modules_data, idx, file, metadata_cache=None, all_files=sample_files
            )
            basename = os.path.splitext(new_name)[0]
            results.append(basename)

        # folder_a: 010, 015, 020, folder_b: 010, 015 (reset at folder boundary)
        assert results == ["010", "015", "020", "010", "015"]

    def test_mixed_modules_with_scope(self, sample_files):
        """Test counter scope works with other modules."""
        modules_data = [
            {"type": "specified_text", "text": "photo"},
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 2,
                "scope": CounterScope.PER_FOLDER.value,
            },
        ]

        results = []
        for idx, file in enumerate(sample_files):
            new_name = apply_rename_modules(
                modules_data, idx, file, metadata_cache=None, all_files=sample_files
            )
            basename = os.path.splitext(new_name)[0]
            results.append(basename)

        # Should be: photo01, photo02, photo03 (folder_a), photo01, photo02 (folder_b - reset!)
        assert results == ["photo01", "photo02", "photo03", "photo01", "photo02"]

    def test_counter_without_all_files_falls_back_to_global(self, sample_files):
        """Test that counter without all_files parameter falls back to global index."""
        modules_data = [
            {
                "type": "counter",
                "start": 1,
                "step": 1,
                "padding": 3,
                "scope": CounterScope.PER_FOLDER.value,
            }
        ]

        # Call without all_files - should use global index as fallback
        results = []
        for idx, file in enumerate(sample_files):
            new_name = apply_rename_modules(
                modules_data,
                idx,
                file,
                metadata_cache=None,
                all_files=None,  # No files list!
            )
            basename = os.path.splitext(new_name)[0]
            results.append(basename)

        # Should fallback to global sequence: 001, 002, 003, 004, 005
        assert results == ["001", "002", "003", "004", "005"]
