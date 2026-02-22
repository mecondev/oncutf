"""Module: controller_adapters.py.

Author: Michael Economou
Date: 2026-01-30

Adapters that implement controller protocols using UI components.

This module provides concrete implementations of the protocols defined
in oncutf.controllers.protocols. These adapters bridge the gap between
UI-agnostic controllers and Qt-based UI components.

Usage:
    Adapters are instantiated during bootstrap and injected into controllers.
    This allows controllers to remain testable without Qt dependencies.
"""

from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ConflictResolverAdapter:
    """Adapter that implements ConflictResolverProtocol using the app context.

    Delegates to the ConflictResolutionPort registered in the Qt app context,
    keeping RenameController free of any direct Qt/UI imports.
    """

    def show_conflict(
        self,
        old_filename: str,
        new_filename: str,
        parent: Any = None,
    ) -> tuple[str, bool]:
        """Show conflict resolution dialog and return user decision.

        Args:
            old_filename: Current filename
            new_filename: Conflicting target filename
            parent: Optional parent window (resolved from context if None)

        Returns:
            Tuple of (action, apply_to_all).

        """
        try:
            from oncutf.ui.adapters.qt_app_context import QtAppContext

            context = QtAppContext.get_instance()
            if context and context.has_manager("conflict_resolution"):
                resolver = context.get_manager("conflict_resolution")
                return resolver.show_conflict(
                    old_filename=old_filename,
                    new_filename=new_filename,
                    parent=parent,
                )
        except Exception:
            logger.exception("[ConflictResolverAdapter] Error showing conflict dialog")
        return ("skip", False)


class ValidationDialogAdapter:
    """Adapter that implements ValidationDialogProtocol using Qt dialogs.

    This adapter wraps the ValidationIssuesDialog Qt dialog, providing
    a protocol-compliant interface that controllers can use without
    directly importing UI code.
    """

    def show_validation_issues(self, validation_result: Any) -> str:
        """Show validation issues dialog and get user decision.

        Args:
            validation_result: ValidationResult object with issues

        Returns:
            User decision: "skip", "cancel", or "refresh"

        """
        try:
            from oncutf.ui.dialogs.validation_issues_dialog import (
                ValidationIssuesDialog,
            )

            dialog = ValidationIssuesDialog(validation_result)
            result_code = dialog.exec_()

            if result_code == ValidationIssuesDialog.SKIP_AND_CONTINUE:
                return "skip"
            if result_code == ValidationIssuesDialog.REFRESH_PREVIEW:
                return "refresh"
        except Exception:
            logger.exception("[ValidationDialogAdapter] Error showing dialog")
            return "cancel"
        else:
            return "cancel"
