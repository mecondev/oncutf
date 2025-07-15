"""
Module: metadata_widget.py

Author: Michael Economou
Date: 2025-05-31

Widget for metadata selection (file dates or EXIF), with optimized signal emission system.
"""

from typing import Optional, Set

from core.persistent_metadata_cache import MetadataEntry
from core.pyqt_imports import QComboBox, QHBoxLayout, QLabel, Qt, QVBoxLayout, QWidget, pyqtSignal
from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_ui_update

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

    def __init__(
        self, parent: Optional[QWidget] = None, parent_window: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.parent_window = parent_window  # Keep for backward compatibility
        self.setProperty("module", True)
        self._last_data: Optional[dict] = None  # For change tracking
        self._cached_metadata_keys: Optional[Set[str]] = None  # Cache for metadata keys
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)  # Match final transformer margins
        layout.setSpacing(4)  # Set spacing to 4px

        # Row 1: Category
        category_row = QHBoxLayout()
        category_row.setContentsMargins(
            0, 0, 0, 0
        )  # Removed vertical margins to allow spacing control
        category_row.setSpacing(8)  # Match final transformer spacing between label and control
        category_label = QLabel("Category")
        category_label.setFixedWidth(70)  # Increased width by 10px
        category_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore
        self.category_combo = QComboBox()
        self.category_combo.addItem("File Dates", userData="file_dates")
        self.category_combo.addItem("EXIF/Metadata", userData="metadata_keys")
        self.category_combo.setFixedWidth(120)  # Reduced width by 10px
        self.category_combo.setFixedHeight(22)  # Match final transformer combo height
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
        options_label = QLabel("Field")
        options_label.setFixedWidth(70)  # Increased width by 10px
        options_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore
        self.options_combo = QComboBox()
        self.options_combo.setFixedWidth(120)  # Reduced width by 10px
        self.options_combo.setFixedHeight(22)  # Match final transformer combo height
        options_row.addWidget(options_label)
        options_row.addWidget(self.options_combo)
        options_row.addStretch()
        layout.addLayout(options_row)

        # Connections
        self.category_combo.currentIndexChanged.connect(self.update_options)
        self.options_combo.currentIndexChanged.connect(self.emit_if_changed)

        # Schedule options update
        schedule_ui_update(self.update_options, 0)

    def update_options(self) -> None:
        """Updates fields according to the selected category."""
        category = self.category_combo.currentData()
        logger.debug(f"[MetadataWidget] Updating options for category: {category}")
        self.options_combo.clear()

        if category == "file_dates":
            self.populate_file_dates()
        elif category == "metadata_keys":
            self.populate_metadata_keys()

        self.emit_if_changed()

    def populate_file_dates(self) -> None:
        file_date_options = [
            ("Last Modified (YYMMDD)", "last_modified_yymmdd"),
            ("Last Modified (YYYY-MM-DD)", "last_modified_iso"),
            ("Last Modified (DD-MM-YYYY)", "last_modified_eu"),
            ("Last Modified (MM-DD-YYYY)", "last_modified_us"),
            ("Last Modified (YYYY)", "last_modified_year"),
            ("Last Modified (YYYY-MM)", "last_modified_month"),
        ]
        for label, val in file_date_options:
            self.options_combo.addItem(label, userData=val)

    def populate_metadata_keys(self) -> None:
        keys = self.get_available_metadata_keys()
        if not keys:
            # Check if metadata cache exists but is empty vs not loaded
            metadata_cache = self._get_metadata_cache_via_context()
            if (
                metadata_cache
                and hasattr(metadata_cache, "_memory_cache")
                and metadata_cache._memory_cache
            ):
                self.options_combo.addItem("(No metadata found in files)", userData=None)
            else:
                self.options_combo.addItem("(No metadata loaded)", userData=None)
            return

        # Add hash options first
        self.options_combo.addItem("CRC32 Hash", userData="hash_crc32")
        self.options_combo.addItem("MD5 Hash", userData="hash_md5")
        self.options_combo.addItem("SHA1 Hash", userData="hash_sha1")
        self.options_combo.addItem("SHA256 Hash", userData="hash_sha256")

        # Add separator
        self.options_combo.addItem("─" * 20, userData=None)

        # Add metadata keys
        for key in sorted(keys):
            display = self.format_metadata_key_name(key)
            self.options_combo.addItem(display, userData=key)

    def _get_app_context(self):
        """Get ApplicationContext with fallback to None."""
        if get_app_context is None:
            return None
        try:
            return get_app_context()
        except RuntimeError:
            # ApplicationContext not ready yet
            return None

    def _get_metadata_cache_via_context(self):
        """Get metadata cache via ApplicationContext with fallback to parent traversal."""
        # Try ApplicationContext first
        context = self._get_app_context()
        if context and hasattr(context, "_metadata_cache"):
            logger.debug("[MetadataWidget] Found metadata cache via ApplicationContext")
            return context._metadata_cache

        # Fallback to legacy parent_window approach
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            logger.debug("[MetadataWidget] Found metadata cache via parent_window")
            return self.parent_window.metadata_cache

        # Try to find metadata cache in main window
        if (
            self.parent_window
            and hasattr(self.parent_window, "main_window")
            and self.parent_window.main_window
        ):
            main_window = self.parent_window.main_window
            if hasattr(main_window, "metadata_cache"):
                logger.debug("[MetadataWidget] Found metadata cache via main_window")
                return main_window.metadata_cache

        # Try to find metadata cache in rename modules area
        if self.parent_window and hasattr(self.parent_window, "rename_modules_area"):
            rename_area = self.parent_window.rename_modules_area
            if hasattr(rename_area, "parent") and rename_area.parent():
                parent = rename_area.parent()
                if hasattr(parent, "metadata_cache"):
                    logger.debug("[MetadataWidget] Found metadata cache via rename area parent")
                    return parent.metadata_cache

        logger.warning("[MetadataWidget] No metadata cache found")
        return None

    def get_available_metadata_keys(self) -> Set[str]:
        # Return cached keys if available
        if self._cached_metadata_keys is not None:
            return self._cached_metadata_keys

        metadata_cache = self._get_metadata_cache_via_context()
        if not metadata_cache:
            self._cached_metadata_keys = set()
            return self._cached_metadata_keys

        all_keys = set()
        try:
            # For PersistentMetadataCache, we need to access the memory cache
            if hasattr(metadata_cache, "_memory_cache"):
                for entry in metadata_cache._memory_cache.values():
                    if isinstance(entry, MetadataEntry) and entry.data:
                        filtered = {
                            k
                            for k in entry.data
                            if not k.startswith("_") and k not in {"path", "filename"}
                        }
                        all_keys.update(filtered)
            # Fallback for other cache types
            elif hasattr(metadata_cache, "_cache"):
                for entry in metadata_cache._cache.values():
                    if isinstance(entry, MetadataEntry) and entry.data:
                        filtered = {
                            k
                            for k in entry.data
                            if not k.startswith("_") and k not in {"path", "filename"}
                        }
                        all_keys.update(filtered)
            # Additional fallback for different cache structures
            elif hasattr(metadata_cache, "get_all_entries"):
                entries = metadata_cache.get_all_entries()
                for entry in entries:
                    if hasattr(entry, "data") and entry.data:
                        filtered = {
                            k
                            for k in entry.data
                            if not k.startswith("_") and k not in {"path", "filename"}
                        }
                        all_keys.update(filtered)
            # Direct dictionary access fallback
            elif isinstance(metadata_cache, dict):
                for entry in metadata_cache.values():
                    if isinstance(entry, dict):
                        filtered = {
                            k
                            for k in entry
                            if not k.startswith("_") and k not in {"path", "filename"}
                        }
                        all_keys.update(filtered)
        except Exception as e:
            logger.warning(f"[MetadataWidget] Error accessing metadata cache: {e}")

        # Cache the result
        self._cached_metadata_keys = all_keys
        return all_keys

    def format_metadata_key_name(self, key: str) -> str:
        formatted = key.replace("_", " ").title()
        replacements = {"Exif": "EXIF", "Gps": "GPS", "Iso": "ISO", "Rgb": "RGB", "Dpi": "DPI"}
        for old, new in replacements.items():
            formatted = formatted.replace(old, new)
        return formatted

    def get_data(self) -> dict:
        """Returns the state for use in the rename system."""
        return {
            "type": "metadata",
            "category": self.category_combo.currentData() or "file_dates",
            "field": self.options_combo.currentData() or "last_modified_yymmdd",
        }

    def emit_if_changed(self) -> None:
        """Emits updated signal only if the state has changed."""
        new_data = self.get_data()
        if new_data != self._last_data:
            self._last_data = new_data
            self.updated.emit(self)

    def clear_cache(self) -> None:
        """Clear the metadata keys cache to force refresh."""
        self._cached_metadata_keys = None

    def refresh_metadata_keys(self) -> None:
        """Refresh metadata keys and update the combo box if currently showing metadata."""
        logger.debug("[MetadataWidget] Refreshing metadata keys")
        self.clear_cache()
        if self.category_combo.currentData() == "metadata_keys":
            logger.debug("[MetadataWidget] Currently showing metadata keys, updating combo box")
            self.populate_metadata_keys()
            self.emit_if_changed()
        else:
            logger.debug(
                "[MetadataWidget] Not currently showing metadata keys, cache cleared for next time"
            )

    @staticmethod
    def is_effective(data: dict) -> bool:
        """
        The metadata module is always effective because it always produces output
        (either file dates or metadata values).
        """
        return True
