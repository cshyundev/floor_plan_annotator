import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsItem, QApplication
from PyQt6.QtCore import QPointF
import sys
if not QApplication.instance():
    app = QApplication(sys.argv)
from src.core.undo_commands import (AddItemCommand, DeleteItemCommand, MoveNodesCommand,
                                     ChangeRoomTypeCommand, ChangeCustomPolygonTypeCommand,
                                     ChangeObjectTypeCommand, TransformObjectCommand)
from src.gui.items import NodeItem, RoomItem, CustomPolygonItem, ObjectItem

class TestCommandsExtended(unittest.TestCase):
    def setUp(self):
        self.scene = QGraphicsScene()
        
    def test_add_item_command(self):
        item = NodeItem(0, 0)
        cmd = AddItemCommand(self.scene, [item], "Add Node")
        
        # Initial state: redo() called in init? No, usually pushed to stack.
        # But command constructor doesn't call redo.
        
        cmd.redo()
        self.assertIn(item, self.scene.items())
        
        cmd.undo()
        self.assertNotIn(item, self.scene.items())
        
    def test_delete_item_command(self):
        item = NodeItem(0, 0)
        self.scene.addItem(item)
        
        cmd = DeleteItemCommand(self.scene, [item], "Delete Node")
        cmd.redo()
        self.assertNotIn(item, self.scene.items())
        
        cmd.undo()
        self.assertIn(item, self.scene.items())
        
    def test_move_nodes_command(self):
        node = NodeItem(0, 0)
        self.scene.addItem(node)
        
        old_pos_list = [node.pos()]
        from PyQt6.QtCore import QPointF
        new_pos_list = [QPointF(10, 10)]
        
        cmd = MoveNodesCommand([node], old_pos_list, new_pos_list)
        cmd.redo()
        self.assertEqual(node.pos(), QPointF(10, 10))
        
        cmd.undo()
        self.assertEqual(node.pos(), QPointF(0, 0))
        
    def test_change_room_type_command(self):
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        room = RoomItem(nodes, room_type="living_room")
        self.scene.addItem(room)
        
        cmd = ChangeRoomTypeCommand(room, "living_room", "kitchen")
        cmd.redo()
        self.assertEqual(room.room_type, "kitchen")
        
        cmd.undo()
        self.assertEqual(room.room_type, "living_room")

    def test_change_custom_polygon_type_command(self):
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        poly = CustomPolygonItem(nodes, polygon_type="clean_zone")
        self.scene.addItem(poly)

        cmd = ChangeCustomPolygonTypeCommand(poly, "clean_zone", "danger_zone")
        cmd.redo()
        self.assertEqual(poly.polygon_type, "danger_zone")

        cmd.undo()
        self.assertEqual(poly.polygon_type, "clean_zone")

    def test_change_object_type_command(self):
        center = QPointF(5.0, 5.0)
        obj = ObjectItem(center=center, width=2.0, height=1.0,
                         object_type="furniture", object_id="1")
        self.scene.addItem(obj)

        cmd = ChangeObjectTypeCommand(obj, "furniture", "obstacle")
        cmd.redo()
        self.assertEqual(obj.object_type, "obstacle")

        cmd.undo()
        self.assertEqual(obj.object_type, "furniture")

    def test_transform_object_command(self):
        center = QPointF(0.0, 0.0)
        obj = ObjectItem(center=center, width=2.0, height=1.0, angle=0.0,
                         object_type="furniture", object_id="2")
        self.scene.addItem(obj)

        old_state = (QPointF(0.0, 0.0), 2.0, 1.0, 0.0)
        new_state = (QPointF(5.0, 5.0), 4.0, 2.0, 45.0)

        cmd = TransformObjectCommand(obj, old_state, new_state)
        cmd.redo()
        self.assertEqual(obj.center, QPointF(5.0, 5.0))
        self.assertEqual(obj.width, 4.0)
        self.assertEqual(obj.angle, 45.0)

        cmd.undo()
        self.assertEqual(obj.center, QPointF(0.0, 0.0))
        self.assertEqual(obj.width, 2.0)
        self.assertEqual(obj.angle, 0.0)


if __name__ == "__main__":
    unittest.main()
