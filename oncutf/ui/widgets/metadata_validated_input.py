"""Module: metadata_validated_input.py

Author: Michael Economou
Date: 2025-06-01

Validated input widgets specifically designed for metadata field editing.
Provides real-time character validation, paste cleaning, and visual feedback
tailored for different metadata field types.
Contains:
- MetadataValidatedLineEdit: Single-line input with metadata-specific validation
- MetadataValidatedTextEdit: Multi-line input for description fields
"""

import logging

from oncutf.core.pyqt_imports import QComboBox, QKeyEvent, QLineEdit, QTextEdit, QWidget, pyqtSignal
from oncutf.ui.widgets.base_validated_input import BaseValidatedInput
from oncutf.utils.metadata_field_validators import MetadataFieldValidator

logger = logging.getLogger(__name__)


class MetadataValidatedLineEdit(QLineEdit, BaseValidatedInput):
    """Single-line input widget with metadata-specific validation.

    Features:
    - Field-specific character blocking (e.g., filename chars for Title)
    - Real-time validation with visual feedback
    - Paste content cleaning
    - Length validation based on field type
    """

    # Signal emitted when validation state changes
    validation_changed = pyqtSignal(bool)  # True if valid, False if invalid

    def __init__(self, field_name: str = "", parent: QWidget | None = None):
        QLineEdit.__init__(self, parent)
        BaseValidatedInput.__init__(self)

        self._field_name = field_name
        self._setup_field_specific_properties()

    def _setup_validation_signals(self) -> None:
        """Setup internal signal connections."""
        self.textChanged.connect(self._on_text_changed)

    def emit_validation_changed(self, is_valid: bool) -> None:
        """Emit validation changed signal."""
        self.validation_changed.emit(is_valid)

    def _setup_field_specific_properties(self) -> None:
        """Setup field-specific properties like max length."""
        if self._field_name:
            max_length = self._get_field_max_length()
            if max_length > 0:
                self.setMaxLength(max_length)

    def _get_field_max_length(self) -> int:
        """Get maximum length for the current field."""
        field_limits = {
            "Title": MetadataFieldValidator.MAX_TITLE_LENGTH,
            "Artist": MetadataFieldValidator.MAX_ARTIST_LENGTH,
            "Author": MetadataFieldValidator.MAX_ARTIST_LENGTH,
            "Copyright": MetadataFieldValidator.MAX_COPYRIGHT_LENGTH,
            "Keywords": 1000,  # Reasonable limit for keywords field
        }
        return field_limits.get(self._field_name, 0)

    def get_blocked_characters(self) -> set[str]:
        """Get set of characters that should be blocked for this field.

        Returns:
            Set of characters to block

        """
        # Only Title field blocks filename-unsafe characters
        if self._field_name == "Title":
            return set(MetadataFieldValidator.INVALID_FILENAME_CHARS)

        # Other fields allow all characters
        return set()

    def validate_text_content(self, text: str) -> tuple[bool, str]:
        """Validate text content using metadata field validators.

        Args:
            text: Text to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        if not self._field_name:
            return super().validate_text_content(text)

        # Use MetadataFieldValidator for validation
        return MetadataFieldValidator.validate_field(self._field_name, text)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events with validation."""
        if self.handle_key_press_validation(event):
            super().keyPressEvent(event)

    def insertFromMimeData(self, source) -> None:
        """Handle paste operations with validation and cleaning."""
        try:
            if source.hasText():
                original_text = source.text()
                cleaned_text = self.handle_paste_validation(original_text)

                # Insert the cleaned text
                self.insert(cleaned_text)
            else:
                super().insertFromMimeData(source)

        except Exception as e:
            logger.error("[MetadataValidatedLineEdit] Error in insertFromMimeData: %s", e)
            super().insertFromMimeData(source)

    def _on_text_changed(self, text: str) -> None:
        """Handle text changes and update validation state."""
        self.update_validation_state(text)

    def set_field_name(self, field_name: str) -> None:
        """Set the field name and update validation rules.

        Args:
            field_name: Name of the metadata field

        """
        self._field_name = field_name
        self._setup_field_specific_properties()

        # Re-validate current text with new rules
        self.update_validation_state(self.text())


class MetadataValidatedTextEdit(QTextEdit, BaseValidatedInput):
    """Multi-line input widget for description and other long text fields.

    Features:
    - Multi-line text support
    - Length validation with character counting
    - Visual feedback for content state
    - Paste content cleaning (if needed)
    """

    # Signal emitted when validation state changes
    validation_changed = pyqtSignal(bool)  # True if valid, False if invalid

    def __init__(self, field_name: str = "", parent: QWidget | None = None):
        QTextEdit.__init__(self, parent)
        BaseValidatedInput.__init__(self)

        self._field_name = field_name
        self._max_length_override = 0
        self._setup_field_specific_properties()

    def _setup_validation_signals(self) -> None:
        """Setup internal signal connections."""
        self.textChanged.connect(self._on_text_changed)

    def emit_validation_changed(self, is_valid: bool) -> None:
        """Emit validation changed signal."""
        self.validation_changed.emit(is_valid)

    def _setup_field_specific_properties(self) -> None:
        """Setup field-specific properties like max length."""
        if self._field_name:
            max_length = self._get_field_max_length()
            if max_length > 0:
                self._max_length_override = max_length

    def _get_field_max_length(self) -> int:
        """Get maximum length for the current field."""
        field_limits = {
            "Description": MetadataFieldValidator.MAX_DESCRIPTION_LENGTH,
        }
        return field_limits.get(self._field_name, 0)

    def text(self) -> str:
        """Get current text content."""
        return self.toPlainText()

    def setText(self, text: str) -> None:
        """Set text content."""
        self.setPlainText(text)

    def maxLength(self) -> int:
        """Get maximum length."""
        return self._max_length_override

    def get_blocked_characters(self) -> set[str]:
        """Get set of characters that should be blocked for this field.

        Returns:
            Set of characters to block (empty for text fields)

        """
        # Text fields generally don't block characters
        return set()

    def validate_text_content(self, text: str) -> tuple[bool, str]:
        """Validate text content using metadata field validators.

        Args:
            text: Text to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        if not self._field_name:
            return super().validate_text_content(text)

        # Use MetadataFieldValidator for validation
        return MetadataFieldValidator.validate_field(self._field_name, text)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events with validation."""
        if self.handle_key_press_validation(event):
            super().keyPressEvent(event)

    def insert(self, text: str) -> None:
        """Insert text at current cursor position."""
        cursor = self.textCursor()
        cursor.insertText(text)

    def insertFromMimeData(self, source) -> None:
        """Handle paste operations with validation and cleaning."""
        try:
            if source and source.hasText():
                original_text = source.text()
                cleaned_text = self.handle_paste_validation(original_text)

                # Insert the cleaned text at cursor position
                cursor = self.textCursor()
                cursor.insertText(cleaned_text)
            else:
                super().insertFromMimeData(source)

        except Exception as e:
            logger.error("[MetadataValidatedTextEdit] Error in insertFromMimeData: %s", e)
            super().insertFromMimeData(source)

    def _on_text_changed(self) -> None:
        """Handle text changes and update validation state."""
        self.update_validation_state(self.text())

    def set_field_name(self, field_name: str) -> None:
        """Set the field name and update validation rules.

        Args:
            field_name: Name of the metadata field

        """
        self._field_name = field_name
        self._setup_field_specific_properties()

        # Re-validate current text with new rules
        self.update_validation_state(self.text())


class MetadataRotationComboBox(QComboBox):
    """Specialized combo box for rotation values.

    Features:
    - Predefined rotation values (0°, 90°, 180°, 270°)
    - Automatic validation (always valid since values are predefined)
    - Compatible interface with other metadata input widgets
    """

    # Signal emitted when validation state changes (always True for combo box)
    validation_changed = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        # Setup rotation values
        self.rotation_values = ["0", "90", "180", "270"]
        self.rotation_labels = [
            "0° (No rotation)",
            "90° (Clockwise)",
            "180° (Upside down)",
            "270° (Counter-clockwise)",
        ]

        # Populate combo box
        for _i, (value, label) in enumerate(
            zip(self.rotation_values, self.rotation_labels, strict=False)
        ):
            self.addItem(label, value)

        # Set default to 0°
        self.setCurrentIndex(0)

        # Connect signals
        self.currentTextChanged.connect(self._on_selection_changed)

        # Set fixed height to match other input widgets
        from oncutf.core.theme_manager import get_theme_manager

        theme = get_theme_manager()
        self.setFixedHeight(theme.get_constant("combo_height"))  # Use theme constant

    def _on_selection_changed(self, _text: str) -> None:
        """Handle selection changes - always emit valid state."""
        self.validation_changed.emit(True)

    def text(self) -> str:
        """Get current rotation value as text."""
        return self.currentData() or "0"

    def setText(self, text: str) -> None:
        """Set rotation value from text."""
        # Clean the input - remove degree symbol and extra spaces
        clean_text = text.strip().replace("°", "").replace(" ", "")

        # Try to find matching value
        try:
            # Find the index of the matching rotation value
            if clean_text in self.rotation_values:
                index = self.rotation_values.index(clean_text)
                self.setCurrentIndex(index)
            else:
                # Try to parse as number and find closest match
                rotation_num = float(clean_text) % 360  # Normalize to 0-359

                # Find closest standard rotation
                closest_value = min(
                    self.rotation_values, key=lambda x: abs(float(x) - rotation_num)
                )
                index = self.rotation_values.index(closest_value)
                self.setCurrentIndex(index)

        except (ValueError, TypeError):
            # If parsing fails, default to 0°
            self.setCurrentIndex(0)

    def is_valid(self) -> bool:
        """Rotation combo box is always valid since values are predefined."""
        return True

    def get_validation_error_message(self) -> str:
        """No error messages for combo box since it's always valid."""
        return ""

    def setPlaceholderText(self, text: str) -> None:
        """Placeholder text not applicable for combo box."""
        # No-op for combo box

    def selectAll(self) -> None:
        """Select all not applicable for combo box."""
        # No-op for combo box


def create_metadata_input_widget(
    field_name: str, is_multiline: bool = False, parent: QWidget | None = None
):
    """Factory function to create appropriate metadata input widget.

    Args:
        field_name: Name of the metadata field
        is_multiline: Whether to create a multi-line widget
        parent: Parent widget

    Returns:
        MetadataValidatedLineEdit, MetadataValidatedTextEdit, or MetadataRotationComboBox

    """
    # Special case for Rotation field - use combo box
    if field_name == "Rotation":
        return MetadataRotationComboBox(parent)

    # Multi-line text fields
    if is_multiline:
        widget = MetadataValidatedTextEdit(field_name, parent)
        # Set reasonable size for text edit
        widget.setMaximumHeight(100)
        widget.setMinimumHeight(80)
    else:
        # Single-line text fields
        widget = MetadataValidatedLineEdit(field_name, parent)
        widget.setFixedHeight(20)

    return widget
