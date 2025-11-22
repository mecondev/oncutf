"""
Module: results_table_dialog.py

Author: Michael Economou
Date: 2025-11-22

Global reusable dialog for displaying tabular results with persistent geometry.

Features:
- Two-column table with customizable headers
- Alternating row colors for better readability
- Adjustable column widths (persisted to user config)
- Auto-hide scrollbar
- Min/max height constraints
- Header with resizable sections
- Persistent window geometry (position and size)
"""

from pathlib import Path

from config import (
    QLABEL_BORDER_GRAY,
    QLABEL_PRIMARY_TEXT,
    RESULTS_TABLE_DEFAULT_HEIGHT,
    RESULTS_TABLE_DEFAULT_WIDTH,
    RESULTS_TABLE_LEFT_COLUMN_WIDTH,
    RESULTS_TABLE_MAX_HEIGHT,
    RESULTS_TABLE_MIN_HEIGHT,
    RESULTS_TABLE_RIGHT_COLUMN_WIDTH,
)
from core.pyqt_imports import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ResultsTableDialog(QDialog):
    """
    Global reusable dialog for displaying two-column tabular results.

    Supports:
    - Customizable column headers
    - Alternating row colors
    - Persistent column widths
    - Persistent window geometry
    - Auto-sizing with min/max constraints
    """

    def __init__(
        self,
        parent=None,
        title: str = "Results",
        left_header: str = "Item",
        right_header: str = "Value",
        data: dict | None = None,
        config_key: str = "results_table",
    ):
        """
        Initialize the results table dialog.

        Args:
            parent: Parent widget
            title: Dialog window title
            left_header: Left column header text
            right_header: Right column header text
            data: Dictionary with left column value as key, right column value as value
            config_key: Key for storing geometry/column widths in user config
        """
        super().__init__(parent)
        self.config_key = config_key
        self.left_header = left_header
        self.right_header = right_header
        self.data = data or {}

        self.setWindowTitle(title)
        self.setModal(True)

        # Setup UI
        self._setup_ui()
        self._apply_styling()
        self._load_geometry()
        self._populate_data()

        logger.debug(f"[ResultsTableDialog] Created with {len(self.data)} rows")

    def _setup_ui(self):
        """Setup the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Title label
        self.title_label = QLabel(f"{len(self.data)} items")
        self.title_label.setObjectName("title_label")
        layout.addWidget(self.title_label)

        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([self.left_header, self.right_header])

        # Table properties
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        # Header configuration
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # Left column resizable
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Right auto-size

        # Connect header resize signal to save column widths
        header.sectionResized.connect(self._on_column_resized)

        # Auto-hide scrollbar
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addWidget(self.table)

        # Button bar
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setMinimumWidth(80)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _apply_styling(self):
        """Apply styling to the dialog."""
        style = f"""
        QDialog {{
            background-color: #1e1e1e;
        }}

        QLabel#title_label {{
            color: {QLABEL_PRIMARY_TEXT};
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 4px;
        }}

        QTableWidget {{
            background-color: #252525;
            alternate-background-color: #2a2a2a;
            color: {QLABEL_PRIMARY_TEXT};
            border: 1px solid {QLABEL_BORDER_GRAY};
            gridline-color: {QLABEL_BORDER_GRAY};
            selection-background-color: #3a3a3a;
            font-size: 11px;
        }}

        QTableWidget::item {{
            padding: 4px 8px;
        }}

        QHeaderView::section {{
            background-color: #2d2d2d;
            color: {QLABEL_PRIMARY_TEXT};
            border: 1px solid {QLABEL_BORDER_GRAY};
            padding: 6px 8px;
            font-weight: 600;
            font-size: 11px;
        }}

        QPushButton {{
            background-color: #3a3a3a;
            color: {QLABEL_PRIMARY_TEXT};
            border: 1px solid {QLABEL_BORDER_GRAY};
            border-radius: 4px;
            padding: 6px 16px;
            font-size: 12px;
        }}

        QPushButton:hover {{
            background-color: #4a4a4a;
        }}

        QPushButton:pressed {{
            background-color: #2a2a2a;
        }}
        """
        self.setStyleSheet(style)

    def _populate_data(self):
        """Populate the table with data."""
        if not self.data:
            return

        self.table.setRowCount(len(self.data))

        for row, (left_value, right_value) in enumerate(self.data.items()):
            # Left column (filename or key)
            left_item = QTableWidgetItem(str(left_value))
            left_item.setToolTip(str(left_value))  # Full text on hover
            self.table.setItem(row, 0, left_item)

            # Right column (hash or value)
            right_item = QTableWidgetItem(str(right_value))
            right_item.setToolTip(str(right_value))
            self.table.setItem(row, 1, right_item)

        # Adjust row heights to content
        self.table.resizeRowsToContents()

    def _load_geometry(self):
        """Load persistent geometry and column widths from user config."""
        from utils.json_config_manager import get_app_config_manager

        config_manager = get_app_config_manager()
        dialogs_config = config_manager.get_category("dialogs", create_if_not_exists=True)

        # Load window geometry
        geometry_key = f"{self.config_key}_geometry"
        geometry = dialogs_config.get(geometry_key)
        if geometry:
            try:
                x, y, width, height = geometry
                self.setGeometry(x, y, width, height)
                logger.debug(f"[ResultsTableDialog] Loaded geometry: {geometry}")
            except Exception as e:
                logger.warning(f"[ResultsTableDialog] Failed to restore geometry: {e}")
                self._set_default_geometry()
        else:
            self._set_default_geometry()

        # Load column widths
        column_widths_key = f"{self.config_key}_column_widths"
        column_widths = dialogs_config.get(column_widths_key)
        if column_widths and len(column_widths) == 2:
            try:
                self.table.setColumnWidth(0, column_widths[0])
                # Right column auto-sizes, no need to set explicitly
                logger.debug(f"[ResultsTableDialog] Loaded column widths: {column_widths}")
            except Exception as e:
                logger.warning(f"[ResultsTableDialog] Failed to restore column widths: {e}")
                self._set_default_column_widths()
        else:
            self._set_default_column_widths()

    def _set_default_geometry(self):
        """Set default window geometry from config."""
        width = RESULTS_TABLE_DEFAULT_WIDTH
        height = RESULTS_TABLE_DEFAULT_HEIGHT

        # Adjust height based on row count
        if self.data:
            row_count = len(self.data)
            # Estimate: ~25px per row + header + margins
            estimated_height = 80 + (row_count * 25)
            height = max(RESULTS_TABLE_MIN_HEIGHT, min(estimated_height, RESULTS_TABLE_MAX_HEIGHT))

        self.resize(width, height)

        # Center on parent or screen
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - width) // 2
            y = parent_geo.y() + (parent_geo.height() - height) // 2
            self.move(x, y)

        logger.debug(f"[ResultsTableDialog] Set default geometry: {width}x{height}")

    def _set_default_column_widths(self):
        """Set default column widths from config."""
        left_width = RESULTS_TABLE_LEFT_COLUMN_WIDTH
        self.table.setColumnWidth(0, left_width)
        # Right column auto-sizes
        logger.debug(f"[ResultsTableDialog] Set default column width: {left_width}")

    def _on_column_resized(self, logical_index: int, _old_size: int, new_size: int):
        """Handle column resize event and save to user config."""
        if logical_index == 0:  # Only track left column (right auto-sizes)
            from utils.json_config_manager import get_app_config_manager

            config_manager = get_app_config_manager()
            dialogs_config = config_manager.get_category("dialogs", create_if_not_exists=True)
            column_widths_key = f"{self.config_key}_column_widths"

            # Get current widths
            left_width = new_size
            right_width = self.table.columnWidth(1)

            dialogs_config.set(column_widths_key, [left_width, right_width])
            config_manager.save()  # Persist to disk
            logger.debug(
                f"[ResultsTableDialog] Saved column widths: [{left_width}, {right_width}]",
                extra={"dev_only": True},
            )

    def closeEvent(self, event):
        """Save geometry when dialog closes."""
        from utils.json_config_manager import get_app_config_manager

        config_manager = get_app_config_manager()
        dialogs_config = config_manager.get_category("dialogs", create_if_not_exists=True)
        geometry_key = f"{self.config_key}_geometry"

        geo = self.geometry()
        geometry = [geo.x(), geo.y(), geo.width(), geo.height()]
        dialogs_config.set(geometry_key, geometry)
        config_manager.save()  # Persist to disk

        logger.debug(
            f"[ResultsTableDialog] Saved geometry: {geometry}", extra={"dev_only": True}
        )

        super().closeEvent(event)

    @classmethod
    def show_hash_results(
        cls,
        parent,
        hash_results: dict,
        was_cancelled: bool = False,
    ):
        """
        Factory method to show hash/checksum results.

        Args:
            parent: Parent widget
            hash_results: Dictionary with file_path as key, hash as value
            was_cancelled: Whether operation was cancelled (shown in title)
        """
        if not hash_results:
            return

        # Extract filenames from full paths
        display_data = {}
        for file_path, hash_value in hash_results.items():
            filename = Path(file_path).name
            display_data[filename] = hash_value

        title_suffix = " (Partial)" if was_cancelled else ""
        title = f"Checksum Results{title_suffix}"

        dialog = cls(
            parent=parent,
            title=title,
            left_header="Filename",
            right_header="CRC32 Hash",
            data=display_data,
            config_key="hash_results_table",
        )

        # Update title label with count
        dialog.title_label.setText(f"{len(display_data)} file(s) processed")

        dialog.exec_()

    @classmethod
    def show_duplicate_results(
        cls,
        parent,
        duplicates: dict,
    ):
        """
        Factory method to show duplicate file results.

        Args:
            parent: Parent widget
            duplicates: Dictionary with hash as key, list of file paths as value
        """
        if not duplicates:
            return

        # Flatten duplicates into filename -> hash mapping
        display_data = {}
        for hash_value, file_list in duplicates.items():
            for file_path in file_list:
                filename = Path(file_path).name
                display_data[filename] = hash_value

        dialog = cls(
            parent=parent,
            title="Duplicate Files",
            left_header="Filename",
            right_header="CRC32 Hash",
            data=display_data,
            config_key="duplicate_results_table",
        )

        dialog.title_label.setText(
            f"{len(display_data)} duplicate file(s) in {len(duplicates)} group(s)"
        )

        dialog.exec_()

    @classmethod
    def show_comparison_results(
        cls,
        parent,
        comparison_results: dict,
    ):
        """
        Factory method to show file comparison results.

        Args:
            parent: Parent widget
            comparison_results: Dictionary with filename as key, comparison data as value
        """
        if not comparison_results:
            return

        # Convert to filename -> status mapping
        display_data = {}
        for filename, result in comparison_results.items():
            is_same = result.get("is_same", False)
            status = "Identical" if is_same else "Different"
            display_data[filename] = status

        dialog = cls(
            parent=parent,
            title="File Comparison Results",
            left_header="Filename",
            right_header="Status",
            data=display_data,
            config_key="comparison_results_table",
        )

        # Count matches/differences
        matches = sum(1 for r in comparison_results.values() if r.get("is_same", False))
        differences = len(comparison_results) - matches

        dialog.title_label.setText(
            f"{len(comparison_results)} file(s): {matches} identical, {differences} different"
        )

        dialog.exec_()
