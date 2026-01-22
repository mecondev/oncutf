# Phase A Implementation Guide - Breaking Import Cycles

**Author:** Michael Economou  
**Date:** 2026-01-22  
**Status:** In Progress

## Overview

This guide describes how to break the import cycles identified in [import_cycles_analysis_260122.md](import_cycles_analysis_260122.md).

## Architecture Created

### New directories:
- `oncutf/app/` - Application layer (use cases, ports, events)
- `oncutf/app/ports/` - Protocol interfaces
- `oncutf/app/use_cases/` - Workflow orchestration
- `oncutf/app/events/` - Plain event objects
- `oncutf/infra/` - Infrastructure layer
- `oncutf/infra/external/` - External tool clients
- `oncutf/infra/cache/` - Cache implementations
- `oncutf/infra/db/` - Database repositories
- `oncutf/infra/filesystem/` - Filesystem adapters
- `oncutf/ui/adapters/` - Qt adapters for ports

### New modules created:
1. `app/ports/user_interaction.py` - Protocols for dialogs/status
2. `ui/adapters/qt_user_interaction.py` - Qt implementations of ports
3. `ui/adapters/__init__.py` - Legacy dialog adapter (for backward compatibility)

## Breaking core→ui Cycles

### Pattern 1: Dialog Dependencies

**Before (violates boundary):**
```python
# oncutf/core/metadata/unified_manager.py
def some_method(self):
    if error:
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog
        CustomMessageDialog.critical(self.parent_window, "Error", message)
```

**After (uses ports):**
```python
# oncutf/core/metadata/unified_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.app.ports.user_interaction import UserDialogPort

class UnifiedMetadataManager:
    def __init__(self, ..., dialog_port: UserDialogPort | None = None):
        self._dialog = dialog_port
        
    def some_method(self):
        if error and self._dialog:
            self._dialog.show_error("Error", message)
```

**Wiring in main_window.py:**
```python
# oncutf/ui/main_window.py
from oncutf.ui.adapters.qt_user_interaction import QtUserDialogAdapter

dialog_adapter = QtUserDialogAdapter(parent=self)
metadata_manager = UnifiedMetadataManager(..., dialog_port=dialog_adapter)
```

### Pattern 2: Status Bar Dependencies

**Before:**
```python
if self.parent_window and hasattr(self.parent_window, "status_bar"):
    self.parent_window.status_bar.showMessage(message, 5000)
```

**After:**
```python
from oncutf.app.ports.user_interaction import StatusReporter

class SomeManager:
    def __init__(self, ..., status_reporter: StatusReporter | None = None):
        self._status = status_reporter
        
    def some_method(self):
        if self._status:
            self._status.show_status(message, 5000)
```

**Wiring:**
```python
from oncutf.ui.adapters.qt_user_interaction import QtStatusReporter

status_reporter = QtStatusReporter(self.status_bar)
manager = SomeManager(..., status_reporter=status_reporter)
```

## Breaking models→core Cycles

### Pattern 3: FileItem → Database

**Current violation:**
```python
# oncutf/models/file_item.py
def get_folder_id(self) -> int | None:
    from oncutf.core.database.database_manager import get_database_manager
    db = get_database_manager()
    return db.get_folder_id(self.folder_path)
```

**Solution - Extract to Repository:**

Step 1: Create repository in infra/db:
```python
# oncutf/infra/db/file_repository.py
class FileRepository:
    def __init__(self, db_manager):
        self._db = db_manager
        
    def get_folder_id(self, folder_path: str) -> int | None:
        return self._db.get_folder_id(folder_path)
```

Step 2: Remove database logic from FileItem:
```python
# oncutf/models/file_item.py
# Remove database import and methods
# FileItem becomes pure data model
```

Step 3: Use repository where needed:
```python
# Where folder_id is needed
from oncutf.infra.db.file_repository import FileRepository

repo = FileRepository(db_manager)
folder_id = repo.get_folder_id(file_item.folder_path)
```

### Pattern 4: models → core/pyqt_imports

**Current:**
```python
# oncutf/models/file_table/icon_manager.py
from oncutf.core.pyqt_imports import QColor, QIcon, QPainter, QPixmap
```

**Solution:**
Keep for now. The pyqt_imports module is a centralized import location. 
In a future phase, we may move it to `oncutf/shared/qt_imports.py` or similar,
but this is low priority compared to breaking core→ui cycles.

**Alternative (if needed):**
```python
# Direct imports (acceptable for models in ui layer)
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
```

## Breaking utils→core Cycles

### Pattern 5: utils/ui → core

**Solution:** Move utils/ui/ → ui/utilities/

```bash
# Migration plan
mv oncutf/utils/ui/ oncutf/ui/utilities/
```

Update all imports:
```python
# Before
from oncutf.utils.ui.cursor_helper import wait_cursor

# After
from oncutf.ui.utilities.cursor_helper import wait_cursor
```

### Pattern 6: utils/naming → core/database

**Current violation:**
```python
# oncutf/utils/naming/renamer.py
from oncutf.core.database.database_manager import get_database_manager
```

**Solution:**
Move database operations to infra layer and pass as dependency:
```python
# Inject database operations via port
from oncutf.app.ports.database import RenameHistoryPort

class Renamer:
    def __init__(self, history_port: RenameHistoryPort | None = None):
        self._history = history_port
```

## Migration Checklist

### High Priority (core→ui cycles):
- [ ] Update `core/metadata/unified_manager.py` to use ports
- [ ] Update `core/metadata/operations_manager.py` to use ports
- [ ] Update `core/metadata/metadata_writer.py` to use ports
- [ ] Update `core/file/operations_manager.py` to use ports
- [ ] Update `core/events/context_menu/rotation_handlers.py` to use ports

### Medium Priority (models→core):
- [ ] Create `infra/db/file_repository.py`
- [ ] Remove database logic from `models/file_item.py`
- [ ] Update callers to use repository

### Lower Priority (utils→core):
- [ ] Move `utils/ui/` → `ui/utilities/`
- [ ] Update all imports
- [ ] Fix `utils/naming/renamer.py` database dependency

## Testing Strategy

1. **No behavior changes** - all existing functionality must work
2. **Run full test suite** after each module update
3. **Manual testing** of dialogs/status messages
4. **Import validation** - use tools to verify no cycles remain

## Exit Criteria

- [ ] No imports from `core/` → `ui/`
- [ ] No database imports from `models/file_item.py`
- [ ] All utils→core cycles broken
- [ ] All 592+ tests pass
- [ ] `ruff check .` passes
- [ ] `mypy .` passes (respecting tier overrides)

## Next Steps

1. Start with highest-impact module: `core/metadata/unified_manager.py`
2. Update one method at a time
3. Test after each change
4. Document patterns for team review
5. Continue with remaining modules

## Notes

- Keep backward compatibility shims temporarily
- Mark deprecated paths with warnings
- Remove deprecated code in Phase B
- Focus on breaking cycles first, cleanup later
