"""
metadata_edit_dialog.py

Author: Michael Economou
Date: 2025-01-28

Generic dialog for editing metadata fields.
Based on bulk_rotation_dialog.py but made flexible for different field types.
"""

from typing import List, Optional, Dict, Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


from utils.logger_factory import get_cached_logger
from utils.metadata_field_validators import MetadataFieldValidator

logger = get_cached_logger(__name__)


class MetadataEditDialog(QDialog):
    """
    Generic dialog for editing metadata fields.

    Supports:
    - Single field editing (Title, Artist, Copyright, etc.)
    - Multi-file operations with file type grouping
    - Field validation using MetadataFieldValidator
    - Dynamic UI based on field type (single-line vs multi-line)
    """

    def __init__(self, parent=None, selected_files=None, metadata_cache=None,
                 field_name: str = "Title", field_value: str = ""):
        super().__init__(parent)
        self.selected_files = selected_files or []
        self.metadata_cache = metadata_cache
        self.field_name = field_name
        self.field_value = field_value

        # Determine if this is a multi-line field
        self.is_multiline = field_name in ["Description"]

        # Set up dialog properties - frameless but draggable
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)

        # Add drag functionality
        self._drag_position = None

        # Adjust size based on field type (single file only)
        if self.is_multiline:
            self.setFixedSize(420, 200)
        else:
            self.setFixedSize(380, 140)

        self._setup_styles()
        self._setup_ui()

    def _setup_styles(self):
        """Set up dialog styling using theme system."""
        # All styling now handled by the QSS theme system
        pass

    def _setup_ui(self):
        """Set up the main UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)  # No default spacing - we'll control it manually

        # Simple field label (e.g., "Title:", "Description:", etc.)
        self.field_label = QLabel(f"{self.field_name}:")
        layout.addWidget(self.field_label)

        # Small space between label and input
        layout.addSpacing(2)

        # Input field (QLineEdit or QTextEdit)
        self._create_input_field()
        layout.addWidget(self.input_field)

        # Very small space between input and hints
        layout.addSpacing(1)

        # Hints label (right under the input field)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        from utils.theme import get_theme_color
        muted_color = get_theme_color('text')
        self.info_label.setStyleSheet(f"color: {muted_color}; font-size: 8pt; opacity: 0.7;")
        layout.addWidget(self.info_label)

        # Update validation info
        self._update_validation_info()

        # Larger space before buttons
        layout.addSpacing(20)

        # Buttons
        self._setup_buttons(layout)

    def _setup_buttons(self, parent_layout):
        """Set up OK/Cancel buttons."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setDefault(False)
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.setFocus()
        self.cancel_button.clicked.connect(self.reject)



        # OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self._validate_and_accept)



        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        parent_layout.addLayout(button_layout)

    def _create_input_field(self):
        """Create the input field (QLineEdit or QTextEdit) based on field type."""
        if self.is_multiline:
            self.input_field = QTextEdit()
            self.input_field.setPlainText(self.field_value)
            self.input_field.setMaximumHeight(100)
            self.input_field.setMinimumHeight(80)
        else:
            self.input_field = QLineEdit()
            self.input_field.setText(self.field_value)
            self.input_field.selectAll()

        # Add field-specific placeholder text
        placeholder = self._get_field_placeholder()
        if placeholder:
            self.input_field.setPlaceholderText(placeholder)

        # Set focus to input field
        self.input_field.setFocus()

    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if event.buttons() == Qt.LeftButton and self._drag_position:
            self.move(event.globalPos() - self._drag_position)
            event.accept()

    def _get_field_placeholder(self) -> str:
        """Get placeholder text for the field."""
        placeholders = {
            "Title": "Enter title...",
            "Artist": "Enter artist name...",
            "Author": "Enter author name...",
            "Copyright": "Enter copyright information...",
            "Description": "Enter description...",
            "Keywords": "Enter keywords (comma-separated)..."
        }
        return placeholders.get(self.field_name, "")

    def _update_validation_info(self):
        """Update info label with validation information."""
        if self.field_name == "Title":
            self.info_label.setText("The title is required and cannot contain special characters.")
        elif self.field_name == "Keywords":
            self.info_label.setText("Separate keywords with commas. Maximum 50 keywords.")
        else:
            max_length = getattr(MetadataFieldValidator, f'MAX_{self.field_name.upper()}_LENGTH', None)
            if max_length:
                self.info_label.setText(f"Maximum {max_length} characters.")

    def _validate_and_accept(self):
        """Validate input and accept dialog if valid."""
        # Get the input value
        if self.is_multiline:
            value = self.input_field.toPlainText()
        else:
            value = self.input_field.text()

        # Validate using MetadataFieldValidator
        is_valid, error_message = MetadataFieldValidator.validate_field(self.field_name, value)

        if not is_valid:
            # Show error in info label
            self.info_label.setText(f"Error: {error_message}")
            from utils.theme import get_theme_color
            error_color = get_theme_color('text')  # Use theme-based error color
            self.info_label.setStyleSheet(f"color: #ff6b6b; font-size: 8pt;")
            return

        # Store the validated value
        self.validated_value = value.strip()
        self.accept()

    def get_validated_value(self) -> str:
        """Get the validated input value."""
        return getattr(self, 'validated_value', '')



    @staticmethod
    def edit_metadata_field(parent, selected_files, metadata_cache, field_name: str, current_value: str = ""):
        """
        Static method to show metadata edit dialog and return results.

        Args:
            parent: Parent widget
            selected_files: List of FileItem objects
            metadata_cache: Metadata cache instance
            field_name: Name of field to edit
            current_value: Current value (for single file editing)

        Returns:
            Tuple of (success: bool, value: str, files_to_modify: List)
        """
        dialog = MetadataEditDialog(parent, selected_files, metadata_cache, field_name, current_value)

        if dialog.exec_() == QDialog.Accepted:
            return True, dialog.get_validated_value(), dialog.get_selected_files()

        return False, "", []
