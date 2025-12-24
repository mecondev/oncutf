"""Unit tests for StyledComboBox widget.

Tests theme integration and delegate setup.
"""

import pytest
from PyQt5.QtWidgets import QWidget

from oncutf.ui.widgets.styled_combo_box import StyledComboBox
from oncutf.ui.widgets.ui_delegates import ComboBoxItemDelegate


@pytest.fixture
def parent_widget(qtbot):
    """Create a parent widget for testing."""
    widget = QWidget()
    qtbot.addWidget(widget)
    return widget


class TestStyledComboBoxInit:
    """Test StyledComboBox initialization."""

    def test_init_without_parent(self, qtbot):
        """Test initialization without parent."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        assert combo is not None
        assert isinstance(combo, StyledComboBox)

    def test_init_with_parent(self, qtbot, parent_widget):
        """Test initialization with parent."""
        combo = StyledComboBox(parent=parent_widget)
        qtbot.addWidget(combo)

        assert combo is not None
        assert combo.parent() == parent_widget


class TestStyledComboBoxDelegate:
    """Test delegate setup."""

    def test_delegate_is_set(self, qtbot):
        """Test that ComboBoxItemDelegate is set."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        delegate = combo.itemDelegate()
        assert delegate is not None
        # Delegate should be ComboBoxItemDelegate
        assert isinstance(delegate, ComboBoxItemDelegate)

    def test_delegate_survives_add_items(self, qtbot):
        """Test delegate remains after adding items."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        # Add items
        combo.addItem("Item 1")
        combo.addItem("Item 2")
        combo.addItem("Item 3")

        # Delegate should still be set
        delegate = combo.itemDelegate()
        assert isinstance(delegate, ComboBoxItemDelegate)


class TestStyledComboBoxTheme:
    """Test theme application."""

    def test_height_is_set(self, qtbot):
        """Test that height is set from theme."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        height = combo.height()
        # Height should be set (either from theme or fallback)
        assert height > 0
        # Typical combo height should be between 24 and 48 pixels
        assert 24 <= height <= 48

    def test_fixed_height(self, qtbot):
        """Test that height is fixed (not resizable)."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        original_height = combo.height()

        # Try to resize
        combo.resize(200, 100)

        # Height should remain fixed
        assert combo.height() == original_height


class TestStyledComboBoxFunctionality:
    """Test basic QComboBox functionality is preserved."""

    def test_add_items(self, qtbot):
        """Test adding items works."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        combo.addItem("Item 1")
        combo.addItem("Item 2")

        assert combo.count() == 2
        assert combo.itemText(0) == "Item 1"
        assert combo.itemText(1) == "Item 2"

    def test_current_text(self, qtbot):
        """Test getting current text."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        combo.addItem("First")
        combo.addItem("Second")
        combo.setCurrentIndex(1)

        assert combo.currentText() == "Second"

    def test_current_index(self, qtbot):
        """Test getting/setting current index."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        combo.addItem("A")
        combo.addItem("B")
        combo.addItem("C")

        combo.setCurrentIndex(2)
        assert combo.currentIndex() == 2

    def test_clear(self, qtbot):
        """Test clearing items."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        combo.addItem("Item 1")
        combo.addItem("Item 2")
        assert combo.count() == 2

        combo.clear()
        assert combo.count() == 0

    def test_add_items_with_data(self, qtbot):
        """Test adding items with user data."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        combo.addItem("Display", "data_value")
        assert combo.count() == 1
        assert combo.itemText(0) == "Display"
        assert combo.itemData(0) == "data_value"


class TestStyledComboBoxSignals:
    """Test signal emission."""

    def test_current_index_changed_signal(self, qtbot):
        """Test currentIndexChanged signal."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        combo.addItem("A")
        combo.addItem("B")

        # Connect signal
        with qtbot.waitSignal(combo.currentIndexChanged, timeout=1000):
            combo.setCurrentIndex(1)

    def test_activated_signal(self, qtbot):
        """Test activated signal."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        combo.addItem("A")
        combo.addItem("B")

        # Simulate user activation
        with qtbot.waitSignal(combo.activated, timeout=1000):
            combo.activated.emit(1)


class TestStyledComboBoxEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_combo(self, qtbot):
        """Test empty combo box."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        assert combo.count() == 0
        assert combo.currentIndex() == -1
        assert combo.currentText() == ""

    def test_many_items(self, qtbot):
        """Test combo with many items."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        # Add 100 items
        for i in range(100):
            combo.addItem(f"Item {i}")

        assert combo.count() == 100
        # Delegate should still work
        assert isinstance(combo.itemDelegate(), ComboBoxItemDelegate)

    def test_unicode_items(self, qtbot):
        """Test combo with Unicode items."""
        combo = StyledComboBox()
        qtbot.addWidget(combo)

        combo.addItem("Ελληνικά")
        combo.addItem("中文")
        combo.addItem("العربية")

        assert combo.count() == 3
        assert combo.itemText(0) == "Ελληνικά"
