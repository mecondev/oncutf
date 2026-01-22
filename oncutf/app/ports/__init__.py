"""Ports - Protocol interfaces for infrastructure dependencies.

Define interfaces that infrastructure layer implements:
- MetadataProvider
- HashProvider
- Filesystem
- CacheStore
- DatabaseRepository

Author: Michael Economou
Date: 2026-01-22
"""

from oncutf.app.ports.metadata import CacheStore, MetadataProvider, MetadataWriter
from oncutf.app.ports.user_interaction import ProgressReporter, StatusReporter, UserDialogPort

__all__ = [
    "CacheStore",
    "MetadataProvider",
    "MetadataWriter",
    "ProgressReporter",
    "StatusReporter",
    "UserDialogPort",
]
