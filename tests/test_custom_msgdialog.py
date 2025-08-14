"""
Module: test_custom_msgdialog.py

Author: Michael Economou
Date: 2025-05-31

This module contains unit tests for the CustomMessageDialog class used in the oncutf application.
CustomMessageDialog is a styled and flexible alternative to the standard QMessageBox, supporting:
- Modal and non-modal dialogs
- Progress bar display for long-running operations
- Cancel via Escape key
- Custom question and conflict dialogs
Tests in this module cover:
- Dialog creation and visibility
- Escape key cancellation behavior
- Progress bar value updates
- Static dialogs for questions and information
- File conflict resolution options
- Application modality settings
- Callback triggering (e.g., accept on cancel)
These tests ensure consistent and reliable user interaction in dialog-based flows within the application.
"""

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

#!/usr/bin/python3
# coding: utf-8

"""
Module: test_custom_msgdialog.py

This module contains unit tests for the CustomMessageDialog class used in the oncutf application.

CustomMessageDialog is a styled and flexible alternative to the standard QMessageBox, supporting:
- Modal and non-modal dialogs
- Progress bar display for long-running operations
- Cancel via Escape key
- Custom question and conflict dialogs

Tests in this module cover:
- Dialog creation and visibility
- Escape key cancellation behavior
- Progress bar value updates
- Static dialogs for questions and information
- File conflict resolution options
- Application modality settings
- Callback triggering (e.g., accept on cancel)

These tests ensure consistent and reliable user interaction in dialog-based flows within the application.
"""


import os

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget

from widgets.custom_message_dialog import CustomMessageDialog


@pytest.mark.skipif("CI" in os.environ, reason="Fails on CI due to GUI")
def test_esc_key_triggers_cancel(qtbot) -> None:  # noqa: ARG001
    dlg = CustomMessageDialog.show_waiting(None, "Reading metadata…")
    qtbot.addWidget(dlg)
    assert dlg.isVisible(), "Dialog should be visible initially"

    qtbot.keyPress(dlg, Qt.Key_Escape)
    qtbot.wait(1200)

    assert not dlg.isVisible(), "Dialog should close after Esc"
    assert dlg.label.text() == "Canceling metadata scan..."


def test_progress_updates_correctly(qtbot) -> None:  # noqa: ARG001
    dlg = CustomMessageDialog.show_waiting(None, "Loading...")
    qtbot.addWidget(dlg)
    dlg.set_progress_range(10)
    dlg.set_progress(5)

    assert dlg.progress_bar.value() == 5
    assert dlg.progress_bar.maximum() == 10


def test_dialog_question_response_yes(qtbot, monkeypatch) -> None:  # noqa: ARG001
    monkeypatch.setattr(CustomMessageDialog, "exec_", lambda self: setattr(self, "selected", "Yes"))
    result = CustomMessageDialog.question(QWidget(), "Test", "Do you confirm?", "Yes", "No")
    assert result is True


def test_dialog_question_response_no(qtbot, monkeypatch) -> None:  # noqa: ARG001
    monkeypatch.setattr(CustomMessageDialog, "exec_", lambda self: setattr(self, "selected", "No"))
    result = CustomMessageDialog.question(QWidget(), "Test", "Do you confirm?", "Yes", "No")
    assert result is False


def test_information_dialog_sets_message(qtbot, monkeypatch) -> None:  # noqa: ARG001
    captured = {}

    def fake_exec(self):
        captured["message"] = self.label.text()
        return None

    monkeypatch.setattr(CustomMessageDialog, "exec_", fake_exec)
    CustomMessageDialog.information(QWidget(), "Notice", "Everything is OK.")

    assert captured["message"] == "Everything is OK."


def test_conflict_dialog_selection_skip(qtbot, monkeypatch) -> None:  # noqa: ARG001
    monkeypatch.setattr(
        CustomMessageDialog, "exec_", lambda self: setattr(self, "selected", "Skip")
    )
    result = CustomMessageDialog.rename_conflict_dialog(QWidget(), "example.txt")
    assert result == "skip"


def test_conflict_dialog_selection_overwrite(qtbot, monkeypatch) -> None:  # noqa: ARG001
    monkeypatch.setattr(
        CustomMessageDialog, "exec_", lambda self: setattr(self, "selected", "Overwrite")
    )
    result = CustomMessageDialog.rename_conflict_dialog(QWidget(), "example.txt")
    assert result == "overwrite"


def test_waiting_dialog_is_application_modal(qtbot) -> None:  # noqa: ARG001
    dlg = CustomMessageDialog.show_waiting(None, "Working...")
    qtbot.addWidget(dlg)

    assert dlg.isModal()
    assert dlg.windowModality() == Qt.ApplicationModal


def test_escape_triggers_callback_and_close(qtbot) -> None:  # noqa: ARG001
    # Create the dialog
    dlg = CustomMessageDialog.show_waiting(None, "Reading...")
    qtbot.addWidget(dlg)

    # Track whether reject() was called (close via Esc)
    rejected = {"called": False}

    def fake_reject():
        rejected["called"] = True
        dlg.close()

    dlg.reject = fake_reject

    qtbot.keyPress(dlg, Qt.Key_Escape)
    qtbot.wait(1200)

    assert rejected["called"], "Dialog should call reject() when Esc is pressed"
    assert not dlg.isVisible(), "Dialog should close after Esc"
