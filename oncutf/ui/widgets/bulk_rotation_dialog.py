"""
Module: bulk_rotation_dialog.py

Author: Michael Economou
Date: 2025-06-01

bulk_rotation_dialog.py
Dialog for bulk rotation operations.
"""

from pathlib import Path

from config import QLABEL_MUTED_TEXT
from oncutf.core.pyqt_imports import (
    QCheckBox,
    QDialog,
    QFont,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    Qt,
    QVBoxLayout,
    QWidget,
)
from oncutf.core.theme_manager import get_theme_manager
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class BulkRotationDialog(QDialog):
    """Dialog for bulk rotation operations with file analysis and checkboxes."""

    def __init__(self, parent=None, selected_files=None, metadata_cache=None):
        super().__init__(parent)
        self.selected_files = selected_files or []
        self.metadata_cache = metadata_cache
        self.file_groups = {}
        self.checkboxes = {}

        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint)
        self.setModal(True)
        self.setFixedSize(600, 450)

        theme = get_theme_manager()
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {theme.get_color('dialog_background')};
                color: {theme.get_color('text')};
                font-size: 9pt; font-family: "Inter", "Segoe UI", Arial, sans-serif; font-weight: 500;
                border-radius: 8px;
            }}
            QLabel {{
                background-color: transparent;
                color: {theme.get_color('text')};
                font-size: 9pt; font-family: "Inter", "Segoe UI", Arial, sans-serif; font-weight: 500;
                border: none;
                padding: 2px;
            }}
            QCheckBox {{
                color: {theme.get_color('text')};
                font-size: 9pt; font-family: "Inter", "Segoe UI", Arial, sans-serif; font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {theme.get_color('border')};
                border-radius: 3px;
                background-color: {theme.get_color('input_bg')};
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme.get_color('selected')};
                border-color: {theme.get_color('selected')};
            }}
            QFrame {{
                background-color: {theme.get_color('background')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 8px;
            }}
            QScrollArea {{
                background-color: {theme.get_color('background')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 8px;
            }}
            QScrollArea QWidget {{
                background-color: transparent;
            }}
        """
        )

        self._setup_ui()
        self._analyze_files()

    def _apply_info_label_style(self, color: str, opacity: str = "1.0"):
        """Apply consistent font styling to info label."""
        from oncutf.utils.fonts import get_inter_css_weight, get_inter_family

        font_family = get_inter_family("base")
        font_weight = get_inter_css_weight("base")
        self.info_label.setStyleSheet(
            f"color: {color}; font-family: '{font_family}', Arial, sans-serif; font-size: 8pt; font-weight: {font_weight}; opacity: {opacity};"
        )

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("Bulk Rotation Settings")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel("Set rotation to 0° for selected file types:")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Scroll area for file groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumHeight(250)

        # Content widget
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(12)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Info label
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self._apply_info_label_style(QLABEL_MUTED_TEXT)
        layout.addWidget(self.info_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setDefault(False)
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.setFocus()
        self.cancel_button.clicked.connect(self.reject)

        theme = get_theme_manager()
        self.cancel_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {theme.get_color('button_bg')};
                color: {theme.get_color('text')};
                font-size: 9pt; font-family: "Inter", "Segoe UI", Arial, sans-serif; font-weight: 500;
                border: none;
                border-radius: 8px;
                padding: 4px 12px 4px 8px;
                min-width: 70px;
            }}
            QPushButton:hover {{
                background-color: {theme.get_color('button_hover_bg')};
            }}
            QPushButton:pressed {{
                background-color: {theme.get_color('pressed')};
            }}
        """
        )

        # Apply button
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.accept)

        theme = get_theme_manager()
        self.apply_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {theme.get_color('button_bg')};
                color: {theme.get_color('text')};
                font-size: 9pt; font-family: "Inter", "Segoe UI", Arial, sans-serif; font-weight: 500;
                border: none;
                border-radius: 8px;
                padding: 4px 12px 4px 8px;
                min-width: 70px;
            }}
            QPushButton:hover {{
                background-color: {theme.get_color('selected')};
            }}
            QPushButton:pressed {{
                background-color: {theme.get_color('pressed')};
            }}
        """
        )

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
        layout.addLayout(button_layout)

    def _analyze_files(self):
        if not self.selected_files:
            self.info_label.setText("No files selected.")
            return

        # Group files by extension and analyze rotation needs
        file_types = {}
        total_files = len(self.selected_files)
        total_needing_rotation = 0
        files_missing_metadata = 0

        for file_item in self.selected_files:
            ext = Path(file_item.filename).suffix.lower()
            if ext.startswith("."):
                ext = ext[1:]

            if ext in ["jpg", "jpeg", "png", "tiff", "tif", "bmp", "gif"]:
                file_type = "Images"
            elif ext in ["mp4", "avi", "mov", "mkv", "wmv", "flv", "m4v"]:
                file_type = "Videos"
            elif ext in ["mp3", "wav", "flac", "aac", "m4a", "ogg"]:
                file_type = "Audio"
            else:
                file_type = "Other"

            if file_type not in file_types:
                file_types[file_type] = {
                    "all_files": [],
                    "files_needing_change": [],
                    "extensions": set(),
                }

            file_types[file_type]["all_files"].append(file_item)
            file_types[file_type]["extensions"].add(ext.upper())

            # Check if this file needs rotation change
            current_rotation = self._get_current_rotation(file_item)
            if current_rotation is None:
                files_missing_metadata += 1
                # Files without metadata will be treated as needing change (assume non-zero)
                file_types[file_type]["files_needing_change"].append(file_item)
                total_needing_rotation += 1
            elif current_rotation != "0":
                file_types[file_type]["files_needing_change"].append(file_item)
                total_needing_rotation += 1

        # Only create UI for file types that have files needing rotation change
        groups_with_changes = 0
        for file_type, data in file_types.items():
            if data["files_needing_change"]:  # Only show groups with files that need changes
                files_needing_change = data["files_needing_change"]
                total_files_in_group = len(data["all_files"])
                extensions = sorted(data["extensions"])
                self._create_group_widget(
                    file_type, files_needing_change, total_files_in_group, extensions
                )
                groups_with_changes += 1

        # Update info label with meaningful information
        if total_needing_rotation == 0:
            self.info_label.setText("All selected files already have 0° rotation.")
            # Disable apply button since no changes needed
            self.apply_button.setEnabled(False)
            self.apply_button.setText("No Changes Needed")
            # Update dialog title to reflect no changes needed
            self.setWindowTitle("Bulk Rotation - No Changes Needed")
        else:
            info_text = (
                f"{total_needing_rotation} of {total_files} files will be set to 0° rotation"
            )
            if files_missing_metadata > 0:
                info_text += f" ({files_missing_metadata} without metadata)"
            self.info_label.setText(info_text)
            # Update dialog title to show how many files will be changed
            self.setWindowTitle(f"Bulk Rotation - {total_needing_rotation} Files")

    def _get_current_rotation(self, file_item) -> str | None:
        """Get current rotation value for a file, checking cache first then file metadata."""
        if not self.metadata_cache:
            return None

        # Check metadata cache first (includes any pending modifications)
        metadata_entry = self.metadata_cache.get_entry(file_item.full_path)
        if metadata_entry and hasattr(metadata_entry, "data"):
            rotation = metadata_entry.data.get("Rotation")
            if rotation is not None:
                return str(rotation)

        # Fallback to file metadata
        if hasattr(file_item, "metadata") and file_item.metadata:
            rotation = file_item.metadata.get("Rotation")
            if rotation is not None:
                return str(rotation)

        # Return None for files without rotation metadata (will be treated as needing change)
        return None

    def _create_group_widget(
        self,
        file_type: str,
        files_needing_change: list,
        total_files_in_group: int,
        extensions: list[str],
    ):
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

        # Label with file count showing only files that need changes
        extensions_text = ", ".join(extensions)
        files_to_change = len(files_needing_change)

        if files_to_change == total_files_in_group:
            # All files in this group need changes
            label_text = f"{file_type} ({files_to_change} files): {extensions_text}"
        else:
            # Some files already have 0° rotation
            label_text = (
                f"{file_type} ({files_to_change}/{total_files_in_group} files): {extensions_text}"
            )

        label = QLabel(label_text)
        label.setWordWrap(True)

        header_layout.addWidget(checkbox)
        header_layout.addWidget(label, 1)
        layout.addLayout(header_layout)

        self.content_layout.addWidget(frame)
        # Store only the files that actually need changes
        self.file_groups[file_type] = files_needing_change

    def get_selected_files(self) -> list:
        selected = []
        for file_type, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected.extend(self.file_groups[file_type])
        return selected

    @staticmethod
    def get_bulk_rotation_choice(parent, selected_files, metadata_cache):
        dialog = BulkRotationDialog(parent, selected_files, metadata_cache)

        if dialog.exec_() == QDialog.Accepted:
            return dialog.get_selected_files()
        return []
