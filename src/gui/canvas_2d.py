from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from src.gui.tools import SelectTool, DrawWallTool, DrawRoomTool
from src.core.config import ConfigManager

class Canvas2D(QGraphicsView):
    status_message = pyqtSignal(str)
    
    def __init__(self, main_window=None):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Items
        self.background_item = None
        
        # Undo
        self._undo_stack = None
        
        # Tools
        self.select_tool = SelectTool(self)
        self.wall_tool = DrawWallTool(self)
        self.room_tool = DrawRoomTool(self)
        self.current_tool = self.select_tool
        
        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag) # Tools handle drag
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        # Grid
        self.grid_pen = QPen(QColor(60, 60, 60))
        self.grid_pen.setWidth(0)

    def set_undo_stack(self, stack):
        self._undo_stack = stack
        
    def push_command(self, command):
        stack = self._undo_stack
        print(f"Canvas2D.push_command local stack: {stack}")
        if stack is not None:
            stack.push(command)
        else:
            command.redo()


    def set_tool(self, tool_name):
        config = ConfigManager.instance()
        if tool_name == "select":
            self.current_tool = self.select_tool
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Allow panning in select mode
            self.status_message.emit(config.get_string("tools", "select", "status"))
        elif tool_name == "wall":
            self.current_tool = self.wall_tool
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.status_message.emit(config.get_string("tools", "wall", "status"))
        elif tool_name == "room":
            self.current_tool = self.room_tool
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.status_message.emit("Room Tool: Left Click to add points, Right Click to finish.")
            
    def update_background(self, image_data, origin, scale):
        """
        Updates the background image.
        image_data: numpy array (grayscale)
        origin: (min_x, min_y, max_x, max_y) in world coords
        scale: pixels per meter
        """
        if image_data is None:
            return
            
        height, width = image_data.shape
        bytes_per_line = width
        
        q_image = QImage(image_data.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_image)
        
        if self.background_item:
            self.scene.removeItem(self.background_item)
            
        self.background_item = QGraphicsPixmapItem(pixmap)
        config = ConfigManager.instance()
        self.background_item.setZValue(config.get_value("colors", "background", "z_value") or -100) # Background
        self.scene.addItem(self.background_item)
        
        # TODO: Adjust coordinate system.
        
    def wheelEvent(self, event):
        """Zoom with mouse wheel"""
        config = ConfigManager.instance()
        zoom_in = event.angleDelta().y() > 0
        factor = 1.1 if zoom_in else 0.9
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        # Translate Qt event to InputContext
        # Note: mapToScene(event.pos()) works for QMouseEvent in QGraphicsView
        from src.core.input_context import InputContext
        
        scene_pos = self.mapToScene(event.pos())
        context = InputContext(
            scene_pos=scene_pos,
            screen_pos=event.pos(),
            buttons=event.buttons(),
            modifiers=event.modifiers()
        )
        
        if self.current_tool:
            self.current_tool.on_mouse_press(context)
            
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        from src.core.input_context import InputContext
        
        scene_pos = self.mapToScene(event.pos())
        context = InputContext(
            scene_pos=scene_pos,
            screen_pos=event.pos(),
            buttons=event.buttons(),
            modifiers=event.modifiers()
        )

        if self.current_tool:
            self.current_tool.on_mouse_move(context)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        from src.core.input_context import InputContext
        
        scene_pos = self.mapToScene(event.pos())
        context = InputContext(
            scene_pos=scene_pos,
            screen_pos=event.pos(),
            buttons=event.buttons(),
            modifiers=event.modifiers()
        )

        if self.current_tool:
            self.current_tool.on_mouse_release(context)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        config = ConfigManager.instance()
        delete_keys = config.get_shortcut("tools", "delete") or ["Delete", "Backspace"]
        
        key_map = {
            "Delete": Qt.Key.Key_Delete,
            "Backspace": Qt.Key.Key_Backspace,
        }
        
        triggered = False
        for k_name in delete_keys:
            if k_name in key_map and event.key() == key_map[k_name]:
                triggered = True
                break
                
        if triggered:
            self.delete_selected_items()
            
        super().keyPressEvent(event)
        
    def delete_selected_items(self):
        items = self.scene.selectedItems()
        for item in items:
            self.scene.removeItem(item)

    def save_to_data(self) -> 'ProjectData':
        from src.model.data import ProjectData, Wall, Room, Point2D
        from src.gui.items import NodeItem, EdgeItem, RoomItem
        
        data = ProjectData()
        
        # Iterate items
        # We need to capture connected walls and rooms.
        # Current data model stores Walls and Rooms with coordinates.
        
        items = self.scene.items()
        
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

    def load_from_data(self, data: 'ProjectData'):
        self.scene.clear()
        if self.undo_stack:
            self.undo_stack.clear()
        
        # Recreate items
        from src.gui.items import NodeItem, EdgeItem, RoomItem
        
        # Helper to reuse nodes at same position
        nodes_at_pos = {} # (x, y) -> NodeItem
        
        def get_or_create_node(x, y):
            key = (round(x, 4), round(y, 4))
            if key in nodes_at_pos:
                return nodes_at_pos[key]
            node = NodeItem(x, y)
            self.scene.addItem(node)
            nodes_at_pos[key] = node
            return node
            
        # Walls
        for wall in data.walls:
            n1 = get_or_create_node(wall.start.x, wall.start.y)
            n2 = get_or_create_node(wall.end.x, wall.end.y)
            edge = EdgeItem(n1, n2)
            self.scene.addItem(edge)
            
        # Rooms
        for room in data.rooms:
            nodes = []
            for p in room.points:
                n = get_or_create_node(p.x, p.y)
                nodes.append(n)
            
            if nodes:
                poly = RoomItem(nodes, room_type=room.room_type, room_id=room.id)
                self.scene.addItem(poly)
                # Ensure edges exist for room boundary? 
                # User might expect them. For now, following logic of DrawRectTool which adds edges.
                for i in range(len(nodes)):
                    n_start = nodes[i]
                    n_end = nodes[(i+1)%len(nodes)]
                    # Check if edge exists
                    existing_edge = False
                    for edge in n_start.edges:
                        if edge.end_node == n_end or edge.start_node == n_end:
                            existing_edge = True
                            break
                    if not existing_edge:
                         edge = EdgeItem(n_start, n_end)
                         self.scene.addItem(edge)
                
        # Background?
        # Data/JSON currently doesn't refer to the background image file (PLY source or Slice Image).
        # We might want to keep the current background if just loading annotations, 
        # or we might need to store the background image path in ProjectData.
        # For now, we assume the user loads 3D data first, then loads annotations.
        # But `scene.clear()` wiped the background item! We must restore it if it existed.
        if self.background_item:
             # Wait, self.background_item was a wrapper around value. 
             # But scene.clear() removed it from scene.
             # We should re-add it.
             self.scene.addItem(self.background_item)
             config = ConfigManager.instance()
             self.background_item.setZValue(config.get_value("colors", "background", "z_value") or -100) # Ensure it's behind
