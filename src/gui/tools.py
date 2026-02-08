from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QInputDialog
from src.gui.items import NodeItem, EdgeItem, RoomItem
from src.core.undo_commands import AddItemCommand, MoveNodeCommand
from src.core.input_context import InputContext
from src.core.config import ConfigManager

class Tool:
    def __init__(self, canvas):
        self.canvas = canvas
        self.scene = canvas.scene
    
    def on_mouse_press(self, context: InputContext): pass
    def on_mouse_move(self, context: InputContext): pass
    def on_mouse_release(self, context: InputContext): pass

class SelectTool(Tool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.moving_item = None
        self.start_pos = None

    def on_mouse_press(self, context: InputContext):
        # Check item at scene pos
        # View transform needed for precise picking? 
        # itemAt uses view transform usually. 
        # But we have scene pos. scene.itemAt also takes transform.
        # We can ask canvas for transform or use scene.items(pos).
        
        # items(pos) returns all items at pos.
        item = None
        items = self.scene.items(context.scene_pos)
        if items:
            item = items[0]
            
        config = ConfigManager.instance()
        
        if isinstance(item, NodeItem):
            self.moving_item = item
            self.start_pos = item.pos()
            self.canvas.status_message.emit(config.get_string("tools", "select", "moving"))
        # If clicked on background/nothing, clear selection
        elif not item or item == self.canvas.background_item:
            self.scene.clearSelection()
            self.canvas.status_message.emit(config.get_string("tools", "select", "cleared"))
        else:
             # Select the item
             item.setSelected(True)
             self.canvas.status_message.emit(config.get_string("tools", "select", "selected"))

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
        if self.moving_item and self.start_pos is not None:
            end_pos = self.moving_item.pos()
            if end_pos != self.start_pos:
                # Push Undo Command
                cmd = MoveNodeCommand(self.moving_item, self.start_pos, end_pos)
                self.canvas.push_command(cmd)
        
        self.moving_item = None
        self.start_pos = None

class DrawWallTool(Tool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.current_start_node = None
        
    def on_mouse_press(self, context: InputContext):
        if context.buttons == Qt.MouseButton.LeftButton:
            pos = context.scene_pos
            
            # Check if we clicked an existing node (snapping)
            clicked_node = self.find_node_at(pos)
            
            config = ConfigManager.instance()
            
            if not self.current_start_node:
                # First click: Start Wall
                if clicked_node:
                    self.current_start_node = clicked_node
                else:
                    self.current_start_node = NodeItem(pos.x(), pos.y())
                    # For the first node, we add it immediately. 
                    cmd = AddItemCommand(self.scene, [self.current_start_node], config.get_string("tools", "wall", "add_node_cmd"))
                    self.canvas.push_command(cmd)
                self.canvas.status_message.emit(config.get_string("tools", "wall", "started"))
            else:
                # Second click: End Wall
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
                        cmd = AddItemCommand(self.scene, new_items, config.get_string("tools", "wall", "add_wall_cmd"))
                        self.canvas.push_command(cmd)
                        self.canvas.status_message.emit(config.get_string("tools", "wall", "segment_added"))
                
                # Chain
                self.current_start_node = end_node

    def on_mouse_release(self, context: InputContext):
        if context.buttons == Qt.MouseButton.RightButton:
             # Stop drawing chain
             self.current_start_node = None
             config = ConfigManager.instance()
             self.canvas.status_message.emit(config.get_string("tools", "wall", "finished"))
    
    def find_node_at(self, pos, tolerance=10):
        # We can implement custom spatial search or use scene.items
        # tolerance is in scene units if we use a rect
        rect = QPointF(tolerance, tolerance)
        # items = self.scene.items(QRectF(pos - rect, pos + rect)) # Logic requires QRectF import
        items = self.scene.items(pos)
        for item in items:
            if isinstance(item, NodeItem):
                return item
        return None

class DrawRoomTool(Tool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.current_nodes = [] # List of NodeItems
        self.temp_visuals = [] # Edges/Lines for visualization
        
    def on_mouse_press(self, context: InputContext):
        config = ConfigManager.instance()
        
        if context.buttons == Qt.MouseButton.LeftButton:
            pos = context.scene_pos
            
            # Snap?
            # For now, simple click
            node = NodeItem(pos.x(), pos.y())
            self.scene.addItem(node)
            self.current_nodes.append(node)
            
            # Visual feedback (Edge from prev node)
            if len(self.current_nodes) > 1:
                prev = self.current_nodes[-2]
                # We typically want persistent edges for Walls, but for Room polygon, 
                # we might just want to visualize the boundary.
                # However, RoomItem constructs itself from Nodes. 
                # If we want the boundary to be Walls, we should create Wall/EdgeItems.
                # User said: "Layout(Wall)과 동일한 점을 공유할수도, 아닐수도 있어. Layout과 차이점은 Room은 엣지들이 반드시 벽이 아닐 수 있어."
                # So Room edges are NOT necessarily Wall EdgeItems.
                # But RoomItem visuals (polygon stroke) will show the boundary.
                pass
            
            self.canvas.status_message.emit(config.get_string("tools", "room", "add_point").format(len(self.current_nodes)))
            
        elif context.buttons == Qt.MouseButton.RightButton:
            # Finish
            if len(self.current_nodes) < 3:
                # Cancel or not enough points
                self.cleanup()
                self.canvas.status_message.emit("Cancelled or not enough points.")
                return

            # Select Type
            room_config = config.get_value("rooms", "types")
            if room_config:
                types = list(room_config.keys())
                display_names = [f"{k}: {v['name']}" for k, v in room_config.items()]
                item, ok = QInputDialog.getItem(self.canvas, "Select Room Type", "Room Type:", display_names, 0, False)
                if ok and item:
                    selected_key = item.split(":")[0]
                else:
                    selected_key = config.get_value("rooms", "default_type")
            else:
                selected_key = "default"
            
            # Create RoomItem
            # We already added nodes to scene.
            # Create RoomItem
            # Use AddItemCommand for undo, but we have multiple items (nodes + room)
            # Logic: We already added nodes to scene? 
            # If we use Undo, we should package them.
            # Currently I added nodes directly to scene in on_mouse_press. 
            # Ideally we should use a temporary visual and only commit on finish.
            # Refactor: 
            # 1. Remove nodes from scene (they were just visual/temp?)
            # 2. Command adds them back properly.
            
            # For now, let's just use what we have, but we need to ensure Undo works.
            # If I don't use Command for nodes, they are in scene but not in Undo stack.
            # Better: Collect points, create Nodes in Command.
            scene_nodes = self.current_nodes
            for n in scene_nodes:
                if n.scene() == self.scene:
                    self.scene.removeItem(n) # Remove from scene to let Command handle it
            
            # Create Command
            room_item = RoomItem(scene_nodes, room_type=selected_key)
            # Edges? Room edges are not necessarily Walls. RoomItem draws its own boundary.
            
            all_items = scene_nodes + [room_item]
            cmd = AddItemCommand(self.scene, all_items, "Add Room")
            self.canvas.push_command(cmd)
            
            self.current_nodes = []
            self.canvas.status_message.emit(f"Room '{selected_key}' created.")

    def cleanup(self):
        for n in self.current_nodes:
            if n.scene() == self.scene:
                self.scene.removeItem(n)
        self.current_nodes = []
