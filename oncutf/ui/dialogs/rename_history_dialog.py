"""Module: rename_history_dialog.py.

Author: Michael Economou
Date: 2025-06-01

rename_history_dialog.py
Dialog for viewing and managing rename history with undo functionality.
Provides a user-friendly interface for undoing batch rename operations.
Features:
- List of recent rename operations
- Detailed view of each operation
- Undo functionality with validation
- Operation status and file counts
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from oncutf.app.services import get_rename_history_manager
from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog
from oncutf.ui.helpers.tooltip_helper import TooltipHelper, TooltipType
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class RenameHistoryDialog(QDialog):
    """Dialog for viewing and managing rename history.

    Provides interface for viewing recent rename operations and
    undoing them if possible.
    """

    def __init__(self, parent: QWidget | None = None):
        """Initialize the rename history dialog with history manager."""
        super().__init__(parent)
        self.parent_window = parent
        self.history_manager = get_rename_history_manager()
        self.current_operation_id = None

        self.setWindowTitle("Rename History - Undo Operations")
        self.setModal(True)
        self.resize(800, 600)

        self._setup_ui()
        self._load_history()

        logger.debug("[RenameHistoryDialog] Initialized")

    def showEvent(self, event):
        """Handle show event to ensure proper positioning on multiscreen setups."""
        super().showEvent(event)
        # Ensure dialog appears centered on the same screen as its parent
        from oncutf.ui.helpers.multiscreen_helper import position_dialog_relative_to_parent

        position_dialog_relative_to_parent(self)

    def _setup_ui(self):
        """Setup the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title_label = QLabel("Recent Rename Operations")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(title_label)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left side: Operations list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 5, 0)

        # Operations table
        self.operations_table = QTableWidget()
        self.operations_table.setColumnCount(3)
        self.operations_table.setHorizontalHeaderLabels(["Date/Time", "Files", "Status"])

        # Configure table
        header = self.operations_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.operations_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.operations_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.operations_table.setAlternatingRowColors(True)
        self.operations_table.setShowGrid(False)
        self.operations_table.verticalHeader().setVisible(False)

        # Connect selection change
        self.operations_table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        left_layout.addWidget(self.operations_table)

        # Undo button
        self.undo_button = QPushButton("Undo Selected Operation")
        self.undo_button.setEnabled(False)
        self.undo_button.clicked.connect(self._undo_operation)
        left_layout.addWidget(self.undo_button)

        splitter.addWidget(left_widget)

        # Right side: Operation details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)

        details_label = QLabel("Operation Details")
        details_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        right_layout.addWidget(details_label)

        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlainText("Select an operation to view details...")
        right_layout.addWidget(self.details_text)

        splitter.addWidget(right_widget)

        # Set splitter proportions
        splitter.setSizes([400, 400])

        # Bottom buttons
        button_layout = QHBoxLayout()

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._load_history)
        button_layout.addWidget(refresh_button)

        # Cleanup button
        cleanup_button = QPushButton("Cleanup Old History")
        cleanup_button.clicked.connect(self._cleanup_history)
        button_layout.addWidget(cleanup_button)

        button_layout.addStretch()

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)

        layout.addLayout(button_layout)

    def _load_history(self):
        """Load recent rename operations into the table."""
        try:
            operations = self.history_manager.get_recent_operations(50)

            self.operations_table.setRowCount(len(operations))

            for row, operation in enumerate(operations):
                # Date/Time
                timestamp = operation.get("timestamp", "")
                display_time = timestamp[:19].replace("T", " ") if "T" in timestamp else timestamp

                time_item = QTableWidgetItem(display_time)
                time_item.setData(Qt.UserRole, operation["operation_id"])
                self.operations_table.setItem(row, 0, time_item)

                # File count
                file_count = operation.get("file_count", 0)
                count_item = QTableWidgetItem(f"{file_count} files")
                count_item.setTextAlignment(Qt.AlignCenter)
                self.operations_table.setItem(row, 1, count_item)

                # Status (check if can undo)
                operation_id = operation["operation_id"]
                can_undo, reason = self.history_manager.can_undo_operation(operation_id)

                if can_undo:
                    status_item = QTableWidgetItem("Can Undo")
                    status_item.setForeground(Qt.darkGreen)
                else:
                    status_item = QTableWidgetItem("Cannot Undo")
                    status_item.setForeground(Qt.darkRed)
                    TooltipHelper.setup_tooltip(status_item, reason, TooltipType.INFO)

                status_item.setTextAlignment(Qt.AlignCenter)
                self.operations_table.setItem(row, 2, status_item)

            # Resize rows to content
            self.operations_table.resizeRowsToContents()

            logger.debug("[RenameHistoryDialog] Loaded %d operations", len(operations))

        except Exception as e:
            logger.error("[RenameHistoryDialog] Error loading history: %s", e)
            CustomMessageDialog.critical(self, "Error", f"Failed to load rename history: {e!s}")

    def _on_selection_changed(self):
        """Handle selection change in operations table."""
        selected_rows = self.operations_table.selectionModel().selectedRows()

        if not selected_rows:
            self.current_operation_id = None
            self.undo_button.setEnabled(False)
            self.details_text.setPlainText("Select an operation to view details...")
            return

        # Get operation ID from selected row
        row = selected_rows[0].row()
        time_item = self.operations_table.item(row, 0)
        operation_id = time_item.data(Qt.UserRole)

        self.current_operation_id = operation_id
        self._load_operation_details(operation_id)

        # Enable/disable undo button based on operation status
        can_undo, _ = self.history_manager.can_undo_operation(operation_id)
        self.undo_button.setEnabled(can_undo)

    def _load_operation_details(self, operation_id: str):
        """Load and display details for a specific operation."""
        try:
            batch = self.history_manager.get_operation_details(operation_id)
            if not batch:
                self.details_text.setPlainText("Operation details not found.")
                return

            # Format details text
            details = []
            details.append(f"Operation ID: {operation_id}")
            details.append(f"Timestamp: {batch.timestamp}")
            details.append(f"Files Renamed: {batch.file_count}")
            details.append("")

            # Check if operation can be undone
            can_undo, reason = self.history_manager.can_undo_operation(operation_id)
            if can_undo:
                details.append("Status: Can be undone")
            else:
                details.append(f"Status: Cannot be undone - {reason}")

            details.append("")
            details.append("Files in this operation:")
            details.append("-" * 40)

            for i, operation in enumerate(batch.operations, 1):
                details.append(f"{i:3d}. {operation.old_filename} → {operation.new_filename}")
                if i > 20:  # Limit display for very large operations
                    remaining = batch.file_count - 20
                    details.append(f"     ... and {remaining} more files")
                    break

            # Add modules information if available
            if batch.modules_data:
                details.append("")
                details.append("Modules used:")
                for i, module_data in enumerate(batch.modules_data, 1):
                    module_type = module_data.get("type", "Unknown")
                    details.append(f"  {i}. {module_type}")

            self.details_text.setPlainText("\n".join(details))

        except Exception as e:
            logger.error("[RenameHistoryDialog] Error loading operation details: %s", e)
            self.details_text.setPlainText(f"Error loading details: {e!s}")

    def _undo_operation(self):
        """Undo the selected operation."""
        if not self.current_operation_id:
            return

        try:
            # Get operation details for confirmation
            batch = self.history_manager.get_operation_details(self.current_operation_id)
            if not batch:
                CustomMessageDialog.warning(self, "Error", "Operation details not found.")
                return

            # Confirm undo
            message = "Are you sure you want to undo this rename operation?\n\n"
            message += f"This will revert {batch.file_count} files to their previous names.\n"
            message += f"Operation from: {batch.timestamp[:19].replace('T', ' ')}"

            if not CustomMessageDialog.question(
                self, "Confirm Undo", message, yes_text="Undo", no_text="Cancel"
            ):
                return

            # Perform undo
            success, message, _files_processed = self.history_manager.undo_operation(
                self.current_operation_id
            )

            if success:
                CustomMessageDialog.information(self, "Undo Complete", message)

                # Refresh the parent window if available
                if hasattr(self.parent_window, "load_files_from_folder") and hasattr(
                    self.parent_window, "current_folder_path"
                ):
                    if self.parent_window.current_folder_path:
                        self.parent_window.load_files_from_folder(
                            self.parent_window.current_folder_path
                        )

                # Refresh history list
                self._load_history()
            else:
                CustomMessageDialog.warning(self, "Undo Failed", message)

        except Exception as e:
            logger.error("[RenameHistoryDialog] Error during undo: %s", e)
            CustomMessageDialog.critical(self, "Error", f"Failed to undo operation: {e!s}")

    def _cleanup_history(self):
        """Clean up old history records."""
        try:
            if not CustomMessageDialog.question(
                self,
                "Cleanup History",
                "This will remove old rename history records.\nContinue?",
                yes_text="Cleanup",
                no_text="Cancel",
            ):
                return

            cleaned_count = self.history_manager.cleanup_old_history(30)  # Keep 30 days

            if cleaned_count > 0:
                CustomMessageDialog.information(
                    self, "Cleanup Complete", f"Cleaned up {cleaned_count} old history records."
                )
                self._load_history()
            else:
                CustomMessageDialog.information(
                    self, "Cleanup Complete", "No old records found to clean up."
                )

        except Exception as e:
            logger.error("[RenameHistoryDialog] Error during cleanup: %s", e)
            CustomMessageDialog.critical(self, "Error", f"Failed to cleanup history: {e!s}")


def show_rename_history_dialog(parent: QWidget | None = None) -> None:
    """Show the rename history dialog.

    Args:
        parent: Parent widget for the dialog

    """
    dialog = RenameHistoryDialog(parent)

    # Ensure proper positioning on multiscreen setups before showing
    if parent:
        from oncutf.ui.helpers.multiscreen_helper import ensure_dialog_on_parent_screen

        ensure_dialog_on_parent_screen(dialog, parent)

    dialog.exec_()
