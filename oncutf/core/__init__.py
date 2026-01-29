"""Module: __init__.py.

Author: Michael Economou
Date: 2025-05-31

Core package providing application services, type definitions, and base classes.
"""

# Type aliases and TypedDicts for type safety
# Base worker classes for background operations
from oncutf.app.types import (
    ExifMetadata,
    FilePath,
    FilePathList,
    ManagerProtocol,
    MetadataCache,
    MetadataCacheMap,
    MetadataCacheProtocol,
    MetadataDict,
    ModuleData,
    ModulesDataList,
    NamePair,
    NamePairsList,
)
from oncutf.core.base_worker import (
    CancellableMixin,
    WorkerProtocol,
    WorkerResult,
)

__all__ = [
    # Worker base classes
    "CancellableMixin",
    # Type aliases
    "ExifMetadata",
    "FilePath",
    "FilePathList",
    "ManagerProtocol",
    "MetadataCache",
    "MetadataCacheMap",
    "MetadataCacheProtocol",
    "MetadataDict",
    "ModuleData",
    "ModulesDataList",
    "NamePair",
    "NamePairsList",
    "WorkerProtocol",
    "WorkerResult",
]
