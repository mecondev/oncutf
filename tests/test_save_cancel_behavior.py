"""Tests for save operation cancel behavior.

Tests ESC key blocking logic for different save scenarios:
- Normal save: ESC blocked by default (config controlled)
- Exit save: ESC always blocked (critical data safety)
- Other operations: ESC allowed (metadata loading, hash calc)
"""

from unittest.mock import Mock, patch

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from oncutf.utils.ui.progress_dialog import ProgressDialog


@pytest.fixture
def _qt_app():
    """Ensure QApplication instance exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_parent(_qtbot):
    """Create a mock parent widget."""
    parent = Mock()
    parent.setCursor = Mock()
    parent.cursor = Mock(return_value=Qt.WaitCursor)
    return parent


class TestSaveCancelBehavior:
    """Test save operation cancel behavior with ESC key."""

    def test_normal_save_esc_blocked_by_default(self, _qt_app, qtbot):
        """Test that normal save blocks ESC by default (config = False)."""
        with patch("oncutf.config.SAVE_OPERATION_SETTINGS", {"ALLOW_CANCEL_NORMAL_SAVE": False}):
            dialog = ProgressDialog(
                parent=None,
                operation_type="metadata_save",
                cancel_callback=Mock(),
                is_exit_save=False,
            )
            qtbot.addWidget(dialog)

            # Verify ESC should be blocked
            assert dialog._should_block_esc() is True

            # Try to press ESC
            cancel_mock = dialog.cancel_callback
            QTest.keyPress(dialog, Qt.Key_Escape)

            # Cancel callback should NOT be called
            cancel_mock.assert_not_called()

            dialog.close()

    def test_normal_save_esc_allowed_when_config_enabled(self, _qt_app, qtbot):
        """Test that normal save allows ESC when config is True."""
        with patch("oncutf.config.SAVE_OPERATION_SETTINGS", {"ALLOW_CANCEL_NORMAL_SAVE": True}):
            cancel_callback = Mock()
            dialog = ProgressDialog(
                parent=None,
                operation_type="metadata_save",
                cancel_callback=cancel_callback,
                is_exit_save=False,
            )
            qtbot.addWidget(dialog)

            # Verify ESC should be allowed
            assert dialog._should_block_esc() is False

            # Press ESC
            QTest.keyPress(dialog, Qt.Key_Escape)
            QApplication.processEvents()

            # Cancel callback should be called
            cancel_callback.assert_called_once()

    def test_exit_save_esc_always_blocked(self, _qt_app, qtbot):
        """Test that exit save always blocks ESC regardless of config."""
        # Test with config = True (should still block)
        with patch("oncutf.config.SAVE_OPERATION_SETTINGS", {"ALLOW_CANCEL_NORMAL_SAVE": True}):
            dialog = ProgressDialog(
                parent=None,
                operation_type="metadata_save",
                cancel_callback=Mock(),
                is_exit_save=True,
            )
            qtbot.addWidget(dialog)

            # Verify ESC should be blocked
            assert dialog._should_block_esc() is True

            # Try to press ESC
            cancel_mock = dialog.cancel_callback
            QTest.keyPress(dialog, Qt.Key_Escape)

            # Cancel callback should NOT be called
            cancel_mock.assert_not_called()

            dialog.close()

    def test_non_save_operations_allow_esc(self, _qt_app, qtbot):
        """Test that non-save operations (metadata load, hash) allow ESC."""
        for operation_type in [
            "metadata_basic",
            "metadata_extended",
            "hash_calculation",
            "file_loading",
        ]:
            cancel_callback = Mock()
            dialog = ProgressDialog(
                parent=None,
                operation_type=operation_type,
                cancel_callback=cancel_callback,
                is_exit_save=False,
            )
            qtbot.addWidget(dialog)

            # Verify ESC should be allowed
            assert (
                dialog._should_block_esc() is False
            ), f"ESC should be allowed for {operation_type}"

            # Press ESC
            QTest.keyPress(dialog, Qt.Key_Escape)
            QApplication.processEvents()

            # Cancel callback should be called
            cancel_callback.assert_called_once()

            dialog.close()

    def test_exit_save_flag_propagation(self, _qt_app):
        """Test that is_exit_save flag is properly stored."""
        dialog = ProgressDialog(
            parent=None,
            operation_type="metadata_save",
            is_exit_save=True,
        )

        assert dialog.is_exit_save is True
        dialog.close()

    def test_normal_save_flag_default(self, _qt_app):
        """Test that is_exit_save defaults to False."""
        dialog = ProgressDialog(
            parent=None,
            operation_type="metadata_save",
        )

        assert dialog.is_exit_save is False
        dialog.close()

    def test_should_block_esc_logic(self, _qt_app):
        """Test _should_block_esc logic comprehensively."""
        # Case 1: Exit save always blocks
        dialog = ProgressDialog(
            parent=None,
            operation_type="metadata_save",
            is_exit_save=True,
        )
        assert dialog._should_block_esc() is True
        dialog.close()

        # Case 2: Normal save with ALLOW_CANCEL_NORMAL_SAVE = False blocks
        with patch("oncutf.config.SAVE_OPERATION_SETTINGS", {"ALLOW_CANCEL_NORMAL_SAVE": False}):
            dialog = ProgressDialog(
                parent=None,
                operation_type="metadata_save",
                is_exit_save=False,
            )
            assert dialog._should_block_esc() is True
            dialog.close()

        # Case 3: Normal save with ALLOW_CANCEL_NORMAL_SAVE = True allows
        with patch("oncutf.config.SAVE_OPERATION_SETTINGS", {"ALLOW_CANCEL_NORMAL_SAVE": True}):
            dialog = ProgressDialog(
                parent=None,
                operation_type="metadata_save",
                is_exit_save=False,
            )
            assert dialog._should_block_esc() is False
            dialog.close()

        # Case 4: Non-save operations always allow
        for op_type in ["metadata_basic", "hash_calculation"]:
            dialog = ProgressDialog(
                parent=None,
                operation_type=op_type,
                is_exit_save=False,
            )
            assert dialog._should_block_esc() is False
            dialog.close()


@pytest.mark.integration
class TestSaveCancelIntegration:
    """Integration tests for save cancel behavior in full context."""

    def test_metadata_manager_exit_save_flag(self):
        """Test that metadata manager passes is_exit_save correctly."""
        # Test that the signature accepts is_exit_save parameter
        # We test this by checking the method signature directly
        import inspect

        from oncutf.core.metadata import UnifiedMetadataManager

        # Get the signature of save_all_modified_metadata
        sig = inspect.signature(UnifiedMetadataManager.save_all_modified_metadata)

        # Verify is_exit_save parameter exists
        assert "is_exit_save" in sig.parameters

        # Verify default value is False
        param = sig.parameters["is_exit_save"]
        assert param.default is False

    def test_config_default_value(self):
        """Test that SAVE_OPERATION_SETTINGS has correct default."""
        from oncutf.config import SAVE_OPERATION_SETTINGS

        assert "ALLOW_CANCEL_NORMAL_SAVE" in SAVE_OPERATION_SETTINGS
        # Default is now True (cancellation enabled) - updated for user convenience
        assert SAVE_OPERATION_SETTINGS["ALLOW_CANCEL_NORMAL_SAVE"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
