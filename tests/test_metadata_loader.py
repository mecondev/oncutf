"""Module: test_metadata_loader.py

Author: Michael Economou
Date: 2025-12-21

Unit tests for MetadataLoader.

Tests cover:
- Loading mode determination
- Cancellation management
- Cache filtering logic
- Single vs multiple file loading paths
"""

from __future__ import annotations

from unittest.mock import MagicMock


class TestLoadingModeDetermination:
    """Tests for loading mode determination logic."""

    def test_single_file_uses_wait_cursor(self) -> None:
        """Single file should use wait_cursor mode."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()
        mode = loader.determine_loading_mode(file_count=1)

        assert mode == "single_file_wait_cursor"

    def test_two_files_uses_dialog(self) -> None:
        """Two files should use progress dialog mode."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()
        mode = loader.determine_loading_mode(file_count=2)

        assert mode == "multiple_files_dialog"

    def test_many_files_uses_dialog(self) -> None:
        """Many files should use progress dialog mode."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()
        mode = loader.determine_loading_mode(file_count=100)

        assert mode == "multiple_files_dialog"

    def test_zero_files_uses_dialog(self) -> None:
        """Zero files should technically use dialog mode (edge case)."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()
        mode = loader.determine_loading_mode(file_count=0)

        assert mode == "multiple_files_dialog"


class TestCancellationManagement:
    """Tests for cancellation flag management."""

    def test_initial_state_not_cancelled(self) -> None:
        """Initial state should not be cancelled."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()

        assert loader.is_cancelled() is False

    def test_request_cancellation_sets_flag(self) -> None:
        """Requesting cancellation should set the flag."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()
        loader.request_cancellation()

        assert loader.is_cancelled() is True

    def test_reset_clears_cancellation(self) -> None:
        """Reset should clear the cancellation flag."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()
        loader.request_cancellation()
        assert loader.is_cancelled() is True

        loader.reset_cancellation_flag()
        assert loader.is_cancelled() is False

    def test_multiple_cancellation_requests(self) -> None:
        """Multiple cancellation requests should be idempotent."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()
        loader.request_cancellation()
        loader.request_cancellation()
        loader.request_cancellation()

        assert loader.is_cancelled() is True


class TestLoadMetadataForItems:
    """Tests for the main loading entry point."""

    def test_empty_items_returns_early(self) -> None:
        """Empty items list should return early without error."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()

        # Should not raise
        loader.load_metadata_for_items(items=[], use_extended=False)

    def test_on_finished_called_for_empty_items(self) -> None:
        """on_finished callback should NOT be called for empty items."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()
        callback = MagicMock()

        loader.load_metadata_for_items(items=[], use_extended=False, on_finished=callback)

        # Empty items returns early without calling callback
        callback.assert_not_called()


class TestExifToolWrapperProperty:
    """Tests for exiftool_wrapper property."""

    def test_uses_getter_function(self) -> None:
        """Should use the getter function if provided."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        mock_wrapper = MagicMock()
        getter = MagicMock(return_value=mock_wrapper)

        loader = MetadataLoader(exiftool_getter=getter)

        result = loader.exiftool_wrapper

        getter.assert_called_once()
        assert result is mock_wrapper

    def test_creates_wrapper_if_no_getter(self) -> None:
        """Should create new wrapper if no getter provided."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader
        from oncutf.utils.shared.exiftool_wrapper import ExifToolWrapper

        loader = MetadataLoader(exiftool_getter=None)

        result = loader.exiftool_wrapper

        # Should return an ExifToolWrapper instance
        assert isinstance(result, ExifToolWrapper)


class TestParallelLoaderProperty:
    """Tests for lazy parallel loader initialization."""

    def test_lazy_initialization(self) -> None:
        """Parallel loader should be lazily initialized."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()

        # Initially None
        assert loader._parallel_loader is None

    def test_initializes_on_first_access(self) -> None:
        """Should initialize ParallelMetadataLoader on first access."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader
        from oncutf.core.metadata.parallel_loader import ParallelMetadataLoader

        loader = MetadataLoader()

        result = loader.parallel_loader

        assert isinstance(result, ParallelMetadataLoader)
        assert loader._parallel_loader is result

    def test_reuses_existing_instance(self) -> None:
        """Should reuse existing instance on subsequent access."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader()

        # First access
        result1 = loader.parallel_loader
        # Second access
        result2 = loader.parallel_loader

        # Should be same instance
        assert result1 is result2


class TestParentWindowProperty:
    """Tests for parent_window property."""

    def test_getter_returns_set_value(self) -> None:
        """Getter should return the set parent window."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        mock_window = MagicMock()
        loader = MetadataLoader(parent_window=mock_window)

        assert loader.parent_window is mock_window

    def test_setter_updates_value(self) -> None:
        """Setter should update the parent window."""
        from oncutf.core.metadata.metadata_loader import MetadataLoader

        loader = MetadataLoader(parent_window=None)
        assert loader.parent_window is None

        new_window = MagicMock()
        loader.parent_window = new_window

        assert loader.parent_window is new_window
