"""Boot layer - Application composition root.

This package is the ONLY place where concrete infrastructure implementations
are instantiated and wired together. It serves as the "composition root"
following dependency injection patterns.

Architecture rules:
- boot CAN import: ui, app, domain, infra, core, utils, models, modules, config
- NO OTHER layer imports infra (except infra itself)
- UI gets a fully-configured application via boot.create_app()

This enforces clean architecture boundaries where:
- Domain has no dependencies
- App depends only on domain and ports (abstractions)
- Infra implements ports defined in app
- UI consumes app services, never infra directly
- Boot wires everything together

Author: Michael Economou
Date: 2026-01-30
"""

from __future__ import annotations

from oncutf.boot.app_factory import create_app, create_app_context
from oncutf.boot.infra_wiring import register_infra_factories, wire_service_registry
from oncutf.boot.lifecycle import (
    perform_emergency_cleanup,
    perform_graceful_shutdown,
    setup_lifecycle_handlers,
)
from oncutf.boot.startup_orchestrator import run_startup

__all__ = [
    "create_app",
    "create_app_context",
    "perform_emergency_cleanup",
    "perform_graceful_shutdown",
    "register_infra_factories",
    "run_startup",
    "setup_lifecycle_handlers",
    "wire_service_registry",
]
