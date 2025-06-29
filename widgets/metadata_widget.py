"""
Module: metadata_widget.py

Author: Michael Economou
Date: 2025-05-01

Widget for metadata selection (file dates or EXIF), with optimized signal emission system.
"""

from typing import Optional, Set

from core.qt_imports import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget, pyqtSignal
from utils.logger_factory import get_cached_logger
from core.persistent_metadata_cache import MetadataEntry
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

    def __init__(self, parent: Optional[QWidget] = None, parent_window: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.parent_window = parent_window  # Keep for backward compatibility
        self.setProperty("module", True)
        self._last_data: Optional[dict] = None  # For change tracking
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Row 1: Category
        category_row = QHBoxLayout()
        category_label = QLabel("Category:")
        category_label.setFixedWidth(80)
        self.category_combo = QComboBox()
        self.category_combo.addItem("File Dates", userData="file_dates")
        self.category_combo.addItem("EXIF/Metadata", userData="metadata_keys")
        self.category_combo.setFixedWidth(120)
        category_row.addWidget(category_label)
        category_row.addWidget(self.category_combo)
        category_row.addStretch()
        layout.addLayout(category_row)

        # Row 2: Field
        options_row = QHBoxLayout()
        options_label = QLabel("Field:")
        options_label.setFixedWidth(80)
        self.options_combo = QComboBox()
        self.options_combo.setFixedWidth(200)
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
        logger.debug(f"[MetadataWidget] Updating options for category: {category}", extra={"dev_only": True})
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
        logger.debug(f"[MetadataWidget] Populated {len(file_date_options)} file date options", extra={"dev_only": True})

    def populate_metadata_keys(self) -> None:
        keys = self.get_available_metadata_keys()
        if not keys:
            self.options_combo.addItem("(No metadata loaded)", userData=None)
            logger.info("[MetadataWidget] No metadata keys available")
            return
        for key in sorted(keys):
            display = self.format_metadata_key_name(key)
            self.options_combo.addItem(display, userData=key)
        logger.debug(f"[MetadataWidget] Populated {len(keys)} metadata keys", extra={"dev_only": True})

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
        if context and hasattr(context, '_metadata_cache'):
            return context._metadata_cache

        # Fallback to legacy parent_window approach
        if self.parent_window and hasattr(self.parent_window, 'metadata_cache'):
            return self.parent_window.metadata_cache

        return None

    def get_available_metadata_keys(self) -> Set[str]:
        metadata_cache = self._get_metadata_cache_via_context()
        if not metadata_cache:
            logger.warning("[MetadataWidget] No access to metadata cache")
            return set()

        all_keys = set()
        try:
            for entry in metadata_cache._cache.values():
                if isinstance(entry, MetadataEntry) and entry.data:
                    filtered = {k for k in entry.data if not k.startswith('_') and k not in {'path', 'filename'}}
                    all_keys.update(filtered)
        except Exception as e:
            logger.warning(f"[MetadataWidget] Error accessing metadata cache: {e}")

        return all_keys

    def format_metadata_key_name(self, key: str) -> str:
        formatted = key.replace('_', ' ').title()
        replacements = {'Exif': 'EXIF',
            'Gps': 'GPS',
            'Iso': 'ISO',
            'Rgb': 'RGB',
            'Dpi': 'DPI'}
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
            logger.debug(f"[MetadataWidget] Emitting updated with data: {new_data}")
            self._last_data = new_data
            self.updated.emit(self)

    @staticmethod
    def is_effective(data: dict) -> bool:
        """
        The metadata module is always effective because it always produces output
        (either file dates or metadata values).
        """
        return True
