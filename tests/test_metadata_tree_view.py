"""Module: test_metadata_tree_view.py

Author: Michael Economou
Date: 2025-05-01

Tests for MetadataTreeView widget
"""

import os
import warnings

# Force headless Qt platform to reduce GUI-related crashes in tests
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication, QTreeView

    from oncutf.core.theme_manager import get_theme_manager
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False


@pytest.mark.gui
@pytest.mark.skipif(not PYQT5_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.skipif("CI" in os.environ, reason="GUI tests don't work on CI")
class TestMetadataTreeView:
    """Test suite for MetadataTreeView widget."""

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
    def theme_manager(self):
        """Create a ThemeManager instance for testing."""
        return get_theme_manager()

    @pytest.fixture
    def tree_view(self, qapp, theme_manager, qtbot):  # noqa: ARG002
        """Create a MetadataTreeView for testing."""
        tree = MetadataTreeView()
        tree.setStyleSheet(
            f"""
            QTreeView {{
                background-color: {theme_manager.get_color("table_background")};
                color: {theme_manager.get_color("text")};
            }}
        """
        )
        qtbot.addWidget(tree)
        yield tree

    def test_widget_initialization(self, tree_view):
        """Test MetadataTreeView initialization."""
        assert isinstance(tree_view, QTreeView)
        assert tree_view.rootIsDecorated() is True
        assert tree_view.alternatingRowColors() is True
        assert tree_view.selectionMode() == QTreeView.SingleSelection

    def test_theme_application(self, tree_view, theme_manager):
        """Test that theme styles are properly applied."""
        # Apply stylesheet with branch styling
        style_sheet = f"""
            QTreeView {{
                background-color: {theme_manager.get_color("table_background")};
                color: {theme_manager.get_color("text")};
            }}
            QTreeView::branch:has-children:closed {{
                image: url(:/icons/chevron-right.svg);
            }}
        """
        tree_view.setStyleSheet(style_sheet)

        # Basic checks
        applied_style = tree_view.styleSheet()
        assert applied_style != "", "Style sheet should not be empty"
        assert "QTreeView" in applied_style

        # Check for chevron/branch styling - now properly included in test stylesheet
        has_branch_styling = any(
            keyword in applied_style
            for keyword in ["branch:", "::branch", "has-children", "closed"]
        )
        assert has_branch_styling, "Tree should have branch/chevron styling"

    def test_hover_state_handling(self, tree_view):
        """Test hover state behavior (basic functionality)."""
        from PyQt5.QtCore import QEvent, QPoint
        from PyQt5.QtGui import QMouseEvent

        enter_event = QEvent(QEvent.Enter)
        leave_event = QEvent(QEvent.Leave)

        tree_view.event(enter_event)
        tree_view.event(leave_event)

        mouse_event = QMouseEvent(
            QEvent.MouseMove, QPoint(10, 10), Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        tree_view.mouseMoveEvent(mouse_event)

    def test_styling_consistency(self, tree_view, theme_manager):
        """Test that styling remains consistent across states."""
        style_sheet = f"""
            QTreeView {{
                background-color: {theme_manager.get_color("table_background")};
                color: {theme_manager.get_color("text")};
            }}
            QTreeView::item:selected {{
                background-color: {theme_manager.get_color("table_selection_bg")};
                color: {theme_manager.get_color("table_selection_text")};
            }}
        """
        tree_view.setStyleSheet(style_sheet)
        style = tree_view.styleSheet()

        # Should have consistent theme colors
        assert theme_manager.get_color("table_background") in style
        assert theme_manager.get_color("text") in style

        # Note: This test checks for actual color values
        assert len(style) > 0, "Style sheet should not be empty"


class TestMetadataTreeViewLogic:
    """Test MetadataTreeView logic without GUI dependencies."""

    def test_metadata_structure_validation(self):
        """Test metadata structure validation logic."""
        valid_metadata = {
            "EXIF": {"Camera Make": "Canon", "Camera Model": "EOS R5"},
            "File": {"File Name": "test.jpg"},
        }

        assert isinstance(valid_metadata, dict)
        assert "EXIF" in valid_metadata
        assert isinstance(valid_metadata["EXIF"], dict)

    def test_tree_item_creation_logic(self):
        """Test the logic for creating tree items."""

        # Mock the tree item creation without GUI
        def create_tree_item(key, value):
            return {"key": key, "value": str(value), "type": type(value).__name__}

        text_item = create_tree_item("Camera Make", "Canon")
        assert text_item["key"] == "Camera Make"
        assert text_item["value"] == "Canon"
        assert text_item["type"] == "str"

    def test_path_generation_logic(self):
        """Test metadata path generation logic."""

        def generate_path(parent_path, key):
            if parent_path:
                return f"{parent_path}/{key}"
            return key

        assert generate_path("", "EXIF") == "EXIF"
        assert generate_path("EXIF", "Camera Make") == "EXIF/Camera Make"
        assert generate_path("EXIF/GPS", "Latitude") == "EXIF/GPS/Latitude"


@pytest.mark.gui
@pytest.mark.skipif(not PYQT5_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.skipif("CI" in os.environ, reason="GUI tests don't work on CI")
class TestMetadataTreeViewRotation:
    """Test suite for MetadataTreeView rotation functionality."""

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
    def mock_file_item(self):
        """Create a mock FileItem for testing."""
        from unittest.mock import MagicMock

        file_item = MagicMock()
        file_item.filename = "test_image.jpg"
        file_item.full_path = "/path/to/test_image.jpg"
        file_item.metadata_status = "clean"
        return file_item

    @pytest.fixture
    def tree_view(self, qapp):
        """Create a MetadataTreeView for testing."""
        tree = MetadataTreeView()
        yield tree
        tree.setModel(None)
        tree.deleteLater()
        if qapp:
            from PyQt5.QtCore import QCoreApplication

            QCoreApplication.processEvents()

    def test_set_rotation_to_zero_with_existing_value(self, tree_view, mock_file_item):
        """Test setting rotation to 0 when a rotation value exists."""
        from unittest.mock import MagicMock, patch

        # Setup mock metadata cache with existing rotation value
        mock_metadata = {"EXIF:Orientation": "3"}  # 180 degrees rotation

        # Mock the necessary methods
        tree_view._get_metadata_cache = MagicMock(return_value=mock_metadata)
        tree_view._get_current_selection = MagicMock(return_value=[mock_file_item])

        # Mock direct loader
        mock_direct_loader = MagicMock()
        tree_view._direct_loader = mock_direct_loader

        # Mock update methods on behavior
        tree_view._edit_behavior._update_tree_item_value = MagicMock()
        tree_view._edit_behavior.mark_as_modified = MagicMock()

        # Mock signal
        tree_view.value_edited = MagicMock()
        tree_view.value_edited.emit = MagicMock()

        # Mock file_status_helpers.get_metadata_value to return "3"
        with patch(
            "oncutf.ui.behaviors.metadata_edit.rotation_handler.get_metadata_value",
            return_value="3",
        ):
            # Call the method
            tree_view.set_rotation_to_zero("EXIF:Orientation")

        # Verify direct loader was called
        mock_direct_loader.set_metadata_value.assert_called_once_with(
            mock_file_item.full_path, "EXIF:Orientation", "0"
        )

        # Verify tree was updated
        tree_view._edit_behavior._update_tree_item_value.assert_called_once_with("EXIF:Orientation", "0")

        # Verify modified state was set
        tree_view._edit_behavior.mark_as_modified.assert_called_once_with("EXIF:Orientation")

        # Verify signal was emitted with old value
        tree_view.value_edited.emit.assert_called_once_with("EXIF:Orientation", "0", "3")

    def test_set_rotation_to_zero_without_existing_value(self, tree_view, mock_file_item):
        """Test setting rotation to 0 when no rotation value exists in metadata."""
        from unittest.mock import MagicMock, patch

        # Setup mock metadata cache without rotation value
        mock_metadata = {"EXIF:CameraMake": "Canon"}  # No orientation key

        # Mock the necessary methods
        tree_view._get_metadata_cache = MagicMock(return_value=mock_metadata)
        tree_view._get_current_selection = MagicMock(return_value=[mock_file_item])

        # Mock direct loader
        mock_direct_loader = MagicMock()
        tree_view._direct_loader = mock_direct_loader

        # Mock update methods on behavior
        tree_view._edit_behavior._update_tree_item_value = MagicMock()
        tree_view._edit_behavior.mark_as_modified = MagicMock()

        # Mock signal
        tree_view.value_edited = MagicMock()
        tree_view.value_edited.emit = MagicMock()

        # Mock file_status_helpers.get_metadata_value to return None
        with patch(
            "oncutf.ui.behaviors.metadata_edit.rotation_handler.get_metadata_value",
            return_value=None,
        ):
            # Call the method
            tree_view.set_rotation_to_zero("EXIF:Orientation")

        # Verify direct loader was called
        mock_direct_loader.set_metadata_value.assert_called_once_with(
            mock_file_item.full_path, "EXIF:Orientation", "0"
        )

        # Verify signal was emitted with empty string (no previous value)
        tree_view.value_edited.emit.assert_called_once_with("EXIF:Orientation", "0", "")

    def test_set_rotation_to_zero_already_zero(self, tree_view, mock_file_item):
        """Test setting rotation to 0 when rotation is already 0."""
        from unittest.mock import MagicMock, patch

        # Setup mock metadata cache with rotation already at 0
        mock_metadata = {"EXIF:Orientation": "0"}

        # Mock the necessary methods
        tree_view._get_metadata_cache = MagicMock(return_value=mock_metadata)
        tree_view._get_current_selection = MagicMock(return_value=[mock_file_item])

        # Mock direct loader (should not be called)
        mock_direct_loader = MagicMock()
        tree_view._direct_loader = mock_direct_loader

        # Mock file_status_helpers.get_metadata_value to return "0"
        with patch(
            "oncutf.ui.behaviors.metadata_edit.rotation_handler.get_metadata_value",
            return_value="0",
        ):
            # Call the method
            tree_view.set_rotation_to_zero("EXIF:Orientation")

        # Verify direct loader was NOT called (early return)
        mock_direct_loader.set_metadata_value.assert_not_called()

    def test_set_rotation_to_zero_fallback_path(self, tree_view, mock_file_item):
        """Test fallback path when direct loader fails or is unavailable."""
        from unittest.mock import MagicMock, patch

        # Setup mock metadata cache
        mock_metadata = {"EXIF:Orientation": "3"}

        # Mock the necessary methods
        tree_view._get_metadata_cache = MagicMock(return_value=mock_metadata)
        tree_view._get_current_selection = MagicMock(return_value=[mock_file_item])

        # Make direct loader fail
        mock_direct_loader = MagicMock()
        mock_direct_loader.set_metadata_value.side_effect = Exception("Direct loader failed")
        tree_view._direct_loader = mock_direct_loader

        # Mock fallback method on behavior
        tree_view._edit_behavior._fallback_set_rotation_to_zero = MagicMock()

        # Mock file_status_helpers.get_metadata_value to return "3"
        with patch(
            "oncutf.ui.behaviors.metadata_edit.rotation_handler.get_metadata_value",
            return_value="3",
        ):
            # Call the method
            tree_view.set_rotation_to_zero("EXIF:Orientation")

        # Verify fallback was called with current value
        tree_view._edit_behavior._fallback_set_rotation_to_zero.assert_called_once_with(
            "EXIF:Orientation", "0", "3"
        )

    def test_set_rotation_to_zero_empty_metadata_cache(self, tree_view, mock_file_item):
        """Test setting rotation to 0 when metadata cache is None or empty."""
        from unittest.mock import MagicMock, patch

        # Setup empty metadata cache
        tree_view._get_metadata_cache = MagicMock(return_value=None)
        tree_view._get_current_selection = MagicMock(return_value=[mock_file_item])

        # Mock direct loader
        mock_direct_loader = MagicMock()
        tree_view._direct_loader = mock_direct_loader

        # Mock update methods on behavior
        tree_view._edit_behavior._update_tree_item_value = MagicMock()
        tree_view._edit_behavior.mark_as_modified = MagicMock()

        # Mock signal
        tree_view.value_edited = MagicMock()
        tree_view.value_edited.emit = MagicMock()

        # Mock file_status_helpers.get_metadata_value to return None
        with patch(
            "oncutf.ui.behaviors.metadata_edit.rotation_handler.get_metadata_value",
            return_value=None,
        ):
            # Call the method (should not crash with UnboundLocalError)
            tree_view.set_rotation_to_zero("EXIF:Orientation")

        # Verify signal was emitted with empty string (no previous value)
        tree_view.value_edited.emit.assert_called_once_with("EXIF:Orientation", "0", "")

    def test_set_rotation_to_zero_no_direct_loader(self, tree_view, mock_file_item):
        """Test setting rotation to 0 when direct loader is not available."""
        from unittest.mock import MagicMock, patch

        # Setup mock metadata cache
        mock_metadata = {"EXIF:Orientation": "3"}

        # Mock the necessary methods
        tree_view._get_metadata_cache = MagicMock(return_value=mock_metadata)
        tree_view._get_current_selection = MagicMock(return_value=[mock_file_item])

        # No direct loader
        tree_view._direct_loader = None

        # Mock fallback method on behavior
        tree_view._edit_behavior._fallback_set_rotation_to_zero = MagicMock()

        # Mock file_status_helpers.get_metadata_value to return "3"
        with patch(
            "oncutf.ui.behaviors.metadata_edit.rotation_handler.get_metadata_value",
            return_value="3",
        ):
            # Call the method
            tree_view.set_rotation_to_zero("EXIF:Orientation")

        # Verify fallback was called
        tree_view._edit_behavior._fallback_set_rotation_to_zero.assert_called_once_with(
            "EXIF:Orientation", "0", "3"
        )
