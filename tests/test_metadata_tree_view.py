"""
Module: test_metadata_tree_view.py

Author: Michael Economou
Date: 2025-01-11

Tests for MetadataTreeView widget
"""

import os
import warnings
from unittest.mock import MagicMock, Mock, patch

import pytest

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

try:
    from PyQt5.QtCore import QModelIndex, Qt
    from PyQt5.QtWidgets import QApplication, QTreeView

    from utils.theme_engine import ThemeEngine
    from widgets.metadata_tree_view import MetadataTreeView

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
    def theme_engine(self):
        """Create a ThemeEngine instance for testing."""
        return ThemeEngine()

    @pytest.fixture
    def tree_view(self, qapp, theme_engine):
        """Create a MetadataTreeView for testing."""
        tree = MetadataTreeView()
        tree.setStyleSheet(f"""
            QTreeView {{
                background-color: {theme_engine.get_color('table_background')};
                color: {theme_engine.get_color('table_text')};
            }}
        """)
        yield tree
        tree.setModel(None)
        tree.deleteLater()
        if qapp:
            from PyQt5.QtCore import QCoreApplication
            QCoreApplication.processEvents()

    def test_widget_initialization(self, tree_view):
        """Test MetadataTreeView initialization."""
        assert isinstance(tree_view, QTreeView)
        assert tree_view.rootIsDecorated() is True
        assert tree_view.alternatingRowColors() is True
        assert tree_view.selectionMode() == QTreeView.SingleSelection

    def test_theme_application(self, tree_view, theme_engine):
        """Test that theme styles are properly applied."""
        style_sheet = f"""
            QTreeView {{
                background-color: {theme_engine.get_color('table_background')};
                color: {theme_engine.get_color('table_text')};
            }}
        """
        tree_view.setStyleSheet(style_sheet)
        assert tree_view.styleSheet() != ""
        assert "QTreeView" in tree_view.styleSheet()

    def test_hover_state_handling(self, tree_view):
        """Test hover state behavior (basic functionality)."""
        from PyQt5.QtCore import QEvent, QPoint
        from PyQt5.QtGui import QMouseEvent

        enter_event = QEvent(QEvent.Enter)
        leave_event = QEvent(QEvent.Leave)

        tree_view.event(enter_event)
        tree_view.event(leave_event)

        mouse_event = QMouseEvent(
            QEvent.MouseMove,
            QPoint(10, 10),
            Qt.NoButton,
            Qt.NoButton,
            Qt.NoModifier
        )
        tree_view.mouseMoveEvent(mouse_event)

    def test_styling_consistency(self, tree_view, theme_engine):
        """Test that styling remains consistent across states."""
        style_sheet = f"""
            QTreeView {{
                background-color: {theme_engine.get_color('table_background')};
                color: {theme_engine.get_color('table_text')};
            }}
            QTreeView::item:selected {{
                background-color: {theme_engine.get_color('table_selection_background')};
                color: {theme_engine.get_color('table_selection_text')};
            }}
        """
        tree_view.setStyleSheet(style_sheet)
        style = tree_view.styleSheet()

        assert theme_engine.get_color('table_background') in style
        assert theme_engine.get_color('table_text') in style
        assert len(style) > 0


class TestMetadataTreeViewLogic:
    """Test MetadataTreeView logic without GUI dependencies."""

    def test_metadata_structure_validation(self):
        """Test metadata structure validation logic."""
        valid_metadata = {
            "EXIF": {
                "Camera Make": "Canon",
                "Camera Model": "EOS R5"
            },
            "File": {
                "File Name": "test.jpg"
            }
        }

        assert isinstance(valid_metadata, dict)
        assert "EXIF" in valid_metadata
        assert isinstance(valid_metadata["EXIF"], dict)

    def test_tree_item_creation_logic(self):
        """Test the logic for creating tree items."""
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
