"""Type aliases for common types used across the oncutf codebase.

This module centralizes type definitions to improve type safety and
consistency throughout the application, especially for cross-module
type consistency.

Author: Michael Economou
Date: December 19, 2025
"""

from typing import Any, Protocol, TypedDict, runtime_checkable

# =============================================================================
# Metadata Types
# =============================================================================

# A single file's metadata - mapping of field name to value
MetadataDict = dict[str, Any]

# The metadata cache - mapping of normalized file path to metadata dict
MetadataCacheMap = dict[str, MetadataDict]
MetadataCache = MetadataCacheMap  # Alias for backward compatibility


class ExifMetadata(TypedDict, total=False):
    """TypedDict for common EXIF metadata fields from ExifTool.

    All fields are optional (total=False) as not all files have all metadata.
    This provides IDE autocomplete for commonly accessed fields.
    """

    # File information
    SourceFile: str
    FileName: str
    Directory: str
    FileSize: str
    FileModifyDate: str
    FileAccessDate: str
    FileType: str
    FileTypeExtension: str
    MIMEType: str

    # Image dimensions
    ImageWidth: int
    ImageHeight: int
    ImageSize: str

    # EXIF dates
    DateTimeOriginal: str
    CreateDate: str
    ModifyDate: str

    # Camera information
    Make: str
    Model: str
    LensModel: str
    FocalLength: str
    FNumber: str
    ExposureTime: str
    ISO: int

    # GPS data
    GPSLatitude: str
    GPSLongitude: str
    GPSAltitude: str

    # Orientation and rotation
    Orientation: str | int
    Rotation: int

    # Video specific
    Duration: str
    VideoFrameRate: float
    AudioChannels: int
    AudioSampleRate: int

    # IPTC/XMP
    Title: str
    Description: str
    Subject: list[str]
    Keywords: list[str]
    Creator: str
    Copyright: str
    Rating: int

    # Internal flags (added by oncutf)
    __extended__: bool
    __modified__: bool


@runtime_checkable
class MetadataCacheProtocol(Protocol):
    """Protocol for metadata cache providers (e.g. PersistentMetadataCache)."""

    def get(self, file_path: str) -> MetadataDict:
        """Get metadata for a file."""
        ...

    def set(self, file_path: str, metadata: MetadataDict, **kwargs: Any) -> None:
        """Store metadata for a file."""
        ...


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
