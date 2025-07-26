"""
Module: metadata_widget.py

Author: Michael Economou
Date: 2025-05-31

Widget for metadata selection (file dates or EXIF), with optimized signal emission system.
"""

import time
from typing import Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPalette, QStandardItem, QStandardItemModel
from core.pyqt_imports import QComboBox, QHBoxLayout, QLabel, QStyle, QVBoxLayout, QWidget
from utils.file_status_helpers import (
    batch_hash_status,
    batch_metadata_status,
)
from utils.logger_factory import get_cached_logger
from utils.metadata_field_validators import MetadataFieldValidator
from utils.theme_engine import ThemeEngine
from widgets.ui_delegates import ComboBoxItemDelegate
from widgets.hierarchical_combo_box import HierarchicalComboBox

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
            from utils.timer_manager import get_timer_manager, TimerType
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

        try:
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

            # Force preview update by clearing cache and emitting signal
            # This ensures preview is always updated when category changes
            try:
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
            except Exception as e:
                logger.warning(f"Error in category change preview update: {e}")
                # Fallback to basic preview update
                self.force_preview_update()

            logger.debug(f"Category change completed for: {current_data}")

        except Exception as e:
            logger.error(f"Error in _on_category_changed: {e}")

    def update_options(self) -> None:
        category = self.category_combo.currentData()
        self.options_combo.clear()

        logger.debug(f"update_options called with category: {category}")

        if category == "file_dates":
            self.options_label.setText("Type")
            self.populate_file_dates()
            # File dates are always enabled
            self.options_combo.setEnabled(True)
            # Apply normal styling
            self._apply_normal_combo_styling()
        elif category == "hash":
            self.options_label.setText("Type")
            # ALWAYS call populate_hash_options for hash checking (even when file selection changes)
            self.populate_hash_options()
            # Hash combo is managed by populate_hash_options
        elif category == "metadata_keys":
            self.options_label.setText("Field")
            self.populate_metadata_keys()
            # Metadata combo is managed by populate_metadata_keys
            # Apply normal styling if enabled
            if self.options_combo.isEnabled():
                self._apply_normal_combo_styling()

        # Set to first option by default (if exists)
        if hasattr(self.options_combo, "get_current_data"):
            # For hierarchical combo box, we don't need to set index
            # The first item will be automatically selected
            current_data = self.options_combo.get_current_data()
            logger.debug(f"Hierarchical combo current data: {current_data}")
        elif self.options_combo.count() > 0:
            self.options_combo.setCurrentIndex(0)
            logger.debug("Regular combo set to index 0")

        # Use timer to ensure currentData is updated before emitting
        try:
            from utils.timer_manager import get_timer_manager, TimerType
            timer_manager = get_timer_manager()
            timer_manager.schedule(
                self.emit_if_changed,
                delay=15,  # 15ms delay for UI update
                timer_type=TimerType.UI_UPDATE,
                timer_id="metadata_widget_options_update"
            )

            # Also force preview update to ensure it's always updated
            timer_manager.schedule(
                self._force_preview_update_with_cache_clear,
                delay=20,  # 20ms delay for preview update
                timer_type=TimerType.PREVIEW_UPDATE,
                timer_id="metadata_widget_preview_force_update"
            )
        except Exception:
            # Fallback for testing or when timer manager is not available
            self.emit_if_changed()
            self._force_preview_update_with_cache_clear()

    def populate_file_dates(self) -> None:
        # Prepare hierarchical data for file dates
        hierarchical_data = {
            "File Dates": [
                ("Last Modified (YYMMDD)", "last_modified_yymmdd"),
                ("Last Modified (YYYY-MM-DD)", "last_modified_iso"),
                ("Last Modified (DD-MM-YYYY)", "last_modified_eu"),
                ("Last Modified (MM-DD-YYYY)", "last_modified_us"),
                ("Last Modified (YYYY)", "last_modified_year"),
                ("Last Modified (YYYY-MM)", "last_modified_month"),
            ]
        }

        logger.debug(f"Populating file dates with data: {hierarchical_data}")

        # Populate the hierarchical combo box
        self.options_combo.populate_from_metadata_groups(hierarchical_data)
        logger.debug("Used hierarchical combo populate_from_metadata_groups for file dates")

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when file dates are populated
        try:
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
        except Exception as e:
            logger.warning(f"Error in populate_file_dates preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def populate_hash_options(self) -> bool:
        """Populate hash options with efficient batch hash checking."""
        self.options_combo.clear()

        try:
            # Get selected files
            selected_files = self._get_selected_files()

            if not selected_files:
                # No files selected - disable hash option
                hierarchical_data = {
                    "Hash Types": [
                        ("CRC32", "hash_crc32"),
                    ]
                }

                logger.debug("No files selected, populating disabled hash options")

                self.options_combo.populate_from_metadata_groups(hierarchical_data)

                # Disable the combo box
                self.options_combo.setEnabled(False)
                # Apply disabled styling to show text in gray
                self._apply_disabled_combo_styling()
                return False

            # Use efficient batch checking via database
            file_paths = [file_item.full_path for file_item in selected_files]

            # Get files that have hashes using batch query
            from core.persistent_hash_cache import get_persistent_hash_cache

            hash_cache = get_persistent_hash_cache()

            # Use batch method for efficiency
            files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, "CRC32")
            files_needing_hash = [path for path in file_paths if path not in files_with_hash]

            # Always add CRC32 option (only hash type supported) - but always disabled
            hierarchical_data = {
                "Hash Types": [
                    ("CRC32", "hash_crc32"),
                ]
            }

            logger.debug(
                f"Populating hash options: {len(files_with_hash)}/{len(file_paths)} files have hash"
            )

            self.options_combo.populate_from_metadata_groups(hierarchical_data)

            # Always disabled combo box for hash (only CRC32 available)
            self.options_combo.setEnabled(False)
            # Apply disabled styling to show text in gray
            self._apply_disabled_combo_styling()

            if files_needing_hash:
                # Some files need hash calculation
                return True
            else:
                # All files have hashes - but combo still disabled
                return True

        except Exception as e:
            logger.error(f"[MetadataWidget] Error in populate_hash_options: {e}")
            # On error, disable hash option
            hierarchical_data = {
                "Hash Types": [
                    ("CRC32", "hash_crc32"),
                ]
            }

            self.options_combo.populate_from_metadata_groups(hierarchical_data)
            self.options_combo.setEnabled(False)
            self._apply_disabled_combo_styling()
            return False

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when hash options are populated
        try:
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
        except Exception as e:
            logger.warning(f"Error in populate_hash_options preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _get_selected_files(self):
        """Get selected files from the main window."""
        try:
            # Try to get from parent window first
            if self.parent_window and hasattr(self.parent_window, "get_selected_files"):
                return self.parent_window.get_selected_files()

            # Fallback to ApplicationContext
            context = self._get_app_context()
            if context and hasattr(context, "get_selected_files"):
                return context.get_selected_files()

            # Final fallback - empty list
            logger.warning("[MetadataWidget] Could not get selected files")
            return []

        except Exception as e:
            logger.error(f"[MetadataWidget] Error getting selected files: {e}")
            return []

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when selected files are retrieved
        try:
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
        except Exception as e:
            logger.warning(f"Error in _get_selected_files preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _calculate_hashes_for_files(self, files_needing_hash):
        """Calculate hashes for the given file paths."""
        try:
            # Convert file paths back to FileItem objects for hash calculation
            selected_files = self._get_selected_files()
            file_items_needing_hash = []

            for file_path in files_needing_hash:
                for file_item in selected_files:
                    if file_item.full_path == file_path:
                        file_items_needing_hash.append(file_item)
                        break

            if not file_items_needing_hash:
                logger.warning("[MetadataWidget] No file items found for hash calculation")
                return

            # Get main window for hash calculation
            main_window = None
            if self.parent_window and hasattr(self.parent_window, "main_window"):
                main_window = self.parent_window.main_window
            elif self.parent_window:
                main_window = self.parent_window
            else:
                context = self._get_app_context()
                if context and hasattr(context, "main_window"):
                    main_window = context.main_window

            if main_window and hasattr(main_window, "event_handler_manager"):
                # Use the existing hash calculation method
                main_window.event_handler_manager._handle_calculate_hashes(file_items_needing_hash)

                # Force preview update after hash calculation
                try:
                    from utils.timer_manager import get_timer_manager, TimerType
                    timer_manager = get_timer_manager()
                    timer_manager.schedule(
                        self.force_preview_update,
                        delay=100,  # Small delay to ensure hash calculation completes
                        timer_type=TimerType.PREVIEW_UPDATE,
                        timer_id="metadata_widget_hash_preview_update"
                    )
                except ImportError:
                    # Fallback to immediate call if timer manager not available
                    self.force_preview_update()
                self._hash_dialog_active = False  # <-- Ensure flag reset after calculation
            else:
                logger.error("[MetadataWidget] Could not find main window for hash calculation")
                self._hash_dialog_active = False

        except Exception as e:
            logger.error(f"[MetadataWidget] Error calculating hashes: {e}")
            self._hash_dialog_active = False  # <-- Ensure flag reset on error

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when hashes are calculated
        try:
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
        except Exception as e:
            logger.warning(f"Error in _calculate_hashes_for_files preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

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

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when metadata keys are populated
        try:
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
        except Exception as e:
            logger.warning(f"Error in populate_metadata_keys preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

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

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when app context is retrieved
        try:
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
        except Exception as e:
            logger.warning(f"Error in _get_app_context preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _get_metadata_cache_via_context(self):
        try:
            context = self._get_app_context()
            if context and hasattr(context, "metadata_cache"):
                return context.metadata_cache
            return None
        except Exception as e:
            logger.warning(f"[MetadataWidget] Error getting metadata cache via context: {e}")
            return None

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when metadata cache is retrieved
        try:
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
        except Exception as e:
            logger.warning(f"Error in _get_metadata_cache_via_context preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def get_available_metadata_keys(self) -> set[str]:
        # Return cached keys if available
        if self._cached_metadata_keys is not None:
            return self._cached_metadata_keys

        # Get selected files
        selected_files = self._get_selected_files()
        if not selected_files:
            self._cached_metadata_keys = set()
            return self._cached_metadata_keys

        # Get metadata cache
        metadata_cache = self._get_metadata_cache_via_context()
        if not metadata_cache:
            self._cached_metadata_keys = set()
            return self._cached_metadata_keys

        # Collect all available keys from selected files
        all_keys = set()
        for file_item in selected_files:
            metadata = metadata_cache.get(file_item.full_path, {})
            if isinstance(metadata, dict):
                all_keys.update(metadata.keys())

        # Cache the result
        self._cached_metadata_keys = all_keys
        logger.debug(f"[MetadataWidget] Found {len(all_keys)} metadata keys", extra={"dev_only": True})

        return all_keys

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when metadata keys are retrieved
        try:
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
        except Exception as e:
            logger.warning(f"Error in get_available_metadata_keys preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

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

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when metadata key names are formatted
        try:
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
        except Exception as e:
            logger.warning(f"Error in format_metadata_key_name preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

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

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when field names are formatted
        try:
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
        except Exception as e:
            logger.warning(f"Error in _format_field_name preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _format_camel_case(self, text: str) -> str:
        """Format camelCase text by adding spaces before capitals."""
        import re

        # Add space before capital letters, but not at the beginning
        formatted = re.sub(r"(?<!^)(?=[A-Z])", " ", text)
        return formatted.title()

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when camel case text is formatted
        try:
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
        except Exception as e:
            logger.warning(f"Error in _format_camel_case preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

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

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when data is retrieved
        try:
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
        except Exception as e:
            logger.warning(f"Error in get_data preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

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

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when data changes
        try:
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
        except Exception as e:
            logger.warning(f"Error in emit_if_changed preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def force_preview_update(self) -> None:
        """Force preview update even if data hasn't changed (for hash calculation)."""
        self.update_options()
        self.emit_if_changed()
        self.updated.emit(self)
        logger.debug(
            "[MetadataWidget] Forced preview update with options refresh and emit_if_changed",
            extra={"dev_only": True},
        )

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when forced preview update is called
        try:
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
        except Exception as e:
            logger.warning(f"Error in force_preview_update preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _force_preview_update_with_cache_clear(self) -> None:
        """Force preview update with cache clearing to ensure it's always updated."""
        try:
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
        except Exception as e:
            logger.warning(f"Error in _force_preview_update_with_cache_clear: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when cache clearing preview update is called
        try:
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
        except Exception as e:
            logger.warning(f"Error in _force_preview_update_with_cache_clear preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def clear_cache(self) -> None:
        """Clear the metadata keys cache to force refresh."""
        self._cached_metadata_keys = None

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when cache is cleared
        try:
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
        except Exception as e:
            logger.warning(f"Error in clear_cache preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

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

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when metadata keys are refreshed
        try:
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
        except Exception as e:
            logger.warning(f"Error in refresh_metadata_keys preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when metadata keys are refreshed
        try:
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
        except Exception as e:
            logger.warning(f"Error in refresh_metadata_keys preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    @staticmethod
    def is_effective(data: dict) -> bool:
        """
        The metadata module is effective if it has a valid field for the selected category.
        """
        field = data.get("field")
        category = data.get("category", "file_dates")

        # For hash category, check if field is a valid hash type
        if category == "hash":
            return field and field.startswith("hash_")

        # For other categories, any field is effective
        return bool(field)

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when effectiveness is checked
        try:
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
        except Exception as e:
            logger.warning(f"Error in is_effective preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _get_supported_hash_algorithms(self) -> set:
        """Get list of supported hash algorithms from the async operations manager."""
        # Only CRC32 is supported and implemented
        return {"CRC32"}

    def update_category_availability(self):
        """Update category combo box availability based on selected files."""
        # Ensure theme inheritance
        self._ensure_theme_inheritance()

        # Get selected files
        selected_files = self._get_selected_files()

        # Set up the model if not already done
        if not hasattr(self, "category_model"):
            self.category_model = QStandardItemModel()
            self.category_combo.setModel(self.category_model)

            # Add items to model
            item1 = QStandardItem("File Dates")
            item1.setData("file_dates", Qt.UserRole)
            self.category_model.appendRow(item1)

            item2 = QStandardItem("Hash")
            item2.setData("hash", Qt.UserRole)
            self.category_model.appendRow(item2)

            item3 = QStandardItem("EXIF/Metadata")
            item3.setData("metadata_keys", Qt.UserRole)
            self.category_model.appendRow(item3)

        # File Dates category is ALWAYS enabled
        file_dates_item = self.category_model.item(0)
        file_dates_item.setFlags(file_dates_item.flags() | Qt.ItemIsEnabled)
        file_dates_item.setForeground(QColor())  # Reset to default color

        if not selected_files:
            # Disable Hash and EXIF when no files are selected
            hash_item = self.category_model.item(1)
            metadata_item = self.category_model.item(2)

            hash_item.setFlags(hash_item.flags() & ~Qt.ItemIsEnabled)
            hash_item.setForeground(QColor("#888888"))

            metadata_item.setFlags(metadata_item.flags() & ~Qt.ItemIsEnabled)
            metadata_item.setForeground(QColor("#888888"))

            # Apply normal styling - disabled items will be gray via QAbstractItemView styling
            self._apply_category_styling()

            # If current category is hash and is disabled, apply disabled styling
            if self.category_combo.currentData() == "hash":
                self.options_combo.clear()
                hierarchical_data = {
                    "Hash Types": [
                        ("CRC32", "hash_crc32"),
                    ]
                }

                self.options_combo.populate_from_metadata_groups(hierarchical_data)

                self.options_combo.setEnabled(False)
                self._apply_disabled_combo_styling()

            logger.debug(
                "[MetadataWidget] No files selected - disabled Hash and EXIF options",
                extra={"dev_only": True},
            )
        else:
            # Check if files have hash data
            has_hash_data = self._check_files_have_hash(selected_files)
            hash_item = self.category_model.item(1)

            if has_hash_data:
                hash_item.setFlags(hash_item.flags() | Qt.ItemIsEnabled)
                hash_item.setForeground(QColor())  # Reset to default color
            else:
                hash_item.setFlags(hash_item.flags() & ~Qt.ItemIsEnabled)
                hash_item.setForeground(QColor("#888888"))

                # If current category is hash and is disabled, apply disabled styling
                if self.category_combo.currentData() == "hash":
                    self.options_combo.clear()
                    hierarchical_data = {
                        "Hash Types": [
                            ("CRC32", "hash_crc32"),
                        ]
                    }

                    self.options_combo.populate_from_metadata_groups(hierarchical_data)

                    self.options_combo.setEnabled(False)
                    self._apply_disabled_combo_styling()

            # Check if files have EXIF/metadata data
            has_metadata_data = self._check_files_have_metadata(selected_files)
            metadata_item = self.category_model.item(2)

            if has_metadata_data:
                metadata_item.setFlags(metadata_item.flags() | Qt.ItemIsEnabled)
                metadata_item.setForeground(QColor())  # Reset to default color
            else:
                metadata_item.setFlags(metadata_item.flags() & ~Qt.ItemIsEnabled)
                metadata_item.setForeground(QColor("#888888"))

            # Apply styling to category combo based on state
            self._apply_category_styling()

            logger.debug(
                f"[MetadataWidget] {len(selected_files)} files selected - Hash: {has_hash_data}, EXIF: {has_metadata_data}"
            )

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when category availability is updated
        try:
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
        except Exception as e:
            logger.warning(f"Error in update_category_availability preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _check_files_have_hash(self, selected_files) -> bool:
        """Check if any of the selected files have hash data."""
        if not selected_files:
            return False

        try:
            # Use efficient batch checking via database
            file_paths = [file_item.full_path for file_item in selected_files]

            # Get files that have hashes using batch query
            from core.persistent_hash_cache import get_persistent_hash_cache

            hash_cache = get_persistent_hash_cache()

            # Use batch method for efficiency
            files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, "CRC32")

            has_hash_data = len(files_with_hash) > 0
            logger.debug(
                f"[MetadataWidget] Hash check: {len(files_with_hash)}/{len(file_paths)} files have hash",
                extra={"dev_only": True},
            )

            return has_hash_data

        except Exception as e:
            logger.warning(f"[MetadataWidget] Error checking hash data: {e}")
            return False

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when hash data is checked
        try:
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
        except Exception as e:
            logger.warning(f"Error in _check_files_have_hash preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _check_files_have_metadata(self, selected_files) -> bool:
        """Check if any of the selected files have metadata."""
        try:
            file_paths = [file_item.full_path for file_item in selected_files]
            return any(batch_metadata_status(file_paths).values())
        except Exception as e:
            logger.error(f"[MetadataWidget] Error checking metadata availability: {e}")
            return False

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when metadata data is checked
        try:
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
        except Exception as e:
            logger.warning(f"Error in _check_files_have_metadata preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _ensure_theme_inheritance(self) -> None:
        """
        Ensure that child widgets inherit theme styles properly.
        This is needed because child widgets sometimes don't inherit
        the global application stylesheet correctly.
        """
        try:
            # Apply minimal styles to combo boxes
            # Note: Detailed styling is handled by ComboBoxItemDelegate
            pass

        except Exception as e:
            logger.warning(f"[MetadataWidget] Failed to ensure theme inheritance: {e}")

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when theme inheritance is ensured
        try:
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
        except Exception as e:
            logger.warning(f"Error in _ensure_theme_inheritance preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def trigger_update_options(self):
        """Trigger options update with debouncing."""
        try:
            from utils.timer_manager import get_timer_manager, TimerType
            timer_manager = get_timer_manager()
            timer_manager.schedule(
                self._debounced_update_options,
                delay=50,  # 50ms delay for debouncing
                timer_type=TimerType.UI_UPDATE,
                timer_id="metadata_widget_trigger_update"
            )
        except Exception:
            # Fallback for testing or when timer manager is not available
            self._debounced_update_options()

    def _debounced_update_options(self):
        """Debounced options update."""
        self.update_options()

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when options are triggered
        try:
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
        except Exception as e:
            logger.warning(f"Error in _debounced_update_options preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _check_calculation_requirements(self, category: str):
        """Check if calculation dialog is needed for the selected category."""
        selected_files = self._get_selected_files()

        if category == "hash":
            self._check_hash_calculation_requirements(selected_files)
        elif category == "metadata_keys":
            self._check_metadata_calculation_requirements(selected_files)

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when calculation requirements are checked
        try:
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
        except Exception as e:
            logger.warning(f"Error in _check_calculation_requirements preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _check_hash_calculation_requirements(self, selected_files):
        """Check if hash calculation dialog is needed."""
        if self._hash_dialog_active:
            logger.debug(
                "[MetadataWidget] Hash dialog already active, skipping check", extra={"dev_only": True}
            )
            return

        try:
            if not selected_files:
                logger.debug(
                    "[MetadataWidget] No files selected, no hash dialog needed", extra={"dev_only": True}
                )
                return

            # Use efficient batch checking via database
            file_paths = [file_item.full_path for file_item in selected_files]

            # Get files that have hashes using batch query
            from core.persistent_hash_cache import get_persistent_hash_cache

            hash_cache = get_persistent_hash_cache()

            # Use batch method for efficiency
            files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, "CRC32")
            files_needing_hash = [path for path in file_paths if path not in files_with_hash]

            if files_needing_hash:
                # Some files need hash calculation
                self._show_calculation_dialog(files_needing_hash, "hash")

        except Exception as e:
            logger.error(f"[MetadataWidget] Error checking hash calculation requirements: {e}")
            self._hash_dialog_active = False

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when hash calculation requirements are checked
        try:
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
        except Exception as e:
            logger.warning(f"Error in _check_hash_calculation_requirements preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _check_metadata_calculation_requirements(self, selected_files):
        """Check if metadata calculation dialog is needed."""
        if self._hash_dialog_active:
            logger.debug(
                "[MetadataWidget] Metadata dialog already active, skipping check", extra={"dev_only": True}
            )
            return

        try:
            if not selected_files:
                logger.debug(
                    "[MetadataWidget] No files selected, no metadata dialog needed", extra={"dev_only": True}
                )
                return

            # Use efficient batch checking via database
            file_paths = [file_item.full_path for file_item in selected_files]

            # Get files that have metadata using batch query
            from utils.metadata_cache_helper import get_metadata_cache_helper

            cache_helper = get_metadata_cache_helper(parent_window=self.parent_window)

            # Use batch method for efficiency
            files_with_metadata = cache_helper.get_files_with_metadata_batch(file_paths)
            files_needing_metadata = [path for path in file_paths if path not in files_with_metadata]

            if files_needing_metadata:
                # Some files need metadata calculation
                self._show_calculation_dialog(files_needing_metadata, "metadata")

        except Exception as e:
            logger.error(f"[MetadataWidget] Error checking metadata calculation requirements: {e}")
            self._hash_dialog_active = False

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when metadata calculation requirements are checked
        try:
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
        except Exception as e:
            logger.warning(f"Error in _check_metadata_calculation_requirements preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _show_calculation_dialog(self, files_needing_calculation, calculation_type: str):
        """Show calculation dialog for files that need hash or metadata calculation."""
        if self._hash_dialog_active:
            logger.debug(
                "[MetadataWidget] Dialog already active, skipping", extra={"dev_only": True}
            )
            return

        self._hash_dialog_active = True

        try:
            from utils.custom_message_dialog import CustomMessageDialog

            # Create dialog
            dialog = CustomMessageDialog(
                title="Calculation Required",
                message=f"Some files need {calculation_type} calculation to use this feature.",
                detailed_text=f"{len(files_needing_calculation)} files need {calculation_type} calculation.\n\nWould you like to calculate {calculation_type} for these files now?",
                icon="info",
                buttons=["Calculate", "Cancel"],
                default_button="Calculate",
                parent=self.parent_window,
            )

            # Show dialog
            result = dialog.exec_()

            if result == 0:  # Calculate button clicked
                if calculation_type == "hash":
                    self._calculate_hashes_for_files(files_needing_calculation)
                elif calculation_type == "metadata":
                    self._load_metadata_for_files(files_needing_calculation)
            else:
                # User cancelled - reset flag
                self._hash_dialog_active = False

        except Exception as e:
            logger.error(f"[MetadataWidget] Error showing calculation dialog: {e}")
            self._hash_dialog_active = False

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when calculation dialog is shown
        try:
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
        except Exception as e:
            logger.warning(f"Error in _show_calculation_dialog preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _load_metadata_for_files(self, files_needing_metadata):
        """Load metadata for the given file paths."""
        try:
            # Get main window reference
            main_window = None
            if self.parent_window:
                main_window = self.parent_window
            else:
                context = self._get_app_context()
                if context and hasattr(context, "main_window"):
                    main_window = context.main_window

            if main_window and hasattr(main_window, "load_metadata_for_items"):
                # Use the existing metadata loading method
                main_window.load_metadata_for_items(
                    files_needing_metadata, use_extended=False, source="metadata_widget"
                )

                # Force preview update after metadata loading
                try:
                    from utils.timer_manager import get_timer_manager, TimerType
                    timer_manager = get_timer_manager()
                    timer_manager.schedule(
                        self.force_preview_update,
                        delay=100,  # Small delay to ensure metadata loading completes
                        timer_type=TimerType.PREVIEW_UPDATE,
                        timer_id="metadata_widget_metadata_preview_update"
                    )
                except ImportError:
                    # Fallback to immediate call if timer manager not available
                    self.force_preview_update()
                self._hash_dialog_active = False
                logger.debug(
                    "[MetadataWidget] Metadata loading completed, preview update scheduled",
                    extra={"dev_only": True},
                )
            else:
                logger.error("[MetadataWidget] Could not find main window for metadata loading")
                self._hash_dialog_active = False

        except Exception as e:
            logger.error(f"[MetadataWidget] Error loading metadata: {e}")
            self._hash_dialog_active = False

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when metadata is loaded
        try:
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
        except Exception as e:
            logger.warning(f"Error in _load_metadata_for_files preview update: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _apply_disabled_combo_styling(self):
        """Apply disabled styling to the options combo box to show gray text"""
        try:
            from utils.theme_engine import ThemeEngine

            theme = ThemeEngine()

            # Apply simplified styling - dropdown styling handled by delegate
            disabled_css = f"""
                QComboBox {{
                    color: {theme.get_color("disabled_text")} !important;
                    background-color: {theme.get_color("combo_background")};
                    border: 1px solid {theme.get_color("combo_border")};
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-family: "{theme.fonts["base_family"]}", "Segoe UI", Arial, sans-serif;
                    font-size: {theme.fonts["interface_size"]};
                    min-height: 18px;
                }}

                QComboBox:disabled {{
                    color: {theme.get_color("disabled_text")} !important;
                    background-color: {theme.get_color("combo_background")};
                    border: 1px solid {theme.get_color("combo_border")};
                }}

                QComboBox::drop-down {{
                    border: none;
                    background-color: transparent;
                    width: 18px;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}
            """

            self.options_combo.setStyleSheet(disabled_css)
            self.options_combo.view().setStyleSheet(disabled_css)
            logger.debug(
                "[MetadataWidget] Applied disabled styling to hash combo", extra={"dev_only": True}
            )

        except Exception as e:
            logger.warning(f"[MetadataWidget] Error applying disabled combo styling: {e}")

    def _apply_normal_combo_styling(self):
        """Apply normal styling to the options combo box"""
        try:
            from utils.theme_engine import ThemeEngine

            theme = ThemeEngine()

            # Apply simplified styling - dropdown styling handled by delegate
            normal_css = f"""
                QComboBox {{
                    background-color: {theme.get_color("combo_background")};
                    border: 1px solid {theme.get_color("combo_border")};
                    border-radius: 4px;
                    padding: 2px 6px;
                    color: {theme.get_color("combo_text")};
                    font-family: "{theme.fonts["base_family"]}", "Segoe UI", Arial, sans-serif;
                    font-size: {theme.fonts["interface_size"]};
                    min-height: 18px;
                    selection-background-color: {theme.get_color("combo_item_background_selected")};
                    selection-color: {theme.get_color("input_selection_text")};
                }}

                QComboBox:hover {{
                    background-color: {theme.get_color("combo_background_hover")};
                    border-color: {theme.get_color("input_border_hover")};
                    color: {theme.get_color("combo_text")};
                }}

                QComboBox:focus {{
                    border-color: {theme.get_color("input_border_focus")};
                    background-color: {theme.get_color("combo_background_hover")};
                    color: {theme.get_color("combo_text")};
                }}

                QComboBox:focus:hover {{
                    background-color: {theme.get_color("combo_background_pressed")};
                    color: {theme.get_color("combo_text_pressed")};
                }}

                QComboBox:on {{
                    background-color: {theme.get_color("combo_background_pressed")};
                    color: {theme.get_color("combo_text_pressed")};
                    border-color: {theme.get_color("input_border_focus")};
                }}

                QComboBox::drop-down {{
                    border: none;
                    background-color: transparent;
                    width: 18px;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}
            """

            self.options_combo.setStyleSheet(normal_css)
            self.options_combo.view().setStyleSheet(normal_css)
            logger.debug(
                "[MetadataWidget] Applied normal styling to options combo", extra={"dev_only": True}
            )

        except Exception as e:
            logger.warning(f"[MetadataWidget] Error applying normal combo styling: {e}")

    def _apply_combo_theme_styling(self):
        """Apply theme styling to combo boxes and ensure inheritance"""
        try:
            theme = ThemeEngine()
            logger.debug(
                "[MetadataWidget] Theme inheritance ensured for combo boxes",
                extra={"dev_only": True},
            )

            css = f"""
                QComboBox {{
                    background-color: {theme.get_color("input_background")};
                    border: 1px solid {theme.get_color("input_border")};
                    border-radius: 4px;
                    padding: 6px 8px;
                    color: {theme.get_color("input_text")};
                    font-size: 12px;
                    min-height: 20px;
                    selection-background-color: {theme.get_color("input_selection_background")};
                    selection-color: {theme.get_color("input_selection_text")};
                }}

                QComboBox:hover {{
                    border-color: {theme.get_color("input_border_hover")};
                }}

                QComboBox:focus {{
                    border-color: {theme.get_color("input_border_focus")};
                }}

                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}

                /* Custom styling for disabled items in custom model */
                QComboBox QAbstractItemView::item {{
                    background-color: transparent;
                    color: {theme.get_color("combo_text")};
                    padding: 6px 8px;
                    border: none;
                    min-height: 18px;
                    border-radius: 3px;
                    margin: 1px;
                }}

                QComboBox QAbstractItemView::item:hover {{
                    background-color: {theme.get_color("combo_item_background_hover")};
                    color: {theme.get_color("combo_text")};
                }}

                QComboBox QAbstractItemView::item:selected {{
                    background-color: {theme.get_color("combo_item_background_selected")};
                    color: {theme.get_color("input_selection_text")};
                }}

                /* Force grayout for items without ItemIsEnabled flag */
                QComboBox QAbstractItemView::item:!enabled {{
                    background-color: transparent !important;
                    color: {theme.get_color("disabled_text")} !important;
                    opacity: 0.6 !important;
                }}

                QComboBox QAbstractItemView::item:!enabled:hover {{
                    background-color: transparent !important;
                    color: {theme.get_color("disabled_text")} !important;
                }}
            """

            self.category_combo.setStyleSheet(css)

            # Apply style recursively to ensure inheritance
            # apply_style_recursively(self.category_combo, self.category_combo.style()) # This line was removed

        except Exception as e:
            logger.error(f"[MetadataWidget] Error applying combo theme styling: {e}")

    def _apply_disabled_category_styling(self):
        """Apply disabled styling to the category combo box to show gray text"""
        try:
            from utils.theme_engine import ThemeEngine

            theme = ThemeEngine()

            # Apply simplified styling - dropdown styling handled by delegate
            disabled_css = f"""
                QComboBox {{
                    color: {theme.get_color("disabled_text")} !important;
                    background-color: {theme.get_color("combo_background")};
                    border: 1px solid {theme.get_color("combo_border")};
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-family: "{theme.fonts["base_family"]}", "Segoe UI", Arial, sans-serif;
                    font-size: {theme.fonts["interface_size"]};
                    min-height: 18px;
                }}

                QComboBox:disabled {{
                    color: {theme.get_color("disabled_text")} !important;
                    background-color: {theme.get_color("combo_background")};
                    border: 1px solid {theme.get_color("combo_border")};
                }}

                QComboBox::drop-down {{
                    border: none;
                    background-color: transparent;
                    width: 18px;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}
            """

            self.category_combo.setStyleSheet(disabled_css)
            self.category_combo.view().setStyleSheet(disabled_css)
            logger.debug(
                "[MetadataWidget] Applied disabled styling to category combo",
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.warning(f"[MetadataWidget] Error applying disabled category styling: {e}")

    def _apply_category_styling(self):
        """Apply normal styling to the category combo box"""
        try:
            from utils.theme_engine import ThemeEngine

            theme = ThemeEngine()

            # Apply simplified styling - dropdown styling handled by delegate
            normal_css = f"""
                QComboBox {{
                    background-color: {theme.get_color("combo_background")};
                    border: 1px solid {theme.get_color("combo_border")};
                    border-radius: 4px;
                    padding: 2px 6px;
                    color: {theme.get_color("combo_text")};
                    font-family: "{theme.fonts["base_family"]}", "Segoe UI", Arial, sans-serif;
                    font-size: {theme.fonts["interface_size"]};
                    min-height: 18px;
                    selection-background-color: {theme.get_color("combo_item_background_selected")};
                    selection-color: {theme.get_color("input_selection_text")};
                }}

                QComboBox:hover {{
                    background-color: {theme.get_color("combo_background_hover")};
                    border-color: {theme.get_color("input_border_hover")};
                    color: {theme.get_color("combo_text")};
                }}

                QComboBox:focus {{
                    border-color: {theme.get_color("input_border_focus")};
                    background-color: {theme.get_color("combo_background_hover")};
                    color: {theme.get_color("combo_text")};
                }}

                QComboBox:focus:hover {{
                    background-color: {theme.get_color("combo_background_pressed")};
                    color: {theme.get_color("combo_text_pressed")};
                }}

                QComboBox:on {{
                    background-color: {theme.get_color("combo_background_pressed")};
                    color: {theme.get_color("combo_text_pressed")};
                    border-color: {theme.get_color("input_border_focus")};
                }}

                QComboBox::drop-down {{
                    border: none;
                    background-color: transparent;
                    width: 18px;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}
            """

            self.category_combo.setStyleSheet(normal_css)
            self.category_combo.view().setStyleSheet(normal_css)

        except Exception as e:
            logger.warning(f"[MetadataWidget] Error applying normal category styling: {e}")

    def _on_hierarchical_item_selected(self, _text: str, _data: Any):
        """Handle item selection from hierarchical combo box."""
        # text and data are provided by the signal but not used here
        logger.debug(f"Hierarchical item selected: {_text} with data: {_data}")

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when selection changes
        try:
            # Clear any preview caches to force regeneration
            if self.parent_window and hasattr(self.parent_window, "utility_manager"):
                self.parent_window.utility_manager.clear_preview_cache()

            # Also clear unified rename engine cache if available
            if self.parent_window and hasattr(self.parent_window, "unified_rename_engine"):
                self.parent_window.unified_rename_engine.clear_cache()

            # Force preview update through main window
            if self.parent_window and hasattr(self.parent_window, "request_preview_update"):
                self.parent_window.request_preview_update()

            # Use global timer manager to delay the emit_if_changed call
            # This prevents rapid successive calls and ensures proper preview update
            from utils.timer_manager import get_timer_manager, TimerType
            timer_manager = get_timer_manager()
            timer_manager.schedule(
                self.emit_if_changed,
                delay=25,  # 25ms delay for smooth preview update
                timer_type=TimerType.PREVIEW_UPDATE,
                timer_id="metadata_widget_preview_update"
            )
        except ImportError:
            # Fallback to immediate call if timer manager not available
            self.emit_if_changed()

    def _on_selection_changed(self):
        """Handle selection change - update options and force preview update."""
        self.update_options()

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when file selection changes
        try:
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
        except Exception as e:
            logger.warning(f"Error in _on_selection_changed: {e}")
            # Fallback to basic preview update
            self.force_preview_update()

    def _on_metadata_loaded(self):
        """Handle metadata loading completion - update options and force preview update."""
        self.update_options()

        # Force preview update by clearing cache and emitting signal
        # This ensures preview is always updated when metadata is loaded
        try:
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
        except Exception as e:
            logger.warning(f"Error in _on_metadata_loaded: {e}")
            # Fallback to basic preview update
            self.force_preview_update()
