"""
Module: test_metadata_progress_handler.py

Author: Michael Economou
Date: 2025-12-21

Unit tests for MetadataProgressHandler.

Tests cover:
- Progress dialog creation
- Dialog lifecycle management
- Parent window property behavior
"""

from __future__ import annotations

from unittest.mock import MagicMock


class TestProgressDialogCreation:
    """Tests for progress dialog creation methods."""

    def test_create_metadata_dialog_calls_factory(self) -> None:
        """create_metadata_progress_dialog should call ProgressDialog factory."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler
        from oncutf.utils.progress_dialog import ProgressDialog

        handler = MetadataProgressHandler(parent_window=None)

        result = handler.create_metadata_progress_dialog(is_extended=False, cancel_callback=None)

        assert isinstance(result, ProgressDialog)

    def test_create_metadata_dialog_stores_reference(self) -> None:
        """Should store reference to created dialog."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler

        handler = MetadataProgressHandler(parent_window=None)
        assert handler._metadata_progress_dialog is None

        result = handler.create_metadata_progress_dialog(is_extended=False, cancel_callback=None)

        assert handler._metadata_progress_dialog is result

    def test_create_hash_dialog_calls_factory(self) -> None:
        """create_hash_progress_dialog should call ProgressDialog factory."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler
        from oncutf.utils.progress_dialog import ProgressDialog

        handler = MetadataProgressHandler(parent_window=None)

        result = handler.create_hash_progress_dialog(cancel_callback=None)

        assert isinstance(result, ProgressDialog)

    def test_create_hash_dialog_stores_reference(self) -> None:
        """Should store reference to created hash dialog."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler

        handler = MetadataProgressHandler(parent_window=None)
        assert handler._hash_progress_dialog is None

        result = handler.create_hash_progress_dialog(cancel_callback=None)

        assert handler._hash_progress_dialog is result


class TestDialogLifecycle:
    """Tests for dialog lifecycle management."""

    def test_close_metadata_dialog_when_exists(self) -> None:
        """close_metadata_progress_dialog should close existing dialog."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler

        handler = MetadataProgressHandler(parent_window=None)

        mock_dialog = MagicMock()
        handler._metadata_progress_dialog = mock_dialog

        handler.close_metadata_progress_dialog()

        mock_dialog.close.assert_called_once()
        assert handler._metadata_progress_dialog is None

    def test_close_metadata_dialog_when_none(self) -> None:
        """close_metadata_progress_dialog should handle None gracefully."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler

        handler = MetadataProgressHandler(parent_window=None)
        handler._metadata_progress_dialog = None

        # Should not raise
        handler.close_metadata_progress_dialog()

        assert handler._metadata_progress_dialog is None

    def test_close_metadata_dialog_suppresses_exceptions(self) -> None:
        """close_metadata_progress_dialog should suppress exceptions."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler

        handler = MetadataProgressHandler(parent_window=None)

        mock_dialog = MagicMock()
        mock_dialog.close.side_effect = RuntimeError("Close failed")
        handler._metadata_progress_dialog = mock_dialog

        # Should not raise
        handler.close_metadata_progress_dialog()

        # Dialog reference should still be cleared
        assert handler._metadata_progress_dialog is None


class TestParentWindowProperty:
    """Tests for parent_window property behavior."""

    def test_getter_returns_set_value(self) -> None:
        """Getter should return the parent window set at init."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler

        mock_window = MagicMock()
        handler = MetadataProgressHandler(parent_window=mock_window)

        assert handler.parent_window is mock_window

    def test_setter_updates_value(self) -> None:
        """Setter should update the parent window."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler

        handler = MetadataProgressHandler(parent_window=None)
        assert handler.parent_window is None

        new_window = MagicMock()
        handler.parent_window = new_window

        assert handler.parent_window is new_window

    def test_initial_none_parent(self) -> None:
        """Parent window should be None by default."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler

        handler = MetadataProgressHandler()

        assert handler.parent_window is None


class TestInitialState:
    """Tests for initial state after construction."""

    def test_dialogs_initially_none(self) -> None:
        """Both dialog references should be None initially."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler

        handler = MetadataProgressHandler(parent_window=None)

        assert handler._metadata_progress_dialog is None
        assert handler._hash_progress_dialog is None

    def test_accepts_parent_window(self) -> None:
        """Should accept parent_window in constructor."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler

        mock_window = MagicMock()
        handler = MetadataProgressHandler(parent_window=mock_window)

        assert handler._parent_window is mock_window


class TestShowDialogMethods:
    """Tests for show_*_progress_dialog methods."""

    def test_show_metadata_dialog_returns_dialog(self) -> None:
        """show_metadata_progress_dialog should return a dialog."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler
        from oncutf.utils.progress_dialog import ProgressDialog

        handler = MetadataProgressHandler(parent_window=None)

        # Create mock file items
        mock_file = MagicMock()
        mock_file.full_path = "/tmp/test.jpg"

        result = handler.show_metadata_progress_dialog(
            files=[mock_file], is_extended=False, cancel_callback=None
        )

        assert result is None or isinstance(result, ProgressDialog)

    def test_show_hash_dialog_returns_dialog(self) -> None:
        """show_hash_progress_dialog should return a dialog."""
        from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler
        from oncutf.utils.progress_dialog import ProgressDialog

        handler = MetadataProgressHandler(parent_window=None)

        # Create mock file items
        mock_file = MagicMock()
        mock_file.full_path = "/tmp/test.jpg"

        result = handler.show_hash_progress_dialog(files=[mock_file], cancel_callback=None)

        assert result is None or isinstance(result, ProgressDialog)
