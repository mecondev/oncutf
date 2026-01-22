# Migration Guide - Using New Infrastructure Layer

**Author:** Michael Economou  
**Date:** 2026-01-22  
**Status:** Active

## Overview

This guide shows how to migrate from old patterns to the new layered architecture.

## Quick Reference

### ExifTool Operations

**OLD (DEPRECATED):**
```python
from oncutf.services.exiftool_service import ExifToolService

service = ExifToolService()
metadata = service.load_metadata(Path("image.jpg"))
```

**NEW (RECOMMENDED):**
```python
from oncutf.infra.external import get_exiftool_client

client = get_exiftool_client()
metadata = client.extract_metadata(Path("image.jpg"))
```

**For batch operations:**
```python
from oncutf.infra.external import get_exiftool_client

client = get_exiftool_client()
paths = [Path("img1.jpg"), Path("img2.jpg")]
results = client.extract_batch(paths)  # Dict[str, Dict[str, Any]]
```

### Metadata Caching

**OLD (scattered):**
```python
# Various cache implementations across codebase
self._metadata_cache[key] = value
```

**NEW (canonical):**
```python
from oncutf.infra.cache import get_metadata_cache

cache = get_metadata_cache()
cache.set(Path("image.jpg"), metadata)
metadata = cache.get(Path("image.jpg"))
```

**Features:**
- TTL-based expiration (default 5 minutes)
- File modification time tracking
- Thread-safe operations
- Automatic cleanup

### File Database Operations

**OLD (models→core cycle):**
```python
# In FileItem class
from oncutf.core.database.database_manager import get_database_manager

db = get_database_manager()
folder_id = db.get_folder_id(self.folder_path)
```

**NEW (repository pattern):**
```python
from oncutf.infra.db import get_file_repository

repo = get_file_repository()
folder_id = repo.get_folder_id(file_item.folder_path)
```

**Operations:**
```python
from oncutf.infra.db import get_file_repository

repo = get_file_repository()

# Get folder ID
folder_id = repo.get_folder_id("/path/to/folder")

# Ensure folder exists (creates if needed)
folder_id = repo.ensure_folder_exists("/path/to/folder")

# Hash operations
hash_value = repo.get_file_hash("/path/to/file.jpg")
success = repo.store_file_hash("/path/to/file.jpg", "abc123...")
```

### User Dialogs (Breaking core→ui cycles)

**OLD (direct UI import in core):**
```python
# In core module
from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

CustomMessageDialog.critical(parent, "Error", "Something went wrong")
```

**NEW (port-based):**
```python
# In core/app module - depend on protocol
from oncutf.app.ports import UserDialogPort

class SomeManager:
    def __init__(self, dialog_port: UserDialogPort | None = None):
        self._dialog = dialog_port
    
    def some_method(self):
        if self._dialog:
            self._dialog.show_error("Error", "Something went wrong")

# In UI layer - wire up adapter
from oncutf.ui.adapters.qt_user_interaction import QtUserDialogAdapter

dialog_adapter = QtUserDialogAdapter(parent=self)
manager = SomeManager(dialog_port=dialog_adapter)
```

### Status Messages

**OLD:**
```python
if self.parent_window and hasattr(self.parent_window, "status_bar"):
    self.parent_window.status_bar.showMessage("Processing...", 5000)
```

**NEW:**
```python
from oncutf.app.ports import StatusReporter

class SomeManager:
    def __init__(self, status_reporter: StatusReporter | None = None):
        self._status = status_reporter
    
    def some_method(self):
        if self._status:
            self._status.show_status("Processing...", 5000)

# In UI layer
from oncutf.ui.adapters.qt_user_interaction import QtStatusReporter

status_reporter = QtStatusReporter(self.status_bar)
manager = SomeManager(status_reporter=status_reporter)
```

## Module Locations

### Infrastructure Layer

| Component | Location | Purpose |
|-----------|----------|---------|
| ExifToolClient | `infra/external/exiftool_client.py` | Canonical ExifTool operations |
| MetadataCache | `infra/cache/metadata_cache.py` | Metadata caching with TTL |
| FileRepository | `infra/db/file_repository.py` | File database operations |

### Application Layer

| Component | Location | Purpose |
|-----------|----------|---------|
| MetadataProvider | `app/ports/metadata.py` | Metadata extraction protocol |
| UserDialogPort | `app/ports/user_interaction.py` | Dialog interface protocol |
| StatusReporter | `app/ports/user_interaction.py` | Status message protocol |

### UI Layer

| Component | Location | Purpose |
|-----------|----------|---------|
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
from oncutf.infra.external import ExifToolClient
from pathlib import Path

def test_exiftool_extraction():
    client = ExifToolClient()
    assert client.is_available()
    
    metadata = client.extract_metadata(Path("test.jpg"))
    assert isinstance(metadata, dict)
```

## Deprecation Timeline

| Module | Status | Removal Target |
|--------|--------|----------------|
| `services/exiftool_service.py` | Deprecated | v2.0 |
| `utils/metadata/exiftool_adapter.py` | To be deprecated | v2.0 |
| Direct `core→ui` imports | Forbidden (new code) | Ongoing |

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

## Migration Strategy

1. **New code:** Use new patterns from day one
2. **Bug fixes:** Migrate small sections as needed
3. **Refactoring:** Systematic migration of modules
4. **Deprecation:** Mark old patterns, remove after 2 releases

## Questions?

Check:
- [phase_a_implementation_guide.md](phase_a_implementation_guide.md) - Implementation details
- [migration_stance.md](migration_stance.md) - Architecture rules
- [import_cycles_analysis_260122.md](reports/import_cycles_analysis_260122.md) - Identified issues
