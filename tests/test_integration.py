
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QGraphicsScene
from PyQt6.QtCore import QPointF, Qt, QPoint
from PyQt6.QtGui import QUndoStack
import sys

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.gui.canvas_2d import Canvas2D
from src.core.input_context import InputContext
from src.gui.items import NodeItem, EdgeItem
from src.core.undo_commands import AddItemCommand

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.canvas = Canvas2D()
        self.undo_stack = QUndoStack()
        self.canvas.set_undo_stack(self.undo_stack)
        
    def create_context(self, x, y, buttons=Qt.MouseButton.LeftButton):
        return InputContext(
            scene_pos=QPointF(x, y),
            screen_pos=QPoint(int(x), int(y)),
            buttons=buttons
        )

    def test_draw_wall_flow(self):
        # 1. Select Wall Tool
        self.canvas.set_tool("wall")
        
        # 2. Click (Start)
        ctx1 = self.create_context(0, 0)
        self.canvas.wall_tool.on_mouse_press(ctx1)
        
        # Verify node added
        items = self.canvas.scene.items()
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0], NodeItem)
        node1 = items[0]
        
        # 3. Click (End)
        ctx2 = self.create_context(100, 0)
        self.canvas.wall_tool.on_mouse_press(ctx2)
        
        # Verify edge and node added
        items = self.canvas.scene.items()
        # Should be node1, edge, node2 (plus maybe background if set, but it's None)
        self.assertEqual(len(items), 3) # Node1, Edge, Node2
        
        # 4. Undo
        self.undo_stack.undo()
        # Should remove Edge and Node2, keeping Node1 (because they were separate commands? 
        # Wall tool adds first node immediately in one command, 
        # then adds edge+node2 in another command.)
        
        items_after_undo = self.canvas.scene.items()
        self.assertEqual(len(items_after_undo), 1)
        self.assertEqual(items_after_undo[0], node1)

        # 5. Redo
        self.undo_stack.redo()
        self.assertEqual(len(self.canvas.scene.items()), 3)

    def test_select_move_undo_flow(self):
        # Setup scene with one node
        node = NodeItem(50, 50)
        self.canvas.scene.addItem(node)
        
        self.canvas.set_tool("select")
        
        # Press on node
        ctx_press = self.create_context(50, 50)
        self.canvas.select_tool.on_mouse_press(ctx_press)
        
        # Simulate Move (manually update pos as per previous finding)
        node.setPos(150, 150)
        
        # Release
        ctx_release = self.create_context(150, 150)
        self.canvas.select_tool.on_mouse_release(ctx_release)
        
        # Verify Undo Stack has command
        self.assertEqual(self.undo_stack.count(), 1)
        
        # Undo
        self.undo_stack.undo()
        self.assertEqual(node.pos(), QPointF(50, 50))
        
        # Redo
        self.undo_stack.redo()
        self.assertEqual(node.pos(), QPointF(150, 150))

if __name__ == "__main__":
    unittest.main()
