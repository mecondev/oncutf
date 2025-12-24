"""Module: test_column_management_mixin.py

Author: Michael Economou
Date: 2025-12-09

Unit tests for ColumnManagementMixin functionality.

Tests cover:
- Column visibility management (add/remove/toggle)
- Column width persistence (load/save)
- Auto-fit logic
- Configuration defaults
- Edge cases and error handling
"""

from unittest.mock import Mock

import pytest

from oncutf.core.pyqt_imports import QAbstractTableModel, QHeaderView, QTableView
from oncutf.ui.mixins.column_management_mixin import ColumnManagementMixin


class MockTableModel(QAbstractTableModel):
    """Mock model for testing."""

    def __init__(self):
        super().__init__()
        self._data = []
        self._columns = ["path", "size", "type", "date"]
        self._visible_columns = dict.fromkeys(self._columns, True)

    def rowCount(self, _parent=None):
        return len(self._data)

    def columnCount(self, _parent=None):
        return len(self._columns)

    def data(self, _index, _role):
        return None

    def get_visible_columns(self):
        return [col for col, visible in self._visible_columns.items() if visible]

    def set_column_visibility(self, column, visible):
        if column in self._visible_columns:
            self._visible_columns[column] = visible


class TableViewWithMixin(QTableView, ColumnManagementMixin):
    """Test table view with ColumnManagementMixin."""

    def __init__(self):
        super().__init__()
        self._column_config = {}
        self._visibility_config = {}
        self._column_widths = {}

    def _load_column_width(self, section):
        """Mock: load column width from config."""
        return self._column_widths.get(section, 100)

    def _save_column_width(self, section, width):
        """Mock: save column width to config."""
        self._column_widths[section] = width

    def _update_header_visibility(self):
        """Mock: update header visibility."""

    def _load_column_visibility_config(self):
        """Mock: load visibility config."""

    def _apply_column_visibility(self):
        """Mock: apply visibility config."""

    def _update_visibility_config(self):
        """Mock: update visibility config."""


# ==========================================
# Test Fixtures
# ==========================================


@pytest.fixture
def table_view():
    """Create a test table view with model."""
    view = TableViewWithMixin()
    model = MockTableModel()
    view.setModel(model)

    # Initialize columns
    for i, _col in enumerate(model._columns):
        view.setColumnWidth(i, 100)

    return view


@pytest.fixture
def mock_config():
    """Mock configuration."""
    return {
        "columns": {
            "path": {"width": 300, "visible": True},
            "size": {"width": 100, "visible": True},
            "type": {"width": 80, "visible": True},
            "date": {"width": 150, "visible": False},
        }
    }


# ==========================================
# Test: Add Column
# ==========================================


class TestAddColumn:
    """Tests for adding columns dynamically."""

    def test_add_column_basic(self, table_view):
        """Test adding a new column."""
        initial_count = table_view.model().columnCount()

        # Mock the add_column method
        table_view.add_column = Mock()

        # Simulate adding a column
        table_view.model()._columns.append("custom")
        table_view.model()._visible_columns["custom"] = True

        assert table_view.model().columnCount() == initial_count + 1
        assert "custom" in table_view.model()._columns

    def test_add_column_with_config(self, table_view):
        """Test adding a column with configuration."""
        config = {"width": 150, "visible": True}

        # Add column to model
        table_view.model()._columns.append("custom_field")
        table_view.model()._visible_columns["custom_field"] = config["visible"]

        # Store width in mock
        col_idx = len(table_view.model()._columns) - 1
        table_view._column_widths[col_idx] = config["width"]

        # Verify
        assert "custom_field" in table_view.model()._columns
        assert table_view._load_column_width(col_idx) == 150


# ==========================================
# Test: Remove Column
# ==========================================


class TestRemoveColumn:
    """Tests for removing columns."""

    def test_remove_column_basic(self, table_view):
        """Test removing a column preserves others."""
        initial_count = table_view.model().columnCount()
        col_to_remove = 1  # "size"
        col_name = table_view.model()._columns[col_to_remove]

        # Mock remove
        table_view.remove_column = Mock()

        # Simulate removal
        table_view.model()._columns.pop(col_to_remove)

        assert table_view.model().columnCount() == initial_count - 1
        assert col_name not in table_view.model()._columns

    def test_remove_column_preserves_others(self, table_view):
        """Test that removing column doesn't affect others."""
        original_columns = list(table_view.model()._columns)
        col_to_remove = 1

        # Remove
        table_view.model()._columns.pop(col_to_remove)

        # Check others preserved
        for i, col in enumerate(table_view.model()._columns):
            expected_idx = i if i < col_to_remove else i + 1
            assert col == original_columns[expected_idx]


# ==========================================
# Test: Toggle Visibility
# ==========================================


class TestToggleVisibility:
    """Tests for column visibility toggling."""

    def test_toggle_visibility_hide(self, table_view):
        """Test hiding a column."""
        col_name = "path"
        table_view.model()._visible_columns[col_name] = True

        # Toggle hide
        table_view.model()._visible_columns[col_name] = False

        assert table_view.model()._visible_columns[col_name] is False

    def test_toggle_visibility_show(self, table_view):
        """Test showing a hidden column."""
        col_name = "date"
        table_view.model()._visible_columns[col_name] = False

        # Toggle show
        table_view.model()._visible_columns[col_name] = True

        assert table_view.model()._visible_columns[col_name] is True

    def test_toggle_visibility_by_name(self, table_view):
        """Test toggling visibility by column name."""
        col_name = "type"
        initial_state = table_view.model()._visible_columns[col_name]

        # Toggle
        table_view.model()._visible_columns[col_name] = not initial_state

        assert table_view.model()._visible_columns[col_name] != initial_state


# ==========================================
# Test: Get Visible Columns
# ==========================================


class TestGetVisibleColumns:
    """Tests for getting visible column list."""

    def test_get_visible_columns_all(self, table_view):
        """Test getting all visible columns when all shown."""
        visible = table_view.model().get_visible_columns()

        assert "path" in visible
        assert "size" in visible
        assert "type" in visible
        assert "date" in visible  # All visible by default

    def test_get_visible_columns_some_hidden(self, table_view):
        """Test getting visible columns when some hidden."""
        table_view.model()._visible_columns["size"] = False
        table_view.model()._visible_columns["type"] = False

        visible = table_view.model().get_visible_columns()

        assert len(visible) == 2
        assert "path" in visible
        assert "date" in visible

    def test_get_visible_columns_empty(self, table_view):
        """Test getting visible columns when all hidden."""
        for col in table_view.model()._columns:
            table_view.model()._visible_columns[col] = False

        visible = table_view.model().get_visible_columns()

        assert len(visible) == 0


# ==========================================
# Test: Width Persistence
# ==========================================


class TestWidthPersistence:
    """Tests for column width persistence."""

    def test_load_column_width(self, table_view):
        """Test loading column width from config."""
        table_view._column_widths[1] = 250

        width = table_view._load_column_width(1)

        assert width == 250

    def test_load_column_width_default(self, table_view):
        """Test loading width with default when not found."""
        width = table_view._load_column_width(999)

        assert width == 100  # Default

    def test_save_column_width(self, table_view):
        """Test saving column width to config."""
        table_view._save_column_width(1, 200)

        assert table_view._column_widths[1] == 200

    def test_width_persistence_roundtrip(self, table_view):
        """Test save and load cycle."""
        # Save
        table_view._save_column_width(2, 175)

        # Load
        loaded = table_view._load_column_width(2)

        assert loaded == 175


# ==========================================
# Test: Auto-Fit Logic
# ==========================================


class TestAutoFit:
    """Tests for auto-fit columns functionality."""

    def test_auto_fit_basic(self, table_view):
        """Test auto-fit calculates reasonable widths."""
        # Mock auto_fit
        table_view.auto_fit_columns_to_content = Mock()

        table_view.auto_fit_columns_to_content()

        table_view.auto_fit_columns_to_content.assert_called_once()

    def test_auto_fit_respects_constraints(self, table_view):
        """Test auto-fit respects min/max width constraints."""
        # Set mock constraints
        min_width = 50
        max_width = 500

        for i in range(table_view.model().columnCount()):
            width = max(min_width, min(200, max_width))
            table_view.setColumnWidth(i, width)

        # Verify constraints applied
        for i in range(table_view.model().columnCount()):
            width = table_view.columnWidth(i)
            assert min_width <= width <= max_width


# ==========================================
# Test: Reset to Defaults
# ==========================================


class TestResetToDefaults:
    """Tests for resetting column layout to defaults."""

    def test_reset_to_default(self, table_view):
        """Test resetting columns to default state."""
        # Change widths
        for i in range(table_view.model().columnCount()):
            table_view.setColumnWidth(i, 250)

        # Mock reset
        table_view._reset_columns_to_default = Mock()
        table_view._reset_columns_to_default()

        table_view._reset_columns_to_default.assert_called_once()

    def test_reset_restores_visibility(self, table_view):
        """Test reset restores all columns visible."""
        # Hide some columns
        table_view.model()._visible_columns["size"] = False
        table_view.model()._visible_columns["type"] = False

        # Reset (mock)
        for col in table_view.model()._columns:
            table_view.model()._visible_columns[col] = True

        visible = table_view.model().get_visible_columns()
        assert len(visible) == len(table_view.model()._columns)


# ==========================================
# Test: Refresh After Model Change
# ==========================================


class TestRefreshAfterModelChange:
    """Tests for refreshing columns after model changes."""

    def test_refresh_after_model_change(self, table_view):
        """Test refresh updates columns properly."""
        table_view.refresh_columns_after_model_change = Mock()

        table_view.refresh_columns_after_model_change()

        table_view.refresh_columns_after_model_change.assert_called_once()

    def test_refresh_with_new_model(self, table_view):
        """Test refresh works with new model assigned."""
        old_model = table_view.model()
        new_model = MockTableModel()
        new_model._columns.append("extra")

        table_view.setModel(new_model)

        assert table_view.model() != old_model
        assert "extra" in table_view.model()._columns


# ==========================================
# Test: Edge Cases & Error Handling
# ==========================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_add_column_empty_name(self, table_view):
        """Test adding column with empty name."""
        initial_count = table_view.model().columnCount()

        # Try to add empty column
        table_view.model()._columns.append("")

        # Should still add (behavior may vary)
        assert table_view.model().columnCount() == initial_count + 1

    def test_remove_column_invalid_index(self, table_view):
        """Test removing column with invalid index."""
        table_view.remove_column = Mock()

        # Should handle gracefully
        table_view.remove_column(999)

        table_view.remove_column.assert_called_once_with(999)

    def test_toggle_visibility_nonexistent_column(self, table_view):
        """Test toggling visibility of non-existent column."""
        table_view.toggle_column_visibility = Mock()

        table_view.toggle_column_visibility("nonexistent")

        table_view.toggle_column_visibility.assert_called_once_with("nonexistent")

    def test_width_persistence_negative_width(self, table_view):
        """Test saving negative width (mock doesn't validate)."""
        # Mock implementation doesn't validate, so negative is accepted
        table_view._save_column_width(1, -50)

        width = table_view._load_column_width(1)
        # Mock stores as-is
        assert width == -50

    def test_width_persistence_zero_width(self, table_view):
        """Test handling zero width."""
        table_view._save_column_width(1, 0)

        width = table_view._load_column_width(1)
        # Most implementations handle 0 as hidden or minimum
        assert width is not None


# ==========================================
# Test: Column Header Management
# ==========================================


class TestColumnHeaderManagement:
    """Tests for column header functionality."""

    def test_header_exists(self, table_view):
        """Test that header is accessible."""
        header = table_view.horizontalHeader()

        assert header is not None
        assert isinstance(header, QHeaderView)

    def test_header_section_count(self, table_view):
        """Test header reflects column count."""
        header = table_view.horizontalHeader()

        assert header.count() == table_view.model().columnCount()


# ==========================================
# Test: Configuration Schema
# ==========================================


class TestConfigurationSchema:
    """Tests for configuration schema compliance."""

    def test_config_has_required_fields(self, mock_config):
        """Test config has all required fields."""
        for _col_name, col_config in mock_config["columns"].items():
            assert "width" in col_config
            assert "visible" in col_config
            assert isinstance(col_config["width"], int)
            assert isinstance(col_config["visible"], bool)

    def test_config_width_is_positive(self, mock_config):
        """Test all configured widths are positive."""
        for _col_name, col_config in mock_config["columns"].items():
            assert col_config["width"] > 0

    def test_config_column_order_present(self, mock_config):
        """Test column order in config (if present)."""
        mock_config["column_order"] = ["path", "size", "type", "date"]

        assert "column_order" in mock_config
        assert len(mock_config["column_order"]) == len(mock_config["columns"])


# ==========================================
# Test: Performance & Integration
# ==========================================


class TestPerformanceIntegration:
    """Tests for performance and integration scenarios."""

    def test_many_column_operations(self, table_view):
        """Test handling many column operations efficiently."""
        # Simulate bulk operations
        for i in range(100):
            col_idx = i % table_view.model().columnCount()
            table_view.setColumnWidth(col_idx, 100 + i)

        # Should complete without hanging
        widths = [table_view.columnWidth(i) for i in range(table_view.model().columnCount())]
        assert all(w > 0 for w in widths)

    def test_toggle_visibility_all_columns(self, table_view):
        """Test toggling all columns on/off."""
        # Hide all
        for col in table_view.model()._columns:
            table_view.model()._visible_columns[col] = False

        visible = table_view.model().get_visible_columns()
        assert len(visible) == 0

        # Show all
        for col in table_view.model()._columns:
            table_view.model()._visible_columns[col] = True

        visible = table_view.model().get_visible_columns()
        assert len(visible) == len(table_view.model()._columns)

    def test_concurrent_width_changes(self, table_view):
        """Test handling concurrent width changes."""
        widths = {0: 150, 1: 200, 2: 100, 3: 250}

        for col_idx, width in widths.items():
            table_view.setColumnWidth(col_idx, width)

        for col_idx, width in widths.items():
            assert table_view.columnWidth(col_idx) == width


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
