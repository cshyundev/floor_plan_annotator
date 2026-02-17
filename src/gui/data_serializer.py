"""Data serialization for Canvas2D."""

from src.core.config import ConfigManager


class DataSerializer:
    """Manages saving and loading of canvas data to/from ProjectData format."""

    def __init__(self, canvas):
        """Initialize data serializer.

        Args:
            canvas: Canvas2D instance
        """
        self.canvas = canvas
        self._config = ConfigManager.instance()

    def save_to_data(self):
        """Convert scene items to ProjectData format.

        Returns:
            ProjectData instance containing all walls and rooms
        """
        from src.model.data import ProjectData, Wall, Room, Point2D
        from src.gui.items import NodeItem, EdgeItem, RoomItem

        data = ProjectData()

        # Iterate items
        # We need to capture connected walls and rooms.
        # Current data model stores Walls and Rooms with coordinates.

        items = self.canvas.scene.items()

        for item in items:
            if isinstance(item, EdgeItem):
                p1 = item.start_node.pos()
                p2 = item.end_node.pos()
                wall = Wall(
                    start=Point2D(p1.x(), p1.y()),
                    end=Point2D(p2.x(), p2.y())
                )
                data.walls.append(wall)
            elif isinstance(item, RoomItem):
                points = [Point2D(n.pos().x(), n.pos().y()) for n in item.nodes]
                room = Room(points=points)
                room.room_type = item.room_type
                room.id = item.room_id
                data.rooms.append(room)

        return data

    def load_from_data(self, data):
        """Recreate scene items from ProjectData format.

        Args:
            data: ProjectData instance to load
        """
        self.canvas.scene.clear()
        if hasattr(self.canvas, '_undo_stack') and self.canvas._undo_stack:
            self.canvas._undo_stack.clear()

        # Reset room ID counter to max(existing IDs) + 1
        self._reset_room_id_counter(data)

        # Recreate items
        from src.gui.items import NodeItem, EdgeItem, RoomItem

        # Helper to reuse nodes at same position
        nodes_at_pos = {}  # (x, y) -> NodeItem

        def get_or_create_node(x, y):
            key = (round(x, 4), round(y, 4))
            if key in nodes_at_pos:
                return nodes_at_pos[key]
            node = NodeItem(x, y)
            self.canvas.scene.addItem(node)
            nodes_at_pos[key] = node
            return node

        # Recreate walls
        self._load_walls(data, get_or_create_node)

        # Recreate rooms
        self._load_rooms(data, get_or_create_node)

        # Restore background if it exists
        self._restore_background()

    def _reset_room_id_counter(self, data):
        """Reset the room ID counter based on existing room IDs in data."""
        max_id = -1
        for room in data.rooms:
            try:
                max_id = max(max_id, int(room.id))
            except (ValueError, TypeError):
                pass
        self.canvas._next_room_id = max_id + 1

    def _load_walls(self, data, get_or_create_node):
        """Load walls from ProjectData."""
        from src.gui.items import EdgeItem

        for wall in data.walls:
            n1 = get_or_create_node(wall.start.x, wall.start.y)
            n2 = get_or_create_node(wall.end.x, wall.end.y)
            edge = EdgeItem(n1, n2)
            self.canvas.scene.addItem(edge)

    def _load_rooms(self, data, get_or_create_node):
        """Load rooms from ProjectData."""
        from src.gui.items import RoomItem, EdgeItem

        for room in data.rooms:
            nodes = []
            for p in room.points:
                n = get_or_create_node(p.x, p.y)
                nodes.append(n)

            if nodes:
                poly = RoomItem(nodes, room_type=room.room_type, room_id=room.id)
                self.canvas.scene.addItem(poly)

                # Ensure edges exist for room boundary
                self._create_room_boundary_edges(nodes)

    def _create_room_boundary_edges(self, nodes):
        """Create edges for room boundary if they don't already exist."""
        from src.gui.items import EdgeItem

        for i in range(len(nodes)):
            n_start = nodes[i]
            n_end = nodes[(i + 1) % len(nodes)]

            # Check if edge exists
            existing_edge = False
            for edge in n_start.edges:
                if edge.end_node == n_end or edge.start_node == n_end:
                    existing_edge = True
                    break

            if not existing_edge:
                edge = EdgeItem(n_start, n_end)
                self.canvas.scene.addItem(edge)

    def _restore_background(self):
        """Restore background item after scene.clear()."""
        if self.canvas.background_item:
            # scene.clear() removed it from scene, re-add it
            self.canvas.scene.addItem(self.canvas.background_item)
            z_value = self._config.get_value("colors", "background", "z_value") or -100
            self.canvas.background_item.setZValue(z_value)
