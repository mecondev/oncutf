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
    HASH_LIST_COLUMN_CONFIG,
    HASH_LIST_CONTENT_MARGINS,
    HASH_LIST_FONT_SIZE,
    HASH_LIST_HEADER_ALIGNMENT,
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
    RESULTS_TABLE_RIGHT_COLUMN_WIDTH,
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from core.theme_manager import get_theme_manager
from core.window_config_manager import WindowConfigManager

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
        # Internal flag to avoid saving column widths during programmatic adjustments
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
        # Use HASH_LIST_CONTENT_MARGINS if provided (keeps same spacing as file table)
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
        # Rows should not be selectable
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        # Apply configured row height if provided
        from contextlib import suppress
        with suppress(Exception):
            if HASH_LIST_ROW_HEIGHT:
                row_height = int(HASH_LIST_ROW_HEIGHT)
                self.table.verticalHeader().setDefaultSectionSize(row_height)
                # Lock row height using Fixed mode (like file_table_view) for cross-platform consistency
                self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        # Header configuration
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        # Default align header text according to config
        try:
            if HASH_LIST_HEADER_ALIGNMENT == "left":
                header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            elif HASH_LIST_HEADER_ALIGNMENT == "center":
                header.setDefaultAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            else:
                header.setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        except Exception:
            header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Column resize behavior: consult HASH_LIST_COLUMN_CONFIG
        try:
            left_cfg = HASH_LIST_COLUMN_CONFIG.get("filename", {})
            right_cfg = HASH_LIST_COLUMN_CONFIG.get("hash", {})

            # Left column: None width => use smart-fill (we handle on resize), else interactive with given width
            if left_cfg.get("width") is None:
                # set Interactive so user can still resize; we'll programmatically adjust width on dialog resize
                header.setSectionResizeMode(0, QHeaderView.Interactive)
                min_w = left_cfg.get("min_width", 80)
                header.setMinimumSectionSize(min_w)
            else:
                header.setSectionResizeMode(0, QHeaderView.Interactive)

            # Right column: respect configured behavior, default to ResizeToContents
            if right_cfg.get("width") is None:
                header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            else:
                header.setSectionResizeMode(1, QHeaderView.Interactive)
                # set initial width if provided
                from contextlib import suppress
                with suppress(Exception):
                    self.table.setColumnWidth(1, int(right_cfg.get("width", RESULTS_TABLE_RIGHT_COLUMN_WIDTH)))
        except Exception:
            header.setSectionResizeMode(0, QHeaderView.Interactive)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # Connect header resize signal to save column widths
        header.sectionResized.connect(self._on_column_resized)

        # Context menu for copying hash values from right column
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)

        # Scrollbars: show when needed (like file table)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addWidget(self.table)

        # Button bar
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        # Let theme engine decide size/styling; give objectName for theme hooks
        self.close_button.setObjectName("dialog_action_button")
        # Fixed height for cross-platform consistency (matches custom_message_dialog pattern)
        self.close_button.setFixedHeight(24)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Export button (left of Close) - created here to match layout styling
        # (Export action is a placeholder for now)
        try:
            self.export_button = QPushButton("Export")
            self.export_button.setObjectName("dialog_action_button")
            # Fixed height for cross-platform consistency
            self.export_button.setFixedHeight(24)
            # Insert export button before close in the layout
            button_layout.insertWidget(button_layout.count() - 1, self.export_button)
        except Exception:
            pass

    def _apply_styling(self):
        """Apply styling to the dialog."""
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
        }}

        QTableWidget {{
            background-color: {theme.get_color('table_background')};
            alternate-background-color: {theme.get_color('table_alternate')};
            color: {theme.get_color('text')};
            border: 1px solid {theme.get_color('border')};
            gridline-color: {theme.get_color('table_grid')};
            selection-background-color: {theme.get_color('table_selection_bg')};
            font-size: 11px;
        }}

        QTableWidget::item {{
            padding: 4px 8px;
        }}

        QHeaderView::section {{
            background-color: {theme.get_color('results_header_bg')};
            color: {theme.get_color('text')};
            border: 1px solid {theme.get_color('border')};
            padding: 6px 8px;
            font-weight: 600;
            font-size: 11px;
        }}

        QPushButton {{
            background-color: {theme.get_color('button_bg')};
            color: {theme.get_color('text')};
            border: 1px solid {theme.get_color('border')};
            border-radius: 4px;
            padding: 6px 16px;
            font-size: 12px;
        }}

        QPushButton:hover {{
            background-color: {theme.get_color('button_hover_bg')};
        }}

        QPushButton:pressed {{
            background-color: {theme.get_color('pressed')};
        }}
        """
        self.setStyleSheet(style)

        # Runtime adjustments from HASH_LIST_* config
        from contextlib import suppress
        with suppress(Exception):
            # Title label background override: empty -> transparent
            if HASH_LIST_LABEL_BACKGROUND == "":
                self.title_label.setStyleSheet("background-color: transparent;")
            else:
                self.title_label.setStyleSheet(f"background-color: {HASH_LIST_LABEL_BACKGROUND};")

            # Font size override for table/title if provided
            if HASH_LIST_FONT_SIZE:
                fs = int(HASH_LIST_FONT_SIZE)
                font = self.table.font()
                font.setPointSize(fs)
                self.table.setFont(font)
                tfont = self.title_label.font()
                tfont.setPointSize(max(fs, 12))
                self.title_label.setFont(tfont)

            # Row height override (we will NOT call resizeRowsToContents if a fixed row height is set)
            if HASH_LIST_ROW_HEIGHT:
                row_height = int(HASH_LIST_ROW_HEIGHT)
                self.table.verticalHeader().setDefaultSectionSize(row_height)
                # Ensure Fixed mode is still set
                self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

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

        # Enforce row height explicitly to work on Linux/macOS
        if HASH_LIST_ROW_HEIGHT:
            row_height = int(HASH_LIST_ROW_HEIGHT)
            for row in range(self.table.rowCount()):
                self.table.setRowHeight(row, row_height)
        else:
            # Only resize to contents when no fixed height is requested
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
                # enforce min/max after loading persisted geometry
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
                # Right column auto-sizes, no need to set explicitly
                logger.debug(f"[ResultsTableDialog] Loaded column widths: {column_widths}")
            except Exception as e:
                logger.warning(f"[ResultsTableDialog] Failed to restore column widths: {e}")
                self._set_default_column_widths()
        else:
            self._set_default_column_widths()

    def _set_default_geometry(self):
        """Set default window geometry from config."""
        # Choose appropriate defaults: hash-specific if config_key indicates hash
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

        # Minimum width setting (use results table min width)
        try:
            min_w = RESULTS_TABLE_MIN_WIDTH
        except NameError:
            min_w = 350

        # Adjust height based on row count
        if self.data:
            row_count = len(self.data)
            # Estimate: ~25px per row + header + margins
            estimated_height = 80 + (row_count * 25)
            height = max(min_h, min(estimated_height, max_h))

        self.resize(width, height)
        # Enforce minimum size so dialog does not become too small
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
        # Right column auto-sizes
        logger.debug(f"[ResultsTableDialog] Set default column width: {left_width}")

    def _on_column_resized(self, logical_index: int, _old_size: int, new_size: int):
        """Handle column resize event and save to user config."""
        # Ignore saves while we're programmatically adjusting column widths
        if getattr(self, "_suspend_column_save", False):
            return

        if logical_index == 0:  # Only track left column (right auto-sizes)
            from utils.json_config_manager import get_app_config_manager

            config_manager = get_app_config_manager()
            dialogs_config = config_manager.get_category("dialogs", create_if_not_exists=True)
            column_widths_key = f"{self.config_key}_column_widths"

            # Get current widths
            left_width = new_size
            right_width = self.table.columnWidth(1)

            dialogs_config.set(column_widths_key, [left_width, right_width])
            config_manager.mark_dirty()  # Mark for debounced save
            logger.debug(
                f"[ResultsTableDialog] Marked column widths dirty: [{left_width}, {right_width}]",
                extra={"dev_only": True},
            )

    def resizeEvent(self, event):
        """Smart-fill behavior: when filename column width is None in config, fill remaining space."""
        from contextlib import suppress
        with suppress(Exception):
            super().resizeEvent(event)

        # Smart fill only when configured
        try:
            left_cfg = HASH_LIST_COLUMN_CONFIG.get("filename", {})
            if left_cfg.get("width") is None:
                # compute available viewport width and right column width
                available = self.table.viewport().width()
                right_w = self.table.columnWidth(1)
                min_w = left_cfg.get("min_width", 80)

                # leave small padding for gridlines
                target_left = max(min_w, available - right_w - 4)

                # programmatic resize: suspend saving
                self._suspend_column_save = True
                try:
                    self.table.setColumnWidth(0, int(target_left))
                finally:
                    self._suspend_column_save = False
        except Exception:
            # best-effort; do not raise
            pass

    def _on_table_context_menu(self, pos):
        """Show context menu for table; allows copying hash values from right column."""
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        row = idx.row()
        col = idx.column()
        # Only provide copy for right column (hash/value)
        if col != 1:
            return

        menu = QMenu(self)
        action_copy = QAction("Copy value", self)

        def do_copy():
            item = self.table.item(row, col)
            if item:
                QApplication.clipboard().setText(item.text())

        action_copy.triggered.connect(do_copy)
        menu.addAction(action_copy)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def closeEvent(self, event):
        """Save geometry when dialog closes."""
        from utils.json_config_manager import get_app_config_manager

        config_manager = get_app_config_manager()
        dialogs_config = config_manager.get_category("dialogs", create_if_not_exists=True)
        geometry_key = f"{self.config_key}_geometry"

        geo = self.geometry()
        geometry = [geo.x(), geo.y(), geo.width(), geo.height()]
        dialogs_config.set(geometry_key, geometry)
        config_manager.save_immediate()  # Force immediate save on close

        logger.debug(
            f"[ResultsTableDialog] Saved geometry immediately: {geometry}", extra={"dev_only": True}
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
