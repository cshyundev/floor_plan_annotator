from PyQt6.QtGui import QUndoCommand
from PyQt6.QtCore import QPointF
# Imports for type hinting if needed, but avoiding circular deps if they exist
# from src.gui.items import NodeItem 

class AddItemCommand(QUndoCommand):
    def __init__(self, scene, items, description="Add Items"):
        super().__init__()
        self.setText(description)
        self.scene = scene
        self.items = items
        
    def redo(self):
        for item in self.items:
            if item.scene() != self.scene:
                self.scene.addItem(item)
            
    def undo(self):
        for item in self.items:
            if item.scene() == self.scene:
                self.scene.removeItem(item)

class DeleteItemCommand(QUndoCommand):
    def __init__(self, scene, items, description="Delete Items"):
        super().__init__()
        self.setText(description)
        self.scene = scene
        self.items = items
        
    def redo(self):
        for item in self.items:
            if item.scene() == self.scene:
                self.scene.removeItem(item)
                
    def undo(self):
        for item in self.items:
            if item.scene() != self.scene:
                self.scene.addItem(item)

class MoveNodeCommand(QUndoCommand):
    def __init__(self, node, old_pos: QPointF, new_pos: QPointF):
        super().__init__()
        self.setText("Move Node")
        self.node = node
        self.old_pos = old_pos
        self.new_pos = new_pos
        
    def redo(self):
        self.node.setPos(self.new_pos)
        
    def undo(self):
        self.node.setPos(self.old_pos)

class MoveNodesCommand(QUndoCommand):
    def __init__(self, nodes, old_positions, new_positions):
        super().__init__(f"Move {len(nodes)} Nodes")
        self.nodes = nodes
        self.old_positions = old_positions
        self.new_positions = new_positions

    def undo(self):
        for i, node in enumerate(self.nodes):
            node.setPos(self.old_positions[i])

    def redo(self):
        for i, node in enumerate(self.nodes):
            node.setPos(self.new_positions[i])

class ChangeCustomPolygonTypeCommand(QUndoCommand):
    def __init__(self, polygon_item, old_type, new_type):
        super().__init__(f"Change Custom Polygon Type to {new_type}")
        self.polygon_item = polygon_item
        self.old_type = old_type
        self.new_type = new_type

    def redo(self):
        self.polygon_item.polygon_type = self.new_type
        self.polygon_item.update_style()
        self.polygon_item.update_overlay()

    def undo(self):
        self.polygon_item.polygon_type = self.old_type
        self.polygon_item.update_style()
        self.polygon_item.update_overlay()


class ChangeObjectTypeCommand(QUndoCommand):
    def __init__(self, object_item, old_type, new_type):
        super().__init__(f"Change Object Type to {new_type}")
        self.object_item = object_item
        self.old_type = old_type
        self.new_type = new_type
        self.old_elevation = object_item.elevation
        self.old_height_3d = object_item.height_3d
        from src.core.config import ConfigManager
        config = ConfigManager.instance()
        self.new_elevation, self.new_height_3d = config.get_object_3d_defaults(new_type)

    def redo(self):
        self.object_item.object_type = self.new_type
        self.object_item.elevation = self.new_elevation
        self.object_item.height_3d = self.new_height_3d
        self.object_item.update_style()

    def undo(self):
        self.object_item.object_type = self.old_type
        self.object_item.elevation = self.old_elevation
        self.object_item.height_3d = self.old_height_3d
        self.object_item.update_style()


class ChangeObject3DPropertiesCommand(QUndoCommand):
    """Undo command for changing object elevation and 3D height."""

    def __init__(self, object_item, old_elevation, old_height_3d,
                 new_elevation, new_height_3d):
        super().__init__("Change Object 3D Properties")
        self.object_item = object_item
        self.old_elevation = old_elevation
        self.old_height_3d = old_height_3d
        self.new_elevation = new_elevation
        self.new_height_3d = new_height_3d

    def redo(self):
        self.object_item.elevation = self.new_elevation
        self.object_item.height_3d = self.new_height_3d

    def undo(self):
        self.object_item.elevation = self.old_elevation
        self.object_item.height_3d = self.old_height_3d


class TransformObjectCommand(QUndoCommand):
    """Undo command for any OBB transformation (move/resize/rotate)."""

    def __init__(self, object_item, old_state, new_state):
        """
        Args:
            object_item: ObjectItem
            old_state: (center, width, height, angle)
            new_state: (center, width, height, angle)
        """
        super().__init__("Transform Object")
        self.object_item = object_item
        self.old_state = old_state
        self.new_state = new_state

    def _apply(self, state):
        center, width, height, angle = state
        self.object_item.center = center
        self.object_item.width = width
        self.object_item.height = height
        self.object_item.angle = angle
        self.object_item.update_shape()

    def redo(self):
        self._apply(self.new_state)

    def undo(self):
        self._apply(self.old_state)


class ChangeRoomTypeCommand(QUndoCommand):
    def __init__(self, room_item, old_type, new_type):
        super().__init__(f"Change Room Type to {new_type}")
        self.room_item = room_item
        self.old_type = old_type
        self.new_type = new_type

    def redo(self):
        self.room_item.room_type = self.new_type
        self.room_item.update_style()
        self.room_item.update_overlay()

    def undo(self):
        self.room_item.room_type = self.old_type
        self.room_item.update_style()
        self.room_item.update_overlay()
