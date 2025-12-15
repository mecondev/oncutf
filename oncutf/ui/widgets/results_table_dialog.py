"""
Module: results_table_dialog.py

Author: Michael Economou
Date: 2025-11-23

Global reusable dialog for displaying tabular results with persistent geometry.

Features:
- QTableView with custom model (not QTableWidget)
- Two-column table with customizable headers
- Proper styling matching file_table_view
- Alternating row colors
- Adjustable column widths (persisted to user config)
- Persistent window geometry
- Min/max height constraints
"""

from pathlib import Path

from config import (
    HASH_LIST_CONTENT_MARGINS,
    HASH_LIST_FONT_SIZE,
    HASH_LIST_LABEL_BACKGROUND,
    HASH_LIST_ROW_HEIGHT,
    HASH_LIST_WINDOW_DEFAULT_HEIGHT,
    HASH_LIST_WINDOW_DEFAULT_WIDTH,
    HASH_LIST_WINDOW_MAX_HEIGHT,
    HASH_LIST_WINDOW_MIN_HEIGHT,
    RESULTS_TABLE_DEFAULT_HEIGHT,
    RESULTS_TABLE_DEFAULT_WIDTH,
    RESULTS_TABLE_LEFT_COLUMN_WIDTH,
    RESULTS_TABLE_MAX_HEIGHT,
    RESULTS_TABLE_MIN_HEIGHT,
    RESULTS_TABLE_MIN_WIDTH,
)
from core.pyqt_imports import (
    QAction,
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    Qt,
    QTableView,
    QVBoxLayout,
)
from core.theme_manager import get_theme_manager
from oncutf.models.results_table_model import ResultsTableModel
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ResultsTableDialog(QDialog):
    """
    Global reusable dialog for displaying two-column tabular results using QTableView.

    Features:
    - QTableView with custom ResultsTableModel for full control
    - Customizable column headers
    - Persistent column widths
    - Persistent window geometry
    - Auto-sizing with min/max constraints
    - Proper dark theme styling
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
        """Initialize the results table dialog."""
        super().__init__(parent)
        self.config_key = config_key
        self.left_header = left_header
        self.right_header = right_header
        self.data = data or {}
        self._suspend_column_save = False

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

        # Margins
        try:
            margins = HASH_LIST_CONTENT_MARGINS
            layout.setContentsMargins(
                margins.get("left", 8),
                margins.get("top", 8),
                margins.get("right", 8),
                margins.get("bottom", 8),
            )
        except Exception:
            layout.setContentsMargins(12, 12, 12, 12)

        layout.setSpacing(10)

        # Title label with descriptive text
        item_count = len(self.data)
        count_text = f"checksum for {item_count} selected {'item' if item_count == 1 else 'items'}"
        self.title_label = QLabel(count_text)
        self.title_label.setObjectName("title_label")
        layout.addWidget(self.title_label)

        # Create model and table view
        self.model = ResultsTableModel(self.data, parent=self)
        self.model.set_headers(self.left_header, self.right_header)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.NoSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        # Configure row height
        if HASH_LIST_ROW_HEIGHT:
            row_height = int(HASH_LIST_ROW_HEIGHT)
            self.table.verticalHeader().setDefaultSectionSize(row_height)
            self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        # Configure columns
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # Connect header resize signal
        header.sectionResized.connect(self._on_column_resized)

        # Context menu for copying values
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)

        # Scrollbars
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addWidget(self.table)

        # Button bar
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Cancel button (index 1) - with focus
        self.close_button = QPushButton("Cancel")
        self.close_button.clicked.connect(self.reject)
        self.close_button.setObjectName("dialog_action_button")
        self.close_button.setFocus()
        self.close_button.setDefault(True)
        button_layout.addWidget(self.close_button)

        # Export button (index 2)
        try:
            self.export_button = QPushButton("Export")
            self.export_button.setObjectName("dialog_action_button")
            button_layout.addWidget(self.export_button)
        except Exception:
            pass

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _apply_styling(self):
        """Apply dark theme styling matching file_table_view."""
        theme = get_theme_manager()

        style = f"""
        QDialog {{
            background-color: {theme.get_color('dialog_background')};
        }}

        QLabel#title_label {{
            color: {theme.get_color('text')};
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 4px;
            margin-left: 8px;
        }}

        QTableView {{
            background-color: {theme.get_color('table_background')};
            alternate-background-color: {theme.get_color('table_alternate')};
            color: {theme.get_color('text')};
            border: 1px solid {theme.get_color('border')};
            gridline-color: transparent;
            selection-background-color: {theme.get_color('table_selection_bg')};
            font-size: 11px;
        }}

        QTableView::item {{
            padding: 4px 8px;
        }}

        QHeaderView::section {{
            background-color: {theme.get_color('results_header_bg')};
            color: {theme.get_color('text')};
            border: 1px solid {theme.get_color('border')};
            padding: 0px 8px;
            font-weight: 600;
            font-size: 11px;
        }}

        QHeaderView::section:hover {{
            background-color: {theme.get_color('results_header_bg')};
        }}
        """
        self.setStyleSheet(style)

        # Runtime overrides from config
        from contextlib import suppress
        with suppress(Exception):
            if HASH_LIST_LABEL_BACKGROUND == "":
                self.title_label.setStyleSheet("background-color: transparent;")
            else:
                self.title_label.setStyleSheet(f"background-color: {HASH_LIST_LABEL_BACKGROUND};")

            if HASH_LIST_FONT_SIZE:
                fs = int(HASH_LIST_FONT_SIZE)
                font = self.table.font()
                font.setPointSize(fs)
                self.table.setFont(font)
                tfont = self.title_label.font()
                tfont.setPointSize(max(fs, 12))
                self.title_label.setFont(tfont)

    def _populate_data(self):
        """Populate the table with data."""
        if not self.data:
            return
        self.model.set_data(self.data)

    def _load_geometry(self):
        """Load persistent geometry and column widths from user config."""
        from oncutf.utils.json_config_manager import get_app_config_manager

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

                # Enforce min/max
                if getattr(self, "config_key", "").startswith("hash"):
                    min_h = HASH_LIST_WINDOW_MIN_HEIGHT
                    max_h = HASH_LIST_WINDOW_MAX_HEIGHT
                else:
                    min_h = RESULTS_TABLE_MIN_HEIGHT
                    max_h = RESULTS_TABLE_MAX_HEIGHT

                try:
                    min_w = RESULTS_TABLE_MIN_WIDTH
                except NameError:
                    min_w = 350

                self.setMinimumSize(min_w, min_h)
                self.setMaximumHeight(max_h)
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
                logger.debug(f"[ResultsTableDialog] Loaded column widths: {column_widths}")
            except Exception as e:
                logger.warning(f"[ResultsTableDialog] Failed to restore column widths: {e}")
                self._set_default_column_widths()
        else:
            self._set_default_column_widths()

    def _set_default_geometry(self):
        """Set default window geometry from config."""
        if getattr(self, "config_key", "").startswith("hash"):
            width = HASH_LIST_WINDOW_DEFAULT_WIDTH
            height = HASH_LIST_WINDOW_DEFAULT_HEIGHT
            min_h = HASH_LIST_WINDOW_MIN_HEIGHT
            max_h = HASH_LIST_WINDOW_MAX_HEIGHT
        else:
            width = RESULTS_TABLE_DEFAULT_WIDTH
            height = RESULTS_TABLE_DEFAULT_HEIGHT
            min_h = RESULTS_TABLE_MIN_HEIGHT
            max_h = RESULTS_TABLE_MAX_HEIGHT

        try:
            min_w = RESULTS_TABLE_MIN_WIDTH
        except NameError:
            min_w = 350

        # Adjust height based on row count
        if self.data:
            row_count = len(self.data)
            estimated_height = 80 + (row_count * 25)
            height = max(min_h, min(estimated_height, max_h))

        self.resize(width, height)
        from contextlib import suppress
        with suppress(Exception):
            self.setMinimumSize(min_w, min_h)

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
        logger.debug(f"[ResultsTableDialog] Set default column width: {left_width}")

    def _on_column_resized(self, logical_index: int, _old_size: int, new_size: int):
        """Handle column resize and persist to config."""
        if getattr(self, "_suspend_column_save", False):
            return

        if logical_index == 0:
            from oncutf.utils.json_config_manager import get_app_config_manager

            config_manager = get_app_config_manager()
            dialogs_config = config_manager.get_category("dialogs", create_if_not_exists=True)
            column_widths_key = f"{self.config_key}_column_widths"

            left_width = new_size
            right_width = self.table.columnWidth(1)

            dialogs_config.set(column_widths_key, [left_width, right_width])
            config_manager.mark_dirty()
            logger.debug(f"[ResultsTableDialog] Marked column widths dirty: [{left_width}, {right_width}]",
                extra={"dev_only": True})

    def _on_table_context_menu(self, pos):
        """Show context menu for copying values - works on entire row."""
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return

        row = idx.row()
        # Get value from right column (column 1) regardless of where click was
        value_idx = self.model.index(row, 1)

        menu = QMenu(self)
        action_copy = QAction("Copy hash value", self)

        def do_copy():
            value = self.model.data(value_idx, Qt.DisplayRole)
            if value:
                QApplication.clipboard().setText(str(value))

        action_copy.triggered.connect(do_copy)
        menu.addAction(action_copy)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def closeEvent(self, event):
        """Save geometry when dialog closes."""
        from oncutf.utils.json_config_manager import get_app_config_manager

        config_manager = get_app_config_manager()
        dialogs_config = config_manager.get_category("dialogs", create_if_not_exists=True)
        geometry_key = f"{self.config_key}_geometry"

        geo = self.geometry()
        geometry = [geo.x(), geo.y(), geo.width(), geo.height()]
        dialogs_config.set(geometry_key, geometry)
        config_manager.save_immediate()

        logger.debug(f"[ResultsTableDialog] Saved geometry immediately: {geometry}",
            extra={"dev_only": True})

        super().closeEvent(event)

    @classmethod
    def show_hash_results(
        cls,
        parent,
        hash_results: dict,
        was_cancelled: bool = False,
    ):
        """Factory method to show hash/checksum results."""
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
            right_header="Checksum",
            data=display_data,
            config_key="hash_list",
        )
        dialog.exec_()
