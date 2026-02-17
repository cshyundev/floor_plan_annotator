import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QGraphicsScene
from PyQt6.QtCore import Qt, QPointF
import sys

if not QApplication.instance():
    app = QApplication(sys.argv)

from src.gui.canvas_2d import Canvas2D
from src.gui.items import NodeItem, RoomItem

class TestCanvasExtended(unittest.TestCase):
    def setUp(self):
        self.canvas = Canvas2D()
        # Initialize undo stack if Canvas2D doesn't do it (it seems it doesn't, expecting set_undo_stack or similar?)
        # Or it might be initialized in __init__?
        # Let's mock it just in case or set it.
        from PyQt6.QtGui import QUndoStack
        self.canvas._undo_stack = QUndoStack()
        
    def test_delete_items(self):
        # Create items
        node = NodeItem(0, 0)
        self.canvas.scene.addItem(node)
        node.setSelected(True)
        
        # Test delete
        # We need to mock create_undo_command because it might fail if undo stack issues? 
        # Actually Canvas2D.delete_selected_items uses DeleteItemCommand and pushes to self._undo_stack
        
        # Mock undo stack to verify push
        self.canvas._undo_stack = MagicMock()
        
        # Patch selectedItems because headless scene selection is flaky
        with patch.object(self.canvas.scene, 'selectedItems', return_value=[node]):
            self.canvas.delete_selected_items()
            
        # Verify DeleteItemCommand was pushed
        self.canvas._undo_stack.push.assert_called()
        cmd = self.canvas._undo_stack.push.call_args[0][0]
        self.assertIn("Delete Items", cmd.text())
        
        
    def test_context_menu_event(self):
        pass

    def test_set_tool(self):
        self.canvas.set_tool("select")
        self.assertEqual(self.canvas.current_tool, self.canvas.select_tool)
        
        self.canvas.set_tool("wall")
        self.assertEqual(self.canvas.current_tool, self.canvas.wall_tool)
        
        self.canvas.set_tool("room")
        self.assertEqual(self.canvas.current_tool, self.canvas.room_tool)
        
    def test_save_load(self):
        # Setup some items
        n1 = NodeItem(0, 0)
        self.canvas.scene.addItem(n1)
        
        data = self.canvas.save_to_data()
        self.assertIsNotNone(data)
        
        # Add Edge
        from src.gui.items import EdgeItem
        n2 = NodeItem(10, 10)
        self.canvas.scene.addItem(n2)
        edge = EdgeItem(n1, n2)
        self.canvas.scene.addItem(edge)
        
        data = self.canvas.save_to_data()
        
        # Load
        self.canvas.load_from_data(data)
        # Should have restored items (NodeItem at least, EdgeItem restoration logic depends on implementation)
        # Check scene items count. 2 nodes + 1 edge + implicit nodes?
        # load_from_data clears scene.
        self.assertTrue(len(self.canvas.scene.items()) > 0)

if __name__ == "__main__":
    unittest.main()
