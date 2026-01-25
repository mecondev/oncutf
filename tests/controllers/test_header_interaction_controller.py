"""Module: test_header_interaction_controller.py

Author: Michael Economou
Date: 2026-01-12

Unit tests for HeaderInteractionController.
Tests business logic without Qt dependencies.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest


class TestHeaderInteractionController:
    """Tests for HeaderInteractionController."""

    @pytest.fixture
    def mock_main_window(self):
        """Create a mock main window."""
        mock = Mock()
        mock.handle_header_toggle = Mock()
        mock.sort_by_column = Mock()
        return mock

    @pytest.fixture
    def controller(self, mock_main_window):
        """Create a controller with mock main window."""
        from oncutf.controllers.header_interaction_controller import HeaderInteractionController

        return HeaderInteractionController(mock_main_window)

    def test_handle_toggle_all(self, controller, mock_main_window):
        """Test toggle all action calls main window correctly."""
        controller.handle_toggle_all()

        from PyQt5.QtCore import Qt

        mock_main_window.handle_header_toggle.assert_called_once_with(Qt.Checked)

    def test_handle_sort_without_force_order(self, controller, mock_main_window):
        """Test sort action without forced order."""
        controller.handle_sort(column=3)

        mock_main_window.sort_by_column.assert_called_once_with(3, force_order=None)

    def test_handle_sort_with_force_order(self, controller, mock_main_window):
        """Test sort action with forced order."""
        from PyQt5.QtCore import Qt

        controller.handle_sort(column=5, force_order=Qt.AscendingOrder)

        mock_main_window.sort_by_column.assert_called_once_with(5, force_order=Qt.AscendingOrder)

    def test_validate_column_drag_blocks_status_column_from(self, controller):
        """Test that dragging FROM status column (0) is blocked."""
        result = controller.validate_column_drag(from_visual=0, to_visual=3)

        assert result is False

    def test_validate_column_drag_blocks_status_column_to(self, controller):
        """Test that dragging TO status column (0) is blocked."""
        result = controller.validate_column_drag(from_visual=2, to_visual=0)

        assert result is False

    def test_validate_column_drag_allows_valid_moves(self, controller):
        """Test that valid column drags are allowed."""
        result = controller.validate_column_drag(from_visual=2, to_visual=5)

        assert result is True

    def test_is_status_column_true(self, controller):
        """Test status column detection returns True for column 0."""
        assert controller.is_status_column(0) is True

    def test_is_status_column_false(self, controller):
        """Test status column detection returns False for other columns."""
        assert controller.is_status_column(1) is False
        assert controller.is_status_column(5) is False

    def test_should_handle_click_disabled_actions(self, controller):
        """Test that clicks are ignored when actions are disabled."""
        should_handle, action_type = controller.should_handle_click(
            pressed_index=1,
            released_index=1,
            manhattan_length=2,
            click_actions_enabled=False,
        )

        assert should_handle is False
        assert action_type == ""

    def test_should_handle_click_drag_detected(self, controller):
        """Test that clicks are ignored when drag is detected (manhattan > 4)."""
        should_handle, action_type = controller.should_handle_click(
            pressed_index=1,
            released_index=1,
            manhattan_length=10,
            click_actions_enabled=True,
        )

        assert should_handle is False
        assert action_type == ""

    def test_should_handle_click_position_mismatch(self, controller):
        """Test that clicks are ignored when release position != press position."""
        should_handle, action_type = controller.should_handle_click(
            pressed_index=1,
            released_index=2,
            manhattan_length=2,
            click_actions_enabled=True,
        )

        assert should_handle is False
        assert action_type == ""

    def test_should_handle_click_invalid_index(self, controller):
        """Test that clicks are ignored when released_index is -1."""
        should_handle, action_type = controller.should_handle_click(
            pressed_index=1,
            released_index=-1,
            manhattan_length=2,
            click_actions_enabled=True,
        )

        assert should_handle is False
        assert action_type == ""

    def test_should_handle_click_toggle_action(self, controller):
        """Test that status column click returns toggle action."""
        should_handle, action_type = controller.should_handle_click(
            pressed_index=0,
            released_index=0,
            manhattan_length=2,
            click_actions_enabled=True,
        )

        assert should_handle is True
        assert action_type == "toggle"

    def test_should_handle_click_sort_action(self, controller):
        """Test that other column clicks return sort action."""
        should_handle, action_type = controller.should_handle_click(
            pressed_index=3,
            released_index=3,
            manhattan_length=2,
            click_actions_enabled=True,
        )

        assert should_handle is True
        assert action_type == "sort"
