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
        self.file_groups = {}
        self.checkboxes = {}

        # Determine if this is a multi-line field
        self.is_multiline = field_name in ["Description"]

        # Set up dialog properties - frameless but draggable
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)

        # Add drag functionality
        self._drag_position = None

        # Adjust size based on field type and number of files
        if len(self.selected_files) > 1:
            # Multi-file mode - larger dialog
            self.setFixedSize(550, 450)
        else:
            # Single file mode - smaller dialog
            if self.is_multiline:
                self.setFixedSize(420, 280)
            else:
                self.setFixedSize(380, 180)

        self._setup_styles()
        self._setup_ui()

        # Analyze files only for multi-file operations
        if len(self.selected_files) > 1:
            self._analyze_files()
        else:
            self._setup_single_file_ui()

    def _setup_styles(self):
        """Set up dialog styling using theme system."""
        # All styling now handled by the QSS theme system
        pass

    def _setup_ui(self):
        """Set up the main UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Description (will be set differently for single vs multi-file)
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # Content area (either input field or scroll area for file groups)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(2)  # Very tight spacing for content
        self.content_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        layout.addWidget(self.content_widget)

        # Info label
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        from utils.theme import get_theme_color
        muted_color = get_theme_color('text')  # Use theme text color
        self.info_label.setStyleSheet(f"color: {muted_color}; font-size: 8pt; opacity: 0.7;")
        layout.addWidget(self.info_label)

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

    def _setup_single_file_ui(self):
        """Set up UI for single file editing."""
        # Update description
        if self.selected_files:
            filename = self.selected_files[0].filename
            self.desc_label.setText(f"Edit {self.field_name} for: {filename}")
        else:
            self.desc_label.setText(f"Edit {self.field_name}")

        # Create input field based on field type
        if self.is_multiline:
            self.input_field = QTextEdit()
            self.input_field.setPlainText(self.field_value)
            self.input_field.setMaximumHeight(100)
            self.input_field.setMinimumHeight(80)
        else:
            self.input_field = QLineEdit()
            self.input_field.setText(self.field_value)
            self.input_field.setFixedHeight(20)  # Match specified text module height
            self.input_field.selectAll()

        # Add field-specific placeholder text
        placeholder = self._get_field_placeholder()
        if placeholder:
            if self.is_multiline:
                self.input_field.setPlaceholderText(placeholder)
            else:
                self.input_field.setPlaceholderText(placeholder)

        self.content_layout.addWidget(self.input_field)

        # Set focus to input field
        self.input_field.setFocus()

        # Update info with validation info
        self._update_validation_info()

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

    def _analyze_files(self):
        """Analyze files for multi-file editing (similar to bulk rotation)."""
        if not self.selected_files:
            self.info_label.setText("No files selected.")
            return

        # Update description for multi-file
        self.desc_label.setText(f"Set {self.field_name} for selected files:")

        # Group files by type and existing field values
        file_types = {}
        total_files = len(self.selected_files)
        files_with_existing_values = 0

        for file_item in self.selected_files:
            # Determine file type
            file_type = self._get_file_type_category(file_item)

            if file_type not in file_types:
                file_types[file_type] = {
                    'all_files': [],
                    'extensions': set()
                }

            file_types[file_type]['all_files'].append(file_item)

            # Get extension for display
            ext = file_item.filename.split('.')[-1].upper() if '.' in file_item.filename else 'UNKNOWN'
            file_types[file_type]['extensions'].add(ext)

            # Check if file has existing value for this field
            if self._get_current_field_value(file_item):
                files_with_existing_values += 1

        # Create scroll area for file groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumHeight(200)

        # Content widget for scroll area
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(12)

        # Create groups
        for file_type, data in file_types.items():
            all_files = data['all_files']
            extensions = sorted(data['extensions'])
            self._create_group_widget(scroll_layout, file_type, all_files, extensions)

        scroll.setWidget(scroll_content)
        self.content_layout.addWidget(scroll)

        # Add input field for new value
        input_layout = QVBoxLayout()
        input_label = QLabel(f"New value for {self.field_name}:")
        input_layout.addWidget(input_label)

        if self.is_multiline:
            self.input_field = QTextEdit()
            self.input_field.setPlainText(self.field_value)
            self.input_field.setMaximumHeight(80)
        else:
            self.input_field = QLineEdit()
            self.input_field.setText(self.field_value)

        # Add placeholder
        placeholder = self._get_field_placeholder()
        if placeholder:
            self.input_field.setPlaceholderText(placeholder)

        input_layout.addWidget(self.input_field)
        self.content_layout.addLayout(input_layout)

        # Update info label
        info_text = f"{total_files} files selected"
        if files_with_existing_values > 0:
            info_text += f" ({files_with_existing_values} already have values)"
        self.info_label.setText(info_text)

        # Set focus to input field
        self.input_field.setFocus()

    def _get_file_type_category(self, file_item) -> str:
        """Get file type category for grouping."""
        if not hasattr(file_item, 'filename'):
            return "Other"

        ext = file_item.filename.lower().split('.')[-1] if '.' in file_item.filename else ''

        if ext in ['jpg', 'jpeg', 'png', 'tiff', 'tif', 'bmp', 'gif', 'webp', 'heic']:
            return "Images"
        elif ext in ['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'm4v', 'webm']:
            return "Videos"
        elif ext in ['mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg', 'opus']:
            return "Audio"
        elif ext in ['pdf', 'doc', 'docx', 'txt']:
            return "Documents"
        else:
            return "Other"

    def _get_current_field_value(self, file_item) -> Optional[str]:
        """Get current value of the field for a file."""
        if not self.metadata_cache:
            return None

        # Check metadata cache first
        metadata_entry = self.metadata_cache.get_entry(file_item.full_path)
        if metadata_entry and hasattr(metadata_entry, 'data'):
            # Try different field standards
            standards = self._get_field_standards()
            for standard in standards:
                value = metadata_entry.data.get(standard)
                if value:
                    return str(value)

        # Fallback to file metadata
        if hasattr(file_item, 'metadata') and file_item.metadata:
            for standard in self._get_field_standards():
                value = file_item.metadata.get(standard)
                if value:
                    return str(value)

        return None

    def _get_field_standards(self) -> List[str]:
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

    def _create_group_widget(self, parent_layout, file_type: str, all_files: List, extensions: List[str]):
        """Create a widget for a file type group."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Header with checkbox
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(True)  # Default to checked
        self.checkboxes[file_type] = checkbox

        # Label with file count
        extensions_text = ", ".join(extensions)
        file_count = len(all_files)
        label_text = f"{file_type} ({file_count} files): {extensions_text}"

        label = QLabel(label_text)
        label.setWordWrap(True)

        header_layout.addWidget(checkbox)
        header_layout.addWidget(label, 1)
        layout.addLayout(header_layout)

        parent_layout.addWidget(frame)

        # Store files for this group
        self.file_groups[file_type] = all_files

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

    def get_selected_files(self) -> List:
        """Get list of files that should be modified (for multi-file mode)."""
        if len(self.selected_files) <= 1:
            return self.selected_files

        # Return files from checked groups
        selected = []
        for file_type, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected.extend(self.file_groups[file_type])
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
