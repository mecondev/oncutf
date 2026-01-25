# ADR 003: FileRepository Pattern for Breaking Cycles

**Status:** Accepted  
**Date:** 2026-01-25  
**Author:** Michael Economou  
**Phase:** Phase D (Breaking Circular Dependencies)

---

## Context

During Phase C (Architecture Migration), we discovered a circular dependency cycle:

```
oncutf/infra/db/database_manager.py
    ↓ imports
oncutf/domain/models/file_entry.py
    ↓ imports
oncutf/infra/cache/advanced_cache_manager.py
    ↓ imports
oncutf/infra/db/database_manager.py  ← CYCLE!
```

**Root Cause:**
- `DatabaseManager` (infrastructure) had methods that returned domain models (`FileEntry`)
- Domain models had no knowledge of infrastructure (correct)
- `AdvancedCacheManager` needed both database access and domain models
- No clear boundary between data access and domain logic

**Symptoms:**
1. Import errors in some execution paths
2. Difficult to test database code without full app context
3. Unclear separation of concerns
4. Mypy struggled with circular imports (ignore_errors=true workarounds)

---

## Decision

**Introduce Repository Pattern with Protocol-Based Abstraction:**

Create `FileRepository` as a protocol (interface) that:
- Lives in `oncutf/app/ports/` (domain boundary)
- Defines data access operations (no implementation)
- Used by domain/application layers
- Implemented by infrastructure layer

**Structure:**
```
oncutf/
    app/
        ports/
            file_repository.py       # Protocol (interface)
    
    domain/
        models/
            file_entry.py             # Pure domain model
    
    infra/
        repositories/
            sqlite_file_repository.py # Protocol implementation
        db/
            database_manager.py       # Low-level DB operations
```

**Key Pattern:**
```python
# app/ports/file_repository.py (Protocol)
from typing import Protocol
from oncutf.domain.models import FileEntry

class FileRepository(Protocol):
    def get_by_path(self, path: str) -> FileEntry | None: ...
    def save(self, file: FileEntry) -> None: ...
    def get_all(self) -> list[FileEntry]: ...

# infra/repositories/sqlite_file_repository.py (Implementation)
class SQLiteFileRepository:
    def __init__(self, db_manager: DatabaseManager):
        self._db = db_manager
    
    def get_by_path(self, path: str) -> FileEntry | None:
        row = self._db.fetch_one("SELECT * FROM files WHERE path = ?", path)
        return FileEntry.from_db_row(row) if row else None

# domain/services/file_service.py (Usage)
class FileService:
    def __init__(self, repo: FileRepository):  # Protocol, not concrete
        self._repo = repo
    
    def load_files(self) -> list[FileEntry]:
        return self._repo.get_all()  # No dependency on SQLite!
```

---

## Consequences

### Positive

1. **Cycle Broken**
   - Database layer no longer imports domain models directly
   - Domain models never import infrastructure
   - Repository interface bridges the gap
   - Mypy no longer needs ignore_errors for circular imports

2. **Improved Testability**
   ```python
   # Mock repository for tests (no SQLite needed!)
   class MockFileRepository:
       def get_all(self) -> list[FileEntry]:
           return [FileEntry(...), FileEntry(...)]
   
   service = FileService(MockFileRepository())  # Easy!
   ```

3. **Clear Boundaries**
   - `app/ports/` = Interfaces (what operations exist)
   - `domain/` = Business logic (no dependencies)
   - `infra/` = Implementation details (can swap SQLite → PostgreSQL)

4. **Type Safety**
   - Protocol ensures implementations conform to interface
   - Mypy catches missing methods at compile time
   - No runtime isinstance() checks needed

5. **Flexibility**
   - Easy to add `InMemoryFileRepository` for testing
   - Easy to add `RedisFileRepository` for caching
   - Business logic unchanged (depends on protocol)

### Negative

1. **Indirection**
   - One more abstraction layer
   - Slightly more code to maintain
   - Learning curve for repository pattern

2. **Boilerplate**
   - Protocol definition + implementation = 2 files
   - For simple CRUD, feels like over-engineering
   - Must maintain protocol in sync with implementations

3. **Performance Overhead**
   - Protocol calls have tiny overhead (negligible in practice)
   - Additional object allocations for repository instances

### Neutral

1. **Alternative Rejected: Keep Circular Import**
   ```python
   # Use import guards
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from oncutf.domain.models import FileEntry
   
   # Problem: Still tightly coupled, just hidden
   # Mypy still struggles, tests still hard
   ```

2. **Alternative Rejected: Merge Database and Domain**
   ```python
   # Put everything in one module
   class FileEntry:
       @staticmethod
       def load_from_db(db: DatabaseManager):
           ...
   
   # Problem: Domain models now know about SQLite
   # Can't test domain logic without database
   ```

---

## Implementation

**Phase D (Commits: b91e34a8, etc.):**

1. **Created Protocol:**
   - `oncutf/app/ports/file_repository.py`
   - Defined interface with 8 core operations

2. **Created Implementation:**
   - `oncutf/infra/repositories/sqlite_file_repository.py`
   - Delegates to `DatabaseManager` for SQL operations
   - Converts DB rows to domain models

3. **Updated Services:**
   - `FileLoadController` now depends on `FileRepository` protocol
   - `AdvancedCacheManager` uses repository interface
   - No direct database imports in application layer

4. **Verified Cycle Broken:**
   ```bash
   # Before: Circular import error
   python -c "from oncutf.infra.db import DatabaseManager" 
   # ImportError: cannot import name 'FileEntry' from partially initialized module
   
   # After: Clean import
   python -c "from oncutf.infra.db import DatabaseManager"
   # Success!
   ```

---

## Verification

**Dependency Flow (Correct Direction):**
```
Domain Models (oncutf/domain/)
       ↑
    Ports (oncutf/app/ports/) ← Protocols/Interfaces
       ↑
Infrastructure (oncutf/infra/) ← Implementations
```

**No More Cycles:**
```bash
# Check import graph
python -m pydeps oncutf --max-bacon=3 --cluster
# No cycles detected in core architecture
```

**Test Improvement:**
```python
# Before: Needed full database setup
db = DatabaseManager(":memory:")
db.create_tables()
db.insert_test_data()
service = FileService(db)  # Tightly coupled

# After: Simple mock
repo = MockFileRepository([file1, file2])
service = FileService(repo)  # Testable!
assert service.load_files() == [file1, file2]
```

---

## Related

- **Supersedes:** Direct DatabaseManager usage in domain services
- **Complements:** [ADR 002: Application Services Facade](002-app-services-facade.md)
- **See also:**
  - [Hexagonal Architecture Pattern](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software))
  - [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- **References:**
  - Phase D commits: b91e34a8, c74d2f19, etc.
  - [Phase D summary](../260121_summary.md#phase-d)
