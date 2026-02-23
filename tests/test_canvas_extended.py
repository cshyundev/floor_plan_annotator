import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QGraphicsScene
from PyQt6.QtCore import Qt, QPointF
import sys

if not QApplication.instance():
    app = QApplication(sys.argv)

from src.gui.canvas_2d import Canvas2D
from src.gui.items import NodeItem, EdgeItem, RoomItem, CustomPolygonItem, ObjectItem

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
        
        
    def test_delete_node_also_deletes_connected_edges(self):
        """Deleting a NodeItem must also delete its connected EdgeItems (BUG-001)."""
        n1 = NodeItem(0, 0)
        n2 = NodeItem(10, 0)
        self.canvas.scene.addItem(n1)
        self.canvas.scene.addItem(n2)
        edge = EdgeItem(n1, n2)
        self.canvas.scene.addItem(edge)

        self.canvas._undo_stack = MagicMock()
        with patch.object(self.canvas.scene, 'selectedItems', return_value=[n1]):
            self.canvas.delete_selected_items()

        cmd = self.canvas._undo_stack.push.call_args[0][0]
        deleted_items = set(cmd.items)
        self.assertIn(n1, deleted_items)
        self.assertIn(edge, deleted_items)

    def test_delete_node_with_multiple_edges(self):
        """Deleting a node connected to multiple edges must delete all of them (BUG-001)."""
        n1 = NodeItem(0, 0)
        n2 = NodeItem(10, 0)
        n3 = NodeItem(0, 10)
        for n in (n1, n2, n3):
            self.canvas.scene.addItem(n)
        edge1 = EdgeItem(n1, n2)
        edge2 = EdgeItem(n1, n3)
        self.canvas.scene.addItem(edge1)
        self.canvas.scene.addItem(edge2)

        self.canvas._undo_stack = MagicMock()
        with patch.object(self.canvas.scene, 'selectedItems', return_value=[n1]):
            self.canvas.delete_selected_items()

        cmd = self.canvas._undo_stack.push.call_args[0][0]
        deleted_items = set(cmd.items)
        self.assertIn(n1, deleted_items)
        self.assertIn(edge1, deleted_items)
        self.assertIn(edge2, deleted_items)

    def test_context_menu_event(self):
        pass

    def test_set_tool(self):
        self.canvas.set_tool("select")
        self.assertEqual(self.canvas.current_tool, self.canvas.select_tool)

        self.canvas.set_tool("wall")
        self.assertEqual(self.canvas.current_tool, self.canvas.wall_tool)

        self.canvas.set_tool("room")
        self.assertEqual(self.canvas.current_tool, self.canvas.room_tool)

        self.canvas.set_tool("custom_polygon")
        self.assertEqual(self.canvas.current_tool, self.canvas.tool_manager.custom_polygon_tool)

        self.canvas.set_tool("object")
        self.assertEqual(self.canvas.current_tool, self.canvas.tool_manager.object_tool)
        
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

    def test_save_load_custom_polygon(self):
        """CustomPolygonItem should be saved to and loaded from ProjectData."""
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        for n in nodes:
            self.canvas.scene.addItem(n)
        poly = CustomPolygonItem(nodes, polygon_type="clean_zone", polygon_id="0")
        self.canvas.scene.addItem(poly)

        data = self.canvas.save_to_data()
        self.assertEqual(len(data.custom_polygons), 1)
        self.assertEqual(data.custom_polygons[0].polygon_type, "clean_zone")

        self.canvas.load_from_data(data)
        cp_items = [i for i in self.canvas.scene.items() if isinstance(i, CustomPolygonItem)]
        self.assertEqual(len(cp_items), 1)
        self.assertEqual(cp_items[0].polygon_type, "clean_zone")

    def test_save_load_object(self):
        """ObjectItem should be saved to and loaded from ProjectData."""
        obj = ObjectItem(center=QPointF(5.0, 5.0), width=2.0, height=1.0,
                         angle=30.0, object_type="furniture", object_id="0")
        self.canvas.scene.addItem(obj)

        data = self.canvas.save_to_data()
        self.assertEqual(len(data.objects), 1)
        self.assertAlmostEqual(data.objects[0].rotation, 30.0)

        self.canvas.load_from_data(data)
        obj_items = [i for i in self.canvas.scene.items() if isinstance(i, ObjectItem)]
        self.assertEqual(len(obj_items), 1)
        self.assertAlmostEqual(obj_items[0].angle, 30.0)


if __name__ == "__main__":
    unittest.main()
