"""
companion_files_widget.py

Widget for managing companion files settings and preferences.
Allows users to control how companion/sidecar files are handled.

Author: Michael Economou
Date: 2025-11-25
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from oncutf.config import (
    AUTO_RENAME_COMPANION_FILES,
    COMPANION_FILES_ENABLED,
    DEFAULT_COMPANION_FILE_MODE,
    LOAD_COMPANION_METADATA,
    SHOW_COMPANION_FILES_IN_TABLE,
    CompanionFileMode,
)
from oncutf.core.theme_manager import get_theme_manager
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.tooltip_helper import TooltipHelper, TooltipType

logger = get_cached_logger(__name__)


class CompanionFilesWidget(QWidget):
    """
    Widget for companion files settings.

    Allows users to control:
    - Whether companion files are detected and handled
    - How companion files are displayed in the file table
    - Whether companion files are automatically renamed
    - Whether metadata is loaded from companion files
    """

    settings_changed = pyqtSignal(dict)  # Emits updated settings dictionary

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Main enable/disable
        self.enabled_checkbox = QCheckBox("Enable companion files detection")
        TooltipHelper.setup_tooltip(
            self.enabled_checkbox,
            "Automatically detect companion files (like Sony XML metadata files, XMP sidecar files, etc.)",
            TooltipType.INFO
        )
        self.enabled_checkbox.toggled.connect(self._on_settings_changed)
        layout.addWidget(self.enabled_checkbox)

        # Display options group
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)

        self.display_button_group = QButtonGroup(self)

        self.hide_radio = QRadioButton("Hide companion files from file table")
        TooltipHelper.setup_tooltip(
            self.hide_radio,
            "Companion files are detected but not shown in the main file list",
            TooltipType.INFO
        )
        self.display_button_group.addButton(self.hide_radio, 0)
        display_layout.addWidget(self.hide_radio)

        self.show_radio = QRadioButton("Show companion files in file table")
        TooltipHelper.setup_tooltip(
            self.show_radio,
            "Companion files are shown alongside main files",
            TooltipType.INFO
        )
        self.display_button_group.addButton(self.show_radio, 1)
        display_layout.addWidget(self.show_radio)

        self.grouped_radio = QRadioButton("Show companion files grouped with main files")
        TooltipHelper.setup_tooltip(
            self.grouped_radio,
            "Companion files are shown but grouped/indented under main files",
            TooltipType.INFO
        )
        self.grouped_radio.setEnabled(False)  # Future feature
        self.display_button_group.addButton(self.grouped_radio, 2)
        display_layout.addWidget(self.grouped_radio)

        # Add note about grouped mode
        grouped_note = QLabel("(Grouped display is planned for a future version)")
        theme = get_theme_manager()
        grouped_note.setStyleSheet(f"color: {theme.get_color('text_muted')}; font-style: italic; font-size: 10px;")
        display_layout.addWidget(grouped_note)

        self.display_button_group.buttonToggled.connect(self._on_settings_changed)
        layout.addWidget(display_group)

        # Behavior options group
        behavior_group = QGroupBox("Behavior Options")
        behavior_layout = QVBoxLayout(behavior_group)

        self.auto_rename_checkbox = QCheckBox("Automatically rename companion files when main file is renamed")
        TooltipHelper.setup_tooltip(
            self.auto_rename_checkbox,
            "When you rename a video file, its companion XML file will also be renamed to match",
            TooltipType.INFO
        )
        self.auto_rename_checkbox.toggled.connect(self._on_settings_changed)
        behavior_layout.addWidget(self.auto_rename_checkbox)

        self.load_metadata_checkbox = QCheckBox("Load metadata from companion files")
        TooltipHelper.setup_tooltip(
            self.load_metadata_checkbox,
            "Extract and display metadata from companion files (like Sony XML files) in the metadata view",
            TooltipType.INFO
        )
        self.load_metadata_checkbox.toggled.connect(self._on_settings_changed)
        behavior_layout.addWidget(self.load_metadata_checkbox)

        layout.addWidget(behavior_group)

        # Information section
        info_group = QGroupBox("Companion Files Information")
        info_layout = QVBoxLayout(info_group)

        info_text = QLabel(
            "Companion files are additional files created by cameras and other devices "
            "that contain metadata or settings related to your main media files. Common examples:\n\n"
            "• Sony cameras: C8227.MP4 + C8227M01.XML (metadata)\n"
            "• RAW images: IMG_1234.CR2 + IMG_1234.xmp (editing data)\n"
            "• Videos: movie.mp4 + movie.srt (subtitles)\n\n"
            "OnCutF can automatically detect and handle these files to keep them "
            "synchronized with your main files."
        )
        info_text.setWordWrap(True)
        theme = get_theme_manager()
        info_text.setStyleSheet(f"color: {theme.get_color('text_muted')}; font-size: 11px; padding: 8px;")
        info_layout.addWidget(info_text)

        layout.addWidget(info_group)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.detect_button = QPushButton("Detect Companion Files in Current Folder")
        TooltipHelper.setup_tooltip(
            self.detect_button,
            "Scan the current folder for companion files and show a report",
            TooltipType.INFO
        )
        self.detect_button.clicked.connect(self._detect_companion_files)
        buttons_layout.addWidget(self.detect_button)

        buttons_layout.addStretch()

        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self._reset_to_defaults)
        buttons_layout.addWidget(self.reset_button)

        layout.addLayout(buttons_layout)

        # Connect enabled state to other controls
        self.enabled_checkbox.toggled.connect(self._update_controls_state)

    def load_current_settings(self):
        """Load current settings from configuration."""
        # Load from config
        self.enabled_checkbox.setChecked(COMPANION_FILES_ENABLED)
        self.auto_rename_checkbox.setChecked(AUTO_RENAME_COMPANION_FILES)
        self.load_metadata_checkbox.setChecked(LOAD_COMPANION_METADATA)

        # Set display mode
        if SHOW_COMPANION_FILES_IN_TABLE:
            self.show_radio.setChecked(True)
        # Check if using grouped mode (future feature)
        elif CompanionFileMode["GROUPED"] == DEFAULT_COMPANION_FILE_MODE:
            self.grouped_radio.setChecked(True)
        else:
            self.hide_radio.setChecked(True)

        self._update_controls_state()

    def get_current_settings(self) -> dict:
        """Get current settings as dictionary."""
        display_mode = CompanionFileMode["HIDE"]  # Default

        if self.show_radio.isChecked():
            display_mode = CompanionFileMode["SHOW"]
        elif self.grouped_radio.isChecked():
            display_mode = CompanionFileMode["GROUPED"]

        return {
            'enabled': self.enabled_checkbox.isChecked(),
            'show_in_table': self.show_radio.isChecked(),
            'auto_rename': self.auto_rename_checkbox.isChecked(),
            'load_metadata': self.load_metadata_checkbox.isChecked(),
            'display_mode': display_mode
        }

    def _update_controls_state(self):
        """Update enabled state of controls based on main checkbox."""
        enabled = self.enabled_checkbox.isChecked()

        # Enable/disable all sub-controls
        for radio in [self.hide_radio, self.show_radio, self.grouped_radio]:
            radio.setEnabled(enabled)

        self.auto_rename_checkbox.setEnabled(enabled)
        self.load_metadata_checkbox.setEnabled(enabled)
        self.detect_button.setEnabled(enabled)

    def _on_settings_changed(self):
        """Handle settings changes."""
        settings = self.get_current_settings()
        self.settings_changed.emit(settings)
        logger.debug("[CompanionFilesWidget] Settings changed: %s", settings)

    def _detect_companion_files(self):
        """Detect companion files in current folder and show report."""
        try:
            # This would need to be connected to the main application
            # to get the current folder and file list
            from PyQt5.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                "Companion Files Detection",
                "This feature will scan the current folder for companion files.\n\n"
                "To implement this, connect this widget to your main application "
                "to access the current folder path and file list."
            )

        except Exception as e:
            logger.error("[CompanionFilesWidget] Error detecting companion files: %s", e)

    def _reset_to_defaults(self):
        """Reset settings to default values."""
        self.enabled_checkbox.setChecked(True)
        self.hide_radio.setChecked(True)
        self.auto_rename_checkbox.setChecked(True)
        self.load_metadata_checkbox.setChecked(True)

        self._on_settings_changed()
        logger.info("[CompanionFilesWidget] Settings reset to defaults")

    def apply_settings(self, settings: dict):
        """Apply settings from external source."""
        if 'enabled' in settings:
            self.enabled_checkbox.setChecked(settings['enabled'])

        if 'show_in_table' in settings:
            if settings['show_in_table']:
                self.show_radio.setChecked(True)
            else:
                self.hide_radio.setChecked(True)

        if 'auto_rename' in settings:
            self.auto_rename_checkbox.setChecked(settings['auto_rename'])

        if 'load_metadata' in settings:
            self.load_metadata_checkbox.setChecked(settings['load_metadata'])

        self._update_controls_state()
        logger.debug("[CompanionFilesWidget] Applied settings: %s", settings)


class CompanionFilesDialog(QWidget):
    """
    Standalone dialog for companion files settings.
    Can be opened from settings menu or toolbar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Companion Files Settings")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        # Add the main widget
        self.companion_widget = CompanionFilesWidget(self)
        layout.addWidget(self.companion_widget)

        # Add dialog buttons
        from PyQt5.QtWidgets import QDialogButtonBox

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self._apply_settings)
        layout.addWidget(button_box)

        # Connect signals
        self.companion_widget.settings_changed.connect(self._on_settings_changed)

    def _on_settings_changed(self, settings):
        """Handle settings changes."""
        logger.debug("[CompanionFilesDialog] Settings changed: %s", settings)
        # Here you would save settings to config or emit signal to main app

    def _apply_settings(self):
        """Apply current settings."""
        settings = self.companion_widget.get_current_settings()
        logger.info("[CompanionFilesDialog] Applying settings: %s", settings)
        # Here you would save settings and apply them

    def accept(self):
        """Accept and apply settings."""
        self._apply_settings()
        super().accept()

    def reject(self):
        """Cancel without applying."""
        super().reject()
