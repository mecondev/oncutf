"""
Module: oncutf.controllers

Author: Michael Economou
Date: 2025-12-15

Controllers package for separating UI from business logic.

Controllers act as an orchestration layer between the UI (MainWindow) and
domain services (core managers). They handle:
- User action coordination
- Multi-service orchestration
- UI-agnostic business workflows

This separation allows:
- Testability: Controllers can be tested without Qt/GUI
- Maintainability: Business logic separate from UI concerns
- Reusability: Controllers can be used by different UI implementations
"""

from oncutf.controllers.file_load_controller import FileLoadController

__all__ = ["FileLoadController"]
