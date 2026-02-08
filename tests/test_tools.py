
import unittest
from unittest.mock import MagicMock, call
from PyQt6.QtWidgets import QApplication, QGraphicsScene
from PyQt6.QtCore import QPointF, Qt, QPoint
import sys

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.core.input_context import InputContext
from src.gui.tools import SelectTool, DrawWallTool, DrawRectTool
from src.gui.items import NodeItem
from src.core.undo_commands import AddItemCommand, MoveNodeCommand

class MockCanvas:
    def __init__(self):
        self.scene = QGraphicsScene()
        self.background_item = None
        self.status_message = MagicMock()
        self.push_command = MagicMock()
    
    def transform(self):
        return MagicMock()

    def set_tool(self, tool_name):
        pass

class TestTools(unittest.TestCase):
    def setUp(self):
        self.canvas = MockCanvas()
        
    def create_context(self, scene_pos, buttons=Qt.MouseButton.LeftButton):
        # We need to make sure buttons are set correctly for tools that check them.
        # DrawRectTool checks for LeftButton in mouseMove/Release?
        # Actually standard practice is press sets button, move/release might typically track buttons.
        return InputContext(
            scene_pos=scene_pos,
            screen_pos=QPoint(int(scene_pos.x()), int(scene_pos.y())),
            buttons=buttons
        )

    def test_select_tool_move(self):
        tool = SelectTool(self.canvas)
        
        # Add a node
        node = NodeItem(0, 0)
        self.canvas.scene.addItem(node)
        
        # We can patch scene.items directly on the instance
        # Note: In PyQt/PySide some methods are not easily monkeypatched on instance if they are C++ slots
        # But usually straightforward assignment works for python access.
        
        self.canvas.scene.items = unittest.mock.MagicMock(return_value=[node])
        
        # Select (Press)
        ctx_press = self.create_context(QPointF(0, 0))
        tool.on_mouse_press(ctx_press)
        
        # Verify selection
        self.assertEqual(tool.moving_item, node)
        
        # Move (Release at different pos)
        ctx_release = self.create_context(QPointF(100, 100))
        
        # Simulate manual move since no event loop
        node.setPos(100, 100) 
        tool.on_mouse_release(ctx_release)
    
        # Verify Command Pushed
        # If start_pos != end_pos, it should push command.
        if self.canvas.push_command.call_count == 0:
            print(f"DEBUG: SelectTool failed. Start: {tool.start_pos}, End: {ctx_release.scene_pos}")
            
        self.assertEqual(self.canvas.push_command.call_count, 1)

    def test_rec_tool_create(self): # Renamed to force re-run if needed, but keeping name same
        self.canvas.push_command.reset_mock() # Reset count
        tool = DrawRectTool(self.canvas)
        
        # Press (Start)
        ctx_press = self.create_context(QPointF(0, 0))
        tool.on_mouse_press(ctx_press)
        
        # Release (End) - Ensure it's far enough
        ctx_release = self.create_context(QPointF(100, 100))
        tool.on_mouse_release(ctx_release)
        
        # Verify Command Pushed
        # DrawRectTool checks for self.start_pos. 
        # on_mouse_press sets self.drag_start = context.scene_pos
        # on_mouse_release uses self.drag_start
        
        if self.canvas.push_command.call_count == 0:
             print(f"DEBUG: RectTool failed. Start: {tool.start_pos}")

        self.assertEqual(self.canvas.push_command.call_count, 1)
        cmd = self.canvas.push_command.call_args[0][0]
        self.assertIsInstance(cmd, AddItemCommand)

if __name__ == "__main__":
    unittest.main()
