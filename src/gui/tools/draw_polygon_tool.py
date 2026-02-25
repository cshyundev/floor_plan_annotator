from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen

from src.core.input_context import InputContext
from src.core.undo_commands import AddItemCommand
from src.gui.items.nodes import NodeItem, EdgeItem
from src.gui.items.polygon_base import PolygonItem
from src.gui.tools.base import Tool


class DrawPolygonTool(Tool):
    """
    Base class for polygon-drawing tools.
    Handles node placement, temp edges, and polygon closing logic.
    Subclasses implement _finish_polygon() to create the final item.
    """

    def __init__(self, canvas):
        super().__init__(canvas)
        self.current_nodes = []
        self.temp_edges = []
        self._press_pos = None
        self._is_dragging = False
        self._passthrough = False

    def _find_polygon_item_at(self, scene_pos):
        """Return PolygonItem at scene_pos, or None."""
        for item in self.scene.items(scene_pos):
            if isinstance(item, PolygonItem):
                return item
        return None

    def on_mouse_press(self, context: InputContext):
        if not self.canvas._is_within_bounds(context.scene_pos):
            return
        if context.buttons == Qt.MouseButton.LeftButton:
            # If not drawing yet and clicking on an existing polygon, passthrough
            if not self.current_nodes and self._find_polygon_item_at(context.scene_pos) is not None:
                self._passthrough = True
                return
            self._press_pos = context.scene_pos
            self._is_dragging = False
        elif context.buttons == Qt.MouseButton.RightButton:
            self._handle_right_click()

    def on_mouse_move(self, context: InputContext):
        if self._passthrough:
            return

        # Show snap guide preview while drawing
        if self.current_nodes:
            anchor = self.current_nodes[-1].pos()
            self.snap_manager.snap_drawing_point(
                context.scene_pos,
                anchor_pos=anchor,
                modifiers=context.modifiers,
            )

        if self._press_pos is None:
            return
        DRAG_THRESHOLD = 5
        view = self.canvas
        press_view = view.mapFromScene(self._press_pos)
        curr_view = view.mapFromScene(context.scene_pos)
        dx = curr_view.x() - press_view.x()
        dy = curr_view.y() - press_view.y()
        if (dx * dx + dy * dy) > DRAG_THRESHOLD * DRAG_THRESHOLD:
            self._is_dragging = True

    def on_mouse_release(self, context: InputContext):
        if self._passthrough:
            self._passthrough = False
            return
        if self._press_pos is not None and not self._is_dragging:
            self._handle_left_click(context.scene_pos)
        self._press_pos = None
        self._is_dragging = False

    def _handle_left_click(self, pos):
        """Handle left click: add node or close polygon."""
        if not self.current_nodes:
            if self._is_clicking_existing_item(pos):
                return

        if self._should_close_polygon(pos):
            self.snap_manager.clear_guides()
            self._finish_polygon()
            return

        self._add_node(pos)

    def _is_clicking_existing_item(self, pos):
        """Check if clicking on an existing NodeItem or same-type polygon item."""
        items = self.scene.items(pos)
        for item in items:
            if isinstance(item, NodeItem):
                return True
        return self._find_polygon_item_at(pos) is not None

    def _should_close_polygon(self, pos):
        """Check if click is near first node (should close polygon)."""
        if len(self.current_nodes) < 3:
            return False

        first_node = self.current_nodes[0]
        tolerance_pixels = self.config.get_ui_value("room", "edge", "snap_tolerance")

        view = self.canvas
        first_view_pos = view.mapFromScene(first_node.pos())
        click_view_pos = view.mapFromScene(pos)

        dx = click_view_pos.x() - first_view_pos.x()
        dy = click_view_pos.y() - first_view_pos.y()
        distance_squared = dx * dx + dy * dy

        return distance_squared < (tolerance_pixels * tolerance_pixels)

    def _add_node(self, pos):
        """Add a new node to the current polygon."""
        anchor = self.current_nodes[-1].pos() if self.current_nodes else None
        snapped = self.snap_manager.snap_drawing_point(pos, anchor_pos=anchor)
        node = NodeItem(snapped.x(), snapped.y())
        self.scene.addItem(node)
        self.current_nodes.append(node)

        if len(self.current_nodes) > 1:
            prev = self.current_nodes[-2]
            temp_edge = self._create_temp_edge(prev, node)
            self.temp_edges.append(temp_edge)

        self.canvas.status_message.emit(
            self.config.get_string("tools", "room", "add_point").format(len(self.current_nodes))
        )

    def _handle_right_click(self):
        """Handle right click: finish polygon or cancel."""
        if len(self.current_nodes) < 3:
            self.cleanup()
            self.canvas.status_message.emit("Cancelled or not enough points.")
            return
        self._finish_polygon()

    def _finish_polygon(self) -> None:
        """Polygon complete: create item and add to scene. Subclasses must implement."""
        raise NotImplementedError

    def _create_temp_edge(self, start_node, end_node):
        """Create a temporary EdgeItem with polygon-specific color from config."""
        edge_color = self.config.get_color("room", "edge", "color")
        edge_width = self.config.get_ui_value("room", "edge", "width")
        room_pen = QPen(edge_color, edge_width)

        edge = EdgeItem(start_node, end_node)
        edge.pen_default = room_pen
        edge.pen_selected = room_pen
        edge.setPen(room_pen)
        self.scene.addItem(edge)
        return edge

    def _remove_temp_edges(self):
        for e in self.temp_edges:
            if e in e.start_node.edges:
                e.start_node.edges.remove(e)
            if e in e.end_node.edges:
                e.end_node.edges.remove(e)
            if e.scene() == self.scene:
                self.scene.removeItem(e)
        self.temp_edges = []

    def cleanup(self):
        self.snap_manager.clear_guides()
        self._remove_temp_edges()
        for n in self.current_nodes:
            if n.scene() == self.scene:
                self.scene.removeItem(n)
        self.current_nodes = []


class DrawRoomTool(DrawPolygonTool):
    """Draws room polygons. Prompts for room type on finish."""
    annotation_type = "room"

    def _find_polygon_item_at(self, scene_pos):
        """Return RoomItem at scene_pos, or None. Only same-type passthrough."""
        from src.gui.items.room_item import RoomItem
        for item in self.scene.items(scene_pos):
            if isinstance(item, RoomItem):
                return item
        return None

    def _finish_polygon(self):
        """Complete the polygon: clean up temp, select type, create RoomItem."""
        from src.gui.items.room_item import RoomItem

        self._remove_temp_edges()

        selected_key = self._select_room_type()

        for n in self.current_nodes:
            if n.scene() == self.scene:
                self.scene.removeItem(n)

        room_id = self.canvas.next_room_id()
        room_item = RoomItem(
            self.current_nodes,
            room_type=selected_key,
            room_id=room_id
        )

        all_items = self.current_nodes + [room_item]
        cmd = AddItemCommand(self.scene, all_items, "Add Room")
        self.canvas.push_command(cmd)

        self.current_nodes = []
        self.canvas.status_message.emit(f"Room '{selected_key}' created.")

    def _select_room_type(self):
        from PyQt6.QtGui import QCursor  # noqa: QCursor is in QtGui
        from src.gui.room_type_popup import RoomTypePopup
        popup = RoomTypePopup(self.canvas)
        popup.move(QCursor.pos())
        if popup.exec():
            selected = popup.get_selected_type()
            if selected:
                return selected
        default_type = self.config.get_value("rooms", "default_type")
        if default_type is None:
            raise KeyError("rooms key not found: default_type")
        return default_type


class DrawCustomPolygonTool(DrawPolygonTool):
    """Draws custom polygon annotations (e.g. clean zone, danger zone)."""
    annotation_type = "custom_polygon"

    def _find_polygon_item_at(self, scene_pos):
        """Return CustomPolygonItem at scene_pos, or None. Only same-type passthrough."""
        from src.gui.items.custom_polygon_item import CustomPolygonItem
        for item in self.scene.items(scene_pos):
            if isinstance(item, CustomPolygonItem):
                return item
        return None

    def _finish_polygon(self):
        """Complete the polygon: clean up temp, select type, create CustomPolygonItem."""
        from src.gui.items.custom_polygon_item import CustomPolygonItem

        self._remove_temp_edges()

        selected_key = self._select_custom_polygon_type()

        for n in self.current_nodes:
            if n.scene() == self.scene:
                self.scene.removeItem(n)

        polygon_id = self.canvas.next_custom_polygon_id()
        polygon_item = CustomPolygonItem(
            self.current_nodes,
            polygon_type=selected_key,
            polygon_id=polygon_id
        )

        all_items = self.current_nodes + [polygon_item]
        cmd = AddItemCommand(self.scene, all_items, "Add Custom Polygon")
        self.canvas.push_command(cmd)

        self.current_nodes = []
        self.canvas.status_message.emit(f"Custom polygon '{selected_key}' created.")

    def _select_custom_polygon_type(self):
        from PyQt6.QtGui import QCursor  # noqa: QCursor is in QtGui
        from src.gui.custom_polygon_type_popup import CustomPolygonTypePopup
        popup = CustomPolygonTypePopup(self.canvas)
        popup.move(QCursor.pos())
        if popup.exec():
            selected = popup.get_selected_type()
            if selected:
                return selected
        default_type = self.config.get_value("custom_polygons", "default_type")
        if default_type is None:
            raise KeyError("custom_polygons key not found: default_type")
        return default_type
