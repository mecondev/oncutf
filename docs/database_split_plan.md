# Database Manager Split Plan

**Author:** Michael Economou  
**Date:** 2026-01-01  
**Current:** 1615 lines → **Target:** ~400 lines (main orchestrator)

---

## File Structure

```
oncutf/core/database/
├── __init__.py                    # Re-export DatabaseManager
├── database_manager.py            # Main orchestrator (~400 lines)
├── migrations.py                  # Schema creation + migrations (~350 lines)
├── path_store.py                  # file_paths table operations (~150 lines)
├── metadata_store.py              # Metadata operations (~550 lines)
├── hash_store.py                  # file_hashes table operations (~150 lines)
└── backup_store.py                # Rename history + backup (~150 lines)
```

**Total estimated:** ~1750 lines (includes new structure/imports/docs)

---

## 1. migrations.py (~350 lines)

**Purpose:** Schema creation, version management, migrations, index creation

### Methods to Move:
- `_create_schema_v2(cursor)` (lines 170-289)
- `_migrate_schema(cursor, from_version)` (lines 291-366)
- `_create_indexes(cursor)` (lines 368-408)
- `initialize_default_metadata_schema()` (lines 1154-1415)

### New Interface:
```python
class DatabaseMigrations:
    """Schema creation and migration management."""
    
    SCHEMA_VERSION = 4
    
    @staticmethod
    def initialize_schema(conn: sqlite3.Connection) -> None:
        """Initialize or migrate schema to current version."""
        
    @staticmethod
    def _create_schema_v2(cursor: sqlite3.Cursor) -> None:
        """Create the v2 schema with separated tables."""
        
    @staticmethod
    def _migrate_schema(cursor: sqlite3.Cursor, from_version: int, to_version: int) -> None:
        """Migrate from older schema versions."""
        
    @staticmethod
    def _create_indexes(cursor: sqlite3.Cursor) -> None:
        """Create database indexes for performance."""
        
    @staticmethod
    def initialize_default_metadata_schema(conn: sqlite3.Connection) -> bool:
        """Initialize default metadata categories and fields."""
```

### Dependencies:
- **Imports:** `sqlite3`, `logging`, `logger_factory`
- **No internal dependencies** (pure schema operations)

---

## 2. path_store.py (~150 lines)

**Purpose:** file_paths table CRUD operations

### Methods to Move:
- `get_or_create_path_id(file_path)` (lines 410-462)
- `get_path_id(file_path)` (lines 468-480)
- `_normalize_path(file_path)` (lines 464-466)
- `update_file_path(old_path, new_path)` (lines 1523-1587)

### New Interface:
```python
class PathStore:
    """Manages file_paths table operations."""
    
    def __init__(self, get_connection_func):
        """Initialize with connection provider."""
        self._get_connection = get_connection_func
        
    def get_or_create_path_id(self, file_path: str) -> int:
        """Get path_id for a file, creating record if needed."""
        
    def get_path_id(self, file_path: str) -> int | None:
        """Get path_id for a file without creating it."""
        
    def update_file_path(self, old_path: str, new_path: str) -> bool:
        """Update file path (e.g., after rename operation)."""
        
    def _normalize_path(self, file_path: str) -> str:
        """Use the central normalize_path function."""
```

### Dependencies:
- **Imports:** `sqlite3`, `os`, `datetime`, `Path`, `normalize_path`, `logger_factory`
- **Runtime dependency:** Connection provider from DatabaseManager

---

## 3. hash_store.py (~150 lines)

**Purpose:** file_hashes table operations

### Methods to Move:
- `store_hash(file_path, hash_value, algorithm)` (lines 737-784)
- `get_hash(file_path, algorithm)` (lines 786-810)
- `has_hash(file_path, algorithm)` (lines 812-829)
- `get_files_with_hash_batch(file_paths, algorithm)` (lines 831-870)

### New Interface:
```python
class HashStore:
    """Manages file_hashes table operations."""
    
    def __init__(self, get_connection_func, path_store: PathStore):
        """Initialize with connection provider and path store."""
        self._get_connection = get_connection_func
        self._path_store = path_store
        
    def store_hash(self, file_path: str, hash_value: str, algorithm: str = "CRC32") -> bool:
        """Store file hash."""
        
    def get_hash(self, file_path: str, algorithm: str = "CRC32") -> str | None:
        """Retrieve file hash."""
        
    def has_hash(self, file_path: str, algorithm: str = "CRC32") -> bool:
        """Check if hash exists for a file."""
        
    def get_files_with_hash_batch(
        self, file_paths: list[str], algorithm: str = "CRC32"
    ) -> list[str]:
        """Get all files from the list that have a hash stored."""
```

### Dependencies:
- **Imports:** `sqlite3`, `os`, `logger_factory`
- **Runtime dependency:** PathStore (for get_or_create_path_id, get_path_id)

---

## 4. metadata_store.py (~550 lines)

**Purpose:** All metadata operations (JSON metadata + structured metadata + categories/fields)

### Methods to Move:

#### JSON Metadata (file_metadata table):
- `store_metadata(file_path, metadata, is_extended, is_modified)` (lines 482-524)
- `batch_store_metadata(metadata_items)` (lines 526-589)
- `get_metadata(file_path)` (lines 591-627)
- `get_metadata_batch(file_paths)` (lines 629-696)
- `has_metadata(file_path, metadata_type)` (lines 698-735)

#### Categories & Fields (metadata_categories/metadata_fields tables):
- `create_metadata_category(category_name, display_name, description, sort_order)` (lines 872-899)
- `get_metadata_categories()` (lines 901-916)
- `create_metadata_field(field_key, field_name, category_id, ...)` (lines 918-955)
- `get_metadata_fields(category_id)` (lines 957-991)
- `get_metadata_field_by_key(field_key)` (lines 993-1013)

#### Structured Metadata (file_metadata_structured table):
- `store_structured_metadata(file_path, field_key, field_value)` (lines 1015-1047)
- `batch_store_structured_metadata(file_path, field_data)` (lines 1049-1110)
- `get_structured_metadata(file_path)` (lines 1112-1152)

### New Interface:
```python
class MetadataStore:
    """Manages all metadata operations (JSON + structured + schema)."""
    
    def __init__(self, get_connection_func, path_store: PathStore):
        """Initialize with connection provider and path store."""
        self._get_connection = get_connection_func
        self._path_store = path_store
    
    # JSON Metadata Operations
    def store_metadata(
        self, file_path: str, metadata: dict[str, Any],
        is_extended: bool = False, is_modified: bool = False
    ) -> bool:
        """Store metadata for a file."""
        
    def batch_store_metadata(
        self, metadata_items: list[tuple[str, dict[str, Any], bool, bool]]
    ) -> int:
        """Store metadata for multiple files in batch."""
        
    def get_metadata(self, file_path: str) -> dict[str, Any] | None:
        """Retrieve metadata for a file."""
        
    def get_metadata_batch(
        self, file_paths: list[str]
    ) -> dict[str, dict[str, Any] | None]:
        """Retrieve metadata for multiple files in batch."""
        
    def has_metadata(self, file_path: str, metadata_type: str | None = None) -> bool:
        """Check if file has metadata stored."""
    
    # Metadata Categories & Fields
    def create_metadata_category(
        self, category_name: str, display_name: str,
        description: str | None = None, sort_order: int = 0
    ) -> int | None:
        """Create a new metadata category."""
        
    def get_metadata_categories(self) -> list[dict[str, Any]]:
        """Get all metadata categories ordered by sort_order."""
        
    def create_metadata_field(
        self, field_key: str, field_name: str, category_id: int,
        data_type: str = "text", is_editable: bool = False,
        is_searchable: bool = True, display_format: str | None = None,
        sort_order: int = 0
    ) -> int | None:
        """Create a new metadata field."""
        
    def get_metadata_fields(self, category_id: int | None = None) -> list[dict[str, Any]]:
        """Get metadata fields, optionally filtered by category."""
        
    def get_metadata_field_by_key(self, field_key: str) -> dict[str, Any] | None:
        """Get a metadata field by its key."""
    
    # Structured Metadata Operations
    def store_structured_metadata(
        self, file_path: str, field_key: str, field_value: str
    ) -> bool:
        """Store structured metadata for a file."""
        
    def batch_store_structured_metadata(
        self, file_path: str, field_data: list[tuple[str, str]]
    ) -> int:
        """Store multiple structured metadata fields in batch."""
        
    def get_structured_metadata(self, file_path: str) -> dict[str, Any]:
        """Get structured metadata for a file."""
```

### Dependencies:
- **Imports:** `sqlite3`, `json`, `os`, `Any`, `logger_factory`
- **Runtime dependency:** PathStore (for get_or_create_path_id, get_path_id)

---

## 5. backup_store.py (~150 lines)

**Purpose:** file_rename_history table operations (currently no methods exist, but table exists)

### Current State:
- Table `file_rename_history` exists in schema (lines 226-238)
- **NO methods currently implemented** in database_manager.py
- Index created: `idx_file_rename_history_*` (lines 389-391)

### Proposed Interface (for future implementation):
```python
class BackupStore:
    """Manages file_rename_history table operations."""
    
    def __init__(self, get_connection_func, path_store: PathStore):
        """Initialize with connection provider and path store."""
        self._get_connection = get_connection_func
        self._path_store = path_store
        
    def store_rename_operation(
        self, operation_id: str, old_path: str, new_path: str,
        operation_type: str = "rename", modules_data: str | None = None,
        post_transform_data: str | None = None
    ) -> bool:
        """Store a rename operation in history."""
        
    def get_rename_history(
        self, file_path: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get rename history for a file."""
        
    def get_operation_files(self, operation_id: str) -> list[dict[str, Any]]:
        """Get all files involved in a rename operation."""
        
    def clear_old_history(self, days: int = 90) -> int:
        """Clear rename history older than N days."""
```

### Dependencies:
- **Imports:** `sqlite3`, `json`, `datetime`, `Any`, `logger_factory`
- **Runtime dependency:** PathStore (for get_or_create_path_id, get_path_id)

### Note:
Since no methods currently exist, this file will be mostly scaffolding for future implementation. The table is already in the schema and ready to use.

---

## 6. database_manager.py (~400 lines - Main Orchestrator)

**Purpose:** High-level coordination, connection management, public API facade

### Methods to Keep:
- `__init__(db_path)` (lines 51-87) — initialization + DEBUG_RESET_DATABASE logic
- `_get_connection()` (lines 89-104) — connection factory with pragmas
- `transaction()` (lines 106-121) — transaction context manager
- `_initialize_database()` (lines 123-168) — delegates to migrations
- `get_database_stats()` (lines 1417-1448) — utility method
- `set_color_tag(file_path, color_hex)` (lines 1450-1488) — delegates to path_store
- `get_color_tag(file_path)` (lines 1490-1521) — delegates to path_store
- `close()` (lines 1589-1592) — cleanup

### New Delegation Architecture:
```python
class DatabaseManager:
    """Enhanced database management with improved separation of concerns.
    
    Main orchestrator that delegates to specialized stores:
    - PathStore: file_paths table operations
    - MetadataStore: all metadata operations
    - HashStore: file_hashes table operations
    - BackupStore: file_rename_history table operations
    """
    
    SCHEMA_VERSION = 4
    
    def __init__(self, db_path: str | None = None):
        """Initialize database manager."""
        # Existing initialization logic
        # Create store instances
        self._path_store = PathStore(self._get_connection)
        self._metadata_store = MetadataStore(self._get_connection, self._path_store)
        self._hash_store = HashStore(self._get_connection, self._path_store)
        self._backup_store = BackupStore(self._get_connection, self._path_store)
    
    # Connection management (keep)
    def _get_connection(self): ...
    def transaction(self): ...
    def _initialize_database(self): ...
    def close(self): ...
    
    # Delegation to PathStore
    def get_or_create_path_id(self, file_path: str) -> int:
        return self._path_store.get_or_create_path_id(file_path)
    
    def get_path_id(self, file_path: str) -> int | None:
        return self._path_store.get_path_id(file_path)
    
    def update_file_path(self, old_path: str, new_path: str) -> bool:
        return self._path_store.update_file_path(old_path, new_path)
    
    # Delegation to MetadataStore (JSON metadata)
    def store_metadata(self, file_path: str, metadata: dict[str, Any],
                      is_extended: bool = False, is_modified: bool = False) -> bool:
        return self._metadata_store.store_metadata(file_path, metadata, is_extended, is_modified)
    
    def batch_store_metadata(self, metadata_items: list[tuple[str, dict[str, Any], bool, bool]]) -> int:
        return self._metadata_store.batch_store_metadata(metadata_items)
    
    def get_metadata(self, file_path: str) -> dict[str, Any] | None:
        return self._metadata_store.get_metadata(file_path)
    
    def get_metadata_batch(self, file_paths: list[str]) -> dict[str, dict[str, Any] | None]:
        return self._metadata_store.get_metadata_batch(file_paths)
    
    def has_metadata(self, file_path: str, metadata_type: str | None = None) -> bool:
        return self._metadata_store.has_metadata(file_path, metadata_type)
    
    # Delegation to MetadataStore (categories & fields)
    def create_metadata_category(self, category_name: str, display_name: str,
                                 description: str | None = None, sort_order: int = 0) -> int | None:
        return self._metadata_store.create_metadata_category(category_name, display_name, description, sort_order)
    
    def get_metadata_categories(self) -> list[dict[str, Any]]:
        return self._metadata_store.get_metadata_categories()
    
    def create_metadata_field(self, field_key: str, field_name: str, category_id: int,
                             data_type: str = "text", is_editable: bool = False,
                             is_searchable: bool = True, display_format: str | None = None,
                             sort_order: int = 0) -> int | None:
        return self._metadata_store.create_metadata_field(
            field_key, field_name, category_id, data_type,
            is_editable, is_searchable, display_format, sort_order
        )
    
    def get_metadata_fields(self, category_id: int | None = None) -> list[dict[str, Any]]:
        return self._metadata_store.get_metadata_fields(category_id)
    
    def get_metadata_field_by_key(self, field_key: str) -> dict[str, Any] | None:
        return self._metadata_store.get_metadata_field_by_key(field_key)
    
    # Delegation to MetadataStore (structured metadata)
    def store_structured_metadata(self, file_path: str, field_key: str, field_value: str) -> bool:
        return self._metadata_store.store_structured_metadata(file_path, field_key, field_value)
    
    def batch_store_structured_metadata(self, file_path: str, field_data: list[tuple[str, str]]) -> int:
        return self._metadata_store.batch_store_structured_metadata(file_path, field_data)
    
    def get_structured_metadata(self, file_path: str) -> dict[str, Any]:
        return self._metadata_store.get_structured_metadata(file_path)
    
    def initialize_default_metadata_schema(self) -> bool:
        """Delegates to migrations module."""
        with self._get_connection() as conn:
            return DatabaseMigrations.initialize_default_metadata_schema(conn)
    
    # Delegation to HashStore
    def store_hash(self, file_path: str, hash_value: str, algorithm: str = "CRC32") -> bool:
        return self._hash_store.store_hash(file_path, hash_value, algorithm)
    
    def get_hash(self, file_path: str, algorithm: str = "CRC32") -> str | None:
        return self._hash_store.get_hash(file_path, algorithm)
    
    def has_hash(self, file_path: str, algorithm: str = "CRC32") -> bool:
        return self._hash_store.has_hash(file_path, algorithm)
    
    def get_files_with_hash_batch(self, file_paths: list[str], algorithm: str = "CRC32") -> list[str]:
        return self._hash_store.get_files_with_hash_batch(file_paths, algorithm)
    
    # Color tag operations (keep in manager - uses path_store internally)
    def set_color_tag(self, file_path: str, color_hex: str) -> bool:
        """Set color tag for a file (delegates to path_store for path_id)."""
        # Existing implementation with validation logic
        
    def get_color_tag(self, file_path: str) -> str:
        """Get color tag for a file (delegates to path_store for path_id)."""
        # Existing implementation
    
    # Utility methods
    def get_database_stats(self) -> dict[str, int]:
        """Get database statistics."""
        # Keep existing implementation
```

### Dependencies:
- **Imports:** `sqlite3`, `os`, `Path`, `contextlib`, `contextmanager`, `normalize_path`, `logger_factory`, `AppPaths`, `DEBUG_RESET_DATABASE`
- **Internal imports:**
  ```python
  from oncutf.core.database.migrations import DatabaseMigrations
  from oncutf.core.database.path_store import PathStore
  from oncutf.core.database.metadata_store import MetadataStore
  from oncutf.core.database.hash_store import HashStore
  from oncutf.core.database.backup_store import BackupStore
  ```

---

## 7. __init__.py

**Purpose:** Re-export DatabaseManager for backward compatibility

```python
"""Database management subsystem.

Architecture:
- DatabaseManager: Main orchestrator
- PathStore: file_paths table operations
- MetadataStore: All metadata operations
- HashStore: file_hashes table operations
- BackupStore: Rename history operations
- DatabaseMigrations: Schema creation and migrations
"""

from oncutf.core.database.database_manager import (
    DatabaseManager,
    get_database_manager,
    initialize_database,
)

__all__ = [
    "DatabaseManager",
    "get_database_manager",
    "initialize_database",
]
```

---

## Dependency Graph

```
DatabaseManager (orchestrator)
    ├── _get_connection() ─┐
    │                      │
    ├─> DatabaseMigrations (schema, no runtime deps)
    │                      │
    ├─> PathStore <────────┤
    │       │              │
    ├─> MetadataStore ─────┤
    │       └─> PathStore  │
    │                      │
    ├─> HashStore ─────────┤
    │       └─> PathStore  │
    │                      │
    └─> BackupStore ───────┘
            └─> PathStore
```

**Key Points:**
- All stores receive `_get_connection` callable from DatabaseManager
- PathStore has no dependencies (only needs connection)
- All other stores depend on PathStore for path_id resolution
- DatabaseMigrations is stateless (pure functions)

---

## Migration Strategy

### Phase 1: Extract Migrations (Low Risk)
1. Create `migrations.py` with `DatabaseMigrations` class
2. Update `database_manager._initialize_database()` to delegate
3. Run tests

### Phase 2: Extract PathStore (Low Risk)
1. Create `path_store.py` with `PathStore` class
2. Update DatabaseManager to instantiate and delegate
3. Keep delegator methods for backward compatibility
4. Run tests

### Phase 3: Extract HashStore (Low Risk)
1. Create `hash_store.py` with `HashStore` class
2. Update DatabaseManager to instantiate and delegate
3. Run tests

### Phase 4: Extract MetadataStore (Medium Risk - largest module)
1. Create `metadata_store.py` with `MetadataStore` class
2. Move JSON metadata methods
3. Move category/field methods
4. Move structured metadata methods
5. Update DatabaseManager to instantiate and delegate
6. Run tests

### Phase 5: Create BackupStore Scaffolding (Low Risk)
1. Create `backup_store.py` with empty/placeholder methods
2. Update DatabaseManager to instantiate (no delegation yet)
3. Document TODOs for future implementation

### Phase 6: Update __init__.py and Documentation
1. Update `__init__.py` with re-exports
2. Update docstrings
3. Run full test suite
4. Run quality gates: `ruff check .` → `mypy .` → `pytest`

---

## Testing Strategy

### Unit Tests (New)
- `tests/unit/core/database/test_migrations.py`
- `tests/unit/core/database/test_path_store.py`
- `tests/unit/core/database/test_metadata_store.py`
- `tests/unit/core/database/test_hash_store.py`
- `tests/unit/core/database/test_backup_store.py`

### Integration Tests (Existing)
- Keep existing `tests/integration/core/test_database_manager.py`
- Should pass without modification (backward compatibility)

### Coverage Requirements
- Each new module: ≥80% coverage
- DatabaseManager: ≥90% coverage (delegator layer)

---

## Backward Compatibility

**CRITICAL:** All existing code using DatabaseManager MUST work without changes.

### Guaranteed:
- All public methods remain in DatabaseManager (as delegators)
- Method signatures unchanged
- Return types unchanged
- Error handling behavior unchanged
- Global instance management unchanged (`get_database_manager()`)

### Breaking Changes:
- **NONE** — This is a pure internal refactoring

---

## Benefits

### Maintainability
- **Single Responsibility:** Each store has one clear purpose
- **Easier Testing:** Smaller, focused test files
- **Better Organization:** Logical grouping by database table

### Performance
- **No impact:** Delegation is minimal overhead
- **Connection sharing:** All stores use same connection pool
- **Transaction support:** Stores operate within DatabaseManager transactions

### Extensibility
- **Easy to add features:** BackupStore ready for rename history implementation
- **Future stores:** Can add ThumbnailStore, TagStore, etc.
- **Independent evolution:** Each store can be refactored independently

---

## Risks & Mitigations

### Risk 1: Circular dependencies
**Mitigation:** PathStore has no dependencies; other stores only depend on PathStore

### Risk 2: Transaction scope issues
**Mitigation:** All stores use `_get_connection()` from manager; transactions managed at manager level

### Risk 3: Breaking existing tests
**Mitigation:** Keep all public methods as delegators; run full test suite after each phase

### Risk 4: Performance regression
**Mitigation:** Delegation is just one method call; profile if needed

---

## Success Criteria

- [ ] DatabaseManager reduced from 1615 to ~400 lines
- [ ] All 5 new modules created and tested
- [ ] All existing tests pass without modification
- [ ] `ruff check .` passes (no new warnings)
- [ ] `mypy .` passes (no new errors)
- [ ] `pytest` passes (all 592+ tests)
- [ ] No breaking changes to public API
- [ ] Code coverage maintained or improved

---

## Timeline Estimate

- **Phase 1 (Migrations):** 2 hours
- **Phase 2 (PathStore):** 2 hours
- **Phase 3 (HashStore):** 2 hours
- **Phase 4 (MetadataStore):** 4 hours (largest module)
- **Phase 5 (BackupStore):** 1 hour
- **Phase 6 (Finalization):** 2 hours

**Total:** ~13 hours (spread over 2-3 days with testing breaks)

---

## Next Steps

1. **User approval** of this plan
2. Execute Phase 1 (Migrations)
3. Run quality gates
4. Continue with subsequent phases
5. Final review and merge

