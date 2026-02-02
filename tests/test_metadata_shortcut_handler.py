"""Module: test_metadata_shortcut_handler.py

Author: Michael Economou
Date: 2025-12-21

Unit tests for MetadataShortcutHandler.

Tests cover:
- Modifier key detection and metadata mode determination
- Shortcut method delegation
- Edge cases for modifier combinations
"""

from __future__ import annotations

from unittest.mock import MagicMock

# Qt modifier key values
QT_NO_MODIFIER = 0
QT_CTRL_MODIFIER = 0x04000000
QT_SHIFT_MODIFIER = 0x02000000
QT_CTRL_SHIFT = QT_CTRL_MODIFIER | QT_SHIFT_MODIFIER


class TestModifierDetection:
    """Tests for modifier key detection logic."""

    def test_no_modifier_skips_metadata(self) -> None:
        """No modifiers should skip metadata loading."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        # Mock manager
        mock_manager = MagicMock()
        mock_manager.parent_window = None

        handler = MetadataShortcutHandler(mock_manager, parent_window=None)

        # Pass modifier_state directly - no patching needed
        skip_metadata, use_extended = handler.determine_metadata_mode(modifier_state=QT_NO_MODIFIER)

        assert skip_metadata is True
        assert use_extended is False

    def test_ctrl_only_loads_fast_metadata(self) -> None:
        """Ctrl modifier should load fast metadata."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        mock_manager = MagicMock()
        mock_manager.parent_window = None

        handler = MetadataShortcutHandler(mock_manager, parent_window=None)

        skip_metadata, use_extended = handler.determine_metadata_mode(
            modifier_state=QT_CTRL_MODIFIER
        )

        assert skip_metadata is False
        assert use_extended is False

    def test_ctrl_shift_loads_extended_metadata(self) -> None:
        """Ctrl+Shift should load extended metadata."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        mock_manager = MagicMock()
        mock_manager.parent_window = None

        handler = MetadataShortcutHandler(mock_manager, parent_window=None)

        skip_metadata, use_extended = handler.determine_metadata_mode(modifier_state=QT_CTRL_SHIFT)

        assert skip_metadata is False
        assert use_extended is True

    def test_shift_only_skips_metadata(self) -> None:
        """Shift alone (without Ctrl) should skip metadata."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        mock_manager = MagicMock()
        mock_manager.parent_window = None

        handler = MetadataShortcutHandler(mock_manager, parent_window=None)

        skip_metadata, use_extended = handler.determine_metadata_mode(
            modifier_state=QT_SHIFT_MODIFIER
        )

        # Shift without Ctrl = no metadata
        assert skip_metadata is True
        assert use_extended is False


class TestShouldUseExtendedMetadata:
    """Tests for should_use_extended_metadata helper method."""

    def test_returns_true_for_ctrl_shift(self) -> None:
        """Should return True when Ctrl+Shift are both held."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        mock_manager = MagicMock()
        mock_manager.parent_window = None

        handler = MetadataShortcutHandler(mock_manager, parent_window=None)

        result = handler.should_use_extended_metadata(modifier_state=QT_CTRL_SHIFT)

        assert result is True

    def test_returns_false_for_ctrl_only(self) -> None:
        """Should return False when only Ctrl is held."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        mock_manager = MagicMock()
        mock_manager.parent_window = None

        handler = MetadataShortcutHandler(mock_manager, parent_window=None)

        result = handler.should_use_extended_metadata(modifier_state=QT_CTRL_MODIFIER)

        assert result is False

    def test_returns_false_for_no_modifiers(self) -> None:
        """Should return False when no modifiers are held."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        mock_manager = MagicMock()
        mock_manager.parent_window = None

        handler = MetadataShortcutHandler(mock_manager, parent_window=None)

        result = handler.should_use_extended_metadata(modifier_state=QT_NO_MODIFIER)

        assert result is False


class TestShortcutMethods:
    """Tests for shortcut method delegation."""

    def test_shortcut_load_metadata_no_window_returns_early(self) -> None:
        """shortcut_load_metadata should return early with no parent window."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        mock_manager = MagicMock()
        mock_manager.parent_window = None

        handler = MetadataShortcutHandler(mock_manager, parent_window=None)

        # Should not raise, just return early
        handler.shortcut_load_metadata()

        # Manager's load method should not be called
        mock_manager.load_metadata_for_items.assert_not_called()

    def test_shortcut_load_extended_no_window_returns_early(self) -> None:
        """shortcut_load_extended_metadata should return early with no parent window."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        mock_manager = MagicMock()
        mock_manager.parent_window = None

        handler = MetadataShortcutHandler(mock_manager, parent_window=None)

        # Should not raise, just return early
        handler.shortcut_load_extended_metadata()

        # Manager's load method should not be called
        mock_manager.load_metadata_for_items.assert_not_called()

    def test_shortcut_load_extended_blocked_when_running(self) -> None:
        """Extended metadata should be blocked if task is already running."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        mock_manager = MagicMock()
        mock_manager.parent_window = None
        mock_manager.is_running_metadata_task.return_value = True

        mock_window = MagicMock()

        handler = MetadataShortcutHandler(mock_manager, parent_window=mock_window)

        handler.shortcut_load_extended_metadata()

        # Manager's load method should not be called
        mock_manager.load_metadata_for_items.assert_not_called()


class TestParentWindowProperty:
    """Tests for parent_window property behavior."""

    def test_uses_own_parent_window_first(self) -> None:
        """Should use own parent_window if set."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        mock_manager = MagicMock()
        manager_window = MagicMock()
        mock_manager.parent_window = manager_window

        own_window = MagicMock()

        handler = MetadataShortcutHandler(mock_manager, parent_window=own_window)

        assert handler.parent_window is own_window

    def test_falls_back_to_manager_window(self) -> None:
        """Should fall back to manager's parent_window if own is None."""
        from oncutf.ui.handlers.metadata_shortcuts import (
            MetadataShortcutHandler,
        )

        mock_manager = MagicMock()
        manager_window = MagicMock()
        mock_manager.parent_window = manager_window

        handler = MetadataShortcutHandler(mock_manager, parent_window=None)

        assert handler.parent_window is manager_window
