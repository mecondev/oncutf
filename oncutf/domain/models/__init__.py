"""Domain models - pure data entities without UI, infra, or orchestration deps.

These value objects/entities form the core data vocabulary of the application:
FileItem, MetadataEntry, FileGroup, CounterScope, and the validation result
types. They depend only on the standard library (entities may use stdlib
``logging``); Qt-bound model classes live in ``oncutf.ui.models``.

Author: Michael Economou
Date: 2026-05-30
"""

from oncutf.domain.models.counter_scope import CounterScope
from oncutf.domain.models.file_group import FileGroup
from oncutf.domain.models.file_item import FileItem
from oncutf.domain.models.metadata_entry import MetadataEntry
from oncutf.domain.models.validation_result import (
    ValidationIssue,
    ValidationIssueType,
    ValidationResult,
)

__all__ = [
    "CounterScope",
    "FileGroup",
    "FileItem",
    "MetadataEntry",
    "ValidationIssue",
    "ValidationIssueType",
    "ValidationResult",
]
