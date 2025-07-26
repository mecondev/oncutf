"""
Module: metadata_widget.py

Author: Michael Economou
Date: 2025-05-31

Widget for metadata selection (file dates or EXIF), with optimized signal emission system.
"""

import time

from PyQt5.QtCore import Qt, pyqtSignal

from core.pyqt_imports import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from utils.logger_factory import get_cached_logger
from utils.theme_engine import ThemeEngine
from widgets.hierarchical_combo_box import HierarchicalComboBox
from widgets.ui_delegates import ComboBoxItemDelegate

# ApplicationContext integration
try:
    from core.application_context import get_app_context
except ImportError:
    get_app_context = None

logger = get_cached_logger(__name__)



class MetadataWidget(QWidget):
    """
    Widget for file metadata selection (file dates or EXIF).
    Supports category selection and dynamic fields,
    and emits update signal only when there is an actual change.
    """

    updated = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None, parent_window: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parent_window = parent_window

        # Initialize data tracking
        self._last_data = None
        self._last_category = None

        # Debounce mechanism for emit_if_changed
        self._last_emit_time = 0
        self._emit_debounce_delay = 50  # 50ms debounce delay

        # Hash dialog tracking
        self._hash_dialog_active = False

        # Cache for metadata keys
        self._cached_metadata_keys = None

        # Setup UI
        self.setup_ui()

        # Ensure theme inheritance for child widgets
        self._ensure_theme_inheritance()

    def setup_ui(self) -> None:
        """Setup the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # Reduced from 8px to match text_removal_module

        # Row 1: Category
        category_row = QHBoxLayout()
        category_row.setContentsMargins(0, 0, 0, 0)
        category_row.setSpacing(8)
        category_label = QLabel("Category")
        category_label.setFixedWidth(70)
        category_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore

        self.category_combo = QComboBox()
        self.category_combo.setFixedWidth(150)
        self.category_combo.setFixedHeight(24)

        category_row.addWidget(category_label)
        category_row.addWidget(self.category_combo)
        category_row.addStretch()
        layout.addLayout(category_row)

        # Row 2: Field
        options_row = QHBoxLayout()
        options_row.setContentsMargins(
            0, 0, 0, 0
        )  # Removed vertical margins to allow spacing control
        options_row.setSpacing(8)  # Match final transformer spacing between label and control
        self.options_label = QLabel("Field")  # Will be updated based on category
        self.options_label.setFixedWidth(70)  # Increased width by 10px
        self.options_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore

        # Use HierarchicalComboBox for better organization
        self.options_combo = HierarchicalComboBox()
        self.options_combo.setFixedWidth(200)  # Increased width for metadata field names
        self.options_combo.setFixedHeight(24)  # Increased to match theme engine better

        options_row.addWidget(self.options_label)
        options_row.addWidget(self.options_combo)
        options_row.addStretch()
        layout.addLayout(options_row)

        # Apply custom delegates for better dropdown styling
        theme = ThemeEngine()
        self.category_combo.setItemDelegate(ComboBoxItemDelegate(self.category_combo, theme))
        self.options_combo.setItemDelegate(ComboBoxItemDelegate(self.options_combo, theme))

        # Connections
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        # Connect to hierarchical combo box signal
        self.options_combo.item_selected.connect(self._on_hierarchical_item_selected)
        logger.debug("Connected to hierarchical combo item_selected signal")

        # Initialize category availability
        self.update_category_availability()

        # Schedule options update (only if timer manager is available)
        try:
            from utils.timer_manager import TimerType, get_timer_manager
            timer_manager = get_timer_manager()
            timer_manager.schedule(
                self.update_options,
                delay=0,  # Immediate execution
                timer_type=TimerType.UI_UPDATE,
                timer_id="metadata_widget_initial_setup"
            )
        except Exception:
            # Fallback for testing or when timer manager is not available
            self.update_options()

        self.setLayout(layout)
        logger.debug("MetadataWidget UI setup completed")

    def _on_category_changed(self) -> None:
        """
        Handle category combo box changes.
        Updates available options based on selected category.
        """
        current_data = self.category_combo.currentData()
        logger.debug(f"Category changed to: {current_data}")

        if current_data is None:
            self.category_combo.setCurrentIndex(0)
            return

        # Clear and update options
        self.options_combo.clear()
        self.update_options()

        # Enable combo box for metadata keys
        if current_data == "metadata_keys":
            self.options_combo.setEnabled(True)
            self._apply_normal_combo_styling()

        # Check calculation requirements
        if current_data in ["hash", "metadata_keys"]:
            self._check_calculation_requirements(current_data)

        # Force UI update
        self.options_combo.repaint()

    def _on_hierarchical_item_selected(self, text: str, user_data: object) -> None:
        """
        Handle hierarchical combo box item selection.
        Called when an item is selected from the hierarchical dropdown.
        """
        logger.debug(f"Hierarchical item selected: text='{text}', data={user_data}")

        # Emit change signal to update preview
        self.emit_if_changed()

    def populate_metadata_keys(self) -> None:
        """
        Populate the hierarchical combo box with available metadata keys.
        Keys are grouped by category for better organization.
        """
        keys = self.get_available_metadata_keys()
        self.options_combo.clear()

        # Log available keys for debugging
        logger.debug(f"Available metadata keys: {keys}")

        if not keys:
            hierarchical_data = {
                "No Metadata": [
                    ("(No metadata fields available)", None),
                ]
            }
            self.options_combo.populate_from_metadata_groups(hierarchical_data)
            logger.debug("No metadata keys available, showing placeholder")
            return

        # Group keys by category
        grouped_keys = self._group_metadata_keys(keys)
        logger.debug(f"Grouped keys: {grouped_keys}")

        # Build hierarchical data structure
        hierarchical_data = {}
        for category, category_keys in grouped_keys.items():
            if category_keys:  # Only add categories that have items
                hierarchical_data[category] = []
                for key in sorted(category_keys):
                    display_text = self.format_metadata_key_name(key)
                    hierarchical_data[category].append((display_text, key))
                    logger.debug(f"Added {display_text} -> {key} to {category}")

        # Populate combo box with grouped data
        self.options_combo.populate_from_metadata_groups(hierarchical_data)

        # Force update to ensure UI reflects changes
        self.emit_if_changed()

        # Enable the combo box
        self.options_combo.setEnabled(True)

        # Apply normal styling
        self._apply_normal_combo_styling()

        logger.debug(f"Populated metadata keys with {len(hierarchical_data)} categories")


    def _group_metadata_keys(self, keys: set[str]) -> dict[str, list[str]]:
        """Group metadata keys by category for better organization."""
        grouped = {}

        for key in keys:
            category = self._classify_metadata_key(key)
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(key)

        # Sort categories for consistent display order
        category_order = [
            "File Info",
            "Camera Settings",
            "Image Info",
            "Video Info",
            "Audio Info",
            "GPS & Location",
            "Technical Info",
            "Other",
        ]

        # Return ordered dictionary
        ordered_grouped = {}
        for category in category_order:
            if category in grouped:
                ordered_grouped[category] = grouped[category]

        return ordered_grouped

    def _classify_metadata_key(self, key: str) -> str:
        """Classify a metadata key into a category."""
        key_lower = key.lower()

        # File-related metadata
        if key_lower.startswith("file") or key_lower in {"rotation", "directory", "sourcefile"}:
            return "File Info"

        # Camera Settings - Critical for photography/videography
        if any(
            term in key_lower
            for term in [
                "iso",
                "aperture",
                "fnumber",
                "shutter",
                "exposure",
                "focal",
                "flash",
                "metering",
                "whitebalance",
                "gain",
                "lightvalue",
            ]
        ):
            return "Camera Settings"

        # GPS and Location
        if any(
            term in key_lower for term in ["gps", "location", "latitude", "longitude", "altitude"]
        ):
            return "GPS & Location"

        # Audio-related metadata
        if key_lower.startswith("audio") or key_lower in {
            "samplerate",
            "channelmode",
            "bitrate",
            "title",
            "album",
            "artist",
            "composer",
            "genre",
            "duration",
        }:
            return "Audio Info"

        # Image-specific metadata
        if (
            key_lower.startswith("image")
            or "sensor" in key_lower
            or any(
                term in key_lower for term in ["width", "height", "resolution", "dpi", "colorspace"]
            )
        ):
            return "Image Info"

        # Video-specific metadata
        if any(
            term in key_lower
            for term in [
                "video",
                "frame",
                "codec",
                "bitrate",
                "fps",
                "duration",
                "format",
                "avgbitrate",
                "maxbitrate",
                "videocodec",
            ]
        ):
            return "Video Info"

        # Technical/System
        if any(
            term in key_lower
            for term in ["version", "software", "firmware", "make", "model", "serial", "uuid", "id"]
        ):
            return "Technical Info"

        return "Other"

    def _get_app_context(self):
        """Get ApplicationContext with fallback to None."""
        if get_app_context is None:
            return None
        try:
            return get_app_context()
        except RuntimeError:
            # ApplicationContext not ready yet
            return None


    def format_metadata_key_name(self, key: str) -> str:
        """Format metadata key name for display."""
        # Remove common prefixes
        prefixes_to_remove = ["EXIF:", "XMP:", "IPTC:", "ICC_Profile:", "Composite:"]
        formatted_key = key
        for prefix in prefixes_to_remove:
            if formatted_key.startswith(prefix):
                formatted_key = formatted_key[len(prefix):]
                break

        # Apply field name formatting
        formatted_key = self._format_field_name(formatted_key)

        return formatted_key


    def _format_field_name(self, field: str) -> str:
        """Format field name for better readability."""
        # Handle underscore-separated fields
        if "_" in field:
            return field.replace("_", " ").title()

        # Handle camelCase fields
        if field != field.lower() and field != field.upper():
            return self._format_camel_case(field)

        # Handle all caps fields
        if field.isupper():
            return field.title()

        return field


    def _format_camel_case(self, text: str) -> str:
        """Format camelCase text by adding spaces before capitals."""
        import re

        # Add space before capital letters, but not at the beginning
        formatted = re.sub(r"(?<!^)(?=[A-Z])", " ", text)
        return formatted.title()


    def get_data(self) -> dict:
        """Returns the state for use in the rename system."""
        category = self.category_combo.currentData() or "file_dates"

        # Use the hierarchical combo box API
        if hasattr(self.options_combo, "get_current_data"):
            field = self.options_combo.get_current_data()
            logger.debug(f"get_data: Using hierarchical combo, field: {field}")
        else:
            # Fallback to regular QComboBox API
            field = self.options_combo.currentData()
            logger.debug(f"get_data: Using regular combo, field: {field}")

        # Set default field based on category
        if not field:
            if category == "file_dates":
                field = "last_modified_yymmdd"
            elif category == "hash":
                field = "hash_crc32"
            elif category == "metadata_keys":
                field = "last_modified_yymmdd"  # Fallback

        # For hash category, ensure we only return CRC32
        if category == "hash" and field:
            # Only CRC32 is supported, so ensure we return it
            if field != "hash_crc32":
                logger.warning(
                    f"[MetadataWidget] Hash algorithm '{field}' not supported, using CRC32"
                )
                field = "hash_crc32"

        # For metadata_keys category, ensure we don't return None field
        if category == "metadata_keys" and not field:
            # If no field is selected, try to get the first available metadata key
            available_keys = self.get_available_metadata_keys()
            if available_keys:
                field = sorted(available_keys)[0]
                logger.debug(
                    f"[MetadataWidget] No field selected, using first available key: {field}",
                    extra={"dev_only": True},
                )
            else:
                # If no metadata keys available, fallback to file dates
                category = "file_dates"
                field = "last_modified_yymmdd"
                logger.debug(
                    "[MetadataWidget] No metadata keys available, falling back to file dates",
                    extra={"dev_only": True},
                )

        # Validate the field using MetadataFieldValidator if applicable
        if category == "metadata_keys" and field:
            # For metadata keys, we can't use the standard validators since these are field names
            # But we can check if the field exists in available keys
            available_keys = self.get_available_metadata_keys()
            if field not in available_keys:
                logger.warning(
                    f"[MetadataWidget] Selected metadata field '{field}' not available, using first available key"
                )
                if available_keys:
                    field = sorted(available_keys)[0]
                else:
                    # Fallback to file dates if no metadata keys available
                    category = "file_dates"
                    field = "last_modified_yymmdd"

        result = {
            "type": "metadata",
            "category": category,
            "field": field,
        }

        logger.debug(f"get_data returning: {result}")
        return result


    def emit_if_changed(self) -> None:
        # Debounce mechanism to prevent rapid successive calls
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        if current_time - self._last_emit_time < self._emit_debounce_delay:
            logger.debug("emit_if_changed debounced - too soon after previous call", extra={"dev_only": True})
            return

        self._last_emit_time = current_time

        # Log current combo box state
        if hasattr(self.options_combo, "get_current_data"):
            current_text = self.options_combo.get_current_text()
            current_data = self.options_combo.get_current_data()
            current_index = -1  # Not applicable for hierarchical combo
        else:
            current_index = self.options_combo.currentIndex()
            current_text = self.options_combo.currentText()
            current_data = self.options_combo.currentData()
        logger.debug(
            f"[MetadataWidget] Current combo state - index: {current_index}, text: '{current_text}', data: {current_data}",
            extra={"dev_only": True},
        )

        new_data = self.get_data()

        if new_data != self._last_data:
            self._last_data = new_data
            logger.debug("[MetadataWidget] Data changed, emitting signal", extra={"dev_only": True})
            self.updated.emit(self)
        else:
            # If data is the same but category changed, still emit for preview update
            # This handles the case where user switches from file_dates to hash and back
            current_category = self.category_combo.currentData()
            if hasattr(self, "_last_category") and self._last_category != current_category:
                self._last_category = current_category
                logger.debug(
                    f"[MetadataWidget] Category changed to {current_category}, forcing preview update",
                    extra={"dev_only": True},
                )
                self.updated.emit(self)
            elif not hasattr(self, "_last_category"):
                self._last_category = current_category


    def force_preview_update(self) -> None:
        """Force preview update even if data hasn't changed (for hash calculation)."""
        self.update_options()
        # Don't call emit_if_changed() here to avoid infinite loop
        # Just emit the signal directly
        self.updated.emit(self)
        logger.debug(
            "[MetadataWidget] Forced preview update with options refresh",
            extra={"dev_only": True},
        )

    def _force_preview_update_with_cache_clear(self) -> None:
        """Force preview update with cache clearing to ensure it's always updated."""
        # Clear any preview caches to force regeneration
        if self.parent_window and hasattr(self.parent_window, "utility_manager"):
            self.parent_window.utility_manager.clear_preview_cache()

        # Also clear unified rename engine cache if available
        if self.parent_window and hasattr(self.parent_window, "unified_rename_engine"):
            self.parent_window.unified_rename_engine.clear_cache()

        # Force preview update through main window
        if self.parent_window and hasattr(self.parent_window, "request_preview_update"):
            self.parent_window.request_preview_update()

        self.force_preview_update()
        logger.debug(
            "[MetadataWidget] Forced preview update with cache clearing",
            extra={"dev_only": True},
        )

    def clear_cache(self) -> None:
        """Clear the metadata keys cache to force refresh."""
        self._cached_metadata_keys = None


    def refresh_metadata_keys(self) -> None:
        """Refresh metadata keys and update the combo box if currently showing metadata."""
        self.clear_cache()
        category = self.category_combo.currentData()
        if category == "metadata_keys":
            self.populate_metadata_keys()
            self.emit_if_changed()
        elif category == "hash":
            self.populate_hash_options()
            # The hash combo will remain disabled from populate_hash_options
            self.emit_if_changed()

    def update_category_availability(self) -> None:
        """Update the available categories in the category combo box."""
        logger.debug("Updating category availability")

        # Clear existing items
        self.category_combo.clear()

        # Add available categories
        self.category_combo.addItem("File Dates", "file_dates")
        self.category_combo.addItem("Hash (CRC32)", "hash")
        self.category_combo.addItem("Metadata Fields", "metadata_keys")

        # Set default to file dates
        self.category_combo.setCurrentIndex(0)

        logger.debug("Category availability updated")

    def update_options(self) -> None:
        """Update the options combo box based on the selected category."""
        category = self.category_combo.currentData()
        logger.debug(f"Updating options for category: {category}")

        if category == "file_dates":
            self._populate_file_date_options()
        elif category == "hash":
            self.populate_hash_options()
        elif category == "metadata_keys":
            self.populate_metadata_keys()
        else:
            # Default to file dates
            self._populate_file_date_options()

        logger.debug("Options updated")

    def _populate_file_date_options(self) -> None:
        """Populate options for file date category."""
        self.options_combo.clear()

        # Add file date options
        date_options = [
            ("Modified (YYMMDD)", "last_modified_yymmdd"),
            ("Modified (YYYYMMDD)", "last_modified_yyyymmdd"),
            ("Created (YYMMDD)", "created_yymmdd"),
            ("Created (YYYYMMDD)", "created_yyyymmdd"),
        ]

        for display_text, data in date_options:
            self.options_combo.addItem(display_text, data)

        # Enable the combo box
        self.options_combo.setEnabled(True)
        self._apply_normal_combo_styling()

    def populate_hash_options(self) -> None:
        """Populate options for hash category."""
        self.options_combo.clear()

        # Add only CRC32 hash option (as mentioned in get_data method)
        self.options_combo.addItem("CRC32", "hash_crc32")

        # Disable the combo box since there's only one option
        self.options_combo.setEnabled(False)

        logger.debug("Hash options populated (CRC32 only)")

    def get_available_metadata_keys(self) -> set[str]:
        """Get available metadata keys from the application context."""
        if self._cached_metadata_keys is not None:
            return self._cached_metadata_keys

        app_context = self._get_app_context()
        if app_context is None:
            logger.debug("ApplicationContext not available, returning empty metadata keys")
            self._cached_metadata_keys = set()
            return self._cached_metadata_keys

        try:
            # Get metadata keys from the application context
            metadata_keys = app_context.get_available_metadata_keys()
            self._cached_metadata_keys = set(metadata_keys) if metadata_keys else set()
            logger.debug(f"Retrieved {len(self._cached_metadata_keys)} metadata keys from ApplicationContext")
        except Exception as e:
            logger.warning(f"Error getting metadata keys: {e}")
            self._cached_metadata_keys = set()

        return self._cached_metadata_keys

    def _check_calculation_requirements(self, category: str) -> None:
        """Check if calculation is required for the selected category."""
        if category in ["hash", "metadata_keys"]:
            logger.debug(f"Category '{category}' requires calculation")
            # Could trigger calculation here if needed
            # For now, just log the requirement
        else:
            logger.debug(f"Category '{category}' does not require calculation")

    def _apply_normal_combo_styling(self) -> None:
        """Apply normal styling to the options combo box."""
        # Reset any disabled styling
        if hasattr(self.options_combo, 'setStyleSheet'):
            self.options_combo.setStyleSheet("")
        logger.debug("Applied normal combo styling")

    def _ensure_theme_inheritance(self) -> None:
        """Ensure child widgets inherit theme settings."""
        try:
            from utils.theme_engine import ThemeEngine
            theme = ThemeEngine()
            theme.apply_widget_theme(self)
            logger.debug("Theme inheritance ensured for MetadataWidget")
        except Exception as e:
            logger.debug(f"Could not apply theme inheritance: {e}")


