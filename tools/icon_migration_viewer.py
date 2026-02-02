#!/usr/bin/env python3
"""
Icon Migration Viewer - Visual comparison of Feather vs Material Design icons

Author: Michael Economou
Date: 2026-02-02

GUI tool to visually compare Feather icons with their Material Design equivalents.
"""

import sys
from pathlib import Path
from typing import Dict, Optional

from PyQt5.QtCore import Qt, QSize, QByteArray
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPalette, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QLabel, QPushButton, QLineEdit,
    QHeaderView, QSplitter, QGroupBox, QTextEdit, QCheckBox
)


# FEATHER → MATERIAL DESIGN MAPPING (from migrate_icons.py)
ICON_MAPPING: Dict[str, str] = {
    # NAVIGATION
    "keyboard_arrow_up": "keyboard_arrow_up",
    "keyboard_arrow_down": "keyboard_arrow_down",
    "keyboard_arrow_right": "keyboard_arrow_right",
    "close": "close",
    "menu": "menu",

    # EDITING & CLIPBOARD
    "content_cut": "content_cut",
    "content_paste": "content_paste",
    "content_copy": "content_copy",
    "edit": "edit",
    "undo": "undo",
    "redo": "redo",

    # FILE OPERATIONS
    "folder": "folder",
    "create_new_folder": "create_new_folder",
    "draft": "draft",
    "note_add": "note_add",
    "save": "save",
    "download": "download",
    "refresh": "refresh",
    "refresh": "refresh",

    # SELECTION & CHECKBOXES
    "check_box": "check_box",
    "check_box_outline_blank": "check_box_outline_blank",

    # TOGGLES & BUTTONS
    "add": "add",
    "remove": "remove",
    "toggle_off": "toggle_off",
    "toggle_on": "toggle_on",

    # UTILITIES & INFO
    "info": "info",
    "list": "list",
    "schedule": "schedule",
    "tag": "tag",
    "palette": "palette",
    "view_column": "view_column",
    "stacks": "stacks",
    "more_vert": "more_vert",

    # METADATA/HASH ICONS
    "circle": "circle",
    "check_circle": "check_circle",
    "edit_note": "edit_note",
    "error": "error",
    "warning": "warning",
    "tag": "tag",
}

# Category mapping
FOLDER_MAPPING: Dict[str, str] = {
    "keyboard_arrow_up": "navigation",
    "keyboard_arrow_down": "navigation",
    "keyboard_arrow_right": "navigation",
    "close": "navigation",
    "menu": "navigation",
    "search": "navigation",

    "content_cut": "editing",
    "content_paste": "editing",
    "content_copy": "editing",
    "edit": "editing",
    "undo": "editing",
    "redo": "editing",

    "folder": "files",
    "create_new_folder": "files",
    "draft": "files",
    "note_add": "files",
    "save": "files",
    "download": "files",
    "refresh": "files",

    "check_box": "selection",
    "check_box_outline_blank": "selection",

    "add": "toggles",
    "remove": "toggles",
    "toggle_off": "toggles",
    "toggle_on": "toggles",

    "info": "utilities",
    "list": "utilities",
    "schedule": "utilities",
    "tag": "utilities",
    "palette": "utilities",
    "view_column": "utilities",
    "stacks": "utilities",
    "more_vert": "utilities",

    "circle": "metadata",
    "check_circle": "metadata",
    "edit_note": "metadata",
    "error": "metadata",
    "warning": "metadata",
}


# THEME COLORS (from oncutf/config/ui/theme.py)
THEME_COLORS = {
    "dark": {
        "background": "#181818",
        "text": "#f0ebd8",
        "text_selected": "#0d1321",
        "alternate_row": "#232323",
        "hover": "#3e5c76",
        "selected": "#748cab",
        "selected_hover": "#8a9bb4",
        "button_bg": "#2a2a2a",
        "button_hover": "#4a6fa5",
        "border": "#3a3b40",
        "groupbox_bg": "#1e1e1e",
    },
    "light": {
        "background": "#ffffff",
        "text": "#212121",
        "text_selected": "#ffffff",
        "alternate_row": "#f8f8f8",
        "hover": "#e3f2fd",
        "selected": "#1976d2",
        "selected_hover": "#42a5f5",
        "button_bg": "#f5f5f5",
        "button_hover": "#e3f2fd",
        "border": "#cccccc",
        "groupbox_bg": "#fafafa",
    },
}


class IconMigrationViewer(QMainWindow):
    """Visual icon migration comparison tool."""

    def __init__(self):
        super().__init__()
        self.project_root = Path(__file__).parent.parent
        self.feather_dir = self.project_root / "oncutf/resources/icons/feather_icons"
        self.material_base = self.project_root / "oncutf/resources/icons"

        self.icon_size = 48
        self.current_filter = ""
        self.current_theme = "dark"  # Default dark theme
        self.icon_color = "#ffffff"  # White for dark theme

        self.init_ui()
        self.apply_theme(self.current_theme)
        self.load_icons()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Icon Migration Viewer - Feather → Material Design")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Top controls
        controls = self._create_controls()
        layout.addLayout(controls)

        # Main splitter (table + preview)
        splitter = QSplitter(Qt.Vertical)

        # Icon comparison table
        self.table = self._create_table()
        splitter.addWidget(self.table)

        # Preview panel
        preview_panel = self._create_preview_panel()
        splitter.addWidget(preview_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _create_controls(self) -> QHBoxLayout:
        """Create top control bar."""
        layout = QHBoxLayout()

        # Search box
        layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter icon names...")
        self.search_box.textChanged.connect(self.filter_table)
        layout.addWidget(self.search_box)

        # Size controls
        layout.addWidget(QLabel("Icon Size:"))

        size_32 = QPushButton("32px")
        size_32.clicked.connect(lambda: self.set_icon_size(32))
        layout.addWidget(size_32)

        size_48 = QPushButton("48px")
        size_48.clicked.connect(lambda: self.set_icon_size(48))
        layout.addWidget(size_48)

        size_64 = QPushButton("64px")
        size_64.clicked.connect(lambda: self.set_icon_size(64))
        layout.addWidget(size_64)

        # Show missing toggle
        self.show_missing = QCheckBox("Show Missing Material Icons")
        self.show_missing.stateChanged.connect(self.load_icons)
        layout.addWidget(self.show_missing)

        layout.addStretch()

        # Theme toggle button (top right)
        self.theme_toggle = QPushButton("☀️ Light Theme")
        self.theme_toggle.setToolTip("Toggle between Light and Dark theme")
        self.theme_toggle.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_toggle)

        # Refresh button
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.load_icons)
        layout.addWidget(refresh)

        return layout

    def _create_table(self) -> QTableWidget:
        """Create icon comparison table."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Feather Icon",
            "Preview",
            "→",
            "Material Icon",
            "Preview",
            "Category"
        ])

        # Column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Stretch)

        table.setColumnWidth(1, 60)
        table.setColumnWidth(2, 40)
        table.setColumnWidth(4, 60)

        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setAlternatingRowColors(True)

        table.itemSelectionChanged.connect(self.on_selection_changed)

        return table

    def _create_preview_panel(self) -> QWidget:
        """Create bottom preview panel."""
        group = QGroupBox("Icon Details")
        layout = QVBoxLayout(group)

        # Large previews
        preview_layout = QHBoxLayout()

        # Feather preview
        feather_box = QGroupBox("Feather Icon")
        feather_layout = QVBoxLayout(feather_box)
        self.feather_preview = QLabel()
        self.feather_preview.setAlignment(Qt.AlignCenter)
        self.feather_preview.setMinimumHeight(150)
        feather_layout.addWidget(self.feather_preview)
        self.feather_name = QLabel("(no selection)")
        self.feather_name.setAlignment(Qt.AlignCenter)
        feather_layout.addWidget(self.feather_name)
        preview_layout.addWidget(feather_box)

        # Material preview (no arrow between - icons side by side)
        material_box = QGroupBox("Material Design Icon")
        material_layout = QVBoxLayout(material_box)
        self.material_preview = QLabel()
        self.material_preview.setAlignment(Qt.AlignCenter)
        self.material_preview.setMinimumHeight(150)
        material_layout.addWidget(self.material_preview)
        self.material_name = QLabel("(no selection)")
        self.material_name.setAlignment(Qt.AlignCenter)
        material_layout.addWidget(self.material_name)
        preview_layout.addWidget(material_box)

        layout.addLayout(preview_layout)

        # Info text
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(60)
        self.info_text.setReadOnly(True)
        layout.addWidget(self.info_text)

        return group

    def load_icons(self):
        """Load and display all icon mappings."""
        self.table.setRowCount(0)
        show_missing = self.show_missing.isChecked()

        row = 0
        missing_count = 0

        for feather_name, material_name in sorted(ICON_MAPPING.items()):
            # Get paths
            feather_path = self.feather_dir / f"{feather_name}.svg"
            category = FOLDER_MAPPING.get(material_name, "icons")
            material_path = self.material_base / category / f"{material_name}.svg"

            # Check existence
            feather_exists = feather_path.exists()
            material_exists = material_path.exists()

            if not material_exists:
                missing_count += 1
                if not show_missing:
                    continue

            self.table.insertRow(row)

            # Feather icon name
            item = QTableWidgetItem(feather_name)
            if not feather_exists:
                item.setForeground(QColor(200, 0, 0))
            self.table.setItem(row, 0, item)

            # Feather preview
            if feather_exists:
                preview = self._create_icon_label(feather_path)
                self.table.setCellWidget(row, 1, preview)

            # Arrow
            arrow_item = QTableWidgetItem("→")
            arrow_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, arrow_item)

            # Material icon name
            item = QTableWidgetItem(material_name)
            if not material_exists:
                item.setForeground(QColor(200, 0, 0))
                item.setToolTip("Missing!")
            self.table.setItem(row, 3, item)

            # Material preview
            if material_exists:
                preview = self._create_icon_label(material_path)
                self.table.setCellWidget(row, 4, preview)
            else:
                missing_label = QLabel("❌")
                missing_label.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(row, 4, missing_label)

            # Category
            self.table.setItem(row, 5, QTableWidgetItem(category))

            row += 1

        self.table.resizeRowsToContents()

        status = f"Loaded {row} icon mappings"
        if missing_count > 0:
            status += f" ({missing_count} Material icons missing)"
        self.statusBar().showMessage(status)

    def _create_icon_label(self, icon_path: Path) -> QLabel:
        """Create a label with icon preview."""
        label = QLabel()
        pixmap = self._load_colored_svg(icon_path, self.icon_size)
        if not pixmap.isNull():
            label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        return label

    def _load_colored_svg(self, svg_path: Path, size: int) -> QPixmap:
        """Load SVG and apply current theme color."""
        try:
            # Read SVG file
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_data = f.read()

            import re

            # Detect if this is a Feather icon (has fill="none" and stroke)
            is_feather = 'fill="none"' in svg_data or 'class="feather' in svg_data

            if is_feather:
                # Feather icons: Update stroke color, preserve fill="none"
                svg_data = re.sub(r'stroke="[^"]*"', f'stroke="{self.icon_color}"', svg_data)
                # Keep fill="none" as is
            else:
                # Material Design icons: Add/update fill attribute
                # Replace existing fill colors
                svg_data = re.sub(r'fill="[^"]*"', f'fill="{self.icon_color}"', svg_data)
                svg_data = re.sub(r'stroke="[^"]*"', f'stroke="{self.icon_color}"', svg_data)

                # Add fill to <path> tags that don't have fill attribute
                svg_data = re.sub(
                    r'<path(?![^>]*fill=)([^>]*)>',
                    f'<path fill="{self.icon_color}"\\1>',
                    svg_data
                )

                # Add fill to <svg> tag for overall color
                svg_data = re.sub(
                    r'<svg([^>]*)>',
                    f'<svg\\1 fill="{self.icon_color}">',
                    svg_data
                )

            # Render SVG to pixmap
            renderer = QSvgRenderer(QByteArray(svg_data.encode('utf-8')))
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()

            return pixmap
        except Exception as e:
            # Fallback to regular pixmap loading
            pixmap = QPixmap(str(svg_path))
            if not pixmap.isNull():
                return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return QPixmap()

    def set_icon_size(self, size: int):
        """Change icon preview size."""
        self.icon_size = size
        self.load_icons()

    def filter_table(self, text: str):
        """Filter table rows by search text."""
        self.current_filter = text.lower()

        for row in range(self.table.rowCount()):
            feather_item = self.table.item(row, 0)
            material_item = self.table.item(row, 3)

            if feather_item and material_item:
                feather_name = feather_item.text().lower()
                material_name = material_item.text().lower()

                match = (self.current_filter in feather_name or
                        self.current_filter in material_name)

                self.table.setRowHidden(row, not match)

    def on_selection_changed(self):
        """Handle row selection change."""
        selected = self.table.selectedItems()
        if not selected:
            return

        row = selected[0].row()

        # Get names
        feather_name = self.table.item(row, 0).text()
        material_name = self.table.item(row, 3).text()
        category = self.table.item(row, 5).text()

        # Get paths
        feather_path = self.feather_dir / f"{feather_name}.svg"
        material_path = self.material_base / category / f"{material_name}.svg"

        # Update large previews with colored icons
        if feather_path.exists():
            pixmap = self._load_colored_svg(feather_path, 128)
            self.feather_preview.setPixmap(pixmap)
            self.feather_name.setText(f"{feather_name}.svg")
        else:
            self.feather_preview.setText("Missing")
            self.feather_name.setText(f"{feather_name}.svg (NOT FOUND)")

        if material_path.exists():
            pixmap = self._load_colored_svg(material_path, 128)
            self.material_preview.setPixmap(pixmap)
            self.material_name.setText(f"{material_name}.svg")
        else:
            self.material_preview.setText("Missing")
            self.material_name.setText(f"{material_name}.svg (NOT FOUND)")

        # Update info text
        info = f"<b>Migration:</b> {feather_name} → {material_name}<br>"
        info += f"<b>Category:</b> {category}<br>"
        info += f"<b>Feather path:</b> {feather_path}<br>"
        info += f"<b>Material path:</b> {material_path}<br>"
        info += f"<b>Status:</b> "

        if feather_path.exists() and material_path.exists():
            info += "✅ Both icons available"
        elif not material_path.exists():
            info += "❌ Material icon missing"
        elif not feather_path.exists():
            info += "⚠️ Feather icon missing (already migrated?)"

        self.info_text.setHtml(info)

    def toggle_theme(self):
        """Toggle between light and dark theme."""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"

        # Update icon color based on theme
        self.icon_color = "#ffffff" if self.current_theme == "dark" else "#000000"

        self.apply_theme(self.current_theme)

        # Update button text
        if self.current_theme == "dark":
            self.theme_toggle.setText("☀️ Light Theme")
        else:
            self.theme_toggle.setText("🌙 Dark Theme")

        # Reload icons with new color
        self.load_icons()

    def apply_theme(self, theme_name: str):
        """Apply the specified theme."""
        colors = THEME_COLORS[theme_name]

        # Application-wide palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(colors["background"]))
        palette.setColor(QPalette.WindowText, QColor(colors["text"]))
        palette.setColor(QPalette.Base, QColor(colors["background"]))
        palette.setColor(QPalette.AlternateBase, QColor(colors["alternate_row"]))
        palette.setColor(QPalette.Text, QColor(colors["text"]))
        palette.setColor(QPalette.Button, QColor(colors["button_bg"]))
        palette.setColor(QPalette.ButtonText, QColor(colors["text"]))
        palette.setColor(QPalette.Highlight, QColor(colors["selected"]))
        palette.setColor(QPalette.HighlightedText, QColor(colors["text_selected"]))

        self.setPalette(palette)

        # Table-specific styling
        table_style = f"""
            QTableWidget {{
                background-color: {colors["background"]};
                color: {colors["text"]};
                alternate-background-color: {colors["alternate_row"]};
                gridline-color: {colors["border"]};
                border: 1px solid {colors["border"]};
            }}
            QTableWidget::item:selected {{
                background-color: {colors["selected"]};
                color: {colors["text_selected"]};
            }}
            QTableWidget::item:hover {{
                background-color: {colors["hover"]};
            }}
            QHeaderView::section {{
                background-color: {colors["button_bg"]};
                color: {colors["text"]};
                border: 1px solid {colors["border"]};
                padding: 4px;
            }}
        """
        self.table.setStyleSheet(table_style)

        # GroupBox styling
        groupbox_style = f"""
            QGroupBox {{
                background-color: {colors["groupbox_bg"]};
                color: {colors["text"]};
                border: 1px solid {colors["border"]};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: {colors["text"]};
            }}
        """

        # Apply to all group boxes
        for widget in self.findChildren(QGroupBox):
            widget.setStyleSheet(groupbox_style)

        # Button styling
        button_style = f"""
            QPushButton {{
                background-color: {colors["button_bg"]};
                color: {colors["text"]};
                border: 1px solid {colors["border"]};
                border-radius: 3px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {colors["button_hover"]};
            }}
            QPushButton:pressed {{
                background-color: {colors["selected"]};
            }}
        """

        for widget in self.findChildren(QPushButton):
            widget.setStyleSheet(button_style)

        # LineEdit styling
        lineedit_style = f"""
            QLineEdit {{
                background-color: {colors["background"]};
                color: {colors["text"]};
                border: 1px solid {colors["border"]};
                border-radius: 3px;
                padding: 3px;
            }}
        """

        for widget in self.findChildren(QLineEdit):
            widget.setStyleSheet(lineedit_style)

        # TextEdit styling
        textedit_style = f"""
            QTextEdit {{
                background-color: {colors["background"]};
                color: {colors["text"]};
                border: 1px solid {colors["border"]};
                border-radius: 3px;
            }}
        """

        for widget in self.findChildren(QTextEdit):
            widget.setStyleSheet(textedit_style)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle('Fusion')

    viewer = IconMigrationViewer()
    viewer.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
