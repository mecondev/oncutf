"""
Module: counter_scope.py

Author: Michael Economou
Date: 2025-12-16

Counter scope enumeration for controlling counter reset behavior.
Part of Phase 2: State Management Fix.
"""

from enum import Enum


class CounterScope(str, Enum):
    """
    Defines the scope for counter reset behavior.

    Used to control when the counter resets to the start value:
    - GLOBAL: Single counter across all files (legacy behavior)
    - PER_FOLDER: Reset counter at folder boundaries (fixes multi-folder issue)
    - PER_EXTENSION: Reset counter at extension type changes
    - PER_FILEGROUP: Reset counter for each file group (future feature)
    """

    GLOBAL = "global"
    PER_FOLDER = "per_folder"
    PER_EXTENSION = "per_extension"
    PER_FILEGROUP = "per_filegroup"

    def __str__(self) -> str:
        """Return the string value of the scope."""
        return self.value

    @property
    def display_name(self) -> str:
        """Return a user-friendly display name."""
        return {
            CounterScope.GLOBAL: "Global (all files)",
            CounterScope.PER_FOLDER: "Per Folder",
            CounterScope.PER_EXTENSION: "Per Extension",
            CounterScope.PER_FILEGROUP: "Per File Group",
        }[self]

    @property
    def description(self) -> str:
        """Return a description of the scope behavior."""
        return {
            CounterScope.GLOBAL: "Single counter across all files",
            CounterScope.PER_FOLDER: "Reset counter at folder boundaries",
            CounterScope.PER_EXTENSION: "Reset counter for each extension type",
            CounterScope.PER_FILEGROUP: "Reset counter for each file group",
        }[self]
