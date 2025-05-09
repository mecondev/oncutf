import pytest
import time
from PyQt5.QtCore import QCoreApplication, QTimer
from widgets.metadata_worker import MetadataWorker

@pytest.fixture
def fake_reader(mocker):
    reader = mocker.Mock()
    reader.read_metadata.side_effect = lambda path: (time.sleep(0.05), {"fake": "data"})[1]
    return reader

def test_metadata_worker_cancel_stops_early(qtbot, fake_reader):
    app = QCoreApplication.instance() or QCoreApplication([])

    files = [f"/fake/path/file{i}.mp4" for i in range(5)]
    worker = MetadataWorker(fake_reader)

    results = {}
    progress_updates = []

    def on_progress(current, total):
        progress_updates.append((current, total))
        if current == 2:
            worker.cancel()

    worker.progress.connect(on_progress)
    worker.finished.connect(lambda data: results.update(data))

    worker.load_batch(files)

    with qtbot.waitSignal(worker.finished, timeout=3000):
        pass

    assert len(progress_updates) < 5, "Worker did not stop early after cancel"
    assert isinstance(results, dict), "Finished signal should return a dict"

def test_metadata_worker_runs_to_completion(qtbot, fake_reader):
    app = QCoreApplication.instance() or QCoreApplication([])

    files = [f"/fake/path/file{i}.mp4" for i in range(5)]
    worker = MetadataWorker(fake_reader)

    results = {}
    progress_updates = []

    worker.progress.connect(lambda current, total: progress_updates.append((current, total)))
    worker.finished.connect(lambda data: results.update(data))

    worker.load_batch(files)

    with qtbot.waitSignal(worker.finished, timeout=3000):
        pass

    assert len(progress_updates) == 5, "Worker did not complete all files"
    assert len(results) == 5, "Results dictionary does not contain all expected entries"
