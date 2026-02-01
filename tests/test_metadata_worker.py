"""Module: test_metadata_worker.py

Author: Michael Economou
Date: 2025-05-09

This module provides functionality for the oncutf batch file renaming application.
"""

import time

import pytest
from PyQt5.QtCore import QCoreApplication

from oncutf.ui.widgets.metadata_tree.worker import MetadataWorker


@pytest.fixture
def fake_reader(mocker):
    reader = mocker.Mock()
    reader.extract_metadata.side_effect = lambda _path: (
        time.sleep(0.05),
        {"fake": "data"},
    )[1]
    return reader


@pytest.fixture
def fake_cache(mocker):
    cache = mocker.Mock()
    cache.get_entry.return_value = None
    cache.set.return_value = None
    return cache


def test_metadata_worker_cancel_stops_early(qtbot, fake_reader, fake_cache, mocker):  # noqa: ARG001
    mocker.patch("os.path.getsize", return_value=1024 * 1024)  # Mock file size as 1MB
    app = QCoreApplication.instance() or QCoreApplication([])  # noqa: F841

    files = [f"/fake/path/file{i}.mp4" for i in range(5)]
    worker = MetadataWorker(reader=fake_reader, metadata_cache=fake_cache)
    worker.file_path = files

    progress_updates = []

    def on_progress(current, total):
        progress_updates.append((current, total))
        if current == 2:
            worker.cancel()

    worker.progress.connect(on_progress)

    worker.run_batch()

    assert len(progress_updates) <= 2, "Worker did not stop early after cancel"


def test_metadata_worker_runs_to_completion(qtbot, fake_reader, fake_cache, mocker):  # noqa: ARG001
    mocker.patch("os.path.getsize", return_value=1024 * 1024)  # Mock file size as 1MB
    app = QCoreApplication.instance() or QCoreApplication([])  # noqa: F841

    files = [f"/fake/path/file{i}.mp4" for i in range(3)]
    worker = MetadataWorker(reader=fake_reader, metadata_cache=fake_cache)
    worker.file_path = files

    progress_updates = []

    worker.progress.connect(lambda current, total: progress_updates.append((current, total)))

    worker.run_batch()

    assert (
        len(progress_updates) == 3
    ), f"Worker did not complete all files, got {len(progress_updates)} progress updates"

    # With batch operations, cache.set might not be called directly
    # Instead, check that the reader was called for each file
    assert fake_reader.extract_metadata.call_count == 3, "Reader should be called for each file"
