"""test_selection_provider.py

Test suite for SelectionProvider unified selection interface.
"""

from datetime import datetime

from oncutf.models.file_item import FileItem
from oncutf.ui.helpers.selection_provider import (
    SelectionProvider,
    get_checked_files,
    get_selected_files,
    get_selected_rows,
    get_single_selected_file,
    has_selection,
)


class MockSelectionModel:
    """Mock Qt selection model."""

    def __init__(self, selected_rows: list[int]):
        self._selected_rows = selected_rows

    def selectedRows(self):
        class MockIndex:
            def __init__(self, row):
                self._row = row

            def row(self):
                return self._row

        return [MockIndex(row) for row in self._selected_rows]


class MockFileListView:
    """Mock file table view."""

    def __init__(self, selected_rows: list[int]):
        self._selection_model = MockSelectionModel(selected_rows)

    def selectionModel(self):
        return self._selection_model


class MockFileModel:
    """Mock file model."""

    def __init__(self, files: list[FileItem]):
        self.files = files


class MockSelectionStore:
    """Mock selection store."""

    def __init__(self, selected_rows: set[int]):
        self._selected_rows = selected_rows

    def get_selected_rows(self):
        return self._selected_rows.copy()

    def get_selection_count(self):
        return len(self._selected_rows)


class MockTableManager:
    """Mock table manager."""

    def __init__(self, selected_files: list[FileItem]):
        self._selected_files = selected_files

    def get_selected_files(self):
        return self._selected_files


class MockParentWindow:
    """Mock parent window with various selection methods."""

    def __init__(self):
        # Create test files
        self.files = [
            FileItem(path=f"/path/file{i}.txt", extension="txt", modified=datetime.now())
            for i in range(5)
        ]

        # Set up file model
        self.file_model = MockFileModel(self.files)

        # Default: no selection
        self.file_list_view = None
        self.selection_store = None
        self.table_manager = None

    def setup_selection_model(self, selected_rows: list[int]):
        """Set up Qt selection model."""
        self.file_list_view = MockFileListView(selected_rows)

    def setup_selection_store(self, selected_rows: set[int]):
        """Set up selection store."""
        self.selection_store = MockSelectionStore(selected_rows)

    def setup_table_manager(self, selected_files: list[FileItem]):
        """Set up table manager."""
        self.table_manager = MockTableManager(selected_files)

    def set_checked_state(self, checked_rows: list[int]):
        """Set checked state for files."""
        for i, file in enumerate(self.files):
            file.checked = i in checked_rows


class TestSelectionProviderBasic:
    """Test basic SelectionProvider functionality."""

    def setup_method(self):
        """Clear cache before each test."""
        SelectionProvider.clear_cache()

    def test_empty_parent_window(self):
        """Test with None parent window."""
        result = SelectionProvider.get_selected_files(None)
        assert result == []

    def test_via_table_manager(self):
        """Test selection via table manager (preferred)."""
        parent = MockParentWindow()
        selected = [parent.files[0], parent.files[2]]
        parent.setup_table_manager(selected)

        result = SelectionProvider.get_selected_files(parent)

        assert len(result) == 2
        assert result[0] == parent.files[0]
        assert result[1] == parent.files[2]

    def test_via_selection_model(self):
        """Test selection via Qt selection model."""
        parent = MockParentWindow()
        parent.setup_selection_model([1, 3])  # Select rows 1 and 3

        result = SelectionProvider.get_selected_files(parent)

        assert len(result) == 2
        assert result[0] == parent.files[1]
        assert result[1] == parent.files[3]

    def test_via_checked_state(self):
        """Test selection via checked state (fallback)."""
        parent = MockParentWindow()
        parent.set_checked_state([0, 4])  # Check rows 0 and 4

        result = SelectionProvider.get_selected_files(parent)

        assert len(result) == 2
        assert parent.files[0] in result
        assert parent.files[4] in result


class TestSelectionProviderRows:
    """Test row-based selection queries."""

    def setup_method(self):
        """Clear cache before each test."""
        SelectionProvider.clear_cache()

    def test_get_selected_rows_via_store(self):
        """Test getting selected rows via SelectionStore."""
        parent = MockParentWindow()
        parent.setup_selection_store({0, 2, 4})

        result = SelectionProvider.get_selected_rows(parent)

        assert result == {0, 2, 4}

    def test_get_selected_rows_via_model(self):
        """Test getting selected rows via selection model."""
        parent = MockParentWindow()
        parent.setup_selection_model([1, 3])

        result = SelectionProvider.get_selected_rows(parent)

        assert result == {1, 3}

    def test_get_selected_rows_empty(self):
        """Test getting selected rows when nothing selected."""
        parent = MockParentWindow()

        result = SelectionProvider.get_selected_rows(parent)

        assert result == set()


class TestSelectionProviderCaching:
    """Test caching behavior."""

    def setup_method(self):
        """Clear cache before each test."""
        SelectionProvider.clear_cache()

    def test_cache_hit_selected_files(self):
        """Test that second call uses cache."""
        parent = MockParentWindow()
        parent.setup_table_manager([parent.files[0]])

        # First call
        result1 = SelectionProvider.get_selected_files(parent)

        # Second call (should use cache)
        result2 = SelectionProvider.get_selected_files(parent)

        assert result1 is result2  # Same object (cached)

    def test_cache_hit_selected_rows(self):
        """Test that row cache works."""
        parent = MockParentWindow()
        parent.setup_selection_store({1, 2})

        # First call
        result1 = SelectionProvider.get_selected_rows(parent)

        # Second call (should use cache)
        result2 = SelectionProvider.get_selected_rows(parent)

        assert result1 is result2  # Same object (cached)

    def test_cache_clear(self):
        """Test cache clearing."""
        parent = MockParentWindow()
        parent.setup_table_manager([parent.files[0]])

        # First call
        result1 = SelectionProvider.get_selected_files(parent)
        assert len(result1) == 1

        # Clear cache
        SelectionProvider.clear_cache()

        # Change underlying selection
        parent.setup_table_manager([parent.files[1], parent.files[2]])

        # Second call (should not use cache, should reflect new selection)
        result2 = SelectionProvider.get_selected_files(parent)

        # Results are different because cache was cleared
        assert len(result2) == 2
        assert result1 != result2


class TestSelectionProviderChecked:
    """Test checked state queries."""

    def setup_method(self):
        """Clear cache before each test."""
        SelectionProvider.clear_cache()

    def test_get_checked_files(self):
        """Test getting checked files."""
        parent = MockParentWindow()
        parent.set_checked_state([0, 2, 4])

        result = SelectionProvider.get_checked_files(parent)

        assert len(result) == 3
        assert parent.files[0] in result
        assert parent.files[2] in result
        assert parent.files[4] in result

    def test_get_checked_files_none(self):
        """Test when no files are checked."""
        parent = MockParentWindow()
        parent.set_checked_state([])

        result = SelectionProvider.get_checked_files(parent)

        assert result == []


class TestSelectionProviderHelpers:
    """Test helper methods."""

    def setup_method(self):
        """Clear cache before each test."""
        SelectionProvider.clear_cache()

    def test_get_selection_count(self):
        """Test selection count via get_selected_files."""
        parent = MockParentWindow()
        # Use table_manager which returns actual FileItem objects
        selected_files = [parent.files[0], parent.files[1], parent.files[2]]
        parent.setup_table_manager(selected_files)

        files = SelectionProvider.get_selected_files(parent)
        count = len(files)

        assert count == 3

    def test_has_selection_true(self):
        """Test has_selection when files selected."""
        parent = MockParentWindow()
        parent.setup_table_manager([parent.files[0]])

        assert SelectionProvider.has_selection(parent) is True

    def test_has_selection_false(self):
        """Test has_selection when no files selected."""
        parent = MockParentWindow()

        assert SelectionProvider.has_selection(parent) is False

    def test_get_single_selected_file(self):
        """Test getting single selected file."""
        parent = MockParentWindow()
        parent.setup_table_manager([parent.files[2]])

        result = SelectionProvider.get_single_selected_file(parent)

        assert result == parent.files[2]

    def test_get_single_selected_file_multiple(self):
        """Test when multiple files selected."""
        parent = MockParentWindow()
        parent.setup_table_manager([parent.files[0], parent.files[1]])

        result = SelectionProvider.get_single_selected_file(parent)

        assert result is None

    def test_get_single_selected_file_none(self):
        """Test when no files selected."""
        parent = MockParentWindow()

        result = SelectionProvider.get_single_selected_file(parent)

        assert result is None


class TestConvenienceFunctions:
    """Test convenience functions."""

    def setup_method(self):
        """Clear cache before each test."""
        SelectionProvider.clear_cache()

    def test_get_selected_files_function(self):
        """Test get_selected_files convenience function."""
        parent = MockParentWindow()
        parent.setup_table_manager([parent.files[0]])

        result = get_selected_files(parent)

        assert len(result) == 1
        assert result[0] == parent.files[0]

    def test_get_selected_rows_function(self):
        """Test get_selected_rows convenience function."""
        parent = MockParentWindow()
        parent.setup_selection_store({1, 2})

        result = get_selected_rows(parent)

        assert result == {1, 2}

    def test_get_checked_files_function(self):
        """Test get_checked_files convenience function."""
        parent = MockParentWindow()
        parent.set_checked_state([0, 4])

        result = get_checked_files(parent)

        assert len(result) == 2

    def test_has_selection_function(self):
        """Test has_selection convenience function."""
        parent = MockParentWindow()
        parent.setup_table_manager([parent.files[0]])

        assert has_selection(parent) is True

    def test_get_single_selected_file_function(self):
        """Test get_single_selected_file convenience function."""
        parent = MockParentWindow()
        parent.setup_table_manager([parent.files[3]])

        result = get_single_selected_file(parent)

        assert result == parent.files[3]


class TestSelectionProviderFallback:
    """Test fallback strategies."""

    def setup_method(self):
        """Clear cache before each test."""
        SelectionProvider.clear_cache()

    def test_strategy_fallback_order(self):
        """Test that strategies are tried in correct order."""
        parent = MockParentWindow()

        # Setup both table_manager and selection_model
        parent.setup_table_manager([parent.files[0]])  # Should be used
        parent.setup_selection_model([1, 2])  # Should be ignored

        result = SelectionProvider.get_selected_files(parent)

        # Should use table_manager (higher priority)
        assert len(result) == 1
        assert result[0] == parent.files[0]

    def test_all_strategies_fail(self):
        """Test when all strategies fail."""

        # Create empty parent with no selection mechanisms
        class EmptyParent:
            pass

        parent = EmptyParent()
        result = SelectionProvider.get_selected_files(parent)

        assert result == []
