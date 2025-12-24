"""Module: test_loading_dialog.py

Author: Michael Economou
Date: 2025-05-09

This module contains tests for the loading dialog behavior used in the oncutf application,
specifically for the non-blocking progress dialog implemented via CustomMessageDialog.show_waiting().
The tests validate:
- Correct initialization and visibility of the dialog
- Dynamic updates of progress bar values and ranges
- Signal-based integration with background workers (e.g., FakeWorker)
- Proper closure of the dialog upon completion
- Modal behavior and safe event handling
These tests ensure that the loading dialog provides responsive and reliable user feedback
during asynchronous operations like metadata scanning.
"""

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

#!/usr/bin/python3
# coding: utf-8

"""
Module: test_loading_dialog.py

This module contains tests for the loading dialog behavior used in the oncutf application,
specifically for the non-blocking progress dialog implemented via CustomMessageDialog.show_waiting().

The tests validate:
- Correct initialization and visibility of the dialog
- Dynamic updates of progress bar values and ranges
- Signal-based integration with background workers (e.g., FakeWorker)
- Proper closure of the dialog upon completion
- Modal behavior and safe event handling

These tests ensure that the loading dialog provides responsive and reliable user feedback
during asynchronous operations like metadata scanning.
"""

import pytest
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget

from oncutf.ui.widgets.custom_message_dialog import CustomMessageDialog


class FakeWorker(QObject):
    """A fake worker with progressed and finished signals to simulate metadata loading.
    """

    progressed = pyqtSignal(int, int)  # emit(value, total)
    finished = pyqtSignal()


@pytest.fixture
def parent_widget(qtbot):
    """A simple parent QWidget for dialogs.
    """
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


@pytest.fixture
def dialog(qtbot, parent_widget):
    """Create a non-modal waiting dialog using show_waiting.
    """
    dlg = CustomMessageDialog.show_waiting(parent_widget, message="Loading...")
    qtbot.addWidget(dlg)
    assert dlg.progress_bar is not None, "Progress bar should be initialized"
    assert dlg.isVisible(), "Dialog should be visible after show_waiting"
    return dlg


def test_progress_and_range(dialog, qtbot):
    # Initially, range is indeterminate (0,0) if not set
    # Now set a concrete range
    dialog.set_progress_range(4)
    assert dialog.progress_bar.minimum() == 0
    assert dialog.progress_bar.maximum() == 4
    assert dialog.progress_bar.value() == 0

    # Simulate progress and check value
    dialog.set_progress(2)
    qtbot.wait(10)
    assert dialog.progress_bar.value() == 2

    # Simulate progress with total override
    dialog.set_progress(3, total=5)
    qtbot.wait(10)
    assert dialog.progress_bar.maximum() == 5
    assert dialog.progress_bar.value() == 3

    # Emit finished should close dialog
    dialog.accept()
    qtbot.wait(10)
    assert not dialog.isVisible(), "Dialog should be hidden after accept()"


def test_signal_integration(dialog, qtbot):
    # Test integrating with a fake worker via signals
    worker = FakeWorker()

    # Connect worker signals to dialog slots
    # Note: FakeWorker.progressed emits two args: value, total
    worker.progressed.connect(dialog.set_progress)
    worker.finished.connect(dialog.accept)

    # Simulate setting range via signal
    worker.progressed.emit(1, 4)
    qtbot.wait(10)
    assert dialog.progress_bar.maximum() == 4
    assert dialog.progress_bar.value() == 1

    # Simulate progress update without changing range
    worker.progressed.emit(2, None)
    qtbot.wait(10)
    assert dialog.progress_bar.value() == 2

    # Simulate finish and check closure
    worker.finished.emit()
    qtbot.wait(10)
    assert not dialog.isVisible(), "Dialog should close when worker.finished is emitted"
