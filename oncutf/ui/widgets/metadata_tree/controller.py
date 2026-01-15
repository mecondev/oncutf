"""Module: controller.py

Author: Michael Economou
Date: 2025-12-23

Controller layer for the metadata tree widget.

This module contains the controller that orchestrates between the service
layer (business logic) and the view layer (Qt UI):
- Converts TreeNodeData to QStandardItemModel for display
- Handles user interactions (selection, editing, context menu)
- Manages state synchronization
- Coordinates with staging manager

The controller is Qt-aware but delegates business logic to the service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.config import METADATA_ICON_COLORS
from oncutf.core.pyqt_imports import QColor, QFont, QStandardItem, QStandardItemModel
from oncutf.ui.widgets.metadata_tree.model import (
    FieldStatus,
    MetadataDisplayState,
    TreeNodeData,
)
from oncutf.ui.widgets.metadata_tree.service import MetadataTreeService
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.ui.tooltip_helper import TooltipHelper, TooltipType

if TYPE_CHECKING:
    from oncutf.core.metadata import MetadataStagingManager

logger = get_cached_logger(__name__)


class MetadataTreeController:
    """Controller for metadata tree widget.

    This class orchestrates between the service layer (pure business logic)
    and the view layer (Qt widgets). It handles:
    - Converting TreeNodeData to QStandardItemModel
    - Styling items based on FieldStatus
    - User interaction events
    - State management

    Usage:
        controller = MetadataTreeController(service, staging_manager)
        qt_model = controller.build_qt_model(metadata, display_state)
    """

    def __init__(
        self,
        service: MetadataTreeService,
        staging_manager: MetadataStagingManager | None = None,
    ) -> None:
        """Initialize the controller.

        Args:
            service: The business logic service
            staging_manager: Optional staging manager for modifications

        """
        self._service = service
        self._staging_manager = staging_manager

        if staging_manager:
            self._service.set_staging_manager(staging_manager)

    def build_qt_model(
        self,
        metadata: dict[str, Any],
        display_state: MetadataDisplayState,
    ) -> QStandardItemModel:
        """Build a QStandardItemModel from metadata.

        This is the main entry point for creating a Qt model ready for display.
        It delegates business logic to the service and handles Qt presentation.

        Args:
            metadata: Raw metadata dictionary
            display_state: Current display state

        Returns:
            QStandardItemModel ready for QTreeView

        """
        logger.debug(
            "[MetadataTreeController] Building Qt model for: %s",
            display_state.file_path,
            extra={"dev_only": True},
        )

        # Get pure data structure from service
        tree_data = self._service.build_tree_data(metadata, display_state)

        # Convert to Qt model
        qt_model = self._convert_to_qt_model(tree_data)

        logger.debug(
            "[MetadataTreeController] Qt model built: %d groups",
            qt_model.invisibleRootItem().rowCount(),
            extra={"dev_only": True},
        )

        return qt_model

    def _convert_to_qt_model(self, root: TreeNodeData) -> QStandardItemModel:
        """Convert TreeNodeData hierarchy to QStandardItemModel.

        Args:
            root: Root TreeNodeData node

        Returns:
            QStandardItemModel with styled items

        """
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Key", "Value"])
        root_item = model.invisibleRootItem()

        # Process each group
        for group_node in root.children:
            group_item, value_item = self._create_group_items(group_node)

            # Add field items to group
            for field_node in group_node.children:
                field_key_item, field_value_item = self._create_field_items(field_node)
                group_item.appendRow([field_key_item, field_value_item])

            root_item.appendRow([group_item, value_item])

        return model

    def _create_group_items(self, group_node: TreeNodeData) -> tuple[QStandardItem, QStandardItem]:
        """Create QStandardItem pair for a group node.

        Args:
            group_node: The group TreeNodeData

        Returns:
            Tuple of (key_item, value_item)

        """
        # Check if group has extended metadata
        has_extended = any(child.status == FieldStatus.EXTENDED for child in group_node.children)

        # Format display name
        if has_extended:
            display_name = f"{group_node.key} [Extended] {group_node.value}"
        else:
            display_name = f"{group_node.key} {group_node.value}"

        # Create styled group item
        group_item = QStandardItem(display_name)
        group_item.setEditable(False)
        group_item.setSelectable(False)

        # Set font
        group_font = QFont()
        group_font.setBold(True)
        group_font.setPointSize(10)
        group_item.setFont(group_font)

        # Add tooltip for extended groups
        if has_extended:
            extended_count = sum(
                1 for child in group_node.children if child.status == FieldStatus.EXTENDED
            )
            group_item.setToolTip(f"Contains {extended_count} keys from extended metadata")

        # Create dummy value item for second column
        value_item = QStandardItem("")
        value_item.setSelectable(False)

        return group_item, value_item

    def _create_field_items(self, field_node: TreeNodeData) -> tuple[QStandardItem, QStandardItem]:
        """Create QStandardItem pair for a field node.

        Args:
            field_node: The field TreeNodeData

        Returns:
            Tuple of (key_item, value_item)

        """
        # Format the key (with smart simplification)
        formatted_key = self._service.format_key(field_node.key)

        # Create items
        key_item = QStandardItem(formatted_key)
        value_item = QStandardItem(field_node.value)

        # Add custom tooltip with original key if it was simplified
        if formatted_key != field_node.key:
            TooltipHelper.set_tooltip(
                key_item,
                field_node.key,
                tooltip_type=TooltipType.INFO
            )

        # Apply styling based on status
        self._apply_field_styling(key_item, value_item, field_node.status, formatted_key)

        return key_item, value_item

    def _apply_field_styling(
        self,
        key_item: QStandardItem,
        value_item: QStandardItem,
        status: FieldStatus,
        formatted_key: str,
    ) -> None:
        """Apply styling to field items based on status.

        Args:
            key_item: The key QStandardItem
            value_item: The value QStandardItem
            status: The field status
            formatted_key: Human-readable formatted key

        """
        if status == FieldStatus.MODIFIED:
            # Modified metadata styling - yellow text + bold
            modified_font = QFont()
            modified_font.setBold(True)
            key_item.setFont(modified_font)
            value_item.setFont(modified_font)

            # Yellow color from config
            modified_color = QColor(METADATA_ICON_COLORS["modified"])
            key_item.setForeground(modified_color)
            value_item.setForeground(modified_color)

            # Tooltips
            key_item.setToolTip("Modified value")
            value_item.setToolTip("Modified value")

        elif status == FieldStatus.EXTENDED:
            # Extended metadata styling - italic + blue
            extended_font = QFont()
            extended_font.setItalic(True)
            key_item.setFont(extended_font)
            value_item.setFont(extended_font)

            # Add [Ext] prefix to key
            key_item.setText(f"[Ext] {formatted_key}")

            # Light blue color
            extended_color = QColor(100, 150, 255)
            key_item.setForeground(extended_color)

            # Tooltips
            key_item.setToolTip("Available only in extended metadata mode")
            value_item.setToolTip("Available only in extended metadata mode")

    def get_field_count(self, metadata: dict[str, Any]) -> int:
        """Get total field count.

        Args:
            metadata: Metadata dictionary

        Returns:
            Total number of fields

        """
        return self._service.get_field_count(metadata)

    def get_modification_count(self, display_state: MetadataDisplayState) -> int:
        """Get modification count.

        Args:
            display_state: Current display state

        Returns:
            Number of modified fields

        """
        return self._service.get_modification_count(display_state)


def create_metadata_tree_controller(
    service: MetadataTreeService | None = None,
    staging_manager: MetadataStagingManager | None = None,
) -> MetadataTreeController:
    """Factory function to create a configured MetadataTreeController.

    Args:
        service: Optional service instance (creates new if None)
        staging_manager: Optional staging manager

    Returns:
        Configured controller instance

    """
    if service is None:
        from oncutf.ui.widgets.metadata_tree.service import create_metadata_tree_service

        service = create_metadata_tree_service()

    controller = MetadataTreeController(service, staging_manager)

    logger.debug(
        "[MetadataTreeController] Controller created",
        extra={"dev_only": True},
    )

    return controller
