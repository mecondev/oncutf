"""Module: conflict_resolution_dialog.py

Author: Michael Economou
Date: 2026-01-15

Dialog for handling file rename conflicts with user interaction.

Provides options:
- Skip: Skip this file
- Overwrite: Replace existing file
- Rename: Add numeric suffix (_1, _2, etc.)
- Skip All: Skip all remaining conflicts
- Cancel: Abort entire operation

Includes "Apply to All" checkbox for batch operations.
"""

from oncutf.core.pyqt_imports import QDialog, QWidget
from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ConflictResolutionDialog(CustomMessageDialog):
    """Dialog for resolving file rename conflicts."""

    def __init__(
        self,
        old_filename: str,
        new_filename: str,
        parent: QWidget | None = None,
    ):
        """Initialize conflict resolution dialog.

        Args:
            old_filename: Original filename being renamed
            new_filename: Target filename that already exists
            parent: Parent widget

        """
        message = (
            f"Cannot rename file:\n\n"
            f"From: {old_filename}\n"
            f"To: {new_filename}\n\n"
            f"A file with the target name already exists.\n"
            f"How would you like to proceed?"
        )

        buttons = ["Skip", "Overwrite", "Rename", "Skip All", "Cancel"]

        super().__init__(
            title="File Rename Conflict",
            message=message,
            buttons=buttons,
            parent=parent,
            show_checkbox=True,  # Show "Apply to All" checkbox
        )

        # Set default button focus
        if "Skip" in self._buttons:
            self._buttons["Skip"].setDefault(True)
            self._buttons["Skip"].setFocus()

        # Style buttons with appropriate colors
        self._style_buttons()

    def _style_buttons(self):
        """Apply appropriate styling to buttons."""
        # Destructive action (Overwrite) should be visually distinct
        if "Overwrite" in self._buttons:
            self._buttons["Overwrite"].setStyleSheet(
                "QPushButton { background-color: #d32f2f; color: white; }"
                "QPushButton:hover { background-color: #f44336; }"
            )

        # Primary action (Skip) is safe default
        if "Skip" in self._buttons:
            self._buttons["Skip"].setStyleSheet(
                "QPushButton { font-weight: bold; }"
            )

    def get_resolution(self) -> tuple[str, bool]:
        """Execute dialog and return user choice.

        Returns:
            Tuple of (action, apply_to_all) where:
                action: One of "skip", "overwrite", "rename", "skip_all", "cancel"
                apply_to_all: True if checkbox was checked

        """
        result = self.exec_()

        if result == QDialog.Rejected or self.selected is None:
            return ("cancel", False)

        # Map button text to action
        action_map = {
            "Skip": "skip",
            "Overwrite": "overwrite",
            "Rename": "rename",
            "Skip All": "skip_all",
            "Cancel": "cancel",
        }

        action = action_map.get(self.selected, "cancel")
        apply_to_all = self.checkbox.isChecked() if self.checkbox else False

        logger.info(
            "[ConflictResolutionDialog] User chose: %s (apply_to_all=%s)",
            action,
            apply_to_all,
        )

        return (action, apply_to_all)

    @staticmethod
    def show_conflict(
        old_filename: str,
        new_filename: str,
        parent: QWidget | None = None,
    ) -> tuple[str, bool]:
        """Show conflict resolution dialog (convenience method).

        Args:
            old_filename: Original filename
            new_filename: Target filename that exists
            parent: Parent widget

        Returns:
            Tuple of (action, apply_to_all)

        """
        dialog = ConflictResolutionDialog(old_filename, new_filename, parent)
        return dialog.get_resolution()
