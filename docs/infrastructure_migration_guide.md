# Infrastructure Layer - Usage Guide

**Author:** Michael Economou
**Date:** 2026-01-22

## Overview

Reference for using the layered architecture patterns.

## Quick Reference

### Metadata Operations

```python
from oncutf.infra.external import get_exopsis_client

client = get_exopsis_client()
metadata = client.extract_metadata(Path("image.jpg"))
```

**For batch operations:**

```python
from oncutf.infra.external import get_exopsis_client

client = get_exopsis_client()
paths = [Path("img1.jpg"), Path("img2.jpg")]
results = client.extract_batch(paths)  # Dict[str, Dict[str, Any]]
```

### Metadata Caching

```python
from oncutf.infra.cache import get_metadata_cache

cache = get_metadata_cache()
cache.set(Path("image.jpg"), metadata)
metadata = cache.get(Path("image.jpg"))
```

Features: TTL expiration (default 5 min), mtime tracking, thread-safe, auto-cleanup.

### File Database Operations

```python
from oncutf.infra.db import get_file_repository

repo = get_file_repository()
folder_id = repo.get_folder_id("/path/to/folder")
folder_id = repo.ensure_folder_exists("/path/to/folder")
hash_value = repo.get_file_hash("/path/to/file.jpg")
repo.store_file_hash("/path/to/file.jpg", "abc123...")
```

### User Dialogs

```python
# core/app module — depend on protocol
from oncutf.app.ports import UserDialogPort

class SomeManager:
    def __init__(self, dialog_port: UserDialogPort | None = None):
        self._dialog = dialog_port

    def some_method(self):
        if self._dialog:
            self._dialog.show_error("Error", "Something went wrong")

# UI layer — wire up Qt adapter
from oncutf.ui.adapters.qt_user_interaction import QtUserDialogAdapter

manager = SomeManager(dialog_port=QtUserDialogAdapter(parent=self))
```

### Status Messages

```python
from oncutf.app.ports import StatusReporter

class SomeManager:
    def __init__(self, status_reporter: StatusReporter | None = None):
        self._status = status_reporter

    def some_method(self):
        if self._status:
            self._status.show_status("Processing...", 5000)
```

For metadata status use `MetadataUIBridge` (`core/metadata/metadata_ui_bridge.py`).

## Module Locations

### Infrastructure Layer

| Component | Location | Purpose |
| --------- | -------- | -------- |
| ExopsisClient | `infra/external/exopsis_client.py` | Metadata extraction (delegates to exopsis) |
| MetadataCache | `infra/cache/metadata_cache.py` | Metadata caching with TTL |
| FileRepository | `infra/db/file_repository.py` | File database operations |

### Application Layer

| Component | Location | Purpose |
| --------- | -------- | ------- |
| MetadataProvider | `app/ports/metadata.py` | Metadata extraction protocol |
| UserDialogPort | `app/ports/user_interaction.py` | Dialog interface protocol |
| StatusReporter | `app/ports/user_interaction.py` | Status message protocol |

### UI Layer

| Component | Location | Purpose |
| --------- | -------- | ------- |
| QtUserDialogAdapter | `ui/adapters/qt_user_interaction.py` | Qt dialog implementation |
| QtStatusReporter | `ui/adapters/qt_user_interaction.py` | Qt status bar implementation |

## Testing

### Unit Tests (without Qt)

```python
# Test with mock implementations
from unittest.mock import Mock

mock_dialog = Mock()
mock_dialog.show_error = Mock()

manager = SomeManager(dialog_port=mock_dialog)
manager.some_method()

mock_dialog.show_error.assert_called_once()
```

### Integration Tests

```python
from oncutf.infra.external import ExopsisClient
from pathlib import Path

def test_metadata_extraction():
    client = ExopsisClient()
    assert client.is_available()

    metadata = client.extract_metadata(Path("test.jpg"))
    assert isinstance(metadata, dict)
```

## Benefits

### Separation of Concerns

- Business logic (app) separate from UI (ui)
- Infrastructure (infra) separate from domain
- Clear dependency direction

### Testability

- Mock ports for unit testing
- No Qt dependencies in business logic
- Isolated infrastructure components

### Flexibility

- Easy to swap implementations
- Support multiple UI frameworks
- Independent evolution of layers

## Further Reading

- [docs/architecture.md](architecture.md) — 4-tier design
- [docs/application_workflow.md](application_workflow.md) — init/shutdown flow
