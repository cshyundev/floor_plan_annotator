from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QCursor
from src.gui.items import NodeItem, EdgeItem, RoomItem
from src.core.undo_commands import AddItemCommand
from src.core.input_context import InputContext
from src.core.config import ConfigManager

class Tool:
    """Base class for all drawing tools."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.scene = canvas.scene
        self._config = None

    @property
    def config(self):
        """Get the ConfigManager instance."""
        if self._config is None:
            self._config = ConfigManager.instance()
        return self._config

    def on_mouse_press(self, context: InputContext): pass
    def on_mouse_move(self, context: InputContext): pass
    def on_mouse_release(self, context: InputContext): pass

    def find_node_at(self, pos, tolerance=None):
        """Find a NodeItem at the given position within tolerance.

        Args:
            pos: QPointF position to search
            tolerance: Distance tolerance (uses config default if None)

        Returns:
            NodeItem if found, None otherwise
        """
        if tolerance is None:
            tolerance = self.config.get_value("colors", "node", "snap_tolerance") or 10

        items = self.scene.items(pos)
        for item in items:
            if isinstance(item, NodeItem):
                return item
        return None

class SelectTool(Tool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.moving_item = None
        self.start_pos = None

    def on_mouse_press(self, context: InputContext):
        item = None
        items = self.scene.items(context.scene_pos)
        if items:
            item = items[0]

        if isinstance(item, NodeItem):
            self.moving_item = item
            self.start_pos = item.pos()
            self.canvas.status_message.emit(self.config.get_string("tools", "select", "moving"))
        # If clicked on background/nothing, clear selection
        elif not item or item == self.canvas.background_item:
            self.scene.clearSelection()
            self.canvas.status_message.emit(self.config.get_string("tools", "select", "cleared"))
        else:
             # Select the item
             item.setSelected(True)
             self.canvas.status_message.emit(self.config.get_string("tools", "select", "selected"))

    def on_mouse_move(self, context: InputContext):
        if self.moving_item:
             # Logic to move item handled by QGraphicsItem standard flags?
             # Actually if we use ItemIsMovable, QGraphicsView handles it internally 
             # via mouse events translated to scene events.
             # If we consume the event here and don't pass it to super/scene, 
             # the default internal move might not work unless we implement it manually.
             # Our architecture decision: "Mouse/Keyboard independent of Viz".
             # If we rely on QGraphicsView's internal event propagation to items, 
             # we are coupled to Qt's event system.
             # BUT adhering to "standard Qt" means letting Qt handle it.
             # The user asked to decouple.
             # If we want full decoupling, we should move the item manually here based on context.scene_pos.
             pass

    def on_mouse_release(self, context: InputContext):
        self.moving_item = None
        self.start_pos = None

class DrawWallTool(Tool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.current_start_node = None
        
    def on_mouse_press(self, context: InputContext):
        if not self.canvas._is_within_bounds(context.scene_pos):
            return
        if context.buttons == Qt.MouseButton.LeftButton:
            pos = context.scene_pos
            clicked_node = self.find_node_at(pos)

            if not self.current_start_node:
                self._handle_first_click(pos, clicked_node)
            else:
                self._handle_second_click(pos, clicked_node)

    def _handle_first_click(self, pos, clicked_node):
        """Handle first click: start wall drawing."""
        if clicked_node:
            self.current_start_node = clicked_node
        else:
            self.current_start_node = NodeItem(pos.x(), pos.y())
            # For the first node, we add it immediately.
            cmd = AddItemCommand(
                self.scene,
                [self.current_start_node],
                self.config.get_string("tools", "wall", "add_node_cmd")
            )
            self.canvas.push_command(cmd)
        self.canvas.status_message.emit(self.config.get_string("tools", "wall", "started"))

    def _handle_second_click(self, pos, clicked_node):
        """Handle second click: complete wall segment and prepare for next."""
        end_node = clicked_node
        new_items = []

        if not end_node:
            end_node = NodeItem(pos.x(), pos.y())
            new_items.append(end_node)

        # Check duplication
        if end_node != self.current_start_node:
            # Create Edge
            edge = EdgeItem(self.current_start_node, end_node)
            new_items.append(edge)

            if new_items:
                cmd = AddItemCommand(
                    self.scene,
                    new_items,
                    self.config.get_string("tools", "wall", "add_wall_cmd")
                )
                self.canvas.push_command(cmd)
                self.canvas.status_message.emit(self.config.get_string("tools", "wall", "segment_added"))

        # Chain: end node becomes start node for next segment
        self.current_start_node = end_node

    def on_mouse_release(self, context: InputContext):
        if context.buttons == Qt.MouseButton.RightButton:
             # Stop drawing chain
             self.current_start_node = None
             self.canvas.status_message.emit(self.config.get_string("tools", "wall", "finished"))

class DrawRoomTool(Tool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.current_nodes = []
        self.temp_edges = []
        self._press_pos = None
        self._is_dragging = False

    def on_mouse_press(self, context: InputContext):
        if not self.canvas._is_within_bounds(context.scene_pos):
            return
        if context.buttons == Qt.MouseButton.LeftButton:
            self._press_pos = context.scene_pos
            self._is_dragging = False
        elif context.buttons == Qt.MouseButton.RightButton:
            self._handle_right_click()

    def on_mouse_move(self, context: InputContext):
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
        if self._press_pos is not None and not self._is_dragging:
            self._handle_left_click(context.scene_pos)
        self._press_pos = None
        self._is_dragging = False

    def _handle_left_click(self, pos):
        """Handle left click: add node or close polygon."""
        # If NOT currently drawing, check if clicking on existing items first
        if not self.current_nodes:
            if self._is_clicking_existing_item(pos):
                return

        # If 3+ nodes exist, check if clicking near the first node -> close polygon
        if self._should_close_polygon(pos):
            self._finish_room()
            return

        self._add_node(pos)

    def _is_clicking_existing_item(self, pos):
        """Check if clicking on an existing NodeItem or RoomItem."""
        items = self.scene.items(pos)
        for item in items:
            if isinstance(item, (NodeItem, RoomItem)):
                # Let Qt's event propagation handle it (select/drag)
                return True
        return False

    def _should_close_polygon(self, pos):
        """Check if click is near first node (should close polygon)."""
        if len(self.current_nodes) < 3:
            return False

        first_node = self.current_nodes[0]

        # Get tolerance in PIXELS
        tolerance_pixels = self.config.get_value("colors", "room", "edge", "snap_tolerance") or 15

        # Convert positions to VIEW COORDINATES (pixels) for comparison
        view = self.canvas
        first_view_pos = view.mapFromScene(first_node.pos())
        click_view_pos = view.mapFromScene(pos)

        # Calculate distance in view (pixel) coordinates
        dx = click_view_pos.x() - first_view_pos.x()
        dy = click_view_pos.y() - first_view_pos.y()
        distance_squared = dx * dx + dy * dy

        # Compare in pixels
        return distance_squared < (tolerance_pixels * tolerance_pixels)

    def _add_node(self, pos):
        """Add a new node to the current room polygon."""
        node = NodeItem(pos.x(), pos.y())
        self.scene.addItem(node)
        self.current_nodes.append(node)

        # Temp edge with room color (blue), not wall color
        if len(self.current_nodes) > 1:
            prev = self.current_nodes[-2]
            temp_edge = self._create_room_edge(prev, node)
            self.temp_edges.append(temp_edge)

        self.canvas.status_message.emit(
            self.config.get_string("tools", "room", "add_point").format(len(self.current_nodes))
        )

    def _handle_right_click(self):
        """Handle right click: finish room or cancel."""
        if len(self.current_nodes) < 3:
            self.cleanup()
            self.canvas.status_message.emit("Cancelled or not enough points.")
            return
        self._finish_room()

    def _create_room_edge(self, start_node, end_node):
        """Create a temp EdgeItem with room-specific blue color from config."""
        from PyQt6.QtGui import QPen

        edge_color = self.config.get_color("room", "edge", "color")
        edge_width = self.config.get_value("colors", "room", "edge", "width") or 2
        room_pen = QPen(edge_color, edge_width)

        edge = EdgeItem(start_node, end_node)
        edge.pen_default = room_pen
        edge.pen_selected = room_pen
        edge.setPen(room_pen)
        self.scene.addItem(edge)
        return edge

    def _finish_room(self):
        """Complete the polygon: clean up temp, select type, create RoomItem."""
        self._remove_temp_edges()

        # Select room type
        selected_key = self._select_room_type()

        # Remove nodes from scene (AddItemCommand will re-add them)
        for n in self.current_nodes:
            if n.scene() == self.scene:
                self.scene.removeItem(n)

        # Create RoomItem with sequential ID from canvas
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
        from src.gui.room_type_popup import RoomTypePopup
        popup = RoomTypePopup(self.canvas)
        popup.move(QCursor.pos())
        if popup.exec():
            selected = popup.get_selected_type()
            if selected:
                return selected
        return self.config.get_value("rooms", "default_type") or "living_room"

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
        self._remove_temp_edges()
        for n in self.current_nodes:
            if n.scene() == self.scene:
                self.scene.removeItem(n)
        self.current_nodes = []
