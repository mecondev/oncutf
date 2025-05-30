import pytest
import time
from unittest.mock import Mock
from PyQt5.QtCore import QCoreApplication, QTimer
from widgets.metadata_worker import MetadataWorker
import os

@pytest.fixture
def fake_reader(mocker):
    reader = mocker.Mock()
    reader.read_metadata.side_effect = lambda filepath, use_extended=False: (time.sleep(0.05), {"fake": "data"})[1]
    return reader

@pytest.fixture
def fake_cache(mocker):
    cache = mocker.Mock()
    cache.get_entry.return_value = None
    cache.set.return_value = None
    return cache

def test_metadata_worker_cancel_stops_early(qtbot, fake_reader, fake_cache, mocker):
    mocker.patch('os.path.getsize', return_value=1024*1024)  # Mock file size as 1MB
    app = QCoreApplication.instance() or QCoreApplication([])

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


def test_metadata_worker_runs_to_completion(qtbot, fake_reader, fake_cache, mocker):
    mocker.patch('os.path.getsize', return_value=1024*1024)  # Mock file size as 1MB
    app = QCoreApplication.instance() or QCoreApplication([])

    files = [f"/fake/path/file{i}.mp4" for i in range(3)]
    worker = MetadataWorker(reader=fake_reader, metadata_cache=fake_cache)
    worker.file_path = files

    progress_updates = []

    worker.progress.connect(lambda current, total: progress_updates.append((current, total)))

    worker.run_batch()

    assert len(progress_updates) == 3, f"Worker did not complete all files, got {len(progress_updates)} progress updates"
    assert fake_cache.set.call_count == 3, "Cache should be updated for each file"
