"""Main graphics view widget for the node editor.

This module provides QDMGraphicsView, the primary Qt view handling all
user interactions with the node graph:

- Zooming with mouse wheel
- Panning with middle mouse button
- Edge dragging and creation from sockets
- Edge cutting with Ctrl+Left-Click
- Node selection and dragging
- Edge rerouting with Ctrl+Click on connected socket
- Socket snapping during edge operations

The view integrates with EdgeDragging, EdgeRerouting, EdgeIntersect,
and EdgeSnapping tools to provide full interaction support.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from PyQt5.QtCore import QEvent, QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QWheelEvent,
)
from PyQt5.QtWidgets import QApplication, QGraphicsView

from oncutf.ui.widgets.node_editor.utils.helpers import dump_exception
from oncutf.ui.widgets.node_editor.utils.qt_helpers import (
    is_ctrl_pressed,
    is_shift_pressed,
)

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QGraphicsItem, QWidget

    from oncutf.ui.widgets.node_editor.graphics.scene import QDMGraphicsScene

# View mode constants
MODE_NOOP = 1  # Ready state
MODE_EDGE_DRAG = 2  # Dragging an edge
MODE_EDGE_CUT = 3  # Drawing cutting line
MODE_EDGES_REROUTING = 4  # Rerouting existing edges
MODE_NODE_DRAG = 5  # Dragging a node

STATE_STRING = ["", "Noop", "Edge Drag", "Edge Cut", "Edge Rerouting", "Node Drag"]

# Configuration constants
EDGE_DRAG_START_THRESHOLD = 50  # Distance threshold for edge drag
EDGE_REROUTING_UE = True  # Enable UnrealEngine style rerouting
EDGE_SNAPPING_RADIUS = 24  # Socket snapping distance
EDGE_SNAPPING = True  # Enable socket snapping


class QDMGraphicsView(QGraphicsView):
    """Graphics view managing node editor interactions.

    Handles zooming, panning, edge operations, and selection through
    a state machine with multiple interaction modes.

    Attributes:
        graphics_scene: QDMGraphicsScene being displayed.
        mode: Current interaction mode constant.
        zoom: Current zoom level integer.
        zoom_in_factor: Scaling factor per zoom step.
        zoom_clamp: Whether zoom is clamped to range.
        zoom_range: [min, max] zoom level range.
        last_scene_mouse_position: Last cursor position in scene coords.

    Signals:
        scene_pos_changed: Emitted with (x, y) when cursor moves.

    """

    scene_pos_changed = pyqtSignal(int, int)

    def __init__(self, graphics_scene: QDMGraphicsScene, parent: QWidget | None = None) -> None:
        """Initialize graphics view with a scene.

        Args:
            graphics_scene: QDMGraphicsScene to display.
            parent: Optional parent widget.

        """
        super().__init__(parent)
        self.graphics_scene = graphics_scene

        self.init_ui()
        self.setScene(self.graphics_scene)

        self.mode: int = MODE_NOOP
        self.editing_flag: bool = False
        self.rubber_band_dragging_rectangle: bool = False

        from oncutf.ui.widgets.node_editor.tools.edge_dragging import EdgeDragging

        self.dragging = EdgeDragging(self)

        from oncutf.ui.widgets.node_editor.tools.edge_rerouting import EdgeRerouting

        self.rerouting = EdgeRerouting(self)

        from oncutf.ui.widgets.node_editor.tools.edge_intersect import EdgeIntersect

        self.edgeIntersect = EdgeIntersect(self)

        from oncutf.ui.widgets.node_editor.tools.edge_snapping import EdgeSnapping

        self.snapping = EdgeSnapping(self, snapping_radius=EDGE_SNAPPING_RADIUS)

        from oncutf.ui.widgets.node_editor.graphics.cutline import QDMCutLine

        self.cutline = QDMCutLine()
        self.graphics_scene.addItem(self.cutline)

        self.last_scene_mouse_position = QPoint(0, 0)
        self.last_lmb_click_scene_pos: QPointF | None = None

        self.zoom_in_factor = 1.25
        self.zoom_clamp = True
        self.zoom = 10
        self.zoom_step = 1
        self.zoom_range = [0, 10]

        self._drag_enter_listeners: list = []
        self._drop_listeners: list = []

    def init_ui(self) -> None:
        """Configure rendering hints and viewport behavior."""
        self.setRenderHints(
            QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform
        )

        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        self.setAcceptDrops(True)

    def is_snapping_enabled(self, event: QMouseEvent | None = None) -> bool:
        """Check if socket snapping is active.

        Args:
            event: Mouse event to check for Ctrl modifier.

        Returns:
            True if snapping enabled and Ctrl pressed.

        """
        return EDGE_SNAPPING and is_ctrl_pressed(event) if event else True

    def reset_mode(self) -> None:
        """Reset state machine to default NOOP mode."""
        self.mode = MODE_NOOP

    def add_drag_enter_listener(self, callback) -> None:
        """Register callback for drag enter events.

        Args:
            callback: Function called on drag enter.

        """
        self._drag_enter_listeners.append(callback)

    def add_drop_listener(self, callback) -> None:
        """Register callback for drop events.

        Args:
            callback: Function called on drop.

        """
        self._drop_listeners.append(callback)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Dispatch drag enter to registered listeners.

        Args:
            event: Qt drag enter event.

        """
        for callback in self._drag_enter_listeners:
            callback(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Handle drag move to keep drag active over the view.

        Args:
            event: Qt drag move event.

        """
        for callback in self._drag_enter_listeners:
            callback(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Handle drag leave to properly terminate drag operations.

        Args:
            event: Qt drag leave event.

        """

    def dropEvent(self, event: QDropEvent) -> None:
        """Dispatch drop to registered listeners.

        Args:
            event: Qt drop event.

        """
        for callback in self._drop_listeners:
            callback(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Route mouse press to button-specific handler.

        Args:
            event: Qt mouse press event.

        """
        if event.button() == Qt.MiddleButton:
            self.middleMouseButtonPress(event)
        elif event.button() == Qt.LeftButton:
            self.leftMouseButtonPress(event)
        elif event.button() == Qt.RightButton:
            self.rightMouseButtonPress(event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Route mouse release to button-specific handler.

        Args:
            event: Qt mouse release event.

        """
        if event.button() == Qt.MiddleButton:
            self.middleMouseButtonRelease(event)
        elif event.button() == Qt.LeftButton:
            self.leftMouseButtonRelease(event)
        elif event.button() == Qt.RightButton:
            self.rightMouseButtonRelease(event)
        else:
            super().mouseReleaseEvent(event)

    def middleMouseButtonPress(self, event: QMouseEvent) -> None:
        """Start panning with middle mouse button.

        Enables scroll-hand drag mode by simulating left button events.

        Args:
            event: Qt mouse press event.

        """
        _ = self.getItemAtClick(event)

        release_event = QMouseEvent(
            QEvent.MouseButtonRelease,
            event.localPos(),
            event.screenPos(),
            Qt.LeftButton,
            Qt.NoButton,
            event.modifiers(),
        )
        super().mouseReleaseEvent(release_event)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        fake_event = QMouseEvent(
            event.type(),
            event.localPos(),
            event.screenPos(),
            Qt.LeftButton,
            event.buttons() | Qt.LeftButton,
            event.modifiers(),
        )
        super().mousePressEvent(fake_event)

    def middleMouseButtonRelease(self, event: QMouseEvent) -> None:
        """Stop panning and restore rubber band mode.

        Args:
            event: Qt mouse release event.

        """
        fake_event = QMouseEvent(
            event.type(),
            event.localPos(),
            event.screenPos(),
            Qt.LeftButton,
            event.buttons() & ~Qt.LeftButton,
            event.modifiers(),
        )
        super().mouseReleaseEvent(fake_event)
        self.setDragMode(QGraphicsView.RubberBandDrag)

    def leftMouseButtonPress(self, event: QMouseEvent) -> None:
        """Handle left click for selection and edge operations.

        Determines action based on clicked item and modifier keys:
        - Shift+click for multi-select
        - Socket click to start edge drag
        - Ctrl+socket click to start rerouting
        - Ctrl+empty click to start cut line

        Args:
            event: Qt mouse press event.

        """
        from oncutf.ui.widgets.node_editor.graphics.edge import QDMGraphicsEdge
        from oncutf.ui.widgets.node_editor.graphics.socket import QDMGraphicsSocket

        item = self.getItemAtClick(event)

        self.last_lmb_click_scene_pos = self.mapToScene(event.pos())

        if (
            hasattr(item, "node") or isinstance(item, QDMGraphicsEdge) or item is None
        ) and is_shift_pressed(event):
            event.ignore()
            fake_event = QMouseEvent(
                QEvent.MouseButtonPress,
                event.localPos(),
                event.screenPos(),
                Qt.LeftButton,
                event.buttons() | Qt.LeftButton,
                event.modifiers() | Qt.ControlModifier,
            )
            super().mousePressEvent(fake_event)
            return

        if hasattr(item, "node") and self.mode == MODE_NOOP:
            self.mode = MODE_NODE_DRAG
            self.edgeIntersect.enter_state(item.node)

        if self.is_snapping_enabled(event):
            item = self.snapping.getSnappedSocketItem(event)

        if isinstance(item, QDMGraphicsSocket):
            if self.mode == MODE_NOOP and is_ctrl_pressed(event):
                socket = item.socket
                if socket.has_any_edge():
                    self.mode = MODE_EDGES_REROUTING
                    self.rerouting.start_rerouting(socket)
                    return

            if self.mode == MODE_NOOP:
                self.mode = MODE_EDGE_DRAG
                self.dragging.edge_drag_start(item)
                return

        if self.mode == MODE_EDGE_DRAG:
            res = self.dragging.edge_drag_end(item)
            if res:
                return

        if item is None:
            if is_ctrl_pressed(event):
                self.mode = MODE_EDGE_CUT
                fake_event = QMouseEvent(
                    QEvent.MouseButtonRelease,
                    event.localPos(),
                    event.screenPos(),
                    Qt.LeftButton,
                    Qt.NoButton,
                    event.modifiers(),
                )
                super().mouseReleaseEvent(fake_event)
                QApplication.setOverrideCursor(Qt.CrossCursor)
                return
            self.rubberBandDraggingRectangle = True

        super().mousePressEvent(event)

    def leftMouseButtonRelease(self, event: QMouseEvent) -> None:
        """Handle left button release to complete operations.

        Finishes edge drag, rerouting, cutting, or selection based
        on current mode.

        Args:
            event: Qt mouse release event.

        """
        from oncutf.ui.widgets.node_editor.graphics.edge import QDMGraphicsEdge
        from oncutf.ui.widgets.node_editor.graphics.socket import QDMGraphicsSocket

        item = self.getItemAtClick(event)

        try:
            if (
                hasattr(item, "node") or isinstance(item, QDMGraphicsEdge) or item is None
            ) and is_shift_pressed(event):
                event.ignore()
                fake_event = QMouseEvent(
                    event.type(),
                    event.localPos(),
                    event.screenPos(),
                    Qt.LeftButton,
                    Qt.NoButton,
                    event.modifiers() | Qt.ControlModifier,
                )
                super().mouseReleaseEvent(fake_event)
                return

            if self.mode == MODE_EDGE_DRAG and self.distanceBetweenClickAndReleaseIsOff(event):
                if self.is_snapping_enabled(event):
                    item = self.snapping.getSnappedSocketItem(event)

                res = self.dragging.edge_drag_end(item)
                if res:
                    return

            if self.mode == MODE_EDGES_REROUTING:
                if self.is_snapping_enabled(event):
                    item = self.snapping.getSnappedSocketItem(event)

                if not EDGE_REROUTING_UE and not self.rerouting.first_mb_release:
                    self.rerouting.first_mb_release = True
                    return

                self.rerouting.stop_rerouting(
                    item.socket if isinstance(item, QDMGraphicsSocket) else None
                )
                self.mode = MODE_NOOP

            if self.mode == MODE_EDGE_CUT:
                self.cutIntersectingEdges()
                self.cutline.line_points = []
                self.cutline.update()
                QApplication.setOverrideCursor(Qt.ArrowCursor)
                self.mode = MODE_NOOP
                return

            if self.mode == MODE_NODE_DRAG:
                scenepos = self.mapToScene(event.pos())
                self.edgeIntersect.leave_state(scenepos.x(), scenepos.y())
                self.mode = MODE_NOOP
                self.update()

            if self.rubber_band_dragging_rectangle:
                self.rubber_band_dragging_rectangle = False
                current_selected_items = self.graphics_scene.selectedItems()

                if current_selected_items != self.graphics_scene.scene._last_selected_items:
                    if current_selected_items == []:
                        self.graphics_scene.items_deselected.emit()
                    else:
                        self.graphics_scene.item_selected.emit()
                    self.graphics_scene.scene._last_selected_items = current_selected_items

                super().mouseReleaseEvent(event)
                return

            if item is None:
                self.graphics_scene.items_deselected.emit()

        except Exception as e:
            dump_exception(e)

        super().mouseReleaseEvent(event)

    def rightMouseButtonPress(self, event: QMouseEvent) -> None:
        """Handle right mouse button press.

        Args:
            event: Qt mouse press event.

        """
        super().mousePressEvent(event)

    def rightMouseButtonRelease(self, event: QMouseEvent) -> None:
        """Handle right mouse button release.

        Args:
            event: Qt mouse release event.

        """
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Update interactions during mouse movement.

        Updates socket highlights, edge drag position, node drag
        position, rerouting position, or cut line based on mode.

        Args:
            event: Qt mouse move event.

        """
        if event is None:
            return

        scenepos = self.mapToScene(event.pos())

        try:
            modified = self.setSocketHighlights(
                scenepos, highlighted=False, radius=EDGE_SNAPPING_RADIUS + 100
            )
            if self.is_snapping_enabled(event):
                _, scenepos = self.snapping.getSnappedToSocketPosition(scenepos)
            if modified:
                self.update()

            if self.mode == MODE_EDGE_DRAG:
                self.dragging.update_destination(scenepos.x(), scenepos.y())

            if self.mode == MODE_NODE_DRAG:
                self.edgeIntersect.update(scenepos.x(), scenepos.y())

            if self.mode == MODE_EDGES_REROUTING:
                self.rerouting.update_scene_pos(scenepos.x(), scenepos.y())

            if self.mode == MODE_EDGE_CUT and self.cutline is not None:
                self.cutline.line_points.append(scenepos)
                self.cutline.update()

        except (RuntimeError, AttributeError) as e:
            # Ignore errors from deleted Qt objects during rapid movements
            dump_exception(e)
        except Exception as e:
            dump_exception(e)

        self.last_scene_mouse_position = scenepos

        with suppress(RuntimeError):
            self.scene_pos_changed.emit(int(scenepos.x()), int(scenepos.y()))

        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard input.

        Args:
            event: Qt key press event.

        """
        super().keyPressEvent(event)

    def cutIntersectingEdges(self) -> None:
        """Remove all edges intersecting the current cut line.

        Iterates through cut line segments and removes any edges
        that intersect. Stores history after completion.
        """
        for ix in range(len(self.cutline.line_points) - 1):
            p1 = self.cutline.line_points[ix]
            p2 = self.cutline.line_points[ix + 1]

            for edge in self.graphics_scene.scene.edges.copy():
                if edge.graphics_edge.intersects_with(p1, p2):
                    edge.remove()

        self.graphics_scene.scene.history.store_history("Delete cutted edges", set_modified=True)

    def setSocketHighlights(
        self, scenepos: QPointF, highlighted: bool = True, radius: float = 50
    ) -> list:
        """Set highlight state for sockets in an area.

        Args:
            scenepos: Center position for search area.
            highlighted: Whether to highlight or clear.
            radius: Search radius in scene coordinates.

        Returns:
            List of affected QDMGraphicsSocket items.

        """
        from oncutf.ui.widgets.node_editor.graphics.socket import QDMGraphicsSocket

        scanrect = QRectF(scenepos.x() - radius, scenepos.y() - radius, radius * 2, radius * 2)
        items = self.graphics_scene.items(scanrect)
        items = list(filter(lambda x: isinstance(x, QDMGraphicsSocket), items))

        for graphics_socket in items:
            graphics_socket.isHighlighted = highlighted

        return items

    def delete_selected(self) -> None:
        """Delete all currently selected nodes and edges.

        Removes selected items and stores undo history.
        """
        from oncutf.ui.widgets.node_editor.graphics.edge import QDMGraphicsEdge

        for item in self.graphics_scene.selectedItems():
            if isinstance(item, QDMGraphicsEdge):
                item.edge.remove()
            elif hasattr(item, "node"):
                item.node.remove()

        self.graphics_scene.scene.history.store_history("Delete selected", set_modified=True)

    def getItemAtClick(self, event: QEvent) -> QGraphicsItem | None:
        """Get graphics item at event position.

        Args:
            event: Qt event with position information.

        Returns:
            QGraphicsItem at position, or None.

        """
        pos = event.pos()
        return self.itemAt(pos)

    def distanceBetweenClickAndReleaseIsOff(self, event: QMouseEvent) -> bool:
        """Check if release position exceeds drag threshold.

        Used to distinguish click from drag on sockets.

        Args:
            event: Qt mouse release event.

        Returns:
            True if distance exceeds EDGE_DRAG_START_THRESHOLD.

        """
        new_lmb_release_scene_pos = self.mapToScene(event.pos())
        dist_scene = new_lmb_release_scene_pos - self.last_lmb_click_scene_pos
        edge_drag_threshold_sq = EDGE_DRAG_START_THRESHOLD * EDGE_DRAG_START_THRESHOLD
        return (dist_scene.x() ** 2 + dist_scene.y() ** 2) > edge_drag_threshold_sq

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zooming.

        Scales view centered on cursor position.

        Args:
            event: Qt wheel event.

        """
        # Determine zoom direction from wheel delta
        zoom_in = event.angleDelta().y() > 0

        zoom_out_factor = 1 / self.zoom_in_factor

        if zoom_in:
            zoom_factor = self.zoom_in_factor
            self.zoom += self.zoom_step
        else:
            zoom_factor = zoom_out_factor
            self.zoom -= self.zoom_step

        clamped = False
        if self.zoom < self.zoom_range[0]:
            self.zoom, clamped = self.zoom_range[0], True
        if self.zoom > self.zoom_range[1]:
            self.zoom, clamped = self.zoom_range[1], True

        if not clamped or self.zoom_clamp is False:
            self.scale(zoom_factor, zoom_factor)
