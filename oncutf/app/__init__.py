"""Application layer - workflow orchestration without Qt dependencies.

This layer contains:
- Use cases (application workflows)
- Ports (interfaces/Protocols for infrastructure)
- Application events and callbacks

Allowed imports:
- domain/ modules
- Ports (Protocols)
- Standard library (typing, dataclasses, etc.)

Forbidden imports:
- PyQt5/Qt imports
- Direct IO operations (use ports instead)
- ui/ modules

Author: Michael Economou
Date: 2026-01-22
"""
