"""
bulk_rotation_dialog.py

Author: Michael Economou
Date: 2025-06-20

Dialog for bulk rotation operations on selected files.
Features file type grouping, missing metadata detection, and toggle switches.
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
    QGroupBox
)

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ToggleSwitch(QWidget):
    """
    Custom toggle switch widget with smooth animation and professional styling.
    """
    toggled = pyqtSignal(bool)

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self._checked = True
        self._text = text

        # Apply toggle switch styling
        self.setStyleSheet("""
            ToggleSwitch {
                background: transparent;
                border: none;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Text label
        self.label = QLabel(text)
        self.label.setStyleSheet("color: #333333; font-size: 14px;")
        layout.addWidget(self.label)

        layout.addStretch()

        # Toggle switch button
        self.switch_button = QPushButton()
        self.switch_button.setCheckable(True)
        self.switch_button.setChecked(True)
        self.switch_button.setFixedSize(50, 25)
        self.switch_button.clicked.connect(self._on_toggle)

        # Apply switch styling with green color from buttons.qss
        self.switch_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: 2px solid #4CAF50;
                border-radius: 12px;
                color: white;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            QPushButton:!checked {
                background-color: #cccccc;
                border-color: #cccccc;
                color: #666666;
            }
            QPushButton:hover {
                background-color: #45a049;
                border-color: #45a049;
            }
            QPushButton:!checked:hover {
                background-color: #bbbbbb;
                border-color: #bbbbbb;
            }
        """)

        layout.addWidget(self.switch_button)

        self._update_switch_text()

    def _on_toggle(self):
        """Handle toggle switch click."""
        self._checked = self.switch_button.isChecked()
        self._update_switch_text()
        self.toggled.emit(self._checked)

    def _update_switch_text(self):
        """Update switch button text."""
        if self._checked:
            self.switch_button.setText("ON")
        else:
            self.switch_button.setText("OFF")

    def isChecked(self) -> bool:
        """Return whether the switch is checked."""
        return self._checked

    def setChecked(self, checked: bool):
        """Set the switch state."""
        self._checked = checked
        self.switch_button.setChecked(checked)
        self._update_switch_text()


class BulkRotationDialog(QDialog):
    """
    Dialog for setting rotation to 0° for multiple selected files.

    Features:
    - File type grouping with counts
    - Missing metadata detection
    - Toggle switches for modern UX
    - Professional styling
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Remove title bar and make it a widget-like dialog
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint)
        self.setModal(True)
        self.setMinimumWidth(550)  # Wider to prevent text cutting
        self.setMaximumWidth(600)

        # Data storage
        self.selected_files: List = []
        self.file_groups: Dict[str, List] = {}
        self.missing_metadata_files: List = []
        self.files_needing_change: Dict[str, List] = {}

        # UI components
        self.file_type_switches: Dict[str, ToggleSwitch] = {}
        self.load_metadata_switch: Optional[ToggleSwitch] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Title section
        title_label = QLabel("Set Rotation to 0° (Reset to Normal)")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333333;
            margin-bottom: 5px;
        """)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel("This will reset the rotation metadata to 0° for selected file types.")
        desc_label.setStyleSheet("""
            color: #666666;
            font-size: 14px;
            margin-bottom: 15px;
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # File types group
        self.file_types_group = QGroupBox("Files to Process")
        self.file_types_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: white;
            }
        """)
        self.file_types_layout = QVBoxLayout(self.file_types_group)
        self.file_types_layout.setSpacing(12)
        layout.addWidget(self.file_types_group)

        # Missing metadata section
        self.metadata_frame = QFrame()
        self.metadata_layout = QVBoxLayout(self.metadata_frame)
        self.metadata_layout.setContentsMargins(0, 15, 0, 0)
        layout.addWidget(self.metadata_frame)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #e0e0e0; margin: 10px 0;")
        layout.addWidget(separator)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedWidth(120)
        self.cancel_button.clicked.connect(self.reject)

        # Apply button styling from buttons.qss theme
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #333333;
                border: 2px solid #cccccc;
                padding: 10px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border-color: #999999;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        button_layout.addWidget(self.cancel_button)

        self.apply_button = QPushButton("Apply")
        self.apply_button.setFixedWidth(120)
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self.accept)

        # Apply green button styling consistent with theme
        self.apply_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 2px solid #4CAF50;
                padding: 10px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
                border-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
                border-color: #3d8b40;
            }
        """)
        button_layout.addWidget(self.apply_button)

        layout.addLayout(button_layout)

        # Set focus to Cancel button (safer default)
        self.cancel_button.setFocus()

    def set_files(self, files: List, metadata_cache) -> None:
        """
        Set the files to process and analyze them.

        Args:
            files: List of FileItem objects
            metadata_cache: Metadata cache to check for existing metadata
        """
        self.selected_files = files
        self._analyze_files(metadata_cache)
        self._update_ui()

    def _analyze_files(self, metadata_cache) -> None:
        """Analyze files by type, metadata availability, and rotation values."""
        # Group files by extension
        self.file_groups = defaultdict(list)
        self.missing_metadata_files = []
        self.files_needing_change = defaultdict(list)

        for file_item in self.selected_files:
            # Get file extension
            ext = Path(file_item.filename).suffix.lower()
            if ext.startswith('.'):
                ext = ext[1:]  # Remove the dot

            # Group by extension
            self.file_groups[ext].append(file_item)

            # Check if metadata is missing
            if not metadata_cache.has(file_item.full_path):
                self.missing_metadata_files.append(file_item)
            else:
                # Check if file needs rotation change (not already 0)
                cache_entry = metadata_cache.get_entry(file_item.full_path)
                if cache_entry and hasattr(cache_entry, 'data'):
                    current_rotation = cache_entry.data.get("Rotation", "0")
                    if str(current_rotation) != "0":
                        self.files_needing_change[ext].append(file_item)
                        logger.debug(f"[BulkRotation] {file_item.filename} needs change: rotation={current_rotation}")
                    else:
                        logger.debug(f"[BulkRotation] {file_item.filename} already at 0°")

        logger.debug(f"[BulkRotation] Analyzed {len(self.selected_files)} files into {len(self.file_groups)} groups")
        logger.debug(f"[BulkRotation] {len(self.missing_metadata_files)} files missing metadata")
        logger.debug(f"[BulkRotation] {sum(len(files) for files in self.files_needing_change.values())} files need rotation change")

    def _update_ui(self) -> None:
        """Update UI based on analyzed files."""
        # Clear existing switches
        for switch in self.file_type_switches.values():
            switch.deleteLater()
        self.file_type_switches.clear()

        # Add file type switches - show only files that need changes or missing metadata
        total_files = len(self.selected_files)
        for ext, all_files in sorted(self.file_groups.items()):
            files_needing_change = self.files_needing_change.get(ext, [])
            missing_files = [f for f in all_files if f in self.missing_metadata_files]

            # Count files that need processing (either missing metadata or need rotation change)
            files_to_process = len(set(files_needing_change + missing_files))
            total_of_type = len(all_files)

            if files_to_process == 0:
                continue  # Skip file types that don't need any changes

            # Determine file type description
            if ext.lower() in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']:
                type_desc = "Images"
            elif ext.lower() in ['mp4', 'mov', 'avi', 'mkv', 'wmv', 'flv', 'm4v']:
                type_desc = "Videos"
            elif ext.lower() in ['mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg']:
                type_desc = "Audio"
            else:
                type_desc = "Files"

            # Show ratio of files that need processing vs total
            switch_text = f"{type_desc} ({files_to_process}/{total_of_type} files): {ext.upper()}"
            switch = ToggleSwitch(switch_text)
            switch.setChecked(True)  # Default to checked

            self.file_types_layout.addWidget(switch)
            self.file_type_switches[ext] = switch

        # Update files count in group title
        total_needing_change = sum(len(files) for files in self.files_needing_change.values())
        total_missing = len(self.missing_metadata_files)
        total_to_process = len(set(self.missing_metadata_files +
                                [f for files in self.files_needing_change.values() for f in files]))

        self.file_types_group.setTitle(f"Files to Process: {total_to_process}/{total_files} selected")

        # Add missing metadata switch if needed
        if self.missing_metadata_files:
            missing_count = len(self.missing_metadata_files)

            if self.load_metadata_switch:
                self.load_metadata_switch.deleteLater()

            switch_text = f"Load missing metadata first ({missing_count} files)"
            self.load_metadata_switch = ToggleSwitch(switch_text)
            self.load_metadata_switch.setChecked(True)  # Default to checked

            # Special styling for metadata loading switch
            self.load_metadata_switch.label.setStyleSheet("""
                color: #ff6b35;
                font-weight: bold;
                font-size: 14px;
            """)

            self.metadata_layout.addWidget(self.load_metadata_switch)
            self.metadata_frame.setVisible(True)
        else:
            self.metadata_frame.setVisible(False)

    def get_selected_file_types(self) -> Set[str]:
        """Get the file extensions that are selected for processing."""
        selected = set()
        for ext, switch in self.file_type_switches.items():
            if switch.isChecked():
                selected.add(ext)
        return selected

    def should_load_missing_metadata(self) -> bool:
        """Check if missing metadata should be loaded."""
        return (self.load_metadata_switch is not None and
                self.load_metadata_switch.isChecked())

    def get_files_to_process(self) -> List:
        """Get the actual FileItem objects to process based on selections."""
        selected_extensions = self.get_selected_file_types()
        files_to_process = []

        for file_item in self.selected_files:
            ext = Path(file_item.filename).suffix.lower()
            if ext.startswith('.'):
                ext = ext[1:]

            if ext in selected_extensions:
                files_to_process.append(file_item)

        return files_to_process

    def get_missing_metadata_files(self) -> List:
        """Get files that need metadata loading."""
        if not self.should_load_missing_metadata():
            return []

        selected_extensions = self.get_selected_file_types()
        missing_to_load = []

        for file_item in self.missing_metadata_files:
            ext = Path(file_item.filename).suffix.lower()
            if ext.startswith('.'):
                ext = ext[1:]

            if ext in selected_extensions:
                missing_to_load.append(file_item)

        return missing_to_load

    @staticmethod
    def get_bulk_rotation_choice(parent: QWidget, files: List, metadata_cache) -> Tuple[bool, Dict]:
        """
        Show the bulk rotation dialog and return user choice.

        Args:
            parent: Parent widget
            files: List of FileItem objects
            metadata_cache: Metadata cache

        Returns:
            Tuple of (accepted, result_data) where result_data contains:
            - 'files_to_process': List of files to process
            - 'load_missing': List of files needing metadata loading
            - 'selected_extensions': Set of selected file extensions
        """
        dialog = BulkRotationDialog(parent)
        dialog.set_files(files, metadata_cache)

        if dialog.exec_() == QDialog.Accepted:
            result_data = {
                'files_to_process': dialog.get_files_to_process(),
                'load_missing': dialog.get_missing_metadata_files(),
                'selected_extensions': dialog.get_selected_file_types()
            }
            return True, result_data
        else:
            return False, {}
