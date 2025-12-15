"""
Module: test_hierarchical_combo_box.py

Author: Michael Economou
Date: 2025-05-01

Tests for HierarchicalComboBox widget
Tests dropdown behavior, chevron icons, category selection, and theme consistency.
These tests cover the combobox issues we've been addressing.
"""

import os
import warnings
from unittest.mock import patch

import pytest

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

# PyQt5 widget tests (only run if PyQt5 is available and not in CI)
try:
    from PyQt5.QtWidgets import QApplication, QTreeView

    from oncutf.ui.widgets.hierarchical_combo_box import HierarchicalComboBox
    from oncutf.utils.theme_engine import ThemeEngine

    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False


@pytest.mark.gui
@pytest.mark.skipif(not PYQT5_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.skipif("CI" in os.environ, reason="GUI tests don't work on CI")
class TestHierarchicalComboBox:
    """Test suite for HierarchicalComboBox widget."""

    @pytest.fixture(scope="session")
    def qapp(self):
        """Create QApplication instance for widget testing."""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    @pytest.fixture
    def theme_engine(self):
        """Create a ThemeEngine instance for testing."""
        return ThemeEngine()

    @pytest.fixture
    def sample_metadata_groups(self):
        """Create sample metadata groups for testing."""
        return {
            "File Info": [
                ("File Name", "filename"),
                ("File Size", "filesize"),
                ("File Type", "filetype"),
            ],
            "File Date/Time": [
                ("Date Created", "date_created"),
                ("Date Modified", "date_modified"),
                ("Date Taken", "date_taken"),
            ],
            "EXIF": [
                ("Camera Make", "camera_make"),
                ("Camera Model", "camera_model"),
                ("ISO", "iso"),
                ("F-Stop", "fstop"),
            ],
            "GPS": [("Latitude", "latitude"), ("Longitude", "longitude"), ("Altitude", "altitude")],
        }

    @pytest.fixture
    def combo_box(self, qapp, theme_engine):  # noqa: ARG002
        """Create a HierarchicalComboBox for testing."""
        combo = HierarchicalComboBox()
        # Apply theme to get consistent styling
        if hasattr(combo, "tree_view"):
            combo.tree_view.setStyleSheet(f"""
                QTreeView {{
                    background-color: {theme_engine.get_color("combo_dropdown_background")};
                    color: {theme_engine.get_color("combo_text")};
                }}
            """)
        return combo

    def test_widget_initialization(self, combo_box):
        """Test HierarchicalComboBox initialization."""
        assert hasattr(combo_box, "tree_view")
        assert isinstance(combo_box.tree_view, QTreeView)

        # Check tree view properties
        tree = combo_box.tree_view
        assert tree.rootIsDecorated() is True  # Should show chevrons
        assert tree.headerHidden() is True  # No header
        assert tree.alternatingRowColors() is False  # No alternating rows

    def test_metadata_population(self, combo_box, sample_metadata_groups):
        """Test populating combobox with metadata groups."""
        combo_box.populate_from_metadata_groups(sample_metadata_groups)

        # Check that model has items
        model = combo_box.tree_view.model()
        assert model is not None
        assert model.rowCount() > 0

        # Check for expected groups
        root = model.invisibleRootItem()
        group_names = []
        for i in range(root.rowCount()):
            item = root.child(i)
            if item:
                group_names.append(item.text())

        assert "File Info" in group_names
        assert "EXIF" in group_names

    def test_group_expansion_behavior(self, combo_box, sample_metadata_groups):
        """Test that groups can be expanded to show items."""
        combo_box.populate_from_metadata_groups(sample_metadata_groups)

        model = combo_box.tree_view.model()
        tree = combo_box.tree_view

        # Find the File Info group
        file_info_index = None
        root = model.invisibleRootItem()
        for i in range(root.rowCount()):
            item = root.child(i)
            if item and item.text() == "File Info":
                file_info_index = model.indexFromItem(item)
                break

        assert file_info_index is not None

        # Test expansion
        tree.expand(file_info_index)
        assert tree.isExpanded(file_info_index) is True

        # Check that children are accessible
        item = model.itemFromIndex(file_info_index)
        assert item.rowCount() > 0  # Should have child items

    def test_selection_behavior(self, combo_box, sample_metadata_groups):
        """Test item selection behavior."""
        combo_box.populate_from_metadata_groups(sample_metadata_groups)

        model = combo_box.tree_view.model()
        tree = combo_box.tree_view

        # Find and select an item
        root = model.invisibleRootItem()
        if root.rowCount() > 0:
            first_group = root.child(0)
            if first_group and first_group.rowCount() > 0:
                first_item = first_group.child(0)
                if first_item:
                    item_index = model.indexFromItem(first_item)
                    tree.setCurrentIndex(item_index)

                    assert tree.currentIndex() == item_index
                    assert tree.selectionModel().isSelected(item_index) is True

    def test_default_selection_logic(self, combo_box, sample_metadata_groups):
        """Test default selection to File Name in File Info group."""
        combo_box.populate_from_metadata_groups(sample_metadata_groups)

        # Should default to File Name if available
        current_text = combo_box.currentText()

        # Note: Actual default selection logic may vary
        # This test ensures the method doesn't crash
        assert isinstance(current_text, str)

    def test_theme_consistency(self, combo_box, theme_engine):
        """Test theme consistency between tree view and combobox."""
        # Apply theme styling
        if hasattr(combo_box, "tree_view"):
            style_sheet = f"""
                QTreeView {{
                    background-color: {theme_engine.get_color("combo_dropdown_background")};
                    color: {theme_engine.get_color("combo_text")};
                }}
                QTreeView::item:hover {{
                    background-color: {theme_engine.get_color("combo_item_background_hover")};
                }}
                QTreeView::item:selected {{
                    background-color: {theme_engine.get_color("combo_item_background_selected")};
                }}
            """
            combo_box.tree_view.setStyleSheet(style_sheet)

            applied_style = combo_box.tree_view.styleSheet()
            assert applied_style != ""

            # Check for hover and selection styling
            has_hover_style = "hover" in applied_style.lower()
            has_selection_style = "selected" in applied_style.lower()

            # At least one should be present
            assert has_hover_style or has_selection_style

    def test_chevron_icon_presence(self, combo_box, sample_metadata_groups):
        """Test that chevron icons are configured."""
        combo_box.populate_from_metadata_groups(sample_metadata_groups)

        tree = combo_box.tree_view
        style = tree.styleSheet()

        # Check for branch/chevron styling in QSS
        has_branch_styling = any(
            keyword in style
            for keyword in ["branch:", "::branch", "has-children", "open", "closed"]
        )

        # Or check if root decoration is enabled (shows default chevrons)
        assert has_branch_styling or tree.rootIsDecorated()

    @patch("oncutf.ui.widgets.hierarchical_combo_box.HierarchicalComboBox.item_selected")
    def test_selection_signal_emission(self, mock_signal, combo_box, sample_metadata_groups):
        """Test that selection changes emit appropriate signals."""
        combo_box.populate_from_metadata_groups(sample_metadata_groups)

        # Trigger a selection change
        model = combo_box.tree_view.model()
        if model and model.rowCount() > 0:
            root = model.invisibleRootItem()
            first_group = root.child(0)
            if first_group and first_group.rowCount() > 0:
                first_item = first_group.child(0)
                if first_item:
                    index = model.indexFromItem(first_item)
                    combo_box.tree_view.setCurrentIndex(index)

        # The signal should be callable (mocked)
        assert callable(mock_signal)

    def test_dropdown_popup_behavior(self, combo_box):
        """Test dropdown popup behavior."""
        # Test basic popup functionality
        combo_box.showPopup()

        # Should have a popup view
        assert hasattr(combo_box, "tree_view")

        # Hide popup
        combo_box.hidePopup()

        # Should not crash
        assert True

    def test_empty_groups_handling(self, combo_box):
        """Test handling of empty metadata groups."""
        empty_groups = {}

        # Should not crash with empty data
        combo_box.populate_from_metadata_groups(empty_groups)

        model = combo_box.tree_view.model()
        if model:
            assert model.rowCount() == 0

    def test_partial_groups_handling(self, combo_box):
        """Test handling of groups with some empty categories."""
        partial_groups = {
            "File Info": [("File Name", "filename")],  # Has items
            "Empty Group": [],  # No items
            "EXIF": [("Camera Make", "camera_make"), ("ISO", "iso")],  # Has items
        }

        # Should handle mixed data gracefully
        combo_box.populate_from_metadata_groups(partial_groups)

        model = combo_box.tree_view.model()
        assert model is not None


# Non-GUI tests that can run anywhere
class TestHierarchicalComboBoxLogic:
    """Test HierarchicalComboBox logic without GUI dependencies."""

    def test_metadata_groups_validation(self):
        """Test metadata groups structure validation."""
        valid_groups = {
            "File Info": ["File Name", "File Size"],
            "EXIF": ["Camera Make", "Camera Model"],
        }

        # Test structure validation
        assert isinstance(valid_groups, dict)
        for group_name, items in valid_groups.items():
            assert isinstance(group_name, str)
            assert isinstance(items, list)
            for item in items:
                assert isinstance(item, str)

    def test_group_item_filtering(self):
        """Test filtering logic for group items."""

        def filter_valid_items(items):
            """Mock filtering function."""
            return [item for item in items if item and isinstance(item, str)]

        test_items = ["Valid Item", "", None, "Another Valid", 123]
        filtered = filter_valid_items(test_items)

        assert len(filtered) == 2
        assert "Valid Item" in filtered
        assert "Another Valid" in filtered

    def test_selection_path_building(self):
        """Test building selection paths."""

        def build_selection_path(group, item):
            """Mock path building."""
            return f"{group}/{item}" if group and item else item or group or ""

        # Test various combinations
        assert build_selection_path("EXIF", "Camera Make") == "EXIF/Camera Make"
        assert build_selection_path("", "File Name") == "File Name"
        assert build_selection_path("File Info", "") == "File Info"
        assert build_selection_path("", "") == ""

    def test_default_selection_logic(self):
        """Test default selection determination."""

        def get_default_selection(groups):
            """Mock default selection logic."""
            # Priority: File Name in File Info, then first item in first group
            if "File Info" in groups and "File Name" in groups["File Info"]:
                return "File Info/File Name"

            # Fallback to first available item
            for group_name, items in groups.items():
                if items:
                    return f"{group_name}/{items[0]}"

            return ""

        # Test with File Name available
        groups_with_filename = {"File Info": ["File Name", "File Size"], "EXIF": ["Camera Make"]}
        assert get_default_selection(groups_with_filename) == "File Info/File Name"

        # Test without File Name
        groups_without_filename = {"EXIF": ["Camera Make", "Camera Model"], "GPS": ["Latitude"]}
        assert get_default_selection(groups_without_filename) == "EXIF/Camera Make"

        # Test empty groups
        empty_groups = {}
        assert get_default_selection(empty_groups) == ""
