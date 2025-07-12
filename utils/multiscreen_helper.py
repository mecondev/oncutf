"""
Module: multiscreen_helper.py

Author: Michael Economou
Date: 2025-01-21

Utility functions for handling window positioning in multiscreen desktop environments.
Ensures dialogs and progress bars appear on the correct monitor relative to their parent window.
"""

from typing import Optional

from core.pyqt_imports import QApplication, QWidget, QScreen, QFileDialog
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def get_screen_for_widget(widget: QWidget) -> Optional[QScreen]:
    """
    Get the screen that contains the given widget.

    Args:
        widget: The widget to find the screen for

    Returns:
        QScreen object containing the widget, or None if not found
    """
    if not widget:
        return None

    app = QApplication.instance()
    if not app:
        return None

    # Get the center point of the widget
    widget_geometry = widget.frameGeometry()
    widget_center = widget_geometry.center()

    # Find the screen that contains the widget center
    for screen in app.screens():
        if screen.geometry().contains(widget_center):
            logger.debug(f"Found screen '{screen.name()}' for widget at {widget_center}")
            return screen

    # If widget is not on any screen, return primary screen
    primary_screen = app.primaryScreen()
    if primary_screen:
        logger.debug(f"Widget not on any screen, using primary screen '{primary_screen.name()}'")
    else:
        logger.warning("No primary screen found")

    return primary_screen


def center_dialog_on_parent_screen(dialog: QWidget, parent: Optional[QWidget] = None) -> None:
    """
    Center a dialog on the same screen as its parent widget.

    Args:
        dialog: The dialog to center
        parent: The parent widget. If None, uses dialog.parent()
    """
    target_parent = parent or dialog.parent()

    if not target_parent:
        # No parent, center on primary screen
        center_dialog_on_screen(dialog)
        return

    # Get the screen containing the parent
    parent_screen = get_screen_for_widget(target_parent)
    if not parent_screen:
        logger.warning("Could not find screen for parent widget")
        center_dialog_on_screen(dialog)
        return

    # Center the dialog on the parent's screen
    center_dialog_on_screen(dialog, parent_screen)


def center_dialog_on_screen(dialog: QWidget, screen: Optional[QScreen] = None) -> None:
    """
    Center a dialog on the specified screen.

    Args:
        dialog: The dialog to center
        screen: The screen to center on. If None, uses primary screen
    """
    app = QApplication.instance()
    if not app:
        return

    if not screen:
        screen = app.primaryScreen()

    if not screen:
        logger.warning("No screen available for centering dialog")
        return

    # Get the available geometry (excluding taskbars, docks, etc.)
    screen_geometry = screen.availableGeometry()

    # Get dialog size
    dialog_size = dialog.sizeHint()
    if dialog_size.isEmpty():
        dialog_size = dialog.size()

    # Calculate center position
    x = screen_geometry.x() + (screen_geometry.width() - dialog_size.width()) // 2
    y = screen_geometry.y() + (screen_geometry.height() - dialog_size.height()) // 2

    # Move dialog to center
    dialog.move(x, y)

    logger.debug(f"Centered dialog on screen '{screen.name()}' at ({x}, {y})")


def position_dialog_relative_to_parent(dialog: QWidget, parent: Optional[QWidget] = None) -> None:
    """
    Position a dialog relative to its parent widget, ensuring it stays on the same screen.

    Args:
        dialog: The dialog to position
        parent: The parent widget. If None, uses dialog.parent()
    """
    target_parent = parent or dialog.parent()

    if not target_parent:
        center_dialog_on_parent_screen(dialog)
        return

    # Get the screen containing the parent
    parent_screen = get_screen_for_widget(target_parent)
    if not parent_screen:
        center_dialog_on_parent_screen(dialog)
        return

    # Get parent geometry
    parent_geometry = target_parent.frameGeometry()
    dialog_size = dialog.sizeHint()
    if dialog_size.isEmpty():
        dialog_size = dialog.size()

    # Calculate position centered on parent
    x = parent_geometry.x() + (parent_geometry.width() - dialog_size.width()) // 2
    y = parent_geometry.y() + (parent_geometry.height() - dialog_size.height()) // 2

    # Ensure the dialog stays within the parent's screen bounds
    screen_geometry = parent_screen.availableGeometry()

    # Adjust if dialog would go off-screen
    if x < screen_geometry.x():
        x = screen_geometry.x()
    elif x + dialog_size.width() > screen_geometry.x() + screen_geometry.width():
        x = screen_geometry.x() + screen_geometry.width() - dialog_size.width()

    if y < screen_geometry.y():
        y = screen_geometry.y()
    elif y + dialog_size.height() > screen_geometry.y() + screen_geometry.height():
        y = screen_geometry.y() + screen_geometry.height() - dialog_size.height()

    # Move dialog to calculated position
    dialog.move(x, y)

    logger.debug(f"Positioned dialog relative to parent on screen '{parent_screen.name()}' at ({x}, {y})")


def ensure_dialog_on_parent_screen(dialog: QWidget, parent: Optional[QWidget] = None) -> None:
    """
    Ensure a dialog is positioned on the same screen as its parent.
    This is the main function to use for dialog positioning.

    Args:
        dialog: The dialog to position
        parent: The parent widget. If None, uses dialog.parent()
    """
    try:
        position_dialog_relative_to_parent(dialog, parent)
    except Exception as e:
        logger.error(f"Error positioning dialog: {e}")
        # Fallback to simple centering
        try:
            center_dialog_on_parent_screen(dialog, parent)
        except Exception as e2:
            logger.error(f"Error in fallback positioning: {e2}")
            # Final fallback - just move to a safe position
            dialog.move(100, 100)


def get_existing_directory_on_parent_screen(parent: Optional[QWidget] = None,
                                          caption: str = "Select Directory",
                                          directory: str = "",
                                          options: QFileDialog.Options = QFileDialog.ShowDirsOnly) -> str:
    """
    Show a directory selection dialog positioned on the same screen as the parent.

    Args:
        parent: Parent widget
        caption: Dialog caption
        directory: Initial directory
        options: Dialog options

    Returns:
        Selected directory path, or empty string if cancelled
    """
    # For static methods, we need to use a different approach
    # Create a temporary dialog and position it properly
    dialog = QFileDialog(parent, caption, directory)
    dialog.setFileMode(QFileDialog.Directory)
    dialog.setOptions(options)

    # Position the dialog on the parent's screen
    if parent:
        ensure_dialog_on_parent_screen(dialog, parent)

    # Show the dialog and get result
    if dialog.exec_() == QFileDialog.Accepted:
        selected_dirs = dialog.selectedFiles()
        return selected_dirs[0] if selected_dirs else ""

    return ""


def get_open_file_name_on_parent_screen(parent: Optional[QWidget] = None,
                                       caption: str = "Open File",
                                       directory: str = "",
                                       filter: str = "",
                                       options: QFileDialog.Options = QFileDialog.Options()) -> tuple[str, str]:
    """
    Show a file selection dialog positioned on the same screen as the parent.

    Args:
        parent: Parent widget
        caption: Dialog caption
        directory: Initial directory
        filter: File filter string
        options: Dialog options

    Returns:
        Tuple of (selected_file_path, selected_filter)
    """
    dialog = QFileDialog(parent, caption, directory, filter)
    dialog.setFileMode(QFileDialog.ExistingFile)
    dialog.setOptions(options)

    # Position the dialog on the parent's screen
    if parent:
        ensure_dialog_on_parent_screen(dialog, parent)

    # Show the dialog and get result
    if dialog.exec_() == QFileDialog.Accepted:
        selected_files = dialog.selectedFiles()
        selected_filter = dialog.selectedNameFilter()
        return (selected_files[0] if selected_files else "", selected_filter)

    return ("", "")


def get_save_file_name_on_parent_screen(parent: Optional[QWidget] = None,
                                       caption: str = "Save File",
                                       directory: str = "",
                                       filter: str = "",
                                       options: QFileDialog.Options = QFileDialog.Options()) -> tuple[str, str]:
    """
    Show a save file dialog positioned on the same screen as the parent.

    Args:
        parent: Parent widget
        caption: Dialog caption
        directory: Initial directory
        filter: File filter string
        options: Dialog options

    Returns:
        Tuple of (selected_file_path, selected_filter)
    """
    dialog = QFileDialog(parent, caption, directory, filter)
    dialog.setFileMode(QFileDialog.AnyFile)
    dialog.setAcceptMode(QFileDialog.AcceptSave)
    dialog.setOptions(options)

    # Position the dialog on the parent's screen
    if parent:
        ensure_dialog_on_parent_screen(dialog, parent)

    # Show the dialog and get result
    if dialog.exec_() == QFileDialog.Accepted:
        selected_files = dialog.selectedFiles()
        selected_filter = dialog.selectedNameFilter()
        return (selected_files[0] if selected_files else "", selected_filter)

    return ("", "")
