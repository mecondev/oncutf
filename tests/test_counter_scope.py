"""
Tests for CounterScope and CounterModule scope support.

Author: Michael Economou
Date: 2025-12-16
"""


from oncutf.models.counter_scope import CounterScope
from oncutf.modules.counter_module import CounterModule


class TestCounterScope:
    """Test CounterScope enum."""

    def test_scope_values(self):
        """Test that all scope values are defined correctly."""
        assert CounterScope.GLOBAL.value == "global"
        assert CounterScope.PER_FOLDER.value == "per_folder"
        assert CounterScope.PER_SELECTION.value == "per_selection"

    def test_scope_str(self):
        """Test string representation of CounterScope."""
        assert str(CounterScope.GLOBAL) == "global"
        assert str(CounterScope.PER_FOLDER) == "per_folder"
        assert str(CounterScope.PER_SELECTION) == "per_selection"

    def test_scope_display_name(self):
        """Test display names for UI."""
        assert CounterScope.GLOBAL.display_name == "Global (all files)"
        assert CounterScope.PER_FOLDER.display_name == "Per Folder"
        assert CounterScope.PER_SELECTION.display_name == "Per Selection"

    def test_scope_description(self):
        """Test descriptions."""
        assert "Single counter" in CounterScope.GLOBAL.description
        assert "Reset counter at folder" in CounterScope.PER_FOLDER.description
        assert "Reset counter for each selection" in CounterScope.PER_SELECTION.description


class TestCounterModuleScope:
    """Test CounterModule with scope support."""

    def test_counter_module_default_scope(self, qtbot):
        """Test that counter module defaults to PER_FOLDER scope."""
        counter = CounterModule()
        qtbot.addWidget(counter)

        data = counter.get_data()

        assert "scope" in data
        assert data["scope"] == CounterScope.PER_FOLDER.value

    def test_counter_module_scope_selection(self, qtbot):
        """Test that scope can be changed via combobox."""
        counter = CounterModule()
        qtbot.addWidget(counter)

        # Change to GLOBAL scope
        counter.scope_combo.setCurrentIndex(0)  # GLOBAL is index 0
        data = counter.get_data()

        assert data["scope"] == CounterScope.GLOBAL.value

        # Change to PER_SELECTION scope
        counter.scope_combo.setCurrentIndex(2)  # PER_SELECTION is index 2
        data = counter.get_data()

        assert data["scope"] == CounterScope.PER_SELECTION.value

    def test_counter_apply_with_scope_global(self):
        """Test counter with GLOBAL scope (legacy behavior)."""
        data = {
            "type": "counter",
            "start": 1,
            "padding": 3,
            "step": 1,
            "scope": CounterScope.GLOBAL.value
        }

        # Simulate 3 files with global index
        result1 = CounterModule.apply_from_data(data, None, index=0)
        result2 = CounterModule.apply_from_data(data, None, index=1)
        result3 = CounterModule.apply_from_data(data, None, index=2)

        assert result1 == "001"
        assert result2 == "002"
        assert result3 == "003"

    def test_counter_apply_with_scope_per_folder(self):
        """Test counter with PER_FOLDER scope (index should reset per folder)."""
        data = {
            "type": "counter",
            "start": 1,
            "padding": 3,
            "step": 1,
            "scope": CounterScope.PER_FOLDER.value
        }

        # Folder 1: indices 0, 1, 2
        folder1_file1 = CounterModule.apply_from_data(data, None, index=0)
        folder1_file2 = CounterModule.apply_from_data(data, None, index=1)
        folder1_file3 = CounterModule.apply_from_data(data, None, index=2)

        # Folder 2: indices reset to 0, 1, 2 (preview engine's responsibility)
        folder2_file1 = CounterModule.apply_from_data(data, None, index=0)
        folder2_file2 = CounterModule.apply_from_data(data, None, index=1)

        assert folder1_file1 == "001"
        assert folder1_file2 == "002"
        assert folder1_file3 == "003"
        assert folder2_file1 == "001"  # Reset to 001 (same as folder1_file1)
        assert folder2_file2 == "002"  # Same as folder1_file2

    def test_counter_with_custom_start_and_step(self):
        """Test counter with custom start value and step."""
        data = {
            "type": "counter",
            "start": 10,
            "padding": 4,
            "step": 5,
            "scope": CounterScope.PER_FOLDER.value
        }

        result1 = CounterModule.apply_from_data(data, None, index=0)
        result2 = CounterModule.apply_from_data(data, None, index=1)
        result3 = CounterModule.apply_from_data(data, None, index=2)

        assert result1 == "0010"  # 10 + 0*5
        assert result2 == "0015"  # 10 + 1*5
        assert result3 == "0020"  # 10 + 2*5

    def test_counter_backward_compatibility(self):
        """Test that counter works without scope (backward compatibility)."""
        data = {
            "type": "counter",
            "start": 1,
            "padding": 3,
            "step": 1
            # No scope provided - should default to PER_FOLDER
        }

        result = CounterModule.apply_from_data(data, None, index=5)

        assert result == "006"  # 1 + 5*1


class TestCounterModuleEmitSignals:
    """Test that CounterModule emits signals on scope change."""

    def test_scope_change_updates_data(self, qtbot):
        """Test that changing scope updates the module data."""
        counter = CounterModule()
        qtbot.addWidget(counter)

        # Get initial data
        initial_data = counter.get_data()
        assert initial_data["scope"] == CounterScope.PER_FOLDER.value

        # Change scope to GLOBAL
        counter.scope_combo.setCurrentIndex(0)

        # Verify data changed
        new_data = counter.get_data()
        assert new_data["scope"] == CounterScope.GLOBAL.value
        assert new_data["scope"] != initial_data["scope"]
