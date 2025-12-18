# Phase 6: Domain Layer Purification — Execution Plan

> **Status**: IN PROGRESS  
> **Created**: December 18, 2025  
> **Branch**: `phase6-refactoring`  
> **Author**: Michael Economou

---

## Overview

**Phase 6** focuses on creating proper service protocols/interfaces for dependency injection
and ensuring the domain layer remains Qt-free. This enables better testability and
cleaner separation of concerns.

### Current State Analysis

After audit, the following findings:

| Layer | Qt-Free Status | Notes |
|-------|----------------|-------|
| `oncutf/modules/` | ✅ Clean | All rename modules are pure Python |
| `oncutf/domain/` | ✅ Clean | MetadataExtractor is Qt-free |
| `oncutf/core/` | ⚠️ Mixed | Many managers depend on PyQt5 signals |
| `oncutf/services/` | ❌ Missing | No services layer exists yet |

### Goals

1. Create `oncutf/services/` layer with proper interfaces
2. Define service protocols for dependency injection
3. Ensure all business logic in domain is testable without Qt
4. Create adapters from Qt-based managers to service protocols

---

## Execution Rules

1. **One responsibility per step** - never mix concerns
2. **Test → Lint → Commit** after every sub-step
3. **App must be runnable** at every checkpoint
4. **No optimization** - correctness over elegance

---

## Step 6.1: Create Services Package Structure

**Goal**: Create the services layer directory with proper structure.

**Files/Folders to Create**:
```
oncutf/services/
oncutf/services/__init__.py
oncutf/services/interfaces.py
```

**Allowed**:
- Creating directories
- Creating files with docstrings

**Commit Message**: `chore: create services package structure`

**Definition of Done**:
- [ ] Directory created
- [ ] `__init__.py` with module docstring
- [ ] `interfaces.py` placeholder created
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

## Step 6.2: Define Service Protocols

**Goal**: Define Protocol classes for all external services.

**File**: `oncutf/services/interfaces.py`

**Protocols to Define**:

```python
from typing import Protocol, Any
from pathlib import Path

class MetadataServiceProtocol(Protocol):
    """Protocol for metadata extraction services."""
    def load_metadata(self, path: Path) -> dict[str, Any]: ...
    def load_metadata_batch(self, paths: list[Path]) -> dict[Path, dict[str, Any]]: ...

class HashServiceProtocol(Protocol):
    """Protocol for file hashing services."""
    def compute_hash(self, path: Path, algorithm: str = "crc32") -> str: ...
    def compute_hashes_batch(self, paths: list[Path], algorithm: str = "crc32") -> dict[Path, str]: ...

class FilesystemServiceProtocol(Protocol):
    """Protocol for filesystem operations."""
    def rename_file(self, source: Path, target: Path) -> bool: ...
    def file_exists(self, path: Path) -> bool: ...
    def get_file_info(self, path: Path) -> dict[str, Any]: ...

class DatabaseServiceProtocol(Protocol):
    """Protocol for database operations."""
    def store_rename(self, source: str, target: str, timestamp: float) -> None: ...
    def get_rename_history(self, path: str) -> list[dict[str, Any]]: ...

class ConfigServiceProtocol(Protocol):
    """Protocol for configuration access."""
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
```

**Tests to Add**: `tests/unit/services/test_interfaces.py`

**Commit Message**: `feat: add service protocols for dependency injection`

**Definition of Done**:
- [ ] All protocols defined
- [ ] Protocol tests pass (structural subtyping)
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

## Step 6.3: Implement ExifTool Service

**Goal**: Create a concrete implementation of MetadataServiceProtocol.

**File**: `oncutf/services/exiftool_service.py`

**Implementation**:
- Wraps existing ExifTool functionality
- Implements MetadataServiceProtocol
- Pure Python (no Qt dependencies)

**Commit Message**: `feat: add ExifToolService implementing MetadataServiceProtocol`

**Definition of Done**:
- [ ] Service implementation complete
- [ ] Tests pass
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

## Step 6.4: Implement Hash Service

**Goal**: Create a concrete implementation of HashServiceProtocol.

**File**: `oncutf/services/hash_service.py`

**Implementation**:
- Uses existing hash computation logic
- Implements HashServiceProtocol
- Pure Python (no Qt dependencies)

**Commit Message**: `feat: add HashService implementing HashServiceProtocol`

**Definition of Done**:
- [ ] Service implementation complete
- [ ] Tests pass
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

## Step 6.5: Implement Filesystem Service

**Goal**: Create a concrete implementation of FilesystemServiceProtocol.

**File**: `oncutf/services/filesystem_service.py`

**Implementation**:
- Abstracts filesystem operations
- Implements FilesystemServiceProtocol
- Pure Python (no Qt dependencies)

**Commit Message**: `feat: add FilesystemService implementing FilesystemServiceProtocol`

**Definition of Done**:
- [ ] Service implementation complete
- [ ] Tests pass
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

## Step 6.6: Create Service Registry

**Goal**: Create a simple service registry for dependency injection.

**File**: `oncutf/services/registry.py`

**Implementation**:
```python
class ServiceRegistry:
    """Simple service locator for dependency injection."""
    
    _instance: ClassVar["ServiceRegistry | None"] = None
    
    def __init__(self) -> None:
        self._services: dict[type, Any] = {}
    
    @classmethod
    def instance(cls) -> "ServiceRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register(self, protocol: type, implementation: Any) -> None: ...
    def get(self, protocol: type) -> Any: ...
```

**Commit Message**: `feat: add ServiceRegistry for dependency injection`

**Definition of Done**:
- [ ] Registry implementation complete
- [ ] Tests pass
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

## Step 6.7: Update Domain Layer to Use Protocols

**Goal**: Update MetadataExtractor to accept services via dependency injection.

**Changes**:
- Add optional service parameters to MetadataExtractor constructor
- Use protocol types for type hints
- Maintain backwards compatibility

**Commit Message**: `refactor: update MetadataExtractor to use service protocols`

**Definition of Done**:
- [ ] MetadataExtractor uses protocols
- [ ] All existing tests pass
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

## Step 6.8: Export Services in __init__.py

**Goal**: Clean exports from services package.

**File**: `oncutf/services/__init__.py`

**Exports**:
- All protocol types
- All concrete service implementations
- ServiceRegistry

**Commit Message**: `chore: export services package public API`

**Definition of Done**:
- [ ] All services exported properly
- [ ] Import tests pass
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check .` passes

---

## Step 6.9: Final Verification

**Goal**: Complete verification of Phase 6.

**Checks**:
```bash
pytest tests/ -v
ruff check .
python main.py  # Manual verification
```

**Manual Tests**:
- [ ] App launches successfully
- [ ] Load files works
- [ ] Preview rename works
- [ ] Metadata loading works

**Commit Message**: `docs: complete Phase 6 domain layer purification`

**Definition of Done**:
- [ ] All tests pass
- [ ] `ruff check .` clean
- [ ] App works correctly
- [ ] PHASE6_COMPLETE.md created

---

## Summary

| Step | Description | Risk |
|------|-------------|------|
| 6.1 | Create services package | Low |
| 6.2 | Define service protocols | Low |
| 6.3 | Implement ExifTool service | Medium |
| 6.4 | Implement Hash service | Low |
| 6.5 | Implement Filesystem service | Low |
| 6.6 | Create service registry | Low |
| 6.7 | Update domain layer | Medium |
| 6.8 | Export services API | Low |
| 6.9 | Final verification | Low |

---

*Document version: 1.0*  
*Created: December 18, 2025*
