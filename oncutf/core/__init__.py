"""Module: __init__.py

Author: Michael Economou
Date: 2025-05-31

Core package providing application services, type definitions, and base classes.
"""

# Type aliases and TypedDicts for type safety
# Base worker classes for background operations
from oncutf.core.base_worker import (
    CancellableMixin,
    WorkerProtocol,
    WorkerResult,
)
from oncutf.core.type_aliases import (
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

__all__ = [
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
    # Worker base classes
    "CancellableMixin",
    "WorkerProtocol",
    "WorkerResult",
]
