"""
Test suite for metadata tree visual feedback system.

Verifies that modified metadata fields are displayed with yellow color and bold font.
"""

import pytest

from oncutf.config import METADATA_ICON_COLORS
from oncutf.core.pyqt_imports import QApplication
from oncutf.utils.build_metadata_tree_model import build_metadata_tree_model


@pytest.fixture
def app():
    """Create QApplication for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_modified_keys_styling(app):
    """Test that modified keys have yellow color and bold font."""
    # Use fixture for QApplication; not referenced further
    del app

    metadata = {
        'FileName': 'test.jpg',
        'ISO': 100,
        'ISOSpeed': 1600,
        'FocalLength': 50.0,
        'Aperture': 2.8,
    }

    modified_keys = {'ISOSpeed', 'Aperture'}
    model = build_metadata_tree_model(metadata, modified_keys)

    # Find Camera Settings group
    root = model.invisibleRootItem()
    camera_settings_group = None

    for group_idx in range(root.rowCount()):
        group = root.child(group_idx, 0)
        if 'Camera Settings' in group.text():
            camera_settings_group = group
            break

    assert camera_settings_group is not None, "Camera Settings group not found"

    # Check modified keys
    found_modified = {}
    for i in range(camera_settings_group.rowCount()):
        key_item = camera_settings_group.child(i, 0)
        key_text = key_item.text()

        # Check for modified indicators
        if key_text.replace(' ', '') == 'ISOSpeed':  # Handle formatted text "I S O Speed"
            found_modified['ISOSpeed'] = key_item
        elif 'Aperture' in key_text:
            found_modified['Aperture'] = key_item

    # Verify styling for ISOSpeed
    assert 'ISOSpeed' in found_modified, f"ISOSpeed key not found. Found in group: {[camera_settings_group.child(i, 0).text() for i in range(camera_settings_group.rowCount())]}"
    iso_item = found_modified['ISOSpeed']
    iso_color = iso_item.foreground().color()
    expected_hex = METADATA_ICON_COLORS["modified"]
    expected_color = iso_color.fromRgbF(1, 1, 1)  # placeholder to access QColor class
    # Use QColor.fromRgb to parse the hex string to avoid hardcoding RGB values
    expected_color = expected_color.fromRgb(int(expected_hex[1:3], 16), int(expected_hex[3:5], 16), int(expected_hex[5:7], 16))
    assert iso_color.red() == expected_color.red(), f"Expected red={expected_color.red()}, got {iso_color.red()}"
    assert iso_color.green() == expected_color.green(), f"Expected green={expected_color.green()}, got {iso_color.green()}"
    assert iso_color.blue() == expected_color.blue(), f"Expected blue={expected_color.blue()}, got {iso_color.blue()}"
    assert iso_item.font().bold(), "ISOSpeed font should be bold"

    # Verify styling for Aperture
    assert 'Aperture' in found_modified, f"Aperture key not found. Found in group: {[camera_settings_group.child(i, 0).text() for i in range(camera_settings_group.rowCount())]}"
    aperture_item = found_modified['Aperture']
    aperture_color = aperture_item.foreground().color()
    assert aperture_color.red() == expected_color.red(), f"Expected red={expected_color.red()}, got {aperture_color.red()}"
    assert aperture_color.green() == expected_color.green(), f"Expected green={expected_color.green()}, got {aperture_color.green()}"
    assert aperture_color.blue() == expected_color.blue(), f"Expected blue={expected_color.blue()}, got {aperture_color.blue()}"
    assert aperture_item.font().bold(), "Aperture font should be bold"


def test_unmodified_keys_normal_styling(app):
    """Test that unmodified keys have normal styling."""
    # Use fixture for QApplication; not referenced further
    del app

    metadata = {
        'FileName': 'test.jpg',
        'ISOSpeed': 1600,
        'FocalLength': 50.0,
    }

    modified_keys = {'ISOSpeed'}  # Only ISO is modified
    model = build_metadata_tree_model(metadata, modified_keys)

    # Find Camera Settings group
    root = model.invisibleRootItem()
    camera_settings_group = None

    for group_idx in range(root.rowCount()):
        group = root.child(group_idx, 0)
        if 'Camera Settings' in group.text():
            camera_settings_group = group
            break

    assert camera_settings_group is not None

    # Check FocalLength (unmodified)
    for i in range(camera_settings_group.rowCount()):
        key_item = camera_settings_group.child(i, 0)
        if 'Focal Length' in key_item.text():
            focal_color = key_item.foreground().color()
            # Unmodified should have default color (usually black/0,0,0)
            assert focal_color.red() == 0, f"Expected red=0 for unmodified, got {focal_color.red()}"
            assert focal_color.green() == 0, f"Expected green=0 for unmodified, got {focal_color.green()}"
            assert focal_color.blue() == 0, f"Expected blue=0 for unmodified, got {focal_color.blue()}"
            assert not key_item.font().bold(), "Unmodified font should not be bold"
            break


def test_empty_modified_keys(app):
    """Test that passing empty modified_keys doesn't break anything."""
    metadata = {
        'FileName': 'test.jpg',
        'ISOSpeed': 1600,
    }

    # Use fixture for QApplication; not referenced further
    del app

    # No modified keys
    model = build_metadata_tree_model(metadata, set())

    root = model.invisibleRootItem()
    assert root.rowCount() > 0, "Model should have at least one group"


def test_modified_tooltip(app):
    """Test that modified keys have appropriate tooltips."""
    metadata = {
        'FileName': 'test.jpg',
        'ISOSpeed': 1600,
    }

    # Use fixture for QApplication; not referenced further
    del app

    modified_keys = {'ISOSpeed'}
    model = build_metadata_tree_model(metadata, modified_keys)

    # Find Camera Settings group
    root = model.invisibleRootItem()
    for group_idx in range(root.rowCount()):
        group = root.child(group_idx, 0)
        if 'Camera Settings' in group.text():
            for i in range(group.rowCount()):
                key_item = group.child(i, 0)
                if 'ISO Speed' in key_item.text():
                    tooltip = key_item.toolTip()
                    assert 'Modified' in tooltip, f"Expected 'Modified' in tooltip, got: {tooltip}"
                    break
            break


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
