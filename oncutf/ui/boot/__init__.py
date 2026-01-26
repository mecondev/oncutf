"""Application bootstrap module.

This module provides application startup and initialization functionality including:
- BootstrapManager: Manages bootstrap state and progress
- BootstrapOrchestrator: Coordinates startup sequence
- BootstrapWorker: Background bootstrap tasks

Author: Michael Economou
Date: 2026-01-26 (Phase 2: Moved from core to ui layer)
"""

from __future__ import annotations

from oncutf.ui.boot.bootstrap_manager import BootstrapManager
from oncutf.ui.boot.bootstrap_orchestrator import BootstrapOrchestrator
from oncutf.ui.boot.bootstrap_worker import BootstrapWorker

# Backward compatibility aliases
InitializationManager = BootstrapManager
InitializationOrchestrator = BootstrapOrchestrator
InitializationWorker = BootstrapWorker

__all__ = [
    "BootstrapManager",
    "BootstrapOrchestrator",
    "BootstrapWorker",
    # Deprecated aliases
    "InitializationManager",
    "InitializationOrchestrator",
    "InitializationWorker",
]
