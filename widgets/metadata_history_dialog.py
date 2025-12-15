"""
Module: metadata_history_dialog.py

Author: Michael Economou
Date: 2025-05-01

Dialog for viewing and managing metadata command history.
Provides interface for viewing recent metadata operations and undoing/redoing them.

Features:
- List of recent metadata operations
- Detailed view of each operation
- Undo/redo functionality
- Integration with rename history
- Keyboard shortcuts
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QShortcut,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import UNDO_REDO_SETTINGS
from core.metadata_command_manager import get_metadata_command_manager
from core.rename_history_manager import get_rename_history_manager
from core.theme_manager import get_theme_manager
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.tooltip_helper import TooltipType, setup_tooltip

logger = get_cached_logger(__name__)


class MetadataHistoryDialog(QDialog):
    """
    Dialog for viewing and managing metadata command history.

    Provides interface for viewing recent metadata operations,
    rename operations, and performing undo/redo operations.
    """

    def __init__(self, parent: QWidget | None = None):
        """
        Initialize metadata history dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.parent_window = parent
        self.command_manager = get_metadata_command_manager()
        self.rename_history_manager = get_rename_history_manager()

        self.setWindowTitle("Command History - Undo/Redo Operations")
        self.setModal(True)
        self.resize(
            UNDO_REDO_SETTINGS["HISTORY_DIALOG_WIDTH"], UNDO_REDO_SETTINGS["HISTORY_DIALOG_HEIGHT"]
        )

        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()
        self._load_history()

        logger.debug("[MetadataHistoryDialog] Initialized")

    def showEvent(self, event):
        """Handle show event to ensure proper positioning."""
        super().showEvent(event)
        # Refresh history when dialog is shown
        self._load_history()

    def _setup_ui(self):
        """Setup the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title_label = QLabel("Command History")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(title_label)

        # Info label
        theme = get_theme_manager()
        info_label = QLabel(
            "Recent metadata and rename operations. Global shortcuts: Ctrl+Z (Undo), Ctrl+Shift+Z (Redo), Ctrl+Y (History)."
        )
        info_label.setStyleSheet(
            f"color: {theme.get_color('text_muted')}; font-size: 11px; margin-bottom: 10px;"
        )
        layout.addWidget(info_label)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left side: Operations list
        left_widget = self._create_operations_panel()
        splitter.addWidget(left_widget)

        # Right side: Operation details
        right_widget = self._create_details_panel()
        splitter.addWidget(right_widget)

        # Set splitter proportions
        splitter.setSizes([500, 400])

        # Bottom buttons
        button_layout = self._create_button_layout()
        layout.addLayout(button_layout)

    def _create_operations_panel(self) -> QWidget:
        """Create the operations list panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 5, 0)

        # Operations table
        self.operations_table = QTableWidget()
        self.operations_table.setColumnCount(4)
        self.operations_table.setHorizontalHeaderLabels(["Time", "Operation", "File", "Status"])

        # Configure table
        header = self.operations_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.operations_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.operations_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.operations_table.setAlternatingRowColors(True)
        self.operations_table.setShowGrid(False)
        self.operations_table.verticalHeader().setVisible(False)

        # Set row height from theme engine
        from oncutf.utils.theme_engine import ThemeEngine
        theme = ThemeEngine()
        self.operations_table.verticalHeader().setDefaultSectionSize(theme.get_constant("table_row_height"))

        # Connect selection change
        self.operations_table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self.operations_table)

        # Action buttons
        button_layout = QHBoxLayout()

        self.undo_button = QPushButton("Undo")
        self.undo_button.setEnabled(False)
        self.undo_button.clicked.connect(self._undo_selected)
        setup_tooltip(self.undo_button, "Undo the selected operation from history", TooltipType.INFO)
        button_layout.addWidget(self.undo_button)

        self.redo_button = QPushButton("Redo")
        self.redo_button.setEnabled(False)
        self.redo_button.clicked.connect(self._redo_selected)
        setup_tooltip(
            self.redo_button, "Redo the selected operation from history", TooltipType.INFO
        )
        button_layout.addWidget(self.redo_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        return widget

    def _create_details_panel(self) -> QWidget:
        """Create the operation details panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 0, 0, 0)

        details_label = QLabel("Operation Details")
        details_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(details_label)

        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlainText("Select an operation to view details...")

        # Set monospace font for better formatting
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier", 10)
        self.details_text.setFont(font)

        layout.addWidget(self.details_text)

        return widget

    def _create_button_layout(self) -> QHBoxLayout:
        """Create the bottom button layout."""
        layout = QHBoxLayout()

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._load_history)
        setup_tooltip(refresh_button, "Refresh the command history", TooltipType.INFO)
        layout.addWidget(refresh_button)

        # Clear history button
        clear_button = QPushButton("Clear History")
        clear_button.clicked.connect(self._clear_history)
        setup_tooltip(clear_button, "Clear all command history", TooltipType.WARNING)
        layout.addWidget(clear_button)

        layout.addStretch()

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        return layout

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Dialog-specific Ctrl+Z/Ctrl+R shortcuts removed - global shortcuts apply
        # Buttons provide explicit "undo/redo selected operation" functionality

        # Refresh shortcut (F5) - dialog-specific, doesn't conflict with global
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self._load_history)

    def _connect_signals(self):
        """Connect signals from command manager."""
        self.command_manager.can_undo_changed.connect(self._update_button_states)
        self.command_manager.can_redo_changed.connect(self._update_button_states)
        self.command_manager.history_changed.connect(self._load_history)

    def _load_history(self):
        """Load command history into the table."""
        try:
            # Get metadata commands
            metadata_commands = self.command_manager.get_command_history(
                UNDO_REDO_SETTINGS["HISTORY_ITEMS_PER_PAGE"]
            )

            # Get rename operations
            rename_operations = self.rename_history_manager.get_recent_operations(20)

            # Combine and sort by timestamp
            all_operations = []

            # Add metadata commands
            for cmd in metadata_commands:
                all_operations.append(
                    {
                        "timestamp": cmd["timestamp"],
                        "operation": cmd["description"],
                        "file": self._get_file_basename(cmd["file_path"]),
                        "status": (
                            "Can Undo"
                            if cmd["can_undo"]
                            else "Can Redo"
                            if cmd["can_redo"]
                            else "Done"
                        ),
                        "type": "metadata",
                        "data": cmd,
                    }
                )

            # Add rename operations
            for op in rename_operations:
                all_operations.append(
                    {
                        "timestamp": op["timestamp"],
                        "operation": op["display_text"],
                        "file": f"{op['file_count']} files",
                        "status": "Rename Operation",
                        "type": "rename",
                        "data": op,
                    }
                )

            # Sort by timestamp (most recent first)
            all_operations.sort(key=lambda x: x["timestamp"], reverse=True)

            # Populate table
            self.operations_table.setRowCount(len(all_operations))

            for row, operation in enumerate(all_operations):
                # Time
                timestamp = operation["timestamp"]
                if hasattr(timestamp, "strftime"):
                    time_str = timestamp.strftime("%H:%M:%S")
                else:
                    time_str = str(timestamp)[:8] if len(str(timestamp)) > 8 else str(timestamp)

                time_item = QTableWidgetItem(time_str)
                time_item.setData(Qt.UserRole, operation)
                self.operations_table.setItem(row, 0, time_item)

                # Operation
                op_item = QTableWidgetItem(operation["operation"])
                self.operations_table.setItem(row, 1, op_item)

                # File
                file_item = QTableWidgetItem(operation["file"])
                self.operations_table.setItem(row, 2, file_item)

                # Status
                status_item = QTableWidgetItem(operation["status"])

                # Color code status
                if operation["status"] == "Can Undo":
                    status_item.setForeground(Qt.darkGreen)
                elif operation["status"] == "Can Redo":
                    status_item.setForeground(Qt.darkBlue)
                elif operation["status"] == "Rename Operation":
                    status_item.setForeground(Qt.darkMagenta)
                else:
                    status_item.setForeground(Qt.gray)

                self.operations_table.setItem(row, 3, status_item)

            # Update button states
            self._update_button_states()

            logger.debug(f"[MetadataHistoryDialog] Loaded {len(all_operations)} operations")

        except Exception as e:
            logger.error(f"[MetadataHistoryDialog] Error loading history: {e}")

    def _on_selection_changed(self):
        """Handle selection change in operations table."""
        selected_items = self.operations_table.selectedItems()
        if not selected_items:
            self.details_text.setPlainText("Select an operation to view details...")
            self._update_button_states()
            return

        # Get selected operation data
        row = selected_items[0].row()
        time_item = self.operations_table.item(row, 0)
        operation_data = time_item.data(Qt.UserRole)

        if operation_data:
            self._load_operation_details(operation_data)

        self._update_button_states()

    def _load_operation_details(self, operation_data: dict):
        """Load details for selected operation."""
        try:
            details = []

            if operation_data["type"] == "metadata":
                # Metadata command details
                cmd_data = operation_data["data"]
                details.append("METADATA COMMAND")
                details.append(f"Command ID: {cmd_data['command_id']}")
                details.append(f"Type: {cmd_data['command_type']}")
                details.append(f"Description: {cmd_data['description']}")
                details.append(f"File: {cmd_data['file_path']}")
                details.append(f"Timestamp: {cmd_data['timestamp']}")
                details.append(f"Can Undo: {cmd_data['can_undo']}")
                details.append(f"Can Redo: {cmd_data['can_redo']}")

            elif operation_data["type"] == "rename":
                # Rename operation details
                op_data = operation_data["data"]
                details.append("RENAME OPERATION")
                details.append(f"Operation ID: {op_data['operation_id']}")
                details.append(f"File Count: {op_data['file_count']}")
                details.append(f"Timestamp: {op_data['timestamp']}")
                details.append(f"Operation Type: {op_data['operation_type']}")

                # Get detailed rename information
                rename_details = self.rename_history_manager.get_operation_details(
                    op_data["operation_id"]
                )
                if rename_details:
                    details.append("\nRENAME DETAILS:")
                    for i, rename_op in enumerate(rename_details.operations[:10]):  # Show first 10
                        details.append(
                            f"  {i + 1}. {rename_op.old_filename} → {rename_op.new_filename}"
                        )

                    if len(rename_details.operations) > 10:
                        details.append(
                            f"  ... and {len(rename_details.operations) - 10} more files"
                        )

            self.details_text.setPlainText("\n".join(details))

        except Exception as e:
            logger.error(f"[MetadataHistoryDialog] Error loading operation details: {e}")
            self.details_text.setPlainText(f"Error loading details: {e}")

    def _update_button_states(self):
        """Update the state of undo/redo buttons."""
        selected_items = self.operations_table.selectedItems()

        if not selected_items:
            self.undo_button.setEnabled(self.command_manager.can_undo())
            self.redo_button.setEnabled(self.command_manager.can_redo())
            return

        # Get selected operation
        row = selected_items[0].row()
        time_item = self.operations_table.item(row, 0)
        operation_data = time_item.data(Qt.UserRole)

        if operation_data and operation_data["type"] == "metadata":
            cmd_data = operation_data["data"]
            self.undo_button.setEnabled(cmd_data["can_undo"])
            self.redo_button.setEnabled(cmd_data["can_redo"])
        else:
            # For rename operations, use general undo/redo state
            self.undo_button.setEnabled(self.command_manager.can_undo())
            self.redo_button.setEnabled(self.command_manager.can_redo())

    def _undo_selected(self):
        """Undo the selected operation or the last operation."""
        if self.command_manager.undo():
            self._load_history()

            # Show status message
            if self.parent_window and hasattr(self.parent_window, "status_bar"):
                self.parent_window.status_bar.showMessage("Operation undone", 2000)

    def _redo_selected(self):
        """Redo the selected operation or the last undone operation."""
        if self.command_manager.redo():
            self._load_history()

            # Show status message
            if self.parent_window and hasattr(self.parent_window, "status_bar"):
                self.parent_window.status_bar.showMessage("Operation redone", 2000)

    def _clear_history(self):
        """Clear all command history."""
        from widgets.custom_message_dialog import CustomMsgDialog

        result = CustomMsgDialog.show_question(
            self,
            "Clear History",
            "Are you sure you want to clear all command history?\n\n"
            "This action cannot be undone and will remove all undo/redo capabilities.",
        )

        if result:
            self.command_manager.clear_history()
            self._load_history()

            # Show status message
            if self.parent_window and hasattr(self.parent_window, "status_bar"):
                self.parent_window.status_bar.showMessage("Command history cleared", 2000)

    def _get_file_basename(self, file_path: str) -> str:
        """Get the basename of a file path."""
        import os

        return os.path.basename(file_path) if file_path else ""


def show_metadata_history_dialog(parent: QWidget | None = None) -> None:
    """
    Show the metadata history dialog.

    Args:
        parent: Parent widget
    """
    dialog = MetadataHistoryDialog(parent)
    dialog.exec_()
