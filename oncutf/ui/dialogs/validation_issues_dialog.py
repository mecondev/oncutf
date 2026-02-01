"""Module: validation_issues_dialog.py.

Author: Michael Economou
Date: 2025-12-16

Dialog for displaying pre-execution validation issues.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from oncutf.models.validation_result import ValidationIssueType
from oncutf.ui.helpers.tooltip_helper import TooltipHelper, TooltipType

if TYPE_CHECKING:
    from oncutf.models.validation_result import ValidationResult


class ValidationIssuesDialog(QDialog):
    """Dialog showing pre-execution validation issues.

    Allows user to:
    - Skip problematic files and continue
    - Cancel operation
    - Refresh preview
    """

    # Dialog result codes
    SKIP_AND_CONTINUE = 1
    CANCEL_OPERATION = 0
    REFRESH_PREVIEW = 2

    def __init__(self, validation_result: ValidationResult, parent=None) -> None:
        """Initialize dialog.

        Args:
            validation_result: Validation result with issues
            parent: Parent widget

        """
        super().__init__(parent)
        self.validation_result = validation_result
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup dialog UI."""
        self.setWindowTitle("Validation Issues")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)

        # Header message
        header_text = self._get_header_text()
        header_label = QLabel(header_text)
        header_label.setWordWrap(True)
        layout.addWidget(header_label)

        # Issues list
        issues_list = QListWidget()
        self._populate_issues_list(issues_list)
        layout.addWidget(issues_list)

        # Button box
        button_layout = QHBoxLayout()

        skip_button = QPushButton("Skip and Continue")
        TooltipHelper.setup_tooltip(skip_button, "Continue with valid files only", TooltipType.INFO)
        skip_button.clicked.connect(lambda: self.done(self.SKIP_AND_CONTINUE))
        button_layout.addWidget(skip_button)

        refresh_button = QPushButton("Refresh Preview")
        TooltipHelper.setup_tooltip(
            refresh_button, "Regenerate preview with current files", TooltipType.INFO
        )
        refresh_button.clicked.connect(lambda: self.done(self.REFRESH_PREVIEW))
        button_layout.addWidget(refresh_button)

        cancel_button = QPushButton("Cancel")
        TooltipHelper.setup_tooltip(cancel_button, "Cancel rename operation", TooltipType.WARNING)
        cancel_button.clicked.connect(lambda: self.done(self.CANCEL_OPERATION))
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        # Default to cancel (safest option)
        cancel_button.setDefault(True)
        cancel_button.setFocus()

    def _get_header_text(self) -> str:
        """Get header text based on validation result."""
        result = self.validation_result

        if result.has_critical_issues:
            return (
                f"<b>Cannot proceed with rename:</b> "
                f"{len(result.issues)} file(s) have critical issues.<br><br>"
                "Please resolve these issues or skip affected files."
            )
        return (
            f"<b>Warning:</b> {len(result.issues)} file(s) have been modified "
            "since preview.<br><br>"
            "You can continue, but results may differ from preview."
        )

    def _populate_issues_list(self, list_widget: QListWidget) -> None:
        """Populate issues list widget.

        Args:
            list_widget: QListWidget to populate

        """
        for issue in self.validation_result.issues:
            # Create item text
            icon = self._get_issue_icon(issue.issue_type)
            item_text = f"{icon} {issue.message}"

            item = QListWidgetItem(item_text)
            TooltipHelper.setup_item_tooltip(
                list_widget, item, issue.technical_details, TooltipType.WARNING
            )
            list_widget.addItem(item)

    def _get_issue_icon(self, issue_type: ValidationIssueType) -> str:
        """Get icon/emoji for issue type.

        Args:
            issue_type: Type of validation issue

        Returns:
            ASCII icon character

        """
        # Use ASCII characters only (no Unicode/emoji)
        icons = {
            ValidationIssueType.MISSING: "[X]",
            ValidationIssueType.LOCKED: "[!]",
            ValidationIssueType.PERMISSION_DENIED: "[!]",
            ValidationIssueType.MODIFIED: "[~]",
            ValidationIssueType.INACCESSIBLE: "[?]",
        }
        return icons.get(issue_type, "[!]")
