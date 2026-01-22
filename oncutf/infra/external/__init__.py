"""External tool clients - ExifTool, FFmpeg, etc.

Author: Michael Economou
Date: 2026-01-22
"""

from oncutf.infra.external.exiftool_client import (
    ExifToolClient,
    get_exiftool_client,
    set_exiftool_client,
)

__all__ = [
    "ExifToolClient",
    "get_exiftool_client",
    "set_exiftool_client",
]
