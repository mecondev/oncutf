"""Domain-level port definitions (protocols).

This package contains Protocol definitions that can be imported by any layer.
Protocols are pure abstractions with no implementation dependencies.

Architecture note:
- Domain protocols can be imported by: domain, app, infra, core, boot, ui
- This breaks the infra→app dependency by providing shared interfaces

Author: Michael Economou
Date: 2026-01-30
"""

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
