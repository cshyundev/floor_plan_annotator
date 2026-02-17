import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsItem
from src.core.undo_commands import AddItemCommand, DeleteItemCommand, MoveNodesCommand, ChangeRoomTypeCommand
from src.gui.items import NodeItem, RoomItem

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

if __name__ == "__main__":
    unittest.main()
