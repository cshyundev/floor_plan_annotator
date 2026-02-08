
import unittest
from PyQt6.QtWidgets import QGraphicsScene, QApplication
from PyQt6.QtCore import QPointF
import sys

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.core.undo_commands import AddItemCommand, MoveNodeCommand
from src.gui.items import NodeItem

class TestCommands(unittest.TestCase):
    def setUp(self):
        self.scene = QGraphicsScene()

    def test_add_item_command(self):
        node = NodeItem(0, 0)
        cmd = AddItemCommand(self.scene, [node], "Add Node")
        
        # Initial state (added only after redo or push?)
        # QUndoCommand logic: construction doesn't execute redo automatically unless pushed to stack.
        # But our usage in tools is: push_command(cmd) -> stack.push(cmd) -> cmd.redo()
        
        # Test Redo (Add)
        cmd.redo()
        self.assertIn(node, self.scene.items())
        
        # Test Undo (Remove)
        cmd.undo()
        self.assertNotIn(node, self.scene.items())
        
    def test_move_node_command(self):
        node = NodeItem(0, 0)
        self.scene.addItem(node)
        
        start_pos = QPointF(0, 0)
        end_pos = QPointF(100, 100)
        
        cmd = MoveNodeCommand(node, start_pos, end_pos)
        
        # Test Redo (Move)
        cmd.redo()
        self.assertEqual(node.pos(), end_pos)
        
        # Test Undo (Move back)
        cmd.undo()
        self.assertEqual(node.pos(), start_pos)

if __name__ == "__main__":
    unittest.main()
