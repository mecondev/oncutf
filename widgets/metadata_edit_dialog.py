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

        # Multi-file support
        self.file_groups = {}
        self.checkboxes = {}
        self.is_multi_file = len(self.selected_files) > 1

        # Determine if this is a multi-line field
        self.is_multiline = field_name in ["Description"]

        # Set up dialog properties - frameless but draggable
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog) # type: ignore
        self.setModal(True)

        # Add drag functionality
        self._drag_position = None

        # Adjust size based on mode and field type
        if self.is_multi_file:
            # Multi-file mode - taller for checkboxes
            if self.is_multiline:
                self.setFixedSize(450, 280)
            else:
                self.setFixedSize(450, 220)
        else:
            # Single file mode
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

        # Small space between label and checkboxes/input
        layout.addSpacing(2)

        # Add file group checkboxes for multi-file mode
        if self.is_multi_file:
            self._create_file_group_checkboxes(layout)
            # Small space between checkboxes and input
            layout.addSpacing(4)

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

        # Setup tab order after all widgets are created
        self._setup_tab_order()

        # Set focus to input field after all widgets are created (works for both single and multi-file)
        self.input_field.setFocus()

    def _setup_tab_order(self):
        """Setup proper tab order: text_field -> OK -> Cancel -> checkboxes -> back to text_field"""
        tab_widgets = []

        # Start with input field
        tab_widgets.append(self.input_field)

        # Then buttons
        tab_widgets.append(self.ok_button)
        tab_widgets.append(self.cancel_button)

        # Then checkboxes (if multi-file mode)
        if self.is_multi_file:
            for checkbox in self.checkboxes.values():
                tab_widgets.append(checkbox)

        # Set tab order
        for i in range(len(tab_widgets) - 1):
            self.setTabOrder(tab_widgets[i], tab_widgets[i + 1])

    def _setup_buttons(self, parent_layout):
        """Set up OK/Cancel buttons."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setDefault(False)
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.reject)

        # OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.setDefault(False)  # Prevent default button behavior
        self.ok_button.setAutoDefault(False)  # Prevent auto-default behavior
        self.ok_button.clicked.connect(self._validate_and_accept)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        parent_layout.addLayout(button_layout)

    def _create_file_group_checkboxes(self, layout):
        """Create checkboxes for file groups in multi-file mode."""
        # Group files by type
        self._group_files_by_type()

        # Create checkboxes for each file type
        for file_type, file_data in self.file_groups.items():
            files_list = file_data['files']
            extensions = sorted(file_data['extensions'])

            # Create checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # Default to checked
            self.checkboxes[file_type] = checkbox

            # Create label text
            file_count = len(files_list)
            extensions_text = ", ".join(extensions)
            label_text = f"{file_type} ({file_count} files): {extensions_text}"

            # Create horizontal layout for checkbox + label
            checkbox_layout = QHBoxLayout()
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setSpacing(8)

            checkbox_layout.addWidget(checkbox)

            label = QLabel(label_text)
            label.setWordWrap(True)
            checkbox_layout.addWidget(label, 1)

            layout.addLayout(checkbox_layout)

    def _group_files_by_type(self):
        """Group selected files by their type."""
        for file_item in self.selected_files:
            file_type = self._get_file_type_category(file_item)

            if file_type not in self.file_groups:
                self.file_groups[file_type] = {
                    'files': [],
                    'extensions': set()
                }

            self.file_groups[file_type]['files'].append(file_item)

            # Get extension for display
            ext = file_item.filename.split('.')[-1].upper() if '.' in file_item.filename else 'UNKNOWN'
            self.file_groups[file_type]['extensions'].add(ext)

    def _get_file_type_category(self, file_item) -> str:
        """Get file type category for grouping."""
        if not hasattr(file_item, 'filename'):
            return "Other"

        ext = file_item.filename.lower().split('.')[-1] if '.' in file_item.filename else ''

        if ext in ['jpg', 'jpeg', 'png', 'tiff', 'tif', 'bmp', 'gif', 'webp', 'heic', 'arw', 'nef', 'cr2', 'cr3', 'dng', 'raf', 'orf', 'rw2']:
            return "Images"
        elif ext in ['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'm4v', 'webm']:
            return "Videos"
        elif ext in ['mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg', 'opus']:
            return "Audio"
        elif ext in ['pdf', 'doc', 'docx', 'txt']:
            return "Documents"
        else:
            return "Other"

    def _create_input_field(self):
        """Create the input field (QLineEdit or QTextEdit) based on field type."""
        # For multi-file, start with empty field unless all files have same value
        if self.is_multi_file:
            common_value = self._get_common_field_value()
            field_value = common_value if common_value is not None else ""
        else:
            field_value = self.field_value

        if self.is_multiline:
            self.input_field = QTextEdit()
            self.input_field.setPlainText(field_value)
            self.input_field.setMaximumHeight(100)
            self.input_field.setMinimumHeight(80)
        else:
            self.input_field = QLineEdit()
            self.input_field.setText(field_value)
            if not self.is_multi_file:  # Only select all for single file
                self.input_field.selectAll()

        # Add field-specific placeholder text
        placeholder = self._get_field_placeholder()
        if placeholder:
            self.input_field.setPlaceholderText(placeholder)

    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.LeftButton: # type: ignore
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if event.buttons() == Qt.LeftButton and self._drag_position: # type: ignore
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

    def _get_common_field_value(self):
        """Get common field value if all selected files have the same value."""
        if not self.selected_files:
            return None

        values = set()
        for file_item in self.selected_files:
            value = self._get_current_field_value(file_item)
            values.add(value or "")  # Convert None to empty string

        # Return common value only if all files have the same value
        return list(values)[0] if len(values) == 1 else None

    def _get_current_field_value(self, file_item) -> str:
        """Get current value of the field for a file."""
        if not self.metadata_cache:
            return ""

        # Check metadata cache first
        cache_entry = self.metadata_cache.get_entry(file_item.full_path)
        if cache_entry and hasattr(cache_entry, 'data'):
            # Try different field standards
            standards = self._get_field_standards()
            for standard in standards:
                value = cache_entry.data.get(standard)
                if value:
                    return str(value)

        # Fallback to file metadata
        if hasattr(file_item, 'metadata') and file_item.metadata:
            standards = self._get_field_standards()
            for standard in standards:
                value = file_item.metadata.get(standard)
                if value:
                    return str(value)

        return ""

    def _get_field_standards(self) -> list:
        """Get the metadata standards for current field."""
        field_standards = {
            "Title": ["XMP:Title", "IPTC:Headline", "EXIF:ImageDescription"],
            "Artist": ["XMP:Creator", "IPTC:By-line", "EXIF:Artist"],
            "Author": ["XMP:Creator", "IPTC:By-line", "EXIF:Artist"],
            "Copyright": ["XMP:Rights", "IPTC:CopyrightNotice", "EXIF:Copyright"],
            "Description": ["XMP:Description", "IPTC:Caption-Abstract", "EXIF:ImageDescription"],
            "Keywords": ["XMP:Keywords", "IPTC:Keywords"]
        }
        return field_standards.get(self.field_name, [])

    def get_selected_files(self) -> list:
        """Get list of files that should be modified."""
        if not self.is_multi_file:
            return self.selected_files

        # Return files from checked groups
        selected = []
        for file_type, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected.extend(self.file_groups[file_type]['files'])
        return selected



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
