"""Type aliases for common types used across the oncutf codebase.

This module centralizes type definitions to improve type safety and
consistency throughout the application, especially for cross-module
type consistency.

Author: Michael Economou
Date: December 19, 2025
"""

from typing import Any, Protocol, runtime_checkable

# =============================================================================
# Metadata Types
# =============================================================================

# A single file's metadata - mapping of field name to value
MetadataDict = dict[str, Any]

# The metadata cache - mapping of normalized file path to metadata dict
MetadataCache = dict[str, MetadataDict]


# =============================================================================
# Module Data Types
# =============================================================================

# Rename module configuration data
ModuleData = dict[str, Any]

# List of rename modules
ModulesDataList = list[ModuleData]


# =============================================================================
# Preview Types
# =============================================================================

# Name pair for preview: (original_name, new_name)
NamePair = tuple[str, str]

# List of name pairs for batch preview
NamePairsList = list[NamePair]


# =============================================================================
# File Types
# =============================================================================

# File path (normalized)
FilePath = str

# List of file paths
FilePathList = list[FilePath]


# =============================================================================
# Manager Protocol
# =============================================================================


@runtime_checkable
class ManagerProtocol(Protocol):
    """Protocol for managers that can be registered in ApplicationContext.

    Managers should implement cleanup for proper resource management.
    """

    def cleanup(self) -> None:
        """Clean up manager resources."""
        ...
