"""
Module: realtime_validation_widget.py

Author: Michael Economou
Date: 2025-05-01

Real-time Validation Widget for immediate validation feedback.
"""

from core.pyqt_imports import (
    QFrame,
    QLabel,
    QProgressBar,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class RealTimeValidationWidget(QWidget):
    """Widget for real-time validation feedback."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("RealTimeValidationWidget")
        self.setProperty("class", "RealTimeValidationWidget")

        # Validation update timer
        self.update_timer = QTimer()
        self.update_timer.setInterval(500)  # Update every 500ms
        self.update_timer.timeout.connect(self.update_validation)

        self.setup_ui()

        # Start auto-update
        self.update_timer.start()

    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Title
        title = QLabel("Real-time Validation")
        title.setProperty("class", "ValidationTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Status container
        self.status_container = QWidget()
        status_layout = QVBoxLayout(self.status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(2)
        layout.addWidget(self.status_container)

        # Create status labels
        self.overall_status_label = self._create_status_label("Status: Ready", "ready")
        self.valid_count_label = self._create_status_label("Valid: 0", "valid")
        self.invalid_count_label = self._create_status_label("Invalid: 0", "invalid")
        self.duplicate_count_label = self._create_status_label("Duplicates: 0", "duplicate")
        self.unchanged_count_label = self._create_status_label("Unchanged: 0", "unchanged")

        status_layout.addWidget(self.overall_status_label)
        status_layout.addWidget(self.valid_count_label)
        status_layout.addWidget(self.invalid_count_label)
        status_layout.addWidget(self.duplicate_count_label)
        status_layout.addWidget(self.unchanged_count_label)

        # Progress bar for validation progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setProperty("class", "ValidationProgress")
        layout.addWidget(self.progress_bar)

        # Error details
        self.error_details_label = QLabel("")
        self.error_details_label.setProperty("class", "ValidationError")
        self.error_details_label.setWordWrap(True)
        self.error_details_label.setVisible(False)
        layout.addWidget(self.error_details_label)

    def _create_status_label(self, text: str, status_type: str) -> QLabel:
        """Create a status label."""
        label = QLabel(text)
        label.setProperty("class", f"ValidationStatus_{status_type}")
        return label

    def update_validation(self):
        """Update the validation display."""
        try:
            # Get current state from main window
            from core.application_context import get_app_context

            context = get_app_context()
            if not context or not hasattr(context, "main_window"):
                return

            main_window = context.main_window
            if not hasattr(main_window, "unified_rename_engine"):
                return

            current_state = main_window.unified_rename_engine.get_current_state()

            if not current_state.validation_result:
                # No validation result yet
                self.overall_status_label.setText("Status: No validation data")
                self.overall_status_label.setProperty("class", "ValidationStatus_ready")
                self.valid_count_label.setText("Valid: 0")
                self.invalid_count_label.setText("Invalid: 0")
                self.duplicate_count_label.setText("Duplicates: 0")
                self.unchanged_count_label.setText("Unchanged: 0")
                self.error_details_label.setVisible(False)
                return

            validation_result = current_state.validation_result

            # Count different types
            valid_count = sum(
                1
                for item in validation_result.items
                if item.is_valid and not item.is_duplicate and not item.is_unchanged
            )
            invalid_count = sum(1 for item in validation_result.items if not item.is_valid)
            duplicate_count = sum(1 for item in validation_result.items if item.is_duplicate)
            unchanged_count = sum(1 for item in validation_result.items if item.is_unchanged)
            total_count = len(validation_result.items)

            # Update labels
            self.valid_count_label.setText(f"Valid: {valid_count}")
            self.invalid_count_label.setText(f"Invalid: {invalid_count}")
            self.duplicate_count_label.setText(f"Duplicates: {duplicate_count}")
            self.unchanged_count_label.setText(f"Unchanged: {unchanged_count}")

            # Update overall status
            if invalid_count > 0:
                self.overall_status_label.setText("Status: Validation Errors")
                self.overall_status_label.setProperty("class", "ValidationStatus_error")
                self._show_error_details(validation_result.items)
            elif duplicate_count > 0:
                self.overall_status_label.setText("Status: Duplicates Found")
                self.overall_status_label.setProperty("class", "ValidationStatus_warning")
                self.error_details_label.setVisible(False)
            elif unchanged_count == total_count:
                self.overall_status_label.setText("Status: No Changes")
                self.overall_status_label.setProperty("class", "ValidationStatus_warning")
                self.error_details_label.setVisible(False)
            else:
                self.overall_status_label.setText("Status: Ready to Rename")
                self.overall_status_label.setProperty("class", "ValidationStatus_success")
                self.error_details_label.setVisible(False)

            # Update progress bar
            if total_count > 0:
                progress = (valid_count / total_count) * 100
                self.progress_bar.setValue(int(progress))
                self.progress_bar.setVisible(True)
            else:
                self.progress_bar.setVisible(False)

        except Exception as e:
            logger.error(f"[RealTimeValidationWidget] Error updating validation: {e}")

    def _show_error_details(self, items: list):
        """Show error details."""
        error_messages = []
        for item in items:
            if not item.is_valid and item.error_message:
                error_messages.append(f"• {item.old_name}: {item.error_message}")

        if error_messages:
            self.error_details_label.setText("\n".join(error_messages[:3]))  # Show first 3 errors
            if len(error_messages) > 3:
                self.error_details_label.setText(
                    self.error_details_label.text() + f"\n... and {len(error_messages) - 3} more"
                )
            self.error_details_label.setVisible(True)
        else:
            self.error_details_label.setVisible(False)

    def showEvent(self, event):
        """Show event - start timer."""
        super().showEvent(event)
        self.update_timer.start()

    def hideEvent(self, event):
        """Hide event - stop timer."""
        super().hideEvent(event)
        self.update_timer.stop()
