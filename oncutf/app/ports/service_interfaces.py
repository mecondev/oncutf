"""Service protocol definitions for oncutf application.

Author: Michael Economou
Date: December 18, 2025

This module re-exports Protocol classes from domain.ports for backward
compatibility. New code should import directly from oncutf.domain.ports.

DEPRECATED: Import from oncutf.domain.ports instead.
"""

from __future__ import annotations

# Re-export from domain.ports for backward compatibility
from oncutf.domain.ports.service_protocols import (
    FilesystemServiceProtocol,
    HashServiceProtocol,
    MetadataServiceProtocol,
)

__all__ = [
    "FilesystemServiceProtocol",
    "HashServiceProtocol",
    "MetadataServiceProtocol",
]
