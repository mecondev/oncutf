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

__all__ = [
    "create_app",
    "create_app_context",
    "register_infra_factories",
    "wire_service_registry",
]
